# EEG Visualizer

A desktop viewer for EEG recordings. Open a single file or a whole dataset
folder, scroll through the traces, watch the scalp topography animate as it
plays, and jump straight to annotated seizures.

Built on MNE-Python for I/O, pyqtgraph for the waveform, and matplotlib for the
topomap, in a PyQt6 shell.

![Main window](docs/screenshots/main_window.png)

## Install

```bash
pip install -r requirements.txt
python main.py
```

Python 3.10 or newer (the code uses `X | None` annotations).

## What it does

- **Open one recording** (`Ctrl+O`) or **a whole dataset folder** (`Ctrl+Shift+O`).
  A folder is scanned into subjects and recordings, so a corpus like CHB-MIT
  browses as `chb01 → chb01_03.edf` without digging through directories.
- **Waveform** — all channels stacked, per-channel colours, with a playback
  cursor that auto-scrolls. Channel names label the Y axis.
- **Channel selection** — tick channels on and off; the stack re-lays out to
  the visible set.
- **Time window** — 5 to 300 seconds visible at once.
- **Display filters** — high-pass, low-pass and a mains notch, as zero-phase
  Butterworth so spike onsets keep their timing. Defaults to the usual review
  setting of 0.5 / 70 / 50 Hz; the unfiltered data is kept, so changing the
  filters never degrades the source.
- **Sensitivity in µV** — the gap between two channel baselines *is* the
  sensitivity, the way a review station works: 70 µV is typical and a smaller
  number magnifies the traces. Fixed, never auto-scaled, so trace height means
  the same thing in every recording.
- **Topomap** — instantaneous scalp potential, redrawn as playback advances.
  The colour range is *fixed for the whole recording*, never rescaled per frame,
  so frames can be compared; a colour bar and the title both show the range in
  µV. `Auto` fits it to the recording (99th percentile of |signal|); picking a
  fixed value instead keeps the colours comparable between recordings.
- **Events** — every annotation found for the recording is listed; seizures are
  shaded red on the waveform and shown in red in the list. Clicking an event
  jumps the view to five seconds before onset.
- **Transport** — play/pause, 0.25×–4× speed, and a scrubber. Playback is
  anchored to the wall clock, so a slow repaint drops frames instead of
  stretching time: 1.0× stays 1.0×.

## Supported data

| | |
|---|---|
| Recordings | `.edf`, `.bdf`, `.fif`, `.set`, `.vhdr` (whatever MNE can read) |
| Annotations | EDF+ embedded, CHB-MIT `-summary.txt`, CSV, TUH `.tse` / `.csv_bi` |

Annotations are discovered automatically for a recording `rec.edf`: EDF+
internal annotations, a sibling `rec.csv`, a per-recording `rec-summary.txt`, a
per-subject `chbNN-summary.txt`, and `annotations.csv` in the same folder.
Duplicates across sources are collapsed, so a seizure listed in two places
appears once.

**Channel names are normalised before matching.** The montage match is literal,
and corpora rarely store bare `Fp1`: TUH writes `EEG FP1-REF`, ear-referenced
recordings write `Fp1-A1`. The `EEG ` prefix and reference suffixes (`-REF`,
`-LE`, `-AV`, `-A1`, `-M1`, …) are stripped automatically, so those files get a
topomap; the status bar says how many channels were normalised. Non-EEG channels
(`ECG`, `EKG1-EKG2`, `PHOTIC-REF`, triggers) are recognised and skipped rather
than counted as failures.

**On the topomap and bipolar montages.** A topomap interpolates a scalar field
over electrode positions, so it needs one position per channel. CHB-MIT and most
clinical recordings store *bipolar derivations* — `FP1-F7` is the difference
between two electrodes, closer to a spatial derivative than to a potential — so
there is no single position to place it at, and plotting it at the pair midpoint
would draw a gradient map dressed up as a voltage map. Those recordings are
labelled "Bipolar recording" in the toolbar and load with the waveform, filters
and events all working, with the topomap showing "no electrode positions".
Monopolar recordings (`Fp1`, `F3`, …) get a working topomap. Reconstructing
potentials from the bipolar graph is on the roadmap below.

## If playback stutters

Position is clock-driven, so speed stays correct even when frames are dropped —
but smoothness depends on how fast your machine can repaint 20-odd traces. Two
environment variables help:

```bash
EEGVIZ_FPS=15 python main.py      # repaint less often (default 25)
EEGVIZ_OPENGL=1 python main.py    # pyqtgraph's GL renderer; needs PyOpenGL
```

OpenGL is off by default because it is not a guaranteed win — pyqtgraph's GL
path skips some drawing features, and with clipping and downsampling already on
the CPU renderer is usually fast enough. Narrowing the time window and
unticking channels both cut per-frame work as well.

## Keyboard

| | |
|---|---|
| `Ctrl+O` | Open recording |
| `Ctrl+Shift+O` | Open dataset folder |
| `Ctrl+Q` | Quit |

## Project structure

```
main.py                     entry point — sets the Qt backend, opens the window
core/
  edf_reader.py             loads a recording, montage, annotations
  filters.py                zero-phase high-pass / low-pass / notch
  montage.py                channel-name normalisation and classification
  annotations.py            CHB-MIT / CSV / EDF+ / TUH parsers
  dataset.py                folder → subject → recordings scanning
  playback.py               QTimer transport, emits frame_changed at 25 fps
ui/
  main_window.py            side panel, transport, wiring
  waveform_widget.py        stacked traces, cursor, annotation regions
  topomap_widget.py         matplotlib topomap in a Qt canvas
utils/
  check_dataset_channels.py CLI: report channel counts and rates per subject
tests/                      parser and scanner tests (no GUI needed)
```

## Tools

Check that a corpus is internally consistent before working with it:

```bash
python -m utils.check_dataset_channels /path/to/dataset
```

It reads headers only and reports, per subject, how many channels each file has,
whether the layouts and sampling rates agree, and which files failed to open.

## Tests

```bash
python -m pytest tests/ -q
```

The tests cover annotation parsing and dataset scanning; they do not need a
display or any EEG data.

## Limitations

- Recordings are loaded fully into memory (`preload=True`), so a multi-hour file
  at a high sampling rate needs the RAM to match. A one-hour 23-channel 256 Hz
  recording is ~170 MB of samples and peaks near 1 GB while filtering.
- Pressing Apply re-filters the whole recording, which takes about 6 seconds on
  that same one-hour file.
- Filtering is for display only and is applied to the whole recording at once;
  on a multi-hour file, pressing Apply takes a few seconds.
- No re-referencing, ICA, or artifact rejection — this is a viewer, not a
  preprocessing tool.
- The topomap redraws through matplotlib, which costs ~40 ms, so it is throttled
  to about 8 fps while the waveform runs at 25. Recordings without electrode
  positions skip it entirely and play at full rate.
- Playback smoothness (not speed) depends on repaint cost — see *If playback
  stutters* above.

## Roadmap

- Montage re-derivation (longitudinal / transverse bipolar, average reference,
  Laplacian), which needs the same reconstruction as the topomap item below.
- Lazy loading for files that do not fit in memory.
- Export the current view as PNG/SVG.
- Spectrogram / PSD panel alongside the waveform.
- Bipolar montage support for the topomap by deriving positions from the pair.
- Package for `pip install` with an entry-point script.

## License

MIT — see `LICENSE`.

Tung Lun Yang — https://github.com/protire0821

## 快速開始 (中文)

```bash
pip install -r requirements.txt
python main.py
```

`Ctrl+O` 開單一檔案，`Ctrl+Shift+O` 開整個資料集資料夾（會自動掃成「受試者 → 紀錄」兩層）。
上方工具列可調靈敏度（µV，數字越小波形越大）、時間視窗長度，以及高通／低通／陷波三個濾波器（預設 0.5 / 70 / 50 Hz，
按 Apply 生效；用零相位 Butterworth，不會位移棘波起始點）。左側面板可勾選要顯示的通道，並列出所有標註事件；
點任一癲癇事件會跳到發作前 5 秒，波形上該區段以紅色標示。

支援 `.edf`／`.bdf`／`.fif`／`.set`／`.vhdr`，標註來源包含 EDF+ 內建、CHB-MIT `-summary.txt`、CSV 與 TUH `.tse`。

注意：地形圖（topomap）需要每個通道對應到一個電極座標，而 CHB-MIT 這類存的是**雙極導程**
（`FP1-F7` 是兩個電極的電位差，性質上比較接近空間導數而非電位），沒有單一座標可放，硬畫在兩電極中點
會得到一張「看起來像電位圖、實際是梯度圖」的誤導結果。因此這類檔案工具列會標示「Bipolar recording」，
波形、濾波與事件都正常運作，地形圖區域顯示「無電極座標」。
