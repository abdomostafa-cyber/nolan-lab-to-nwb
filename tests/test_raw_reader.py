"""The independent reader is the reference for every round-trip test, so it is tested on its own."""

import numpy as np
import pytest
from conftest import FIXTURES
from raw_openephys import HEADER_BYTES, RECORD_DTYPE, read_continuous, read_events


def test_header_and_shape():
    c = read_continuous(FIXTURES / "pulse" / "100_CH1.continuous")
    assert c.sampling_rate == 30000.0
    assert c.bit_volts == pytest.approx(0.195)
    assert c.samples.dtype == np.int16
    assert c.samples.size == 16 * 1024
    # The pulse fixture starts at record 185 of a session whose counter started at 107400.
    assert c.first_timestamp == 107400 + 185 * 1024


def test_big_endian_samples_are_decoded():
    """Decode the first samples by hand from the byte layout (offset 8+2+2 into the record, big-endian)."""
    path = FIXTURES / "pulse" / "100_CH1.continuous"
    record = path.read_bytes()[HEADER_BYTES : HEADER_BYTES + RECORD_DTYPE.itemsize]
    by_hand = [int.from_bytes(record[12 + 2 * i : 14 + 2 * i], "big", signed=True) for i in range(5)]
    assert read_continuous(path).samples[:5].tolist() == by_hand


def test_rejects_truncated_file(tmp_path):
    source = FIXTURES / "pulse" / "100_CH1.continuous"
    broken = tmp_path / "100_CH1.continuous"
    broken.write_bytes(source.read_bytes()[:-100])
    with pytest.raises(ValueError, match="whole number"):
        read_continuous(broken)


def test_events_are_recording_start_markers_not_ttls():
    _, events = read_events(FIXTURES / "pulse" / "all_channels.events")
    assert len(events) == 2
    assert set(events["event_type"]) == {5}  # 5 = network/message event; TTL would be 3
    assert set(events["timestamp"]) == {107400}
