"""
Wall-clock playback controller.

The position is derived from `time.monotonic()`, not from counting timer ticks.
That distinction matters: a tick-counting controller advances a fixed number of
samples per timeout, so as soon as repainting costs more than the timer interval
the timer fires late and playback silently runs *slower than real time* — the
2 s marker arrives after 3 s of wall clock. Anchoring to the clock instead means
a slow repaint drops frames rather than stretching time, so "1.0×" stays 1.0×.
"""

from __future__ import annotations

import os
import time

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal


class PlaybackController(QObject):
    """
    Signals
    -------
    frame_changed(int)    — new frame index, emitted on every tick that moves
    playback_finished()   — emitted when the end of the recording is reached
    """

    frame_changed = pyqtSignal(int)
    playback_finished = pyqtSignal()

    # Repaint target. Because the position comes from the clock, lowering this
    # rate costs smoothness but never accuracy — EEGVIZ_FPS=15 on a slow machine
    # still plays back at exactly 1.0x, just with coarser steps.
    _BASE_INTERVAL_MS = max(10, int(1000 / float(os.environ.get("EEGVIZ_FPS", 25))))

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)

        self._n_frames: int = 0
        self._sfreq: float = 256.0
        self._current_frame: int = 0
        self._speed: float = 1.0
        self._playing: bool = False

        # Anchor: the wall-clock instant and frame index playback started from.
        self._anchor_wall: float = 0.0
        self._anchor_frame: int = 0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_data(self, n_frames: int, sfreq: float):
        """Call after loading a new recording to reset state."""
        self.pause()
        self._n_frames = n_frames
        self._sfreq = sfreq
        self._current_frame = 0
        self._reanchor()

    def set_speed(self, speed: float):
        """Set the playback speed multiplier (0.25 – 8.0)."""
        self._speed = max(0.25, min(speed, 8.0))
        self._reanchor()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def play(self):
        if not self._playing and self._n_frames > 0:
            self._playing = True
            self._reanchor()
            self._timer.start(self._BASE_INTERVAL_MS)

    def pause(self):
        self._playing = False
        self._timer.stop()

    def toggle(self):
        self.pause() if self._playing else self.play()

    def seek(self, time_sec: float):
        """Seek to an absolute time position in seconds."""
        self._set_frame(int(time_sec * self._sfreq))

    def seek_to_frame(self, frame_idx: int):
        """Seek to an absolute frame index."""
        self._set_frame(frame_idx)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_frame(self) -> int:
        return self._current_frame

    @property
    def current_time(self) -> float:
        return self._current_frame / self._sfreq if self._sfreq > 0 else 0.0

    @property
    def is_playing(self) -> bool:
        return self._playing

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reanchor(self):
        """Re-base the clock on the current position (after a seek or a speed change)."""
        self._anchor_wall = time.monotonic()
        self._anchor_frame = self._current_frame

    def _set_frame(self, frame: int):
        self._current_frame = max(0, min(frame, max(0, self._n_frames - 1)))
        self._reanchor()
        self.frame_changed.emit(self._current_frame)

    def _tick(self):
        elapsed = time.monotonic() - self._anchor_wall
        frame = self._anchor_frame + int(elapsed * self._sfreq * self._speed)

        if frame >= self._n_frames:
            self._current_frame = self._n_frames - 1
            self.pause()
            self.frame_changed.emit(self._current_frame)
            self.playback_finished.emit()
            return

        if frame == self._current_frame:
            return  # nothing moved yet; skip the repaint

        self._current_frame = frame
        self.frame_changed.emit(frame)
