"""
標註解析器
支援多種標註格式的解析
"""

from abc import ABC, abstractmethod
from typing import List, Dict
import re
import os


class AnnotationParser(ABC):
    """標註解析器基類"""

    @abstractmethod
    def parse(self, source) -> List[Dict]:
        """
        解析標註

        Returns:
            標準格式列表：
            [{
                'start_time': float,  # 秒
                'end_time': float,    # 秒
                'label': str,         # 標籤（如 'seizure'）
                'description': str,   # 描述
                'metadata': dict      # 額外資訊
            }]
        """
        pass


class CHBMITAnnotationParser(AnnotationParser):
    """
    CHB-MIT 資料集標註解析器

    格式範例（-summary.txt 檔案）：
    File Name: chb01_03.edf
    ...
    Number of Seizures in File: 1
    Seizure Start Time: 2996 seconds
    Seizure End Time: 3036 seconds
    """

    def parse(self, summary_file: str, target_filename: str = None) -> List[Dict]:
        """
        解析 CHB-MIT summary 檔案

        Args:
            summary_file: summary 檔案路徑
            target_filename: 目標 EEG 檔案名（如 'chb01_03.edf'），用於過濾

        支援格式：
        File Name: chb01_03.edf
        Number of Seizures in File: 1
        Seizure Start Time: 2996 seconds
        Seizure End Time: 3036 seconds
        """

        if not os.path.exists(summary_file):
            return []

        annotations = []

        try:
            with open(summary_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"無法讀取 summary 檔案: {e}")
            return []

        # 按 'File Name:' 分割成多個檔案區塊
        file_pattern = r'File Name:\s*(\S+)'
        file_blocks = re.split(f'(?={file_pattern})', content, flags=re.IGNORECASE)

        seizure_count = 0

        for block in file_blocks:
            if not block.strip():
                continue

            # 提取檔案名
            file_match = re.search(file_pattern, block, re.IGNORECASE)
            if not file_match:
                continue

            current_file = file_match.group(1).strip()

            # 如果指定了目標檔案，只處理該檔案
            if target_filename:
                # 不區分大小寫比較
                if current_file.lower() != target_filename.lower():
                    continue

            # 在當前區塊中尋找癲癇時間
            # 支援格式：
            # 1. Seizure Start Time: 2996 seconds
            # 2. Seizure 1 Start Time: 2996 seconds
            start_pattern = r'Seizure.*?Start Time:\s*(\d+(?:\.\d+)?)\s*seconds?'
            end_pattern = r'Seizure.*?End Time:\s*(\d+(?:\.\d+)?)\s*seconds?'

            start_matches = list(re.finditer(start_pattern, block, re.IGNORECASE))
            end_matches = list(re.finditer(end_pattern, block, re.IGNORECASE))

            # 配對開始和結束時間
            for i, start_match in enumerate(start_matches):
                start_time = float(start_match.group(1))

                # 找到對應的結束時間
                if i < len(end_matches):
                    end_time = float(end_matches[i].group(1))
                    seizure_count += 1

                    annotations.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'label': 'seizure',
                        'description': f'Seizure #{seizure_count}',
                        'metadata': {
                            'source': 'chb-mit-summary',
                            'seizure_number': seizure_count,
                            'duration': end_time - start_time,
                            'file': current_file
                        }
                    })

        return annotations


class CSVAnnotationParser(AnnotationParser):
    """
    CSV 格式標註解析器

    預期 CSV 格式：
    start,end,label,description
    120.5,135.2,seizure,Focal seizure
    """

    def parse(self, csv_file: str) -> List[Dict]:
        """解析 CSV 標註檔案"""

        if not os.path.exists(csv_file):
            return []

        import pandas as pd

        try:
            df = pd.read_csv(csv_file)
            annotations = []

            # 彈性處理欄位名稱
            start_col = self._find_column(df, ['start', 'start_time', 'onset'])
            end_col = self._find_column(df, ['end', 'end_time', 'offset'])
            label_col = self._find_column(df, ['label', 'type', 'event'])
            desc_col = self._find_column(df, ['description', 'desc', 'note'])

            for _, row in df.iterrows():
                annotation = {
                    'start_time': float(row[start_col]) if start_col else 0,
                    'end_time': float(row[end_col]) if end_col else 0,
                    'label': str(row[label_col]) if label_col else 'unknown',
                    'description': str(row[desc_col]) if desc_col else '',
                    'metadata': {'source': 'csv'}
                }

                annotations.append(annotation)

            return annotations

        except Exception as e:
            print(f"CSV 解析錯誤: {e}")
            return []

    def _find_column(self, df, possible_names: List[str]) -> str:
        """查找欄位名稱（不區分大小寫）"""
        df_columns_lower = [col.lower() for col in df.columns]

        for name in possible_names:
            if name.lower() in df_columns_lower:
                idx = df_columns_lower.index(name.lower())
                return df.columns[idx]

        return None


class EDFAnnotationParser(AnnotationParser):
    """
    EDF+ 內建標註解析器
    """

    def parse(self, edf_file: str) -> List[Dict]:
        """從 EDF+ 檔案提取標註"""

        import mne

        try:
            raw = mne.io.read_raw_edf(edf_file, preload=False, verbose=False)

            if not hasattr(raw, 'annotations') or len(raw.annotations) == 0:
                return []

            annotations = []

            for annot in raw.annotations:
                annotations.append({
                    'start_time': float(annot['onset']),
                    'end_time': float(annot['onset'] + annot['duration']),
                    'label': annot['description'],
                    'description': annot['description'],
                    'metadata': {
                        'source': 'edf-annotation',
                        'duration': float(annot['duration'])
                    }
                })

            return annotations

        except Exception as e:
            print(f"EDF 標註解析錯誤: {e}")
            return []


class TUHAnnotationParser(AnnotationParser):
    """
    TUH (Temple University Hospital) EEG 資料集標註解析器

    格式：.tse 或 .csv_bi 檔案
    """

    def parse(self, tse_file: str) -> List[Dict]:
        """解析 TUH .tse 檔案"""

        if not os.path.exists(tse_file):
            return []

        annotations = []

        with open(tse_file, 'r') as f:
            lines = f.readlines()

        # 跳過標題行
        for line in lines[1:]:
            parts = line.strip().split(',')

            if len(parts) >= 3:
                try:
                    start_time = float(parts[0])
                    end_time = float(parts[1])
                    label = parts[2].strip()

                    annotations.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'label': label,
                        'description': label,
                        'metadata': {'source': 'tuh-tse'}
                    })
                except ValueError:
                    continue

        return annotations


class AnnotationParserFactory:
    """標註解析器工廠"""

    _parsers = {
        'chb-mit': CHBMITAnnotationParser,
        'csv': CSVAnnotationParser,
        'edf': EDFAnnotationParser,
        'tuh': TUHAnnotationParser,
    }

    @classmethod
    def get_parser(cls, parser_type: str) -> AnnotationParser:
        """
        獲取解析器實例

        Args:
            parser_type: 'chb-mit', 'csv', 'edf', 'tuh'
        """
        parser_class = cls._parsers.get(parser_type.lower())

        if not parser_class:
            raise ValueError(f"未知的標註格式: {parser_type}")

        return parser_class()

    @classmethod
    def register_parser(cls, name: str, parser_class: type):
        """註冊自訂解析器"""
        cls._parsers[name.lower()] = parser_class

    @classmethod
    def auto_detect(cls, file_path: str) -> AnnotationParser:
        """
        自動偵測標註格式

        Args:
            file_path: 標註檔案路徑或 EEG 檔案路徑
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            return cls.get_parser('csv')
        elif ext in ['.edf', '.bdf']:
            return cls.get_parser('edf')
        elif ext in ['.tse', '.csv_bi']:
            return cls.get_parser('tuh')
        elif 'summary' in file_path.lower():
            return cls.get_parser('chb-mit')
        else:
            # 預設使用 CSV
            return cls.get_parser('csv')


def load_annotations_for_file(eeg_file_path: str) -> List[Dict]:
    """
    自動尋找並載入 EEG 檔案對應的標註

    搜尋順序：
    1. EDF/BDF 內建標註
    2. 同名 CSV 檔案 (file.edf -> file.csv)
    3. 檔案級別 summary (chb01_03-summary.txt)
    4. 受試者級別 summary (chb01-summary.txt) ← CHB-MIT 格式
    5. 同目錄下的 annotations.csv
    """

    all_annotations = []
    filename = os.path.basename(eeg_file_path)
    dir_name = os.path.dirname(eeg_file_path)

    # 1. EDF 內建標註
    if eeg_file_path.endswith(('.edf', '.bdf')):
        try:
            parser = EDFAnnotationParser()
            annotations = parser.parse(eeg_file_path)
            all_annotations.extend(annotations)
        except Exception as e:
            pass  # 靜默失敗

    # 2. 同名 CSV
    csv_path = os.path.splitext(eeg_file_path)[0] + '.csv'
    if os.path.exists(csv_path):
        try:
            parser = CSVAnnotationParser()
            annotations = parser.parse(csv_path)
            all_annotations.extend(annotations)
        except Exception as e:
            print(f"CSV 解析失敗: {e}")

    # 3. 檔案級別 CHB-MIT summary (chb01_03-summary.txt)
    base_name = os.path.splitext(eeg_file_path)[0]
    summary_path = base_name + '-summary.txt'
    if os.path.exists(summary_path):
        try:
            parser = CHBMITAnnotationParser()
            annotations = parser.parse(summary_path, filename)
            all_annotations.extend(annotations)
        except Exception as e:
            print(f"Summary 解析失敗: {e}")

    # 4. 受試者級別 CHB-MIT summary (chb01-summary.txt)
    # 從檔案名提取受試者 ID：chb01_03.edf -> chb01
    subject_match = re.match(r'(chb\d+)', filename.lower())
    if subject_match:
        subject_id = subject_match.group(1)
        subject_summary = os.path.join(dir_name, f'{subject_id}-summary.txt')

        if os.path.exists(subject_summary):
            try:
                parser = CHBMITAnnotationParser()
                annotations = parser.parse(subject_summary, filename)
                all_annotations.extend(annotations)
                print(f"✓ 從 {subject_id}-summary.txt 載入了 {len(annotations)} 個標註")
            except Exception as e:
                print(f"Summary 解析失敗: {e}")

    # 5. 同目錄 annotations.csv
    dir_annotations = os.path.join(dir_name, 'annotations.csv')
    if os.path.exists(dir_annotations):
        try:
            parser = CSVAnnotationParser()
            annotations = parser.parse(dir_annotations)
            all_annotations.extend(annotations)
        except Exception as e:
            print(f"Annotations.csv 解析失敗: {e}")

    return all_annotations
