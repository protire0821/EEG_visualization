"""Tests for the display filters. Run with: python -m pytest tests/ -q"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.filters import (  # noqa: E402
    FilterError,
    FilterSettings,
    apply_filters,
    validate,
)

SFREQ = 256.0
DURATION = 20.0


def _signal():
    """Drift + alpha + mains + high-frequency noise, in volts."""
    t = np.arange(int(SFREQ * DURATION)) / SFREQ
    sig = (
        50e-6 * np.sin(2 * np.pi * 0.1 * t)   # electrode drift
        + 30e-6 * np.sin(2 * np.pi * 10 * t)  # alpha
        + 40e-6 * np.sin(2 * np.pi * 50 * t)  # mains
        + 20e-6 * np.sin(2 * np.pi * 90 * t)  # EMG-ish
    )
    return t, np.stack([sig, sig])


def _amplitude(x, t, freq):
    return 2 * np.abs(np.sum(x * np.exp(-2j * np.pi * freq * t))) / len(t)


def test_bands_are_attenuated_and_alpha_survives():
    t, data = _signal()
    out = apply_filters(data, SFREQ, FilterSettings(0.5, 70.0, 50.0))

    assert _amplitude(out[0], t, 0.1) < 1e-6    # drift gone
    assert _amplitude(out[0], t, 50) < 2e-6     # mains gone
    assert _amplitude(out[0], t, 90) < 2e-6     # above the low-pass
    assert _amplitude(out[0], t, 10) > 25e-6    # alpha kept


def test_input_is_not_modified():
    _, data = _signal()
    original = data.copy()
    apply_filters(data, SFREQ, FilterSettings())
    assert np.array_equal(data, original)


def test_shape_is_preserved():
    _, data = _signal()
    out = apply_filters(data, SFREQ, FilterSettings())
    assert out.shape == data.shape


def test_identity_settings_return_input():
    _, data = _signal()
    assert apply_filters(data, SFREQ, FilterSettings(None, None, None)) is data


def test_zero_phase_keeps_peak_timing():
    """A filtered transient must not shift in time."""
    t = np.arange(int(SFREQ * 10)) / SFREQ
    spike = np.zeros_like(t)
    centre = len(t) // 2
    spike[centre - 12 : centre + 12] = 100e-6 * np.hanning(24)
    out = apply_filters(np.stack([spike]), SFREQ, FilterSettings(0.5, 70.0, None))
    assert abs(int(np.argmax(np.abs(out[0]))) - centre) <= 2


def test_describe():
    assert FilterSettings(0.5, 70.0, 50.0).describe() == "HP 0.5 Hz, LP 70 Hz, notch 50 Hz"
    assert FilterSettings(None, None, None).describe() == "HP off, LP off, notch off"


@pytest.mark.parametrize(
    "settings",
    [
        FilterSettings(70.0, 0.5, None),     # high-pass above low-pass
        FilterSettings(0.5, 200.0, None),    # low-pass above Nyquist
        FilterSettings(0.5, 70.0, 300.0),    # notch above Nyquist
        FilterSettings(-1.0, 70.0, None),    # negative high-pass
    ],
)
def test_invalid_settings_are_rejected(settings):
    with pytest.raises(FilterError):
        validate(settings, SFREQ)


def test_recording_too_short():
    with pytest.raises(FilterError):
        apply_filters(np.zeros((2, 10)), SFREQ, FilterSettings())
