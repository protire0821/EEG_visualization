# CHB-MIT 癲癇資料集使用指南

## 📋 資料集簡介

CHB-MIT Scalp EEG Database 是一個包含兒童癲癇患者腦電圖記錄的公開資料集。

**資料集特點：**
- 24 位受試者（兒童）
- 每位受試者有多個 EEG 錄音檔案
- 包含癲癇發作事件標註
- 採樣率通常為 256 Hz
- 通道數：23 或 24 個通道

## 📂 資料集結構

```
chb-mit/
├── chb01/
│   ├── chb01_01.edf
│   ├── chb01_02.edf
│   ├── chb01_03.edf      ← 包含癲癇發作
│   ├── ...
│   └── chb01-summary.txt ← 標註檔案（重要！）
├── chb02/
│   └── ...
└── ...
```

## 📄 標註檔案格式

`chb01-summary.txt` 範例：

```
Data Sampling Rate: 256 Hz
...
File Name: chb01_03.edf
Number of Seizures in File: 1
Seizure Start Time: 2996 seconds
Seizure End Time: 3036 seconds

File Name: chb01_04.edf
Number of Seizures in File: 1
Seizure 1 Start Time: 1467 seconds
Seizure 1 End Time: 1494 seconds
```

## 🚀 使用步驟

### 1. 下載資料集

```bash
# 從 PhysioNet 下載
# https://physionet.org/content/chbmit/1.0.0/
```

### 2. 開啟 EEG Viewer

```bash
python main.py
```

### 3. 載入資料集

**方式 A：開啟整個資料集**
1. 點選「檔案」→「開啟資料集資料夾」
2. 選擇 `chb-mit` 資料夾
3. 在左側看到所有受試者列表

**方式 B：開啟單一受試者**
1. 點選「檔案」→「開啟資料集資料夾」
2. 選擇 `chb-mit/chb01` 資料夾
3. 直接看到該受試者的錄音

### 4. 查看癲癇發作

程式會自動：
- ✅ 讀取 `chb01-summary.txt` 標註檔案
- ✅ 解析癲癇發作時間
- ✅ 在左側「癲癇發作事件」列表顯示
- ✅ 在波形圖上以紅色半透明區域標示

### 5. 快速跳轉到癲癇發作

**點擊左側事件列表**，程式會：
- 自動跳轉到發作前 5 秒
- 顯示紅色虛線框標示發作區域
- 狀態列顯示事件詳情

## 🎨 視覺效果

### 癲癇發作標示
- **顏色**：紅色半透明背景（透明度 100/255）
- **邊框**：紅色虛線（寬度 2px）
- **範圍**：從發作開始到結束時間

### 事件列表
- **格式**：`#1: MM:SS - MM:SS (持續時長)`
- **顏色**：紅色文字
- **統計**：顯示總發作次數和總時長

## 📊 範例場景

### 場景 1：查看 chb01_03.edf 的癲癇發作

```
1. 開啟資料集：chb-mit/
2. 選擇受試者：chb01
3. 選擇錄音：chb01_03.edf
4. 左側顯示：
   癲癇發作事件
   #1: 49:56 - 50:36 (40.0s)
   共 1 次發作，總時長 40.0 秒
5. 點擊列表項 → 自動跳到 49:51（發作前 5 秒）
6. 波形圖上看到紅色區域標示
```

### 場景 2：查看無癲癇發作的錄音

```
1. 選擇錄音：chb01_01.edf
2. 左側顯示：
   癲癇發作事件
   無癲癇發作事件
```

## 🔧 標註檔案放置位置

程式會自動搜尋以下位置的標註檔案：

### 優先順序 1：與 EDF 同名的 summary 檔
```
chb01_03.edf
chb01_03-summary.txt  ← 自動搜尋
```

### 優先順序 2：受試者目錄下的 summary 檔
```
chb01/
├── chb01_01.edf
├── chb01_02.edf
└── chb01-summary.txt  ← 自動搜尋（包含所有檔案的標註）
```

### 優先順序 3：同目錄下的 CSV 檔案
```
chb01/
├── chb01_03.edf
└── annotations.csv    ← 自訂格式
```

CSV 格式：
```csv
start,end,label,description
2996,3036,seizure,Seizure #1
```

## 🎯 鍵盤快捷操作

| 操作 | 快捷鍵 | 說明 |
|------|--------|------|
| 上一段 | ← 按鈕 | 往前跳一個時間視窗 |
| 下一段 | → 按鈕 | 往後跳一個時間視窗 |
| 跳轉到發作 | 點擊列表 | 自動跳到發作前 5 秒 |

## ⚙️ 建議設定

### 查看癲癇發作時的最佳設定

```
顯示時間：30 秒（可看到完整發作過程）
振幅縮放：10-20（根據訊號大小調整）
通道選擇：全選或選擇重要通道
```

### 常用通道組合

**完整 23 通道（CHB-MIT 標準）：**
```
FP1-F7, F7-T7, T7-P7, P7-O1
FP1-F3, F3-C3, C3-P3, P3-O1
FP2-F4, F4-C4, C4-P4, P4-O2
FP2-F8, F8-T8, T8-P8, P8-O2
FZ-CZ, CZ-PZ, P7-T7, T7-FT9, FT9-FT10, FT10-T8
```

**重點通道（10 通道）：**
- 左側：FP1-F7, F7-T7, T7-P7, P7-O1
- 中央：FZ-CZ, CZ-PZ
- 右側：FP2-F8, F8-T8, T8-P8, P8-O2

## 📈 資料統計

### 查看資料集統計

```bash
# 使用內建工具
python utils/check_dataset_channels.py D:\EEG_Data\chb-mit

# 輸出：
# 📊 找到 24 個受試者
# 通道數分佈:
#   23 個通道: 180 個檔案
#   24 個通道: 8 個檔案
```

## ❓ 常見問題

### Q: 為什麼看不到癲癇標註？

**檢查清單：**
1. ✅ 確認 `chb01-summary.txt` 存在
2. ✅ 檢查檔案名稱是否匹配（如 chb01_03.edf）
3. ✅ 查看左側「癲癇發作事件」是否顯示「無事件」
4. ✅ 確認 summary 檔案格式正確

### Q: 標註時間不準確？

- CHB-MIT 的時間是從錄音開始計算的「秒數」
- 例如：2996 seconds = 49 分 56 秒
- 程式會自動轉換為 MM:SS 格式顯示

### Q: 如何添加自訂標註？

創建 CSV 檔案（與 EDF 同名）：
```csv
start,end,label,description
2996,3036,seizure,Manual annotation
```

## 🔬 進階功能

### 1. 匯出癲癇片段

（待實作）

### 2. 頻譜分析

（待實作）

### 3. 批次處理

使用 Python API：
```python
from data_loader.eeg_loader import EEGDataLoader
from data_loader.annotation_parser import CHBMITAnnotationParser

loader = EEGDataLoader()
parser = CHBMITAnnotationParser()

# 載入資料
data, info = loader.load_file('chb01_03.edf')

# 載入標註
annotations = parser.parse('chb01-summary.txt')
```

## 📚 參考資源

- [CHB-MIT 資料集官網](https://physionet.org/content/chbmit/1.0.0/)
- [論文引用](https://doi.org/10.1109/TBME.2010.2060521)
- [MNE-Python 文檔](https://mne.tools/)

## 🆘 支援

遇到問題？
1. 檢查 README.md 的「常見問題」
2. 執行 `python test_installation.py`
3. 查看控制台錯誤訊息
4. 提交 Issue 並附上錯誤訊息

---

**祝您使用愉快！** 🎉
