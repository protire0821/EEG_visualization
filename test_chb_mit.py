"""
測試 CHB-MIT 標註解析器

使用方法：
python test_chb_mit.py D:\EEG_Data\chb-mit\chb01\chb01_03.edf
"""

import sys
import os
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent))

from data_loader.annotation_parser import load_annotations_for_file, CHBMITAnnotationParser


def test_annotation_loading(eeg_file_path):
    """測試標註載入"""

    print("=" * 60)
    print("CHB-MIT 標註載入測試")
    print("=" * 60)
    print(f"\n📂 EEG 檔案: {eeg_file_path}")
    print(f"   檔案名: {os.path.basename(eeg_file_path)}")
    print(f"   目錄: {os.path.dirname(eeg_file_path)}")

    # 檢查檔案是否存在
    if not os.path.exists(eeg_file_path):
        print(f"\n❌ 檔案不存在: {eeg_file_path}")
        return

    # 尋找 summary 檔案
    filename = os.path.basename(eeg_file_path)
    dir_name = os.path.dirname(eeg_file_path)

    import re
    subject_match = re.match(r'(chb\d+)', filename.lower())
    if subject_match:
        subject_id = subject_match.group(1)
        subject_summary = os.path.join(dir_name, f'{subject_id}-summary.txt')

        print(f"\n🔍 搜尋 summary 檔案:")
        print(f"   預期位置: {subject_summary}")
        print(f"   存在: {'✓ 是' if os.path.exists(subject_summary) else '✗ 否'}")

        if os.path.exists(subject_summary):
            # 測試解析
            print(f"\n📖 解析 summary 檔案...")
            parser = CHBMITAnnotationParser()

            # 不指定目標檔案（載入所有）
            all_annotations = parser.parse(subject_summary)
            print(f"   所有標註數量: {len(all_annotations)}")

            # 指定目標檔案（只載入當前檔案）
            file_annotations = parser.parse(subject_summary, filename)
            print(f"   當前檔案標註: {len(file_annotations)}")

            if file_annotations:
                print(f"\n✅ 找到 {len(file_annotations)} 個癲癇發作事件:")
                for i, annot in enumerate(file_annotations, 1):
                    print(f"\n   事件 #{i}:")
                    print(f"      開始時間: {annot['start_time']:.1f} 秒 ({_format_time(annot['start_time'])})")
                    print(f"      結束時間: {annot['end_time']:.1f} 秒 ({_format_time(annot['end_time'])})")
                    print(f"      持續時長: {annot['metadata']['duration']:.1f} 秒")
                    print(f"      標籤: {annot['label']}")
                    print(f"      描述: {annot['description']}")
            else:
                print(f"\n   ℹ️  此檔案無癲癇發作事件")

    print(f"\n" + "=" * 60)
    print("使用完整 load_annotations_for_file 函數測試")
    print("=" * 60)

    # 使用完整函數測試
    annotations = load_annotations_for_file(eeg_file_path)

    print(f"\n📊 載入結果:")
    print(f"   總標註數: {len(annotations)}")

    if annotations:
        print(f"\n標註詳情:")
        for i, annot in enumerate(annotations, 1):
            print(f"\n   [{i}] {annot.get('description', annot.get('label', 'Unknown'))}")
            print(f"       時間: {_format_time(annot['start_time'])} - {_format_time(annot['end_time'])}")
            print(f"       持續: {annot.get('end_time', 0) - annot.get('start_time', 0):.1f} 秒")
            print(f"       來源: {annot.get('metadata', {}).get('source', 'unknown')}")
    else:
        print(f"\n   ℹ️  無標註")

    print(f"\n" + "=" * 60)


def _format_time(seconds):
    """格式化時間顯示"""
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_chb_mit.py <EEG檔案路徑>")
        print("\n範例:")
        print("  python test_chb_mit.py D:\\EEG_Data\\chb-mit\\chb01\\chb01_03.edf")
        sys.exit(1)

    eeg_file = sys.argv[1]
    test_annotation_loading(eeg_file)
