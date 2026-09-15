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
from core.filters import FilterSettings, FilterError, apply_filters
from core.montage import MontageMap, build_map

SUPPORTED_FORMATS = (".edf", ".bdf", ".fif", ".set", ".vhdr")


class EDFReader:
    """
    Loads a recording with MNE, maps its channels onto the standard 10/20
    montage where possible, and collects its annotations.

    Attributes
    ----------
    raw         : mne.io.Raw      full MNE raw object
    raw_data    : ndarray         (n_channels, n_samples), DC removed, unfiltered
    data        : ndarray         the same, with the display filters applied
    times       : ndarray         (n_samples,) time axis in seconds
    ch_names    : list[str]       all channel names
    sfreq       : float           sampling frequency in Hz
    annotations : list[dict]      every event found for this recording
    seizures    : list[dict]      the subset of annotations that are seizures
    """

    def __init__(self) -> None:
        self.raw: Optional[mne.io.BaseRaw] = None
        self.raw_data: Optional[np.ndarray] = None
        self.data: Optional[np.ndarray] = None
        self.times: Optional[np.ndarray] = None
        self.ch_names: List[str] = []
        self.sfreq: float = 256.0
        self.filepath: str = ""
        self.annotations: List[Dict[str, Any]] = []
        self.filters = FilterSettings()
        self.filter_warning: str = ""

        # EEG-only subset for the topomap (channels with valid 3-D positions)
        self._eeg_info: Optional[mne.Info] = None
        self._eeg_picks: List[int] = []
        self._montage: Optional[MontageMap] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, filepath: str) -> bool:
        """
        Load a recording, set the 10/20 montage, remove the per-channel DC
        offset and gather annotations. Raises on a fatal read error.
        """
        raw = self._read(filepath)

        raw._data -= raw._data.mean(axis=1, keepdims=True)

        self.raw = raw
        self.filepath = filepath
        self.sfreq = float(raw.info["sfreq"])
        self.ch_names = list(raw.ch_names)
        self.raw_data, self.times = raw.get_data(return_times=True)
        self.data = self.raw_data

        self._setup_eeg_subset(raw)
        self._load_annotations(filepath)

        # Loading must not fail because the current filter presets do not suit
        # this recording's sampling rate — show the data unfiltered instead.
        self.filter_warning = ""
        try:
            self.set_filters(self.filters)
        except FilterError as exc:
            self.data = self.raw_data
            self.filter_warning = str(exc)
        return True

    def set_filters(self, settings: FilterSettings) -> None:
        """
        Re-derive `data` from `raw_data` with *settings*. Raises FilterError if
        the settings do not suit this recording's sampling rate.
        """
        if self.raw_data is None:
            self.filters = settings
            return
        self.data = apply_filters(self.raw_data, self.sfreq, settings)
        self.filters = settings

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
    def is_bipolar(self) -> bool:
        """True when the recording is mostly bipolar pairs (CHB-MIT and friends)."""
        return bool(self._montage and self._montage.is_bipolar_recording)

    @property
    def renamed_channels(self) -> Dict[str, str]:
        """Original label -> montage name, for channels that needed normalising."""
        return dict(self._montage.rename) if self._montage else {}

    @property
    def montage_status(self) -> str:
        """A short explanation of whether a topomap is possible, and why not."""
        if self.has_montage:
            line = f"{len(self.montage_channels)} of {len(self.ch_names)} channels positioned"
            renamed = self.renamed_channels
            if renamed:
                first = next(iter(renamed.items()))
                line += f"\n({len(renamed)} normalised, e.g. {first[0]} → {first[1]})"
            return line

        if self.is_bipolar:
            example = next(
                (n for n, k in self._montage.kinds.items() if k == "bipolar"), "A-B"
            )
            return (
                f"Bipolar recording ({example} …).\n"
                "A topomap plots one value per electrode, but a bipolar channel\n"
                "is the difference between two of them — closer to a spatial\n"
                "derivative than to a potential — so there is no single place\n"
                "on the scalp to put it."
            )

        sample = ", ".join(self.ch_names[:3]) if self.ch_names else "—"
        return (
            "No electrode positions.\n"
            f"No channel name could be matched to the 10-20 system\n"
            f"(first labels: {sample}).\n"
            "Prefixes such as 'EEG ' and reference suffixes such as '-REF'\n"
            "are handled automatically; anything else needs renaming."
        )

    @property
    def _eeg_data(self) -> Optional[np.ndarray]:
        """Topomap channel subset of the *filtered* data."""
        if self._eeg_info is None or self.data is None:
            return None
        return self.data[self._eeg_picks]

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
        return self.data[self._eeg_picks, frame_idx].copy(), self._eeg_info

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_eeg_subset(self, raw: mne.io.BaseRaw) -> None:
        """
        Work out which channels can be placed on a scalp map.

        Names are normalised first (``EEG FP1-REF`` -> ``Fp1``) on a throwaway
        copy, because the montage match is literal and most corpora do not store
        bare 10-20 labels. The copy keeps the original channel order, so index i
        of the picked data still lines up with row i of ``self.data``.
        """
        self._montage = build_map(list(raw.ch_names))

        raw = raw.copy()
        if self._montage.rename:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw.rename_channels(self._montage.rename)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                raw.set_montage("standard_1020", match_case=False,
                                on_missing="ignore", verbose=False)
            except Exception:
                pass  # a partial or missing montage is acceptable

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
            self._eeg_picks = []
            return

        valid_names = [raw.ch_names[i] for i in valid]
        raw_eeg = raw.copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_eeg.pick(valid_names)

        # pick() keeps the original channel order, so row i of data[_eeg_picks]
        # lines up with _eeg_info["ch_names"][i].
        self._eeg_info = raw_eeg.info
        self._eeg_picks = valid

    def _load_annotations(self, filepath: str) -> None:
        try:
            self.annotations = load_annotations_for_file(filepath)
        except Exception as exc:
            print(f"[reader] annotation lookup failed: {exc}")
            self.annotations = []
