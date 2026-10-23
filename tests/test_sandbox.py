"""Bounded runner tests; these do not claim namespace isolation."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from hello_world.sandbox import run_bounded
from tests.helpers import ROOT, cli, new_run, remove_run

class SandboxTests(unittest.TestCase):
    def test_output_contract(self):
        name, path = new_run()
        try:
            result = cli("run", "--run-id", name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"HELLO WORLD\n")
        finally:
            remove_run(path)
    def test_heavy_requires_confirmation(self):
        with self.assertRaises(ValueError):
            run_bounded(["run", "test"], mode="heavy", confirm_heavy=True)
    def test_unknown_command_rejected(self):
        with self.assertRaises(ValueError):
            run_bounded(["/bin/sh", "-c", "echo ignored"])
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            run_bounded(["run", "../../other"])
    def test_live_process_limits(self):
        name, path = new_run()
        try:
            result = cli("limits", "--run-id", name)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stderr.splitlines()[0])
            self.assertEqual(record["worker"]["address_space_bytes"], 192 * 1024**2)
            self.assertEqual(record["supervisor"]["address_space_bytes"], 64 * 1024**2)
            self.assertEqual(record["worker"]["cpu_seconds"], 8)
            self.assertEqual(record["worker"]["file_bytes"], 1024**2)
            self.assertEqual(record["worker"]["cpus"], record["supervisor"]["cpus"])
            self.assertEqual(len(record["worker"]["cpus"]), 1)
        finally:
            remove_run(path)
    def probe(self, kind):
        name, _ = new_run()
        name = "probe-" + kind + "-" + name[5:]
        path = ROOT / ".hello-world" / "runs" / name
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(remove_run, path)
        return subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tests" / "runner_probe.py"), kind, name], cwd=ROOT, capture_output=True, timeout=11), path
    def test_memory_cap_enforced(self):
        result, _ = self.probe("memory")
        self.assertEqual(result.stdout, b"0\n", result.stderr)
        self.assertIn(b"memory-denied", result.stderr)
    def test_file_cap_enforced(self):
        result, path = self.probe("file")
        self.assertEqual(result.stdout, b"0\n", result.stderr)
        self.assertIn(b"file-denied", result.stderr)
        self.assertLessEqual((path / "fixture.bin").stat().st_size, 1024**2)
    def test_cpu_cap_enforced(self):
        result, _ = self.probe("cpu")
        self.assertNotEqual(result.stdout, b"0\n")
        self.assertIn(b"worker failed with status -9", result.stderr)
    def test_timeout_reaps_worker(self):
        result, path = self.probe("timeout")
        self.assertNotEqual(result.stdout, b"0\n")
        self.assertIn(b"deadline", result.stderr)
        pid = int((path / "pid").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
    def test_logs_bounded(self):
        result, _ = self.probe("log")
        self.assertNotEqual(result.stdout, b"0\n")
        self.assertLessEqual(len(result.stderr), 64 * 1024)
        self.assertIn(b"output budget", result.stderr)
    def test_no_network_or_child_creation_in_worker_graph(self):
        paths = [ROOT / "hello_world" / name for name in ("worker.py", "pipeline.py", "storage.py", "limits.py", "safeio.py", "layers/w20261003.py", "layers/w20261010.py", "layers/w20261017.py", "layers/w20261024.py", "history_verifier.py")]
        banned = {"socket", "http", "urllib", "requests", "subprocess", "multiprocessing", "threading", "ctypes", "asyncio"}
        for path in paths:
            self.assertTrue(path.exists(), path)
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({n.name.split('.')[0] for n in node.names} & banned, path)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0], banned, path)
                if isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                    self.assertNotIn(name, {"eval", "exec", "compile", "__import__", "fork", "forkpty", "posix_spawn", "system", "popen", "spawnv", "execv"}, path)

    def test_probe_run_name_is_unique(self):
        result, path = self.probe("memory")
        self.assertNotEqual(path.name, "memory")

    def test_fifo_configuration_fails_fast(self):
        name, path = new_run()
        (path / "hello_world").mkdir(parents=True)
        self.addCleanup(remove_run, path)
        os.mkfifo(path / "hello_world" / "limits.json")
        try:
            result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tests" / "config_probe.py"), str(path)], capture_output=True, timeout=0.5)
        except subprocess.TimeoutExpired:
            self.fail("configuration FIFO blocked supervisor preflight")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_lock_rejects_concurrent_writer(self):
        import fcntl
        name, path = new_run()
        self.addCleanup(remove_run, path)
        locks = ROOT / ".hello-world" / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        with (locks / (name + ".lock")).open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = cli("run", "--run-id", name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(list(path.iterdir()), [])
