"""Heading selection recognizes frontmatter boundaries without interpreting YAML."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fixture_helpers import run_router, write_fixture


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / 'scripts/ai-context.py'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('frontmatter_router', SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class FrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir()
        shutil.copy2(SCRIPT, self.script)
        write_fixture(self.root, 'AGENTS.md', '`guide`\n`whole`\n')
        write_fixture(self.root, 'wiki/README.md', '# Topics\n')
        self.cfg = {'topics': {
            'guide': {'description': 'Selected section', 'sources': [
                {'path': 'wiki/guide.md', 'heading': 'Selected', 'frontmatter': True}]},
            'whole': {'description': 'Whole source', 'sources': [
                {'path': 'wiki/guide.md'}]}}}
        write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))

    def write(self, content):
        return write_fixture(self.root, 'wiki/guide.md', content)

    def test_omitted_or_false_option_preserves_legacy_thematic_rules(self):
        content = '---\n# Selected\nBody.\n---\n# End\n'
        self.assertEqual(list(router.headings(content.split('\n'))),
                         [(1, 1, 'Selected'), (4, 1, 'End')])
        self.write(content)
        source = self.cfg['topics']['guide']['sources'][0]
        for value in (None, False):
            with self.subTest(value=value):
                source.pop('frontmatter', None)
                if value is not None:
                    source['frontmatter'] = value
                write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))
                result = run_router(self.script, 'guide')
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertEqual(result.stdout,
                                 '<!-- wiki/guide.md § Selected -->\n# Selected\nBody.\n---\n')

    def test_option_is_a_boolean_for_local_and_mounted_sources(self):
        self.write('# Selected\nBody.\n')
        for value in ('true', 1, None, [], {}):
            with self.subTest(value=value):
                self.cfg['topics']['guide']['sources'][0]['frontmatter'] = value
                write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))
                result = run_router(self.script, 'guide')
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('frontmatter: expected a boolean', result.stderr)
                with self.assertRaisesRegex(ValueError, 'frontmatter: expected a boolean'):
                    router.validate_mounted_cfg(self.cfg, str(self.root))

    def test_frontmatter_comment_cannot_match_or_duplicate_a_body_heading(self):
        for ending in ('---', '...'):
            for body, count in (('# Other\nBody.\n', 0),
                                ('# Selected\nBody.\n', 1),
                                ('# Selected\nBody.\n# Selected\nAgain.\n', 2)):
                with self.subTest(ending=ending, count=count):
                    self.write('---\ntype: Runbook\n# Selected\n' + ending + '\n' + body)
                    result = run_router(self.script, 'guide')
                    if count == 1:
                        self.assertEqual((result.returncode, result.stderr), (0, ''))
                        self.assertEqual(result.stdout,
                                         '<!-- wiki/guide.md § Selected -->\n# Selected\nBody.\n')
                    else:
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(result.stdout, '')
                        self.assertIn("heading 'Selected' found %dx" % count, result.stderr)

    def test_line_indexes_and_fences_start_after_the_envelope(self):
        lines = ['---', '# Selected', '```', '---', '# Selected', 'Body.',
                 '```sh', '# Not a heading', '```', '## Child', 'Child body.', '# End']
        self.assertEqual(list(router.headings(lines, frontmatter=True)),
                         [(4, 1, 'Selected'), (9, 2, 'Child'), (11, 1, 'End')])
        self.write('\n'.join(lines))
        result = run_router(self.script, 'guide')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '<!-- wiki/guide.md § Selected -->\n' +
                         '\n'.join(lines[4:11]) + '\n')

    def test_delimiters_are_column_zero_and_only_at_the_document_start(self):
        for opening in ('---', '\ufeff---', '--- \t'):
            for closing in ('---', '...', '--- \t', '... \t'):
                with self.subTest(opening=opening, closing=closing):
                    lines = [opening, 'description: |', '  ---', '  # Selected',
                             '# Selected', closing, '# Selected', 'Body.']
                    self.assertEqual(list(router.headings(lines, frontmatter=True)), [(6, 1, 'Selected')])
        for prefix in ('\n', '# Intro\n', '```yaml\n'):
            with self.subTest(prefix=prefix):
                text = prefix + '---\n# Selected\n---\n# End\n'
                self.assertEqual(router.frontmatter_end(text.split('\n')), 0)
        for opening in (' ---', '\t---', '----', '--- # comment'):
            with self.subTest(opening=opening):
                self.assertEqual(router.frontmatter_end([opening, '# Selected', '---']), 0)

    def test_unclosed_or_malformed_delimiters_preserve_markdown_behavior(self):
        for suffix in ('', '\n--', '\n ---', '\n--- # comment'):
            with self.subTest(suffix=suffix):
                lines = ('---\n# Selected\nBody.' + suffix).split('\n')
                self.assertEqual(router.frontmatter_end(lines), 0)
                self.assertEqual(list(router.headings(lines, frontmatter=True)), [(1, 1, 'Selected')])
        # This is envelope detection, not a YAML parser or a conformance verdict.
        self.assertEqual(list(router.headings(
            ['---', 'invalid: [', '# Selected', '---', '# Body'], frontmatter=True)), [(4, 1, 'Body')])

    def test_whole_file_render_and_file_contents_are_preserved(self):
        for text in ('---\n# Selected\ntype: Runbook\n---\n# Selected\nBody.\n',
                     '\ufeff---\n# Selected\n...\n# Selected\nBody.\n'):
            with self.subTest(bom=text.startswith('\ufeff')):
                path = self.write(text)
                before = path.read_bytes()
                result = run_router(self.script, 'whole')
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertEqual(result.stdout, '<!-- wiki/guide.md -->\n' + text.strip() + '\n')
                self.assertEqual(path.read_bytes(), before)

    def test_crlf_and_check_share_heading_selection(self):
        path = self.write('')
        path.write_bytes(b'---\r\n# Selected\r\ntype: Runbook\r\n---\r\n# Selected\r\nBody.\r\n')
        result = run_router(self.script, 'check')
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.assertTrue(result.stdout.endswith('ok\n'))
        result = run_router(self.script, 'guide')
        self.assertEqual(result.stdout, '<!-- wiki/guide.md § Selected -->\n# Selected\nBody.\n')

    def test_late_metadata_only_heading_failure_prints_no_partial_content(self):
        self.write('---\n# Selected\ntype: Runbook\n---\n# Other\nBody.\n')
        result = run_router(self.script, 'whole', 'guide')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn("heading 'Selected' found 0x", result.stderr)

    def test_mounted_heading_source_uses_its_own_option(self):
        self.write('# Selected\nOuter body.\n')
        self.cfg['mounts'] = {'kb': {'root': 'modules/kb'}}
        write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))
        inner = {'topics': {'guide': {'description': 'Inner guide', 'sources': [
            {'path': 'wiki/guide.md', 'heading': 'Selected', 'frontmatter': True}]}}}
        write_fixture(self.root, 'modules/kb/wiki/ai-context.json', json.dumps(inner))
        write_fixture(self.root, 'modules/kb/wiki/guide.md',
                      '---\n# Selected\ntype: Runbook\n---\n# Selected\nInner body.\n')
        result = run_router(self.script, 'guide', 'kb/guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout,
                         '<!-- wiki/guide.md § Selected -->\n# Selected\nOuter body.\n\n'
                         '<!-- modules/kb/wiki/guide.md § Selected -->\n# Selected\nInner body.\n')


if __name__ == '__main__':
    unittest.main()
