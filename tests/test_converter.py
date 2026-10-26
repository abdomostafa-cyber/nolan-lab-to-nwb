"""Converter behaviour that the round-trip tests do not reach directly."""

from __future__ import annotations

import warnings

import pytest
from conftest import FIXTURES
from pynwb import NWBHDF5IO

from nolan_lab_to_nwb.converter import build_metadata, make_converter


@pytest.fixture
def converter():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="The timestamp for starting time from openephys metadata")
        return make_converter(FIXTURES / "end")


def test_padding_and_offset_detected(converter):
    assert converter.padding_samples == 992
    assert converter.recording_offset_s == pytest.approx((107400 + 65017 * 1024) / 30000)


def test_run_conversion_twice_is_idempotent(converter, tmp_path):
    """NeuroConv calls temporally_align_data_interfaces on every run; trim and shift must not stack."""
    metadata = build_metadata(converter)
    for name in ("first.nwb", "second.nwb"):
        converter.run_conversion(nwbfile_path=tmp_path / name, metadata=metadata, overwrite=True)
    for name in ("first.nwb", "second.nwb"):
        with NWBHDF5IO(tmp_path / name, "r") as io:
            series = io.read().acquisition["ElectricalSeries"]
            assert series.data.shape == (16 * 1024 - 992, 16)
            assert series.starting_time == 0.0


def test_yaml_overrides_neuroconv_date_only_start_time(converter):
    metadata = build_metadata(converter)
    assert str(metadata["NWBFile"]["session_start_time"]) in ("2023-04-21T09:55:34+01:00", "2023-04-21 09:55:34+01:00")
