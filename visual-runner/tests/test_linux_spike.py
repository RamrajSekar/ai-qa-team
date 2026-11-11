import subprocess
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from linux.check_dependencies import validate
from linux.process_tree import LinuxProcessTree
from linux.reconcile import finalize
from linux_reconcile_control import reconcile


class LinuxSpikeTests(unittest.TestCase):
    def test_cleanup_remnants_block_next_case_without_relabelling_cancellation(self):
        from linux.batch import cleanup_outcome
        self.assertEqual(cleanup_outcome('cancelled', True), 'cancelled')
        self.assertEqual(cleanup_outcome('timed_out', True), 'timed_out')
        self.assertEqual(cleanup_outcome('completed', True), 'interrupted')
        self.assertEqual(cleanup_outcome('failed', False), 'failed')
    @patch('linux_reconcile_control.subprocess.run')
    def test_host_reconciler_refuses_active_container_before_helper(self, execute):
        execute.return_value = MagicMock(returncode=0, stdout=json.dumps([{
            'Config': {'Labels': {'aiqa.m1a.guard': 'true'}},
            'State': {'Status': 'running', 'Running': True, 'Pid': 12}}]))
        with self.assertRaisesRegex(RuntimeError, 'CONTAINER_NOT_STOPPED'):
            reconcile('podman', 'm1a-guard-' + 'a'*12, 'b'*32)
        self.assertEqual(execute.call_count, 1)

    @patch('linux_reconcile_control.subprocess.run')
    def test_host_reconciler_refuses_unmanaged_container(self, execute):
        execute.return_value = MagicMock(returncode=0, stdout=json.dumps([{'Config': {'Labels': {}}}]))
        with self.assertRaisesRegex(RuntimeError, 'UNMANAGED_CONTAINER'):
            reconcile('podman', 'm1a-guard-' + 'a'*12, 'b'*32)
        self.assertEqual(execute.call_count, 1)

    def test_reconcile_preserves_evidence_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            path = workspace / 'state.json'
            path.write_text(json.dumps({'state': 'running', 'screenshots': ['01-open'], 'logs': []}))
            self.assertTrue(finalize(workspace, exit_code=137))
            original = path.read_bytes()
            state = json.loads(original)
            self.assertEqual(state['state'], 'interrupted')
            self.assertEqual(state['screenshots'], ['01-open'])
            self.assertFalse(state['reconciliation']['replayed'])
            self.assertFalse(finalize(workspace, exit_code=137))
            self.assertEqual(path.read_bytes(), original)

    def test_terminal_states_remain_byte_identical(self):
        for state in ['completed', 'failed', 'cancelled', 'timed_out', 'interrupted']:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as folder:
                workspace = Path(folder)
                path = workspace / 'state.json'
                path.write_text(json.dumps({'state': state, 'screenshots': ['01-open']}))
                original = path.read_bytes()
                self.assertFalse(finalize(workspace, reason='timed_out'))
                self.assertEqual(path.read_bytes(), original)

    def test_watchdog_finalization_marks_timeout_without_dropping_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            (workspace / 'state.json').write_text(json.dumps({'state': 'running', 'startup_stage': 'navigation'}))
            finalize(workspace, reason='timed_out', source='entrypoint_watchdog', exit_code=-9)
            state = json.loads((workspace / 'state.json').read_text())
            self.assertEqual(state['state'], 'timed_out')
            self.assertEqual(state['startup_stage'], 'navigation')
            self.assertEqual(state['reconciliation']['source'], 'entrypoint_watchdog')

    def test_dependency_guard_includes_transitive_distributions(self):
        validate(['robotframework', 'httpx', 'httpcore'])
        for name in ['selenium', 'Playwright', 'puppeteer', 'robotframework_browser', 'robotframework-SeleniumLibrary']:
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'PROHIBITED_RUNNER_DEPENDENCY'):
                validate(['robotframework', name])

    @patch('linux.process_tree.subprocess.Popen')
    def test_driver_starts_in_own_session(self, popen):
        tree = LinuxProcessTree()
        tree.launch(['fixed-driver'], stderr=subprocess.PIPE)
        popen.assert_called_once_with(['fixed-driver'], start_new_session=True, stderr=subprocess.PIPE)

    def test_cleanup_targets_owned_group_and_tolerates_already_exited(self):
        tree = LinuxProcessTree()
        tree.process = MagicMock(pid=123)
        with patch('linux.process_tree.os.killpg', create=True) as kill, patch('linux.process_tree.signal.SIGKILL', 9, create=True):
            tree.close()
            kill.assert_called_once_with(123, 9)
            kill.side_effect = ProcessLookupError
            tree.close()
        self.assertEqual(tree.browser_status(), 'unavailable')
