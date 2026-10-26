"""Round trip: reopen the NWB file with PyNWB and compare it against the raw files.

Expected values come from the independent reader (tests/raw_openephys.py) or are literals read by
hand from settings.xml and the Zenodo record, never from NeuroConv, neo or SpikeInterface.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from pynwb import NWBHDF5IO
from raw_openephys import read_continuous

CH = [f"CH{i}" for i in range(1, 17)]
ADC = [f"ADC{i}" for i in range(1, 9)]
AUX = ["AUX1", "AUX2", "AUX3"]
STREAMS = {"ElectricalSeries": CH, "TimeSeriesAnalogInput": ADC, "TimeSeriesAuxiliaryInput": AUX}
# Zero padding at the end of the final record, located by hand in the full session (DEVLOG, Milestone 3).
PADDING = {"pulse": 0, "end": 992}
SYNC_THRESHOLD_V = 2.5


@pytest.fixture
def nwb(converted_fixture):
    folder, path = converted_fixture
    with NWBHDF5IO(path, "r") as io:
        yield folder, io.read()


def raw_stream(folder, names):
    return [read_continuous(folder / f"100_{name}.continuous") for name in names]


def n_valid(folder, raws):
    return raws[0].samples.size - PADDING[folder.name]


@pytest.mark.parametrize("series_name", STREAMS)
def test_samples_identical_to_raw(nwb, series_name):
    folder, nwbfile = nwb
    raws = raw_stream(folder, STREAMS[series_name])
    expected = np.stack([r.samples[: n_valid(folder, raws)] for r in raws], axis=1)
    data = nwbfile.acquisition[series_name].data[:]
    assert data.dtype == np.int16
    assert data.shape == expected.shape
    np.testing.assert_array_equal(data, expected)


def test_padding_boundary(nwb):
    """Trimmed samples are zero on all 27 channels, and the last kept sample is not (the cut is exact)."""
    folder, _ = nwb
    raws = [r for names in STREAMS.values() for r in raw_stream(folder, names)]
    n = n_valid(folder, raws)
    assert not any(r.samples[n:].any() for r in raws)
    assert any(r.samples[n - 1] != 0 for r in raws)


@pytest.mark.parametrize("series_name, volts_per_header_unit", [
    ("ElectricalSeries", 1e-6),  # CH bitVolts is in microvolts
    ("TimeSeriesAnalogInput", 1.0),  # ADC and AUX bitVolts are in volts
    ("TimeSeriesAuxiliaryInput", 1.0),
])
def test_scaling_matches_header_bitvolts(nwb, series_name, volts_per_header_unit):
    folder, nwbfile = nwb
    series = nwbfile.acquisition[series_name]
    raws = raw_stream(folder, STREAMS[series_name])
    assert {r.bit_volts for r in raws} == {raws[0].bit_volts}
    assert series.unit == "volts"
    assert series.conversion == pytest.approx(raws[0].bit_volts * volts_per_header_unit, rel=1e-7)
    assert series.offset == 0.0
    assert getattr(series, "channel_conversion", None) is None


def test_physical_values_spot_check(nwb):
    """One sample worked through by hand: NWB volts == raw int16 * bitVolts (µV) * 1e-6."""
    folder, nwbfile = nwb
    raw = read_continuous(folder / "100_CH7.continuous")
    series = nwbfile.acquisition["ElectricalSeries"]
    index = 1234
    nwb_volts = series.data[index, 6] * series.conversion + series.offset
    assert nwb_volts == pytest.approx(raw.samples[index] * raw.bit_volts * 1e-6, rel=1e-7)


@pytest.mark.parametrize("series_name", STREAMS)
def test_timing(nwb, series_name):
    folder, nwbfile = nwb
    series = nwbfile.acquisition[series_name]
    raw = read_continuous(folder / f"100_{STREAMS[series_name][0]}.continuous")
    assert series.rate == raw.sampling_rate == 30000.0
    assert series.starting_time == 0.0  # t = 0 is the first recorded sample
    assert series.timestamps is None


def test_session_start_time(nwb):
    _, nwbfile = nwb
    assert nwbfile.session_start_time == datetime(2023, 4, 21, 9, 55, 34, tzinfo=timezone(timedelta(hours=1)))


def test_electrodes_table(nwb):
    _, nwbfile = nwb
    electrodes = nwbfile.electrodes.to_dataframe()
    assert electrodes["channel_name"].tolist() == CH
    assert electrodes["group_name"].tolist() == [f"Tetrode{(i - 1) // 4 + 1}" for i in range(1, 17)]
    assert set(electrodes["location"]) == {"Entorhinal area"}
    assert sorted(nwbfile.electrode_groups) == ["Tetrode1", "Tetrode2", "Tetrode3", "Tetrode4"]
    assert all(group.device.name == "TetrodeDrive" for group in nwbfile.electrode_groups.values())
    # AUX and ADC are not electrodes.
    assert len(electrodes) == 16
    assert nwbfile.acquisition["ElectricalSeries"].electrodes.data[:].tolist() == list(range(16))


def test_devices(nwb):
    _, nwbfile = nwb
    assert sorted(nwbfile.devices) == ["OpenEphysAcquisitionBoard", "TetrodeDrive"]


def test_sync_pulses_match_independent_detection(nwb):
    folder, nwbfile = nwb
    raw = read_continuous(folder / "100_ADC1.continuous")
    volts = raw.samples[: raw.samples.size - PADDING[folder.name]] * raw.bit_volts
    high = volts >= SYNC_THRESHOLD_V
    rising = (np.flatnonzero(~high[:-1] & high[1:]) + 1) / raw.sampling_rate
    falling = (np.flatnonzero(high[:-1] & ~high[1:]) + 1) / raw.sampling_rate
    table = nwbfile.intervals["SyncPulses"].to_dataframe()
    assert len(table) == len(rising) == len(falling) == 1  # each fixture window holds one pulse
    np.testing.assert_array_equal(table["start_time"].to_numpy(), rising)
    np.testing.assert_array_equal(table["stop_time"].to_numpy(), falling)
    # Full-session widths are 4502-4503 samples (0.150067-0.150100 s; DEVLOG, Milestone 3).
    assert 0.1500 <= (table["stop_time"] - table["start_time"]).iloc[0] <= 0.1502


def test_subject_and_session_metadata(nwb):
    _, nwbfile = nwb
    assert nwbfile.subject.subject_id == "1544"
    assert nwbfile.subject.species == "Mus musculus"
    assert nwbfile.subject.sex == "U"
    assert nwbfile.session_id == "1544_2023-04-21_09-55-34_of"
    assert nwbfile.lab == "Nolan Lab"
    assert nwbfile.experimenter == ("Vandrey, Brianna",)
