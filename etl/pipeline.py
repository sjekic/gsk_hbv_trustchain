"""Minimal orchestration sketch for the TrustChain ETL."""

from hashlib import sha256
from pathlib import Path
import json


def hash_file(path: str) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(artifact_paths: list[str]) -> dict:
    return {
        "artifacts": [{"path": p, "sha256": hash_file(p)} for p in artifact_paths]
    }


def save_manifest(artifact_paths: list[str], out_path: str) -> str:
    manifest = build_manifest(artifact_paths)
    Path(out_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path
