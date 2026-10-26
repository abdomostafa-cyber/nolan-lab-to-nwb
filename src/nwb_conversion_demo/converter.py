"""NWBConverter for the Nolan lab open-field tetrode session.

Timing convention (see README, "Timestamps and alignment"):
    t = 0 in the NWB file is the first recorded sample. The Open Ephys sample counter does not start
    at zero (it counts from when acquisition started, before recording was pressed), and neo reports
    that offset as the stream's t_start. Every stream in this session shares that one counter, so all
    of them are shifted by the same amount.

End-of-recording padding:
    The legacy format writes whole 1024-sample records, and the GUI zero-fills the last one when
    recording stops. Samples that are exactly zero on every channel of every stream at the end of the
    final record are padding, not data, and are trimmed from all streams alike.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from neuroconv import NWBConverter
from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface
from neuroconv.utils import DeepDict, dict_deep_update, load_dict_from_file

from .interfaces import OpenEphysLegacyAnalogInterface, SyncPulseInterface, channel_names
from .openephys_settings import SessionSettings, read_settings

DEFAULT_METADATA_PATH = Path(__file__).parent / "metadata.yaml"
SAMPLES_PER_RECORD = 1024


class NolanOpenFieldNWBConverter(NWBConverter):
    data_interface_classes = dict(
        Recording=OpenEphysLegacyRecordingInterface,
        AuxiliaryInput=OpenEphysLegacyAnalogInterface,
        AnalogInput=OpenEphysLegacyAnalogInterface,
        SyncPulses=SyncPulseInterface,
    )

    def __init__(self, source_data: dict, verbose: bool = False):
        super().__init__(source_data=source_data, verbose=verbose)
        folder_path = Path(source_data["Recording"]["folder_path"])
        self.settings: SessionSettings = read_settings(folder_path / "settings.xml")

        recordings = [interface.recording_extractor for interface in self.data_interface_objects.values()]
        self.recording_offset_s = recordings[0].get_start_time()
        if any(recording.get_start_time() != self.recording_offset_s for recording in recordings):
            raise ValueError("Streams do not share a start time; the single-offset alignment does not apply.")
        if len({recording.get_num_samples() for recording in recordings}) != 1:
            raise ValueError("Streams differ in length; the padding trim assumes one shared length.")

        # The trim itself is applied in temporally_align_data_interfaces, i.e. after metadata is built:
        # OpenEphysLegacyRecordingInterface.get_metadata reads ``recording_extractor.neo_reader``, which
        # a FrameSliceRecording does not have (see DEVLOG).
        self.raw_num_samples = recordings[0].get_num_samples()
        self.padding_samples = self._count_trailing_padding(recordings)

        recording = self.data_interface_objects["Recording"].recording_extractor
        recording.set_property("group_name", self._group_names(channel_names(recording)))

    @staticmethod
    def _count_trailing_padding(recordings) -> int:
        """Trailing samples in the final record that are zero on every channel of every stream."""
        n_samples = recordings[0].get_num_samples()
        last_record = slice(n_samples - SAMPLES_PER_RECORD, n_samples)
        all_zero = np.ones(SAMPLES_PER_RECORD, dtype=bool)
        for recording in recordings:
            traces = recording.get_traces(start_frame=last_record.start, end_frame=last_record.stop)
            all_zero &= (traces == 0).all(axis=1)
        nonzero = np.flatnonzero(~all_zero)
        return SAMPLES_PER_RECORD - (nonzero[-1] + 1 if nonzero.size else 0)

    def _group_names(self, channel_ids: list[str]) -> list[str]:
        channel_to_group = {
            channel: name.replace(" ", "") for name, channels in self.settings.tetrodes.items() for channel in channels
        }
        missing = [channel for channel in channel_ids if channel not in channel_to_group]
        if missing:
            raise ValueError(f"Channels {missing} are not assigned to a tetrode in settings.xml")
        return [channel_to_group[channel] for channel in channel_ids]

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        hardware = self.settings.hardware_filter
        metadata["Ecephys"]["ElectricalSeries"]["open_ephys_recording"]["description"] = (
            "Wideband tetrode signal as recorded from the Rhythm FPGA source (processor "
            f"{self.settings.source_processor_id}), before any software filtering. Intan on-chip "
            f"band-pass {hardware.low_cut_hz:.2f}-{hardware.high_cut_hz:.0f} Hz; DSP offset removal "
            f"{'on' if hardware.dsp_offset_removal else 'off'} (cutoff {hardware.dsp_cutoff_hz:.3f} Hz). "
            f"Time zero is the first recorded sample; the Open Ephys sample counter read "
            f"{self.recording_offset_s:.6f} s at that sample. The final {self.padding_samples} samples "
            "of the source files were zero padding of the last record and are not included."
        )
        return metadata

    def add_to_nwbfile(self, nwbfile, metadata, conversion_options: dict | None = None) -> None:
        # The electrodes table has its own ``location`` column, which NeuroConv fills from the recording's
        # "brain_area" property (default "unknown"), not from the group; copy each group's location over.
        group_location = {group["name"]: group["location"] for group in metadata["Ecephys"]["ElectrodeGroups"].values()}
        recording = self.data_interface_objects["Recording"].recording_extractor
        recording.set_property("brain_area", [group_location[name] for name in recording.get_property("group_name")])

        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)
        # NeuroConv creates a device only when an electrode group points to it; the acquisition board
        # is referenced by none, so it is added here from the same metadata entry.
        board = metadata["Devices"]["acquisition_board"]
        if board["name"] not in nwbfile.devices:
            nwbfile.create_device(**board)

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        # Called by every run_conversion, so both steps are idempotent: the trim only applies to a stream
        # still at its raw length, and the shift targets an absolute start of 0.
        # shift_times moves t_start without materialising a 66.6M-sample time vector.
        for interface in self.data_interface_objects.values():
            recording = interface.recording_extractor
            if self.padding_samples and recording.get_num_samples() == self.raw_num_samples:
                recording = recording.frame_slice(start_frame=0, end_frame=self.raw_num_samples - self.padding_samples)
            recording.shift_times(-recording.get_start_time())
            interface.recording_extractor = recording


def build_metadata(converter: NolanOpenFieldNWBConverter, metadata_path: Path = DEFAULT_METADATA_PATH) -> dict:
    """Merge the YAML on top of what NeuroConv reads from the files; the YAML wins on conflicts."""
    metadata = converter.get_metadata()
    return dict_deep_update(metadata, load_dict_from_file(metadata_path))


def make_converter(folder_path: Path) -> NolanOpenFieldNWBConverter:
    folder_path = str(folder_path)
    source_data = dict(
        Recording=dict(folder_path=folder_path, stream_name="Signals CH"),
        AuxiliaryInput=dict(
            folder_path=folder_path,
            stream_name="Signals AUX",
            metadata_key="auxiliary_input",
            time_series_name="TimeSeriesAuxiliaryInput",
            description=(
                "Intan headstage auxiliary inputs AUX1-3 as stored by the GUI. In this session every "
                "sample is +32767, the int16 maximum (1.2255 V), so no signal is recoverable; on headstages "
                "with an accelerometer these inputs carry its three axes. Kept for completeness."
            ),
        ),
        AnalogInput=dict(
            folder_path=folder_path,
            stream_name="Signals ADC",
            metadata_key="analog_input",
            time_series_name="TimeSeriesAnalogInput",
            description=(
                "Acquisition-board analog inputs ADC1-8. ADC1 carries 150 ms sync pulses (see the "
                "SyncPulses intervals table). What is connected to ADC2-8 is not documented in the dataset."
            ),
        ),
        SyncPulses=dict(
            folder_path=folder_path,
            stream_name="Signals ADC",
            channel_id="ADC1",
            threshold_volts=2.5,
            table_name="SyncPulses",
            description=(
                "Pulses on analog input ADC1 (0 V baseline, about 4.6 V high, 150 ms wide, irregularly "
                "spaced 20-58 s apart). The pattern matches the random sync pulses commonly used to align "
                "a tracking camera to the ephys clock, but the dataset does not document their source, "
                "and no camera or position data are included."
            ),
        ),
    )
    return NolanOpenFieldNWBConverter(source_data=source_data)
