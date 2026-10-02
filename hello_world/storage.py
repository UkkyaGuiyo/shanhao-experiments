"""Fixed-name, bounded artifact storage under this checkout only."""
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = ROOT / ".hello-world" / "runs"
STAGES = ("proposal", "ballot", "certificate", "minutes")
MAX_ARTIFACT_BYTES = 65536

def valid_run_id(name):
    return isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) is not None

def prepare_directory(name):
    if not valid_run_id(name):
        raise ValueError("run-id must be 1–64 lowercase letters, digits or hyphens")
    path = ROOT
    for component in (".hello-world", "runs", name):
        path = path / component
        if path.is_symlink():
            raise ValueError("symlink directory refused")
        path.mkdir(mode=0o700, exist_ok=True)
        if not path.is_dir():
            raise ValueError("workspace must be a directory")
    return path

def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")

class ArtifactStore:
    def __init__(self, path):
        path = Path(path).absolute()
        if not valid_run_id(path.name) or path.parent != RUNS_ROOT:
            raise ValueError("workspace outside checkout's .hello-world/runs")
        for ancestor in (path, path.parent, path.parent.parent):
            if ancestor.is_symlink():
                raise ValueError("symlink workspace refused")
        self.fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    def __enter__(self):
        return self
    def __exit__(self, *_):
        os.close(self.fd)
    def expect(self, stages):
        if set(os.listdir(self.fd)) != {stage + ".json" for stage in stages}:
            raise ValueError("missing, extra, or out-of-order artifact")
    def read(self, stage):
        if stage not in STAGES:
            raise ValueError("unknown artifact")
        fd = os.open(stage + ".json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact is not a bounded regular file")
            with os.fdopen(fd, "rb", closefd=False) as source:
                data = source.read(MAX_ARTIFACT_BYTES + 1)
            if len(data) > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact too large")
            return data
        finally:
            os.close(fd)
    def write(self, stage, document):
        if stage not in STAGES:
            raise ValueError("unknown artifact")
        data = canonical(document)
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ValueError("artifact budget exceeded")
        fd = os.open(stage + ".json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            with os.fdopen(fd, "wb", closefd=False) as target:
                target.write(data)
        finally:
            os.close(fd)
