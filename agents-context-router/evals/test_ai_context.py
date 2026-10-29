"""Combined CLI regressions for indexing, shared installs, and relative links."""
from contextlib import redirect_stdout
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / 'scripts/ai-context.py'
PAGE = 'projects/api/deploy-runbook.md'
spec = importlib.util.spec_from_file_location('ai_context', SCRIPT)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'scripts/ai-context.py'
        self.script.parent.mkdir()
        shutil.copy2(SKILL / 'scripts/ai-context.py', self.script)
        self.write('AGENTS.md', '`guide`\n')
        self.write('wiki/README.md', 'wiki/README.md\n')
        self.write('wiki/guide.md', '# Guide\nUse this guide.\n')
        self.write(PAGE, '# Deploy\nRun deployment.\n')
        self.cfg = {'topics': {'guide': {
            'description': 'Guide', 'sources': [{'path': 'wiki/guide.md'}]}},
            'indexed': ['projects/*/*-runbook.md']}

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding='utf-8')

    def run_cli(self, *args):
        self.write('wiki/ai-context.json', json.dumps(self.cfg))
        env = {k: v for k, v in os.environ.items()
               if k not in ('AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG')}
        return subprocess.run([sys.executable, str(self.script), *args],
                              env=env, capture_output=True, encoding='utf-8')

    def check(self, code):
        result = self.run_cli('check')
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_indexed_opt_in(self):
        for patterns, code in [(None, 0), ([], 0), (['projects/*/*-runbook.md'], 1)]:
            with self.subTest(patterns=patterns):
                self.cfg.pop('indexed', None)
                if patterns is not None:
                    self.cfg['indexed'] = patterns
                output = self.check(code)
                if code:
                    self.assertIn('FAIL ' + PAGE, output)
                    for remedy in ['name it in a topic page', 'route it', '"unrouted" with a reason']:
                        self.assertIn(remedy, output)
        self.write('AGENTS.md', f'`guide`\n{PAGE}\n')
        renamed = 'projects/api/new-runbook.md'
        (self.root / PAGE).rename(self.root / renamed)
        self.assertIn('FAIL ' + renamed, self.check(1))

    def test_indexed_references(self):
        for surface in ['root', 'router', 'topic', 'section', 'source', 'source-section', 'basename', 'relative', 'relative-full']:
            with self.subTest(surface=surface):
                self.write('AGENTS.md', '`guide`\n' + (PAGE if surface == 'root' else ''))
                self.cfg['routerFile'] = 'docs/router.md'
                (self.root / 'wiki/README.md').unlink(missing_ok=True)
                self.write('docs/router.md', PAGE if surface == 'router' else '')
                self.write('wiki/guide.md', '# Guide\n' + (
                    'deploy-runbook.md' if surface == 'basename' else
                    f'[Deploy](../{PAGE})' if surface == 'relative-full' else
                    PAGE if surface in ['topic', 'section'] else 'Use this guide.'))
                sources = [{'path': 'wiki/guide.md'}]
                if surface == 'section':
                    sources[0]['heading'] = 'Guide'
                if surface == 'relative':
                    self.write('projects/api/topic.md', '[Deploy](./deploy-runbook.md)')
                    sources.append({'path': 'projects/api/topic.md'})
                if surface in ['source', 'source-section']:
                    sources.append({'path': PAGE})
                    if surface == 'source-section':
                        sources[-1]['heading'] = 'Deploy'
                self.cfg['topics']['guide']['sources'] = sources
                self.check(1 if surface in ['basename', 'relative'] else 0)

    def test_selected_heading_only(self):
        self.cfg['topics']['guide']['sources'][0]['heading'] = 'Selected'
        for selected, other, code in [('Read this.', PAGE, 1), (PAGE, 'Read this.', 0)]:
            with self.subTest(code=code):
                self.write('wiki/guide.md', f'# Guide\n## Selected\n{selected}\n## Other\n{other}\n')
                self.check(code)

    def test_exact_unrouted_reason(self):
        for exceptions, code in [({}, 1), ({PAGE: ''}, 1), ({PAGE: ' \t\n'}, 1),
                                 ({PAGE: None}, 1), ({PAGE: 'Human only'}, 0),
                                 ({PAGE.replace('/', '\\'): 'Human only'}, 0),
                                 ({'projects/*/*.md': 'Human only'}, 0)]:
            with self.subTest(exceptions=exceptions):
                self.cfg['unrouted'] = exceptions
                self.check(code)

    def test_unrouted_globs_and_indexed_overlap(self):
        for path in [PAGE, 'wiki/extra.md', 'wiki/history/log.md',
                     'pkg/AGENTS.md', 'vendor/api/runbook.md']:
            self.write(path, '# Deliberate exception\n')
            self.cfg['indexed'] = [path]
            pattern = path.split('/')[0] + '/*'
            for reason in ['Human only', '', ' \t\n', None, 123]:
                with self.subTest(path=path, reason=reason):
                    self.cfg['unrouted'] = {pattern: reason}
                    output = self.check(0 if reason == 'Human only' else 1)
                    if reason != 'Human only':
                        self.assertIn('FAIL ' + path + ': indexed page not named', output)
                        self.assertIn('1 problem(s)', output)
            if path != PAGE:
                (self.root / path).unlink()
        self.cfg['indexed'] = ['projects/*/*-runbook.md']
        for exceptions, code in [
                ({'projects\\*\\*.md': 'Human only'}, 0),
                ({PAGE: '', 'projects/*': 'Human only'}, 0),
                ({PAGE: 'Human only', 'projects/*': ''}, 0),
                ({'PROJECTS/*': 'Human only'}, 1),
                ({'other/*': 'Human only'}, 1)]:
            with self.subTest(exceptions=exceptions):
                self.cfg['unrouted'] = exceptions
                self.check(code)

    def test_indexed_matching(self):
        self.cfg['indexed'] = ['projects/*/*-runbook.md', '**/*.md', '*.txt']
        self.write('projects/api/readme.txt', 'Not Markdown.\n')
        output = self.check(1)
        self.assertEqual(output.count('FAIL ' + PAGE + ':'), 1)
        self.assertIn('1 problem(s)', output)
        if os.name == 'posix':
            self.cfg['indexed'] = ['PROJECTS/*.md']
            self.check(0)

    def test_indexed_traversal_preserves_legacy_scope(self):
        self.write('.git/internal/runbook.md', 'Git metadata.\n')
        for prefix in ['.internal', 'vendor', 'build']:
            with self.subTest(prefix=prefix):
                page = f'{prefix}/api/deploy-runbook.md'
                for path in [page, f'{prefix}/AGENTS.md', f'{prefix}/wiki/extra.md',
                             f'{prefix}/wiki/history/m1.md']:
                    self.write(path, '# Extra\n')
                self.cfg.update(wikiDir=f'{prefix}/wiki', historyDir=f'{prefix}/wiki/history')
                self.write(f'{prefix}/wiki/README.md', f'{prefix}/wiki/README.md\n')
                self.write('AGENTS.md', '`guide`\n')
                self.cfg.pop('indexed', None)
                self.check(0)
                self.cfg['indexed'] = []
                self.check(0)
                self.cfg['indexed'] = [f'{prefix}/api/*-runbook.md', '.git/**/*.md']
                output = self.check(1)
                self.assertIn('FAIL ' + page, output)
                self.assertIn('1 problem(s)', output)
                self.write('AGENTS.md', f'`guide`\n{page}\n')
                self.check(0)

    def test_indexed_walk_skips_directories_no_pattern_can_reach(self):
        hidden = 'projects/.drafts/api/deploy-runbook.md'
        for path in [hidden, '.cache/projects/old-runbook.md', 'node_modules/pkg/notes-runbook.md']:
            self.write(path, '# Runbook\n')
        self.cfg['indexed'] = ['projects/*-runbook.md']
        self.write('wiki/ai-context.json', json.dumps(self.cfg))
        visited, real_walk = [], os.walk

        def walk(top, *args, **kwargs):
            for entry in real_walk(top, *args, **kwargs):
                visited.append(os.path.relpath(entry[0], os.path.realpath(self.root)).replace(os.sep, '/'))
                yield entry

        with patch.dict(os.environ, {'AI_CONTEXT_ROOT': str(self.root)}):
            router = runpy.run_path(str(self.script))
            with patch('os.walk', walk), redirect_stdout(io.StringIO()) as output:
                status = router['check'](router['load_cfg']())
        self.assertEqual(status, 1, output.getvalue())
        for page in [PAGE, hidden]:
            self.assertIn('FAIL ' + page + ': indexed page not named', output.getvalue())
        self.assertIn('2 problem(s)', output.getvalue())
        self.assertIn('projects/.drafts/api', visited)
        self.assertEqual([d for d in visited if d.split('/')[0] in ('.cache', 'node_modules')], [])

    def test_skip_dirs(self):
        self.write('AGENTS.md', f'`guide`\n{PAGE}\n')
        dump = 'projects/api/artifacts/run'
        for path in [f'{dump}/AGENTS.md', f'{dump}/old-runbook.md']:
            self.write(path, '# Copy\n[gone](missing.md)\n')
        output = self.check(1)
        for path in [f'{dump}/AGENTS.md: scoped', f'{dump}/old-runbook.md: indexed', f'{dump}/old-runbook.md:2']:
            self.assertIn('FAIL ' + path, output)
        for value in [['projects/*/artifacts'], ['projects/api/artifacts/'], ['projects\\api\\artifacts']]:
            with self.subTest(skipDirs=value):
                self.cfg['skipDirs'] = value
                self.check(0)
        visited, real_walk = [], os.walk

        def walk(top, *args, **kwargs):
            for entry in real_walk(top, *args, **kwargs):
                visited.append(os.path.relpath(entry[0], os.path.realpath(self.root)).replace(os.sep, '/'))
                yield entry

        self.write('wiki/ai-context.json', json.dumps(self.cfg))
        with patch.dict(os.environ, {'AI_CONTEXT_ROOT': str(self.root)}):
            router = runpy.run_path(str(self.script))
            with patch('os.walk', walk), redirect_stdout(io.StringIO()):
                router['check'](router['load_cfg']())
        self.assertIn('projects/api', visited)
        self.assertEqual([d for d in visited if 'artifacts' in d], [])

    def test_skip_dirs_never_skip_the_wiki(self):
        self.write('AGENTS.md', f'`guide`\n{PAGE}\n')
        self.write('wiki/notes/unmapped.md', '# Unmapped\n')
        for value in [['wiki'], ['wiki/notes'], ['*']]:
            with self.subTest(skipDirs=value):
                self.cfg['skipDirs'] = value
                self.assertIn('FAIL wiki/notes/unmapped.md: wiki page no topic loads', self.check(1))

    def test_skip_dirs_keep_the_path_to_a_nested_wiki(self):
        self.cfg.update(wikiDir='docs/wiki', routerFile='docs/wiki/README.md')
        self.cfg['topics']['guide']['sources'] = [{'path': 'docs/wiki/guide.md'}]
        self.write('docs/wiki/README.md', 'docs/wiki/README.md\n')
        self.write('docs/wiki/guide.md', '# Guide\nUse this guide.\n')
        self.write('docs/wiki/unmapped.md', '# Unmapped\n')
        self.write('docs/other/AGENTS.md', '# Other\n')
        self.write('AGENTS.md', f'`guide`\n{PAGE}\n')
        for value in [['docs'], ['*'], ['docs/*']]:
            with self.subTest(skipDirs=value):
                self.cfg['skipDirs'] = value
                output = self.check(1)
                self.assertIn('FAIL docs/wiki/unmapped.md: wiki page no topic loads', output)
                self.assertNotIn('docs/other/AGENTS.md', output)

    def test_invalid_skip_dirs(self):
        for value in ['projects/*/artifacts', [1], {'projects': 'x'}]:
            with self.subTest(value=value):
                self.cfg['skipDirs'] = value
                self.assertIn('FAIL skipDirs: expected a list of strings', self.check(1))

    def test_skip_dirs_only_traverse_wiki_ancestors(self):
        self.cfg.update(wikiDir='docs/wiki', routerFile='docs/wiki/README.md')
        sources = [{'path': 'docs/wiki/guide.md'}]
        self.cfg['topics']['guide']['sources'] = sources
        self.write('docs/wiki/README.md', 'docs/wiki/README.md\n')
        self.write('docs/wiki/guide.md', '# Guide\nUse this guide.\n')
        self.write('docs/AGENTS.md', '# Generated instructions\n')
        self.write('docs/dump.md', '# Evidence\n[gone](missing.md)\n')
        for skip in ['docs', '*']:
            for indexed in [[], ['docs/*.md']]:
                with self.subTest(skipDirs=skip, indexed=indexed):
                    self.cfg.update(skipDirs=[skip], indexed=indexed)
                    self.check(0)
                    sources.append({'path': 'docs/dump.md'})
                    self.assertIn('FAIL docs/dump.md:2:', self.check(1))
                    sources.pop()

    def test_invalid_indexed(self):
        for value in ['projects/*.md', None, [123], {'projects/*.md': True}]:
            with self.subTest(value=value):
                self.cfg['indexed'] = value
                self.assertIn('FAIL indexed: expected a list of strings', self.check(1))

    def test_existing_orphan_rules(self):
        for path, detail in [('wiki/extra.md', 'wiki page no topic loads'),
                             ('wiki/history/m1.md', 'history file not indexed'),
                             ('pkg/AGENTS.md', 'scoped instructions no topic loads')]:
            with self.subTest(path=path):
                self.write(path, '# Extra\n')
                self.write('AGENTS.md', f'`guide`\n{PAGE}\n{path}\n')
                self.cfg['indexed'] = ['**/*.md']
                self.cfg['unrouted'] = {}
                self.assertIn(f'FAIL {path}: {detail}', self.check(1))
                # Legacy exact exceptions still permit empty reasons when not indexed.
                self.cfg['indexed'] = ['projects/*.md']
                self.cfg['unrouted'] = {path: ''}
                self.check(0)
                (self.root / path).unlink()

    def test_render_errors_survive(self):
        for text, heading, detail in [(None, None, 'No such file'),
                                      ('# Guide\n', 'Absent', "heading 'Absent' found 0x"),
                                      ('# Guide\n# Guide\n', 'Guide', "heading 'Guide' found 2x")]:
            with self.subTest(detail=detail):
                source = {'path': 'wiki/guide.md'}
                if text is None:
                    (self.root / source['path']).unlink()
                else:
                    self.write(source['path'], text)
                    source['heading'] = heading
                self.cfg['topics']['guide']['sources'] = [source]
                output = self.check(1)
                self.assertIn('FAIL guide:', output)
                self.assertIn(detail, output)
                self.assertIn('FAIL ' + PAGE, output)

    def test_existing_commands_and_fixture(self):
        for args, expected in [(('list',), 'guide              Guide\n'),
                               (('guide',), '<!-- wiki/guide.md -->\n# Guide\nUse this guide.\n')]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, ''))
        fixture = self.root / 'fixture'
        shutil.copytree(SKILL / 'evals/fixtures/routed', fixture)
        shutil.copy2(SKILL / 'scripts/ai-context.py', fixture / 'scripts/ai-context.py')
        result = subprocess.run([sys.executable, str(fixture / 'scripts/ai-context.py'), 'check'],
                                env={k: v for k, v in os.environ.items()
                                     if k not in ('AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG')},
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.endswith('ok\n'), result.stdout)
        self.assertEqual(result.stderr, '')


class LinkCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.write('scripts/ai-context.py', SCRIPT.read_text(encoding='utf-8'))
        self.write('AGENTS.md', '`guide`\n')
        self.write('wiki/README.md', 'history/log.md\n')
        self.cfg = {'topics': {'guide': {'description': 'Guide', 'sources': [
            {'path': 'wiki/guide.md', 'heading': 'Selected'}]}}}
        self.write('wiki/guide.md', '# Selected\nHello\n')
        self.save_cfg()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def save_cfg(self):
        self.write('wiki/ai-context.json', json.dumps(self.cfg))

    def cli(self, *args):
        env = {k: v for k, v in os.environ.items()
               if k not in ('AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG')}
        return subprocess.run([sys.executable, str(self.root / 'scripts/ai-context.py'),
                               *args], env=env, capture_output=True, text=True, encoding='utf-8')

    def problems(self, text):
        self.write('wiki/guide.md', '# Selected\n' + text)
        old_root = router.ROOT
        try:
            router.ROOT = str(self.root)
            return router.link_problems(self.cfg)
        finally:
            router.ROOT = old_root

    def test_cli_missing_link_outside_selected_heading(self):
        self.write('wiki/guide.md', '# Selected\nHello\n# Other\n[Retry](../notes/renamed.md)\n')
        result = self.cli('check')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('wiki/guide.md:4:', result.stdout)
        self.assertIn('../notes/renamed.md', result.stdout)
        self.assertEqual(self.cli('guide').stdout,
                         '<!-- wiki/guide.md § Selected -->\n# Selected\nHello\n')

    def test_diagnostic_paths_use_forward_slashes(self):
        native_relpath = os.path.relpath
        def windows_relpath(*args):
            return native_relpath(*args).replace('/', '\\')
        with patch.object(os.path, 'relpath', side_effect=windows_relpath), patch.object(os, 'sep', '\\'):
            errors = self.problems('[Link](missing.md)')
        self.assertEqual(len(errors), 1, errors)
        self.assertTrue(errors[0].startswith('wiki/guide.md:2:'), errors)

    def test_indexed_pages_are_link_checked(self):
        page = 'projects/api/deploy-runbook.md'
        self.cfg['indexed'] = ['projects/*/*-runbook.md']
        self.write('AGENTS.md', f'`guide`\n{page}\n')
        self.write(page, '[Runbook link](missing.md)\n')
        self.save_cfg()
        result = self.cli('check')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f'{page}:1: relative link', result.stdout)

        self.write('projects/api/missing.md', 'Target exists.\n')
        result = self.cli('check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inline_destinations_and_titles(self):
        for whitespace in [' ', '\t', '\n']:
            text = '[x](a' + '\\' + whitespace + 'b)'
            with self.subTest(whitespace=repr(whitespace)):
                self.assertEqual(self.problems(text), [])
        for raw in ['a<b', 'a' + '\\' + 'zb']:
            with self.subTest(destination=raw):
                self.assertEqual(list(router.link_destinations(['[x](' + raw + ')'])), [(1, raw)])
                self.assertEqual(router.markdown_unescape(raw), raw)
        for title in ['"title"', "'title'", '(title)']:
            text = '[x](<target.txt>' + title + ')'
            self.write('wiki/target.txt', '')
            self.assertEqual(self.problems(text), [])
            (self.root / 'wiki/target.txt').unlink()
            self.assertEqual(self.problems(text), [])
            for separator in [' ', '\t', '\n']:
                live = '[x](<target.txt>' + separator + title + ')'
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(live), [])
                (self.root / 'wiki/target.txt').unlink()
                self.assertEqual(len(self.problems(live)), 1)
        self.assertEqual(self.problems('[x]() [x](<>) [x](<> "")'), [])
        self.assertEqual(len(self.problems('[x](<target.txt>)')), 1)
        for destination in ['a(b).md', r'a\(b\).md', '<space name.md>',
                            'a(b).md "title"', "a(b).md 'title'", 'a(b).md (title)']:
            for mark in ['[link]', '![image]']:
                with self.subTest(destination=destination, mark=mark):
                    name = 'space name.md' if destination.startswith('<') else 'a(b).md'
                    self.write('wiki/' + name, '')
                    self.assertEqual(self.problems(mark + '(' + destination + ')'), [])
                    (self.root / 'wiki' / name).unlink()
                    self.assertEqual(len(self.problems(mark + '(' + destination + ')')), 1)
        self.assertEqual(len(self.problems('[label](missing(a).md "title")')), 1)
        self.assertEqual(len(self.problems('![label](<missing file.png>)')), 1)

        self.write('wiki/neighbor.txt', '')
        text = '[x](file<!--name.txt) and [n](neighbor.txt)'
        self.assertEqual(list(router.link_destinations([text])),
                         [(1, 'file<!--name.txt'), (1, 'neighbor.txt')])
        cases = [('[](target.txt)', 'target.txt'), ('![](target.txt)', 'target.txt'),
                 ('[x](<target`name.txt>) and `example` [n](neighbor.txt)', 'target`name.txt'),
                 ('[x](<target[bracket].txt>) `sample`', 'target[bracket].txt')]
        for text, name in cases:
            with self.subTest(text=text):
                self.write('wiki/' + name, '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki' / name).unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:2:', errors[0])
                self.assertIn(name, errors[0])
                self.write('wiki/' + name, '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki' / name).unlink()

        cases = ['[Read **[the guide]**](target.md)', '[guide](\ntarget.md)',
                 '[multi\nline](target.md\n "title")', '![alt [nested]](<target.md>)',
                 '[guide](\n<target.md>\n)']
        for text in cases:
            with self.subTest(text=text):
                self.write('wiki/target.md', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.md').unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:2:', errors[0])
                self.assertIn('target.md', errors[0])
        self.assertEqual(self.problems('[x](\n\nmissing.md)'), [])

    def test_used_references_report_definition_once(self):
        for whitespace in [' ', '\t']:
            text = '[id]: a' + '\\' + whitespace + 'b\n\n[id]'
            self.assertEqual(self.problems(text), [], text)
        text = '[id]: a' + '\\' + '\nb\n\n[id]'
        self.assertEqual(list(router.link_destinations(text.split('\n'))), [(1, 'a' + '\\')])
        for title in ['"title"', "'title'", '(title)']:
            text = '[x]: <target.txt>' + title + '\n\n[x]'
            self.write('wiki/target.txt', '')
            self.assertEqual(self.problems(text), [])
            (self.root / 'wiki/target.txt').unlink()
            self.assertEqual(self.problems(text), [])
            for separator in [' ', '\t', '\n']:
                live = '[x]: <target.txt>' + separator + title + '\n\n[x]'
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(live), [])
                (self.root / 'wiki/target.txt').unlink()
                self.assertEqual(len(self.problems(live)), 1)
        self.assertEqual(self.problems('[x]: <> ""\n\n[x]'), [])
        self.assertEqual(len(self.problems('[x]: <target.txt>\n\n[x]')), 1)
        for slashes, matched in [(1, True), (2, False), (3, True)]:
            label = '[foo' + '\\' * slashes + ']\nbar]'
            text = label + ': target.txt\n\n' + label
            with self.subTest(slashes=slashes):
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), int(matched), errors)
                if matched:
                    self.assertIn('wiki/guide.md:2:', errors[0])
        text = '[Full][ Some ID ]\n![Some ID][]\n[Some ID]\n\n[some id]: <missing file.md> "title"\n'
        errors = self.problems(text)
        self.assertEqual(len(errors), 1)
        self.assertIn('wiki/guide.md:6:', errors[0])
        self.assertIn('missing file.md', errors[0])
        for usage in ['[x][id]', '[id][]', '[id]', '![id]']:
            with self.subTest(usage=usage):
                self.assertEqual(len(self.problems('[id]: missing.md\n' + usage)), 1)
        self.assertEqual(self.problems('[unused]: missing.md\n[undefined]\n'), [])
        self.write('wiki/good.md', '')
        self.assertEqual(self.problems('[id]\n\n[id]: good.md\n[id]: missing.md'), [])
        self.assertEqual(len(self.problems(r'[a\*b]' + '\n\n[a*b]: missing.md')), 0)

        for text, line in [('[x][id]\n\n[id]:\n  target.md', 4),
                           ('[x][multi\n id]\n\n[multi id]: target.md "title"', 5)]:
            with self.subTest(text=text):
                self.write('wiki/target.md', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.md').unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:' + str(line) + ':', errors[0])
                self.assertIn('target.md', errors[0])
        self.assertEqual(self.problems('[id]:\n\nmissing.md'), [])

        for text in ['- item\n  - [id]: target.txt\n\n    [id]',
                     '> - item\n>   - [id]: target.txt\n>\n>     [id]']:
            with self.subTest(text=text):
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:3:', errors[0])

        for label, use, matches in [(r'foo\!', 'foo!', False), (r'foo\!', r'foo\!', True),
                                    ('a&amp;b', 'a&b', False), ('a&amp;b', 'a&amp;b', True),
                                    ('a\u00a0b', 'a b', False), ('A\t B', 'a b', True)]:
            with self.subTest(label=label, use=use):
                errors = self.problems('[' + label + ']: missing.md\n\n[' + use + ']')
                self.assertEqual(len(errors), int(matches))

        boundaries = ['Title\n=====', 'Title\n---', '---', '***', '_ _ _', '* * *',
                      '  # Heading', '#', '```\ncode\n```', '    code\n',
                      '<div>\nbody\n</div>\n', '> quote\n']
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                text = boundary + '\n[id]: target.txt\n\n[id]'
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                self.assertEqual(len(self.problems(text)), 1)

        text = '- [id]:\n\ttarget.txt\n\n  [id]'
        self.write('wiki/target.txt', '')
        self.assertEqual(self.problems(text), [])
        (self.root / 'wiki/target.txt').unlink()
        errors = self.problems(text)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guide.md:2:', errors[0])

        text = '[id]: existing.md "unfinished\n# Heading\n[broken](missing.md)\nend"\n\n[id]'
        self.write('wiki/existing.md', '')
        errors = self.problems(text)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guide.md:4:', errors[0])
        self.assertIn('missing.md', errors[0])
        for title in ['""', "''", '()', '"first\nend' + '\\' + '"\nlast"',
                      '"first\nend' + '\\' * 2 + '"']:
            text = '[id]: target.txt ' + title + '\n\n[id]'
            self.write('wiki/target.txt', '')
            self.assertEqual(self.problems(text), [])
            (self.root / 'wiki/target.txt').unlink()
            self.assertEqual(len(self.problems(text)), 1)
        for title in ['"first\nsecond"', "'first\nsecond'", '(first\nsecond)']:
            text = '[id]: target.txt ' + title + '\n\n[id]'
            self.write('wiki/target.txt', '')
            self.assertEqual(self.problems(text), [])
            (self.root / 'wiki/target.txt').unlink()
            self.assertEqual(len(self.problems(text)), 1)
        self.assertEqual(self.problems('paragraph\n[id]: missing.md\n\n[id]'), [])
        for text in ['\n[id]: missing.md\n[id]', '# Heading\n[id]: missing.md\n[id]',
                     '- [id]: missing.md\n\n  [id]', '[id]:\n  missing.md\n[id]', '[id]:\n  ```\n[id]',
                     '[id]: missing.md\n "title"\n[id]',
                     '[one]: good.txt\n[two]: missing.md\n[two]']:
            with self.subTest(text=text):
                self.assertEqual(len(self.problems(text)), 1)
        self.assertEqual(self.problems('[id]: good.txt\nparagraph\n[other]: missing.md\n\n[other]'), [])
        for text in ['[id]:\n  good.txt\n[live](missing.md)',
                     '[id]: good.txt\n "title"\n[live](missing.md)']:
            errors = self.problems(text)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('wiki/guide.md:4:', errors[0])
        errors = self.problems('[id]: good.txt\n[live](missing.md)')
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guide.md:3:', errors[0])

    def test_code_escapes_and_original_lines(self):
        text = ('```md\n[x](missing.md)\n```\n~~~\n[id]\n~~~\n'
                '`[x](missing.md)` and `` `[id]` ``\n'
                r'\[x](missing.md)' + '\n' + r'!\[x](missing.md)' + '\n'
                '[unused]: missing.md\n[id]: missing.md\n[live](missing.md)\n')
        errors = self.problems(text)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guide.md:13:', errors[0])
        self.assertEqual(self.problems('`example\n[x](missing.md)\n`'), [])
        self.assertEqual(len(self.problems('` unmatched [x](missing.md)')), 1)
        self.assertEqual(len(self.problems(r'\` [x](missing.md) `')), 1)

        text = '`unfinished\n\n[renamed](target.txt)\n\n`other\n'
        self.write('wiki/target.txt', '')
        self.assertEqual(self.problems(text), [])
        (self.root / 'wiki/target.txt').unlink()
        errors = self.problems(text)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guide.md:4:', errors[0])
        self.write('wiki/target.txt', '')
        self.assertEqual(self.problems(text), [])

        for mark in ['```', '~~~']:
            text = ('[before](missing.md)\n' + mark + '\n' + mark + 'not a closer\n'
                    '[example](missing.md)\n' + mark + '\n[after](missing.md)')
            errors = self.problems(text)
            self.assertEqual(len(errors), 2, errors)
            self.assertIn('wiki/guide.md:2:', errors[0])
            self.assertIn('wiki/guide.md:7:', errors[1])

        self.assertEqual(len(self.problems('```foo`bar\n[live](missing.md)')), 1)
        self.assertEqual(self.problems('~~~foo`bar\n[example](missing.md)'), [])

    def test_exclusions_and_url_decoding(self):
        for target in ['https://example.test/a', 'mailto:a@b.test', 'custom:thing',
                       '//example.test/a', '/absolute/path', '#heading', '?query', '']:
            with self.subTest(target=target):
                self.assertEqual(self.problems('[x](' + target + ')'), [])
        self.write('wiki/space #中文.md', '')
        self.assertEqual(self.problems('[x](space%20%23%E4%B8%AD%E6%96%87.md?q#h)'), [])
        self.assertEqual(len(self.problems('[x](missing.md?query#heading)')), 1)
        self.write('wiki/existing.md', '')
        self.assertEqual(self.problems('[x](existing.md#no-such-heading)'), [])

        for parts in ['a ', '#中', '(a', 'a)']:
            name = parts + '.md'
            target = self.root / 'wiki' / name
            target.write_text('', encoding='utf-8')
            text = '[generated](' + quote(name, safe='') + ')'
            with self.subTest(name=name):
                self.assertEqual(self.problems(text), [])
                target.unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1)
                self.assertIn('wiki/guide.md:2:', errors[0])
                self.assertIn(quote(name, safe=''), errors[0])

    def test_containment_and_file_targets(self):
        outside = self.root.parent / 'repo-lookalike'
        outside.mkdir()
        (outside / 'file.md').write_text('outside', encoding='utf-8')
        (self.root / 'escape').symlink_to(outside, target_is_directory=True)
        self.write('inside.md', '')
        (self.root / 'wiki' / 'inside.md').symlink_to(self.root / 'inside.md')
        self.assertEqual(self.problems('[x](../inside.md) [x](inside.md)'), [])
        for target in ['../wiki', '..', '../../repo-lookalike/file.md',
                       '%2e%2e/%2e%2e/repo-lookalike/file.md', '../escape/file.md', '%00.md']:
            with self.subTest(target=target):
                self.assertEqual(len(self.problems('[x](' + target + ')')), 1)

    def test_inventory_deduplicates_and_includes_unrouted_history_router(self):
        self.cfg['topics']['guide']['sources'].append({'path': 'wiki/guide.md'})
        self.cfg['unrouted'] = {'wiki/extra.md': 'human only'}
        self.write('wiki/extra.md', '[x](missing.md)')
        self.write('wiki/history/log.md', '[x](missing.md)')
        self.write('wiki/README.md', 'history/log.md\n[x](missing.md)')
        errors = self.problems('[x](missing.md)')
        self.assertEqual(len(errors), 4, errors)
        self.assertEqual({e.split(':')[0] for e in errors},
                         {'wiki/guide.md', 'wiki/extra.md', 'wiki/history/log.md', 'wiki/README.md'})
        self.cfg.update(wikiDir='docs', routerFile='INDEX.md')
        self.cfg['topics']['guide']['sources'] = [{'path': 'notes/source.txt'}]
        self.write('notes/source.txt', '[x](missing.md)')
        self.write('docs/extra.md', '[x](missing.md)')
        self.write('INDEX.md', '[x](missing.md)')
        errors = self.problems('hello')
        self.assertEqual({e.split(':')[0] for e in errors},
                         {'notes/source.txt', 'docs/extra.md', 'INDEX.md'})

        self.cfg['topics']['guide']['sources'] = [{'path': 'wiki/guide.md'},
                                                 {'path': str(self.root / 'wiki/guide.md')}]
        errors = self.problems('[x](missing.md)')
        self.assertEqual(sum('wiki/guide.md:2:' in e for e in errors), 1, errors)

    def test_context_masks_examples_but_keeps_live_continuations(self):
        for outer_indent in range(4):
            for outer_depth in range(1, 4):
                prefix = ' ' * outer_indent + '> ' * outer_depth
                text = (prefix + '- item\n' + prefix + '   > ```\n' + prefix +
                        '   > foo ``` [x](missing.md)\n' + prefix + '   > ```\n\n[live](live-missing.md)')
                with self.subTest(outer_indent=outer_indent, outer_depth=outer_depth):
                    errors = self.problems(text)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn('live-missing.md', errors[0])
        for padding, columns in [('\t', 4), ('\t ', 5), ('\t  ', 6), ('\t   ', 7)]:
            text = '- item\n' + padding + '> [live](target.txt)'
            self.assertEqual(len(self.problems(text)), 1, text)
            blank = '- item\n\n' + padding + '> [live](target.txt)'
            self.assertEqual(len(self.problems(blank)), int(columns < 6), blank)
        for spaces in range(2, 8):
            prefix = ' ' * spaces + '> '
            for quote in ['', '> ']:
                text = quote + '- item\n' + quote + prefix + '[live](target.txt)'
                with self.subTest(spaces=spaces, quote=quote):
                    self.write('wiki/target.txt', '')
                    self.assertEqual(self.problems(text), [])
                    (self.root / 'wiki/target.txt').unlink()
                    self.assertEqual(len(self.problems(text)), 1, text)
                    blank = quote + '- item\n' + quote.rstrip() + '\n' + quote + prefix + '[live](target.txt)'
                    self.assertEqual(len(self.problems(blank)), int(spaces < 6), blank)
                    if spaces >= 6:
                        continue
                    code = (quote + '- item\n' + quote + prefix + '```\n' + quote + prefix +
                            '[example](missing.md)\n' + quote + prefix + '```\n\n[live](live-missing.md)')
                    errors = self.problems(code)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn('live-missing.md', errors[0])
        for opening, continuation in [('-\t> ```', '\t> '), ('- > ```', '  > ')]:
            text = opening + '\n' + continuation + '[example](missing.md)\n' + continuation + '```\n\n[live](live-missing.md)'
            errors = self.problems(text)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('live-missing.md', errors[0])
        text = '- > [id]:\n  > target.txt\n  >\n  > [id]'
        self.write('wiki/target.txt', '')
        self.assertEqual(self.problems(text), [])
        (self.root / 'wiki/target.txt').unlink()
        self.assertEqual(len(self.problems(text)), 1)
        self.assertEqual(len(self.problems('- > note\n  > [live](missing.md)')), 1)
        self.assertEqual(len(self.problems('- > [x\n  > y](missing.md)')), 1)
        for continuation in ['  ', '> ']:
            text = '- > ```\n' + continuation + '[live](missing.md)'
            self.assertEqual(len(self.problems(text)), 1, text)
        for depth in range(1, 6):
            opening, continuation = '-\t> ' * depth, '\t> ' * depth
            text = opening + '```\n' + continuation + '[example](missing.md)\n' + continuation + '```\n\n[live](live-missing.md)'
            errors = self.problems(text)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('live-missing.md', errors[0])
        for depth in range(1, 6):
            for prefix in ['', '> ']:
                opening = prefix + '- > ' * depth + '```'
                continuation = prefix + '  > ' * depth
                text = opening + '\n' + continuation + '[example](missing.md)\n' + continuation + '```\n\n[live](live-missing.md)'
                with self.subTest(alternating_depth=depth, prefix=prefix):
                    errors = self.problems(text)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn('live-missing.md', errors[0])
                    self.assertIn('wiki/guide.md:6:', errors[0])
        for example in ['-\t- ```\n      [example](missing.md)\n      ```',
                        '-\t  - [example](missing.md)', '- - ***']:
            errors = self.problems(example + '\n\n[live](live-missing.md)')
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('live-missing.md', errors[0])
        self.assertEqual(len(self.problems('See [x\n2. - y](missing.md)')), 1)
        for depth in range(1, 6):
            for markers in itertools.product(['- ', '1. '], repeat=depth):
                indentation = ' ' * sum(map(len, markers))
                lines = [''.join(markers) + '```', indentation + '[example](missing.md)',
                         indentation + '```', '', '[live](live-missing.md)']
                for quoted in [False, True]:
                    sample = (['> ' + line for line in lines[:3]] + ['>', lines[-1]]
                              if quoted else lines)
                    with self.subTest(same_line=markers, quoted=quoted):
                        errors = self.problems('\n'.join(sample))
                        self.assertEqual(len(errors), 1, errors)
                        self.assertIn('wiki/guide.md:6:', errors[0])
                        self.assertIn('live-missing.md', errors[0])
        for digits, valid in [('0' * (length - 1) + '1', length <= 9) for length in range(1, 11)] + [('١', False)]:
            with self.subTest(digits=digits):
                text = 'See [the\n' + digits + '. guide](target.txt)'
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                self.assertEqual(len(self.problems(text)), int(not valid), text)
                sibling = '- [the\n' + digits + '. guide](target.txt)'
                self.assertEqual(len(self.problems(sibling)), int(not valid), sibling)
                block = digits + '. [live](target.txt)'
                self.assertEqual(len(self.problems(block)), 1, block)
        for first, sibling in [('+', '+'), ('*', '*'), ('1.', '1.'), ('1.', '2.')]:
            for padding in ['', ' ']:
                with self.subTest(first=first, sibling=sibling, padding=padding):
                    text = first + ' [x\n' + sibling + padding + '\ny](target.txt)\n\n[live](missing.md)'
                    errors = self.problems(text)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn('missing.md', errors[0])
                    text = 'See [x\n' + sibling + padding + '\ny](target.txt)'
                    self.write('wiki/target.txt', '')
                    self.assertEqual(self.problems(text), [])
                    (self.root / 'wiki/target.txt').unlink()
                    self.assertEqual(len(self.problems(text)), 1, text)
                    block = first + '\n' + ' ' * (len(first) + 1) + '[live](target.txt)'
                    self.assertEqual(len(self.problems(block)), 1, block)
        for start in [0, 1, 2, 10]:
            for quote in ['', '> ']:
                text = quote + 'See [the\n' + quote + str(start) + '. guide](target.txt)'
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                self.assertEqual(len(self.problems(text)), int(start != 1), text)
                block = str(start) + '. [live](target.txt)'
                self.assertEqual(len(self.problems(block)), 1, block)
        for marker in ['1. ', '2. ', '+ ', '* ']:
            text = 'See [the\n' + marker + '\nguide](target.txt)'
            self.assertEqual(len(self.problems(text)), 1, text)
        self.assertEqual(self.problems('See [the\n- \nguide](target.txt)'), [])
        for first in ['1. ', '- ']:
            for next_marker in ['2. ', '3. ', '2. \n']:
                text = first + '[the\n' + next_marker + 'guide](target.txt)\n\n[live](missing.md)'
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('missing.md', errors[0])
        for first in ['1. ', '- ']:
            text = first + '[the\n' + ' ' * len(first) + '2. guide](target.txt)'
            self.assertEqual(len(self.problems(text)), 1, text)
        for depth in range(1, 6):
            for markers in itertools.product(['- ', '1. '], repeat=depth):
                indent, lines = '', []
                for marker in markers[:-1]:
                    lines.append(indent + marker + 'item')
                    indent += ' ' * len(marker)
                lines.extend([indent + markers[-1] + '```',
                              indent + ' ' * len(markers[-1]) + '[example](missing.md)',
                              indent + ' ' * len(markers[-1]) + '```',
                              '', '[live](live-missing.md)'])
                for quoted in [False, True]:
                    sample = (['> ' + line for line in lines[:-2]] + ['>', lines[-1]]
                              if quoted else lines)
                    with self.subTest(markers=markers, quoted=quoted):
                        errors = self.problems('\n'.join(sample))
                        self.assertEqual(len(errors), 1, errors)
                        self.assertIn('live-missing.md', errors[0])
                        self.assertIn('wiki/guide.md:' + str(depth + 5) + ':', errors[0])
        examples = ['\n    [x](missing.md)', '\n\t[x](missing.md)',
                    '\n>     [x](missing.md)', '- item\n\n      [x](missing.md)',
                    '> ```md\n> [x](missing.md)\n> ```',
                    '- ```md\n  [x](missing.md)\n  ```',
                    '\n<!--\n```\n[x](missing.md)\n-->\n',
                    '\n<!--\n```\n-->\n```\n[x](missing.md)\n```\n',
                    '\n<pre>\n[x](missing.md)\n</pre>\n',
                    '\n<script>\n[x](missing.md)\n</script>\n',
                    '\n<div>\n[x](missing.md)\n</div>\n',
                    '\n    <!--\n\n', '\n    ```\n\n']
        for example in examples:
            with self.subTest(example=example):
                errors = self.problems(example + '\n[live](missing.md)')
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:' + str(example.count('\n') + 3) + ':', errors[0])
        for text in ['paragraph\n    [live](missing.md)', '- paragraph\n    [live](missing.md)',
                     '> paragraph\n>     [live](missing.md)', r'\![live](missing.md)',
                     '`<!--` [live](missing.md)', '[live](missing.md) <!-- hidden -->']:
            with self.subTest(text=text):
                self.assertEqual(len(self.problems(text)), 1)
        self.assertEqual(self.problems('<!-- [id] -->\n[id]: missing.md'), [])
        self.assertEqual(self.problems('[x](existing[id].md)\n\n[id]: missing.md'),
                         ["wiki/guide.md:2: relative link 'existing[id].md' is not a file inside repo"])
        self.assertEqual(len(self.problems('[![image][id]](#anchor)\n\n[id]: missing.md')), 1)
        self.assertEqual(self.problems('\n    [id]: missing.md\n\n[id]'), [])

        cases = [('> [label\nlazy\n> continued](target.txt)', 2),
                 ('- See the [docs on\nconfiguration](target.txt)', 2),
                 ('> - item\n    continued [x\nlazy](target.txt)', 3),
                 ('> [label\ncontinued](target.txt)', 2),
                 ('> Note\n    [missing](target.txt)', 3),
                 ('Note\n\t~~~\n\t[live](target.txt)\n\t~~~', 4)]
        for text, line in cases:
            with self.subTest(text=text):
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
                (self.root / 'wiki/target.txt').unlink()
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:' + str(line) + ':', errors[0])
                self.write('wiki/target.txt', '')
                self.assertEqual(self.problems(text), [])
        for opener, closer in [('<pre>', '</pre>'), ('<div>', '</div>'), ('```', '```')]:
            text = '> note\n' + opener + '\n[example](missing.md)\n' + closer + '\n\n[live](live-missing.md)'
            with self.subTest(block=opener):
                errors = self.problems(text)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:7:', errors[0])
                self.assertIn('live-missing.md', errors[0])
        for boundary in ['- [x\n\ny](missing.md)', '- [x\n# Heading\ny](missing.md)',
                         '- [x\n- y](missing.md)', '- [x\n```\ny](missing.md)\n```',
                         '> [x\n> > y](missing.md)']:
            with self.subTest(boundary=boundary):
                self.assertEqual(self.problems(boundary), [])
        for code in ['> ```\n> [example](missing.md)\n> ```',
                     '\n    [example](missing.md)', '\n\t~~~\n\t[example](missing.md)\n\t~~~',
                     'Note\n~~~\n[example](missing.md)\n~~~']:
            self.assertEqual(self.problems(code), [])

        exits = ['> ```\n> sample\n\n', '- ```\n  sample\n\n',
                 '> <pre>\n> sample\n\n', '- <pre>\n  sample\n\n',
                 '- ```\n  sample\n- ', '> > ```\n> > sample\n> ',
                 '- item\n  - ```\n    sample\n  - ']
        for example in exits:
            with self.subTest(example=example):
                errors = self.problems(example + '[live](missing.md)')
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:' + str(example.count('\n') + 2) + ':', errors[0])
        for text in ['```\n- [example](missing.md)', '> ```\n> - [example](missing.md)',
                     '- ```\n  - [example](missing.md)', '> <pre>\n> [example](missing.md)',
                     '- ```\n  sample\n\n  [example](missing.md)']:
            with self.subTest(text=text):
                self.assertEqual(self.problems(text), [])

        forms = ['<custom>\n[x](missing.md)\n</custom>',
                 '<custom attr="value">\n[x](missing.md)', '</custom>\n[x](missing.md)',
                 '<?processing\n[x](missing.md)\n?>', '<!DOCTYPE\n[x](missing.md)\n>',
                 '<![CDATA[\n[x](missing.md)\n]]>', '<!--\n[x](missing.md)\n-->',
                 '<style>\n[x](missing.md)\n</style>', '<textarea>\n[x](missing.md)\n</textarea>',
                 '<table>\n[x](missing.md)\n</table>', '<figure>\n[x](missing.md)\n</figure>']
        for form in forms:
            with self.subTest(form=form):
                self.assertEqual(self.problems('\n' + form), [])
                errors = self.problems('\n' + form + '\n\n[live](missing.md)')
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:' + str(form.count('\n') + 5) + ':', errors[0])
        self.assertEqual(len(self.problems('paragraph\n<custom>\n[live](missing.md)')), 1)
        self.assertEqual(self.problems('```\n<custom>\n```'), [])
        self.assertEqual(len(self.problems('    <custom>\n\n[live](missing.md)')), 1)

        for text in ['-     [x](missing.md)', '-\t  [x](missing.md)', '  -     [x](missing.md)']:
            self.assertEqual(self.problems(text), [], text)
        for text in ['-    [x](missing.md)', '-\t[x](missing.md)']:
            self.assertEqual(len(self.problems(text)), 1, text)
        for opener, closer in [('```md', '```'), ('<pre>', '</pre>')]:
            text = '- Example:\n  ' + opener + '\n\t[x](missing.md)\n  ' + closer + '\n[live](missing.md)'
            errors = self.problems(text)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('wiki/guide.md:6:', errors[0])

        for prefix in ['\t', '  \t']:
            errors = self.problems('- item\n\n' + prefix + '[live](missing.md)')
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('wiki/guide.md:4:', errors[0])

    def test_entities_decode_before_url_classification(self):
        cases = [('file&copy.txt', 'file&copy.txt', 'file©.txt'),
                 ('file&#65.txt', 'file&', 'fileA.txt'),
                 ('file&copy;.txt', 'file©.txt', 'file&copy;.txt'),
                 ('file&#65;.txt', 'fileA.txt', 'file&#65;.txt'),
                 ('file&amp;copy;.txt', 'file&copy;.txt', 'file©.txt'),
                 (r'file\&copy;.txt', 'file&copy;.txt', 'file©.txt'),
                 ('file&#00000065;.txt', 'file&', 'fileA.txt'),
                 ('file&notreal;.txt', 'file&notreal;.txt', 'file¬real;.txt'),
                 ('file&copycat;.txt', 'file&copycat;.txt', 'file©cat;.txt')]
        for raw, expected, decoy in cases:
            for template in ['[x]({})', '[id]: {}\n\n[id]']:
                with self.subTest(raw=raw, template=template):
                    text = template.format(raw)
                    self.write('wiki/' + expected, '')
                    self.assertEqual(self.problems(text), [])
                    (self.root / 'wiki' / expected).unlink()
                    self.write('wiki/' + decoy, '')
                    self.assertEqual(len(self.problems(text)), 1, text)
                    (self.root / 'wiki' / decoy).unlink()
        for name, dest in [('a&b.md', 'a&amp;b.md'), ('#.md', '&#35;.md'),
                           ('a b.md', 'a&#32;b.md'), ('a&b.md', 'a&#38;b.md')]:
            with self.subTest(dest=dest):
                self.write('wiki/' + name, '')
                # A leading decoded hash is an anchor and is intentionally ignored.
                self.assertEqual(self.problems('[x](' + dest + ')'), [])
                (self.root / 'wiki' / name).unlink()
                if name != '#.md':
                    self.assertEqual(len(self.problems('[x](' + dest + ')')), 1)
        self.assertEqual(self.problems('[x](https&#58;//example.test) [x](&#47;absolute)'), [])

    def test_lexical_aliases_keep_distinct_link_bases(self):
        self.write('docs/guides/page.md', '[x](../target.md)')
        (self.root / 'wiki/guides').symlink_to(self.root / 'docs/guides', target_is_directory=True)
        self.write('wiki/target.md', '')
        self.assertEqual(self.problems('hello'), [])
        (self.root / 'wiki/target.md').unlink()
        self.write('docs/target.md', '')
        errors = self.problems('hello')
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('wiki/guides/page.md:1:', errors[0])
        (self.root / 'wiki/guides').unlink()
        (self.root / 'docs/guides/page.md').unlink()
        (self.root / 'docs/target.md').unlink()
        self.write('docs/page.md', '[x](target.txt)')
        self.write('wiki/target.txt', '')
        (self.root / 'wiki/alias.md').symlink_to(self.root / 'docs/page.md')
        self.cfg['topics']['guide']['sources'] = [{'path': 'wiki/alias.md'}]
        self.assertEqual(self.problems('hello'), [])
        self.cfg['topics']['guide']['sources'].append({'path': 'docs/page.md'})
        for sources in [self.cfg['topics']['guide']['sources'],
                        list(reversed(self.cfg['topics']['guide']['sources']))]:
            self.cfg['topics']['guide']['sources'] = sources
            errors = self.problems('hello')
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('docs/page.md:1:', errors[0])
        self.write('docs/target.txt', '')
        self.assertEqual(self.problems('hello'), [])

    def test_complete_wiki_walk_and_directory_alias_cycles(self):
        for folder in ['.private', 'build', 'vendor', 'node_modules']:
            self.write('wiki/' + folder + '/page.md', '[x](missing.md)')
        errors = self.problems('hello')
        self.assertEqual(len(errors), 4, errors)
        self.write('docs/guides/page.md', '[x](target.txt)')
        self.write('docs/guides/target.txt', '')
        (self.root / 'wiki/guides').symlink_to(self.root / 'docs/guides', target_is_directory=True)
        (self.root / 'docs/guides/cycle').symlink_to(self.root / 'wiki', target_is_directory=True)
        self.assertEqual(len(self.problems('hello')), 4)
        (self.root / 'docs/guides/target.txt').unlink()
        errors = self.problems('hello')
        self.assertEqual(len(errors), 5, errors)
        self.assertTrue(any('wiki/guides/page.md:1:' in error for error in errors))

    def test_link_read_errors_report_and_continue(self):
        self.write('wiki/extra.md', '[x](missing.md)')
        old_root = router.ROOT
        try:
            router.ROOT = str(self.root)
            for name in ['wiki/guide.md', 'wiki/unreadable.md']:
                with self.subTest(name=name):
                    (self.root / name).write_bytes(b'\xff')
                    errors = router.link_problems(self.cfg)
                    self.assertTrue(any(e.startswith(name + ':') for e in errors), errors)
                    self.assertTrue(any('wiki/extra.md:1:' in e for e in errors), errors)
                    self.write(name, '# Selected\n')
        finally:
            router.ROOT = old_root
        real_open = open
        from unittest.mock import patch
        for denied, live in [('extra.md', 'wiki/guide.md:2:'),
                             ('guide.md', 'wiki/extra.md:1:')]:
            def deny(path, *args, **kwargs):
                if str(path).endswith(denied):
                    raise PermissionError('denied for test')
                return real_open(path, *args, **kwargs)
            with self.subTest(denied=denied), patch('builtins.open', side_effect=deny):
                errors = self.problems('[x](missing.md)')
            self.assertTrue(any('wiki/' + denied + ':' in e and 'denied for test' in e for e in errors))
            self.assertTrue(any(live in e for e in errors))

    def test_wiki_inventory_failures_report_without_external_reads(self):
        from unittest.mock import patch
        self.cfg['routerFile'] = 'docs/index.md'
        index = self.root / 'docs/index.md'
        index.parent.mkdir()
        external = self.root.parent / 'external-index.md'
        external.write_text('[hidden](missing.md)', encoding='utf-8')
        real_open = open
        def checked_open(path, *args, **kwargs):
            self.assertNotEqual(Path(path).resolve(), external)
            return real_open(path, *args, **kwargs)
        self.save_cfg()
        for kind in ['missing', 'directory', 'external', 'invalid_utf8']:
            if kind == 'directory':
                index.mkdir()
            elif kind == 'external':
                index.symlink_to(external)
            elif kind == 'invalid_utf8':
                index.write_bytes(b'\xff')
            with self.subTest(router=kind), patch('builtins.open', side_effect=checked_open):
                errors = self.problems('hello')
                self.assertTrue(any('docs/index.md:' in error for error in errors), errors)
                if kind == 'directory':
                    result = self.cli('check')
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertIn('docs/index.md:', result.stdout)
            if kind == 'directory':
                index.rmdir()
            elif kind in ['external', 'invalid_utf8']:
                index.unlink()
        self.write('docs/index.md', '[live](missing.md)')
        self.assertTrue(any('docs/index.md:1:' in e for e in self.problems('hello')))
        self.cfg.pop('routerFile')
        self.write('wiki/private/page.md', '[x](missing.md)')
        real_scandir = router.os.scandir
        def deny(directory):
            if str(directory).endswith('private'):
                raise PermissionError('directory denied for test')
            return real_scandir(directory)
        with patch.object(router.os, 'scandir', side_effect=deny):
            errors = self.problems('[live](missing.md)')
        self.assertTrue(any('wiki/private:' in e and 'directory denied' in e for e in errors))
        self.assertTrue(any('wiki/guide.md:2:' in e for e in errors))

    def test_invalid_wiki_symlinks_fail_without_reading_external_content(self):
        from unittest.mock import patch
        outside = self.root.parent / 'outside.md'
        outside.write_text('[x](missing.md)', encoding='utf-8')
        (self.root / 'wiki/external.md').symlink_to(outside)
        (self.root / 'wiki/dangling.md').symlink_to(self.root / 'absent.md')
        (self.root / 'wiki/README.md').unlink()
        (self.root / 'wiki/README.md').symlink_to(self.root / 'absent.md')
        outside_dir = self.root.parent / 'outside-dir'
        outside_dir.mkdir()
        (outside_dir / 'page.md').write_text('[x](missing.md)', encoding='utf-8')
        (self.root / 'wiki/guides').symlink_to(outside_dir, target_is_directory=True)
        real_scandir = router.os.scandir
        def deny_scandir(path):
            self.assertNotEqual(Path(path).resolve(), outside_dir)
            return real_scandir(path)
        real_open = open
        def deny_external(path, *args, **kwargs):
            self.assertNotEqual(Path(path).resolve(), outside)
            return real_open(path, *args, **kwargs)
        with patch('builtins.open', side_effect=deny_external), patch.object(router.os, 'scandir', side_effect=deny_scandir):
            errors = self.problems('hello')
        self.assertTrue(any('wiki/guides:' in e for e in errors), errors)
        self.assertTrue(any('wiki/external.md:' in e for e in errors))
        self.assertTrue(any('wiki/dangling.md:' in e for e in errors))
        self.assertTrue(any('wiki/README.md:' in e for e in errors))

    def test_autolinks_code_html_and_inline_comment_ownership(self):
        self.write('wiki/good.txt', '')
        for opaque in ['<https://example.test/[x](hidden.md)>', '<user+tag@example.test>',
                       '`<!-- [x](hidden.md) -->`', '`` ` [x](hidden.md) ``',
                       r'\`` [x](hidden.md) `',
                       '<span title="[x](hidden.md)">text</span>',
                       '<!-- [x](hidden.md) -->', '<?pi [x](hidden.md) ?>',
                       '<!DECL [x](hidden.md)>', '<![CDATA[[x](hidden.md)]]>']:
            with self.subTest(opaque=opaque):
                errors = self.problems('[a](good.txt) ' + opaque + ' [live](live-missing.md)')
                self.assertEqual(len(errors), 1, errors)
                self.assertIn('wiki/guide.md:2:', errors[0])
                self.assertIn('live-missing.md', errors[0])
        for text in ['text <!-- unfinished\n\n[live](live-missing.md)',
                     'text <span title="unfinished\n\n[live](live-missing.md)\n">',
                     'text <span title="unfinished\n# Heading\n[live](live-missing.md)\n">',
                     '`<!--\nexample` [live](live-missing.md)',
                     'text <!-- complete\ncomment --> [live](live-missing.md)']:
            with self.subTest(text=text):
                self.assertEqual(len(self.problems(text)), 1)
        self.assertEqual(self.problems('text <!--\n[x](hidden.md)\n-->'), [])
        self.assertEqual(self.problems('\n<!-- unfinished\n\n[x](hidden.md)'), [])

        for text in ['Use <type [guide](missing.md)>']:
            self.assertEqual(len(self.problems(text)), 1, text)
        for tag in ['<type attr="[x](hidden.md)" disabled>', "<type a='[x](hidden.md)'>", '<type a=[x](hidden.md)>']:
            self.assertEqual(self.problems('Use ' + tag), [])
        for tag in ['span', 'a']:
            text = ('[before](before-missing.md)\nText <' + tag + ' title="[example](missing.md)">'
                    'label</' + tag + '>\n[after](after-missing.md)')
            errors = self.problems(text)
            self.assertEqual(len(errors), 2, errors)
            self.assertIn('wiki/guide.md:2:', errors[0])
            self.assertIn('wiki/guide.md:4:', errors[1])
            self.assertIn('before-missing.md', errors[0])
            self.assertIn('after-missing.md', errors[1])

    def test_resolved_link_and_image_nesting(self):
        self.write('wiki/good.txt', '')
        cases = [('[outer [inner](good.txt)](missing.md)', 0),
                 ('[outer [id]](missing.md)\n\n[id]: good.txt', 0),
                 ('[outer [id]](#anchor)\n\n[id]: missing.md', 1),
                 ('[outer ![image](good.txt)](missing.md)', 1),
                 ('![outer [inner](good.txt)](missing.md)', 1),
                 ('[outer ![image][id]](missing.md)\n\n[id]: good.txt', 1),
                 ('![outer [id]](missing.md)\n\n[id]: good.txt', 1),
                 ('[outer [undefined]](missing.md)', 1),
                 ('[undefined][other][live](missing.md)', 1),
                 ('[outer [inner](missing.md)](also-missing.md)', 1),
                 ('[x][bad [label]]\n\n[bad [label]]: missing.md', 0),
                 (r'[x][escaped\[label]'+ '\n\n' + r'[escaped\[label]: missing.md', 1),
                 ('[x][' + 'a' * 1000 + ']\n\n[' + 'a' * 1000 + ']: missing.md', 0)]
        for text, count in cases:
            with self.subTest(text=text):
                errors = self.problems(text)
                self.assertEqual(len(errors), count, errors)
                if 'also-missing.md' in text:
                    self.assertIn("'missing.md'", errors[0])
                    self.assertNotIn('also-missing.md', errors[0])

    def test_definition_lookahead_work_is_bounded_by_input_size(self):
        # Count the normalization operation shared by scanning and definition lookahead.
        from unittest.mock import patch
        for kind in ['even_slashes', 'column_zero', 'definitions', 'headings', 'malformed_titles']:
            work = []
            for count in [100, 200]:
                with self.subTest(kind=kind, count=count):
                    if kind in ['even_slashes', 'column_zero']:
                        title = ' "line\nend' + '\\' * 2 + '"' if kind == 'even_slashes' else '\n "line\n"'
                        text = '\n'.join('[d' + str(i) + ']: target.txt' + title for i in range(count))
                        text += '\n\n[d' + str(count - 1) + ']'
                        expected = [((2 if kind == 'even_slashes' else 3) * (count - 1) + 1, 'target.txt')]
                    elif kind == 'definitions':
                        text = '\n'.join('[d' + str(i) + ']: target.txt' for i in range(count))
                        text += '\n\n[d' + str(count - 1) + ']'
                        expected = [(count, 'target.txt')]
                    else:
                        unit = '# Heading\n[link](target.txt)' if kind == 'headings' else '[id]: target.txt "unfinished\n# Heading\n[link](target.txt)'
                        text = '\n'.join(unit for _ in range(count))
                        step = 2 if kind == 'headings' else 3
                        expected = [(step * (i + 1), 'target.txt') for i in range(count)]
                    with patch.object(router, 'container_prefix', wraps=router.container_prefix) as measured:
                        links = list(router.link_destinations(text.split('\n')))
                    self.assertEqual(links, expected)
                    self.assertGreater(measured.call_count, 0)
                    work.append(measured.call_count)
            self.assertLess(work[1], 3 * work[0], (kind, work))

    def test_shipped_artifacts_match_distributable_assets(self):
        base = SCRIPT.parents[1]
        self.assertEqual(SCRIPT.read_bytes(), (base / 'evals/fixtures/routed/scripts/ai-context.py').read_bytes())
        self.assertEqual((base / 'assets/wiki-ai-context.md').read_bytes(),
                         (base / 'evals/fixtures/routed/wiki/ai-context.md').read_bytes())

    def test_exact_headings_keep_existing_fence_behavior(self):
        self.assertEqual(list(router.headings(['\t~~~', '# Example', '~~~', '# After'])),
                         [(3, 1, 'After')])
        self.write('wiki/guide.md', '# Selected\n```sh\n# Selected\n````\n~~~\n# Other\n~~~\nbody\n# End\n')
        result = self.cli('guide')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('body', result.stdout)
        self.assertNotIn('# End', result.stdout)
        self.write('wiki/guide.md', '# Selected\n# Selected\n')
        result = self.cli('check')
        self.assertEqual(result.returncode, 1)
        self.assertIn("heading 'Selected' found 2x", result.stdout)




class RouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name).resolve()
        self.root = self.cwd / 'repo'
        self.write('AGENTS.md', '`guide`\n')
        self.write('wiki/guide.md', '# Guide\nRoot content.\n')
        self.write('wiki/README.md', '')
        self.cfg = {'topics': {'guide': {'description': 'Read the guide.',
                                       'sources': [{'path': 'wiki/guide.md'}]}}}
        self.save_config()
        self.local_script = self.root / 'scripts' / 'ai-context.py'

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding='utf-8')

    def save_config(self, path=None):
        path = path or self.root / 'wiki' / 'ai-context.json'
        path.write_text(json.dumps(self.cfg), encoding='utf-8')
        return path

    def run_cli(self, command, overrides=None, script=SCRIPT):
        env = {k: v for k, v in os.environ.items()
               if k not in ('AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG')}
        env.update(overrides or {})
        return subprocess.run([sys.executable, str(script), command], cwd=self.cwd,
                              env=env, capture_output=True, text=True, encoding='utf-8')

    def assert_commands(self, overrides=None, script=SCRIPT, description='Read the guide.'):
        for command, expected in [('list', description),
                                  ('guide', '<!-- wiki/guide.md -->\n# Guide\nRoot content.'),
                                  ('check', '\nok\n')]:
            with self.subTest(command=command, overrides=overrides):
                result = self.run_cli(command, overrides, script)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(expected, result.stdout)

    def test_copied_script_defaults(self):
        self.local_script.parent.mkdir()
        shutil.copyfile(SCRIPT, self.local_script)
        for overrides in [{}, {'AI_CONTEXT_ROOT': ''}, {'AI_CONTEXT_CONFIG': ''},
                          {'AI_CONTEXT_ROOT': '', 'AI_CONTEXT_CONFIG': ''}]:
            self.assert_commands(overrides, script=self.local_script)

    def test_shared_root_and_external_config(self):
        self.assert_commands({'AI_CONTEXT_ROOT': str(self.root)})
        description = 'Read the externally configured guide.'
        self.cfg['topics']['guide']['description'] = description
        external = self.save_config(self.cwd / 'router.json')
        default = self.root / 'wiki' / 'ai-context.json'
        self.assertTrue(default.is_file())
        self.assertEqual(json.loads(default.read_text(encoding='utf-8'))['topics']['guide']['description'],
                         'Read the guide.')
        self.assert_commands({'AI_CONTEXT_ROOT': str(self.root), 'AI_CONTEXT_CONFIG': str(external)},
                             description=description)
        self.assertFalse(self.local_script.parent.exists())
        default.unlink()
        self.assert_commands({'AI_CONTEXT_ROOT': str(self.root), 'AI_CONTEXT_CONFIG': str(external)},
                             description=description)
        self.assert_commands({'AI_CONTEXT_ROOT': 'repo', 'AI_CONTEXT_CONFIG': 'router.json'},
                             description=description)

    def test_shared_unknown_topic_recovery(self):
        external = self.save_config(self.cwd / 'router.json')
        overrides = {'AI_CONTEXT_ROOT': str(self.root), 'AI_CONTEXT_CONFIG': str(external)}
        self.assertFalse(self.local_script.parent.exists())
        result = self.run_cli('missing-topic', overrides)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("unknown topic 'missing-topic'; "), result.stderr)
        self.assertIn('rerun this script with list', result.stderr)
        self.assertNotIn('scripts/ai-context.py', result.stderr)
        recovered = self.run_cli('list', overrides)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn('Read the guide.', recovered.stdout)

    def test_config_only_keeps_script_root(self):
        self.local_script.parent.mkdir()
        shutil.copyfile(SCRIPT, self.local_script)
        external = self.save_config(self.cwd / 'router.json')
        (self.root / 'wiki' / 'ai-context.json').unlink()
        self.assert_commands({'AI_CONTEXT_CONFIG': str(external)}, self.local_script)

    def link_script(self, link):
        self.local_script.parent.mkdir(exist_ok=True)
        shutil.copyfile(SCRIPT, self.local_script)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(self.local_script)
        return link

    def other_repo(self, config=True):
        other = self.cwd / 'other'
        (other / 'wiki').mkdir(parents=True)
        (other / 'AGENTS.md').write_text('`guide`\n', encoding='utf-8')
        (other / 'wiki' / 'guide.md').write_text('# Guide\nRoot content.\n', encoding='utf-8')
        (other / 'wiki' / 'README.md').write_text('', encoding='utf-8')
        if config:
            self.cfg['topics']['guide']['description'] = 'Read the other guide.'
            self.save_config(other / 'wiki' / 'ai-context.json')
        return other

    def test_symlink_outside_scripts_uses_target_root(self):
        link = self.link_script(self.cwd / 'bin' / 'ai-context')
        for overrides in [{}, {'AI_CONTEXT_ROOT': ''}, {'AI_CONTEXT_CONFIG': ''}]:
            self.assert_commands(overrides, script=link)

    def test_symlink_with_config_only_keeps_link_root(self):
        link = self.link_script(self.cwd / 'bin' / 'ai-context')
        external = self.save_config(self.cwd / 'router.json')
        result = self.run_cli('guide', {'AI_CONTEXT_CONFIG': str(external)}, link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(repr(str(self.cwd / 'wiki' / 'guide.md')), result.stderr)  # OSError quotes it

    def test_symlink_outside_scripts_with_local_config_keeps_link_root(self):
        other = self.other_repo()
        link = self.link_script(other / 'tools' / 'ai-context.py')
        self.assert_commands(script=link, description='Read the other guide.')

    def test_symlink_with_explicit_root_uses_that_root(self):
        other = self.other_repo()
        link = self.link_script(self.cwd / 'bin' / 'ai-context')
        self.assert_commands({'AI_CONTEXT_ROOT': str(other)}, script=link,
                             description='Read the other guide.')

    def test_symlink_in_scripts_keeps_link_root(self):
        other = self.other_repo()
        link = self.link_script(other / 'scripts' / 'ai-context.py')
        self.assert_commands(script=link, description='Read the other guide.')

    def test_symlink_in_scripts_without_config_fails_closed(self):
        other = self.other_repo(config=False)
        for folder in ['scripts', 'Scripts']:
            with self.subTest(folder=folder):
                link = self.link_script(other / folder / 'ai-context.py')
                result = self.run_cli('list', script=link)
                self.assertEqual(result.returncode, 1)
                self.assertIn(str(other / 'wiki' / 'ai-context.json'), result.stderr)
                self.assertNotIn('Read the guide.', result.stdout)
                link.unlink()

    def test_missing_selected_config(self):
        missing = self.cwd / 'missing.json'
        result = self.run_cli('list', {'AI_CONTEXT_CONFIG': str(missing)})
        self.assertNotEqual(result.returncode, 0)
        for text in [str(missing), 'AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG']:
            self.assertIn(text, result.stderr)

    def test_plain_keys_match_exact_paths_and_globs_regardless_of_existence(self):
        cases = [
            ('projects/*/AGENTS.md', ['projects/api/AGENTS.md',
                                     'projects/team/api/AGENTS.md'], ['other/AGENTS.md']),
            ('windows\\*\\AGENTS.md', ['windows/api/AGENTS.md'], []),
            ('case/*/agents.md', [], ['case/api/AGENTS.md']),
            ('wiki/notes?.md', ['wiki/notes1.md'], ['wiki/notes12.md']),
            ('wiki/file[1].md', ['wiki/file[1].md', 'wiki/file1.md'], []),
            ('wiki/file[1].md', ['wiki/file1.md'], []),
            ('wiki/file[[]1].md', ['wiki/file[1].md'], ['wiki/file1.md']),
            ('wiki/reference.md', ['wiki/reference.md'],
             ['wiki/unmapped.md', 'wiki/history/unindexed.md']),
        ]
        if os.name != 'nt':
            cases += [('wiki/star*.md', ['wiki/star*.md', 'wiki/star2.md'], []),
                      ('wiki/question?.md', ['wiki/question?.md', 'wiki/question2.md'], [])]
        for key, exempt, unmatched in cases:
            with self.subTest(key=key, exempt=exempt):
                for path in exempt + unmatched:
                    self.write(path, '# Instructions\n')
                self.cfg['unrouted'] = {key: 'Deliberate exception.'}
                self.save_config()
                result = self.run_cli('check', {'AI_CONTEXT_ROOT': str(self.root)})
                self.assertEqual(result.returncode, 1 if unmatched else 0,
                                 result.stdout + result.stderr)
                failures = {line.split(':', 1)[0][5:] for line in result.stdout.splitlines()
                            if line.startswith('FAIL ')}
                self.assertEqual(failures, set(unmatched))
            for path in exempt + unmatched:
                (self.root / path).unlink()

    def test_filesystem_anchor_allows_temporary_sources(self):
        self.write('wiki/guide.md', '# Guide\nRoot content.\n[Target](target.txt)\n')
        self.write('wiki/target.txt', 'Inside the selected filesystem root.\n')
        anchor = Path(self.root.anchor)
        source = (self.root / 'wiki' / 'guide.md').relative_to(anchor).as_posix()
        self.cfg['topics']['guide']['sources'] = [{'path': source}]
        self.cfg['rootInstructions'] = str(self.root / 'AGENTS.md')
        self.cfg['routerFile'] = str(self.root / 'wiki' / 'README.md')
        self.cfg['wikiDir'] = str(self.root / 'wiki')
        external = self.save_config(self.cwd / 'router.json')
        overrides = {'AI_CONTEXT_ROOT': str(anchor), 'AI_CONTEXT_CONFIG': str(external)}
        with self.subTest(command='guide'):
            result = self.run_cli('guide', overrides)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('<!-- ' + source + ' -->\n# Guide\nRoot content.', result.stdout)
        with self.subTest(command='check'), patch.dict(os.environ, overrides):
            router = runpy.run_path(str(SCRIPT))
            # Only traversal is mocked: never walk the filesystem anchor.
            with patch('os.walk', return_value=[]), redirect_stdout(io.StringIO()) as output:
                status = router['check'](router['load_cfg']())
            self.assertEqual(status, 0, output.getvalue())
            self.assertIn('\nok\n', output.getvalue())

    def test_external_config_does_not_allow_sources_outside_root(self):
        (self.cwd / 'outside.md').write_text('Outside content.', encoding='utf-8')
        self.cfg['topics']['guide']['sources'] = [{'path': '../outside.md'}]
        external = self.save_config(self.cwd / 'router.json')
        result = self.run_cli('check', {'AI_CONTEXT_ROOT': str(self.root),
                                        'AI_CONTEXT_CONFIG': str(external)})
        self.assertEqual(result.returncode, 1)
        self.assertIn('../outside.md: outside repo', result.stdout)

    def test_canonical_script_checks_existing_fixture(self):
        fixture = Path(__file__).resolve().parent / 'fixtures' / 'routed'
        result = self.run_cli('check', {'AI_CONTEXT_ROOT': str(fixture)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('\nok\n', result.stdout)



if __name__ == '__main__':
    unittest.main()
