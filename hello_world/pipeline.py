"""Mandatory ordered chain; every read revalidates all dependencies."""
import hashlib
import json
from hello_world.layers import w20261003 as layer
from hello_world.layers import w20261010 as language
from hello_world.layers import w20261017 as history
from hello_world.layers import w20261024 as typesetter
from hello_world.storage import ArtifactStore, ROOT, STAGES, canonical
from hello_world.safeio import read_regular

EXPECTED_MANIFEST = {
    "version": 4, "seed": layer.SEED, "weeks": [layer.WEEK, language.WEEK, history.WEEK, typesetter.WEEK],
    "steps": [
        {"id": "dictionary", "week": language.WEEK, "module": "w20261010", "requires": None},
        {"id": "translation", "week": language.WEEK, "module": "w20261010", "requires": "dictionary"},
        {"id": "roundtrip", "week": language.WEEK, "module": "w20261010", "requires": "translation"},
        {"id": "proposal", "week": layer.WEEK, "module": "w20261003", "requires": "roundtrip"},
        {"id": "ballot", "week": layer.WEEK, "module": "w20261003", "requires": "proposal"},
        {"id": "history", "week": history.WEEK, "module": "w20261017", "requires": "ballot"},
        {"id": "certificate", "week": layer.WEEK, "module": "w20261003", "requires": "history"},
        {"id": "minutes", "week": layer.WEEK, "module": "w20261003", "requires": "certificate"},
        {"id": "punchcards", "week": typesetter.WEEK, "module": "w20261024", "requires": "minutes"},
    ],
}

BUILDERS = layer.BUILDERS | {"proposal": lambda _: language.proposal(), "ballot": language.ballot,
                             "certificate": history.certificate, "minutes": typesetter.minutes}

def load_manifest():
    path = ROOT / "pipeline.json"
    manifest = json.loads(read_regular(path, 16384))
    if manifest != EXPECTED_MANIFEST:
        raise ValueError("unknown, missing or reordered pipeline stage")
    return manifest

def envelope(stage, previous):
    return {"stage": stage, "week": layer.WEEK, "seed": layer.SEED,
            "input_sha256": hashlib.sha256(canonical(previous)).hexdigest(),
            "payload": BUILDERS[stage](previous["payload"] if previous else None)}

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
    return typesetter.decode(minutes["payload"])
