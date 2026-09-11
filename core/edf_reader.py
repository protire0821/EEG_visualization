"""
MNE-based recording loader with standard 10/20 montage mapping.

Exposes the full data for waveform display, a montage-aligned subset for the
topomap, and any annotations found alongside the recording.
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import mne

from core.annotations import load_annotations_for_file, is_seizure

SUPPORTED_FORMATS = (".edf", ".bdf", ".fif", ".set", ".vhdr")


class EDFReader:
    """
    Loads a recording with MNE, maps its channels onto the standard 10/20
    montage where possible, and collects its annotations.

    Attributes
    ----------
    raw         : mne.io.Raw      full MNE raw object
    data        : ndarray         (n_channels, n_samples), DC removed
    times       : ndarray         (n_samples,) time axis in seconds
    ch_names    : list[str]       all channel names
    sfreq       : float           sampling frequency in Hz
    annotations : list[dict]      every event found for this recording
    seizures    : list[dict]      the subset of annotations that are seizures
    """

    def __init__(self) -> None:
        self.raw: Optional[mne.io.BaseRaw] = None
        self.data: Optional[np.ndarray] = None
        self.times: Optional[np.ndarray] = None
        self.ch_names: List[str] = []
        self.sfreq: float = 256.0
        self.filepath: str = ""
        self.annotations: List[Dict[str, Any]] = []

        # EEG-only subset for the topomap (channels with valid 3-D positions)
        self._eeg_info: Optional[mne.Info] = None
        self._eeg_data: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, filepath: str) -> bool:
        """
        Load a recording, set the 10/20 montage, remove the per-channel DC
        offset and gather annotations. Raises on a fatal read error.
        """
        raw = self._read(filepath)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                raw.set_montage("standard_1020", match_case=False,
                                on_missing="warn", verbose=False)
            except Exception:
                pass  # a partial or missing montage is acceptable

        raw._data -= raw._data.mean(axis=1, keepdims=True)

        self.raw = raw
        self.filepath = filepath
        self.sfreq = float(raw.info["sfreq"])
        self.ch_names = list(raw.ch_names)
        self.data, self.times = raw.get_data(return_times=True)

        self._setup_eeg_subset(raw)
        self._load_annotations(filepath)
        return True

    @staticmethod
    def _read(filepath: str) -> mne.io.BaseRaw:
        ext = os.path.splitext(filepath)[1].lower()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if ext in (".edf", ".bdf"):
                return mne.io.read_raw_edf(filepath, preload=True, verbose=False)
            if ext == ".fif":
                return mne.io.read_raw_fif(filepath, preload=True, verbose=False)
            if ext == ".set":
                return mne.io.read_raw_eeglab(filepath, preload=True, verbose=False)
            if ext == ".vhdr":
                return mne.io.read_raw_brainvision(filepath, preload=True, verbose=False)
        raise ValueError(
            f"unsupported format '{ext}' — expected one of {', '.join(SUPPORTED_FORMATS)}"
        )

    @property
    def n_samples(self) -> int:
        return self.data.shape[1] if self.data is not None else 0

    @property
    def duration(self) -> float:
        if self.times is not None and len(self.times):
            return float(self.times[-1])
        return 0.0

    @property
    def has_montage(self) -> bool:
        """True when at least some channels carry valid 3-D positions."""
        return self._eeg_info is not None

    @property
    def montage_channels(self) -> List[str]:
        """Names of the channels that the topomap can use."""
        return list(self._eeg_info["ch_names"]) if self._eeg_info is not None else []

    @property
    def seizures(self) -> List[Dict[str, Any]]:
        return [a for a in self.annotations if is_seizure(a)]

    def get_topomap_data(self, frame_idx: int):
        """
        Return ``(data_1d, eeg_info)`` for ``mne.viz.plot_topomap`` at
        *frame_idx*, or ``(None, None)`` when unavailable.
        """
        if not self.has_montage or frame_idx >= self.n_samples:
            return None, None
        return self._eeg_data[:, frame_idx].copy(), self._eeg_info

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_eeg_subset(self, raw: mne.io.BaseRaw) -> None:
        """Pick the EEG channels that ended up with real montage positions."""
        picks = mne.pick_types(raw.info, eeg=True, exclude="bads")

        def positioned(idx: int) -> bool:
            # MNE leaves unmatched channels at NaN (not zero), and np.allclose
            # against NaN is False — so NaN must be excluded explicitly or
            # bipolar montages such as CHB-MIT's "FP1-F7" look positioned.
            loc = raw.info["chs"][idx]["loc"][:3]
            return bool(np.all(np.isfinite(loc))) and not np.allclose(loc, 0.0)

        valid = [p for p in picks if positioned(p)]

        if not valid:
            self._eeg_info = None
            self._eeg_data = None
            return

        valid_names = [raw.ch_names[i] for i in valid]
        raw_eeg = raw.copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_eeg.pick(valid_names)

        self._eeg_info = raw_eeg.info
        self._eeg_data = raw_eeg.get_data()

    def _load_annotations(self, filepath: str) -> None:
        try:
            self.annotations = load_annotations_for_file(filepath)
        except Exception as exc:
            print(f"[reader] annotation lookup failed: {exc}")
            self.annotations = []
