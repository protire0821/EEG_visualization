"""
Channel-name normalisation for montage matching.

Electrode positions come from matching channel names against MNE's
``standard_1020`` montage, and that match is literal. Real corpora almost never
store bare ``Fp1``:

    TUH EEG          EEG FP1-REF        EEG FP1-LE
    ear-referenced   Fp1-A1             Fp1-M1
    CHB-MIT          FP1-F7             F7-T7        (a genuine bipolar pair)
    misc             EKG1-EKG2          PHOTIC-REF   ROC-LOC

Only the first two groups can be placed on a scalp map, and only after the
``EEG `` prefix and the reference suffix are stripped. Without that step a TUH
recording looks position-less and silently loses its topomap, which is what this
module exists to prevent.

A pair of two *scalp* electrodes (``FP1-F7``) is different in kind: it is a
difference between two positions, so it stays unplaceable no matter how it is
spelled.
"""

from __future__ import annotations

import re
from typing import Dict, List, NamedTuple, Optional, Set

# Labels that mark the second half of a name as a reference rather than a second
# scalp site. A1/A2 (ears) and M1/M2 (mastoids) exist in the montage as
# positions, but by convention a channel named "Fp1-A1" is the potential at Fp1.
REFERENCE_TOKENS: Set[str] = {
    "REF", "REF1", "REF2", "LE", "RE", "AV", "AVG", "CAR", "COM", "GND",
    "A1", "A2", "M1", "M2", "EAR", "LER", "RER", "CZREF",
}

# Stripped from the front of a label before matching.
_PREFIX_RE = re.compile(r"^\s*(eeg|ch|chan|channel)[\s\-_.]+", re.IGNORECASE)


class ChannelKind:
    ELECTRODE = "electrode"   # a single scalp site, placeable on a topomap
    BIPOLAR = "bipolar"       # two scalp sites; a difference, not a potential
    OTHER = "other"           # ECG, EMG, photic, trigger, unrecognised


class Classified(NamedTuple):
    kind: str
    electrode: Optional[str]   # montage name, set only for ELECTRODE
    pair: Optional[tuple]      # (a, b) montage names, set only for BIPOLAR


def montage_names(montage: str = "standard_1020") -> List[str]:
    """Electrode names known to *montage*."""
    import mne

    return list(mne.channels.make_standard_montage(montage).get_positions()["ch_pos"])


def classify(name: str, known: Dict[str, str]) -> Classified:
    """
    Classify one channel label. *known* maps UPPERCASED montage names to their
    canonical spelling (build it once with ``{n.upper(): n for n in montage_names()}``).
    """
    cleaned = _PREFIX_RE.sub("", str(name)).strip()
    if not cleaned:
        return Classified(ChannelKind.OTHER, None, None)

    direct = known.get(cleaned.upper())
    if direct:
        return Classified(ChannelKind.ELECTRODE, direct, None)

    parts = [p.strip() for p in cleaned.split("-") if p.strip()]
    if len(parts) == 2:
        first, second = parts
        a, b = known.get(first.upper()), known.get(second.upper())
        if a and second.upper() in REFERENCE_TOKENS:
            return Classified(ChannelKind.ELECTRODE, a, None)
        if a and b:
            return Classified(ChannelKind.BIPOLAR, None, (a, b))
        if a and b is None:
            # e.g. "Fp1-Something": unknown reference, still a single site
            return Classified(ChannelKind.ELECTRODE, a, None)

    return Classified(ChannelKind.OTHER, None, None)


class MontageMap(NamedTuple):
    """Result of classifying every channel in a recording."""

    rename: Dict[str, str]     # original label -> montage name, for placeable channels
    kinds: Dict[str, str]      # original label -> ChannelKind
    n_electrode: int
    n_bipolar: int
    n_other: int

    @property
    def is_bipolar_recording(self) -> bool:
        """True when bipolar pairs outnumber placeable single electrodes."""
        return self.n_bipolar > self.n_electrode


def build_map(ch_names: List[str], montage: str = "standard_1020") -> MontageMap:
    """
    Classify *ch_names* and produce the rename map needed to match *montage*.

    A rename is skipped when it would collide with a name already in use, so a
    file holding both ``Fp1`` and ``EEG FP1-REF`` keeps them distinct rather
    than silently merging two channels.
    """
    known = {n.upper(): n for n in montage_names(montage)}

    rename: Dict[str, str] = {}
    kinds: Dict[str, str] = {}
    taken = {n.upper() for n in ch_names}
    n_elec = n_bip = n_other = 0

    for name in ch_names:
        result = classify(name, known)
        kinds[name] = result.kind

        if result.kind == ChannelKind.ELECTRODE:
            n_elec += 1
            target = result.electrode
            if target.upper() == name.upper():
                continue                      # already spelled correctly
            if target.upper() in taken:
                continue                      # would collide; leave it alone
            rename[name] = target
            taken.add(target.upper())
        elif result.kind == ChannelKind.BIPOLAR:
            n_bip += 1
        else:
            n_other += 1

    return MontageMap(rename, kinds, n_elec, n_bip, n_other)
