"""Opt-in exact-source reuse without changing ordinary topic rendering."""
import copy
import os
from pathlib import Path
from unittest.mock import patch
import test_ai_context_mounts as mounts


router = mounts.router


class DedupeTests(mounts.MountFixture):
    def pair(self, sources=None):
        self.cfg['topics']['second'] = copy.deepcopy(self.cfg['topics']['guide'])
        if sources is not None:
            self.cfg['topics']['second']['sources'] = sources
        self.save_configs()

    def test_opt_in_default_and_single_topic_bytes(self):
        self.pair()
        one = self.cli('guide').stdout
        self.assertEqual(self.cli('guide', 'second').stdout, one.rstrip('\n') + '\n\n' + one)
        for names in [('guide',), ('guide', 'second'), ('guide', 'guide')]:
            result = self.cli('--dedupe', *names)
            self.assertEqual((result.returncode, result.stderr, result.stdout), (0, '', one))
        # Repetition inside one topic is not silently rewritten.
        self.cfg['topics']['guide']['sources'] *= 2
        self.save_configs()
        self.assertEqual(self.cli('--dedupe', 'guide').stdout, self.cli('guide').stdout)
        self.assertEqual(self.cli('--dedupe', 'guide', 'second').stdout, self.cli('guide').stdout)

    def test_first_occurrence_order_and_markers(self):
        self.write('wiki/other.md', '# Other\n中文.\n')
        self.pair([{'path': 'wiki/other.md'}, {'path': 'wiki/guide.md'}])
        result = self.cli('--dedupe', 'guide', 'second')
        self.assertEqual(result.stdout, '<!-- wiki/guide.md -->\n# Guide\nLocal.\n\n'
                         '<!-- wiki/other.md -->\n# Other\n中文.\n')
        self.assertEqual(self.cli('--dedupe', 'second', 'guide').stdout, self.cli('second').stdout)

    def test_exact_sources_not_overlapping_sections_or_identical_content(self):
        self.write('wiki/other.md', '# Guide\nLocal.\n')
        self.pair([{'path': 'wiki/guide.md', 'heading': 'Guide'}, {'path': 'wiki/other.md'}])
        result = self.cli('--dedupe', 'guide', 'second')
        self.assertEqual(result.stdout, self.cli('guide', 'second').stdout)
        self.assertIn('<!-- wiki/guide.md § Guide -->', result.stdout)
        self.cfg['topics']['guide']['sources'][0]['heading'] = 'Guide'
        self.save_configs()
        self.assertEqual(self.cli('--dedupe', 'guide', 'second').stdout.count('§ Guide -->'), 1)

    def test_path_spelling_keeps_distinct_markers(self):
        self.pair([{'path': './wiki/guide.md'}, {'path': 'wiki\\guide.md'}])
        self.assertEqual(self.cli('--dedupe', 'guide', 'second').stdout,
                         self.cli('guide', 'second').stdout)

    def test_owner_roots_are_isolated(self):
        self.sibling()
        result = self.cli('--dedupe', 'guide', 'kb/guide', 'other/guide', 'kb/guide')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, self.cli('guide', 'kb/guide', 'other/guide').stdout)

    def test_late_errors_leave_stdout_empty(self):
        for source, text, error in [({'path': 'wiki/missing.md'}, '', 'missing.md'),
                                   ({'path': 'wiki/guide.md', 'heading': 'Absent'}, '', 'found 0x'),
                                   ({'path': 'wiki/guide.md', 'heading': 'Guide'},
                                    '# Guide\na\n# Guide\nb\n', 'found 2x'),
                                   ({'path': 'wiki'}, '', 'regular file')]:
            with self.subTest(source=source):
                if text:
                    self.write('wiki/guide.md', text)
                self.pair([source])
                result = self.cli('--dedupe', 'guide', 'second')
                self.assertEqual((result.returncode, result.stdout), (1, ''))
                self.assertIn(error, result.stderr)
        for args in [('guide', 'missing'), ('guide', 'kb/missing')]:
            result = self.cli('--dedupe', *args)
            self.assertEqual((result.returncode, result.stdout), (1, ''))

    def test_legacy_flag_topic_and_flag_requires_topics(self):
        result = self.cli('--dedupe')
        self.assertEqual((result.returncode, result.stdout), (1, ''))
        self.assertIn('requires at least one topic', result.stderr)
        self.cfg['topics']['--dedupe'] = copy.deepcopy(self.cfg['topics']['guide'])
        self.save_configs()
        self.assertEqual(self.cli('--dedupe').stdout, self.cli('guide').stdout)
        self.assertEqual(self.cli('--dedupe', 'guide').stdout, self.cli('guide', 'guide').stdout)

    def test_omitted_duplicate_still_rejects_symlink_escape_and_directory(self):
        self.pair()
        path = self.root / 'wiki/guide.md'
        outside = self.parent / 'outside.md'
        outside.write_text('SECRET', encoding='utf-8')
        for replacement in ['symlink', 'directory']:
            self.write('wiki/guide.md', '# Guide\nLocal.\n')
            real_section, calls = router.section, []
            def change(*args, **kwargs):
                calls.append(1)
                if len(calls) == 2:
                    path.unlink()
                    if replacement == 'symlink':
                        self.symlink(path, outside)
                    else:
                        path.mkdir()
                return real_section(*args, **kwargs)
            with patch.object(router, 'section', side_effect=change):
                code, out, err = self.call_main('--dedupe', 'guide', 'second')
            self.assertEqual((code, out), (1, ''))
            self.assertNotIn('SECRET', err)
            self.assertIn('outside repo' if replacement == 'symlink' else 'regular file', err)
            if path.is_symlink():
                path.unlink()
            else:
                path.rmdir()

    def test_heading_fences_and_boundaries_unchanged(self):
        self.write('wiki/guide.md', '# Guide\n## Selected\nText\n```\n## Selected\n```\n'
                   '### Child\nKeep.\n## Other\nOmit.\n')
        self.cfg['topics']['guide']['sources'] = [{'path': 'wiki/guide.md', 'heading': 'Selected'}]
        self.pair()
        result = self.cli('--dedupe', 'guide', 'second')
        self.assertEqual(result.stdout, self.cli('guide').stdout)
        self.assertIn('### Child\nKeep.', result.stdout)
        self.assertNotIn('Omit.', result.stdout)

    def test_invalid_encoding_late_in_request_is_atomic(self):
        self.pair([{'path': 'wiki/bad.md'}])
        (self.root / 'wiki/bad.md').write_bytes(b'\xff')
        result = self.cli('--dedupe', 'guide', 'second')
        self.assertEqual((result.returncode, result.stdout), (1, ''))
        self.assertIn('utf-8', result.stderr)

    def test_check_budgets_do_not_deduplicate(self):
        self.cfg['topics']['guide']['sources'] *= 2
        self.pair()
        single_bytes = len(self.cli('guide').stdout.rstrip('\n').encode('utf-8'))
        self.cfg['topics']['guide']['maxBytes'] = single_bytes - 1
        self.save_configs()
        result = self.cli('check')
        self.assertEqual(result.returncode, 1)
        self.assertIn(f'guide: {single_bytes} B > {single_bytes - 1}', result.stdout)

    def test_distinct_source_options_are_not_silently_deduplicated(self):
        self.cfg['topics']['guide']['sources'][0]['heading'] = 'Guide'
        self.pair([{'path': 'wiki/guide.md', 'heading': 'Guide', 'frontmatter': True}])
        result = self.cli('--dedupe', 'guide', 'second')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, self.cli('guide', 'second').stdout)
        self.assertEqual(result.stdout.count('<!-- wiki/guide.md § Guide -->'), 2)
