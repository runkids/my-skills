"""OKF reserved wiki pages are exempt from orphan checks only when opted in."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fixture_helpers import run_router, write_fixture


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ai-context.py'
sys.dont_write_bytecode = True
ORPHAN = ': wiki page no topic loads'
HISTORY = ': history file not indexed'
MOUNT = {'kb': {'root': 'modules/kb'}}


class OkfReservedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir()
        shutil.copy2(SCRIPT, self.script)

    def write(self, prefix='', *pages, **cfg):
        cfg['topics'] = {'guide': {'description': 'Guide', 'sources': [{'path': 'wiki/guide.md'}]}}
        files = [('AGENTS.md', '`guide`\n'), ('wiki/README.md', '# Router\n'),
                 ('wiki/guide.md', '# Guide\n'), ('wiki/ai-context.json', json.dumps(cfg))]
        for path, content in files + [(page, '# Page\n') for page in pages]:
            write_fixture(self.root, prefix + path, content)

    def check(self, *pages, **cfg):
        self.write('', *pages, **cfg)
        return run_router(self.script, 'check')

    def test_reserved_pages_in_the_wiki_require_opt_in_and_exact_names(self):
        reserved = ('wiki/index.md', 'wiki/log.md', 'wiki/area/index.md', 'wiki/area/log.md')
        history = ('wiki/history/index.md', 'wiki/history/log.md')
        others = ('wiki/case/Index.md', 'wiki/changelog.md')
        for setting in ({}, {'okfReservedPages': False}, {'okfReservedPages': True}):
            with self.subTest(setting=setting):
                result = self.check(*reserved, *history, *others, **setting)
                exempt = setting.get('okfReservedPages', False)
                self.assertEqual(result.returncode, 1, result.stderr)
                for page in reserved:
                    self.assertEqual(page + ORPHAN in result.stdout, not exempt)
                for page in history:
                    self.assertEqual(page + HISTORY in result.stdout, not exempt)
                for page in others:
                    self.assertIn(page + ORPHAN, result.stdout)

    def test_history_outside_the_wiki_is_still_checked(self):
        result = self.check('archive/index.md', 'archive/log.md', historyDir='archive', okfReservedPages=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('archive/index.md' + HISTORY, result.stdout)
        self.assertIn('archive/log.md' + HISTORY, result.stdout)

    def test_links_in_reserved_pages_are_checked(self):
        write_fixture(self.root, 'wiki/index.md', '# Index\n[Missing](missing.md)\n')
        result = self.check(okfReservedPages=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("wiki/index.md:2: relative link 'missing.md'", result.stdout)
        self.assertNotIn('wiki/index.md' + ORPHAN, result.stdout)

    def test_mounts_use_their_own_setting(self):
        for outer, inner in ((True, False), (False, True)):
            with self.subTest(outer=outer, inner=inner):
                self.write('modules/kb/', 'wiki/index.md', okfReservedPages=inner)
                result = self.check('wiki/index.md', mounts=MOUNT, okfReservedPages=outer)
                self.assertEqual('FAIL wiki/index.md' + ORPHAN in result.stdout, not outer)
                self.assertEqual('FAIL mount kb: wiki/index.md' + ORPHAN in result.stdout, not inner)

    def test_non_boolean_is_rejected(self):
        result = self.check(okfReservedPages='yes')
        self.assertIn('FAIL okfReservedPages: expected a boolean', result.stdout)


if __name__ == '__main__':
    unittest.main()
