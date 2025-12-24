"""
範例配置檔案
展示如何針對不同資料集進行配置
"""

# ============================================================================
# 資料集配置範例
# ============================================================================

# CHB-MIT 癲癇資料集
CHB_MIT_CONFIG = {
    'name': 'CHB-MIT',
    'root_dir': r'D:\EEG_Data\chb-mit',
    'file_pattern': '*.edf',
    'annotation_format': 'chb-mit',  # 使用 CHB-MIT 解析器
    'description': 'CHB-MIT Scalp EEG Database',
}

# TUH EEG 資料集
TUH_CONFIG = {
    'name': 'TUH-EEG',
    'root_dir': r'D:\EEG_Data\tuh',
    'file_pattern': '*.edf',
    'annotation_format': 'tuh',  # 使用 TUH 解析器
    'description': 'Temple University Hospital EEG Corpus',
}

# 自訂資料集 - CSV 標註
CUSTOM_CSV_CONFIG = {
    'name': 'My-Dataset',
    'root_dir': r'C:\My_EEG_Data',
    'file_pattern': '*.edf',
    'annotation_format': 'csv',  # CSV 格式標註
    'description': 'Custom EEG Dataset with CSV annotations',
}

# 無標註資料集
NO_ANNOTATION_CONFIG = {
    'name': 'Raw-EEG',
    'root_dir': r'D:\Raw_EEG',
    'file_pattern': '*.edf',
    'annotation_format': None,  # 無標註
    'description': 'Raw EEG recordings without annotations',
}

# ============================================================================
# 顯示設定
# ============================================================================

DISPLAY_SETTINGS = {
    # 預設時間視窗（秒）
    'default_time_window': 10,

    # 預設振幅縮放
    'default_amplitude_scale': 1.0,

    # 預設顯示所有通道
    'show_all_channels': True,

    # 視窗大小
    'window_width': 1600,
    'window_height': 900,
}

# ============================================================================
# 標註顏色配置
# ============================================================================

ANNOTATION_COLORS = {
    'seizure': (255, 0, 0, 80),      # 紅色
    'sz': (255, 0, 0, 80),           # 紅色（縮寫）
    'artifact': (128, 128, 128, 60), # 灰色
    'sleep_stage_1': (0, 100, 255, 60),  # 藍色
    'sleep_stage_2': (0, 150, 255, 60),
    'sleep_stage_3': (0, 200, 255, 60),
    'rem': (150, 0, 255, 60),        # 紫色
    'awake': (0, 255, 0, 60),        # 綠色
    'default': (255, 165, 0, 60),    # 橘色
}

# ============================================================================
# 通道配置
# ============================================================================

# 常見通道配置
COMMON_MONTAGES = {
    '10-20': [
        'Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4',
        'P3', 'P4', 'O1', 'O2', 'F7', 'F8',
        'T3', 'T4', 'T5', 'T6', 'Fz', 'Cz', 'Pz'
    ],
    'CHB-MIT': [
        'FP1-F7', 'F7-T7', 'T7-P7', 'P7-O1',
        'FP1-F3', 'F3-C3', 'C3-P3', 'P3-O1',
        'FP2-F4', 'F4-C4', 'C4-P4', 'P4-O2',
        'FP2-F8', 'F8-T8', 'T8-P8', 'P8-O2',
        'FZ-CZ', 'CZ-PZ'
    ],
}

# ============================================================================
# 濾波器配置
# ============================================================================

FILTER_PRESETS = {
    '無': {
        'enabled': False
    },
    '0.5-40 Hz': {
        'enabled': True,
        'highpass': 0.5,
        'lowpass': 40.0,
        'description': '標準臨床 EEG 濾波'
    },
    '1-30 Hz': {
        'enabled': True,
        'highpass': 1.0,
        'lowpass': 30.0,
        'description': '去除低頻漂移和高頻雜訊'
    },
    '8-13 Hz (Alpha)': {
        'enabled': True,
        'highpass': 8.0,
        'lowpass': 13.0,
        'description': 'Alpha 波段'
    },
    '自訂': {
        'enabled': True,
        'highpass': None,  # 由使用者設定
        'lowpass': None,
        'description': '自訂濾波參數'
    }
}

# ============================================================================
# 效能設定
# ============================================================================

PERFORMANCE_SETTINGS = {
    # 大檔案閾值（MB），超過此大小使用片段載入
    'large_file_threshold': 500,

    # 片段載入時的緩衝區大小（秒）
    'segment_buffer': 10,

    # 最大同時顯示通道數
    'max_visible_channels': 50,

    # 資料降採樣閾值（樣本數）
    'downsample_threshold': 100000,
}

# ============================================================================
# 使用範例
# ============================================================================

if __name__ == '__main__':
    """
    這個配置檔案展示如何設定不同的參數。

    在主程式中使用：

    from example_config import CHB_MIT_CONFIG, DISPLAY_SETTINGS

    # 載入資料集
    dataset = load_dataset(CHB_MIT_CONFIG['root_dir'])

    # 應用顯示設定
    viewer.set_time_window(DISPLAY_SETTINGS['default_time_window'])
    """

    print("配置檔案範例")
    print("\n支援的資料集：")
    for config in [CHB_MIT_CONFIG, TUH_CONFIG, CUSTOM_CSV_CONFIG]:
        print(f"  - {config['name']}: {config['description']}")

    print("\n預設顯示設定：")
    for key, value in DISPLAY_SETTINGS.items():
        print(f"  {key}: {value}")

    print("\n濾波器預設：")
    for name, settings in FILTER_PRESETS.items():
        if settings['enabled']:
            print(f"  {name}: {settings.get('highpass', 'N/A')} - {settings.get('lowpass', 'N/A')} Hz")
