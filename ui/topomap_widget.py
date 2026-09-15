"""
Topomap widget — embeds a matplotlib figure inside a QWidget and
renders the instantaneous EEG potential distribution using
mne.viz.plot_topomap().

Usage
-----
    widget = TopoMapWidget()
    widget.set_reader(reader)          # call after loading a file
    widget.update_frame(frame_idx)     # connect to PlaybackController.frame_changed
"""

import time
import warnings
from typing import Optional

import numpy as np

import matplotlib
try:
    matplotlib.use("QtAgg")
except Exception:
    pass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import mne

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSlot, QTimer


class TopoMapWidget(QWidget):
    """Animated topomap powered by mne.viz.plot_topomap()."""

    # A matplotlib topomap costs ~40 ms to draw, which on its own eats the whole
    # 40 ms budget of 25 fps playback. Scalp topography changes slowly enough to
    # read at ~8 fps, so redraws are throttled and the most recent frame is
    # always drawn last — a seek never leaves a stale map on screen.
    _MIN_REDRAW_MS = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._vmin: float = -1e-4
        self._vmax: float = 1e-4
        self._last_draw_ms: float = -1e9
        self._pending_frame: Optional[int] = None

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_pending)

        self._setup_ui()
        self._show_placeholder("Load a recording\nto see the topomap")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(4, 4), facecolor="#f8f8f8")
        self._fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        self._canvas = FigureCanvas(self._fig)
        self._ax = self._fig.add_subplot(111)
        layout.addWidget(self._canvas)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_reader(self, reader):
        """Configure widget for a newly loaded EDFReader."""
        self._reader = reader

        if reader is None:
            self._show_placeholder("Load a recording\nto see the topomap")
            return
        if not reader.has_montage:
            self._show_placeholder(reader.montage_status)
            return

        # Compute a fixed, symmetric colour range from the data
        eeg = reader._eeg_data
        abs_max = float(np.percentile(np.abs(eeg), 99))
        if abs_max < 1e-12:
            abs_max = 1e-4
        self._vmin, self._vmax = -abs_max, abs_max

        # Draw frame 0 immediately
        self._last_draw_ms = -1e9
        self._pending_frame = None
        self.update_frame(0)

    @pyqtSlot(int)
    def update_frame(self, frame_idx: int):
        """
        Request a redraw for *frame_idx*. Connected to frame_changed; redraws
        are throttled to _MIN_REDRAW_MS and the latest request always wins.
        """
        if self._reader is None or not self._reader.has_montage:
            return

        now = time.monotonic() * 1000.0
        elapsed = now - self._last_draw_ms
        if elapsed < self._MIN_REDRAW_MS:
            self._pending_frame = frame_idx
            if not self._flush_timer.isActive():
                self._flush_timer.start(int(self._MIN_REDRAW_MS - elapsed))
            return

        self._pending_frame = None
        self._last_draw_ms = now
        self._draw(frame_idx)

    def _flush_pending(self):
        if self._pending_frame is None:
            return
        frame_idx = self._pending_frame
        self._pending_frame = None
        self._last_draw_ms = time.monotonic() * 1000.0
        self._draw(frame_idx)

    def _draw(self, frame_idx: int):
        """Render the topomap for *frame_idx*."""
        data, info = self._reader.get_topomap_data(frame_idx)
        if data is None:
            return

        self._ax.cla()

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mne.viz.plot_topomap(
                    data,
                    info,
                    axes=self._ax,
                    show=False,
                    contours=4,
                    res=48,
                    vlim=(self._vmin, self._vmax),
                    cmap="RdBu_r",
                    sensors=True,
                    image_interp="linear",
                    ch_type="eeg",
                )
        except Exception as exc:
            self._ax.text(
                0.5,
                0.5,
                f"Topomap error:\n{exc}",
                transform=self._ax.transAxes,
                ha="center",
                va="center",
                color="red",
                fontsize=8,
                wrap=True,
            )

        # Show current time
        if self._reader.sfreq > 0:
            t = frame_idx / self._reader.sfreq
            self._ax.set_title(f"t = {t:.3f} s", fontsize=9, pad=2)

        self._canvas.draw_idle()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _show_placeholder(self, message: str):
        self._ax.cla()
        self._ax.set_facecolor("#f0f0f0")
        self._ax.text(
            0.5,
            0.5,
            message,
            transform=self._ax.transAxes,
            ha="center",
            va="center",
            color="#777777",
            fontsize=8.5,
            multialignment="center",
            wrap=True,
        )
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        for spine in self._ax.spines.values():
            spine.set_visible(False)
        self._canvas.draw_idle()
