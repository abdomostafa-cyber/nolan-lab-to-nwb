# nolan-lab-to-nwb

Converting a real lab recording to [NWB](https://www.nwb.org/) with
[NeuroConv](https://github.com/catalystneuro/neuroconv), validating it with
[NWB Inspector](https://github.com/NeurodataWithoutBorders/nwbinspector), and checking
the result against the raw files independently of the converter.

> Status: conversion, validation and tests done; CI next.

## Dataset

One open-field session from the Nolan Lab (University of Edinburgh): a mouse with four
tetrodes aimed at medial entorhinal cortex, recorded with the Open Ephys GUI 0.4.2.1 in
the legacy `.continuous` format (16 tetrode channels, 3 headstage accelerometer channels,
8 analog inputs, 30 kHz, about 37 min).

Buccino & Halcrow, *SpikeInterface Training Dataset* v2, Zenodo,
<https://doi.org/10.5281/zenodo.20726062> (CC BY 4.0), session
`1544_2023-04-21_09-55-34_of`, recorded by Brianna Vandrey.

## Reproduce

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python scripts/download_data.py
uv run pytest
```

`download_data.py --metadata-only` fetches just `settings.xml` and the event files
(about 50 kB) by reading the remote zip with HTTP range requests.

Convert (about 2 minutes, writes a 2.1 GB file):

```bash
uv run python -m nolan_lab_to_nwb.convert \
    --data-dir data/raw/1544_2023-04-21_09-55-34_of \
    --output data/nwb/sub-1544_ses-1544-2023-04-21-09-55-34-of_ecephys.nwb
```

Add `--stub` to write only the first 100 samples of each series, for a quick check.

## What ends up in the NWB file

| NWB object | Source | Notes |
|---|---|---|
| `acquisition/ElectricalSeries` (66,592,800 × 16, int16) | `100_CH1-16.continuous` | wideband, `conversion` = 0.195 µV/bit from the headers; 4 `ElectrodeGroup`s (one per tetrode) from the Spike Detector in `settings.xml` |
| `acquisition/TimeSeriesAnalogInput` (× 8) | `100_ADC1-8.continuous` | volts, `conversion` = 152.6 µV/bit |
| `acquisition/TimeSeriesAuxiliaryInput` (× 3) | `100_AUX1-3.continuous` | pinned at the int16 maximum in this session; kept, not presented as an accelerometer |
| `intervals/SyncPulses` (56 rows) | detected on ADC1 | custom `SyncPulseInterface`, 2.5 V threshold |
| `general/subject`, devices, session info | `src/nolan_lab_to_nwb/metadata.yaml` | values the files do not contain, each sourced or marked unknown |

Custom code, beyond NeuroConv's `OpenEphysLegacyRecordingInterface`:
- `OpenEphysLegacyAnalogInterface`: writes the AUX and ADC streams as `TimeSeries`. NeuroConv has
  this only for the binary Open Ephys format.
- `SyncPulseInterface`: turns ADC1 pulses into an intervals table.
- `openephys_settings.read_settings`: reads the tetrode grouping and hardware filter from `settings.xml`.

## Timestamps and alignment

- **t = 0 is the first recorded sample.** The Open Ephys sample counter reads 107,400 (3.58 s)
  there, because acquisition started before recording did. All streams share this counter, so
  all are shifted by the same −3.58 s. The original offset is stated in the ElectricalSeries
  description.
- **`session_start_time` = 2023-04-21 09:55:34, Europe/London (BST, UTC+01:00).** Wall-clock
  time comes from `settings.xml` and has one-second resolution; the timezone is an
  assumption (lab in Edinburgh). NeuroConv's own parsing of the `.continuous` header keeps
  only the date for this file (the header writes the time as `95534`), so the YAML sets it.
- **End padding removed.** The GUI zero-fills the last 1024-sample record when recording stops.
  The final 992 samples (zero on all 27 channels) are trimmed, leaving 2219.76 s.
- **No external clock.** The files contain no position or video data. The ADC1 pulses look like
  camera-sync pulses and are written with their times, but nothing in this dataset can be
  aligned to them.

## NWB Inspector report

`uv run nwbinspector data/nwb/<file>.nwb --threshold BEST_PRACTICE_SUGGESTION` on the full file:

| Importance | Check | Status |
|---|---|---|
| CRITICAL | `check_subject_age`: no age or date of birth | **Left on purpose.** The dataset reports neither, and no publication covers this animal. The lab's papers disagree on age, sex and strain, so nothing is guessed. Asked the lab. |

Everything else the Inspector found along the way is fixed:
- `check_electrodes_location_allen_ccf` (BEST_PRACTICE_VIOLATION): the electrodes table said
  `unknown`. It now uses the Allen CCF term "Entorhinal area". The dataset says "aimed at MEC"
  without a dorsal or ventral zone, so the parent term is used.

`tests/test_inspector.py` fails on any issue at BEST_PRACTICE_VIOLATION or above that is not in
this table. It also fails if a listed exception stops firing, so this table can't go stale.

## How the result is verified

The tests never compare the NWB file against NeuroConv's own reading of the data:

- **Independent reader.** `tests/raw_openephys.py` decodes `.continuous` files with numpy only,
  from the format description, and is tested on its own (big-endian samples decoded by hand
  from the bytes).
- **Round trip** (`tests/test_roundtrip.py`, on two 1 MB fixtures cut from the real files):
  - every sample identical to the raw int16;
  - `conversion` equals the header `bitVolts` (µV for CH, V for ADC/AUX);
  - rate and start time;
  - electrode → tetrode mapping and locations;
  - the padding boundary;
  - sync-pulse edges against an independent detection;
  - session start time and subject.
- **Full session** (`tests/test_full_session.py`, run locally, skipped in CI): all 27 channels
  × 66,592,800 samples identical to the raw files; 56 pulses.
- **Mutation check** (`scripts/mutation_check.py`): six plausible bugs are injected one at a
  time, and the suite must fail on each. Current result: 6/6 caught. The six bugs: mV instead
  of V, untrimmed padding, Channel Map off by one, start offset not removed, pulse edge one
  sample early, UTC instead of BST.

```bash
uv run pytest                              # fixtures + full session if present
uv run python scripts/mutation_check.py
```

## Repository layout

```
src/nolan_lab_to_nwb/   conversion package (CLI: python -m nolan_lab_to_nwb.convert)
scripts/download_data.py   fetches and md5-verifies the raw data into data/ (gitignored)
tests/                     pytest suite, runs on a trimmed fixture in CI
DEVLOG.md                  what went wrong during development, how it was caught, how it was fixed
```

## License

Code: MIT (see `LICENSE`). Data: CC BY 4.0, owned by its authors and not redistributed here.
