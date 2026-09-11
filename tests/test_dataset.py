"""Tests for dataset scanning. Run with: python -m pytest tests/ -q"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dataset import scan_dataset  # noqa: E402


def test_nested_layout(tmp_path):
    for subject, files in {"chb01": ["chb01_03.edf", "chb01_01.edf"], "chb02": ["chb02_01.edf"]}.items():
        d = tmp_path / subject
        d.mkdir()
        for f in files:
            (d / f).write_bytes(b"")
        (d / "notes.txt").write_bytes(b"")

    result = scan_dataset(str(tmp_path))
    assert set(result) == {"chb01", "chb02"}
    assert [r["filename"] for r in result["chb01"]["recordings"]] == ["chb01_01.edf", "chb01_03.edf"]


def test_flat_layout(tmp_path):
    (tmp_path / "a.edf").write_bytes(b"")
    (tmp_path / "b.fif").write_bytes(b"")
    result = scan_dataset(str(tmp_path))
    assert set(result) == {"All files"}
    assert len(result["All files"]["recordings"]) == 2


def test_mixed_layout(tmp_path):
    (tmp_path / "loose.edf").write_bytes(b"")
    d = tmp_path / "chb01"
    d.mkdir()
    (d / "chb01_01.edf").write_bytes(b"")
    result = scan_dataset(str(tmp_path))
    assert set(result) == {"All files", "chb01"}


def test_missing_folder():
    assert scan_dataset("/definitely/not/here") == {}


def test_empty_folder(tmp_path):
    assert scan_dataset(str(tmp_path)) == {}
