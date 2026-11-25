"""List falls back to a routed page's closed frontmatter description."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fixture_helpers import run_router, write_fixture

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ai-context.py'
sys.dont_write_bytecode = True


class PageDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir(parents=True)
        shutil.copy2(SCRIPT, self.script)
        write_fixture(self.root, 'AGENTS.md', '`guide`\n')
        write_fixture(self.root, 'wiki/README.md', '# Topics\n')
        self.topic = {'sources': [{'path': 'wiki/guide.md'}]}

    def configure(self):
        write_fixture(self.root, 'wiki/ai-context.json', json.dumps({'topics': {'guide': self.topic}}))

    def assert_list(self, description):
        self.configure()
        result = run_router(self.script, 'list')
        self.assertEqual((result.returncode, result.stderr, result.stdout),
                         (0, '', f'{"guide":18} {description}\n'))

    def test_page_description_and_config_precedence(self):
        write_fixture(self.root, 'wiki/guide.md', '---\ntitle: T\ndescription: How to bisect.\n---\n')
        self.assert_list('How to bisect.')
        for description in ('Configured', ''):
            with self.subTest(description=description):
                self.topic['description'] = description
                self.assert_list(description)

    def test_first_source_with_heading_and_later_source_ignored(self):
        self.topic['sources'][0]['heading'] = 'Section'
        self.topic['sources'].append({'path': 'wiki/second.md'})
        write_fixture(self.root, 'wiki/guide.md', '---\ndescription: First\n---\n# Section\n')
        write_fixture(self.root, 'wiki/second.md', '---\ndescription: Second\n---\n')
        self.assert_list('First')

    def test_malformed_first_source_lists_blank(self):
        write_fixture(self.root, 'wiki/guide.md', '---\ndescription: Later source\n---\n')
        for source in ('wiki/guide.md', {}, {'path': 1}):
            with self.subTest(source=source):
                self.topic['sources'] = [source, {'path': 'wiki/guide.md'}]
                self.assert_list('')

    def test_scalar_forms(self):
        for scalar, expected in [
                ('Value # comment', 'Value'), ('Value#part', 'Value#part'),
                ('-fast recovery.', '-fast recovery.'), ('1.0.0', '1.0.0'), ('Yes', 'Yes'),
                ('~', ''), ('Null', ''), ("'It''s useful' # note", "It's useful"),
                ("'value' junk", ''), (r'"Say \"hi\" café" # note', 'Say "hi" café'),
                (r'"bad\e"', ''), (r'"bad\x41"', ''), (r'"bad\uD800"', ''),
                ('"wrapped', ''), ('|', ''), ('>', ''), ('[a]', ''),
                ('{a: b}', ''), ('&a text', ''), ('- item', ''), ('word: value', ''),
                (r'"a\nb"', ''), (r'"a\u0085b"', ''), (r'"a\tb"', 'a\tb'),
                ('Value\u0085', ''), ('\x0cValue', ''), (r'"line\u2028break"', ''),
                ("'a\u2029b'", ''), ('Value\u2028', ''), ('Value\u00a0', 'Value\u00a0')]:
            with self.subTest(scalar=scalar):
                write_fixture(self.root, 'wiki/guide.md', f'---\ndescription: {scalar}\n---\n')
                self.assert_list(expected)
        write_fixture(self.root, 'wiki/guide.md',
                      '\ufeff---\ndescription:\tUnicode café\n...\n')
        self.assert_list('Unicode café')

    def test_unavailable_descriptions(self):
        for text in ['# No envelope\n', '---\ndescription: unclosed\n',
                     '---\ntitle: T\n---\n', '---\ndescription: \n---\n',
                     '---\n description: indented\n---\n',
                     '---\ndescription: first\n# note\n\n  second\n---\n']:
            with self.subTest(text=text):
                write_fixture(self.root, 'wiki/guide.md', text)
                self.assert_list('')
        (self.root / 'wiki/guide.md').unlink()
        self.assert_list('')
        self.topic['sources'] = []
        self.assert_list('')
        self.topic['sources'] = [{'path': 'wiki/guide.md'}]
        outside = Path(self.tmp.name) / 'outside.md'
        outside.write_text('---\ndescription: secret\n---\n', encoding='utf-8')
        try:
            (self.root / 'wiki/guide.md').symlink_to(outside)
        except (OSError, NotImplementedError) as error:
            self.skipTest('symlink capability unavailable: ' + str(error))
        self.assert_list('')


if __name__ == '__main__':
    unittest.main()
