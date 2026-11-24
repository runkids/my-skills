"""compactPathLinks prints a link whose text is its own root-relative target as that path."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fixture_helpers import run_router, write_fixture


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ai-context.py'
sys.dont_write_bytecode = True
ROW = '| Ship it | [docs/run.md](../docs/run.md) |\n'


class CompactPathLinksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir()
        shutil.copy2(SCRIPT, self.script)
        write_fixture(self.root, 'AGENTS.md', '`guide`\n')
        write_fixture(self.root, 'wiki/README.md', '# Topics\n')
        write_fixture(self.root, 'docs/run.md', 'Run.\n')
        self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
            {'path': 'wiki/guide.md'}]}}}

    def configure(self, value=True, **topic):
        if value is not None:
            self.cfg['compactPathLinks'] = value
        self.cfg['topics']['guide'].update(topic)
        write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))

    def guide(self, text, *args):
        write_fixture(self.root, 'wiki/guide.md', text)
        return run_router(self.script, *(args or ('guide',)))

    def assertOut(self, result, expected):
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, '<!-- wiki/guide.md -->\n' + expected)

    def test_default_and_false_print_the_page_unchanged(self):
        for value in (None, False):
            with self.subTest(value=value):
                self.cfg.pop('compactPathLinks', None)
                self.configure(value)
                self.assertOut(self.guide(ROW), ROW)

    def test_self_link_prints_its_path_once(self):
        self.configure()
        self.assertOut(self.guide(ROW + '- [docs/run.md](../docs/run.md) and more.\n'
                                  '[./docs/run.md](../docs/run.md) [docs//run.md](../docs/run.md)\n'),
                       '| Ship it | `docs/run.md` |\n- `docs/run.md` and more.\n'
                       '`docs/run.md` `docs/run.md`\n')

    def test_other_links_are_kept_byte_for_byte(self):
        self.configure()
        kept = ('[run](../docs/run.md)\n'                     # text is not the path
                '[docs/run.md](run.md)\n'                     # text names another file
                '[docs/run.md](../docs/run.md#step)\n'        # fragment
                '[docs/run.md](../docs/run.md "Title")\n'     # title
                '![docs/run.md](../docs/run.md)\n'            # image
                '[docs/run.md][ref]\n\n[ref]: ../docs/run.md\n'  # reference link
                '![outer [docs/run.md](../docs/run.md)](image.png)\n'
                '[https://x.dev/a](https://x.dev/a)\n'        # URL
                '[/docs/run.md](/docs/run.md)\n'              # absolute
                '[docs/my run.md](../docs/my%20run.md)\n'     # not a plain path
                '```\n[docs/run.md](../docs/run.md)\n```\n'   # fenced code
                '`[docs/run.md](../docs/run.md)`\n')         # inline code
        self.assertOut(self.guide(kept), kept)

    def test_adjacent_existing_code_remains_separate(self):
        self.configure()
        link = '[docs/run.md](../docs/run.md)'
        code = '`docs/run.md`'
        sep = '<!-- -->'
        self.assertOut(self.guide(f'`before`{link}\n{link}`after`\n'
                                  f'`before`{link}{link}`after`\n'),
                       f'`before`{sep}{code}\n{code}{sep}`after`\n'
                       f'`before`{sep}{code}{sep}{code}{sep}`after`\n')
        self.assertOut(self.guide(f'{link}{link}\n'), f'{code}{sep}{code}\n')

    def test_container_prefixes_preserve_token_offsets(self):
        self.configure()
        # The tab line comes first so its width must carry into the lines after it.
        line = ('>\t[docs/run.md](../docs/run.md)\n'
                '> [docs/run.md](../docs/run.md)\n'
                '- item\n  > [docs/run.md](../docs/run.md)\n')
        expected = ('>\t`docs/run.md`\n'
                    '> `docs/run.md`\n'
                    '- item\n  > `docs/run.md`\n')
        self.assertOut(self.guide(line), expected)

    def test_check_budgets_compact_output_and_still_validates_targets(self):
        printed = len(('<!-- wiki/guide.md -->\n' + '| Ship it | `docs/run.md` |').encode())
        self.configure(maxBytes=printed)
        result = self.guide(ROW, 'check')
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.configure(False)  # Control: without the option the same page exceeds the cap.
        result = run_router(self.script, 'check')
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stdout, rf'FAIL guide: \d+ B > {printed} ')
        # A moved leaf still fails check with the option on.
        self.configure(True)
        (self.root / 'docs/run.md').rename(self.root / 'docs/moved.md')
        result = run_router(self.script, 'check')
        self.assertEqual(result.returncode, 1)
        self.assertIn("relative link '../docs/run.md' is not a file inside repo", result.stdout)

    def test_mounted_path_with_a_backtick_keeps_its_link(self):
        link = '[docs/run.md](../docs/run.md)'
        inner = self.root / 'modules/a`b'
        write_fixture(inner, 'AGENTS.md', '`guide`\n')
        write_fixture(inner, 'wiki/README.md', '# Topics\n')
        write_fixture(inner, 'docs/run.md', 'Run.\n')
        write_fixture(inner, 'wiki/guide.md', f'{link} [wiki/guide.md](guide.md)\n')
        write_fixture(inner, 'wiki/ai-context.json', json.dumps({
            'compactPathLinks': True, 'topics': {'guide': {'description': 'Inner',
                'sources': [{'path': 'wiki/guide.md'}]}}}))
        self.cfg['mounts'] = {'kb': {'root': 'modules/a`b'}}
        self.configure(None)
        result = run_router(self.script, 'kb/guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, f'<!-- modules/a`b/wiki/guide.md -->\n{link} [wiki/guide.md](guide.md)\n')

    def test_mounted_config_uses_its_own_setting(self):
        inner = self.root / 'modules/kb'
        write_fixture(inner, 'AGENTS.md', '`guide`\n')
        write_fixture(inner, 'wiki/README.md', '# Topics\n')
        write_fixture(inner, 'docs/run.md', 'Inner run.\n')
        write_fixture(inner, 'wiki/guide.md', '# Guide\n' + ROW.replace('[docs/', '[./docs/') + '# Other\n')
        native = '<!-- wiki/guide.md § Guide -->\n# Guide\n| Ship it | `docs/run.md` |'
        write_fixture(inner, 'wiki/ai-context.json', json.dumps({
            'compactPathLinks': True, 'topics': {'guide': {'description': 'Inner',
                'maxBytes': len(native.encode()), 'sources': [
                    {'path': 'wiki/guide.md', 'heading': 'Guide'}]}}}))
        self.cfg['mounts'] = {'kb': {'root': 'modules/kb'}}
        self.configure(None)
        result = self.guide(ROW, 'guide', 'kb/guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, '<!-- wiki/guide.md -->\n' + ROW.strip() + '\n\n'
                         '<!-- modules/kb/wiki/guide.md § Guide -->\n# Guide\n'
                         '| Ship it | `modules/kb/docs/run.md` |\n')
        inner_script = inner / 'scripts/ai-context.py'
        inner_script.parent.mkdir()
        shutil.copy2(SCRIPT, inner_script)
        native_result = run_router(inner_script, 'guide')
        self.assertEqual((native_result.returncode, native_result.stdout, native_result.stderr),
                         (0, native + '\n', ''))
        self.assertEqual(run_router(self.script, 'check').returncode, 0)
        # A mount without its own setting does not inherit the outer true.
        write_fixture(inner, 'wiki/ai-context.json', json.dumps({'topics': {'guide': {
            'description': 'Inner', 'sources': [{'path': 'wiki/guide.md', 'heading': 'Guide'}]}}}))
        self.configure(True)
        result = self.guide(ROW, 'guide', 'kb/guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, '<!-- wiki/guide.md -->\n| Ship it | `docs/run.md` |\n\n'
                         '<!-- modules/kb/wiki/guide.md § Guide -->\n# Guide\n'
                         '| Ship it | [./docs/run.md](../docs/run.md) |\n')

    def test_symlinked_sources_resolve_links_like_check(self):
        # The validator resolves a link beside the configured path, not beside the symlink's target.
        for mount in ('', 'modules/kb'):
            for kind in ('file', 'directory'):
                with self.subTest(mount=mount, kind=kind):
                    base = self.root / mount / kind
                    for name in ('run.md', 'wiki/run.md', 'real/run.md', 'real/sub/run.md'):
                        write_fixture(base, name, 'Run.\n')
                    if kind == 'file':
                        # file/wiki/run.md is the target; file/real/run.md sits beside the physical page.
                        write_fixture(base, 'real/page.md', '[file/wiki/run.md](run.md) [file/real/run.md](run.md)\n')
                        os.symlink('../real/page.md', base / 'wiki/alias.md')
                        source, kept, other = 'wiki/alias.md', 'file/wiki/run.md', 'file/real/run.md'
                    else:
                        # ../run.md leaves the alias lexically: directory/run.md is the target.
                        write_fixture(base, 'real/sub/page.md',
                                      '[directory/run.md](../run.md) [directory/real/run.md](../run.md)\n')
                        os.symlink('real/sub', base / 'alias')
                        source, kept, other = 'alias/page.md', 'directory/run.md', 'directory/real/run.md'
                    config = {'compactPathLinks': True, 'topics': {'guide': {
                        'description': 'Guide', 'sources': [{'path': f'{kind}/{source}'}]}}}
                    link = '../run.md' if kind == 'directory' else 'run.md'
                    expected = f'`{mount + "/" if mount else ""}{kept}` [{other}]({link})\n'
                    if mount:
                        write_fixture(self.root / mount, 'AGENTS.md', '`guide`\n')
                        write_fixture(self.root / mount, 'wiki/README.md', '# Topics\n')
                        write_fixture(self.root / mount, 'wiki/ai-context.json', json.dumps(config))
                        self.cfg['mounts'] = {'kb': {'root': mount}}
                        self.configure(None)
                        result = run_router(self.script, 'kb/guide')
                    else:
                        self.cfg['topics']['guide']['sources'] = config['topics']['guide']['sources']
                        self.configure()
                        result = run_router(self.script, 'guide')
                    self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                    self.assertEqual(result.stdout.split('\n', 1)[1], expected)

    def test_aliased_root_keeps_symlinked_source_directory(self):
        alias = self.root.parent / (self.root.name + '-root-alias')
        os.symlink(self.root, alias)
        self.addCleanup(alias.unlink)
        write_fixture(self.root, 'real/sub/run.md', 'Run.\n')
        write_fixture(self.root, 'real/sub/page.md', '[alias/run.md](run.md) [real/sub/run.md](run.md)\n')
        os.symlink('real/sub', self.root / 'alias')
        source = str(alias / 'alias/page.md')
        self.cfg['topics']['guide']['sources'] = [{'path': source}]
        self.configure()
        result = run_router(self.script, 'guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, f'<!-- {source} -->\n`alias/run.md` [real/sub/run.md](run.md)\n')

    def test_option_must_be_a_boolean(self):
        self.configure('yes')
        write_fixture(self.root, 'wiki/guide.md', ROW)
        result = run_router(self.script, 'check')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, 'FAIL compactPathLinks: expected a boolean\n')
        self.cfg['mounts'] = {'kb': {'root': 'modules/kb'}}
        write_fixture(self.root, 'modules/kb/AGENTS.md', '`guide`\n')
        write_fixture(self.root, 'modules/kb/wiki/ai-context.json', json.dumps(
            {'compactPathLinks': 1, 'topics': {'guide': {'description': 'Inner', 'sources': []}}}))
        self.configure(True)
        result = run_router(self.script, 'kb/guide')
        self.assertEqual(result.returncode, 1)
        self.assertIn('compactPathLinks: expected a boolean', result.stderr)


if __name__ == '__main__':
    unittest.main()
