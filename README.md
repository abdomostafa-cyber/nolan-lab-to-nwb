# nolan-lab-to-nwb

[![CI](https://github.com/abdomostafa-cyber/nolan-lab-to-nwb/actions/workflows/ci.yml/badge.svg)](https://github.com/abdomostafa-cyber/nolan-lab-to-nwb/actions/workflows/ci.yml)

A conversion of a real tetrode recording (Open Ephys legacy format) to
[NWB](https://www.nwb.org/) with [NeuroConv](https://github.com/catalystneuro/neuroconv), validated
with [NWB Inspector](https://github.com/NeurodataWithoutBorders/nwbinspector) and checked
sample by sample against the raw files by code that shares nothing with the converter.

## Dataset

One open-field session from the Nolan Lab (University of Edinburgh): a mouse with four tetrodes
aimed at medial entorhinal cortex, recorded with Open Ephys GUI 0.4.2.1 in the legacy `.continuous`
format. It has 16 tetrode channels, 3 headstage auxiliary inputs and 8 analog inputs, at 30 kHz,
for 2219.76 s.

Buccino & Halcrow, *SpikeInterface Training Dataset* v2, Zenodo,
<https://doi.org/10.5281/zenodo.20726062> (CC BY 4.0), session `1544_2023-04-21_09-55-34_of`,
recorded by Brianna Vandrey.

## Reproduce

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python scripts/download_data.py        # 2.2 GB zip from Zenodo, md5-checked, unzipped into data/raw/
uv run nolan-lab-to-nwb-convert \
    --data-dir data/raw/1544_2023-04-21_09-55-34_of \
    --output data/nwb/sub-1544_ses-1544-2023-04-21-09-55-34-of_ecephys.nwb   # ~2 min, 2.1 GB
uv run pytest                                  # fixtures, plus the full session when present
uv run python -m nolan_lab_to_nwb.inspection data/nwb/*.nwb
```

`--stub` writes only the first 100 samples of each series. `download_data.py --metadata-only`
fetches just `settings.xml` and the event files (about 50 kB) by reading the remote zip with HTTP
range requests. Uploading to the DANDI sandbox is covered in [docs/dandi_sandbox.md](docs/dandi_sandbox.md).

## What ends up in the NWB file

| NWB object | Source | Notes |
|---|---|---|
| `acquisition/ElectricalSeries` (66,592,800 × 16, int16) | `100_CH1-16.continuous` | wideband (Intan on-chip 1.96–7604 Hz only); `conversion` = 0.195 µV/bit from the headers; one `ElectrodeGroup` per tetrode, from the Spike Detector in `settings.xml` |
| `acquisition/TimeSeriesAnalogInput` (× 8) | `100_ADC1-8.continuous` | volts, `conversion` = 152.6 µV/bit |
| `acquisition/TimeSeriesAuxiliaryInput` (× 3) | `100_AUX1-3.continuous` | pinned at the int16 maximum for the whole session; kept, and not called an accelerometer |
| `intervals/SyncPulses` (56 rows) | detected on ADC1 | 150 ms pulses 20–58 s apart, consistent with the lab's published LED sync ([Gerlei et al. 2020](https://doi.org/10.1038/s41467-020-17500-1)); not confirmed for this session |
| subject, devices, session | [`metadata.yaml`](src/nolan_lab_to_nwb/metadata.yaml) | everything the files don't contain, each value sourced or marked unknown |

Beyond NeuroConv's `OpenEphysLegacyRecordingInterface`, the conversion adds
([`interfaces.py`](src/nolan_lab_to_nwb/interfaces.py), [`converter.py`](src/nolan_lab_to_nwb/converter.py)):

- **`OpenEphysLegacyAnalogInterface`:** AUX and ADC streams as `TimeSeries`. NeuroConv has this
  only for the binary Open Ephys format; the stock legacy interface would put them in the
  electrodes table.
- **`SyncPulseInterface`:** ADC1 pulses as a `TimeIntervals` table.
- **`read_settings`** ([`openephys_settings.py`](src/nolan_lab_to_nwb/openephys_settings.py)):
  tetrode grouping (Channel Map composed with the Spike Detector) and the hardware filter.
- **`SliceSafeOpenEphysLegacyRecordingInterface`:** a local backport of an upstream fix (below).

## Timestamps and alignment

- **t = 0 is the first recorded sample.** The Open Ephys sample counter reads 107,400 (3.58 s)
  there, because acquisition started before recording did. All streams share that counter and are
  shifted by the same amount. The original offset is stated in the ElectricalSeries description.
- **`session_start_time` = 2023-04-21 09:55:34 +01:00.** The time comes from `settings.xml`, at
  one-second resolution. The timezone is assumed (Edinburgh lab, British Summer Time).
  NeuroConv's own header parsing keeps only the date for this file, so the YAML sets it.
- **End padding removed.** The GUI zero-fills the last 1024-sample record when recording stops.
  The final 992 samples, zero on all 27 channels, are trimmed.
- **No position data.** The sync pulses are written with their times, but the camera data they
  would align to are not in the public dataset.

## NWB Inspector report

Full file, every level down to BEST_PRACTICE_SUGGESTION:

| Importance | Check | Status |
|---|---|---|
| CRITICAL | `check_subject_age`: no age or date of birth | **Left on purpose.** The dataset reports neither, and no publication covers this animal. The lab's papers disagree on age, sex and strain, so nothing is guessed. Asked the lab. This also blocks a DANDI upload ([details](docs/dandi_sandbox.md)). |

Found and fixed along the way:
- `check_electrodes_location_allen_ccf` (BEST_PRACTICE_VIOLATION): the electrodes table said
  `unknown`. It now uses the Allen CCF term "Entorhinal area"; the dataset gives no dorsal or
  ventral zone, so the parent term is used.
- The Inspector doesn't flag pynwb 4's deprecated `Device.manufacturer`, but the test suite now
  fails on it. It moved to a `DeviceModel`.

On the 1 MB CI fixtures, `check_single_row` (BEST_PRACTICE_SUGGESTION) also fires, because each
0.55 s window holds a single sync pulse. That is an artifact of the fixture.

The `nwbinspector` CLI exits 0 even when it reports CRITICAL issues, so CI gates on
[`inspection.py`](src/nolan_lab_to_nwb/inspection.py) instead. That gate fails on anything at
BEST_PRACTICE_VIOLATION or above that is not in the table above, and
[`test_inspector.py`](tests/test_inspector.py) fails if a listed exception stops firing.

## How the result is verified

No test compares the NWB file with NeuroConv's own reading of the data:

- **Independent reader.** [`tests/raw_openephys.py`](tests/raw_openephys.py) decodes `.continuous`
  files with numpy alone, from the format description. It has its own tests (big-endian samples
  decoded by hand from the bytes, truncated files rejected).
- **Round trip** ([`test_roundtrip.py`](tests/test_roundtrip.py)), on two 1 MB fixtures cut from
  the real files, one around a sync pulse and one around the end padding:
  - every sample identical to the raw int16;
  - `conversion` equal to the header `bitVolts`;
  - rate and start time;
  - tetrode mapping and locations;
  - the exact padding boundary;
  - sync-pulse edges against an independent detection;
  - start time and subject.
- **Full session** ([`test_full_session.py`](tests/test_full_session.py), local only): all 27
  channels × 66,592,800 samples identical to the raw files; 56 pulses.
- **Mutation check** ([`scripts/mutation_check.py`](scripts/mutation_check.py), also in CI): six
  plausible bugs are injected one at a time, and the suite must fail on each. 6/6 caught: mV
  instead of V, untrimmed padding, Channel Map off by one, offset not removed, pulse edge one
  sample early, UTC instead of BST.

## What was hard

- **The data contradicted the obvious assumptions.** Intan AUX inputs usually carry an
  accelerometer; here they are pinned at the int16 maximum. The event file looked like it might
  hold TTLs; it holds two "recording started" markers, and the sync signal turned out to be on an
  analog input. Every channel was summarised before it was given a name.
- **Silent failure modes.** The zero-padded last record looks like data. In NeuroConv, setting
  `unit` in TimeSeries metadata quietly turns off the gain-to-volts conversion. The Inspector CLI
  passes CI even with CRITICAL findings. None of these raise an error; each needed a check written
  for it.
- **Metadata with no source.** Age, sex and strain aren't in the dataset, and the lab's two
  papers disagree with each other. The file says "unknown" where that is the truth, and the
  missing age stays a CRITICAL Inspector finding instead of becoming a plausible guess.
- **Framework call order.** NeuroConv calls `get_metadata` on every `run_conversion`. A
  workaround that relied on the order of those calls broke on the second call. A test written for
  something else caught it.

## Rough edges found upstream

One fix is submitted upstream ([catalystneuro/neuroconv#2141](https://github.com/catalystneuro/neuroconv/pull/2141)); the rest are notes. See [docs/upstream/](docs/upstream/).

- **NeuroConv (bug):** `get_metadata()` and `run_conversion()` raise `AttributeError` after the
  interface's own `remove_channels()`. The maintainers fixed the Axon case on the same day
  ([catalystneuro/neuroconv#2140](https://github.com/catalystneuro/neuroconv/pull/2140)).
  `OpenEphysLegacyRecordingInterface` is still affected on current `main`, reproduced on NeuroConv's
  own test data. A fix in the same style as #2140, with a regression test that fails without it,
  is open as [catalystneuro/neuroconv#2141](https://github.com/catalystneuro/neuroconv/pull/2141) ([patch copy](docs/upstream/neuroconv-openephyslegacy-get-metadata-after-remove-channels.patch)).
- **NeuroConv (design question):** a legacy header time like `95534` is reduced to the date,
  even though `settings.xml` holds the full time.
- **NWB Inspector (question):** the CLI exit code doesn't reflect findings.

## Repository layout

```
src/nolan_lab_to_nwb/       converter, custom interfaces, settings.xml reader, metadata.yaml, Inspector gate
scripts/download_data.py    fetch + md5-verify the raw data into data/ (gitignored)
scripts/make_fixture.py     cut record-aligned test windows from the raw files
scripts/mutation_check.py   inject bugs, require the suite to fail
tests/                      pytest suite; fixtures/ holds two 1 MB excerpts of the raw data
docs/                       DANDI sandbox guide, upstream PR text and patch
.github/workflows/ci.yml    tests + Inspector gate + mutation check on Ubuntu and Windows
DEVLOG.md                   every mistake made during development (by me, the agent or a tool), how it was caught, the fix
```

## How this was built

The code was written by an AI coding agent (Claude) under my direction and review, one milestone
at a time. The verification design above exists because agent-written code needs it: checks that
don't trust the converter, tests proven to fail on broken code, and a [DEVLOG](DEVLOG.md) that
records each error, including the agent's own, and how it was caught.

## License

Code: MIT (see [`LICENSE`](LICENSE)). Data: CC BY 4.0, © the original authors. The two test
fixtures are unmodified excerpts of the raw files, redistributed under that license with
attribution ([`tests/fixtures/README.md`](tests/fixtures/README.md)); the full dataset is downloaded
from Zenodo, not stored here.
