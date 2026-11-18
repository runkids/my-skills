"""stripFrontmatter drops a closed leading envelope from printed output and budgets."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fixture_helpers import run_router, write_fixture


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ai-context.py'
sys.dont_write_bytecode = True
META = '---\ntype: Runbook\ndescription: metadata\n---\n'


class StripFrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir()
        shutil.copy2(SCRIPT, self.script)
        write_fixture(self.root, 'AGENTS.md', '`guide`\n')
        write_fixture(self.root, 'wiki/README.md', '# Topics\n')
        self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
            {'path': 'wiki/guide.md'}]}}}

    def configure(self, source=None, top=None, **topic):
        if source is not None:
            self.cfg['topics']['guide']['sources'][0].update(source)
        if top is not None:
            self.cfg['stripFrontmatter'] = top
        self.cfg['topics']['guide'].update(topic)
        write_fixture(self.root, 'wiki/ai-context.json', json.dumps(self.cfg))

    def guide(self, text, *args):
        write_fixture(self.root, 'wiki/guide.md', text)
        return run_router(self.script, *(args or ('guide',)))

    def assertOut(self, result, expected):
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, expected)

    def test_default_and_false_keep_the_frontmatter(self):
        for source, top in ((None, None), ({'stripFrontmatter': False}, None), (None, False)):
            with self.subTest(source=source, top=top):
                self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
                    {'path': 'wiki/guide.md'}]}}}
                self.configure(source, top)
                self.assertOut(self.guide(META + '# Title\nBody.\n'),
                               '<!-- wiki/guide.md -->\n' + META + '# Title\nBody.\n')

    def test_source_flag_and_config_default_strip(self):
        for source, top in (({'stripFrontmatter': True}, None), (None, True)):
            with self.subTest(source=source, top=top):
                self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
                    {'path': 'wiki/guide.md'}]}}}
                self.configure(source, top)
                self.assertOut(self.guide(META + '# Title\nBody.\n'),
                               '<!-- wiki/guide.md -->\n# Title\nBody.\n')

    def test_source_flag_overrides_config_default(self):
        self.configure({'stripFrontmatter': False}, True)
        self.assertOut(self.guide(META + 'Body.\n'), '<!-- wiki/guide.md -->\n' + META + 'Body.\n')
        self.cfg['topics']['guide']['sources'][0]['stripFrontmatter'] = True
        self.configure(top=False)
        self.assertOut(self.guide(META + 'Body.\n'), '<!-- wiki/guide.md -->\nBody.\n')

    def test_file_without_frontmatter_is_unchanged(self):
        self.configure(top=True)
        self.assertOut(self.guide('# Title\nBody.\n'), '<!-- wiki/guide.md -->\n# Title\nBody.\n')

    def test_unclosed_block_does_not_swallow_the_file(self):
        self.configure(top=True)
        text = '---\ntype: Runbook\n# Title\nBody.\n'
        self.assertOut(self.guide(text), '<!-- wiki/guide.md -->\n' + text)

    def test_only_the_leading_envelope_is_removed(self):
        self.configure(top=True)
        self.assertOut(self.guide(META + '# Title\n---\nBetween.\n---\nEnd.\n'),
                       '<!-- wiki/guide.md -->\n# Title\n---\nBetween.\n---\nEnd.\n')
        self.assertOut(self.guide('# Title\n' + META + 'Body.\n'),
                       '<!-- wiki/guide.md -->\n# Title\n' + META + 'Body.\n')

    def test_horizontal_rule_first_line_with_later_rule_is_frontmatter_by_design(self):
        # Envelope detection is delimiter-only, so a leading rule closed by a later one is metadata.
        self.configure(top=True)
        self.assertOut(self.guide('---\nIntro.\n---\nBody.\n'), '<!-- wiki/guide.md -->\nBody.\n')

    def test_crlf_bom_and_dots_closer(self):
        self.configure(top=True)
        path = self.root / 'wiki/guide.md'
        write_fixture(self.root, 'wiki/guide.md', '')
        path.write_bytes(b'\xef\xbb\xbf---\r\ntype: Runbook\r\n...\r\n# Title\r\nBody.\r\n')
        result = run_router(self.script, 'guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout.replace('\r\n', '\n'), '<!-- wiki/guide.md -->\n# Title\nBody.\n')
        self.assertNotIn('type:', result.stdout)

    def test_heading_sources_are_unchanged_and_ignore_metadata_headings(self):
        self.configure({'heading': 'Title'})
        text = '---\n# Title\n---\n# Title\nBody.\n'
        # Without the option the metadata comment is a second match, as before.
        result = self.guide(text)
        self.assertEqual(result.returncode, 1)
        self.assertIn("heading 'Title' found 2x", result.stderr)
        self.configure(top=True)
        self.assertOut(self.guide(text), '<!-- wiki/guide.md § Title -->\n# Title\nBody.\n')

    def test_option_must_be_a_boolean(self):
        for source, top, message in (
                ({'stripFrontmatter': 'yes'}, None, 'wiki/guide.md: stripFrontmatter: expected a boolean'),
                (None, 1, 'FAIL stripFrontmatter: expected a boolean')):
            with self.subTest(source=source, top=top):
                self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
                    {'path': 'wiki/guide.md'}]}}}
                self.configure(source, top)
                result = self.guide('Body.\n')
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_bad_config_default_fails_even_when_every_source_sets_its_own(self):
        self.configure({'stripFrontmatter': False}, 'yes')
        write_fixture(self.root, 'wiki/guide.md', 'Body.\n')
        for args, stream in ((('check',), 'stdout'), (('guide',), 'stderr'), (('list',), 'stderr')):
            with self.subTest(args=args):
                result = run_router(self.script, *args)
                self.assertEqual(result.returncode, 1)
                # Reported once as a config key, not against a topic.
                self.assertEqual(getattr(result, stream), 'FAIL stripFrontmatter: expected a boolean\n')

    def test_budget_counts_printed_bytes_and_check_agrees(self):
        body = 'x' * 200 + '\n'
        printed = len(('<!-- wiki/guide.md -->\n' + body.strip()).encode())
        self.configure(top=True, maxBytes=printed)
        result = self.guide(META + body, 'check')
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        # One byte under the printed size fails, so the cap really tracks the stripped output.
        self.configure(maxBytes=printed - 1)
        result = run_router(self.script, 'check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('guide', result.stdout + result.stderr)
        # Without stripping the same cap fails because the envelope counts.
        self.cfg['stripFrontmatter'] = False
        self.configure(maxBytes=printed)
        result = run_router(self.script, 'check')
        self.assertEqual(result.returncode, 1)

    def test_dedupe_still_collapses_identical_sources(self):
        self.cfg['topics']['other'] = {'description': 'Other', 'sources': [{'path': 'wiki/guide.md'}]}
        write_fixture(self.root, 'AGENTS.md', '`guide`\n`other`\n')
        self.configure(top=True)
        write_fixture(self.root, 'wiki/guide.md', META + 'Body.\n')
        result = run_router(self.script, '--dedupe', 'guide', 'other')
        self.assertOut(result, '<!-- wiki/guide.md -->\nBody.\n')


if __name__ == '__main__':
    unittest.main()
