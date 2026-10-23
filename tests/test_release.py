import unittest
from hello_world.release import publication_allowed, validate_weeks

class ReleaseTests(unittest.TestCase):
    def test_version_order(self):
        for weeks in (["2026-10-03", "2026-10-03"], ["2026-10-10", "2026-10-03"], [], ["not-a-date"]):
            with self.subTest(weeks=weeks), self.assertRaises(ValueError):
                validate_weeks(weeks)
    def test_no_publication_when_guard_fails(self):
        valid = dict(expected_sha="a"*40, actual_sha="a"*40, week="2026-10-03", completed=[], stopped=False, locked=True, tests_passed=True, reviewed=True)
        for patch in (dict(actual_sha="b"*40), dict(completed=["2026-10-03"]), dict(stopped=True), dict(locked=False), dict(tests_passed=False), dict(reviewed=False)):
            with self.subTest(patch=patch):
                calls = []
                if publication_allowed(**(valid | patch)):
                    calls.append("publish")
                self.assertEqual(calls, [])
    def test_ready_can_publish(self):
        self.assertTrue(publication_allowed(expected_sha="a"*40, actual_sha="a"*40, week="2026-10-03", completed=[], stopped=False, locked=True, tests_passed=True, reviewed=True))

    def test_clean_readme_smoke(self):
        import re
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path
        from tests.helpers import ROOT
        with tempfile.TemporaryDirectory(prefix="readme-", dir=ROOT / ".hello-world") as temporary:
            clean = Path(temporary)
            shutil.copytree(ROOT / "hello_world", clean / "hello_world", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy2(ROOT / "pipeline.json", clean / "pipeline.json")
            blocks = re.findall(r"```sh\n(.*?)```", (ROOT / "README.md").read_text(), re.S)
            self.assertGreaterEqual(len(blocks), 7)
            for block in blocks:
                # The aggregate suite runs outside this test; avoid recursive unittest.
                block = block.replace("python3 -B -m unittest discover -s tests -v", "")
                for module in ("language", "history", "punchcards", "pipeline", "release", "sandbox"):
                    block = block.replace("python3 -I -B tools/verify.py . tests -v tests.test_" + module, "")
                result = subprocess.run(["/bin/sh", "-eu", "-c", block], cwd=clean, capture_output=True, timeout=12)
                self.assertEqual(result.returncode, 0, (block, result.stderr))
                if "hello_world.cli show" in block:
                    self.assertEqual(result.stdout, b"HELLO WORLD\n")
            self.assertIn(b"12-byte audit: OK", result.stdout)
