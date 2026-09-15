"""
Multi-channel EEG waveform widget built on pyqtgraph.

Channels are stacked vertically one sensitivity step apart, the way a clinical
review station lays them out: at 70 µV, the gap between two channel baselines
*is* 70 µV, so a lower number magnifies the traces. A red cursor line follows
playback and the view auto-scrolls to keep it visible. Annotations are drawn as
shaded regions behind the traces.

Usage
-----
    widget = WaveformWidget()
    widget.set_data(data, times, ch_names)    # after loading a recording
    widget.set_annotations(reader.annotations)
    widget.update_cursor(frame_idx)           # connect to frame_changed
    widget.set_sensitivity(70)                # µV between channel baselines
    widget.set_visible_channels([0, 1, 4])
    widget.set_window_seconds(30)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pyqtgraph as pg

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QColor

from core.annotations import is_seizure


def _enable_opengl() -> bool:
    """
    Opt into pyqtgraph's OpenGL line renderer with EEGVIZ_OPENGL=1.

    It is off by default because it is not a guaranteed win: pyqtgraph's GL path
    skips some drawing features, and on many machines the CPU renderer is
    already fast enough once clipping and downsampling are on. Try it if
    playback still stutters; it needs PyOpenGL (`pip install PyOpenGL`).
    """
    if os.environ.get("EEGVIZ_OPENGL", "") not in ("1", "true", "True"):
        return False
    try:
        import OpenGL  # noqa: F401
    except ImportError:
        print("[waveform] EEGVIZ_OPENGL is set but PyOpenGL is not installed; "
              "falling back to the CPU renderer")
        return False
    pg.setConfigOptions(useOpenGL=True, enableExperimental=True)
    return True

# Distinct colours for channel curves (cycled when there are more channels)
_CHANNEL_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#F06292", "#CE93D8",
    "#4DD0E1", "#AED581", "#FFD54F", "#FF8A65", "#90A4AE",
    "#64B5F6", "#A5D6A7", "#FFF176", "#EF9A9A", "#80CBC4",
    "#B39DDB", "#FFCC02", "#80DEEA", "#BCAAA4", "#DCE775",
]

_SEIZURE_BRUSH = (211, 47, 47, 55)      # translucent red
_EVENT_BRUSH = (120, 144, 156, 45)      # translucent slate


class WaveformWidget(QWidget):
    """Stacked multi-channel EEG display with a scrolling playback cursor."""

    DEFAULT_WINDOW_SEC = 10.0
    DEFAULT_SENSITIVITY_UV = 70.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: Optional[np.ndarray] = None
        self._times: Optional[np.ndarray] = None
        self._ch_names: List[str] = []
        self._visible: List[int] = []
        self._sens_uv: float = self.DEFAULT_SENSITIVITY_UV
        self._window_sec: float = self.DEFAULT_WINDOW_SEC
        self._curves: List[pg.PlotDataItem] = []
        self._regions: List[pg.LinearRegionItem] = []
        self._annotations: List[Dict[str, Any]] = []

        self._setup_ui()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOption("background", "#1e1e1e")
        pg.setConfigOption("foreground", "#cccccc")
        pg.setConfigOption("antialias", False)
        self.opengl = _enable_opengl()

        self._plot = pg.PlotWidget()
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.showGrid(x=True, y=False, alpha=0.3)
        self._plot.getViewBox().setMouseEnabled(x=True, y=False)

        # A whole recording is far more samples than the screen has pixels.
        # clipToView renders only the visible window and peak downsampling keeps
        # spikes visible while drawing one min/max pair per pixel column —
        # without these, an hour-long file costs ~600 ms per repaint instead of
        # ~17 ms, and playback turns into a slideshow.
        item = self._plot.getPlotItem()
        item.setClipToView(True)
        item.setDownsampling(auto=True, mode="peak")

        self._cursor = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen(color="#ff4444", width=2)
        )
        self._plot.addItem(self._cursor)

        layout.addWidget(self._plot)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, data: np.ndarray, times: np.ndarray, ch_names: Sequence[str]) -> None:
        """Load a new recording. All channels start visible."""
        self._data = data
        self._times = times
        self._ch_names = list(ch_names)
        self._visible = list(range(len(self._ch_names)))
        self._rebuild_curves()

    def set_channel_data(self, data: np.ndarray) -> None:
        """Swap in re-filtered samples, keeping the current view and selection."""
        if self._data is None or data.shape != self._data.shape:
            return
        self._data = data
        for row, ch in enumerate(self._visible):
            self._curves[row].setData(self._times, data[ch] + row * self._spacing)

    def set_visible_channels(self, indices: Sequence[int]) -> None:
        """Show only the channels at *indices* (in their original order)."""
        if self._data is None:
            return
        wanted = sorted(set(int(i) for i in indices if 0 <= int(i) < len(self._ch_names)))
        if wanted == self._visible:
            return
        self._visible = wanted
        self._rebuild_curves()

    def set_window_seconds(self, seconds: float) -> None:
        """Set how many seconds of data are visible at once."""
        seconds = max(1.0, float(seconds))
        if seconds == self._window_sec:
            return
        self._window_sec = seconds
        if self._times is None or not len(self._times):
            return
        centre = float(self._cursor.value())
        duration = float(self._times[-1])
        new_min = max(0.0, min(centre - seconds * 0.15, duration - seconds))
        self._plot.setXRange(new_min, new_min + seconds, padding=0)

    def set_annotations(self, annotations: Sequence[Dict[str, Any]]) -> None:
        """Draw *annotations* as shaded regions; seizures are highlighted red."""
        for r in self._regions:
            self._plot.removeItem(r)
        self._regions.clear()
        self._annotations = list(annotations)

        for a in self._annotations:
            start, end = float(a.get("start_time", 0.0)), float(a.get("end_time", 0.0))
            if end <= start:
                end = start + 0.5  # make instantaneous marks visible
            brush = _SEIZURE_BRUSH if is_seizure(a) else _EVENT_BRUSH
            region = pg.LinearRegionItem(
                values=(start, end),
                movable=False,
                brush=pg.mkBrush(QColor(*brush)),
                pen=pg.mkPen(QColor(brush[0], brush[1], brush[2], 160), width=1),
            )
            region.setZValue(-10)  # behind the traces
            self._plot.addItem(region)
            self._regions.append(region)

    @pyqtSlot(int)
    def update_cursor(self, frame_idx: int) -> None:
        """Move the cursor to *frame_idx*, scrolling the view when needed."""
        if self._times is None or frame_idx >= len(self._times):
            return
        t = float(self._times[frame_idx])
        self._cursor.setPos(t)
        self._scroll_to(t)

    def centre_on(self, t: float) -> None:
        """Scroll so that time *t* sits near the left of the visible window."""
        if self._times is None or not len(self._times):
            return
        duration = float(self._times[-1])
        window = self._window_sec
        new_min = max(0.0, min(t - window * 0.15, max(0.0, duration - window)))
        self._plot.setXRange(new_min, new_min + window, padding=0)
        self._cursor.setPos(t)

    def set_sensitivity(self, microvolts: float) -> None:
        """
        Set how many microvolts separate two channel baselines. This is the
        clinical sensitivity control: 70 µV is a typical review setting, and a
        smaller number makes the traces larger.
        """
        microvolts = max(1.0, float(microvolts))
        if microvolts == self._sens_uv:
            return
        self._sens_uv = microvolts
        self._reposition()

    @property
    def _spacing(self) -> float:
        """Baseline separation in data units (MNE returns volts)."""
        return self._sens_uv * 1e-6

    def _reposition(self) -> None:
        """Re-apply the vertical offsets after a sensitivity change."""
        if self._data is None or not self._visible:
            return
        for row, ch in enumerate(self._visible):
            self._curves[row].setData(self._times, self._data[ch] + row * self._spacing)
        self._plot.getAxis("left").setTicks(
            [[(row * self._spacing, self._ch_names[ch])
              for row, ch in enumerate(self._visible)]]
        )
        self._plot.setYRange(
            -self._spacing * 0.6,
            (len(self._visible) - 0.4) * self._spacing,
            padding=0,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_curves(self) -> None:
        """Drop the old curves and create one per visible channel."""
        for c in self._curves:
            self._plot.removeItem(c)
        self._curves.clear()

        if self._data is None or not self._visible:
            self._plot.getAxis("left").setTicks([[]])
            return

        for row, ch in enumerate(self._visible):
            curve = self._plot.plot(
                self._times,
                self._data[ch] + row * self._spacing,
                pen=pg.mkPen(_CHANNEL_COLORS[ch % len(_CHANNEL_COLORS)], width=1),
                name=self._ch_names[ch],
                antialias=False,
            )
            self._curves.append(curve)

        ticks = [(row * self._spacing, self._ch_names[ch])
                 for row, ch in enumerate(self._visible)]
        self._plot.getAxis("left").setTicks([ticks])
        self._plot.getAxis("left").setStyle(tickTextOffset=4)

        duration = float(self._times[-1]) if len(self._times) else 0.0
        self._plot.setXRange(0, min(self._window_sec, duration) or 1.0, padding=0)
        self._plot.setYRange(
            -self._spacing * 0.6,
            (len(self._visible) - 0.4) * self._spacing,
            padding=0,
        )

    def _scroll_to(self, t: float) -> None:
        """
        Keep the cursor about 15 % from the left edge, scrolling only once it
        approaches the right edge so the view does not jitter every frame.
        """
        vb = self._plot.getViewBox()
        x_min, x_max = vb.viewRange()[0]
        window = x_max - x_min

        if x_min <= t <= x_max and t < x_max - window * 0.1:
            return

        duration = float(self._times[-1]) if self._times is not None else window
        new_min = max(0.0, t - window * 0.15)
        new_max = min(duration, new_min + window)
        new_min = max(0.0, new_max - window)
        self._plot.setXRange(new_min, new_max, padding=0)
