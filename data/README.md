# data/

Everything in this folder except this README is gitignored.

```bash
uv run python scripts/download_data.py            # full session (~2.2 GB zip, ~4 GB unzipped)
uv run python scripts/download_data.py --metadata-only   # settings.xml + event files only (~50 kB)
```

Layout after download:

```
data/
  raw/1544_2023-04-21_09-55-34_of/   # Open Ephys legacy session (CH*, AUX*, ADC* .continuous, settings.xml, *.events)
  downloads/                          # the original zip (delete after extraction if you need the space)
```

Source: Buccino & Halcrow, *SpikeInterface Training Dataset* v2, Zenodo,
<https://doi.org/10.5281/zenodo.20726062>, CC BY 4.0. Session recorded by
Brianna Vandrey, Nolan Lab, University of Edinburgh.
