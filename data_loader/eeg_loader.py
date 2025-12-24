"""
EEG 資料載入器
支援多種格式：EDF, BDF, FIF, SET 等
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import mne

from data_loader.annotation_parser import load_annotations_for_file


class EEGDataLoader:
    """EEG 資料載入器"""

    def __init__(self):
        self.supported_formats = ['.edf', '.bdf', '.fif', '.set', '.vhdr']

    def scan_dataset(self, root_dir: str) -> Dict:
        """
        掃描資料集資料夾，建立階層結構

        假設結構：
        root/
        ├── subject1/
        │   ├── recording1.edf
        │   ├── recording2.edf
        └── subject2/
            └── recording1.edf

        Returns:
            {
                'subject1': {
                    'path': 'path/to/subject1',
                    'recordings': [
                        {'filename': 'recording1.edf', 'path': '...'},
                        ...
                    ]
                },
                ...
            }
        """
        root = Path(root_dir)
        structure = {}

        # 檢查是否是扁平結構（所有檔案在同一層）
        eeg_files = list(root.glob('*.*'))
        eeg_files = [f for f in eeg_files if f.suffix.lower() in self.supported_formats]

        if eeg_files:
            # 扁平結構：所有檔案視為同一個 "subject"
            structure['All Files'] = {
                'path': str(root),
                'recordings': [
                    {
                        'filename': f.name,
                        'path': str(f)
                    }
                    for f in eeg_files
                ]
            }
        else:
            # 階層結構：遍歷子資料夾
            for subject_dir in root.iterdir():
                if not subject_dir.is_dir():
                    continue

                subject_id = subject_dir.name
                recordings = []

                # 查找所有 EEG 檔案
                for ext in self.supported_formats:
                    for file_path in subject_dir.glob(f'*{ext}'):
                        recordings.append({
                            'filename': file_path.name,
                            'path': str(file_path)
                        })

                if recordings:
                    structure[subject_id] = {
                        'path': str(subject_dir),
                        'recordings': sorted(recordings, key=lambda x: x['filename'])
                    }

        return structure

    def load_file(self, file_path: str, preload: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        載入單一 EEG 檔案

        Args:
            file_path: 檔案路徑
            preload: 是否預先載入所有資料

        Returns:
            (data, info) tuple
            - data: numpy array, shape (n_channels, n_samples)
            - info: dict with metadata
        """
        ext = Path(file_path).suffix.lower()

        # 根據副檔名選擇載入方法
        # 使用 warnings 控制 MNE 的警告
        import warnings

        with warnings.catch_warnings():
            # 忽略通道名稱重複的警告（MNE 會自動處理）
            warnings.filterwarnings('ignore', category=RuntimeWarning,
                                  message='.*Channel names are not unique.*')

            if ext in ['.edf', '.bdf']:
                raw = mne.io.read_raw_edf(file_path, preload=preload, verbose=False)
            elif ext == '.fif':
                raw = mne.io.read_raw_fif(file_path, preload=preload, verbose=False)
            elif ext == '.set':
                raw = mne.io.read_raw_eeglab(file_path, preload=preload, verbose=False)
            elif ext == '.vhdr':
                raw = mne.io.read_raw_brainvision(file_path, preload=preload, verbose=False)
            else:
                raise ValueError(f"不支援的檔案格式: {ext}")

        # 提取資料
        data = raw.get_data()

        # 提取元資訊
        info = {
            'ch_names': raw.ch_names,
            'sfreq': raw.info['sfreq'],
            'n_channels': len(raw.ch_names),
            'n_samples': data.shape[1],
            'duration': data.shape[1] / raw.info['sfreq'],
            'ch_types': raw.get_channel_types(),  # 使用新版 MNE API
        }

        # 提取標註（如果有）
        if hasattr(raw, 'annotations') and len(raw.annotations) > 0:
            info['annotations'] = [
                {
                    'onset': annot['onset'],
                    'duration': annot['duration'],
                    'description': annot['description']
                }
                for annot in raw.annotations
            ]
        else:
            info['annotations'] = []

        # 嘗試載入外部標註檔案
        try:
            external_annotations = load_annotations_for_file(file_path)
            if external_annotations:
                # 轉換為統一格式
                for annot in external_annotations:
                    info['annotations'].append({
                        'onset': annot['start_time'],
                        'duration': annot['end_time'] - annot['start_time'],
                        'description': annot['label']
                    })
        except Exception as e:
            print(f"載入外部標註失敗: {e}")

        return data, info

    def load_segment(
        self,
        file_path: str,
        start_time: float,
        end_time: float,
        channels: List[int] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        載入資料片段（用於大檔案）

        Args:
            file_path: 檔案路徑
            start_time: 開始時間（秒）
            end_time: 結束時間（秒）
            channels: 要載入的通道索引列表，None 表示全部

        Returns:
            (data, info) tuple
        """
        ext = Path(file_path).suffix.lower()

        # 不預先載入全部資料
        if ext in ['.edf', '.bdf']:
            raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
        elif ext == '.fif':
            raw = mne.io.read_raw_fif(file_path, preload=False, verbose=False)
        elif ext == '.set':
            raw = mne.io.read_raw_eeglab(file_path, preload=False, verbose=False)
        elif ext == '.vhdr':
            raw = mne.io.read_raw_brainvision(file_path, preload=False, verbose=False)
        else:
            raise ValueError(f"不支援的檔案格式: {ext}")

        # 裁剪時間範圍
        raw_cropped = raw.copy().crop(tmin=start_time, tmax=end_time)

        # 選擇通道
        if channels is not None:
            picks = channels
        else:
            picks = range(len(raw.ch_names))

        # 載入資料
        data = raw_cropped.get_data(picks=picks)

        info = {
            'ch_names': [raw.ch_names[i] for i in picks],
            'sfreq': raw.info['sfreq'],
            'n_channels': len(picks),
            'n_samples': data.shape[1],
            'duration': end_time - start_time,
            'start_time': start_time,
            'end_time': end_time
        }

        return data, info


class AnnotationLoader:
    """標註載入器（可擴展）"""

    @staticmethod
    def load_from_summary(summary_file: str) -> List[Dict]:
        """
        從摘要文件載入標註（例如 CHB-MIT 格式）
        """
        annotations = []

        with open(summary_file, 'r') as f:
            lines = f.readlines()

        # 簡單解析邏輯（需根據實際格式調整）
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if 'Seizure' in line or 'seizure' in line:
                # 嘗試解析發作時間
                try:
                    # 範例格式：
                    # Seizure 1 Start Time: 2996 seconds
                    # Seizure 1 End Time: 3036 seconds
                    if 'Start Time' in line:
                        start_time = float(line.split(':')[1].strip().split()[0])

                        # 查找結束時間
                        if i + 1 < len(lines) and 'End Time' in lines[i + 1]:
                            end_time = float(lines[i + 1].split(':')[1].strip().split()[0])

                            annotations.append({
                                'start_time': start_time,
                                'end_time': end_time,
                                'duration': end_time - start_time,
                                'label': 'seizure',
                                'description': line
                            })
                            i += 1
                except:
                    pass

            i += 1

        return annotations

    @staticmethod
    def load_from_csv(csv_file: str) -> List[Dict]:
        """從 CSV 檔案載入標註"""
        import pandas as pd

        df = pd.read_csv(csv_file)
        annotations = []

        for _, row in df.iterrows():
            annotations.append({
                'start_time': row.get('start', row.get('start_time', 0)),
                'end_time': row.get('end', row.get('end_time', 0)),
                'label': row.get('label', 'unknown'),
                'description': row.get('description', '')
            })

        return annotations
