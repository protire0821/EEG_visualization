"""
Annotation parsing for EEG recordings.

Four sources are supported, each behind the same `AnnotationParser` interface:

  * CHB-MIT  -- the ``chbNN-summary.txt`` files shipped with the PhysioNet
                CHB-MIT Scalp EEG Database
  * CSV      -- a simple ``start,end,label,description`` table
  * EDF+     -- annotations stored inside the recording itself
  * TUH      -- ``.tse`` / ``.csv_bi`` files from the Temple University Hospital
                EEG corpus

Every parser returns the same record shape::

    {
        "start_time": float,   # seconds from the start of the recording
        "end_time":   float,   # seconds
        "label":      str,     # e.g. "seizure"
        "description": str,
        "metadata":   dict,
    }

`load_annotations_for_file` tries all of them for a given recording and returns
whatever it finds, so callers do not need to know which corpus they are holding.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

Annotation = Dict[str, Any]


class AnnotationParser(ABC):
    """Common interface: parse a source into a list of annotation records."""

    @abstractmethod
    def parse(self, source: str, *args, **kwargs) -> List[Annotation]:
        raise NotImplementedError


class CHBMITAnnotationParser(AnnotationParser):
    """
    Parser for CHB-MIT summary files.

    A summary file describes every recording of one subject::

        File Name: chb01_03.edf
        File Start Time: 13:43:04
        Number of Seizures in File: 1
        Seizure Start Time: 2996 seconds
        Seizure End Time: 3036 seconds

    Some subjects number their seizures (``Seizure 1 Start Time:``); both
    spellings are accepted.
    """

    _FILE_RE = re.compile(r"File Name:\s*(\S+)", re.IGNORECASE)
    _START_RE = re.compile(r"Seizure.*?Start Time:\s*(\d+(?:\.\d+)?)\s*seconds?", re.IGNORECASE)
    _END_RE = re.compile(r"Seizure.*?End Time:\s*(\d+(?:\.\d+)?)\s*seconds?", re.IGNORECASE)

    def parse(self, summary_file: str, target_filename: Optional[str] = None) -> List[Annotation]:
        """
        Read *summary_file*; when *target_filename* is given, return only the
        seizures belonging to that recording.
        """
        if not os.path.exists(summary_file):
            return []

        try:
            with open(summary_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            print(f"[annotations] cannot read {summary_file}: {exc}")
            return []

        annotations: List[Annotation] = []
        seizure_no = 0

        # Split ahead of each "File Name:" line. The lookahead is non-capturing
        # so re.split does not interleave the captured names into the result.
        blocks = re.split(r"(?=File Name:)", content, flags=re.IGNORECASE)

        for block in blocks:
            file_match = self._FILE_RE.search(block)
            if not file_match:
                continue
            current_file = file_match.group(1).strip()

            if target_filename and current_file.lower() != target_filename.lower():
                continue

            starts = self._START_RE.findall(block)
            ends = self._END_RE.findall(block)

            for start, end in zip(starts, ends):
                seizure_no += 1
                start_time, end_time = float(start), float(end)
                annotations.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "label": "seizure",
                    "description": f"Seizure #{seizure_no}",
                    "metadata": {
                        "source": "chb-mit-summary",
                        "seizure_number": seizure_no,
                        "duration": end_time - start_time,
                        "file": current_file,
                    },
                })

        return annotations


class CSVAnnotationParser(AnnotationParser):
    """
    Parser for a plain CSV event table::

        start,end,label,description
        120.5,135.2,seizure,Focal seizure

    Column names are matched case-insensitively and a few common aliases are
    accepted (``onset``/``offset``, ``type``/``event``, ``note``).
    """

    _ALIASES = {
        "start": ["start", "start_time", "onset"],
        "end": ["end", "end_time", "offset"],
        "label": ["label", "type", "event"],
        "description": ["description", "desc", "note"],
    }

    def parse(self, csv_file: str) -> List[Annotation]:
        if not os.path.exists(csv_file):
            return []

        import csv as _csv

        try:
            with open(csv_file, "r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = _csv.DictReader(f)
                if not reader.fieldnames:
                    return []
                cols = {
                    key: self._find_column(reader.fieldnames, names)
                    for key, names in self._ALIASES.items()
                }
                annotations = []
                for row in reader:
                    try:
                        start = float(row[cols["start"]]) if cols["start"] else 0.0
                        end = float(row[cols["end"]]) if cols["end"] else 0.0
                    except (TypeError, ValueError):
                        continue
                    annotations.append({
                        "start_time": start,
                        "end_time": end,
                        "label": (row.get(cols["label"]) or "unknown") if cols["label"] else "unknown",
                        "description": (row.get(cols["description"]) or "") if cols["description"] else "",
                        "metadata": {"source": "csv"},
                    })
                return annotations
        except OSError as exc:
            print(f"[annotations] cannot read {csv_file}: {exc}")
            return []

    @staticmethod
    def _find_column(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
        lowered = [c.lower() for c in fieldnames]
        for name in candidates:
            if name in lowered:
                return fieldnames[lowered.index(name)]
        return None


class EDFAnnotationParser(AnnotationParser):
    """Reads annotations embedded in an EDF+ / BDF+ recording."""

    def parse(self, edf_file: str) -> List[Annotation]:
        import mne

        try:
            raw = mne.io.read_raw_edf(edf_file, preload=False, verbose=False)
        except Exception as exc:
            print(f"[annotations] cannot read EDF annotations from {edf_file}: {exc}")
            return []

        if not getattr(raw, "annotations", None) or len(raw.annotations) == 0:
            return []

        return [
            {
                "start_time": float(a["onset"]),
                "end_time": float(a["onset"]) + float(a["duration"]),
                "label": str(a["description"]),
                "description": str(a["description"]),
                "metadata": {"source": "edf-annotation", "duration": float(a["duration"])},
            }
            for a in raw.annotations
        ]


class TUHAnnotationParser(AnnotationParser):
    """Parser for TUH EEG ``.tse`` / ``.csv_bi`` term-based label files."""

    def parse(self, tse_file: str) -> List[Annotation]:
        if not os.path.exists(tse_file):
            return []

        annotations: List[Annotation] = []
        with open(tse_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.lower().startswith("version"):
                    continue
                parts = [p.strip() for p in re.split(r"[,\s]+", line)]
                if len(parts) < 3:
                    continue
                try:
                    start, end = float(parts[0]), float(parts[1])
                except ValueError:
                    continue  # header row
                label = parts[2]
                annotations.append({
                    "start_time": start,
                    "end_time": end,
                    "label": label,
                    "description": label,
                    "metadata": {"source": "tuh-tse"},
                })
        return annotations


class AnnotationParserFactory:
    """Registry of parsers, with extension-based auto-detection."""

    _parsers = {
        "chb-mit": CHBMITAnnotationParser,
        "csv": CSVAnnotationParser,
        "edf": EDFAnnotationParser,
        "tuh": TUHAnnotationParser,
    }

    @classmethod
    def get_parser(cls, parser_type: str) -> AnnotationParser:
        parser_class = cls._parsers.get(parser_type.lower())
        if parser_class is None:
            raise ValueError(f"unknown annotation format: {parser_type}")
        return parser_class()

    @classmethod
    def register_parser(cls, name: str, parser_class: type) -> None:
        cls._parsers[name.lower()] = parser_class

    @classmethod
    def auto_detect(cls, file_path: str) -> AnnotationParser:
        ext = os.path.splitext(file_path)[1].lower()
        if "summary" in os.path.basename(file_path).lower():
            return cls.get_parser("chb-mit")
        if ext == ".csv":
            return cls.get_parser("csv")
        if ext in (".edf", ".bdf"):
            return cls.get_parser("edf")
        if ext in (".tse", ".csv_bi"):
            return cls.get_parser("tuh")
        return cls.get_parser("csv")


def load_annotations_for_file(eeg_file_path: str) -> List[Annotation]:
    """
    Find every annotation that belongs to *eeg_file_path*.

    Sources are tried in order and the results concatenated:

      1. annotations embedded in the EDF+/BDF+ file
      2. a sibling CSV with the same stem (``rec.edf`` -> ``rec.csv``)
      3. a per-recording CHB-MIT summary (``chb01_03-summary.txt``)
      4. a per-subject CHB-MIT summary (``chb01-summary.txt``)
      5. ``annotations.csv`` in the same directory

    Duplicate events (same start, end and label) are collapsed, so a seizure
    listed in both a per-file and a per-subject summary appears once.
    """
    filename = os.path.basename(eeg_file_path)
    dir_name = os.path.dirname(eeg_file_path)
    stem = os.path.splitext(eeg_file_path)[0]
    found: List[Annotation] = []

    if eeg_file_path.lower().endswith((".edf", ".bdf")):
        try:
            found += EDFAnnotationParser().parse(eeg_file_path)
        except Exception:
            pass  # an EDF without annotations is the normal case

    sibling_csv = stem + ".csv"
    if os.path.exists(sibling_csv):
        found += CSVAnnotationParser().parse(sibling_csv)

    per_file_summary = stem + "-summary.txt"
    if os.path.exists(per_file_summary):
        found += CHBMITAnnotationParser().parse(per_file_summary, filename)

    subject_match = re.match(r"(chb\d+)", filename, re.IGNORECASE)
    if subject_match:
        subject_summary = os.path.join(dir_name, f"{subject_match.group(1).lower()}-summary.txt")
        if os.path.exists(subject_summary):
            found += CHBMITAnnotationParser().parse(subject_summary, filename)

    dir_csv = os.path.join(dir_name, "annotations.csv")
    if os.path.exists(dir_csv):
        found += CSVAnnotationParser().parse(dir_csv)

    seen = set()
    unique: List[Annotation] = []
    for a in found:
        key = (round(a["start_time"], 3), round(a["end_time"], 3), a["label"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)

    unique.sort(key=lambda a: a["start_time"])
    return unique


def is_seizure(annotation: Annotation) -> bool:
    """True when an annotation looks like a seizure event."""
    text = f"{annotation.get('label', '')} {annotation.get('description', '')}".lower()
    return "seizure" in text or "seiz" == annotation.get("label", "").lower()
