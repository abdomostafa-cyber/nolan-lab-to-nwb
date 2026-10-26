"""Independent reader for legacy Open Ephys files, written from the format description only.

It deliberately does not import neo, SpikeInterface or NeuroConv, so the round-trip tests compare
the NWB file against the raw bytes rather than against the converter's own reading of them.
Format reference: https://open-ephys.github.io/gui-docs/User-Manual/Recording-data/Open-Ephys-format.html
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HEADER_BYTES = 1024
SAMPLES_PER_RECORD = 1024
RECORD_DTYPE = np.dtype(
    [
        ("timestamp", "<i8"),
        ("n_samples", "<u2"),
        ("recording_number", "<u2"),
        ("samples", ">i2", SAMPLES_PER_RECORD),  # big-endian, unlike the rest of the record
        ("marker", "u1", 10),
    ]
)
RECORD_MARKER = np.arange(10, dtype="u1")
RECORD_MARKER[-1] = 255


def parse_header(raw: bytes) -> dict[str, str]:
    text = raw.decode("latin-1")
    return {key: value.strip().strip("'") for key, value in re.findall(r"header\.(\w+) = (.*?);", text)}


@dataclass
class ContinuousFile:
    header: dict[str, str]
    first_timestamp: int  # sample counter of the first sample
    samples: np.ndarray  # int16, native byte order

    @property
    def sampling_rate(self) -> float:
        return float(self.header["sampleRate"])

    @property
    def bit_volts(self) -> float:
        return float(self.header["bitVolts"])


def read_continuous(path: str | Path) -> ContinuousFile:
    raw = Path(path).read_bytes()
    header = parse_header(raw[:HEADER_BYTES])
    body = raw[HEADER_BYTES:]
    if len(body) % RECORD_DTYPE.itemsize:
        raise ValueError(f"{path}: body is not a whole number of {RECORD_DTYPE.itemsize}-byte records")
    records = np.frombuffer(body, dtype=RECORD_DTYPE)
    if not (records["n_samples"] == SAMPLES_PER_RECORD).all():
        raise ValueError(f"{path}: record with a sample count other than {SAMPLES_PER_RECORD}")
    if not (records["marker"] == RECORD_MARKER).all():
        raise ValueError(f"{path}: corrupt record marker")
    if not (np.diff(records["timestamp"]) == SAMPLES_PER_RECORD).all():
        raise ValueError(f"{path}: gap or jump in record timestamps")
    return ContinuousFile(
        header=header,
        first_timestamp=int(records["timestamp"][0]),
        samples=records["samples"].reshape(-1).astype("<i2"),
    )


EVENT_DTYPE = np.dtype(
    [
        ("timestamp", "<i8"),
        ("sample_position", "<i2"),
        ("event_type", "u1"),
        ("processor_id", "u1"),
        ("event_id", "u1"),
        ("event_channel", "u1"),
        ("recording_number", "<u2"),
    ]
)


def read_events(path: str | Path) -> tuple[dict[str, str], np.ndarray]:
    raw = Path(path).read_bytes()
    return parse_header(raw[:HEADER_BYTES]), np.frombuffer(raw[HEADER_BYTES:], dtype=EVENT_DTYPE)
