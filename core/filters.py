"""
Display filters — high-pass, low-pass and a line-noise notch.

These are the three controls on every clinical EEG review station, and EEG is
close to unreadable without them: without a high-pass the traces wander off
screen on sweat and electrode drift, and without a notch the mains hum buries
everything.

Zero-phase Butterworth (``sosfiltfilt``) is used throughout, so peaks and spike
onsets keep their timing — important when the point of looking is *when* an
event started. Filtering is applied for display only; the unfiltered data stays
on the reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, tf2sos

# Butterworth order per pass. sosfiltfilt runs the filter forwards and
# backwards, so the effective roll-off is twice this.
_ORDER = 4

# Notch quality factor: bandwidth = f0 / Q, so 50 Hz at Q=30 is ~1.7 Hz wide.
_NOTCH_Q = 30.0


@dataclass(frozen=True)
class FilterSettings:
    """
    High-pass / low-pass / notch corner frequencies in Hz. ``None`` disables
    that stage. The defaults are the usual clinical review settings.
    """

    high_pass: Optional[float] = 0.5
    low_pass: Optional[float] = 70.0
    notch: Optional[float] = 50.0

    def describe(self) -> str:
        parts = []
        parts.append(f"HP {self.high_pass:g} Hz" if self.high_pass else "HP off")
        parts.append(f"LP {self.low_pass:g} Hz" if self.low_pass else "LP off")
        parts.append(f"notch {self.notch:g} Hz" if self.notch else "notch off")
        return ", ".join(parts)

    @property
    def is_identity(self) -> bool:
        return not (self.high_pass or self.low_pass or self.notch)


class FilterError(ValueError):
    """Raised when a requested setting cannot be applied to this sampling rate."""


def validate(settings: FilterSettings, sfreq: float) -> None:
    """Raise FilterError if *settings* are impossible for a signal at *sfreq*."""
    nyquist = sfreq / 2.0
    hp, lp, notch = settings.high_pass, settings.low_pass, settings.notch

    if hp is not None and hp <= 0:
        raise FilterError("high-pass must be above 0 Hz")
    if lp is not None and lp >= nyquist:
        raise FilterError(f"low-pass must be below the Nyquist frequency ({nyquist:g} Hz)")
    if hp is not None and lp is not None and hp >= lp:
        raise FilterError("high-pass must be below the low-pass frequency")
    if notch is not None and not (0 < notch < nyquist):
        raise FilterError(f"notch must be between 0 and {nyquist:g} Hz")


def apply_filters(
    data: np.ndarray,
    sfreq: float,
    settings: FilterSettings,
) -> np.ndarray:
    """
    Return a filtered copy of *data* (shape ``(n_channels, n_samples)``).

    The original array is never modified. Stages run in the order notch,
    high-pass, low-pass; each is skipped when its frequency is ``None``.
    """
    if data is None or data.size == 0 or settings.is_identity:
        return data

    validate(settings, sfreq)

    # sosfiltfilt pads by 3 * (max section order), so very short recordings
    # cannot be filtered at all.
    min_len = 3 * (2 * _ORDER + 1)
    if data.shape[1] < min_len:
        raise FilterError(
            f"recording is too short to filter ({data.shape[1]} samples, "
            f"needs at least {min_len})"
        )

    out = np.asarray(data, dtype=np.float64)

    if settings.notch:
        b, a = iirnotch(settings.notch, _NOTCH_Q, fs=sfreq)
        out = sosfiltfilt(tf2sos(b, a), out, axis=1)

    if settings.high_pass:
        sos = butter(_ORDER, settings.high_pass, btype="highpass", fs=sfreq, output="sos")
        out = sosfiltfilt(sos, out, axis=1)

    if settings.low_pass:
        sos = butter(_ORDER, settings.low_pass, btype="lowpass", fs=sfreq, output="sos")
        out = sosfiltfilt(sos, out, axis=1)

    return np.ascontiguousarray(out)
