"""Tests for channel-name normalisation. Run with: python -m pytest tests/ -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.montage import (  # noqa: E402
    ChannelKind,
    build_map,
    classify,
    montage_names,
)


@pytest.fixture(scope="module")
def known():
    return {n.upper(): n for n in montage_names()}


@pytest.mark.parametrize(
    "label,electrode",
    [
        ("Fp1", "Fp1"),
        ("FP1", "Fp1"),
        ("fp1", "Fp1"),
        ("EEG FP1-REF", "Fp1"),       # TUH
        ("EEG FP1-LE", "Fp1"),        # TUH, linked-ear variant
        ("EEG Fp1", "Fp1"),
        ("Fp1-A1", "Fp1"),            # ear reference
        ("C3-M1", "C3"),              # mastoid reference
        ("O1-AV", "O1"),              # average reference
        ("T3", "T3"),                 # pre-1991 naming
        ("  Fz  ", "Fz"),
    ],
)
def test_single_electrodes(label, electrode, known):
    result = classify(label, known)
    assert result.kind == ChannelKind.ELECTRODE
    assert result.electrode == electrode


@pytest.mark.parametrize("label", ["FP1-F7", "F7-T7", "FZ-CZ", "P7-O1"])
def test_true_bipolar_pairs(label, known):
    assert classify(label, known).kind == ChannelKind.BIPOLAR


@pytest.mark.parametrize("label", ["ECG", "EKG1-EKG2", "PHOTIC-REF", "Trigger", "", "   "])
def test_non_eeg_channels(label, known):
    assert classify(label, known).kind == ChannelKind.OTHER


def test_tuh_recording_is_not_called_bipolar():
    names = ["EEG FP1-REF", "EEG F3-REF", "EEG C3-REF", "EKG1-EKG2"]
    m = build_map(names)
    assert not m.is_bipolar_recording
    assert m.n_electrode == 3 and m.n_other == 1
    assert m.rename["EEG FP1-REF"] == "Fp1"


def test_chbmit_recording_is_bipolar():
    m = build_map(["FP1-F7", "F7-T7", "T7-P7", "P7-O1"])
    assert m.is_bipolar_recording
    assert m.n_bipolar == 4 and m.rename == {}


def test_already_correct_names_are_not_renamed():
    m = build_map(["Fp1", "F3", "Cz"])
    assert m.rename == {}
    assert m.n_electrode == 3


def test_rename_collision_is_skipped():
    """A file holding both spellings must not merge two channels into one."""
    m = build_map(["Fp1", "EEG FP1-REF"])
    assert m.rename == {}


def test_kinds_cover_every_channel():
    names = ["EEG FP1-REF", "FP1-F7", "ECG"]
    m = build_map(names)
    assert set(m.kinds) == set(names)
    assert m.n_electrode + m.n_bipolar + m.n_other == len(names)
