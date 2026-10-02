"""Mandatory ordered chain; every read revalidates all dependencies."""
import hashlib
import json
from hello_world.layers import w20261003 as layer
from hello_world.storage import ArtifactStore, ROOT, STAGES, canonical
from hello_world.safeio import read_regular

EXPECTED_MANIFEST = {
    "version": 1, "seed": layer.SEED, "weeks": [layer.WEEK],
    "steps": [{"id": stage, "week": layer.WEEK, "module": "w20261003",
               "requires": STAGES[i - 1] if i else None} for i, stage in enumerate(STAGES)],
}

def load_manifest():
    path = ROOT / "pipeline.json"
    manifest = json.loads(read_regular(path, 16384))
    if manifest != EXPECTED_MANIFEST:
        raise ValueError("unknown, missing or reordered pipeline stage")
    return manifest

def envelope(stage, previous):
    return {"stage": stage, "week": layer.WEEK, "seed": layer.SEED,
            "input_sha256": hashlib.sha256(canonical(previous)).hexdigest(),
            "payload": layer.BUILDERS[stage](previous["payload"] if previous else None)}

def verified_prefix(store, stages):
    previous = None
    for stage in stages:
        expected = envelope(stage, previous)
        if store.read(stage) != canonical(expected):
            raise ValueError("artifact altered or stale: " + stage)
        previous = expected
    return previous

def run_stage(stage, work_dir):
    load_manifest()
    if stage not in STAGES:
        raise ValueError("unknown stage")
    index = STAGES.index(stage)
    with ArtifactStore(work_dir) as store:
        store.expect(STAGES[:index])
        previous = verified_prefix(store, STAGES[:index])
        store.write(stage, envelope(stage, previous))

def display(work_dir):
    load_manifest()
    with ArtifactStore(work_dir) as store:
        store.expect(STAGES)
        minutes = verified_prefix(store, STAGES)
    output = "".join(entry["character"] for entry in minutes["payload"]["entries"])
    return output.encode("ascii") + b"\n"
