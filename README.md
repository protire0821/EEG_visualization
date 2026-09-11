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
- **Time window** — 1 to 300 seconds visible at once.
- **Topomap** — instantaneous scalp potential, redrawn as playback advances,
  on a fixed colour scale taken from the 99th percentile of the recording.
- **Events** — every annotation found for the recording is listed; seizures are
  shaded red on the waveform and shown in red in the list. Clicking an event
  jumps the view to five seconds before onset.
- **Transport** — play/pause, 0.25×–4× speed, 0.1×–5× gain, and a scrubber.

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

**On the topomap and bipolar montages.** The topomap needs electrode positions,
which come from matching channel names against MNE's `standard_1020` montage.
CHB-MIT and most clinical recordings use bipolar pairs (`FP1-F7`, `F7-T7`), which
do not match, so those files load with the waveform and events working and the
topomap showing "no electrode positions". Monopolar recordings (`Fp1`, `F3`, …)
get a working topomap.

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
  at a high sampling rate needs the RAM to match.
- No filtering, re-referencing, or artifact rejection — this is a viewer, not a
  preprocessing tool.
- The topomap redraws through matplotlib on every frame, which is the limiting
  factor on playback smoothness for long recordings.

## Roadmap

- Filter panel (band-pass, notch) and re-referencing.
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
左側面板可勾選要顯示的通道、切換時間視窗長度，並列出所有標註事件；點任一癲癇事件會跳到發作前 5 秒，
波形上該區段以紅色標示。

支援 `.edf`／`.bdf`／`.fif`／`.set`／`.vhdr`，標註來源包含 EDF+ 內建、CHB-MIT `-summary.txt`、CSV 與 TUH `.tse`。

注意：地形圖（topomap）需要電極座標，而 CHB-MIT 這類雙極導程命名（`FP1-F7`）無法對應到 10-20 montage，
因此這類檔案會正常顯示波形與事件，但地形圖區域會顯示「無電極座標」。
