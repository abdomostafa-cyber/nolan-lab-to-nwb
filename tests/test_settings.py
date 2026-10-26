"""settings.xml parsing, checked against values read by hand from the session's settings.xml."""

from datetime import datetime

import pytest
from conftest import FIXTURES

from nolan_lab_to_nwb.openephys_settings import read_settings


@pytest.fixture(scope="module")
def settings():
    return read_settings(FIXTURES / "pulse" / "settings.xml")


def test_channel_names_come_from_channel_info(settings):
    # Regression: the processor's direct <CHANNEL> children are named "0", "1", ... (see DEVLOG).
    expected = (
        tuple(f"CH{i}" for i in range(1, 17)) + ("AUX1", "AUX2", "AUX3") + tuple(f"ADC{i}" for i in range(1, 9))
    )
    assert settings.source_channel_names == expected


def test_tetrodes(settings):
    assert settings.tetrodes == {
        "Tetrode 1": ("CH1", "CH2", "CH3", "CH4"),
        "Tetrode 2": ("CH5", "CH6", "CH7", "CH8"),
        "Tetrode 3": ("CH9", "CH10", "CH11", "CH12"),
        "Tetrode 4": ("CH13", "CH14", "CH15", "CH16"),
    }


def test_hardware_filter_and_info(settings):
    assert settings.gui_version == "0.4.2.1"
    assert settings.settings_date == datetime(2023, 4, 21, 9, 55, 34)
    assert settings.source_processor_id == "100"
    assert settings.hardware_filter.low_cut_hz == pytest.approx(1.9615616675223595)
    assert settings.hardware_filter.high_cut_hz == pytest.approx(7603.7651218333704)
    assert settings.hardware_filter.dsp_offset_removal is True
    assert settings.hardware_filter.dsp_cutoff_hz == pytest.approx(0.14571292570770725)


def test_channel_map_is_composed_not_assumed(tmp_path, settings):
    """A Channel Map that swaps two outputs must move channels between tetrodes."""
    text = (FIXTURES / "pulse" / "settings.xml").read_text(encoding="latin-1")
    swapped = text.replace('<CHANNEL Number="0" Mapping="1"', '<CHANNEL Number="0" Mapping="5"').replace(
        '<CHANNEL Number="4" Mapping="5"', '<CHANNEL Number="4" Mapping="1"'
    )
    assert swapped != text
    path = tmp_path / "settings.xml"
    path.write_text(swapped, encoding="latin-1")
    tetrodes = read_settings(path).tetrodes
    assert tetrodes["Tetrode 1"] == ("CH5", "CH2", "CH3", "CH4")
    assert tetrodes["Tetrode 2"] == ("CH1", "CH6", "CH7", "CH8")
