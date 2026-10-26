"""Checks on the full converted session. Skipped unless the raw data and the NWB file exist locally.

    uv run python scripts/download_data.py
    uv run python -m nolan_lab_to_nwb.convert --data-dir data/raw/1544_2023-04-21_09-55-34_of \
        --output data/nwb/sub-1544_ses-1544-2023-04-21-09-55-34-of_ecephys.nwb
    uv run pytest -m full
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import FULL_SESSION
from pynwb import NWBHDF5IO
from raw_openephys import read_continuous

NWB_PATH = FULL_SESSION.parents[1] / "nwb" / "sub-1544_ses-1544-2023-04-21-09-55-34-of_ecephys.nwb"
N_VALID = 66_592_800  # 65,033 records x 1024 samples - 992 padding samples
SERIES = {"ElectricalSeries": "CH", "TimeSeriesAnalogInput": "ADC", "TimeSeriesAuxiliaryInput": "AUX"}

pytestmark = [
    pytest.mark.full,
    pytest.mark.skipif(not (FULL_SESSION.exists() and NWB_PATH.exists()), reason="full session not available"),
]


@pytest.fixture(scope="module")
def nwbfile():
    with NWBHDF5IO(NWB_PATH, "r") as io:
        yield io.read()


@pytest.mark.parametrize("series_name, prefix", SERIES.items())
def test_every_channel_identical_to_raw(nwbfile, series_name, prefix):
    series = nwbfile.acquisition[series_name]
    assert series.data.shape[0] == N_VALID
    for column in range(series.data.shape[1]):
        raw = read_continuous(FULL_SESSION / f"100_{prefix}{column + 1}.continuous")
        np.testing.assert_array_equal(series.data[:, column], raw.samples[:N_VALID])


def test_duration_and_pulses(nwbfile):
    series = nwbfile.acquisition["ElectricalSeries"]
    assert series.data.shape[0] / series.rate == pytest.approx(2219.76)
    pulses = nwbfile.intervals["SyncPulses"].to_dataframe()
    assert len(pulses) == 56
    assert pulses["start_time"].iloc[0] == pytest.approx(6.4777, abs=1e-4)
    widths = pulses["stop_time"] - pulses["start_time"]
    assert widths.between(0.1500, 0.1502).all()
