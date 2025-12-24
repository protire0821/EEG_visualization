# EEG Viewer - Windows 桌面應用

專為大型 EEG 資料集設計的多通道腦波可視化工具。

## 功能特色

- ✅ **多格式支援**：EDF, BDF, FIF, SET, VHDR
- ✅ **階層式資料集管理**：資料集 → 受試者 → 錄音檔案
- ✅ **高效能可視化**：使用 pyqtgraph，支援大數據量即時渲染
- ✅ **多通道顯示**：同時顯示多個通道，支援獨立選擇
- ✅ **互動控制**：縮放、平移、時間範圍調整
- ✅ **癲癇發作事件列表**：點擊自動跳轉，紅色高亮顯示
- ✅ **CHB-MIT 資料集支援**：自動載入 summary 標註檔案
- ✅ **標註支援**：顯示癲癇發作等事件標註
- ✅ **原生 Windows 應用**：無需瀏覽器，直接存取本地檔案

## 系統需求

- Windows 10/11
- Python 3.9 或更高版本
- 8GB RAM 以上（建議 16GB）

## 安裝步驟

### 1. 安裝 Python

從 [python.org](https://www.python.org/downloads/) 下載並安裝 Python 3.9+

### 2. 建立虛擬環境（建議）

```bash
cd C:\Code\EEG_visualization_website
python -m venv venv
venv\Scripts\activate
```

### 3. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 4. 執行程式

```bash
python main.py
```

## 使用方式

### CHB-MIT 癲癇資料集快速開始

**特別支援 CHB-MIT 資料集！** 程式會自動：
- 載入 `chb01-summary.txt` 標註檔案
- 顯示癲癇發作事件列表
- 在波形圖上紅色高亮標示
- 點擊事件自動跳轉

**步驟：**
1. 開啟資料集資料夾：`chb-mit/`
2. 選擇受試者：如 `chb01`
3. 選擇錄音：如 `chb01_03.edf`
4. 左側自動顯示癲癇事件（如果有）
5. 點擊事件跳轉到發作時間

📖 **詳細說明**：參見 [CHB_MIT_GUIDE.md](CHB_MIT_GUIDE.md)

### 開啟資料集

1. **方式一：開啟整個資料集資料夾**
   - 選單：檔案 → 開啟資料集資料夾
   - 或按 `Ctrl+O`
   - 選擇包含多個受試者子資料夾的根目錄

2. **方式二：開啟單一 EEG 檔案**
   - 選單：檔案 → 開啟單一檔案
   - 或按 `Ctrl+Shift+O`
   - 選擇 .edf, .bdf 等檔案

### 資料集結構

程式支援以下兩種資料集結構：

#### 階層式結構（推薦）
```
dataset/
├── subject01/
│   ├── recording01.edf
│   ├── recording02.edf
│   └── recording01-summary.txt
├── subject02/
│   ├── recording01.edf
│   └── ...
└── ...
```

#### 扁平式結構
```
dataset/
├── file01.edf
├── file02.edf
└── ...
```

### 介面操作

**左側面板：**
- 資料集資訊
- 受試者列表
- 錄音檔案列表
- 檔案詳細資訊

**右側面板：**
- 控制列：時間視窗、振幅縮放、濾波器
- 通道選擇器：選擇要顯示的通道
- 波形顯示區：多通道波形圖

**快捷操作：**
- `◀ 上一段` / `下一段 ▶`：切換時間段
- 拖曳圖表：平移時間軸
- 滾輪：縮放
- 全選/取消全選：快速選擇通道

## 進階功能

### 處理大型資料集（100GB+）

對於非常大的資料集，建議使用預處理：

```python
# 執行預處理腳本（將建立 HDF5 索引）
python utils/preprocess_dataset.py --input D:\EEG_Data --output dataset.h5
```

### 自訂標註格式

在 `data_loader/annotation_parser.py` 中添加自訂解析器：

```python
class MyAnnotationParser(AnnotationParser):
    def parse(self, source):
        # 實作你的解析邏輯
        return annotations
```

### 添加濾波器

修改 `gui/main_window.py` 的 `filter_combo` 處理邏輯。

## 專案結構

```
EEG_visualization_website/
├── main.py                    # 程式入口
├── requirements.txt           # Python 依賴
├── gui/                       # GUI 組件
│   ├── main_window.py        # 主視窗
│   └── eeg_plot_widget.py    # 繪圖組件
├── data_loader/              # 資料載入
│   └── eeg_loader.py         # EEG 檔案載入器
└── utils/                    # 工具函數
```

## 常見問題

**Q: 程式啟動很慢？**
A: 第一次載入大檔案時，MNE 會建立快取。後續開啟會更快。

**Q: 記憶體不足？**
A: 調小「顯示時間」參數，或使用通道選擇器減少同時顯示的通道數。

**Q: 支援哪些 EEG 格式？**
A: 目前支援 EDF, BDF, FIF, SET, VHDR。需要其他格式請提 issue。

**Q: 看到 "Channel names are not unique" 警告？**
A: 這是正常的！某些 EEG 設備會產生重複的通道名稱。MNE 會自動處理（加上編號如 T8-P8-0, T8-P8-1）。程式已自動抑制此警告。

**Q: 不同受試者的通道數不一樣？**
A: 完全支援！程式會在切換檔案時自動更新通道列表。每個檔案可以有：
- 不同數量的通道
- 不同的通道名稱
- 不同的採樣率

**Q: 如何檢查資料集的通道配置？**
A: 使用內建工具：
```bash
python utils/check_dataset_channels.py D:\Your\EEG\Dataset
```

**Q: 如何添加癲癇發作標註？**
A:
- 方法1：使用 EDF+ 格式，標註已內嵌
- 方法2：在資料夾放置對應的 CSV 或摘要文件
- 方法3：擴展 `AnnotationLoader` 類別

## 開發計畫

- [ ] 即時濾波器（帶通、高通、低通）
- [ ] 頻譜分析（FFT、時頻圖）
- [ ] 事件標記工具
- [ ] 匯出功能（圖片、CSV）
- [ ] HDF5 預處理支援
- [ ] 多檔案比較視圖

## 授權

MIT License

## 聯絡

如有問題或建議，歡迎提交 Issue。
