"""
MainWindow — dataset browser, channel selector, event list, topomap, waveform
and playback transport wired together.

Layout
------
  ┌──────────────────────────────────────────────────────────────┐
  │  File                                                        │  menu bar
  ├──────────────┬───────────────┬───────────────────────────────┤
  │ Subjects     │               │                               │
  │ Recordings   │   Topomap     │          Waveform             │
  │ Channels     │               │                               │
  │ Events       │               │                               │
  ├──────────────┴───────────────┴───────────────────────────────┤
  │  [Play]  Speed ───  Gain ───  Window [10 s]                  │
  │  0.0 s  [═════════════ scrubber ═══════════════════]  300 s  │
  ├──────────────────────────────────────────────────────────────┤
  │  Status bar                                                  │
  └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QSlider, QLabel, QFileDialog, QSizePolicy,
    QListWidget, QListWidgetItem, QGroupBox, QCheckBox, QScrollArea,
    QSpinBox, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QColor

from core.edf_reader import EDFReader
from core.playback import PlaybackController
from core.dataset import scan_dataset
from ui.topomap_widget import TopoMapWidget
from ui.waveform_widget import WaveformWidget

# How far before a seizure onset to jump when an event is clicked.
PRE_ONSET_SEC = 5.0


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EEG Visualizer")
        self.resize(1500, 820)

        self._reader = EDFReader()
        self._playback = PlaybackController(self)
        self._was_playing = False
        self._dataset: Dict[str, Any] = {}
        self._channel_boxes: List[QCheckBox] = []

        self._setup_ui()
        self._setup_menu()
        self._setup_connections()
        self._set_controls_enabled(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 4)
        root_layout.setSpacing(4)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._splitter.addWidget(self._build_side_panel())

        self._topomap = TopoMapWidget()
        self._topomap.setMinimumWidth(260)
        self._topomap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._splitter.addWidget(self._topomap)

        self._waveform = WaveformWidget()
        self._splitter.addWidget(self._waveform)

        self._splitter.setSizes([270, 330, 900])
        self._splitter.setStretchFactor(2, 1)
        root_layout.addWidget(self._splitter, stretch=1)

        root_layout.addWidget(self._build_controls())

        self.statusBar().showMessage(
            "Ready — File ▸ Open recording, or File ▸ Open dataset folder"
        )

    def _build_side_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(6)

        # Subjects -----------------------------------------------------
        subj_group = QGroupBox("Subjects")
        subj_layout = QVBoxLayout(subj_group)
        subj_layout.setContentsMargins(6, 6, 6, 6)
        self._subject_list = QListWidget()
        self._subject_list.setMaximumHeight(120)
        subj_layout.addWidget(self._subject_list)
        layout.addWidget(subj_group)

        # Recordings ---------------------------------------------------
        rec_group = QGroupBox("Recordings")
        rec_layout = QVBoxLayout(rec_group)
        rec_layout.setContentsMargins(6, 6, 6, 6)
        self._recording_list = QListWidget()
        self._recording_list.setMaximumHeight(150)
        rec_layout.addWidget(self._recording_list)
        layout.addWidget(rec_group)

        # Channels -----------------------------------------------------
        ch_group = QGroupBox("Channels")
        ch_layout = QVBoxLayout(ch_group)
        ch_layout.setContentsMargins(6, 6, 6, 6)
        ch_layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self._all_btn = QPushButton("All")
        self._none_btn = QPushButton("None")
        for b in (self._all_btn, self._none_btn):
            b.setFixedHeight(22)
            btn_row.addWidget(b)
        ch_layout.addLayout(btn_row)

        self._channel_area = QScrollArea()
        self._channel_area.setWidgetResizable(True)
        self._channel_holder = QWidget()
        self._channel_layout = QVBoxLayout(self._channel_holder)
        self._channel_layout.setContentsMargins(2, 2, 2, 2)
        self._channel_layout.setSpacing(1)
        self._channel_layout.addStretch()
        self._channel_area.setWidget(self._channel_holder)
        ch_layout.addWidget(self._channel_area)
        layout.addWidget(ch_group, stretch=1)

        # Events -------------------------------------------------------
        ev_group = QGroupBox("Events")
        ev_layout = QVBoxLayout(ev_group)
        ev_layout.setContentsMargins(6, 6, 6, 6)
        ev_layout.setSpacing(4)
        self._event_list = QListWidget()
        self._event_list.setMaximumHeight(140)
        ev_layout.addWidget(self._event_list)
        self._event_count = QLabel("No events")
        self._event_count.setStyleSheet("color: gray; font-size: 11px;")
        ev_layout.addWidget(self._event_count)
        layout.addWidget(ev_group)

        return panel

    def _build_controls(self) -> QWidget:
        controls = QWidget()
        controls.setFixedHeight(72)
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setContentsMargins(2, 2, 2, 2)
        ctrl_layout.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setFixedWidth(90)
        row1.addWidget(self._play_btn)

        row1.addWidget(QLabel("Speed:"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(1, 16)        # 0.25× – 4.0×
        self._speed_slider.setValue(4)            # 1.0×
        self._speed_slider.setTickInterval(4)
        self._speed_slider.setFixedWidth(130)
        row1.addWidget(self._speed_slider)
        self._speed_label = QLabel("1.00×")
        self._speed_label.setFixedWidth(48)
        row1.addWidget(self._speed_label)

        row1.addSpacing(16)
        row1.addWidget(QLabel("Gain:"))
        self._gain_slider = QSlider(Qt.Orientation.Horizontal)
        self._gain_slider.setRange(1, 50)         # 0.1× – 5.0×
        self._gain_slider.setValue(10)            # 1.0×
        self._gain_slider.setFixedWidth(130)
        row1.addWidget(self._gain_slider)
        self._gain_label = QLabel("1.0×")
        self._gain_label.setFixedWidth(44)
        row1.addWidget(self._gain_label)

        row1.addSpacing(16)
        row1.addWidget(QLabel("Window:"))
        self._window_spin = QSpinBox()
        self._window_spin.setRange(1, 300)
        self._window_spin.setValue(10)
        self._window_spin.setSuffix(" s")
        self._window_spin.setFixedWidth(78)
        row1.addWidget(self._window_spin)

        row1.addStretch()
        ctrl_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self._cur_time_label = QLabel("0.0 s")
        self._cur_time_label.setFixedWidth(60)
        self._cur_time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        row2.addWidget(self._cur_time_label)

        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setRange(0, 0)
        row2.addWidget(self._scrubber, stretch=1)

        self._tot_time_label = QLabel("0.0 s")
        self._tot_time_label.setFixedWidth(60)
        row2.addWidget(self._tot_time_label)

        ctrl_layout.addLayout(row2)
        return controls

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_file = QAction("&Open recording…", self)
        open_file.setShortcut("Ctrl+O")
        open_file.triggered.connect(self._open_file)
        file_menu.addAction(open_file)

        open_dir = QAction("Open &dataset folder…", self)
        open_dir.setShortcut("Ctrl+Shift+O")
        open_dir.triggered.connect(self._open_dataset)
        file_menu.addAction(open_dir)

        file_menu.addSeparator()
        quit_act = QAction("&Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

    def _setup_connections(self) -> None:
        self._play_btn.clicked.connect(self._on_play_pause)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        self._gain_slider.valueChanged.connect(self._on_gain_changed)
        self._window_spin.valueChanged.connect(self._on_window_changed)

        self._scrubber.sliderPressed.connect(self._on_scrubber_pressed)
        self._scrubber.sliderMoved.connect(self._on_scrubber_moved)
        self._scrubber.sliderReleased.connect(self._on_scrubber_released)

        self._subject_list.currentItemChanged.connect(self._on_subject_changed)
        self._recording_list.itemActivated.connect(self._on_recording_chosen)
        self._recording_list.currentItemChanged.connect(self._on_recording_chosen)
        self._event_list.itemClicked.connect(self._on_event_clicked)

        self._all_btn.clicked.connect(lambda: self._set_all_channels(True))
        self._none_btn.clicked.connect(lambda: self._set_all_channels(False))

        self._playback.frame_changed.connect(self._topomap.update_frame)
        self._playback.frame_changed.connect(self._waveform.update_cursor)
        self._playback.frame_changed.connect(self._on_frame_changed)
        self._playback.playback_finished.connect(self._on_playback_finished)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in (self._play_btn, self._speed_slider, self._gain_slider,
                  self._scrubber, self._window_spin):
            w.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open EEG recording", "",
            "EEG recordings (*.edf *.bdf *.fif *.set *.vhdr);;All files (*)",
        )
        if path:
            self._load(path)

    def _open_dataset(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open dataset folder")
        if not folder:
            return

        self._dataset = scan_dataset(folder)
        self._subject_list.clear()
        self._recording_list.clear()

        if not self._dataset:
            QMessageBox.information(
                self, "Nothing found",
                "No EEG recordings (.edf, .bdf, .fif, .set, .vhdr) were found in "
                "that folder or its immediate subfolders.",
            )
            self.statusBar().showMessage(f"No recordings in {folder}")
            return

        for subject_id, entry in self._dataset.items():
            item = QListWidgetItem(f"{subject_id}  ({len(entry['recordings'])})")
            item.setData(Qt.ItemDataRole.UserRole, subject_id)
            self._subject_list.addItem(item)

        total = sum(len(e["recordings"]) for e in self._dataset.values())
        self.statusBar().showMessage(
            f"{len(self._dataset)} subjects, {total} recordings in {os.path.basename(folder)}"
        )
        self._subject_list.setCurrentRow(0)

    def _load(self, path: str) -> None:
        self._playback.pause()
        self._play_btn.setText("▶  Play")
        self.statusBar().showMessage(f"Loading {os.path.basename(path)} …")
        self.repaint()

        try:
            self._reader.load(path)
        except Exception as exc:
            self.statusBar().showMessage(f"Could not load {os.path.basename(path)}: {exc}")
            QMessageBox.warning(self, "Load failed", f"{os.path.basename(path)}\n\n{exc}")
            return

        self._topomap.set_reader(self._reader)
        self._waveform.set_data(self._reader.data, self._reader.times, self._reader.ch_names)
        self._waveform.set_annotations(self._reader.annotations)
        self._waveform.set_window_seconds(self._window_spin.value())

        self._build_channel_boxes(self._reader.ch_names)
        self._populate_events(self._reader.annotations)

        self._playback.set_data(self._reader.n_samples, self._reader.sfreq)

        self._scrubber.blockSignals(True)
        self._scrubber.setRange(0, max(0, self._reader.n_samples - 1))
        self._scrubber.setValue(0)
        self._scrubber.blockSignals(False)

        self._cur_time_label.setText("0.0 s")
        self._tot_time_label.setText(f"{self._reader.duration:.1f} s")
        self._on_gain_changed(self._gain_slider.value())
        self._set_controls_enabled(True)

        topo_msg = (
            f"{len(self._reader.montage_channels)} channels positioned"
            if self._reader.has_montage
            else "no electrode positions — topomap unavailable"
        )
        n_seiz = len(self._reader.seizures)
        seiz_msg = f"{n_seiz} seizure{'s' if n_seiz != 1 else ''}" if n_seiz else "no seizures"
        self.statusBar().showMessage(
            f"{os.path.basename(path)}  |  {len(self._reader.ch_names)} channels  |  "
            f"{self._reader.duration:.1f} s  |  {self._reader.sfreq:.0f} Hz  |  "
            f"{topo_msg}  |  {seiz_msg}"
        )

    # ------------------------------------------------------------------
    # Side panel
    # ------------------------------------------------------------------

    def _build_channel_boxes(self, names: List[str]) -> None:
        for box in self._channel_boxes:
            box.setParent(None)
        self._channel_boxes.clear()

        for i, name in enumerate(names):
            box = QCheckBox(name)
            box.setChecked(True)
            box.stateChanged.connect(self._on_channel_toggled)
            self._channel_layout.insertWidget(i, box)
            self._channel_boxes.append(box)

    def _set_all_channels(self, checked: bool) -> None:
        for box in self._channel_boxes:
            box.blockSignals(True)
            box.setChecked(checked)
            box.blockSignals(False)
        self._on_channel_toggled()

    @pyqtSlot()
    def _on_channel_toggled(self, *_args) -> None:
        selected = [i for i, box in enumerate(self._channel_boxes) if box.isChecked()]
        self._waveform.set_visible_channels(selected)
        if not selected:
            self.statusBar().showMessage("No channels selected")

    def _populate_events(self, annotations: List[Dict[str, Any]]) -> None:
        self._event_list.clear()
        if not annotations:
            self._event_count.setText("No events")
            self._event_count.setStyleSheet("color: gray; font-size: 11px;")
            return

        from core.annotations import is_seizure

        seizures = [a for a in annotations if is_seizure(a)]
        for a in annotations:
            start = float(a["start_time"])
            dur = float(a["end_time"]) - start
            mm, ss = divmod(start, 60)
            text = f"{int(mm):02d}:{ss:05.2f}  {a['label']}  ({dur:.1f} s)"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, a)
            if is_seizure(a):
                item.setForeground(QColor("#d32f2f"))
            self._event_list.addItem(item)

        if seizures:
            total = sum(float(a["end_time"]) - float(a["start_time"]) for a in seizures)
            self._event_count.setText(
                f"{len(seizures)} seizure{'s' if len(seizures) != 1 else ''}, "
                f"{total:.1f} s total  ·  {len(annotations)} events"
            )
            self._event_count.setStyleSheet(
                "color: #d32f2f; font-size: 11px; font-weight: bold;"
            )
        else:
            self._event_count.setText(f"{len(annotations)} events, no seizures")
            self._event_count.setStyleSheet("color: gray; font-size: 11px;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_subject_changed(self, current, _previous) -> None:
        self._recording_list.clear()
        if current is None:
            return
        subject_id = current.data(Qt.ItemDataRole.UserRole)
        for rec in self._dataset.get(subject_id, {}).get("recordings", []):
            item = QListWidgetItem(rec["filename"])
            item.setData(Qt.ItemDataRole.UserRole, rec["path"])
            self._recording_list.addItem(item)

    def _on_recording_chosen(self, current, _previous=None) -> None:
        if current is None:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if path and path != self._reader.filepath:
            self._load(path)

    def _on_event_clicked(self, item: QListWidgetItem) -> None:
        annotation = item.data(Qt.ItemDataRole.UserRole)
        if not annotation:
            return
        start = float(annotation["start_time"])
        target = max(0.0, start - PRE_ONSET_SEC)
        frame = int(target * self._reader.sfreq)

        self._playback.pause()
        self._play_btn.setText("▶  Play")
        self._playback.seek_to_frame(frame)
        self._waveform.centre_on(target)

        dur = float(annotation["end_time"]) - start
        self.statusBar().showMessage(
            f"{annotation['label']} at {start:.1f} s, {dur:.1f} s long "
            f"— view starts {PRE_ONSET_SEC:.0f} s earlier"
        )

    @pyqtSlot()
    def _on_play_pause(self) -> None:
        self._playback.toggle()
        self._play_btn.setText("⏸  Pause" if self._playback.is_playing else "▶  Play")

    @pyqtSlot(int)
    def _on_frame_changed(self, frame_idx: int) -> None:
        self._scrubber.blockSignals(True)
        self._scrubber.setValue(frame_idx)
        self._scrubber.blockSignals(False)
        t = frame_idx / self._reader.sfreq if self._reader.sfreq > 0 else 0.0
        self._cur_time_label.setText(f"{t:.1f} s")

    @pyqtSlot()
    def _on_playback_finished(self) -> None:
        self._play_btn.setText("▶  Play")

    @pyqtSlot()
    def _on_scrubber_pressed(self) -> None:
        self._was_playing = self._playback.is_playing
        self._playback.pause()
        self._play_btn.setText("▶  Play")

    @pyqtSlot(int)
    def _on_scrubber_moved(self, value: int) -> None:
        self._playback.seek_to_frame(value)

    @pyqtSlot()
    def _on_scrubber_released(self) -> None:
        if self._was_playing:
            self._playback.play()
            self._play_btn.setText("⏸  Pause")

    @pyqtSlot(int)
    def _on_speed_changed(self, value: int) -> None:
        speed = value * 0.25
        self._speed_label.setText(f"{speed:.2f}×")
        self._playback.set_speed(speed)

    @pyqtSlot(int)
    def _on_gain_changed(self, value: int) -> None:
        gain = value * 0.1
        self._gain_label.setText(f"{gain:.1f}×")
        self._waveform.set_gain(gain)

    @pyqtSlot(int)
    def _on_window_changed(self, value: int) -> None:
        self._waveform.set_window_seconds(float(value))
