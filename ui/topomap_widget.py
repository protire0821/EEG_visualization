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

import warnings
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
from PyQt6.QtCore import pyqtSlot


class TopoMapWidget(QWidget):
    """Animated topomap powered by mne.viz.plot_topomap()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._vmin: float = -1e-4
        self._vmax: float = 1e-4

        self._setup_ui()
        self._show_placeholder("Load an EDF file\nto see the topomap")

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

        if reader is None or not reader.has_montage:
            self._show_placeholder("No electrode positions\navailable in this file")
            return

        # Compute a fixed, symmetric colour range from the data
        eeg = reader._eeg_data
        abs_max = float(np.percentile(np.abs(eeg), 99))
        if abs_max < 1e-12:
            abs_max = 1e-4
        self._vmin, self._vmax = -abs_max, abs_max

        # Draw frame 0 immediately
        self.update_frame(0)

    @pyqtSlot(int)
    def update_frame(self, frame_idx: int):
        """Redraw the topomap for *frame_idx*.  Connected to frame_changed."""
        if self._reader is None or not self._reader.has_montage:
            return

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
            color="#888888",
            fontsize=11,
            multialignment="center",
        )
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        for spine in self._ax.spines.values():
            spine.set_visible(False)
        self._canvas.draw_idle()
