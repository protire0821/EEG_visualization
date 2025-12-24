@echo off
REM EEG Viewer 自動安裝腳本

echo ========================================
echo EEG Viewer - 自動安裝程式
echo ========================================
echo.

REM 檢查 Python 是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python！
    echo 請先從 https://www.python.org/downloads/ 下載並安裝 Python 3.9+
    pause
    exit /b 1
)

echo [1/4] 檢測到 Python：
python --version
echo.

REM 建立虛擬環境
echo [2/4] 建立虛擬環境...
python -m venv .venv
if errorlevel 1 (
    echo [錯誤] 無法建立虛擬環境
    pause
    exit /b 1
)
echo      完成！
echo.

REM 啟動虛擬環境
echo [3/4] 啟動虛擬環境...
call .venv\Scripts\activate.bat
echo      完成！
echo.

REM 升級 pip
echo [升級 pip...]
python -m pip install --upgrade pip --quiet
echo      完成！
echo.

REM 安裝依賴
echo [4/4] 安裝依賴套件（這可能需要幾分鐘）...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [錯誤] 安裝失敗！
    echo 請檢查錯誤訊息，或手動執行：
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 安裝完成！
echo ========================================
echo.
echo 接下來您可以：
echo   1. 執行測試：python test_installation.py
echo   2. 啟動程式：python main.py
echo      或直接雙擊 run.bat
echo.
echo 請參考 START_HERE.txt 了解更多資訊
echo ========================================
pause
