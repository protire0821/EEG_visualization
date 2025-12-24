"""
主視窗 - EEG Viewer
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QFileDialog, QLabel,
    QListWidget, QListWidgetItem, QGroupBox, QCheckBox,
    QScrollArea, QSpinBox, QComboBox, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
import os

from gui.eeg_plot_widget import EEGPlotWidget
from data_loader.eeg_loader import EEGDataLoader


class MainWindow(QMainWindow):
    """主視窗類別"""

    def __init__(self):
        super().__init__()

        self.data_loader = EEGDataLoader()
        self.current_dataset = None

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""

        self.setWindowTitle("EEG Viewer - 多通道腦波查看器")
        self.setGeometry(100, 100, 1600, 900)

        # 建立選單列
        self.create_menu_bar()

        # 建立主要布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左側：資料集瀏覽器
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右側：主要顯示區域
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 設定分割比例
        splitter.setStretchFactor(0, 1)  # 左側 20%
        splitter.setStretchFactor(1, 4)  # 右側 80%

        main_layout.addWidget(splitter)

        # 狀態列
        self.statusBar().showMessage("就緒")

    def create_menu_bar(self):
        """建立選單列"""

        menubar = self.menuBar()

        # 檔案選單
        file_menu = menubar.addMenu("檔案(&F)")

        open_folder_action = QAction("開啟資料集資料夾(&O)...", self)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self.open_dataset_folder)
        file_menu.addAction(open_folder_action)

        open_file_action = QAction("開啟單一檔案(&F)...", self)
        open_file_action.setShortcut("Ctrl+Shift+O")
        open_file_action.triggered.connect(self.open_single_file)
        file_menu.addAction(open_file_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 檢視選單
        view_menu = menubar.addMenu("檢視(&V)")

        # 說明選單
        help_menu = menubar.addMenu("說明(&H)")

    def create_left_panel(self):
        """建立左側面板"""

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 資料集資訊
        dataset_group = QGroupBox("資料集")
        dataset_layout = QVBoxLayout()

        self.dataset_label = QLabel("未載入資料集")
        self.dataset_label.setWordWrap(True)
        dataset_layout.addWidget(self.dataset_label)

        open_btn = QPushButton("開啟資料夾...")
        open_btn.clicked.connect(self.open_dataset_folder)
        dataset_layout.addWidget(open_btn)

        dataset_group.setLayout(dataset_layout)
        layout.addWidget(dataset_group)

        # 受試者列表
        subject_group = QGroupBox("受試者")
        subject_layout = QVBoxLayout()

        self.subject_list = QListWidget()
        self.subject_list.currentItemChanged.connect(self.on_subject_changed)
        subject_layout.addWidget(self.subject_list)

        subject_group.setLayout(subject_layout)
        layout.addWidget(subject_group)

        # 錄音檔案列表
        recording_group = QGroupBox("錄音檔案")
        recording_layout = QVBoxLayout()

        self.recording_list = QListWidget()
        self.recording_list.currentItemChanged.connect(self.on_recording_changed)
        recording_layout.addWidget(self.recording_list)

        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)

        # 檔案資訊
        info_group = QGroupBox("檔案資訊")
        info_layout = QVBoxLayout()

        self.info_label = QLabel("未選擇檔案")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 癲癇發作事件列表
        seizure_group = QGroupBox("癲癇發作事件")
        seizure_layout = QVBoxLayout()

        self.seizure_list = QListWidget()
        self.seizure_list.itemClicked.connect(self.on_seizure_clicked)
        seizure_layout.addWidget(self.seizure_list)

        # 統計標籤
        self.seizure_count_label = QLabel("無事件")
        self.seizure_count_label.setStyleSheet("color: gray; font-size: 10px;")
        seizure_layout.addWidget(self.seizure_count_label)

        seizure_group.setLayout(seizure_layout)
        layout.addWidget(seizure_group)

        return panel

    def create_right_panel(self):
        """建立右側面板"""

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 控制列
        control_layout = QHBoxLayout()

        # 時間範圍控制
        control_layout.addWidget(QLabel("顯示時間 (秒):"))
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setRange(1, 300)
        self.time_window_spin.setValue(10)
        self.time_window_spin.valueChanged.connect(self.on_time_window_changed)
        control_layout.addWidget(self.time_window_spin)

        control_layout.addWidget(QLabel("振幅縮放:"))
        self.amplitude_slider = QSlider(Qt.Orientation.Horizontal)
        self.amplitude_slider.setRange(1, 100)
        self.amplitude_slider.setValue(10)
        self.amplitude_slider.valueChanged.connect(self.on_amplitude_changed)
        control_layout.addWidget(self.amplitude_slider)

        # 濾波器
        control_layout.addWidget(QLabel("濾波:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["無", "0.5-40 Hz", "1-30 Hz", "自訂..."])
        control_layout.addWidget(self.filter_combo)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 通道選擇器
        channel_control = QHBoxLayout()
        channel_control.addWidget(QLabel("通道選擇:"))

        select_all_btn = QPushButton("全選")
        select_all_btn.clicked.connect(self.select_all_channels)
        channel_control.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消全選")
        deselect_all_btn.clicked.connect(self.deselect_all_channels)
        channel_control.addWidget(deselect_all_btn)

        channel_control.addStretch()
        layout.addLayout(channel_control)

        # 通道列表（可捲動）
        self.channel_scroll = QScrollArea()
        self.channel_widget = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_widget)
        self.channel_checkboxes = []

        self.channel_scroll.setWidget(self.channel_widget)
        self.channel_scroll.setWidgetResizable(True)
        self.channel_scroll.setMaximumHeight(150)
        layout.addWidget(self.channel_scroll)

        # EEG 繪圖區域
        self.plot_widget = EEGPlotWidget()
        layout.addWidget(self.plot_widget)

        return panel

    def open_dataset_folder(self):
        """開啟資料集資料夾"""

        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇 EEG 資料集資料夾",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.load_dataset(folder)

    def open_single_file(self):
        """開啟單一 EEG 檔案"""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 EEG 檔案",
            "",
            "EEG Files (*.edf *.bdf *.fif *.set *.vhdr);;All Files (*.*)"
        )

        if file_path:
            self.load_single_file(file_path)

    def load_dataset(self, folder_path):
        """載入資料集"""

        self.statusBar().showMessage(f"載入資料集: {folder_path}")

        try:
            # 掃描資料集結構
            structure = self.data_loader.scan_dataset(folder_path)

            self.current_dataset = {
                'path': folder_path,
                'structure': structure
            }

            # 更新 UI
            self.dataset_label.setText(f"資料集: {os.path.basename(folder_path)}\n"
                                      f"受試者數量: {len(structure)}")

            # 填充受試者列表
            self.subject_list.clear()
            for subject_id in sorted(structure.keys()):
                item = QListWidgetItem(subject_id)
                item.setData(Qt.ItemDataRole.UserRole, subject_id)
                self.subject_list.addItem(item)

            self.statusBar().showMessage(f"成功載入資料集: {len(structure)} 位受試者")

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入資料集失敗:\n{str(e)}")
            self.statusBar().showMessage("載入失敗")

    def load_single_file(self, file_path):
        """載入單一檔案"""

        self.statusBar().showMessage(f"載入檔案: {file_path}")

        try:
            # 載入資料
            data, info = self.data_loader.load_file(file_path)

            # 更新通道選擇器
            self.update_channel_selector(info['ch_names'])

            # 更新資訊 - 顯示更多通道細節
            channel_summary = f"{info['n_channels']} 個通道"
            if info['n_channels'] <= 5:
                # 如果通道少，直接列出名稱
                channel_summary += f"\n({', '.join(info['ch_names'])})"

            annotation_count = len(info.get('annotations', []))
            annotation_info = f"\n標註: {annotation_count} 個" if annotation_count > 0 else ""

            self.info_label.setText(
                f"檔案: {os.path.basename(file_path)}\n"
                f"通道數: {channel_summary}\n"
                f"採樣率: {info['sfreq']} Hz\n"
                f"時長: {info['duration']:.1f} 秒"
                f"{annotation_info}"
            )

            # 顯示資料
            self.plot_widget.set_data(data, info)

            # 更新癲癇事件列表
            self.update_seizure_list(info.get('annotations', []))

            self.statusBar().showMessage("檔案載入成功")

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入檔案失敗:\n{str(e)}")
            self.statusBar().showMessage("載入失敗")

    def on_subject_changed(self, current, previous):
        """受試者選擇改變"""

        if current is None:
            return

        subject_id = current.data(Qt.ItemDataRole.UserRole)

        # 填充錄音列表
        self.recording_list.clear()

        if self.current_dataset:
            recordings = self.current_dataset['structure'][subject_id]['recordings']

            for rec in recordings:
                item = QListWidgetItem(rec['filename'])
                item.setData(Qt.ItemDataRole.UserRole, rec)
                self.recording_list.addItem(item)

    def on_recording_changed(self, current, previous):
        """錄音檔案選擇改變"""

        if current is None:
            return

        recording = current.data(Qt.ItemDataRole.UserRole)
        file_path = recording['path']

        self.load_single_file(file_path)

    def update_channel_selector(self, channel_names):
        """更新通道選擇器"""

        # 清除舊的
        for cb in self.channel_checkboxes:
            cb.deleteLater()
        self.channel_checkboxes.clear()

        # 建立新的
        for ch_name in channel_names:
            cb = QCheckBox(ch_name)
            cb.setChecked(True)
            cb.stateChanged.connect(self.on_channel_selection_changed)
            self.channel_layout.addWidget(cb)
            self.channel_checkboxes.append(cb)

    def select_all_channels(self):
        """全選通道"""
        for cb in self.channel_checkboxes:
            cb.setChecked(True)

    def deselect_all_channels(self):
        """取消全選通道"""
        for cb in self.channel_checkboxes:
            cb.setChecked(False)

    def on_channel_selection_changed(self):
        """通道選擇改變"""
        selected = [i for i, cb in enumerate(self.channel_checkboxes) if cb.isChecked()]
        self.plot_widget.set_visible_channels(selected)

    def on_time_window_changed(self, value):
        """時間視窗改變"""
        self.plot_widget.set_time_window(value)

    def on_amplitude_changed(self, value):
        """振幅縮放改變"""
        self.plot_widget.set_amplitude_scale(value / 10.0)

    def update_seizure_list(self, annotations):
        """更新癲癇發作事件列表"""

        self.seizure_list.clear()

        # 過濾出癲癇發作事件
        seizures = [
            annot for annot in annotations
            if 'seizure' in annot.get('description', '').lower() or
               'seizure' in annot.get('label', '').lower() or
               'sz' in annot.get('label', '').lower()
        ]

        if not seizures:
            self.seizure_count_label.setText("無癲癇發作事件")
            self.seizure_count_label.setStyleSheet("color: gray; font-size: 10px;")
            return

        # 更新統計標籤
        total_duration = sum(annot.get('duration', 0) for annot in seizures)
        self.seizure_count_label.setText(
            f"共 {len(seizures)} 次發作，總時長 {total_duration:.1f} 秒"
        )
        self.seizure_count_label.setStyleSheet("color: #d32f2f; font-size: 10px; font-weight: bold;")

        # 添加每個癲癇事件到列表
        for i, seizure in enumerate(seizures, 1):
            start_time = seizure['onset']
            duration = seizure.get('duration', 0)
            end_time = start_time + duration

            # 格式化時間顯示
            start_str = self._format_time(start_time)
            end_str = self._format_time(end_time)

            # 列表項文字
            item_text = f"#{i}: {start_str} - {end_str} ({duration:.1f}s)"

            # 建立列表項
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, seizure)

            # 設定樣式（紅色高亮）
            item.setForeground(Qt.GlobalColor.red)

            self.seizure_list.addItem(item)

    def on_seizure_clicked(self, item):
        """點擊癲癇事件，跳轉到對應時間"""

        seizure = item.data(Qt.ItemDataRole.UserRole)
        if seizure:
            start_time = seizure['onset']

            # 跳轉到發作開始前 5 秒（如果可能）
            jump_time = max(0, start_time - 5)

            self.plot_widget.jump_to_time(jump_time)

            # 更新狀態列
            duration = seizure.get('duration', 0)
            self.statusBar().showMessage(
                f"跳轉到癲癇發作 #{seizure.get('seizure_number', '?')}: "
                f"{self._format_time(start_time)} (時長: {duration:.1f}秒)",
                5000  # 顯示 5 秒
            )

    def _format_time(self, seconds):
        """格式化時間顯示 (秒 -> MM:SS 或 HH:MM:SS)"""

        if seconds < 3600:  # 小於 1 小時
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:  # 超過 1 小時
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
