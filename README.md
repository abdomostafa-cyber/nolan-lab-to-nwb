# nwb-conversion-demo

Converting a real lab recording to [NWB](https://www.nwb.org/) with
[NeuroConv](https://github.com/catalystneuro/neuroconv), validating it with
[NWB Inspector](https://github.com/NeurodataWithoutBorders/nwbinspector), and checking
the result against the raw files independently of the converter.

> Status: work in progress. Conversion works end to end; tests and CI are next.

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
uv run python -m nwb_conversion_demo.convert \
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
| `general/subject`, devices, session info | `src/nwb_conversion_demo/metadata.yaml` | values the files do not contain, each sourced or marked unknown |

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

## Repository layout

```
src/nwb_conversion_demo/   conversion package (CLI: python -m nwb_conversion_demo.convert)
scripts/download_data.py   fetches and md5-verifies the raw data into data/ (gitignored)
tests/                     pytest suite, runs on a trimmed fixture in CI
DEVLOG.md                  what went wrong during development, how it was caught, how it was fixed
```

## License

Code: MIT (see `LICENSE`). Data: CC BY 4.0, owned by its authors and not redistributed here.
