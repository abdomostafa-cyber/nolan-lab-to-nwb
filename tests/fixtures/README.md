# Test fixtures

Two windows of 16 whole records (16 × 1024 samples ≈ 0.55 s) cut from every `.continuous`
file of the real session with `scripts/make_fixture.py`. `settings.xml`, `Continuous_Data.openephys`
and the two `.events` files are copied unchanged.

| folder  | records           | why                                                       |
|---------|-------------------|-----------------------------------------------------------|
| `pulse` | 185–200 (6.31–6.86 s after recording start) | contains the first ADC1 sync pulse (6.4777–6.6278 s) |
| `end`   | last 16           | contains the final record, whose last 992 samples are zero padding |

These are small excerpts of raw data, committed only so that CI can run without downloading 2.2 GB.

Source and licence: Buccino & Halcrow, *SpikeInterface Training Dataset* v2, Zenodo,
<https://doi.org/10.5281/zenodo.20726062>, CC BY 4.0. Session `1544_2023-04-21_09-55-34_of`,
recorded by Brianna Vandrey, Nolan Lab, University of Edinburgh. The excerpts are unmodified
except for the cut.
