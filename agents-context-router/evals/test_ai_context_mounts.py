"""Mounted roots: independent namespaces, guarded reads and atomic requests."""
import copy
from contextlib import nullcontext
import errno
import importlib.util
import io
import json
import ntpath
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / 'scripts/ai-context.py'
sys.dont_write_bytecode = True
from fixture_helpers import run_router, write_fixture


spec = importlib.util.spec_from_file_location('mounted_ai_context', SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class MountFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.root = self.parent / 'project'
        self.module_root = self.root / 'modules/kb-core'
        self.cfg = self.config('Project guide')
        self.cfg['mounts'] = {'kb': {'root': 'modules/kb-core'}}
        self.inner_cfg = self.config('Module guide')
        for prefix, body in [('', 'Local.'), ('modules/kb-core/', 'Module.')]:
            self.write(prefix + 'AGENTS.md', '`guide`\n')
            self.write(prefix + 'wiki/README.md', '# Router\n')
            self.write(prefix + 'wiki/guide.md', '# Guide\n' + body + '\n')
        self.save_configs()

    @staticmethod
    def config(description):
        return {'topics': {'guide': {'description': description,
                                    'sources': [{'path': 'wiki/guide.md'}]}}}

    def write(self, relative, text):
        return write_fixture(self.root, relative, text)

    def save_configs(self):
        self.write('wiki/ai-context.json', json.dumps(self.cfg, ensure_ascii=False))
        self.write(str(self.module_root / 'wiki/ai-context.json'),
                   json.dumps(self.inner_cfg, ensure_ascii=False))

    def cli(self, *args, root=None, config=None, cwd=None):
        overrides = {'AI_CONTEXT_ROOT': str(self.root if root is None else root),
                     'AI_CONTEXT_CONFIG': str(self.root / 'wiki/ai-context.json'
                                              if config is None else config)}
        return run_router(SCRIPT, *args, overrides=overrides, cwd=cwd)

    def call_main(self, *args):
        # Real main with reconfigurable streams; injected I/O faults cannot
        # cross a subprocess boundary. Preserve globals and parent streams.
        output, errors = io.BytesIO(), io.BytesIO()
        stdout = io.TextIOWrapper(output, encoding='utf-8', newline='\n')
        stderr = io.TextIOWrapper(errors, encoding='utf-8', newline='\n')
        try:
            with patch.object(router, 'ROOT', str(self.root)), \
                    patch.object(router, 'CFG_PATH', str(self.root / 'wiki/ai-context.json')), \
                    patch.object(sys, 'stdout', stdout), patch.object(sys, 'stderr', stderr):
                try:
                    code = router.main(['ai-context.py', *args])
                except SystemExit as error:
                    code = error.code if isinstance(error.code, int) else 1
                    if not isinstance(error.code, int):
                        print(error.code, file=stderr)
            stdout.flush()
            stderr.flush()
            return code, output.getvalue().decode('utf-8'), errors.getvalue().decode('utf-8')
        finally:
            stdout.close()
            stderr.close()

    def sibling(self):
        self.cfg['mounts']['other'] = {'root': 'modules/other'}
        for path, text in [('AGENTS.md', '`guide`\n'), ('wiki/README.md', '# Router\n'),
                           ('wiki/guide.md', '# Guide\nOther.\n'),
                           ('wiki/ai-context.json', json.dumps(self.config('Other guide')))]:
            self.write('modules/other/' + path, text)
        self.save_configs()

    def symlink(self, path, target, directory=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest('symlink capability unavailable: ' + str(error))

    def assert_failure(self, result, *details):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        for detail in details:
            self.assertIn(detail, result.stdout + result.stderr)


class MountRoutingTests(MountFixture):
    def test_list_and_mixed_render(self):
        # Dropping mounts or using the outer cfg/body must fail these literals.
        local = '<!-- wiki/guide.md -->\n# Guide\nLocal.'
        mounted = '<!-- modules/kb-core/wiki/guide.md -->\n# Guide\nModule.'
        rows = self.cli('list')
        self.assertEqual((rows.returncode, rows.stderr), (0, ''))
        self.assertEqual(rows.stdout.splitlines(), [f'{"guide":18} Project guide',
                         f'{"kb/guide":18} Module guide [modules/kb-core]'])
        for names, bodies in [(('guide',), [local]), (('kb/guide',), [mounted]),
                              (('guide', 'kb/guide'), [local, mounted]),
                              (('kb/guide', 'guide', 'kb/guide'), [mounted, local, mounted])]:
            with self.subTest(names=names):
                result = self.cli(*names)
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertEqual(result.stdout, '\n\n'.join(bodies) + '\n')
        self.inner_cfg['topics']['指南'] = {'description': '操作說明', 'sources': [
            {'path': 'wiki/中文.md', 'heading': '選擇'}]}
        self.write('modules/kb-core/wiki/中文.md', '# 首頁\n## 選擇\n內容。\n## 其他\n省略。\n')
        self.cfg['mounts']['知識'] = self.cfg['mounts']['kb']
        self.save_configs()
        result = self.cli('知識/指南')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, '<!-- modules/kb-core/wiki/中文.md § 選擇 -->\n## 選擇\n內容。\n')
        self.assertIn(f'{"知識/指南":18} 操作說明 [modules/kb-core]', self.cli('list').stdout)

    def test_namespace_dispatch(self):
        self.cfg['topics']['kb'] = copy.deepcopy(self.cfg['topics']['guide'])
        self.inner_cfg['topics']['ops/guide'] = copy.deepcopy(self.inner_cfg['topics']['guide'])
        self.cfg['mounts']['list'] = {'root': 'modules/kb-core'}
        self.cfg['mounts']['check'] = {'root': 'modules/kb-core'}
        self.save_configs()
        for name, body in [('kb', 'Local.'), ('kb/ops/guide', 'Module.'),
                           ('list/guide', 'Module.'), ('check/guide', 'Module.')]:
            with self.subTest(name=name):
                result = self.cli(name)
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertIn(body, result.stdout)
        for name in ['absent', 'kb/absent']:
            result = self.cli(name)
            self.assertEqual((result.returncode, result.stdout), (1, ''))
            self.assertIn(f'unknown topic {name!r}; rerun this script with list', result.stderr)

    def test_paths_and_overrides(self):
        external = self.parent / 'outer.json'
        nested = self.root / 'one/two/three'
        nested.mkdir(parents=True)
        for root_path, config_path, source in [
                ('modules/kb-core', None, 'wiki/guide.md'),
                (str(self.module_root), str(self.module_root / 'wiki/ai-context.json'),
                 str(self.module_root / 'wiki/guide.md')),
                ('modules\\kb-core', 'context\\router.json', 'wiki\\guide.md')]:
            with self.subTest(root=root_path, config=config_path):
                self.cfg['mounts']['kb'] = {'root': root_path}
                if config_path is not None:
                    self.cfg['mounts']['kb']['config'] = config_path
                self.inner_cfg['topics']['guide']['sources'][0]['path'] = source
                self.save_configs()
                if config_path == 'context\\router.json':
                    self.write('modules/kb-core/context/router.json', json.dumps(self.inner_cfg))
                external.write_text(json.dumps(self.cfg), encoding='utf-8')
                for cwd in [self.root, nested]:
                    for outer_config in [self.root / 'wiki/ai-context.json', external]:
                        result = self.cli('kb/guide', config=outer_config, cwd=cwd)
                        self.assertEqual((result.returncode, result.stderr), (0, ''))
                        self.assertEqual(result.stdout, '<!-- modules/kb-core/wiki/guide.md -->\n# Guide\nModule.\n')
                result = self.cli('kb/guide', root='../../..',
                                  config=os.path.relpath(external, nested), cwd=nested)
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertIn('Module.', result.stdout)
        # The copied executable's default root stays independent of cwd.
        self.cfg['mounts']['kb'] = {'root': 'modules/kb-core'}
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'wiki/guide.md'
        self.save_configs()
        script = self.root / 'scripts/ai-context.py'
        script.parent.mkdir()
        shutil.copyfile(SCRIPT, script)
        result = run_router(script, 'kb/guide', cwd=nested)
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertIn('Module.', result.stdout)
        for literal in ['~', '$MOUNT_ROOT']:
            target = self.root / literal
            shutil.copytree(self.module_root, target)
            self.cfg['mounts']['kb'] = {'root': literal}
            self.save_configs()
            result = self.cli('kb/guide')
            self.assertEqual((result.returncode, result.stderr), (0, ''))
            self.assertIn(f'<!-- {literal}/wiki/guide.md -->', result.stdout)

    def test_explicit_root_keeps_globals(self):
        original = router.ROOT, router.CFG_PATH
        for owner, cfg, expected in [(self.root, self.cfg, 'Local.'),
                                      (self.module_root, self.inner_cfg, 'Module.'),
                                      (self.root, self.cfg, 'Local.')]:
            self.assertEqual(router.section({'path': 'wiki/guide.md'}, root=str(owner)),
                             '# Guide\n' + expected)
            self.assertEqual(router.render(cfg, 'guide', root=str(owner)),
                             '<!-- wiki/guide.md -->\n# Guide\n' + expected)
            self.assertEqual((router.ROOT, router.CFG_PATH), original)
        with patch.object(router, 'ROOT', str(self.root)):
            self.assertEqual(router.section({'path': 'wiki/guide.md'}), '# Guide\nLocal.')

    def test_failure_matrix(self):
        missing = self.root / 'modules/missing'
        self.cfg['mounts']['kb']['root'] = str(missing)
        self.save_configs()
        result = self.cli('list')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, f'{"guide":18} Project guide\nNOTICE mount kb: missing root {missing}\n')
        self.assertEqual(self.cli('guide').stderr, '')
        self.assertEqual((self.cli('kb/guide').returncode, self.cli('kb/guide').stdout), (1, ''))
        for control in ['\n', '\r', '\x85']:
            self.cfg['mounts']['kb']['root'] = 'missing' + control + 'root'
            self.save_configs()
            result = self.cli('list')
            if os.name == 'nt' and control in ('\n', '\r'):
                # Windows rejects these filenames before a missing-root stat.
                self.assert_failure(result, 'mount kb:', 'root')
                self.assertIn('\\x' + format(ord(control), '02x'), result.stderr)
                self.assertEqual(len(result.stderr.splitlines()), 1)
            else:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(result.stdout.splitlines()), 2)
                self.assertIn('NOTICE mount kb: missing root ', result.stdout)
            # The notice-formatting contract also runs where the native FS
            # cannot represent that name; only the load result is synthetic.
            failure = router.MissingMount('missing root missing' + control + 'root')
            with patch.object(router, 'load_mount', side_effect=failure) as loader:
                code, out, err = self.call_main('list')
            self.assertEqual(loader.call_count, 1)
            self.assertEqual((code, err), (0, ''))
            self.assertEqual(out.splitlines(), [f'{"guide":18} Project guide',
                             'NOTICE mount kb: missing root missing\\x' + format(ord(control), '02x') + 'root'])
        self.cfg['mounts']['kb']['root'] = 'modules/kb-core'
        self.sibling()
        config_path = self.module_root / 'wiki/ai-context.json'
        for content, category in [(b'{', 'JSON'), (b'\xff', 'UTF-8'),
                                   (b'{"topics": {}, "mounts": {"nested": {"root": "no"}}}', 'nested')]:
            with self.subTest(category=category):
                config_path.write_bytes(content)
                self.assert_failure(self.cli('list'), 'mount kb:', category)
                self.assertIn('other/guide', self.cli('list').stdout)
                self.assertEqual(self.cli('guide').stderr, '')
                self.assertEqual(self.cli('other/guide').stderr, '')
        self.save_configs()
        config_path.unlink()
        self.assert_failure(self.cli('list'), 'mount kb:', 'config', str(config_path))
        config_path.mkdir()
        self.assert_failure(self.cli('list'), 'mount kb:', 'config')
        config_path.rmdir()
        self.save_configs()
        root_file = self.write('modules/file', 'not a directory')
        self.cfg['mounts']['kb']['root'] = str(root_file)
        self.save_configs()
        self.assert_failure(self.cli('list'), 'mount kb:', 'root', 'directory')
        self.cfg['mounts']['kb']['root'] = 'modules/kb-core'
        self.save_configs()
        real_stat, real_open = os.stat, open
        reached = []
        def denied_stat(path, *args, **kwargs):
            if os.path.abspath(path) == str(self.module_root):
                reached.append('root')
                raise PermissionError('denied root')
            return real_stat(path, *args, **kwargs)
        with patch.object(router.os, 'stat', side_effect=denied_stat):
            code, out, err = self.call_main('list')
        self.assertEqual(code, 1, out + err)
        self.assertIn('mount kb:', err)
        self.assertIn('denied root', err)
        self.assertNotIn('NOTICE', out)
        self.assertIn('root', reached)
        def denied_open(path, *args, **kwargs):
            if os.path.abspath(path) == str(config_path):
                reached.append('config')
                raise PermissionError('denied config')
            return real_open(path, *args, **kwargs)
        with patch('builtins.open', side_effect=denied_open):
            code, out, err = self.call_main('list')
        self.assertEqual(code, 1, out + err)
        self.assertIn('mount kb:', err)
        self.assertIn('denied config', err)
        self.assertIn('other/guide', out)
        self.assertIn('config', reached)

    def test_combined_render_is_atomic(self):
        original = copy.deepcopy(self.inner_cfg)
        for kind in ['unknown', 'inner-unknown', 'missing-mount', 'missing-source',
                     'bad-utf8', 'missing-heading', 'duplicate-heading', 'denied-source']:
            with self.subTest(kind=kind):
                self.inner_cfg = copy.deepcopy(original)
                self.cfg['mounts']['kb']['root'] = 'modules/kb-core'
                source = self.write('modules/kb-core/wiki/guide.md', '# Guide\nModule.\n')
                name = 'kb/guide'
                if kind == 'unknown':
                    name = 'unknown'
                elif kind == 'inner-unknown':
                    name = 'kb/unknown'
                elif kind == 'missing-mount':
                    self.cfg['mounts']['kb']['root'] = 'modules/missing'
                elif kind == 'missing-source':
                    source.unlink()
                elif kind == 'bad-utf8':
                    source.write_bytes(b'\xff')
                elif kind in ('missing-heading', 'duplicate-heading'):
                    self.inner_cfg['topics']['guide']['sources'][0]['heading'] = 'Selected'
                    if kind == 'duplicate-heading':
                        source.write_text('# Selected\nOne\n# Selected\nTwo\n', encoding='utf-8')
                self.save_configs()
                real_open = open
                reached = []
                def selected_open(path, *args, **kwargs):
                    if kind == 'denied-source' and os.path.abspath(path) == str(source):
                        reached.append(str(path))
                        raise PermissionError('denied source')
                    return real_open(path, *args, **kwargs)
                for requests in [('guide', name), (name, 'guide')]:
                    reached.clear()
                    with patch('builtins.open', side_effect=selected_open):
                        code, out, err = self.call_main(*requests)
                    self.assertEqual((code, out), (1, ''), err)
                    self.assertIn(name, err)
                    self.assertNotIn('Traceback', err)
                    if kind == 'denied-source':
                        self.assertTrue(reached, requests)
                        self.assertIn('denied source', err)


class MountDeclarationTests(MountFixture):
    def test_fields_and_namespace(self):
        for value in [None, [], 'kb', 7]:
            with self.subTest(mounts=value):
                self.cfg['mounts'] = value
                self.save_configs()
                for args in [('list',), ('guide',), ('check',)]:
                    result = self.cli(*args)
                    self.assert_failure(result, 'mounts')
                    if args == ('guide',):
                        self.assertEqual(result.stdout, '')
        cases = [(None, 'declaration'), ([], 'declaration'), ('root', 'declaration'),
                 ({}, 'root'), ({'root': ''}, 'root'), ({'root': 1}, 'root'),
                 ({'root': None}, 'root'), ({'root': 'bad\x00path'}, 'root'),
                 ({'root': 'modules/kb-core', 'config': ''}, 'config'),
                 ({'root': 'modules/kb-core', 'config': 1}, 'config'),
                 ({'root': 'modules/kb-core', 'config': None}, 'config'),
                 ({'root': 'modules/kb-core', 'config': 'bad\x00path'}, 'config'),
                 ({'root': 'modules/kb-core', 'typo': True}, 'typo')]
        for declaration, field in cases:
            with self.subTest(declaration=declaration):
                self.cfg['mounts'] = {'kb': declaration}
                self.sibling()
                result = self.cli('list')
                self.assert_failure(result, 'mount kb:', field)
                self.assertIn('other/guide', result.stdout)
                self.assertEqual(self.cli('guide').returncode, 0)
                self.assertEqual((self.cli('kb/guide').returncode, self.cli('kb/guide').stdout), (1, ''))
        for name in ['', '.', '..', 'a/b', 'a\\b', 'a b', 'a\u3000b', 'a\n', 'a\x00', 'a\x7f', 'a\x85']:
            with self.subTest(name=repr(name)):
                self.cfg['mounts'] = {name: {'root': 'modules/kb-core'}}
                self.sibling()
                result = self.cli('list')
                self.assert_failure(result, 'name')
                self.assertIn('other/guide', result.stdout)
        for name in ['kb-core', '知識']:
            self.cfg['mounts'] = {name: {'root': 'modules/kb-core'}}
            self.save_configs()
            self.assertEqual(self.cli(name + '/guide').returncode, 0)
        self.cfg['topics']['kb/guide'] = copy.deepcopy(self.cfg['topics']['guide'])
        for root in ['modules/kb-core', 'modules/missing']:
            self.cfg['mounts'] = {'kb': {'root': root}}
            self.save_configs()
            result = self.cli('list')
            self.assert_failure(result, 'mount kb:', 'collision')
            self.assertNotIn(f'{"kb/guide":18} Project guide', result.stdout)
            failed = self.cli('kb/guide')
            self.assertEqual((failed.returncode, failed.stdout), (1, ''))
            self.assertEqual(self.cli('guide').returncode, 0)
        for mounts in [None, {}]:
            if mounts is None:
                self.cfg.pop('mounts', None)
            else:
                self.cfg['mounts'] = mounts
            self.save_configs()
            self.assertIn('Local.', self.cli('kb/guide').stdout)

    def test_mounted_schema(self):
        original = copy.deepcopy(self.inner_cfg)
        entry = router.mount_entries(self.cfg, root=str(self.root))[0]
        # Field validation belongs to the real loader. CLI attribution and
        # healthy-root continuation have separate list/check handoff cases.
        cases = [(None, 'config'), ([], 'config'), ({}, 'topics'),
                 ({'topics': []}, 'topics'), ({'topics': {'': {}}}, 'topics')]
        for field, value in [('description', 1), ('sources', {}), ('sources', [None]),
                             ('sources', [{'path': ''}]), ('sources', [{'path': 1}]),
                             ('sources', [{}]), ('sources', [{'path': 'wiki/guide.md', 'heading': 1}])]:
            cfg = copy.deepcopy(original)
            cfg['topics']['guide'][field] = value
            cases.append((cfg, field if field == 'description' else 'sources'))
        cfg = copy.deepcopy(original)
        cfg['topics']['guide'] = []
        cases.append((cfg, 'guide'))
        for key, value in [('budgets', []), ('indexed', 'wiki/*'), ('indexed', [1]),
                           ('skipDirs', {}), ('skipDirs', [1]), ('unrouted', []),
                           ('mounts', None), ('mounts', []),
                           ('mounts', {'inner': {'root': '/must-not-follow'}})]:
            cfg = copy.deepcopy(original)
            cfg[key] = value
            cases.append((cfg, 'nested' if key == 'mounts' and isinstance(value, dict) else key))
        for key in ['rootInstructions', 'wikiDir', 'historyDir', 'routerFile']:
            for value in ['', 1, None, 'bad\x00path']:
                cfg = copy.deepcopy(original)
                cfg[key] = value
                cases.append((cfg, key))
        for value in [-1, True, '10']:
            for key in ['rootInstructionsMaxBytes', 'defaultTopicMaxBytes']:
                cfg = copy.deepcopy(original)
                cfg['budgets'] = {key: value}
                cases.append((cfg, key))
            cfg = copy.deepcopy(original)
            cfg['topics']['guide']['maxBytes'] = value
            cases.append((cfg, 'maxBytes'))
        config_path = self.module_root / 'wiki/ai-context.json'
        for cfg, field in cases:
            with self.subTest(field=field, cfg=cfg):
                config_path.write_text(json.dumps(cfg), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, field):
                    router.load_mount(entry)
        for cfg in [{'topics': {}}, {'topics': {'empty': {'description': '', 'sources': []}}},
                    dict(original, budgets={'rootInstructionsMaxBytes': 0, 'defaultTopicMaxBytes': 0},
                         unrouted={'anything': None}, mounts={}, future={'accepted': True})]:
            config_path.write_text(json.dumps(cfg), encoding='utf-8')
            with self.subTest(accepted=cfg):
                self.assertEqual(router.load_mount(entry), cfg)


class MountOwnershipRegressionTests(MountFixture):
    def test_mount_cannot_contain_outer_wiki(self):
        # The inner wiki differs from the outer one: without rejection the
        # outer orphan would silently disappear from both inventories.
        shutil.rmtree(self.root / 'modules')
        (self.root / 'docs').mkdir()
        (self.root / 'wiki').rename(self.root / 'docs/wiki')
        self.cfg['wikiDir'] = 'docs/wiki'
        self.cfg['topics']['guide']['sources'][0]['path'] = 'docs/wiki/guide.md'
        self.cfg['mounts'] = {'kb': {'root': 'docs', 'config': 'kbwiki/ai-context.json'}}
        self.inner_cfg['wikiDir'] = 'kbwiki'
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'kbwiki/guide.md'
        for path, text in [('AGENTS.md', '`guide`\n'), ('kbwiki/README.md', '# Router\n'),
                           ('kbwiki/guide.md', '# Module\n'),
                           ('kbwiki/ai-context.json', json.dumps(self.inner_cfg))]:
            self.write('docs/' + path, text)
        self.write('docs/wiki/orphan.md', '# Orphan\n')
        self.write('wiki/ai-context.json', json.dumps(self.cfg))
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer wikiDir')
        self.assert_failure(self.cli('list'), 'mount kb:', 'contains outer wikiDir')
        self.assert_failure(self.cli('kb/guide'), 'contains outer wikiDir')
        self.cfg.pop('mounts')
        self.write('wiki/ai-context.json', json.dumps(self.cfg))
        self.assert_failure(self.cli('check'), 'docs/wiki/orphan.md: wiki page no topic loads')

    def test_mount_cannot_contain_outer_history(self):
        self.write('modules/kb-core/logs/unindexed.md', '# Unindexed\n')
        for history in ['modules/kb-core/logs', 'modules/kb-core']:
            with self.subTest(historyDir=history):
                self.cfg['historyDir'] = history
                self.save_configs()
                self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer historyDir')
        self.symlink(self.root / 'history-alias', self.module_root / 'logs', directory=True)
        self.cfg['historyDir'] = 'history-alias'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer historyDir')

    def test_mount_cannot_replace_default_outer_history(self):
        target = self.root / 'wiki/history'
        self.module_root.rename(target)
        self.module_root = target
        self.cfg['mounts']['kb']['root'] = 'wiki/history'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer historyDir')
        # A module below that history tree still owns only its own subtree.
        target.rename(self.root / 'modules/kb-core')
        target.mkdir()
        (self.root / 'modules/kb-core').rename(target / 'module')
        self.module_root = target / 'module'
        self.cfg['mounts']['kb']['root'] = 'wiki/history/module'
        self.save_configs()
        result = self.cli('check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mount_cannot_equal_outer_wiki(self):
        self.cfg['wikiDir'] = 'modules/kb-core'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer wikiDir')

    def test_mount_cannot_contain_selected_outer_config(self):
        selected = self.write('modules/kb-core/outer.json', json.dumps(self.cfg))
        for command in ['list', 'check', 'kb/guide']:
            with self.subTest(command=command):
                self.assert_failure(self.cli(command, config=selected),
                                    'contains outer config')

    def test_mount_cannot_contain_outer_instructions(self):
        self.cfg['rootInstructions'] = 'modules/kb-core/AGENTS.md'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer rootInstructions')
        # A lexical path outside the mount still belongs to it physically.
        self.symlink(self.root / 'instructions.md', self.module_root / 'AGENTS.md')
        self.cfg['rootInstructions'] = 'instructions.md'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'mount kb:', 'contains outer rootInstructions')

    def test_ancestor_mounts_rejected_in_either_order(self):
        for path, text in [('AGENTS.md', '`guide`\n'), ('wiki/README.md', '# Router\n'),
                           ('wiki/guide.md', '# Parent\n'),
                           ('wiki/ai-context.json', json.dumps(self.config('Parent guide')))]:
            self.write('modules/' + path, text)
        declarations = [('a', {'root': 'modules'}), ('kb', {'root': 'modules/kb-core'})]
        for pairs in [declarations, list(reversed(declarations))]:
            with self.subTest(order=[name for name, _ in pairs]):
                self.cfg['mounts'] = dict(pairs)
                self.save_configs()
                result = self.cli('check')
                self.assert_failure(
                    result,
                    'mount a: root modules: strict ancestor/descendant overlap with mount kb (modules/kb-core)',
                    'mount kb: root modules/kb-core: strict ancestor/descendant overlap with mount a (modules)')
                self.assertNotIn('scoped instructions no topic loads', result.stdout)
                self.assert_failure(self.cli('list'), 'ancestor/descendant overlap')
                self.assert_failure(self.cli('kb/guide'), 'ancestor/descendant overlap')
        self.symlink(self.root / 'parent-alias', self.root / 'modules', directory=True)
        self.cfg['mounts']['a']['root'] = 'parent-alias'
        self.save_configs()
        self.assert_failure(self.cli('check'), 'ancestor/descendant overlap')

    def test_case_alias_mount_owns_its_tree(self):
        alias = self.root / 'Modules/KB-Core'
        if not alias.exists():
            self.skipTest('requires a case-insensitive filesystem')
        self.cfg['mounts']['kb']['root'] = 'Modules/KB-Core'
        self.save_configs()
        for command in ['list', 'check', 'kb/guide']:
            with self.subTest(command=command):
                result = self.cli(command)
                self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.cfg['mounts']['same'] = {'root': 'modules/kb-core'}
        self.save_configs()
        result = self.cli('check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('same/guide', result.stdout)
        self.write('modules/kb-core-neighbor/AGENTS.md', '# Unowned\n')
        self.assert_failure(self.cli('check'), 'modules/kb-core-neighbor/AGENTS.md: scoped instructions')

    def test_case_alias_absolute_inventory_paths(self):
        if not (self.root / 'Modules/KB-Core').exists():
            self.skipTest('requires a case-insensitive filesystem')
        self.cfg['mounts']['kb']['root'] = 'Modules/KB-Core'
        original = copy.deepcopy(self.inner_cfg)
        for field in ['source', 'wikiDir', 'rootInstructions', 'routerFile']:
            with self.subTest(field=field):
                self.inner_cfg = copy.deepcopy(original)
                if field == 'source':
                    self.inner_cfg['topics']['guide']['sources'][0]['path'] = str(self.module_root / 'wiki/guide.md')
                else:
                    relative = {'wikiDir': 'wiki', 'rootInstructions': 'AGENTS.md',
                                'routerFile': 'wiki/README.md'}[field]
                    self.inner_cfg[field] = str(self.module_root / relative)
                self.save_configs()
                result = self.cli('check')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                orphan = self.write('modules/kb-core/wiki/orphan.md', '# Orphan\n')
                try:
                    self.assert_failure(self.cli('check'), 'FAIL mount kb: wiki/orphan.md: wiki page no topic loads')
                finally:
                    orphan.unlink()

    def test_sibling_history_alias_keeps_lexical_index(self):
        self.inner_cfg['wikiDir'] = 'docs/wiki'
        self.inner_cfg['historyDir'] = str(self.module_root / 'docs/archive')
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'docs/wiki/guide.md'
        self.write('modules/kb-core/docs/wiki/guide.md', '# Guide\n')
        self.write('modules/kb-core/docs/logs/log.md', '# Log\n')
        self.symlink(self.module_root / 'docs/archive', self.module_root / 'docs/logs', directory=True)
        roots = ['modules/kb-core']
        if (self.root / 'Modules/KB-Core').exists():
            roots.append('Modules/KB-Core')
        for spelling in roots:
            with self.subTest(root=spelling):
                self.cfg['mounts']['kb']['root'] = spelling
                self.write('modules/kb-core/docs/wiki/README.md', '# Router\n[Log](../archive/log.md)\n')
                self.save_configs()
                result = self.cli('check')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.write('modules/kb-core/docs/wiki/README.md', '# Router\n')
                self.assert_failure(self.cli('check'), 'FAIL mount kb: docs/logs/log.md: history file not indexed')

    def test_distinct_case_sensitive_roots_keep_separate_ownership(self):
        other = self.root / 'modules/KB-CORE'
        if other.exists():
            self.skipTest('requires a case-sensitive filesystem')
        for path, text in [('AGENTS.md', '`guide`\n'), ('wiki/README.md', '# Router\n'),
                           ('wiki/guide.md', '# Other\n'),
                           ('wiki/ai-context.json', json.dumps(self.config('Other guide')))]:
            self.write('modules/KB-CORE/' + path, text)
        self.cfg['mounts']['other'] = {'root': 'modules/KB-CORE'}
        self.save_configs()
        result = self.cli('check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write('modules/KB-CORE/wiki/orphan.md', '# Orphan\n')
        self.assert_failure(self.cli('check'), 'FAIL mount other: wiki/orphan.md: wiki page no topic loads')

    def test_inner_heading_failures_through_check(self):
        self.sibling()
        self.inner_cfg['topics']['guide']['sources'][0]['heading'] = 'Selected'
        for body, count in [('# Guide\n', 0),
                            ('# Guide\n## Selected\nFirst.\n## Selected\nSecond.\n', 2)]:
            with self.subTest(matches=count):
                self.write('modules/kb-core/wiki/guide.md', body)
                self.save_configs()
                result = self.cli('check')
                self.assert_failure(result, "FAIL mount kb: guide: wiki/guide.md: heading 'Selected' found " + str(count) + 'x')
                self.assertIn('other/guide', result.stdout)
                self.assertTrue(result.stdout.endswith('1 root(s) failed\n'), result.stdout)


class MountBoundaryTests(MountFixture):
    def test_root_and_config_boundaries(self):
        outside = self.parent / 'outside'
        outside.mkdir()
        (outside / 'secret.json').write_text('{"topics": {}}', encoding='utf-8')
        sibling = self.parent / 'project-neighbor'
        sibling.mkdir()
        real_open, real_scan = open, os.scandir
        forbidden = []
        def guarded_root_open(candidate, *args, **kwargs):
            canonical = os.path.realpath(candidate)
            if canonical == str(outside) or canonical.startswith(str(outside) + os.sep):
                forbidden.append(canonical)
                raise AssertionError('outside root opened')
            return real_open(candidate, *args, **kwargs)
        def guarded_root_scan(candidate):
            canonical = os.path.realpath(candidate)
            if canonical == str(outside) or canonical.startswith(str(outside) + os.sep):
                forbidden.append(canonical)
                raise AssertionError('outside root scanned')
            return real_scan(candidate)
        for path in ['.', str(self.root), '../outside', str(outside), str(sibling), '../absent']:
            with self.subTest(root=path):
                self.cfg['mounts']['kb'] = {'root': path}
                self.save_configs()
                result = self.cli('list')
                self.assert_failure(result, 'mount kb:', 'root')
                self.assertNotIn('NOTICE', result.stdout)
                with patch('builtins.open', side_effect=guarded_root_open), \
                        patch.object(router.os, 'scandir', side_effect=guarded_root_scan):
                    code, out, err = self.call_main('list')
                self.assertEqual(code, 1, out + err)
                self.assertIn('mount kb:', err)
                self.assertEqual(forbidden, [])
        self.cfg['mounts']['kb'] = {'root': 'modules/kb-core'}
        for path in ['../../wiki/ai-context.json', str(outside / 'secret.json'),
                     str(self.root / 'wiki/ai-context.json')]:
            with self.subTest(config=path):
                self.cfg['mounts']['kb']['config'] = path
                self.save_configs()
                real_open, real_scan = open, os.scandir
                forbidden = []
                def guarded_open(candidate, *args, **kwargs):
                    canonical = os.path.realpath(candidate)
                    if canonical == str(outside / 'secret.json'):
                        forbidden.append(canonical)
                        raise AssertionError('outside config opened')
                    return real_open(candidate, *args, **kwargs)
                def guarded_scan(candidate):
                    if os.path.realpath(candidate) == str(outside):
                        forbidden.append(str(candidate))
                        raise AssertionError('outside directory scanned')
                    return real_scan(candidate)
                with patch('builtins.open', side_effect=guarded_open), \
                        patch.object(router.os, 'scandir', side_effect=guarded_scan):
                    code, out, err = self.call_main('list')
                self.assertEqual(code, 1, out + err)
                self.assertIn('mount kb:', err)
                self.assertIn('config', err)
                self.assertEqual(forbidden, [])
        self.cfg['mounts']['kb'] = {'root': 'modules/kb-core'}
        aliases = [('modules/back', self.root), ('modules/escape', outside),
                   ('modules/dangling-outside', outside / 'missing'),
                   ('modules/dangling-inside', self.root / 'missing'),
                   ('modules/alias', self.module_root)]
        for name, target in aliases:
            self.symlink(self.root / name, target, directory=True)
            self.cfg['mounts']['kb'] = {'root': name}
            self.save_configs()
            result = self.cli('list')
            if name.endswith('dangling-inside'):
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('NOTICE mount kb: missing root ', result.stdout)
            elif name.endswith('/alias'):
                self.assertEqual((result.returncode, result.stderr), (0, ''))
                self.assertIn('kb/guide', result.stdout)
            else:
                self.assert_failure(result, 'mount kb:', 'root')
                self.assertNotIn('NOTICE', result.stdout)
        self.cfg['mounts'] = {'kb': {'root': 'modules/kb-core'},
                              'same': {'root': 'modules/alias'}}
        self.save_configs()
        self.assertEqual(self.cli('same/guide').returncode, 0)
        config_alias = self.module_root / 'context.json'
        self.symlink(config_alias, self.module_root / 'wiki/ai-context.json')
        self.cfg['mounts']['kb']['config'] = 'context.json'
        self.save_configs()
        self.assertEqual(self.cli('kb/guide').returncode, 0)
        config_alias.unlink()
        self.symlink(config_alias, outside / 'secret.json')
        self.assert_failure(self.cli('list'), 'mount kb:', 'config')
        # Ancestor symlinks must not make a textually contained root safe.
        self.cfg['mounts']['kb'] = {'root': 'modules/escape/child'}
        self.save_configs()
        self.assert_failure(self.cli('list'), 'mount kb:', 'root')

    def test_physical_comparison_and_config_recheck(self):
        # No filesystem anchor is ever walked by this helper-only assertion.
        anchor = Path(self.root.anchor)
        self.assertTrue(router.inside_root(str(self.root), str(anchor)))
        self.assertFalse(router.inside_root(str(anchor), str(anchor)))
        self.assertTrue(router.inside_root(str(anchor), str(anchor), allow_root=True))
        self.assertFalse(router.inside_root(str(self.parent / 'project-sibling'), str(self.root)))
        if os.name == 'nt':
            self.assertFalse(router.inside_root('Z:\\outside', 'C:\\owner'))
        entry = router.mount_entries(self.cfg, root=str(self.root))[0]
        outside = self.parent / 'changed.json'
        outside.write_text('{"topics": {}}', encoding='utf-8')
        config = self.module_root / 'wiki/ai-context.json'
        config.unlink()
        self.symlink(config, outside)
        real_open = open
        opened = []
        def guarded_open(path, *args, **kwargs):
            if os.path.realpath(path) == str(outside):
                opened.append(str(path))
                raise AssertionError('changed config opened outside owner')
            return real_open(path, *args, **kwargs)
        with patch('builtins.open', side_effect=guarded_open):
            with self.assertRaisesRegex(ValueError, 'config'):
                router.load_mount(entry)
        self.assertEqual(opened, [])

    def test_post_stat_containment_rechecks(self):
        cases = [('section', False), ('section', True), ('config', True),
                 ('links', False), ('links', True), ('kernel', True)]
        for operation, mounted in cases:
            with self.subTest(operation=operation, mounted=mounted):
                MountFixture.setUp(self)
                owner = self.module_root if mounted else self.root
                cfg = self.inner_cfg if mounted else self.cfg
                relative = {'section': 'wiki/guide.md', 'config': 'wiki/ai-context.json',
                            'links': 'wiki/README.md', 'kernel': 'AGENTS.md'}[operation]
                target = owner / relative
                token = 'OUTSIDE-POST-STAT-SENTINEL'
                text = '`guide`\n' + token + '\n'
                if operation == 'config':
                    outside_cfg = copy.deepcopy(self.inner_cfg)
                    outside_cfg['topics']['guide']['description'] = token
                    text = json.dumps(outside_cfg)
                outside = self.write(str(self.parent / 'outside/sentinel.txt'), text)
                entry = router.mount_entries(self.cfg, root=str(self.root))[0]
                if operation == 'kernel':
                    self.sibling()
                real_stat, real_open, real_isfile = os.stat, open, os.path.isfile
                swapped, opened = [], []
                def swapping_stat(path, *args, **kwargs):
                    info = real_stat(path, *args, **kwargs)
                    if not swapped and os.path.normcase(os.path.abspath(path)) == os.path.normcase(str(target)):
                        self.assertTrue(router.stat.S_ISREG(info.st_mode))
                        swapped.append(str(path))
                        target.unlink()
                        self.symlink(target, outside)
                    return info
                def swapping_isfile(path):
                    regular = real_isfile(path)
                    # Windows' native predicate bypasses os.stat. Retain its
                    # real result, then exercise the same real-stat boundary.
                    if regular and not swapped:
                        swapping_stat(path)
                    return regular
                def observed_open(path, *args, **kwargs):
                    if os.path.normcase(os.path.realpath(path)) == os.path.normcase(str(outside)):
                        opened.append(str(path))
                    return real_open(path, *args, **kwargs)
                # Return the REAL regular-file stat, then swap its pathname.
                # Only the synthetic sibling sentinel can be exposed on RED.
                with patch.object(router, 'ROOT', str(self.root)), \
                        patch.object(router.os, 'stat', side_effect=swapping_stat), \
                        patch('builtins.open', side_effect=observed_open):
                    try:
                        if operation == 'section':
                            output = router.section({'path': relative},
                                                    root=str(owner) if mounted else None)
                            code = 0
                        elif operation == 'config':
                            output = json.dumps(router.load_mount(entry))
                            code = 0
                        elif operation == 'links':
                            with patch.object(router.os.path, 'isfile', side_effect=swapping_isfile):
                                errors = router.link_problems(cfg, root=str(owner) if mounted else None)
                            code, output = int(bool(errors)), '\n'.join(errors)
                        else:
                            code, out, err = self.call_main('check')
                            output = out + err
                    except (ValueError, OSError) as error:
                        code, output = 1, str(error)
                self.assertEqual([os.path.normcase(path) for path in swapped], [os.path.normcase(str(target))])
                self.assertTrue(target.is_symlink())
                self.assertEqual(os.path.normcase(os.path.realpath(target)), os.path.normcase(str(outside)))
                with self.subTest(oracle='no-outside-open'):
                    self.assertEqual(opened, [])
                with self.subTest(oracle='rejected-before-read'):
                    self.assertEqual(code, 1, output)
                    self.assertIn('outside', output)
                    self.assertNotIn(token, output)
                    if operation == 'kernel':
                        self.assertIn('other/guide', output)


class MountCheckTests(MountFixture):
    def checked(self, failures=0):
        result = self.cli('check')
        self.assertEqual((result.returncode, result.stderr), (int(bool(failures)), ''),
                         result.stdout + result.stderr)
        summary = 'ok' if not failures else f'{failures} root(s) failed'
        self.assertEqual(result.stdout.splitlines()[-1], summary)
        self.assertEqual(result.stdout.splitlines().count(summary), 1)
        self.assertNotIn('problem(s)', result.stdout)
        return result.stdout

    def fresh(self):
        # Each mutation gets a new synthetic parent, and every parent is
        # registered for cleanup by the existing fixture, even on assertion.
        MountFixture.setUp(self)

    def test_independent_discovery(self):
        out = self.checked()
        self.assertIn(f'{"guide":18} ', out)
        self.assertIn(f'{"kb/guide":18} ', out)
        self.assertIn(f'{"kb/AGENTS.md":18} ', out)
        self.write('AGENTS.md', '`guide`\n`kb/guide`\n')
        self.write('modules/kb-core/AGENTS.md', 'No topic discovery.\n')
        self.assertIn('FAIL mount kb: guide: not listed in AGENTS.md', self.checked(1))
        self.write('AGENTS.md', 'No topic discovery.\n')
        self.write('modules/kb-core/AGENTS.md', '`guide`\n')
        out = self.checked(1)
        self.assertIn('FAIL guide: not listed in AGENTS.md', out)
        self.assertNotIn('FAIL mount kb: guide: not listed', out)
        self.write('AGENTS.md', '`guide`\n')
        self.inner_cfg['rootInstructions'] = 'KERNEL.md'
        self.write('modules/kb-core/KERNEL.md', '`guide`\n')
        self.inner_cfg['unrouted'] = {'AGENTS.md': 'Use KERNEL.md'}
        self.save_configs()
        self.assertIn(f'{"kb/KERNEL.md":18} ', self.checked())

    def test_budget_ownership(self):
        native = '<!-- wiki/guide.md -->\n# Guide\nModule.'
        self.assertEqual(len(native.encode('utf-8')), 38)
        raw_kernel = '`guide`\n  \t\n知識\n'
        root_bytes = len(raw_kernel.encode('utf-8'))
        self.write('modules/kb-core/AGENTS.md', raw_kernel)
        self.cfg['budgets'] = {'rootInstructionsMaxBytes': 10000, 'defaultTopicMaxBytes': 10000}
        self.sibling()
        self.inner_cfg['budgets'] = {'rootInstructionsMaxBytes': root_bytes, 'defaultTopicMaxBytes': 38}
        self.save_configs()
        self.assertIn(f'{"kb/guide":18} {38:6} B  (cap 38)', self.checked())
        direct = self.cli('check', root=self.module_root, config=self.module_root / 'wiki/ai-context.json')
        self.assertEqual((direct.returncode, direct.stderr), (0, ''))
        self.assertIn(f'{"guide":18} {38:6} B  (cap 38)', direct.stdout)
        self.inner_cfg['budgets']['defaultTopicMaxBytes'] = 37
        self.save_configs()
        self.assertIn('FAIL mount kb: guide: 38 B > 37', self.checked(1))
        self.inner_cfg['topics']['guide']['maxBytes'] = 38
        self.save_configs()
        self.checked()
        self.inner_cfg['budgets']['rootInstructionsMaxBytes'] = root_bytes - 1
        self.save_configs()
        self.assertIn(f'FAIL mount kb: AGENTS.md {root_bytes} B > {root_bytes - 1}', self.checked(1))
        self.inner_cfg['budgets']['rootInstructionsMaxBytes'] = root_bytes
        long_root = self.root / 'modules/a-very-long-consumer-directory/knowledge/core'
        long_root.parent.mkdir(parents=True)
        self.module_root.rename(long_root)
        self.module_root = long_root
        self.cfg['mounts']['kb']['root'] = str(long_root)
        self.save_configs()
        self.assertIn(f'{"kb/guide":18} {38:6} B  (cap 38)', self.checked())
        absolute = str(self.module_root / 'wiki/guide.md')
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = absolute
        absolute_bytes = len(('<!-- ' + absolute + ' -->\n# Guide\nModule.').encode('utf-8'))
        self.inner_cfg['topics']['guide']['maxBytes'] = absolute_bytes
        self.save_configs()
        self.assertIn(f'{"kb/guide":18} {absolute_bytes:6} B', self.checked())
        self.inner_cfg['topics']['guide']['maxBytes'] -= 1
        self.save_configs()
        self.assertIn(f'{absolute_bytes} B > {absolute_bytes - 1}', self.checked(1))
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'wiki/guide.md'
        self.inner_cfg['topics']['guide']['maxBytes'] = 38
        self.write(str(long_root / 'wiki/guide.md'), '# Guide\n模組。\n')
        multibyte = len('<!-- wiki/guide.md -->\n# Guide\n模組。'.encode('utf-8'))
        self.inner_cfg['topics']['guide']['maxBytes'] = multibyte
        self.save_configs()
        self.checked()
        self.inner_cfg['topics']['guide']['maxBytes'] -= 1
        self.save_configs()
        self.assertIn(f'{multibyte} B > {multibyte - 1}', self.checked(1))

    def test_failed_roots_continue(self):
        for kind, reason in [('missing', 'missing root'), ('outside', 'root'),
                             ('declaration', 'declaration'), ('typo', 'typo'),
                             ('schema', 'topics'), ('config-missing', 'config'),
                             ('config-directory', 'config'),
                             ('config-json', 'JSON'), ('nested', 'nested'),
                             ('kernel-missing', 'AGENTS.md'), ('kernel-utf8', 'AGENTS.md')]:
            with self.subTest(kind=kind):
                self.fresh()
                self.sibling()
                if kind == 'missing':
                    self.cfg['mounts']['kb']['root'] = 'modules/absent'
                    self.cfg['unrouted'] = {'modules/kb-core/*': 'Unmounted data'}
                elif kind == 'outside':
                    self.cfg['mounts']['kb']['root'] = '../outside'
                    self.cfg['unrouted'] = {'modules/kb-core/*': 'Unmounted data'}
                elif kind == 'declaration':
                    self.cfg['mounts']['kb'] = None
                    self.cfg['unrouted'] = {'modules/kb-core/*': 'Unmounted data'}
                elif kind == 'typo':
                    self.cfg['mounts']['kb']['typo'] = True
                elif kind == 'schema':
                    self.inner_cfg['topics'] = []
                elif kind == 'nested':
                    self.inner_cfg['mounts'] = {'never-follow': {'root': '../'}}
                self.save_configs()
                if kind == 'config-missing':
                    (self.module_root / 'wiki/ai-context.json').unlink()
                elif kind == 'config-directory':
                    (self.module_root / 'wiki/ai-context.json').unlink()
                    (self.module_root / 'wiki/ai-context.json').mkdir()
                elif kind == 'config-json':
                    self.write('modules/kb-core/wiki/ai-context.json', '{')
                elif kind == 'kernel-missing':
                    (self.module_root / 'AGENTS.md').unlink()
                elif kind == 'kernel-utf8':
                    (self.module_root / 'AGENTS.md').write_bytes(b'\xff')
                out = self.checked(1)
                self.assertIn('FAIL mount kb:', out)
                self.assertIn(reason, out)
                self.assertIn(f'{"other/guide":18} ', out)
                self.assertNotIn('NOTICE', out)
        self.fresh()
        self.sibling()
        self.write('AGENTS.md', 'No discovery.\n')
        self.write('modules/kb-core/AGENTS.md', 'No discovery.\n')
        self.write('wiki/extra.md', '# Orphan\n')
        out = self.checked(2)
        self.assertIn('FAIL guide: not listed', out)
        self.assertIn('FAIL mount kb: guide: not listed', out)
        self.assertIn(f'{"other/guide":18} ', out)

    def test_each_inner_rule(self):
        self.sibling()
        self.write('modules/kb-core/wiki/extra.md', '# Extra\n')
        self.cfg['unrouted'] = {'*': 'Outer-only exception'}
        self.cfg['skipDirs'] = ['modules']
        self.write('AGENTS.md', '`guide`\nwiki/extra.md\n')
        self.save_configs()
        code, out, err = self.call_main('check')
        self.assertEqual((code, err), (1, ''), out)
        self.assertIn('FAIL mount kb: wiki/extra.md: wiki page no topic loads', out)
        self.assertIn(f'{"other/guide":18} ', out)
        self.assertTrue(out.endswith('1 root(s) failed\n'), out)

    def test_inventory_ownership_and_aliases(self):
        for location in ['modules/kb-core', 'wiki/kb-core']:
            with self.subTest(location=location):
                self.fresh()
                target = self.root / location
                if target != self.module_root:
                    self.module_root.rename(target)
                    self.module_root = target
                self.cfg['mounts']['kb']['root'] = location
                self.cfg['mounts']['same'] = {'root': location}
                self.cfg['indexed'] = ['**/*.md']
                self.write('AGENTS.md', '`guide`\nAGENTS.md wiki/README.md\n')
                self.symlink(self.root / 'wiki/module-alias', target, directory=True)
                self.symlink(self.root / 'wiki/page-alias.md', target / 'wiki/guide.md')
                self.save_configs()
                out = self.checked()
                self.assertIn(f'{"same/guide":18} ', out)
                # Observe the outer walkers alone. Mounted checks legitimately
                # read the same subtree later with their independent rules.
                real_open, real_scan = open, os.scandir
                forbidden = []
                def owned(path):
                    physical = os.path.realpath(path)
                    return physical == str(target) or physical.startswith(str(target) + os.sep)
                def guarded_open(path, *args, **kwargs):
                    if owned(path):
                        forbidden.append(str(path))
                        raise AssertionError('outer automatic inventory read owned file')
                    return real_open(path, *args, **kwargs)
                def guarded_scan(path):
                    if owned(path):
                        forbidden.append(str(path))
                        raise AssertionError('outer automatic inventory scanned owned tree')
                    return real_scan(path)
                with patch.object(router, 'ROOT', str(self.root)), \
                        patch('builtins.open', side_effect=guarded_open), \
                        patch.object(router.os, 'scandir', side_effect=guarded_scan):
                    self.assertEqual(router.orphans(self.cfg, 'AGENTS.md wiki/README.md',
                                                   excluded_roots=[str(target)]), [])
                    self.assertEqual(router.link_problems(self.cfg, excluded_roots=[str(target)]), [])
                self.assertEqual(forbidden, [])
                neighbor = self.write(location + '-neighbor/wiki/extra.md', '# Unmounted\n')
                out = self.checked(1)
                self.assertIn(str(neighbor.relative_to(self.root)).replace(os.sep, '/'), out)
                neighbor.unlink()
                # An invalid config retains safe-root ownership; neither a
                # parent skip nor its exception can hide that mount failure.
                self.cfg['skipDirs'] = ['modules', 'wiki']
                self.cfg['unrouted'] = {'*': 'Outer rule only'}
                self.save_configs()
                (target / 'wiki/ai-context.json').unlink()
                out = self.checked(2)
                self.assertIn('FAIL mount kb: config', out)
                self.assertIn('FAIL mount same: config', out)
                self.assertNotIn('wiki page no topic loads', out)
                self.assertNotIn('indexed page not named', out)
                self.assertNotIn('scoped instructions no topic loads', out)

    def test_explicit_outer_sources_are_checked(self):
        inner_source = {'path': 'modules/kb-core/wiki/guide.md', 'heading': 'Guide'}
        self.cfg['topics']['guide']['sources'].append(inner_source)
        self.cfg['skipDirs'] = ['modules']
        self.write('modules/kb-core/wiki/guide.md', '# Guide\nSelected.\n# Other\n[Bad](missing.md)\n')
        self.save_configs()
        out = self.checked(2)
        self.assertIn('FAIL modules/kb-core/wiki/guide.md:4: relative link', out)
        self.assertIn('FAIL mount kb: wiki/guide.md:4: relative link', out)
        self.write('modules/kb-core/wiki/guide.md', '# Guide\nModule.\n')
        inner_source['heading'] = 'Missing'
        self.save_configs()
        self.assertIn("FAIL guide: modules/kb-core/wiki/guide.md: heading 'Missing' found 0x", self.checked(1))
        inner_source['heading'] = 'Guide'
        self.cfg['topics']['guide']['maxBytes'] = 1
        self.save_configs()
        self.assertIn('FAIL guide:', self.checked(1))
        self.cfg['topics']['guide'].pop('maxBytes')
        self.cfg['topics']['guide']['sources'].pop()
        self.cfg['routerFile'] = 'modules/kb-core/wiki/README.md'
        self.cfg['unrouted'] = {'wiki/README.md': 'Using module router explicitly'}
        self.write('modules/kb-core/wiki/README.md', '[Bad](missing.md)\n')
        self.save_configs()
        self.assertIn('FAIL modules/kb-core/wiki/README.md:1: relative link', self.checked(2))
        self.fresh()
        self.write('wiki/guide.md', '# Guide\n[Module](../modules/kb-core/wiki/guide.md)\n')
        self.checked()
        self.write('modules/kb-core/wiki/guide.md', '# Guide\n[Project](../../../wiki/guide.md)\n')
        self.assertIn('FAIL mount kb: wiki/guide.md:2: relative link', self.checked(1))

    def test_absolute_and_alias_ownership(self):
        self.inner_cfg.update(rootInstructions=str(self.module_root / 'AGENTS.md'),
                              wikiDir=str(self.module_root / 'wiki'),
                              historyDir=str(self.module_root / 'wiki/history'),
                              routerFile=str(self.module_root / 'wiki/README.md'), indexed=['docs/*.md'])
        self.inner_cfg['topics']['guide']['sources'] = [
            {'path': str(self.module_root / 'wiki/guide.md'), 'heading': 'Guide'}]
        self.write('modules/kb-core/wiki/README.md', 'history/log.md\ndocs/runbook.md\n')
        self.write('modules/kb-core/wiki/history/log.md', '# History\n')
        self.write('modules/kb-core/docs/runbook.md', '# Runbook\n')
        self.save_configs()
        self.checked()
        self.symlink(self.module_root / 'wiki/alias.md', self.module_root / 'wiki/guide.md')
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'wiki/alias.md'
        self.save_configs()
        self.checked()
        self.symlink(self.module_root / 'KERNEL.md', self.module_root / 'AGENTS.md')
        self.symlink(self.module_root / 'router-alias.md', self.module_root / 'wiki/README.md')
        self.inner_cfg['rootInstructions'] = 'KERNEL.md'
        self.inner_cfg['routerFile'] = 'router-alias.md'
        self.save_configs()
        self.checked()
        self.symlink(self.module_root / 'wiki-alias', self.module_root / 'wiki', directory=True)
        self.inner_cfg['wikiDir'] = 'wiki-alias'
        self.save_configs()
        self.checked()
        # Each lexical alias has its own link base despite one physical file.
        self.fresh()
        self.write('modules/kb-core/docs/page.md', '[Neighbor](neighbor.md)\n')
        self.write('modules/kb-core/docs/neighbor.md', '# Neighbor\n')
        self.symlink(self.module_root / 'wiki/alias.md', self.module_root / 'docs/page.md')
        self.inner_cfg['topics']['guide']['sources'] = [
            {'path': 'wiki/guide.md'}, {'path': 'wiki/alias.md'}, {'path': 'docs/page.md'}]
        for reverse in [False, True]:
            if reverse:
                self.inner_cfg['topics']['guide']['sources'].reverse()
            self.save_configs()
            out = self.checked(1)
            self.assertEqual(out.count('FAIL mount kb: wiki/alias.md:1: relative link'), 1)
            self.assertNotIn('FAIL mount kb: docs/page.md:1: relative link', out)

    def test_mounted_reads_stay_inside(self):
        for kind in ['instructions-relative', 'instructions-absolute', 'instructions-alias',
                     'source-relative', 'source-absolute', 'source-alias', 'source-directory',
                     'router-relative', 'router-alias', 'wiki-alias', 'indexed-alias',
                     'link-relative', 'link-encoded']:
            with self.subTest(kind=kind):
                self.fresh()
                inside_outer = not kind.endswith('alias')
                outside = self.write('outer-only/secret.md' if inside_outer else
                                     str(self.parent / 'outside/secret.md'), '# Outside inner owner\n')
                relative = '../../outer-only/secret.md'
                detail = 'secret.md'
                if kind.startswith('instructions'):
                    self.inner_cfg['rootInstructions'] = relative
                    if kind.endswith('absolute'):
                        self.inner_cfg['rootInstructions'] = str(outside)
                    elif kind.endswith('alias'):
                        self.symlink(self.module_root / 'kernel.md', outside)
                        self.inner_cfg['rootInstructions'] = 'kernel.md'
                        detail = 'kernel.md'
                elif kind.startswith('source'):
                    source = self.inner_cfg['topics']['guide']['sources'][0]
                    source['path'] = relative
                    if kind.endswith('absolute'):
                        source['path'] = str(outside)
                    elif kind.endswith('alias'):
                        self.symlink(self.module_root / 'wiki/escape.md', outside)
                        source['path'] = 'wiki/escape.md'
                        detail = 'escape.md'
                    elif kind.endswith('directory'):
                        source['path'] = 'wiki'
                        detail = 'wiki'
                elif kind.startswith('router'):
                    self.inner_cfg['routerFile'] = relative
                    if kind.endswith('alias'):
                        self.symlink(self.module_root / 'wiki/router.md', outside)
                        self.inner_cfg['routerFile'] = 'wiki/router.md'
                        detail = 'router.md'
                elif kind == 'wiki-alias':
                    self.symlink(self.module_root / 'wiki/escape', outside.parent, directory=True)
                    detail = 'wiki/escape'
                elif kind == 'indexed-alias':
                    self.symlink(self.module_root / 'docs/escape.md', outside)
                    self.inner_cfg['indexed'] = ['docs/*.md']
                    self.write('modules/kb-core/AGENTS.md', '`guide`\ndocs/escape.md\n')
                    detail = 'docs/escape.md'
                else:
                    destination = '../../../outer-only/secret.md'
                    if kind == 'link-encoded':
                        destination = '%2e%2e/%2e%2e/%2e%2e/outer-only/secret.md'
                    self.write('modules/kb-core/wiki/guide.md', '# Guide\n[Outside](' + destination + ')\n')
                self.save_configs()
                real_open, real_scan = open, os.scandir
                forbidden = []
                def guarded_open(path, *args, **kwargs):
                    if os.path.realpath(path) == str(outside):
                        forbidden.append(str(path))
                        raise AssertionError('external content opened')
                    return real_open(path, *args, **kwargs)
                def guarded_scan(path):
                    # For file escapes into the outer project, its automatic
                    # walk may legitimately scan outer-only. Alias scan cases
                    # target a sibling outside BOTH roots, still in this temp.
                    if not inside_outer and os.path.realpath(path) == str(outside.parent):
                        forbidden.append(str(path))
                        raise AssertionError('external directory scanned')
                    return real_scan(path)
                with patch('builtins.open', side_effect=guarded_open), \
                        patch.object(router.os, 'scandir', side_effect=guarded_scan):
                    code, out, err = self.call_main('check')
                self.assertEqual((code, err), (1, ''), out + err)
                self.assertIn('FAIL mount kb:', out)
                self.assertIn(detail, out)
                self.assertEqual(forbidden, [])
        self.fresh()
        self.write('modules/kb-core/wiki/guide.md', '# Guide\n'
                   '[External](https://example.invalid) [Absolute](/not/read) [Fragment](#guide)\n')
        self.checked()

    def test_directory_settings_and_regular_file_boundaries(self):
        for field in ['wikiDir', 'historyDir', 'routerFile', 'rootInstructions']:
            for spelling in ['relative', 'absolute', 'alias']:
                with self.subTest(field=field, spelling=spelling):
                    self.fresh()
                    outside = self.write(str(self.parent / 'outside/secret.md'), '# Outside\n')
                    target = outside.parent if field in ('wikiDir', 'historyDir') else outside
                    if spelling == 'relative':
                        value = os.path.relpath(target, self.module_root)
                    elif spelling == 'absolute':
                        value = str(target)
                    else:
                        alias = self.module_root / ('external' if target.is_dir() else 'external.md')
                        self.symlink(alias, target, directory=target.is_dir())
                        value = alias.name
                    self.inner_cfg[field] = value
                    self.save_configs()
                    real_open, real_scan = open, os.scandir
                    forbidden = []
                    def guarded_open(path, *args, **kwargs):
                        if os.path.realpath(path) == str(outside):
                            forbidden.append(str(path))
                            raise AssertionError('outside configured file read')
                        return real_open(path, *args, **kwargs)
                    def guarded_scan(path):
                        if os.path.realpath(path) == str(outside.parent):
                            forbidden.append(str(path))
                            raise AssertionError('outside configured directory scanned')
                        return real_scan(path)
                    with patch('builtins.open', side_effect=guarded_open), \
                            patch.object(router.os, 'scandir', side_effect=guarded_scan):
                        code, out, err = self.call_main('check')
                    self.assertEqual((code, err), (1, ''), out + err)
                    self.assertIn('FAIL mount kb:', out)
                    self.assertIn(field, out)
                    self.assertIn(value, out)
                    self.assertEqual(forbidden, [])
        for field in ['rootInstructions', 'routerFile']:
            with self.subTest(directory_file=field):
                self.fresh()
                self.inner_cfg[field] = 'wiki'
                self.save_configs()
                out = self.checked(1)
                self.assertIn('FAIL mount kb:', out)
                self.assertIn('wiki', out)
        self.fresh()
        # A referenced indexed-only dangling file must still fail file checks;
        # the reference deliberately prevents the orphan rule masking it.
        self.symlink(self.module_root / 'docs/broken.md', self.module_root / 'absent.md')
        self.inner_cfg['indexed'] = ['docs/*.md']
        self.write('modules/kb-core/AGENTS.md', '`guide`\ndocs/broken.md\n')
        self.save_configs()
        out = self.checked(1)
        self.assertIn('FAIL mount kb: docs/broken.md', out)
        self.assertNotIn('indexed page not named', out)

    def test_explicit_checkers_keep_globals_and_references(self):
        self.write('modules/kb-core/docs/runbook.md', '# Indexed\n')
        self.inner_cfg['indexed'] = ['docs/*.md']
        self.write('AGENTS.md', '`guide`\ndocs/runbook.md\n')
        self.save_configs()
        original = router.ROOT, router.CFG_PATH
        for owner, cfg, expected in [(self.root, self.cfg, []),
                                      (self.module_root, self.inner_cfg, ['docs/runbook.md']),
                                      (self.root, self.cfg, [])]:
            excluded = [str(self.module_root)] if owner == self.root else []
            problems = router.orphans(cfg, root=str(owner), excluded_roots=excluded)
            self.assertEqual([item.split(':', 1)[0] for item in problems], expected)
            self.assertEqual(router.link_problems(cfg, root=str(owner), excluded_roots=excluded), [])
            output = io.BytesIO()
            stream = io.TextIOWrapper(output, encoding='utf-8')
            try:
                with patch.object(sys, 'stdout', stream):
                    code = router.check(cfg, root=str(owner), excluded_roots=excluded)
                stream.flush()
                text = output.getvalue().decode('utf-8')
            finally:
                stream.close()
            self.assertEqual(code, int(bool(expected)), text)
            self.assertEqual((router.ROOT, router.CFG_PATH), original)
        self.write('modules/kb-core/AGENTS.md', '`guide`\ndocs/runbook.md\n')
        self.checked()

    def test_owned_read_errors_continue(self):
        for relative, operation in [('wiki/ai-context.json', 'read'), ('AGENTS.md', 'read'),
                                    ('wiki/guide.md', 'read'),
                                    ('wiki/README.md', 'read'), ('wiki', 'scan')]:
            for fault in ['denied', 'utf8'] if operation == 'read' else ['denied']:
                with self.subTest(relative=relative, fault=fault):
                    self.fresh()
                    self.sibling()
                    target = self.module_root / relative
                    real_open, real_scan = open, os.scandir
                    reached = []
                    if fault == 'utf8':
                        target.write_bytes(b'\xff')
                    def failing_open(path, *args, **kwargs):
                        if operation == 'read' and os.path.abspath(path) == str(target):
                            reached.append('read')
                            if fault == 'denied':
                                raise PermissionError('synthetic denied read')
                        return real_open(path, *args, **kwargs)
                    def failing_scan(path):
                        if operation == 'scan' and os.path.abspath(path) == str(target):
                            reached.append('scan')
                            raise PermissionError('synthetic denied scan')
                        return real_scan(path)
                    with patch('builtins.open', side_effect=failing_open), \
                            patch.object(router.os, 'scandir', side_effect=failing_scan):
                        code, out, err = self.call_main('check')
                    self.assertEqual((code, err), (1, ''), out + err)
                    self.assertIn('FAIL mount kb:', out)
                    self.assertIn(relative, out.replace('\\', '/'))
                    self.assertIn(f'{"other/guide":18} ', out)
                    self.assertTrue(out.endswith('1 root(s) failed\n'), out)
                    self.assertIn(operation, reached)
                    self.assertIn('synthetic denied ' + operation if fault == 'denied'
                                  else 'utf-8', out.lower())
        self.fresh()
        self.sibling()
        (self.root / 'AGENTS.md').unlink()
        out = self.checked(1)
        self.assertIn('FAIL AGENTS.md', out)
        self.assertIn(f'{"kb/guide":18} ', out)
        self.assertIn(f'{"other/guide":18} ', out)


class MountCompatibilityTests(MountFixture):
    def test_absent_and_empty_mounts_match(self):
        # No static module should influence the original single-root check.
        shutil.rmtree(self.root / 'modules')
        self.cfg.pop('mounts')
        self.cfg['topics']['ops/guide'] = copy.deepcopy(self.cfg['topics']['guide'])
        self.write('AGENTS.md', '`guide`\n`ops/guide`\n')
        local_body = '<!-- wiki/guide.md -->\n# Guide\nLocal.\n'
        commands = [(), ('list',), ('guide',), ('ops/guide',),
                    ('guide', 'ops/guide'), ('guide', 'guide'),
                    ('unknown',), ('check',)]
        for args in commands:
            with self.subTest(args=args):
                self.cfg.pop('mounts', None)
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                absent = self.cli(*args)
                self.cfg['mounts'] = {}
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                empty = self.cli(*args)
                self.assertEqual((absent.returncode, absent.stdout, absent.stderr),
                                 (empty.returncode, empty.stdout, empty.stderr))
                if args == ('unknown',):
                    self.assertEqual((empty.returncode, empty.stdout, empty.stderr),
                                     (1, '', "unknown topic 'unknown'; rerun this script with list\n"))
                else:
                    self.assertEqual((empty.returncode, empty.stderr), (0, ''), empty.stdout)
                    if args in [(), ('list',)]:
                        self.assertEqual(empty.stdout, f'{"guide":18} Project guide\n'
                                         f'{"ops/guide":18} Project guide\n')
                    elif args == ('check',):
                        self.assertTrue(empty.stdout.endswith('\nok\n'), empty.stdout)
                        self.assertNotIn('root(s)', empty.stdout)
                    else:
                        self.assertEqual(empty.stdout,
                                         '\n\n'.join([local_body.rstrip('\n')] * len(args)) + '\n')
        self.write('wiki/ai-context.json', '{malformed existing config')
        version = self.cli('--version')
        expected_version = json.loads((SKILL.parents[1] / 'package.json').read_text(encoding='utf-8'))['version']
        self.assertEqual((version.returncode, version.stdout, version.stderr),
                         (0, f'agents-context-router {expected_version}\n', ''))

    def test_routed_fixture_mount(self):
        fixture = SKILL / 'evals/fixtures/routed'
        overrides = {'AI_CONTEXT_ROOT': str(fixture),
                     'AI_CONTEXT_CONFIG': str(fixture / 'wiki/ai-context.json')}
        mounted = '<!-- modules/kb-core/wiki/guide.md -->\n# Guide\n\nMounted module knowledge.\n'
        listed = run_router(SCRIPT, 'list', overrides=overrides, cwd=self.parent)
        self.assertEqual((listed.returncode, listed.stderr), (0, ''), listed.stdout)
        self.assertIn(f'{"kb/guide":18} Module guide [modules/kb-core]', listed.stdout.splitlines())
        module = run_router(SCRIPT, 'kb/guide', overrides=overrides, cwd=self.parent)
        self.assertEqual((module.returncode, module.stdout, module.stderr), (0, mounted, ''))


class MountAliasTests(MountFixture):
    def checked_alias(self, expected, *details):
        result = self.cli('check')
        self.assertEqual((result.returncode, result.stderr), (expected, ''), result.stdout)
        for detail in details:
            self.assertIn(detail, result.stdout)
        if expected == 0:
            self.assertTrue(result.stdout.endswith('\nok\n'), result.stdout)

    def alias_membership(self, owner, cfg, mounted):
        prefix = 'FAIL mount kb: ' if mounted else 'FAIL '
        cases = [('wiki/extra.md', 'docs/unlisted.md', '', 'wiki page no topic loads'),
                 ('wiki/history/alias.md', 'wiki/guide.md', '', 'history file not indexed'),
                 ('wiki/extra.md', 'wiki/history/log.md', 'history/log.md\n',
                  'wiki page no topic loads'),
                 ('wiki/extra.md', 'wiki/README.md', '', 'wiki page no topic loads'),
                 ('wiki/extra.md', 'AGENTS.md', '', 'wiki page no topic loads'),
                 ('scoped/AGENTS.md', 'AGENTS.md', '', 'scoped instructions no topic loads')]
        for alias_name, target_name, index, reason in cases:
            with self.subTest(mounted=mounted, alias=alias_name, target=target_name):
                target = owner / target_name
                created = not target.exists()
                if created:
                    self.write(str(target), '# Alias target\n')
                alias = owner / alias_name
                self.symlink(alias, target)
                try:
                    self.write(str(owner / 'wiki/README.md'), '# Router\n' + index)
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                    self.checked_alias(1, prefix + alias_name + ': ' + reason)
                    if target_name in ('wiki/README.md', 'AGENTS.md'):
                        cfg.setdefault('unrouted', {})[alias_name] = 'Deliberate lexical alias'
                        self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                        self.checked_alias(0)
                        cfg['unrouted'].pop(alias_name)
                    if reason == 'history file not indexed':
                        self.write(str(owner / 'wiki/README.md'), '# Router\nhistory/alias.md\n')
                    else:
                        cfg['topics']['guide']['sources'].append({'path': alias_name})
                        self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                    self.checked_alias(0)
                finally:
                    cfg['topics']['guide']['sources'] = [{'path': 'wiki/guide.md'}]
                    cfg.get('unrouted', {}).pop(alias_name, None)
                    alias.unlink()
                    if created:
                        target.unlink()
                    self.write(str(owner / 'wiki/README.md'), '# Router\n')
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))

    def configured_alias_membership(self, owner, cfg, mounted):
        prefix = 'FAIL mount kb: ' if mounted else 'FAIL '
        cases = [('routerFile', 'wiki/router.md', 'docs/router.md', '# Router\n',
                  'wiki/README.md', '# Router\n', 'wiki/extra.md', 'wiki page no topic loads'),
                 ('rootInstructions', 'scoped/AGENTS.md', 'kernel.md', '`guide`\n',
                  'AGENTS.md', '`guide`\n', 'other/AGENTS.md', 'scoped instructions no topic loads')]
        for field, selected, target_name, text, default, default_text, extra, reason in cases:
            with self.subTest(mounted=mounted, configured=field, selected=selected):
                target = self.write(str(owner / target_name), text)
                alias, unrelated = owner / selected, owner / extra
                self.symlink(alias, target)
                (owner / default).unlink()
                cfg[field] = selected
                try:
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                    self.checked_alias(0)
                    self.symlink(unrelated, target)
                    self.checked_alias(1, prefix + extra + ': ' + reason)
                    cfg.setdefault('unrouted', {})[extra] = 'Deliberate lexical alias'
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                    self.checked_alias(0)
                    cfg['unrouted'].pop(extra)
                    cfg['topics']['guide']['sources'].append({'path': extra})
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))
                    self.checked_alias(0)
                finally:
                    cfg.pop(field)
                    cfg.get('unrouted', {}).pop(extra, None)
                    cfg['topics']['guide']['sources'] = [{'path': 'wiki/guide.md'}]
                    if unrelated.is_symlink():
                        unrelated.unlink()
                    alias.unlink()
                    target.unlink()
                    self.write(str(owner / default), default_text)
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg))

    def test_outer_alias_membership(self):
        # Also run unchanged against main's executable: no mounts or new API.
        self.cfg.pop('mounts')
        shutil.rmtree(self.root / 'modules')
        self.alias_membership(self.root, self.cfg, mounted=False)
        self.configured_alias_membership(self.root, self.cfg, mounted=False)

    def test_mounted_alias_membership(self):
        self.alias_membership(self.module_root, self.inner_cfg, mounted=True)
        self.configured_alias_membership(self.module_root, self.inner_cfg, mounted=True)

    def test_mounted_routed_aliases_keep_physical_matching(self):
        target = self.write('modules/kb-core/docs/routed.md', '# Routed\n')
        self.symlink(self.module_root / 'wiki/alias.md', target)
        # Routing either spelling makes this one physical page reachable.
        for source in ['docs/routed.md', 'wiki/alias.md', str(target)]:
            with self.subTest(source=source):
                self.inner_cfg['topics']['guide']['sources'] = [
                    {'path': 'wiki/guide.md'}, {'path': source}]
                self.save_configs()
                self.checked_alias(0)


class MountWindowsMembershipTests(MountFixture):
    def membership_case(self, wiki, history, relative, reason, index='', routed=False, alias=False):
        MountFixture.setUp(self)
        shutil.rmtree(self.module_root / 'wiki')
        self.inner_cfg.update(wikiDir=wiki, historyDir=history,
                              routerFile=wiki + '/README.md')
        self.inner_cfg['topics']['guide']['sources'] = [{'path': wiki + '/guide.md'}]
        self.write(str(self.module_root / (wiki + '/README.md')), '# Router\n')
        self.write(str(self.module_root / (wiki + '/guide.md')), '# Guide\nModule.\n')
        self.save_configs()
        self.assertEqual(self.call_main('check')[0], 0)
        if alias:
            target = self.write(str(self.module_root / 'docs/routed.md'), '# Alias target\n')
            self.symlink(self.module_root / relative, target)
        else:
            self.write(str(self.module_root / relative), '# Extra\n')
        if routed:
            self.inner_cfg['topics']['guide']['sources'].append({'path': relative})
        self.save_configs()
        code, out, err = self.call_main('check')
        with self.subTest(stage='unindexed' if index else 'unrouted'):
            self.assertEqual((code, err), (1, ''), out)
            self.assertIn('FAIL mount kb: ' + relative + ': ' + reason, out)
            self.assertNotIn('FAIL mount kb: ' + relative.lower() + ':', out)
        if index:
            # References retain the on-disk case and wiki-relative spelling.
            self.write(str(self.module_root / (wiki + '/README.md')), '# Router\n' + index + '\n')
        else:
            self.inner_cfg['unrouted'] = {relative: 'Deliberate lexical exception'}
            self.save_configs()
            code, out, err = self.call_main('check')
            self.assertEqual((code, err), (0, ''), out)
            self.inner_cfg.pop('unrouted')
            # Physical matching must still recognize a routed alias target.
            source = 'docs/routed.md' if alias else relative
            self.inner_cfg['topics']['guide']['sources'].append({'path': source})
            self.save_configs()
        code, out, err = self.call_main('check')
        self.assertEqual((code, err), (0, ''), out)
        self.assertTrue(out.endswith('\nok\n'), out)

    def simulated_windows_normcase(self):
        # Simulate Windows case normalization on the real host filesystem.
        # Adapt separators only; this is not native Windows runtime evidence.
        native_normcase = ntpath.normcase
        return patch.object(router.os.path, 'normcase',
                            side_effect=lambda path: native_normcase(path).replace('\\', os.sep))

    def test_real_platform_membership(self):
        cases = [('Wiki', 'Wiki/history', 'Wiki/extra.md', 'wiki page no topic loads', '', False, False),
                 ('wiki', 'wiki/HiStOrY', 'wiki/HiStOrY/log.md',
                  'history file not indexed', 'HiStOrY/log.md', False, False),
                 ('wiki', 'wiki/HiStOrY', 'wiki/HiStOrY/log.md',
                  'history file not indexed', 'HiStOrY/log.md', True, False),
                 ('Wiki', 'Wiki/history', 'Wiki/extra.md', 'wiki page no topic loads', '', False, True)]
        # Native execution is never patched. The comparison mode is useful
        # only where Windows normalization differs; it is not filesystem CI.
        modes = [('native', nullcontext)]
        probe = 'Wiki/HiStOrY'
        if os.path.normcase(probe) != ntpath.normcase(probe).replace('\\', os.sep):
            modes.append(('Windows-normalization comparison', self.simulated_windows_normcase))
        for mode, context in modes:
            with context():
                for wiki, history, relative, reason, index, routed, alias in cases:
                    with self.subTest(mode=mode, wiki=wiki, history=history, routed=routed, alias=alias):
                        self.membership_case(wiki, history, relative, reason, index,
                                             routed=routed, alias=alias)


class MountUnicodeInputTests(MountFixture):
    def test_escaped_surrogates_fail_safely_and_continue(self):
        for field in ['mount name', 'topic name', 'description']:
            for surrogate in ['\ud800', '\udfff']:
                for command in ['list', 'check']:
                    with self.subTest(field=field, scalar=ascii(surrogate), command=command):
                        MountFixture.setUp(self)
                        self.sibling()
                        invalid = 'bad' + surrogate
                        if field == 'mount name':
                            self.cfg['mounts'] = {invalid: {'root': 'modules/kb-core'},
                                                  'other': {'root': 'modules/other'}}
                        elif field == 'topic name':
                            self.inner_cfg['topics'] = {invalid: self.inner_cfg['topics']['guide']}
                        else:
                            self.inner_cfg['topics']['guide']['description'] = invalid
                        # Valid UTF-8 JSON containing escapes, never a raw surrogate
                        # in a fixture file, subprocess argument or test output.
                        for owner, cfg in [(self.root, self.cfg), (self.module_root, self.inner_cfg)]:
                            self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg, ensure_ascii=True))
                        result = self.cli(command)
                        with self.subTest(stage='invalid-entry'):
                            self.assertEqual((result.returncode, 'Traceback' in result.stderr,
                                              'other/guide' in result.stdout), (1, False, True),
                                             result.stdout + result.stderr)
                            diagnostic = result.stdout + result.stderr
                            self.assertIn('FAIL mount ', diagnostic)
                            self.assertIn({'mount name': 'name', 'topic name': 'topics',
                                           'description': 'description'}[field], diagnostic)
                        healthy = self.cli('other/guide')
                        self.assertEqual((healthy.returncode, healthy.stderr), (0, ''))
                        self.assertIn('Other.', healthy.stdout)

    def test_ordinary_unicode_and_escaped_pairs_remain_valid(self):
        self.sibling()
        mount, topic, description = '知識🚀', '指南🌍', '操作說明 café 🧭'
        self.cfg['mounts'] = {mount: {'root': 'modules/kb-core'},
                              'other': {'root': 'modules/other'}}
        self.inner_cfg['topics'] = {topic: {'description': description,
                                           'sources': [{'path': 'wiki/guide.md'}]}}
        self.write('modules/kb-core/AGENTS.md', '`' + topic + '`\n')
        for escaped in [True, False]:
            with self.subTest(escaped_json=escaped):
                for owner, cfg in [(self.root, self.cfg), (self.module_root, self.inner_cfg)]:
                    self.write(str(owner / 'wiki/ai-context.json'), json.dumps(cfg, ensure_ascii=escaped))
                listed = self.cli('list')
                self.assertEqual((listed.returncode, listed.stderr), (0, ''))
                self.assertIn(f'{mount + "/" + topic:18} {description} [modules/kb-core]', listed.stdout)
                checked = self.cli('check')
                self.assertEqual((checked.returncode, checked.stderr), (0, ''), checked.stdout)
                selected = self.cli(mount + '/' + topic, 'other/guide')
                self.assertEqual((selected.returncode, selected.stderr), (0, ''))
                self.assertIn('Module.', selected.stdout)
                self.assertIn('Other.', selected.stdout)


class MountSurrogatePathTests(MountFixture):
    def save_path_configs(self, config='wiki/ai-context.json'):
        # JSON stays strict UTF-8; invalid scalars exist only as JSON escapes.
        self.write('wiki/ai-context.json', json.dumps(self.cfg, ensure_ascii=True))
        self.write(str(self.module_root / config), json.dumps(self.inner_cfg, ensure_ascii=True))

    def assert_invalid_path_continues(self, field):
        for args in [('list',), ('check',), ('guide', 'kb/guide'), ('kb/guide', 'guide')]:
            with self.subTest(command=args):
                result = self.cli(*args)
                self.assert_failure(result, 'mount kb:' if args[0] in ('list', 'check') else 'kb/guide:', field)
                self.assertNotIn('NOTICE', result.stdout)
                if args[0] in ('list', 'check'):
                    self.assertIn('other/guide', result.stdout)
                    if args == ('list',):
                        self.assertNotIn(f'{"kb/guide":18} ', result.stdout)
                else:
                    self.assertEqual(result.stdout, '')
        healthy = self.cli('guide', 'other/guide')
        self.assertEqual((healthy.returncode, healthy.stderr), (0, ''))
        self.assertEqual(healthy.stdout, '<!-- wiki/guide.md -->\n# Guide\nLocal.\n\n'
                         '<!-- modules/other/wiki/guide.md -->\n# Guide\nOther.\n')

    def test_escaped_surrogate_paths_fail_safely_and_continue(self):
        for field in ['root', 'config', 'sources.path']:
            for scalar in ['\ud800', '\udcff']:
                with self.subTest(field=field, scalar=ascii(scalar)):
                    MountFixture.setUp(self)
                    self.sibling()
                    self.cfg['skipDirs'] = ['modules']
                    if field == 'root':
                        self.cfg['mounts']['kb']['root'] = 'modules/bad' + scalar
                    elif field == 'config':
                        self.cfg['mounts']['kb']['config'] = 'wiki/bad' + scalar + '.json'
                    else:
                        self.inner_cfg['topics']['guide']['sources'][0]['path'] = 'wiki/bad' + scalar + '.md'
                    self.save_path_configs()
                    self.assert_invalid_path_continues(field)

    @unittest.skipUnless(os.name == 'posix', 'real non-UTF-8 filename requires POSIX')
    def test_posix_non_utf8_paths_fail_without_partial_render(self):
        for field in ['root', 'config', 'sources.path']:
            with self.subTest(field=field):
                MountFixture.setUp(self)
                self.sibling()
                self.cfg['skipDirs'] = ['modules']
                name = os.fsdecode(b'bad\xff')
                self.assertEqual(os.fsencode(name), b'bad\xff')
                self.assertIn('\udcff', name)
                config = 'wiki/ai-context.json'
                if field == 'root':
                    moved = self.module_root.with_name(name)
                    self.cfg['mounts']['kb']['root'] = 'modules/' + name
                elif field == 'config':
                    config = 'wiki/' + name + '.json'
                    self.cfg['mounts']['kb']['config'] = config
                else:
                    source = 'wiki/' + name + '.md'
                    self.inner_cfg['topics']['guide']['sources'][0]['path'] = source
                selected_path = (moved if field == 'root' else self.module_root /
                                 (config if field == 'config' else source))
                try:
                    if field == 'root':
                        self.module_root.rename(moved)
                        self.module_root = moved
                    elif field == 'sources.path':
                        (self.module_root / 'wiki/guide.md').rename(selected_path)
                    self.save_path_configs(config)
                except OSError as error:
                    # Some POSIX filesystems (including hosted macOS) refuse
                    # raw byte names. Still run every CLI safety/continuation
                    # assertion with the identical escaped path declaration.
                    self.assertEqual(error.errno, errno.EILSEQ)
                    failed_paths = [os.fsdecode(path) for path in (error.filename, error.filename2)
                                    if path is not None]
                    self.assertIn(str(selected_path), failed_paths)
                    self.save_path_configs()
                else:
                    # Linux must exercise actual existing non-UTF-8 names.
                    self.assertTrue(selected_path.exists())
                self.assertIn(b'bad\xff', os.fsencode(selected_path))
                self.assert_invalid_path_continues(field)

    def test_unicode_paths_and_escaped_pairs_remain_valid(self):
        self.sibling()
        moved = self.module_root.with_name('知識🚀')
        self.module_root.rename(moved)
        self.module_root = moved
        config, source = 'wiki/設定🧭.json', 'wiki/指南🌍.md'
        (moved / 'wiki/guide.md').rename(moved / source)
        self.cfg['mounts']['kb'] = {'root': 'modules/知識🚀', 'config': config}
        self.inner_cfg['topics']['guide']['sources'][0]['path'] = source
        for escaped in [True, False]:
            with self.subTest(escaped_json=escaped):
                self.write('wiki/ai-context.json', json.dumps(self.cfg, ensure_ascii=escaped))
                self.write(str(moved / config), json.dumps(self.inner_cfg, ensure_ascii=escaped))
                listed = self.cli('list')
                self.assertEqual((listed.returncode, listed.stderr), (0, ''))
                self.assertIn(f'{"kb/guide":18} Module guide [modules/知識🚀]', listed.stdout)
                checked = self.cli('check')
                self.assertEqual((checked.returncode, checked.stderr), (0, ''), checked.stdout)
                selected = self.cli('kb/guide', 'other/guide')
                self.assertEqual((selected.returncode, selected.stderr), (0, ''))
                self.assertEqual(selected.stdout, '<!-- modules/知識🚀/wiki/指南🌍.md -->\n# Guide\nModule.\n\n'
                                 '<!-- modules/other/wiki/guide.md -->\n# Guide\nOther.\n')


class LegacyInventoryPolicyTests(MountFixture):
    def test_legacy_dot_wiki_skip_dirs_preserves_base_success(self):
        shutil.rmtree(self.root / 'modules')
        self.cfg.update(wikiDir='.', routerFile='wiki/README.md',
                        historyDir='wiki/history', skipDirs=['generated'])
        self.write('generated/AGENTS.md', '# Generated instructions\n')
        for empty_mounts in [False, True]:
            with self.subTest(empty_mounts=empty_mounts):
                self.cfg.pop('mounts', None)
                if empty_mounts:
                    self.cfg['mounts'] = {}
                self.cfg['skipDirs'] = ['generated']
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                with self.subTest(stage='base-success'):
                    result = self.cli('check')
                    self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                    self.assertTrue(result.stdout.endswith('\nok\n'), result.stdout)
                    self.assertNotIn('root(s)', result.stdout)
                self.cfg['skipDirs'] = []
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                with self.subTest(stage='unskipped-negative'):
                    self.assert_failure(self.cli('check'),
                                        'FAIL generated/AGENTS.md: scoped instructions no topic loads')
                self.cfg['topics']['guide']['sources'].append({'path': 'generated/AGENTS.md'})
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                with self.subTest(stage='explicit-route'):
                    routed = self.cli('check')
                    self.assertEqual((routed.returncode, routed.stderr), (0, ''), routed.stdout)
                self.cfg['topics']['guide']['sources'].pop()

    def test_legacy_builtin_wiki_scope_stays_unchanged(self):
        for wiki, page in [('.', 'vendor/extra.md'), ('knowledge', 'knowledge/vendor/extra.md'),
                           ('.knowledge', '.knowledge/extra.md'), ('vendor', 'vendor/extra.md'),
                           ('vendor/knowledge', 'vendor/knowledge/extra.md'),
                           ('.cache/knowledge', '.cache/knowledge/extra.md')]:
            with self.subTest(wiki=wiki, page=page):
                MountFixture.setUp(self)
                shutil.rmtree(self.root / 'modules')
                self.cfg.pop('mounts')
                index = 'wiki/README.md' if wiki == '.' else wiki + '/README.md'
                self.cfg.update(wikiDir=wiki, routerFile=index, historyDir='logs')
                self.write(index, '# Router\n')
                self.write(page, '# Unmapped\n')
                # Naming an indexed page preserves legacy built-in exemptions;
                # it does not impose the new mounted wiki-membership contract.
                self.write('wiki/guide.md', '# Guide\nLocal.\n' + page + '\n')
                for indexed in [[], [page]]:
                    with self.subTest(indexed=indexed):
                        self.cfg['indexed'] = indexed
                        self.write('wiki/ai-context.json', json.dumps(self.cfg))
                        result = self.cli('check')
                        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                        self.assertTrue(result.stdout.endswith('\nok\n'), result.stdout)
                self.write(page, '# Unmapped\n[Missing](missing.md)\n')
                self.cfg['topics']['guide']['sources'].append({'path': page})
                self.write('wiki/ai-context.json', json.dumps(self.cfg))
                self.assert_failure(self.cli('check'), f"FAIL {page}:2: relative link 'missing.md'")


class MountInventoryPolicyTests(MountFixture):
    wiki_layouts = [('.', 'vendor/extra.md'), ('knowledge', 'knowledge/vendor/extra.md'),
                    ('.knowledge', '.knowledge/extra.md'), ('vendor', 'vendor/extra.md'),
                    ('vendor/knowledge', 'vendor/knowledge/extra.md'),
                    ('.cache/knowledge', '.cache/knowledge/extra.md')]

    def wiki_case(self, wiki, page):
        MountFixture.setUp(self)
        self.sibling()
        index = 'wiki/README.md' if wiki in ('.', './', 'absolute') else wiki + '/README.md'
        self.inner_cfg.update(wikiDir=str(self.module_root) if wiki == 'absolute' else wiki,
                              routerFile=index, historyDir='logs', skipDirs=['*'])
        self.write(str(self.module_root / index), '# Router\n')
        self.write(str(self.module_root / page), '# Unmapped\n')
        self.save_configs()

    def test_history_directory_alias_keeps_lexical_index(self):
        self.sibling()
        self.write('modules/kb-core/logs/log.md', '# Log\n')
        self.symlink(self.module_root / 'wiki/history', self.module_root / 'logs', directory=True)
        roots = ['modules/kb-core']
        if (self.root / 'Modules/KB-Core').exists():
            roots.append('Modules/KB-Core')
        for spelling in roots:
            self.cfg['mounts']['kb']['root'] = spelling
            for history in ['wiki/history', 'wiki\\history', str(self.module_root / 'wiki/history')]:
                with self.subTest(historyDir=history):
                    self.inner_cfg['historyDir'] = history
                    self.save_configs()
                    for reference in ['[Log](history/log.md)', '[Log](../logs/log.md)', 'logs/log.md']:
                        with self.subTest(stage='valid-index', reference=reference):
                            self.write('modules/kb-core/wiki/README.md', '# Router\n' + reference + '\n')
                            result = self.cli('check')
                            self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                            self.assertTrue(result.stdout.endswith('\nok\n'), result.stdout)
                    self.write('modules/kb-core/wiki/README.md', '# Router\n')
                    with self.subTest(stage='unindexed-negative'):
                        result = self.cli('check')
                        index = os.path.normcase('wiki/README.md').replace(os.sep, '/')
                        self.assert_failure(result, 'FAIL mount kb: logs/log.md: history file not indexed in ' + index)
                        self.assertIn('other/guide', result.stdout)
                        self.assertTrue(result.stdout.endswith('1 root(s) failed\n'), result.stdout)
                    self.write('modules/kb-core/wiki/README.md',
                               '# Router\n[Log](history/log.md)\n[Missing](history/missing.md)\n')
                    with self.subTest(stage='lexical-link-negative'):
                        result = self.cli('check')
                        self.assert_failure(result, "FAIL mount kb: wiki/README.md:3: relative link 'history/missing.md'")
                        self.assertNotIn('history file not indexed', result.stdout)

    def test_mounted_wiki_overrides_builtin_directory_pruning(self):
        layouts = self.wiki_layouts + [('.', name + '/extra.md') for name in
                                      ['node_modules', 'dist', 'build', 'target', '.venv', '.drafts']]
        layouts += [(spelling, 'notes/extra.md') for spelling in ['.', './', 'absolute']]
        for wiki, page in layouts:
            with self.subTest(wiki=wiki, page=page):
                self.wiki_case(wiki, page)
                if page == 'notes/extra.md':
                    self.inner_cfg['skipDirs'] = ['notes']
                    self.save_configs()
                    with self.subTest(stage='clean'):
                        (self.module_root / page).unlink()
                        result = self.cli('check')
                        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                        self.write(str(self.module_root / page), '# Unmapped\n')
                result = self.cli('check')
                self.assert_failure(result, f'FAIL mount kb: {page}: wiki page no topic loads')
                if (wiki, page) == self.wiki_layouts[0]:
                    self.assertIn('other/guide', result.stdout)
                    self.assertTrue(result.stdout.endswith('1 root(s) failed\n'), result.stdout)
                if (wiki, page) not in self.wiki_layouts and page != 'notes/extra.md':
                    continue  # Other builtin names exercise the same pruning gate.
                if (wiki, page) in self.wiki_layouts:
                    self.inner_cfg['indexed'] = [page]
                    self.save_configs()
                    with self.subTest(stage='indexed-and-orphan'):
                        result = self.cli('check')
                        self.assert_failure(result, f'FAIL mount kb: {page}: indexed page not named',
                                            f'FAIL mount kb: {page}: wiki page no topic loads')
                    self.write('modules/kb-core/wiki/guide.md', '# Guide\nModule.\n' + page + '\n')
                    with self.subTest(stage='named-still-unrouted'):
                        result = self.cli('check')
                        self.assert_failure(result, f'FAIL mount kb: {page}: wiki page no topic loads')
                        self.assertNotIn('indexed page not named', result.stdout)
                self.inner_cfg['unrouted'] = {page: 'Deliberate wiki exception'}
                self.save_configs()
                with self.subTest(stage='excepted'):
                    result = self.cli('check')
                    self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
                self.inner_cfg.pop('unrouted')
                self.inner_cfg['topics']['guide']['sources'].append({'path': page})
                self.save_configs()
                with self.subTest(stage='routed'):
                    result = self.cli('check')
                    self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)

        # One representative link lifecycle: parsing belongs to LinkCheckTests,
        # but mounted ownership must carry this page through every inventory.
        self.wiki_case('.', 'notes/extra.md')
        self.inner_cfg.update(skipDirs=['notes'], indexed=['notes/*.md'])
        self.write('modules/kb-core/notes/extra.md', '# Extra\n[gone](missing.md)\n')
        self.save_configs()
        with self.subTest(stage='indexed-orphan-and-link'):
            self.assert_failure(self.cli('check'), 'FAIL mount kb: notes/extra.md: indexed page not named',
                                'FAIL mount kb: notes/extra.md: wiki page no topic loads',
                                "FAIL mount kb: notes/extra.md:2: relative link 'missing.md'")
        self.inner_cfg['topics']['guide']['sources'].append({'path': 'notes/extra.md'})
        self.save_configs()
        with self.subTest(stage='routed-link-still-fails'):
            self.assert_failure(self.cli('check'), "FAIL mount kb: notes/extra.md:2: relative link 'missing.md'")
        self.write('modules/kb-core/notes/missing.md', '# Target\n')
        self.inner_cfg['topics']['guide']['sources'].append({'path': 'notes/missing.md'})
        self.save_configs()
        with self.subTest(stage='routed-link-repaired'):
            result = self.cli('check')
            self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)

        self.wiki_case('wiki', 'wiki/guide.md')
        self.inner_cfg.update(skipDirs=['notes'], indexed=['notes/*.md'])
        for name in ['extra.md', 'AGENTS.md']:
            self.write('modules/kb-core/notes/' + name, '# Copy\n[gone](missing.md)\n')
        self.save_configs()
        with self.subTest(stage='nonwiki-explicit-skip'):
            result = self.cli('check')
            self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.inner_cfg['topics']['guide']['sources'].append({'path': 'notes/extra.md'})
        self.save_configs()
        with self.subTest(stage='nonwiki-explicit-route'):
            self.assert_failure(self.cli('check'), "FAIL mount kb: notes/extra.md:2: relative link 'missing.md'")
        self.inner_cfg['topics']['guide']['sources'].pop()
        self.inner_cfg['skipDirs'] = []
        self.save_configs()
        with self.subTest(stage='nonwiki-unskipped'):
            self.assert_failure(self.cli('check'), 'FAIL mount kb: notes/extra.md: indexed page not named',
                                'FAIL mount kb: notes/AGENTS.md: scoped instructions no topic loads',
                                "FAIL mount kb: notes/extra.md:2: relative link 'missing.md'")

        self.wiki_case('knowledge', 'knowledge/guide.md')
        self.inner_cfg['topics']['guide']['sources'].append({'path': 'knowledge/guide.md'})
        self.write('modules/kb-core/vendor/AGENTS.md', '# Unowned generated instructions\n')
        self.write('modules/kb-core/.git/internal/AGENTS.md', '# Metadata\n')
        self.inner_cfg['skipDirs'] = []
        self.save_configs()
        with self.subTest(stage='nonwiki-builtin-and-git'):
            result = self.cli('check')
            self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout)
        self.inner_cfg['topics']['guide']['sources'].append({'path': 'vendor/AGENTS.md'})
        self.write('modules/kb-core/vendor/AGENTS.md', '# Generated\n[Missing](missing.md)\n')
        self.save_configs()
        with self.subTest(stage='nonwiki-builtin-explicit-route'):
            self.assert_failure(self.cli('check'), "FAIL mount kb: vendor/AGENTS.md:2: relative link 'missing.md'")


if __name__ == '__main__':
    unittest.main()
