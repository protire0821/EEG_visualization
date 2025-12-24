"""
資料集通道檢查工具

快速掃描整個資料集，顯示：
- 每個受試者有多少檔案
- 每個檔案有多少通道
- 通道名稱是否一致
- 採樣率是否一致
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import warnings

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader.eeg_loader import EEGDataLoader


def analyze_dataset(root_dir: str):
    """分析資料集的通道配置"""

    print(f"🔍 掃描資料集: {root_dir}\n")

    loader = EEGDataLoader()

    # 掃描結構
    structure = loader.scan_dataset(root_dir)

    print(f"📊 找到 {len(structure)} 個受試者/群組\n")

    # 統計資訊
    all_channels = set()
    all_sfreqs = set()
    channel_counts = defaultdict(int)
    channel_sets = {}

    # 分析每個受試者
    for subject_id, subject_info in structure.items():
        print(f"👤 受試者: {subject_id}")
        print(f"   檔案數: {len(subject_info['recordings'])}")

        subject_channels = []
        subject_sfreqs = []

        for rec in subject_info['recordings'][:3]:  # 只檢查前 3 個檔案（節省時間）
            try:
                file_path = rec['path']

                # 只讀取元資料，不載入資料
                import mne
                ext = Path(file_path).suffix.lower()

                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')

                    if ext in ['.edf', '.bdf']:
                        raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
                    elif ext == '.fif':
                        raw = mne.io.read_raw_fif(file_path, preload=False, verbose=False)
                    elif ext == '.set':
                        raw = mne.io.read_raw_eeglab(file_path, preload=False, verbose=False)
                    elif ext == '.vhdr':
                        raw = mne.io.read_raw_brainvision(file_path, preload=False, verbose=False)
                    else:
                        continue

                n_channels = len(raw.ch_names)
                sfreq = raw.info['sfreq']

                subject_channels.append(n_channels)
                subject_sfreqs.append(sfreq)

                all_channels.update(raw.ch_names)
                all_sfreqs.add(sfreq)
                channel_counts[n_channels] += 1

                # 儲存第一個檔案的通道配置
                if subject_id not in channel_sets:
                    channel_sets[subject_id] = {
                        'channels': raw.ch_names,
                        'n_channels': n_channels,
                        'sfreq': sfreq,
                        'filename': rec['filename']
                    }

            except Exception as e:
                print(f"   ⚠️  無法讀取 {rec['filename']}: {e}")
                continue

        if subject_channels:
            # 檢查一致性
            channels_consistent = len(set(subject_channels)) == 1
            sfreq_consistent = len(set(subject_sfreqs)) == 1

            print(f"   通道數: {subject_channels[0]}", end="")
            if not channels_consistent:
                print(f" ⚠️ 不一致！範圍: {min(subject_channels)}-{max(subject_channels)}")
            else:
                print(" ✓")

            print(f"   採樣率: {subject_sfreqs[0]} Hz", end="")
            if not sfreq_consistent:
                print(f" ⚠️ 不一致！")
            else:
                print(" ✓")

        print()

    # 總結
    print("=" * 60)
    print("📈 資料集總結\n")

    print(f"通道數分佈:")
    for n_ch in sorted(channel_counts.keys()):
        print(f"  {n_ch} 個通道: {channel_counts[n_ch]} 個檔案")

    print(f"\n採樣率:")
    for sfreq in sorted(all_sfreqs):
        print(f"  {sfreq} Hz")

    print(f"\n唯一通道名稱總數: {len(all_channels)}")

    # 顯示每個受試者的通道配置範例
    print("\n" + "=" * 60)
    print("📋 通道配置範例\n")

    for subject_id, config in list(channel_sets.items())[:3]:  # 只顯示前 3 個
        print(f"受試者: {subject_id} ({config['filename']})")
        print(f"  {config['n_channels']} 個通道 @ {config['sfreq']} Hz")
        print(f"  通道: {', '.join(config['channels'][:10])}", end="")
        if len(config['channels']) > 10:
            print(f" ... (還有 {len(config['channels']) - 10} 個)")
        else:
            print()
        print()


def compare_subjects(root_dir: str, subject1: str, subject2: str):
    """比較兩個受試者的通道配置"""

    loader = EEGDataLoader()
    structure = loader.scan_dataset(root_dir)

    if subject1 not in structure or subject2 not in structure:
        print("❌ 找不到指定的受試者")
        return

    print(f"🔬 比較受試者: {subject1} vs {subject2}\n")

    for subject_id in [subject1, subject2]:
        rec = structure[subject_id]['recordings'][0]
        data, info = loader.load_file(rec['path'])

        print(f"📁 {subject_id} ({rec['filename']})")
        print(f"   通道數: {info['n_channels']}")
        print(f"   採樣率: {info['sfreq']} Hz")
        print(f"   通道: {', '.join(info['ch_names'])}")
        print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='檢查 EEG 資料集的通道配置')
    parser.add_argument('dataset_path', help='資料集根目錄路徑')
    parser.add_argument('--compare', nargs=2, metavar=('SUBJECT1', 'SUBJECT2'),
                       help='比較兩個受試者的通道配置')

    args = parser.parse_args()

    if not os.path.exists(args.dataset_path):
        print(f"❌ 路徑不存在: {args.dataset_path}")
        sys.exit(1)

    if args.compare:
        compare_subjects(args.dataset_path, args.compare[0], args.compare[1])
    else:
        analyze_dataset(args.dataset_path)
