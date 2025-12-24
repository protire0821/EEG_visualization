@echo off
REM EEG Viewer 啟動腳本

echo ========================================
echo EEG Viewer - 腦波可視化工具
echo ========================================
echo.

REM 檢查虛擬環境是否存在
if exist ".venv\Scripts\activate.bat" (
    echo [啟動] 使用虛擬環境...
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 找不到虛擬環境，使用系統 Python
)

REM 啟動程式
echo [執行] 啟動 EEG Viewer...
python main.py

REM 如果程式崩潰，保持視窗開啟
if errorlevel 1 (
    echo.
    echo [錯誤] 程式異常結束
    pause
)
