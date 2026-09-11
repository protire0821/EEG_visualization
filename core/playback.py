"""
QTimer-based playback controller.

Emits frame_changed(int) at ~25 fps, advancing by the correct number
of samples per tick to maintain real-time playback at the chosen speed.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class PlaybackController(QObject):
    """
    Signals
    -------
    frame_changed(int)    — new frame index, emitted every tick
    playback_finished()   — emitted when the end of recording is reached
    """

    frame_changed = pyqtSignal(int)
    playback_finished = pyqtSignal()

    _BASE_INTERVAL_MS = 40  # 25 fps

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._n_frames: int = 0
        self._sfreq: float = 256.0
        self._current_frame: int = 0
        self._speed: float = 1.0
        self._frames_per_tick: int = 1
        self._playing: bool = False

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_data(self, n_frames: int, sfreq: float):
        """Call after loading a new file to reset state."""
        self.pause()
        self._n_frames = n_frames
        self._sfreq = sfreq
        self._current_frame = 0
        self._recalc_frames_per_tick()

    def set_speed(self, speed: float):
        """Set playback speed multiplier (0.25 – 4.0)."""
        self._speed = max(0.25, min(speed, 8.0))
        self._recalc_frames_per_tick()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def play(self):
        if not self._playing and self._n_frames > 0:
            self._playing = True
            self._timer.start(self._BASE_INTERVAL_MS)

    def pause(self):
        self._playing = False
        self._timer.stop()

    def toggle(self):
        self.pause() if self._playing else self.play()

    def seek(self, time_sec: float):
        """Seek to an absolute time position (seconds)."""
        frame = int(time_sec * self._sfreq)
        self._set_frame(frame)

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

    def _set_frame(self, frame: int):
        self._current_frame = max(0, min(frame, self._n_frames - 1))
        self.frame_changed.emit(self._current_frame)

    def _recalc_frames_per_tick(self):
        fps = 1000.0 / self._BASE_INTERVAL_MS  # 25.0
        self._frames_per_tick = max(1, int(self._sfreq * self._speed / fps))

    def _tick(self):
        self._current_frame += self._frames_per_tick
        if self._current_frame >= self._n_frames:
            self._current_frame = self._n_frames - 1
            self.pause()
            self.frame_changed.emit(self._current_frame)
            self.playback_finished.emit()
            return
        self.frame_changed.emit(self._current_frame)
