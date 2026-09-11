"""Tests for the annotation parsers. Run with: python -m pytest tests/ -q"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.annotations import (  # noqa: E402
    CHBMITAnnotationParser,
    CSVAnnotationParser,
    TUHAnnotationParser,
    load_annotations_for_file,
    is_seizure,
)

SUMMARY = """\
Data Sampling Rate: 256 Hz

File Name: chb01_01.edf
Number of Seizures in File: 0

File Name: chb01_03.edf
Number of Seizures in File: 1
Seizure Start Time: 2996 seconds
Seizure End Time: 3036 seconds

File Name: chb01_04.edf
Number of Seizures in File: 2
Seizure 1 Start Time: 1467 seconds
Seizure 1 End Time: 1494 seconds
Seizure 2 Start Time: 1732 seconds
Seizure 2 End Time: 1772 seconds
"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_chbmit_unnumbered_seizure(tmp_path):
    path = _write(tmp_path, "chb01-summary.txt", SUMMARY)
    events = CHBMITAnnotationParser().parse(path, "chb01_03.edf")
    assert len(events) == 1
    assert events[0]["start_time"] == 2996.0
    assert events[0]["end_time"] == 3036.0
    assert events[0]["label"] == "seizure"


def test_chbmit_numbered_seizures(tmp_path):
    path = _write(tmp_path, "chb01-summary.txt", SUMMARY)
    events = CHBMITAnnotationParser().parse(path, "chb01_04.edf")
    assert [(e["start_time"], e["end_time"]) for e in events] == [
        (1467.0, 1494.0),
        (1732.0, 1772.0),
    ]


def test_chbmit_file_without_seizures(tmp_path):
    path = _write(tmp_path, "chb01-summary.txt", SUMMARY)
    assert CHBMITAnnotationParser().parse(path, "chb01_01.edf") == []


def test_chbmit_all_files_when_no_target(tmp_path):
    path = _write(tmp_path, "chb01-summary.txt", SUMMARY)
    assert len(CHBMITAnnotationParser().parse(path)) == 3


def test_chbmit_missing_file_is_empty(tmp_path):
    assert CHBMITAnnotationParser().parse(str(tmp_path / "nope.txt")) == []


def test_csv_column_aliases(tmp_path):
    path = _write(tmp_path, "events.csv", "onset,offset,event,note\n10.0,12.5,artifact,eye blink\n")
    events = CSVAnnotationParser().parse(path)
    assert len(events) == 1
    assert events[0]["start_time"] == 10.0
    assert events[0]["end_time"] == 12.5
    assert events[0]["label"] == "artifact"


def test_csv_skips_unparsable_rows(tmp_path):
    path = _write(tmp_path, "events.csv", "start,end,label\n1.0,2.0,a\nbad,rows,b\n3.0,4.0,c\n")
    assert len(CSVAnnotationParser().parse(path)) == 2


def test_tuh_tse(tmp_path):
    path = _write(tmp_path, "rec.tse", "version = tse_v1.0.0\n\n0.0 10.0 bckg 1.0\n10.0 25.0 seiz 1.0\n")
    events = TUHAnnotationParser().parse(path)
    assert [e["label"] for e in events] == ["bckg", "seiz"]
    assert events[1]["start_time"] == 10.0


def test_load_merges_and_deduplicates(tmp_path):
    _write(tmp_path, "chb01-summary.txt", SUMMARY)
    _write(tmp_path, "chb01_03-summary.txt", SUMMARY)   # same seizure, second source
    _write(tmp_path, "annotations.csv", "start,end,label\n5.0,6.0,artifact\n")
    edf = tmp_path / "chb01_03.edf"
    edf.write_bytes(b"")                                 # unreadable on purpose

    events = load_annotations_for_file(str(edf))
    assert len(events) == 2                              # seizure counted once
    assert [e["start_time"] for e in events] == [5.0, 2996.0]   # sorted by onset


def test_is_seizure():
    assert is_seizure({"label": "seizure", "description": "Seizure #1"})
    assert is_seizure({"label": "seiz", "description": ""})
    assert not is_seizure({"label": "artifact", "description": "eye blink"})
