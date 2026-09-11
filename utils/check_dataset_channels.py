"""
Dataset channel check — scan a folder of recordings and report, per subject:
how many files there are, how many channels each has, and whether channel
names and sampling rates are consistent.

Only file headers are read, so this is fast even on large corpora.

Usage
-----
    python -m utils.check_dataset_channels /path/to/dataset
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.dataset import scan_dataset  # noqa: E402


def _read_header(path: str) -> Tuple[List[str], float]:
    """Return (channel_names, sfreq) without loading sample data."""
    import mne

    ext = os.path.splitext(path)[1].lower()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if ext in (".edf", ".bdf"):
            raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
        elif ext == ".fif":
            raw = mne.io.read_raw_fif(path, preload=False, verbose=False)
        elif ext == ".set":
            raw = mne.io.read_raw_eeglab(path, preload=False, verbose=False)
        elif ext == ".vhdr":
            raw = mne.io.read_raw_brainvision(path, preload=False, verbose=False)
        else:
            raise ValueError(f"unsupported format: {ext}")
    return list(raw.ch_names), float(raw.info["sfreq"])


def check(root: str) -> int:
    dataset = scan_dataset(root)
    if not dataset:
        print(f"No recordings found under {root}")
        return 1

    all_layouts: Dict[Tuple[str, ...], int] = defaultdict(int)
    all_rates: Counter = Counter()
    failures: List[Tuple[str, str]] = []

    for subject_id, entry in dataset.items():
        recordings = entry["recordings"]
        print(f"\n{subject_id}  —  {len(recordings)} recording(s)")

        layouts: Dict[Tuple[str, ...], int] = defaultdict(int)
        rates: Counter = Counter()

        for rec in recordings:
            try:
                names, sfreq = _read_header(rec["path"])
            except Exception as exc:
                failures.append((rec["filename"], str(exc)))
                print(f"  {rec['filename']:<28} ERROR  {exc}")
                continue

            key = tuple(names)
            layouts[key] += 1
            all_layouts[key] += 1
            rates[sfreq] += 1
            all_rates[sfreq] += 1
            print(f"  {rec['filename']:<28} {len(names):>3} ch   {sfreq:>7.1f} Hz")

        if len(layouts) > 1:
            print(f"  ! {len(layouts)} different channel layouts in this subject")
        if len(rates) > 1:
            print(f"  ! mixed sampling rates: {sorted(rates)}")

    print("\n" + "-" * 60)
    print(f"Subjects: {len(dataset)}   Recordings: {sum(len(e['recordings']) for e in dataset.values())}")
    print(f"Distinct channel layouts: {len(all_layouts)}")
    for layout, count in sorted(all_layouts.items(), key=lambda kv: -kv[1])[:5]:
        print(f"  {count:>4} file(s): {len(layout)} ch — {', '.join(layout[:6])}"
              f"{' …' if len(layout) > 6 else ''}")
    print(f"Sampling rates: {', '.join(f'{r:g} Hz ({n})' for r, n in sorted(all_rates.items()))}")
    if failures:
        print(f"\n{len(failures)} file(s) could not be read:")
        for name, err in failures[:10]:
            print(f"  {name}: {err}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("dataset", help="folder holding the recordings")
    args = parser.parse_args()
    return check(args.dataset)


if __name__ == "__main__":
    raise SystemExit(main())
