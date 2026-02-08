"""Manifest persistence (load/save)."""

import json
from pathlib import Path

from .constants import MANIFEST_FILE, OUTPUT_DIR


def load_manifest(manifest_file: Path = MANIFEST_FILE) -> dict:
    """Load the manifest from disk, or return an empty structure."""
    if manifest_file.exists():
        return json.loads(manifest_file.read_text("utf-8"))
    return {"files": {}, "index_last_modified": None}


def save_manifest(
    manifest: dict,
    manifest_file: Path = MANIFEST_FILE,
    output_dir: Path = OUTPUT_DIR,
) -> None:
    """Write the manifest to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8"
    )
