"""Real Git repositories + real jq/fzf; terminal APIs use stateful doubles."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'bin/wt-switch'

class WorktreeSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for executable in ['git', 'jq', 'bash', 'fzf']:
            if not shutil.which(executable):
                raise RuntimeError(f'{executable} is required')
        cls.suite = tempfile.TemporaryDirectory(prefix='mux-tools-tests-')
        cls.base = Path(cls.suite.name).resolve()
        cls.repo = cls.base / 'main repo'
        cls.feature = cls.base / "中文 worktree ' dollar$ back`slash\\"
        cls.detached = cls.base / 'detached checkout'
        cls.repo.mkdir()
        cls.git('init', '-b', 'main', str(cls.repo))
        cls.git('-C', str(cls.repo), 'config', 'user.email', 'tests@example.invalid')
        cls.git('-C', str(cls.repo), 'config', 'user.name', 'Test Fixture')
        cls.git('-C', str(cls.repo), 'config', 'core.hooksPath', '/dev/null')
        cls.git('-C', str(cls.repo), 'commit', '--allow-empty', '-m', 'test fixture')
        cls.git('-C', str(cls.repo), 'worktree', 'add', '-b', 'feature/login', str(cls.feature))
        cls.git('-C', str(cls.repo), 'worktree', 'add', '--detach', str(cls.detached))
        (cls.feature / 'nested folder').mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.suite.cleanup()

    @staticmethod
    def git(*args):
        return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout.strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.state = self.tmp / 'host.json'
        self.write_host({'tabs': []})
        commands = self.tmp / 'commands'
        commands.mkdir()
        for name in ['rex', 'herdr-app', 'hc']:
            (commands / name).symlink_to(ROOT / 'tests/fake_host.py')
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(('REX_', 'HC_', 'HERDR_', 'MUX_TOOLS_', 'FZF_'))}
        self.env.update({'FAKE_HOST_DATA': str(self.state),
                         'MUX_TOOLS_STATE_DIR': str(self.tmp / 'state'),
                         'MUX_TOOLS_REX_BIN': str(commands / 'rex'),
                         'MUX_TOOLS_HERDR_BIN': str(commands / 'herdr-app'),
                         'MUX_TOOLS_HC_BIN': str(commands / 'hc')})

    def write_host(self, data):
        self.state.write_text(json.dumps(data))

    def host(self):
        return json.loads(self.state.read_text())

    def command(self, host='rex', target=None):
        return ['/bin/bash', str(SCRIPT), '--host', host, '--scope', 'session:test' if host == 'rex' else 'space:test',
                '--cwd', str(self.repo), '--path', str(target or self.feature)]

    def run_script(self, args=None, success=True, env=None):
        result = subprocess.run(args or self.command(), capture_output=True, text=True, env=env or self.env)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def tab(self, host='rex', cwd=None):
        return {'id': 'window:existing' if host == 'rex' else 'tab:existing',
                'terminal': 'block:existing' if host == 'rex' else 't-existing',
                'label': 'User renamed this tab', 'cwd': str(cwd or self.feature)}

    def fake_picker(self, exit_code=0, index=0):
        picker = self.tmp / 'commands/fzf'
        picker.write_text('#!/bin/bash\n' + (f'sed -n "{index+1}p"\n' if exit_code == 0 else 'cat >/dev/null\n') + f'exit {exit_code}\n')
        picker.chmod(0o755)
        self.env['PATH'] = str(picker.parent) + os.pathsep + self.env['PATH']

    def test_list_includes_unicode_paths_and_detached_head(self):
        result = self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--list'])
        entries = {e['path']: e['branch'] for e in json.loads(result.stdout)}
        self.assertEqual(entries[str(self.feature)], 'feature/login')
        self.assertTrue(entries[str(self.detached)].startswith('detached:'))
        self.assertEqual(len(entries), 3)
        self.assertFalse(Path(str(self.state) + '.calls').exists())

    def test_rex_creates_then_focuses_without_duplicate(self):
        self.run_script()
        self.run_script()
        self.assertEqual(len(self.host()['tabs']), 1)
        self.assertEqual(self.host()['tabs'][0]['cwd'], str(self.feature))
        self.assertIn('focused:', self.run_script().stdout)

    def test_herdr_creates_then_focuses_without_duplicate(self):
        self.run_script(self.command('herdr'))
        self.run_script(self.command('herdr'))
        self.assertEqual(len(self.host()['tabs']), 1)
        self.assertEqual(self.host()['tabs'][0]['cwd'], str(self.feature))

    def test_existing_rex_tab_is_adopted_from_file_url(self):
        self.write_host({'tabs': [self.tab()]})
        self.assertIn('focused:', self.run_script().stdout)
        self.assertEqual(self.host()['focused'], 'window:existing')
        self.assertEqual(len(self.host()['tabs']), 1)

    def test_existing_herdr_tab_is_adopted_from_nested_folder(self):
        self.write_host({'tabs': [self.tab('herdr', self.feature / 'nested folder')]})
        self.run_script(self.command('herdr'))
        self.assertEqual(self.host()['focused'], 'tab:existing')
        self.assertEqual(len(self.host()['tabs']), 1)

    def test_recorded_tab_survives_rename_and_directory_change(self):
        self.run_script()
        data = self.host()
        data['tabs'][0].update({'label': 'new label', 'cwd': str(self.repo)})
        self.write_host(data)
        self.run_script()
        self.assertEqual(len(self.host()['tabs']), 1)

    def test_closed_tab_is_recreated(self):
        self.run_script()
        self.write_host({'tabs': []})
        self.run_script()
        self.assertEqual(len(self.host()['tabs']), 1)
        self.assertIn('created:', self.run_script(self.command(target=self.detached)).stdout)

    def test_same_title_in_another_worktree_is_not_reused(self):
        tab = self.tab(cwd=self.repo)
        tab['label'] = 'feature/login'
        self.write_host({'tabs': [tab]})
        self.run_script()
        self.assertEqual(len(self.host()['tabs']), 2)

    def test_symlink_selects_the_canonical_worktree(self):
        alias = self.tmp / 'alias'
        alias.symlink_to(self.feature, target_is_directory=True)
        self.run_script(self.command(target=alias))
        self.assertEqual(self.host()['tabs'][0]['cwd'], str(self.feature))

    def test_directory_outside_repo_is_rejected(self):
        result = self.run_script(self.command(target=self.tmp), success=False)
        self.assertIn('not a worktree', result.stderr)
        self.assertEqual(self.host()['tabs'], [])

    def test_subdirectory_cannot_be_selected_as_worktree(self):
        self.run_script(self.command(target=self.feature / 'nested folder'), success=False)
        self.assertEqual(self.host()['tabs'], [])

    def test_remote_herdr_space_is_rejected(self):
        self.write_host({'tabs': [], 'machine': 'remote-server'})
        self.run_script(self.command('herdr'), success=False)
        self.assertEqual(self.host()['tabs'], [])

    def test_focus_failure_does_not_create_another_tab(self):
        self.write_host({'tabs': [self.tab()], 'focus_failure': True})
        self.run_script(success=False)
        self.assertEqual(len(self.host()['tabs']), 1)

    def test_create_failure_leaves_no_state_or_lock(self):
        self.write_host({'tabs': [], 'create_failure': True})
        self.run_script(success=False)
        self.assertEqual(list((self.tmp / 'state').glob('*.json')), [])
        self.assertEqual(list((self.tmp / 'state').glob('*.lock')), [])

    def test_server_failure_does_not_create_tab(self):
        self.write_host({'tabs': [], 'list_failure': True})
        self.run_script(success=False)
        self.assertEqual(self.host()['tabs'], [])

    def test_corrupt_registry_is_not_silently_discarded(self):
        self.run_script()
        registry = next((self.tmp / 'state').glob('*.json'))
        registry.write_text('{invalid')
        self.run_script(success=False)
        self.assertEqual(len(self.host()['tabs']), 1)
        self.assertEqual(registry.read_text(), '{invalid')

    def test_cancel_does_not_contact_host(self):
        for code in [1, 130]:
            with self.subTest(exit_code=code):
                self.fake_picker(exit_code=code)
                self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--host', 'rex'])
                self.assertFalse(Path(str(self.state) + '.calls').exists())

    def test_picker_error_is_reported(self):
        self.fake_picker(exit_code=2)
        result = self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo)], success=False)
        self.assertIn('fzf failed', result.stderr)

    def test_picker_selects_a_real_worktree(self):
        entries = json.loads(self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--list']).stdout)
        index = next(i for i, e in enumerate(entries) if e['path'] == str(self.feature))
        self.fake_picker(index=index)
        self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--host', 'rex'])
        self.assertEqual(self.host()['tabs'][0]['cwd'], str(self.feature))

    def test_concurrent_selections_create_only_one_tab(self):
        self.write_host({'tabs': [], 'create_delay': 0.3})
        processes = [subprocess.Popen(self.command(), env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(len(self.host()['tabs']), 1)

    def test_nested_herdr_is_preferred_to_outer_rex(self):
        tab = self.tab('herdr', self.repo)
        self.write_host({'tabs': [tab]})
        env = dict(self.env, HC_TERMINAL_ID=tab['terminal'], REX_SESSION='outer-session')
        self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--path', str(self.feature)], env=env)
        self.assertTrue(self.host()['focused'].startswith('tab:'))

    def test_missing_host_context_reports_actionable_error(self):
        result = self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--path', str(self.feature)], success=False)
        self.assertIn('pass --host', result.stderr)

    def test_unknown_arguments_and_missing_values_fail(self):
        for args in [['--oops'], ['--host'], ['--host', 'unsupported']]:
            with self.subTest(args=args):
                self.run_script(['/bin/bash', str(SCRIPT), *args], success=False)

    def test_real_fzf_filters_generated_candidates(self):
        entries = self.run_script(['/bin/bash', str(SCRIPT), '--cwd', str(self.repo), '--list']).stdout
        menu = subprocess.run(['jq', '-r', '.[] | [.branch,.path] | @tsv'], input=entries, capture_output=True, text=True, check=True).stdout
        result = subprocess.run(['fzf', '--filter=feature/login'], input=menu, capture_output=True, text=True, env=dict(self.env, FZF_DEFAULT_OPTS='', FZF_DEFAULT_OPTS_FILE=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('feature/login', result.stdout)

if __name__ == '__main__':
    unittest.main(verbosity=2)
