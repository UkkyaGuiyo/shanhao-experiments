import json
import tempfile
import unittest
from pathlib import Path
from hello_world.pipeline import STAGES, display, run_stage
from tests.helpers import cli, new_run, remove_run

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.name, self.path = new_run()
        self.path.mkdir(parents=True)
    def tearDown(self):
        remove_run(self.path)
    def fill(self):
        for stage in STAGES:
            run_stage(stage, self.path)
        self.assertEqual(len(list(self.path.iterdir())), 4, "all mandatory artifacts must exist")
    def test_output_contract(self):
        result = cli("run", "--run-id", self.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"HELLO WORLD\n")
    def test_artifacts_reproducible(self):
        self.fill()
        self.assertEqual(len(list(self.path.iterdir())), 4)
        other_name, other = new_run()
        other.mkdir()
        try:
            for stage in STAGES:
                run_stage(stage, other)
            self.assertEqual({p.name:p.read_bytes() for p in self.path.iterdir()}, {p.name:p.read_bytes() for p in other.iterdir()})
        finally:
            remove_run(other)
    def test_each_missing_artifact_fails_without_stdout(self):
        self.fill()
        for stage in STAGES:
            p = self.path / (stage + ".json")
            data = p.read_bytes()
            p.unlink()
            result = cli("show", "--run-id", self.name)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            p.write_bytes(data)
    def test_each_modified_artifact_fails_without_stdout(self):
        self.fill()
        for stage in STAGES:
            p = self.path / (stage + ".json")
            data = p.read_bytes()
            value = json.loads(data)
            value["input_sha256"] = "0" * 64
            p.write_text(json.dumps(value))
            result = cli("show", "--run-id", self.name)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            p.write_bytes(data)
    def test_out_of_order_rejected(self):
        with self.assertRaises((ValueError, OSError)):
            run_stage("certificate", self.path)
    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            run_stage("unicorn", self.path)
    def test_duplicate_stage_rejected(self):
        run_stage("proposal", self.path)
        with self.assertRaises((ValueError, OSError)):
            run_stage("proposal", self.path)
    def test_extra_file_rejected(self):
        self.fill()
        (self.path / "surprise").write_text("x")
        with self.assertRaises(ValueError):
            display(self.path)
    def test_symlink_rejected(self):
        self.fill()
        source = self.path / "proposal.json"
        source.unlink()
        source.symlink_to("/etc/passwd")
        with self.assertRaises((ValueError, OSError)):
            display(self.path)
    def test_external_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_stage("proposal", Path(temporary))
    def test_minutes_depend_on_votes(self):
        self.fill()
        document = json.loads((self.path / "minutes.json").read_bytes())
        self.assertEqual("".join(row["character"] for row in document["payload"]["entries"]), "HELLO WORLD")
        self.assertTrue(all(row["certificate_seal"] for row in document["payload"]["entries"]))

    def test_existing_run_is_not_overwritten(self):
        self.fill()
        original = {p.name:p.read_bytes() for p in self.path.iterdir()}
        result = cli("run", "--run-id", self.name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(original, {p.name:p.read_bytes() for p in self.path.iterdir()})

    def test_changed_manifest_rejected(self):
        from unittest.mock import patch
        from hello_world.pipeline import EXPECTED_MANIFEST, load_manifest
        for mutate in (lambda m:m["steps"].reverse(), lambda m:m["steps"].pop(), lambda m:m["weeks"].append(m["weeks"][0])):
            value = json.loads(json.dumps(EXPECTED_MANIFEST))
            mutate(value)
            (self.path / "pipeline.json").write_text(json.dumps(value))
            with patch("hello_world.pipeline.ROOT", self.path):
                with self.assertRaises(ValueError):
                    load_manifest()

    def test_rejected_votes_cannot_be_certified(self):
        from hello_world.layers import w20261003 as layer
        ballot = layer.ballot(layer.proposal())
        for vote in ballot["ballots"][0]["votes"][:3]:
            vote["yes"] = False
        with self.assertRaises(ValueError):
            layer.certificate(ballot)
