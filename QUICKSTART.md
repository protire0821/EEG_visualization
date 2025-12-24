# 快速啟動指南

## 5 分鐘快速開始

### 步驟 1：安裝依賴

```bash
# 在專案目錄下
cd C:\Code\EEG_visualization_website

# 建立虛擬環境（建議）
python -m venv venv
venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 步驟 2：執行程式

```bash
python main.py
```

### 步驟 3：載入資料

**方式 A：開啟資料集資料夾**
1. 點選「檔案」→「開啟資料集資料夾」（或 Ctrl+O）
2. 選擇包含 EEG 檔案的資料夾
3. 在左側面板選擇受試者和錄音

**方式 B：開啟單一檔案**
1. 點選「檔案」→「開啟單一檔案」（或 Ctrl+Shift+O）
2. 選擇 .edf, .bdf 等檔案
3. 波形將立即顯示

## 範例資料集結構

### CHB-MIT 癲癇資料集範例

```
D:\EEG_Data\chb-mit\
├── chb01\
│   ├── chb01_01.edf
│   ├── chb01_02.edf
│   ├── chb01_03.edf
│   └── chb01-summary.txt    # 包含發作時間標註
├── chb02\
│   ├── chb02_01.edf
│   └── ...
└── ...
```

**標註檔案格式 (chb01-summary.txt):**
```
File Name: chb01_03.edf
Number of Seizures in File: 1
Seizure Start Time: 2996 seconds
Seizure End Time: 3036 seconds
```

### 自訂資料集範例

```
D:\My_EEG_Data\
├── patient001\
│   ├── baseline.edf
│   ├── task1.edf
│   └── annotations.csv      # CSV 格式標註
└── patient002\
    └── ...
```

**CSV 標註格式 (annotations.csv):**
```csv
start,end,label,description
120.5,135.2,seizure,Focal seizure
300.0,305.0,artifact,Movement artifact
```

## 常用操作

### 通道選擇
- **全選**：點選「全選」按鈕
- **取消全選**：點選「取消全選」
- **個別選擇**：勾選/取消通道核取方塊

### 時間導航
- **上一段/下一段**：使用 ◀ 和 ▶ 按鈕
- **調整視窗大小**：修改「顯示時間」數值（1-300 秒）

### 振幅調整
- 拖動「振幅縮放」滑桿調整波形高度

### 標註顯示
標註會自動以不同顏色顯示：
- 🔴 紅色：癲癇發作 (seizure)
- 🔵 藍色：睡眠階段 (sleep)
- ⚫ 灰色：雜訊 (artifact)
- 🟠 橘色：其他事件

## 處理大型資料集（100GB+）

### 選項 1：使用片段載入（已內建）

程式會自動只載入可見時間範圍的資料，節省記憶體。

### 選項 2：預處理為 HDF5（進階）

對於超大資料集，可預先處理：

```python
# 建立 utils/preprocess_large_dataset.py
from data_loader.eeg_loader import EEGDataLoader
import h5py

# 將 100GB EDF 轉換為 HDF5 格式（約 50GB）
# 詳見 README.md
```

## 支援的檔案格式

| 格式 | 副檔名 | 說明 |
|------|--------|------|
| European Data Format | .edf | 最常見的臨床 EEG 格式 |
| BioSemi Data Format | .bdf | BioSemi 系統專用 |
| Neuromag/Elekta/MEGIN | .fif | MEG/EEG 格式 |
| EEGLAB | .set | MATLAB EEGLAB 格式 |
| BrainVision | .vhdr | Brain Products 格式 |

## 標註格式支援

程式會自動搜尋以下標註來源：

1. **EDF/BDF 內建標註**：自動讀取
2. **同名 CSV**：如 `file.edf` → `file.csv`
3. **CHB-MIT summary**：`chb01-summary.txt`
4. **目錄 CSV**：資料夾內的 `annotations.csv`

### 自訂標註格式

編輯 `data_loader/annotation_parser.py` 添加：

```python
class MyCustomParser(AnnotationParser):
    def parse(self, source):
        # 你的解析邏輯
        return [
            {
                'start_time': 100.0,
                'end_time': 110.0,
                'label': 'event',
                'description': 'Custom event'
            }
        ]

# 註冊解析器
AnnotationParserFactory.register_parser('my_format', MyCustomParser)
```

## 鍵盤快捷鍵

- `Ctrl+O`：開啟資料集資料夾
- `Ctrl+Shift+O`：開啟單一檔案
- `Ctrl+Q`：退出程式

## 效能優化建議

### 記憶體不足時

1. 減少「顯示時間」（例如從 30 秒降到 10 秒）
2. 減少同時顯示的通道數
3. 使用片段載入模式（預設已啟用）

### 顯示很慢時

1. 確保已安裝正確版本的 PyQt6 和 pyqtgraph
2. 降低採樣率（使用濾波功能）
3. 減少可見通道數

## 疑難排解

### 問題：`ModuleNotFoundError: No module named 'PyQt6'`

**解決**：
```bash
pip install PyQt6 pyqtgraph
```

### 問題：無法讀取 EDF 檔案

**解決**：
```bash
pip install mne
```

### 問題：標註沒有顯示

**檢查**：
1. 確認標註檔案與 EEG 檔案在同一目錄
2. 檢查標註格式是否正確
3. 查看控制台是否有錯誤訊息

### 問題：視窗顯示模糊（高 DPI 螢幕）

**解決**：已在 `main.py` 中啟用高 DPI 支援。如仍有問題：
```python
# 在 main.py 添加
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
```

## 下一步

- 📖 閱讀 [README.md](README.md) 了解完整功能
- 🔧 查看 `gui/` 和 `data_loader/` 了解程式架構
- 🎨 自訂 GUI 外觀和配色
- 📊 添加頻譜分析功能

## 需要幫助？

遇到問題？請提供：
1. 作業系統和 Python 版本
2. 錯誤訊息（完整）
3. EEG 檔案格式和來源
4. 重現步驟

建立 Issue 或聯絡開發者。
