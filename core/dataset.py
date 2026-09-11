"""
Dataset scanning — turns a folder of recordings into a subject -> recordings tree.

Two folder shapes are recognised:

  flat                          nested (one folder per subject)
  ----                          ------------------------------
  dataset/                      dataset/
    rec1.edf                      chb01/
    rec2.edf                        chb01_01.edf
                                    chb01_03.edf
                                  chb02/
                                    chb02_01.edf

A flat folder is reported under the single subject name "All files".
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, TypedDict

SUPPORTED_FORMATS = (".edf", ".bdf", ".fif", ".set", ".vhdr")


class Recording(TypedDict):
    filename: str
    path: str


class Subject(TypedDict):
    path: str
    recordings: List[Recording]


def _recordings_in(folder: Path) -> List[Recording]:
    found = [
        {"filename": p.name, "path": str(p)}
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_FORMATS
    ]
    return sorted(found, key=lambda r: r["filename"])


def scan_dataset(root_dir: str) -> Dict[str, Subject]:
    """
    Scan *root_dir* and return ``{subject_id: {"path": ..., "recordings": [...]}}``.

    Subjects with no recordings are omitted. Returns an empty dict when the
    path does not exist or holds nothing readable.
    """
    root = Path(root_dir)
    if not root.is_dir():
        return {}

    structure: Dict[str, Subject] = {}

    top_level = _recordings_in(root)
    if top_level:
        structure["All files"] = {"path": str(root), "recordings": top_level}

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        recordings = _recordings_in(child)
        if recordings:
            structure[child.name] = {"path": str(child), "recordings": recordings}

    return structure
