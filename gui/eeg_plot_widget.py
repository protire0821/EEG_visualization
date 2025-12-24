"""
EEG 繪圖組件
使用 pyqtgraph 進行高效能多通道顯示
"""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from typing import List, Dict


class EEGPlotWidget(QWidget):
    """EEG 多通道波形顯示組件"""

    def __init__(self):
        super().__init__()

        self.data = None
        self.info = None
        self.visible_channels = []
        self.time_window = 10  # 顯示 10 秒
        self.current_start_time = 0
        self.amplitude_scale = 1.0

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""

        layout = QVBoxLayout(self)

        # 控制按鈕
        control_layout = QHBoxLayout()

        self.prev_btn = QPushButton("◀ 上一段")
        self.prev_btn.clicked.connect(self.prev_segment)
        control_layout.addWidget(self.prev_btn)

        self.time_label = QLabel("0.0 - 0.0 秒")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.time_label)

        self.next_btn = QPushButton("下一段 ▶")
        self.next_btn.clicked.connect(self.next_segment)
        control_layout.addWidget(self.next_btn)

        layout.addLayout(control_layout)

        # 建立 pyqtgraph 圖形視窗
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground('w')  # 白色背景
        layout.addWidget(self.graphics_layout)

        self.plots = []  # 儲存每個通道的 plot

    def set_data(self, data: np.ndarray, info: Dict):
        """
        設定要顯示的資料

        Args:
            data: shape (n_channels, n_samples)
            info: 包含 ch_names, sfreq 等資訊
        """
        self.data = data
        self.info = info
        self.current_start_time = 0

        # 預設顯示所有通道
        self.visible_channels = list(range(data.shape[0]))

        self.update_plot()

    def set_visible_channels(self, channels: List[int]):
        """設定可見通道"""
        self.visible_channels = channels
        self.update_plot()

    def set_time_window(self, window_seconds: float):
        """設定時間視窗"""
        self.time_window = window_seconds
        self.update_plot()

    def set_amplitude_scale(self, scale: float):
        """設定振幅縮放"""
        self.amplitude_scale = scale
        self.update_plot()

    def update_plot(self):
        """更新繪圖"""

        if self.data is None or self.info is None:
            return

        # 清除舊的圖
        self.graphics_layout.clear()
        self.plots = []

        if len(self.visible_channels) == 0:
            return

        # 計算要顯示的資料範圍
        sfreq = self.info['sfreq']
        start_sample = int(self.current_start_time * sfreq)
        end_sample = int((self.current_start_time + self.time_window) * sfreq)
        end_sample = min(end_sample, self.data.shape[1])

        # 時間軸
        time_axis = np.arange(start_sample, end_sample) / sfreq

        # 為每個通道建立子圖
        n_channels = len(self.visible_channels)

        for i, ch_idx in enumerate(self.visible_channels):
            # 建立 plot
            plot = self.graphics_layout.addPlot(row=i, col=0)

            # 設定標籤
            ch_name = self.info['ch_names'][ch_idx]
            plot.setLabel('left', ch_name)

            if i == n_channels - 1:
                plot.setLabel('bottom', '時間 (秒)')
            else:
                plot.getAxis('bottom').setTicks([])  # 隱藏 x 軸刻度

            # 繪製資料
            y_data = self.data[ch_idx, start_sample:end_sample]

            # 正規化並縮放
            y_data = y_data * self.amplitude_scale

            # 繪製曲線
            curve = plot.plot(
                time_axis,
                y_data,
                pen=pg.mkPen(color='b', width=1)
            )

            # 連結 X 軸（所有通道同步縮放/平移）
            if i > 0:
                plot.setXLink(self.plots[0])

            self.plots.append(plot)

        # 顯示標註（如果有）
        if 'annotations' in self.info and self.info['annotations']:
            self.add_annotations_to_plots()

        # 更新時間標籤
        self.update_time_label()

        # 啟用/禁用按鈕
        self.prev_btn.setEnabled(self.current_start_time > 0)
        self.next_btn.setEnabled(
            self.current_start_time + self.time_window < self.info['duration']
        )

    def update_time_label(self):
        """更新時間標籤"""
        end_time = min(
            self.current_start_time + self.time_window,
            self.info['duration'] if self.info else 0
        )
        self.time_label.setText(
            f"{self.current_start_time:.1f} - {end_time:.1f} 秒"
        )

    def prev_segment(self):
        """上一段"""
        self.current_start_time = max(0, self.current_start_time - self.time_window)
        self.update_plot()

    def next_segment(self):
        """下一段"""
        if self.info:
            max_start = max(0, self.info['duration'] - self.time_window)
            self.current_start_time = min(
                self.current_start_time + self.time_window,
                max_start
            )
            self.update_plot()

    def jump_to_time(self, target_time: float):
        """
        跳轉到指定時間

        Args:
            target_time: 目標時間（秒）
        """
        if self.info is None:
            return

        # 確保時間在有效範圍內
        max_start = max(0, self.info['duration'] - self.time_window)
        self.current_start_time = max(0, min(target_time, max_start))

        self.update_plot()

    def add_annotations_to_plots(self):
        """在所有圖上添加標註區域"""

        if not self.plots or not self.info.get('annotations'):
            return

        current_end = self.current_start_time + self.time_window

        for annot in self.info['annotations']:
            start_time = annot['onset']
            end_time = start_time + annot['duration']

            # 只顯示可見範圍內的標註
            if end_time < self.current_start_time or start_time > current_end:
                continue

            # 根據標註類型選擇顏色和樣式
            label = annot.get('description', '').lower()
            if 'seizure' in label or 'sz' in label:
                # 癲癇發作 - 紅色半透明背景 + 紅色邊框
                color = (255, 0, 0, 100)  # 更不透明的紅色
                pen = pg.mkPen(color='r', width=2, style=pg.QtCore.Qt.PenStyle.DashLine)
            elif 'artifact' in label:
                color = (128, 128, 128, 60)  # 灰色 - 雜訊
                pen = pg.mkPen(color=(128, 128, 128), width=1)
            elif 'sleep' in label:
                color = (0, 0, 255, 60)  # 藍色 - 睡眠階段
                pen = pg.mkPen(color='b', width=1)
            else:
                color = (255, 165, 0, 60)  # 橘色 - 其他
                pen = pg.mkPen(color=(255, 165, 0), width=1)

            # 在所有圖上添加區域
            for plot in self.plots:
                region = pg.LinearRegionItem(
                    values=[start_time, end_time],
                    brush=color,
                    pen=pen,
                    movable=False
                )
                plot.addItem(region)

    def add_annotation_region(self, start_time: float, end_time: float, label: str = ""):
        """
        手動添加標註區域

        Args:
            start_time: 開始時間（秒）
            end_time: 結束時間（秒）
            label: 標籤文字
        """
        # 在所有圖上添加垂直區域
        for plot in self.plots:
            region = pg.LinearRegionItem(
                values=[start_time, end_time],
                brush=(255, 0, 0, 50),  # 半透明紅色
                movable=False
            )
            plot.addItem(region)


class MultiChannelEEGPlot(QWidget):
    """
    進階版：支援虛擬滾動的多通道顯示
    適用於非常大的資料集（只載入可見範圍）
    """

    def __init__(self):
        super().__init__()

        self.data_loader = None  # 外部提供的資料載入函數
        self.file_path = None
        self.info = None
        self.visible_channels = []
        self.time_window = 10
        self.current_start_time = 0

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 滾動條
        from PyQt6.QtWidgets import QSlider, QHBoxLayout

        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(QLabel("時間位置:"))

        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        scroll_layout.addWidget(self.time_slider)

        layout.addLayout(scroll_layout)

        # 圖形視窗
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground('w')
        layout.addWidget(self.graphics_layout)

        self.plots = []

    def set_file(self, file_path: str, info: Dict, data_loader_func):
        """
        設定檔案（不立即載入全部資料）

        Args:
            file_path: 檔案路徑
            info: 檔案資訊
            data_loader_func: 資料載入函數 func(start_time, end_time, channels)
        """
        self.file_path = file_path
        self.info = info
        self.data_loader = data_loader_func

        # 設定滑桿範圍
        total_duration = info['duration']
        self.time_slider.setRange(0, int(total_duration - self.time_window))

        # 預設顯示所有通道
        self.visible_channels = list(range(info['n_channels']))

        self.load_and_display()

    def on_slider_changed(self, value):
        """滑桿改變"""
        self.current_start_time = value
        self.load_and_display()

    def load_and_display(self):
        """載入並顯示當前時間範圍的資料"""

        if self.data_loader is None or self.info is None:
            return

        # 載入當前範圍的資料
        data, _ = self.data_loader(
            self.current_start_time,
            self.current_start_time + self.time_window,
            self.visible_channels
        )

        # 更新顯示（類似 EEGPlotWidget.update_plot）
        self.graphics_layout.clear()
        self.plots = []

        sfreq = self.info['sfreq']
        time_axis = np.arange(data.shape[1]) / sfreq + self.current_start_time

        for i, ch_idx in enumerate(self.visible_channels):
            plot = self.graphics_layout.addPlot(row=i, col=0)
            plot.setLabel('left', self.info['ch_names'][ch_idx])

            if i == len(self.visible_channels) - 1:
                plot.setLabel('bottom', '時間 (秒)')

            plot.plot(time_axis, data[i], pen='b')

            if i > 0:
                plot.setXLink(self.plots[0])

            self.plots.append(plot)
