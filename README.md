# nwb-conversion-demo

Converting a real lab recording to [NWB](https://www.nwb.org/) with
[NeuroConv](https://github.com/catalystneuro/neuroconv), validating it with
[NWB Inspector](https://github.com/NeurodataWithoutBorders/nwbinspector), and checking
the result against the raw files independently of the converter.

> Status: work in progress. Scaffold only; the conversion is not implemented yet.

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

## Repository layout

```
src/nwb_conversion_demo/   conversion package (CLI: python -m nwb_conversion_demo.convert)
scripts/download_data.py   fetches and md5-verifies the raw data into data/ (gitignored)
tests/                     pytest suite, runs on a trimmed fixture in CI
DEVLOG.md                  what went wrong during development, how it was caught, how it was fixed
```

## License

Code: MIT (see `LICENSE`). Data: CC BY 4.0, owned by its authors and not redistributed here.
