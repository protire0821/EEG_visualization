"""
測試安裝腳本

檢查所有依賴套件是否正確安裝
"""

import sys

def test_imports():
    """測試所有必要的套件是否能正確匯入"""

    print("🧪 測試 EEG Viewer 安裝狀態...\n")

    tests = [
        ("PyQt6", "from PyQt6.QtWidgets import QApplication"),
        ("pyqtgraph", "import pyqtgraph as pg"),
        ("NumPy", "import numpy as np"),
        ("SciPy", "import scipy"),
        ("MNE-Python", "import mne"),
        ("h5py", "import h5py"),
        ("pandas", "import pandas as pd"),
    ]

    failed = []
    success = []

    for name, import_cmd in tests:
        try:
            exec(import_cmd)
            print(f"✅ {name:20s} OK")
            success.append(name)
        except ImportError as e:
            print(f"❌ {name:20s} 失敗: {e}")
            failed.append(name)

    print(f"\n📊 結果: {len(success)}/{len(tests)} 成功")

    if failed:
        print(f"\n⚠️  缺少的套件: {', '.join(failed)}")
        print("\n請執行: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ 所有依賴套件安裝正確！")
        return True


def test_gui():
    """測試 GUI 是否能正常啟動"""

    print("\n🖼️  測試 GUI 初始化...")

    try:
        from PyQt6.QtWidgets import QApplication
        from gui.main_window import MainWindow

        app = QApplication([])
        window = MainWindow()

        print("✅ GUI 初始化成功")
        return True

    except Exception as e:
        print(f"❌ GUI 初始化失敗: {e}")
        return False


def test_data_loader():
    """測試資料載入器"""

    print("\n📂 測試資料載入器...")

    try:
        from data_loader.eeg_loader import EEGDataLoader
        from data_loader.annotation_parser import AnnotationParserFactory

        loader = EEGDataLoader()
        print(f"✅ 支援的格式: {', '.join(loader.supported_formats)}")

        parsers = list(AnnotationParserFactory._parsers.keys())
        print(f"✅ 標註解析器: {', '.join(parsers)}")

        return True

    except Exception as e:
        print(f"❌ 資料載入器測試失敗: {e}")
        return False


def get_version_info():
    """顯示版本資訊"""

    print("\n📋 版本資訊:")

    try:
        import PyQt6.QtCore
        print(f"   PyQt6: {PyQt6.QtCore.PYQT_VERSION_STR}")
    except:
        pass

    try:
        import numpy
        print(f"   NumPy: {numpy.__version__}")
    except:
        pass

    try:
        import mne
        print(f"   MNE: {mne.__version__}")
    except:
        pass

    print(f"   Python: {sys.version.split()[0]}")
    print(f"   平台: {sys.platform}")


if __name__ == '__main__':
    print("=" * 60)
    print("EEG Viewer 安裝測試")
    print("=" * 60 + "\n")

    # 測試匯入
    imports_ok = test_imports()

    if not imports_ok:
        print("\n⚠️  請先安裝缺少的套件")
        sys.exit(1)

    # 測試資料載入器
    loader_ok = test_data_loader()

    # 測試 GUI
    gui_ok = test_gui()

    # 顯示版本
    get_version_info()

    # 最終結果
    print("\n" + "=" * 60)
    if imports_ok and loader_ok and gui_ok:
        print("🎉 所有測試通過！可以執行 python main.py 啟動程式")
    else:
        print("⚠️  某些測試失敗，請檢查錯誤訊息")
    print("=" * 60)
