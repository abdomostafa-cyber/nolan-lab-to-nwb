"""Custom NeuroConv DataInterfaces for what the stock Open Ephys legacy interface does not cover."""

from __future__ import annotations

import numpy as np
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface
from neuroconv.datainterfaces.ecephys.baserecordingastimeseriesinterface import (
    BaseRecordingAsTimeSeriesInterface,
)
from neuroconv.utils import DeepDict
from pydantic import DirectoryPath, validate_call
from pynwb import NWBFile


def _read_legacy_stream(folder_path, stream_name: str):
    from spikeinterface.extractors.extractor_classes import (
        OpenEphysLegacyRecordingExtractor,
    )

    return OpenEphysLegacyRecordingExtractor(folder_path=folder_path, stream_name=stream_name)


def channel_names(recording) -> list[str]:
    """Open Ephys channel names (CH1, ADC1, ...). The legacy extractor's channel *ids* drop the prefix
    ('1', '2', ...), so they repeat across streams and cannot identify a channel on their own."""
    return [str(name) for name in recording.get_property("channel_name")]


class SliceSafeOpenEphysLegacyRecordingInterface(OpenEphysLegacyRecordingInterface):
    """``OpenEphysLegacyRecordingInterface`` whose ``get_metadata`` survives a sliced recording.

    NeuroConv 0.10.2 reads ``self.recording_extractor.neo_reader`` in ``get_metadata``. Any wrapper
    (``frame_slice``, or NeuroConv's own ``remove_channels``) drops that attribute and the call raises
    AttributeError. The base class keeps the unwrapped extractor as ``_extractor_instance``; metadata
    is read from it. Local backport of the fix proposed upstream (see DEVLOG).
    """

    def get_metadata(self, **kwargs) -> DeepDict:
        wrapped = self.recording_extractor
        self.recording_extractor = self._extractor_instance
        try:
            return super().get_metadata(**kwargs)
        finally:
            self.recording_extractor = wrapped


class OpenEphysLegacyAnalogInterface(BaseRecordingAsTimeSeriesInterface):
    """Write one non-electrode stream of a legacy Open Ephys session (AUX or ADC) as a TimeSeries.

    NeuroConv 0.10.2 has ``OpenEphysBinaryAnalogInterface`` for the binary format but no equivalent for
    the legacy ``.continuous`` format, where neo exposes AUX and ADC as their own streams. Writing them
    through ``OpenEphysLegacyRecordingInterface`` would add them to the electrodes table as if they
    were electrodes.

    The data are stored as the raw int16 samples with ``conversion`` set to the per-bit scaling from
    the file headers (``bitVolts``), so ``data * conversion`` is in volts.
    """

    display_name = "OpenEphys Legacy Analog Recording"
    keywords = ("OpenEphys", "analog", "ADC", "AUX")
    associated_suffixes = (".continuous",)
    info = "Interface for the AUX or ADC channels of a legacy Open Ephys (.continuous) session."

    @validate_call
    def __init__(
        self,
        folder_path: DirectoryPath,
        *,
        stream_name: str,
        metadata_key: str,
        time_series_name: str,
        description: str,
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        folder_path : DirectoryPath
            Open Ephys legacy session folder (contains the .continuous files and settings.xml).
        stream_name : str
            neo stream name, "Signals AUX" or "Signals ADC".
        metadata_key : str
            Key of this series' entry in ``metadata["TimeSeries"]``.
        time_series_name : str
            Name of the TimeSeries in the NWB file.
        description : str
            Description of the TimeSeries.
        """
        self.recording_extractor = _read_legacy_stream(folder_path, stream_name)
        self.metadata_key = metadata_key
        self.time_series_name = time_series_name
        self.description = description
        super().__init__(
            folder_path=folder_path,
            stream_name=stream_name,
            metadata_key=metadata_key,
            time_series_name=time_series_name,
            description=description,
            verbose=verbose,
        )

    def get_conversion_to_volts(self) -> float:
        """Volts per bit, from the .continuous headers (identical for every channel of the stream)."""
        gains_uv = np.unique(self.recording_extractor.get_channel_gains())
        offsets = np.unique(self.recording_extractor.get_channel_offsets())
        if len(gains_uv) != 1 or offsets.tolist() != [0.0]:
            raise ValueError(f"Expected one gain and zero offset per stream, got gains={gains_uv}, offsets={offsets}")
        return float(gains_uv[0]) * 1e-6  # SpikeInterface reports gains in microvolts per bit

    def get_channel_names(self) -> list[str]:
        return channel_names(self.recording_extractor)

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        channels = ", ".join(self.get_channel_names())
        metadata["TimeSeries"][self.metadata_key] = dict(
            name=self.time_series_name,
            description=f"{self.description} Columns are channels {channels}, in that order.",
            # Passing ``unit`` makes NeuroConv skip its own scaling, so ``conversion`` must be passed too.
            unit="volts",
            conversion=self.get_conversion_to_volts(),
            offset=0.0,
        )
        return metadata


class SyncPulseInterface(BaseDataInterface):
    """Detect TTL-like pulses on one analog input and write their on/off times as a TimeIntervals table.

    Each pulse becomes one row (``start_time`` = rising edge, ``stop_time`` = falling edge). Edges are
    the first sample at or above / below ``threshold_volts``; the raw trace stays in the analog
    TimeSeries, so the detection can be redone from the NWB file alone.
    """

    display_name = "Sync pulses from an analog input"
    keywords = ("TTL", "sync", "events")

    @validate_call
    def __init__(
        self,
        folder_path: DirectoryPath,
        *,
        stream_name: str,
        channel_id: str,
        threshold_volts: float,
        table_name: str,
        description: str,
        verbose: bool = False,
    ):
        recording = _read_legacy_stream(folder_path, stream_name)
        names = channel_names(recording)
        if channel_id not in names:
            raise ValueError(f"No channel named {channel_id!r} in stream {stream_name!r} (channels: {names})")
        selected_id = recording.get_channel_ids()[names.index(channel_id)]
        self.recording_extractor = recording.select_channels(channel_ids=[selected_id])
        self.channel_id = channel_id
        self.threshold_volts = threshold_volts
        self.table_name = table_name
        self.description = description
        super().__init__(
            folder_path=folder_path,
            stream_name=stream_name,
            channel_id=channel_id,
            threshold_volts=threshold_volts,
            table_name=table_name,
            description=description,
            verbose=verbose,
        )

    def detect_edges(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (rising, falling) edge times in seconds, on the recording's (aligned) clock."""
        trace = self.recording_extractor.get_traces(return_in_uV=True)[:, 0] * 1e-6
        high = trace >= self.threshold_volts
        rising = np.flatnonzero(~high[:-1] & high[1:]) + 1
        falling = np.flatnonzero(high[:-1] & ~high[1:]) + 1
        # Keep only complete pulses: drop a falling edge before the first rise and a rise without a fall.
        if falling.size and rising.size and falling[0] < rising[0]:
            falling = falling[1:]
        rising = rising[: falling.size]
        times = self.recording_extractor.sample_index_to_time
        return np.asarray(times(rising)), np.asarray(times(falling))

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict | None = None, *, stub_test: bool = False) -> None:
        rising, falling = self.detect_edges()
        table = nwbfile.create_time_intervals(
            name=self.table_name,
            description=(
                f"{self.description} Detected on {self.channel_id} with a {self.threshold_volts} V threshold "
                "(first sample at/above for start_time, first sample below for stop_time)."
            ),
        )
        for start, stop in zip(rising, falling):
            table.add_interval(start_time=float(start), stop_time=float(stop))

    def get_timestamps(self) -> np.ndarray:
        return self.recording_extractor.get_times()
