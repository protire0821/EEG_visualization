# 更新日誌

## 2024-12-24 v1.1.0 - CHB-MIT 癲癇標註完整支援

### 🎉 新功能

**CHB-MIT 癲癇發作事件顯示**
- ✅ 新增「癲癇發作事件」面板（左側）
- ✅ 自動載入 `chb01-summary.txt` 受試者級別標註檔案
- ✅ 列表顯示所有癲癇發作事件（時間格式：MM:SS）
- ✅ 點擊事件自動跳轉到發作前 5 秒
- ✅ 紅色半透明區域 + 虛線邊框標示發作範圍
- ✅ 統計總發作次數和總時長

**改進的標註解析器**
- ✅ CHB-MIT 解析器支援受試者級別 summary 檔案
- ✅ 自動從檔案名提取受試者 ID（`chb01_03.edf` → `chb01`）
- ✅ 智能過濾：只顯示當前檔案的標註
- ✅ 支援多種標註格式（`Seizure Start Time` / `Seizure 1 Start Time`）

**視覺改進**
- ✅ 癲癇發作：紅色半透明背景（透明度 100）+ 紅色虛線邊框
- ✅ 事件列表：紅色文字顯示
- ✅ 時間格式化：秒數自動轉換為 MM:SS 或 HH:MM:SS

### 🔧 技術改進

**標註搜尋順序**
1. EDF/BDF 內建標註
2. 同名 CSV 檔案（`chb01_03.csv`）
3. 檔案級別 summary（`chb01_03-summary.txt`）
4. **受試者級別 summary**（`chb01-summary.txt`）← 新增
5. 目錄下的 `annotations.csv`

**測試工具**
- ✅ 新增 `test_chb_mit.py` - 測試標註載入
- ✅ 新增 `CHB_MIT_GUIDE.md` - 完整使用指南

## 2024-12-24 v1.0.1 - MNE API 相容性修正

### 🐛 Bug 修正

**修正 MNE API 變更導致的載入失敗**
- 錯誤：`module 'mne.io.pick' has no attribute 'channel_type'`
- 原因：MNE 1.6+ 版本改變了 API
- 修正：使用 `raw.get_channel_types()` 替代 `mne.io.pick.channel_type()`
- 影響：現在支援 MNE 所有版本（1.0+）

## 2024-12-24 v1.0.0 - 通道處理改進

### ✅ 已修正問題

1. **移除 pyedflib 依賴**
   - 原因：Windows 上編碼問題導致安裝失敗
   - 解決：使用 MNE-Python 內建的 EDF 讀取功能（功能更強大）

2. **抑制通道名稱重複警告**
   - 現象：`Channel names are not unique, found duplicates for: {'T8-P8'}`
   - 解決：使用 `warnings.catch_warnings()` 自動抑制
   - 說明：MNE 會自動處理重複名稱（加上編號）

3. **支援不同受試者的不同通道配置**
   - 通道數量可以不同
   - 通道名稱可以不同
   - 採樣率可以不同
   - GUI 會自動適應並更新

### 🆕 新增功能

1. **通道資訊顯示增強**
   - 檔案資訊面板顯示通道數
   - 顯示標註數量
   - 少於 5 個通道時直接列出名稱

2. **資料集分析工具**
   - 新增 `utils/check_dataset_channels.py`
   - 功能：
     - 快速掃描整個資料集
     - 統計通道數分佈
     - 檢查採樣率一致性
     - 比較不同受試者的配置
   - 使用：`python utils/check_dataset_channels.py D:\Your\Dataset`

3. **安裝測試腳本**
   - 新增 `test_installation.py`
   - 檢查所有依賴套件
   - 測試 GUI 初始化
   - 顯示版本資訊
   - 使用：`python test_installation.py`

### 📝 文件更新

1. **README.md**
   - 新增通道處理相關 FAQ
   - 說明如何檢查通道配置
   - 解釋警告訊息

2. **requirements.txt**
   - 移除 `pyedflib`（不需要）
   - 移除 `wfdb`（可選，暫不需要）
   - 移除 `PyQt6-Qt6`（會自動安裝）
   - 精簡為 8 個核心依賴

### 🔧 技術改進

1. **更好的錯誤處理**
   - 使用 context manager 控制警告
   - 外部標註載入失敗不影響主程式

2. **記憶體優化**
   - `load_file` 方法支援 `preload=False`
   - 元資料讀取不載入完整資料

## 安裝指南

### 方法 1：完整安裝（推薦）

```bash
cd C:\Code\EEG_visualization_website
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python test_installation.py  # 測試安裝
python main.py                # 啟動程式
```

### 方法 2：最小安裝

```bash
pip install PyQt6 pyqtgraph mne numpy scipy pandas
python main.py
```

## 使用範例

### 1. 啟動程式
```bash
python main.py
```

### 2. 檢查資料集
```bash
# 分析整個資料集
python utils/check_dataset_channels.py D:\EEG_Data\chb-mit

# 比較兩個受試者
python utils/check_dataset_channels.py D:\EEG_Data\chb-mit --compare chb01 chb02
```

### 3. 測試安裝
```bash
python test_installation.py
```

## 已知問題與限制

1. **大檔案載入**
   - 超過 1GB 的單一檔案可能需要較長載入時間
   - 建議：使用「顯示時間」控制減少一次載入的資料量

2. **通道選擇器**
   - 超過 100 個通道時，捲軸區域可能較小
   - 建議：使用搜尋功能（待實作）

3. **標註格式**
   - 目前支援：EDF+, CHB-MIT, TUH, CSV
   - 其他格式需要自訂解析器

## 下一步計劃

- [ ] 添加通道搜尋功能
- [ ] 實作即時濾波（帶通、高通、低通）
- [ ] 頻譜分析視圖
- [ ] 匯出功能（PNG, CSV）
- [ ] HDF5 預處理工具（針對超大資料集）
- [ ] 通道群組功能（例如：只看左腦、右腦）
