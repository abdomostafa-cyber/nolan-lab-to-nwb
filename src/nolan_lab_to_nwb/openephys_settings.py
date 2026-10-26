"""Read the parts of an Open Ephys GUI 0.4.x ``settings.xml`` that the conversion needs.

NeuroConv's legacy interface takes channel names, gains and the sampling rate from the
``.continuous`` headers, but it does not read the signal chain. The signal chain is the only
record of which channels form a tetrode and of the acquisition board's hardware filter.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HardwareFilter:
    """Rhythm FPGA (Intan RHD2000) on-chip filter settings, in Hz."""

    low_cut_hz: float
    high_cut_hz: float
    dsp_offset_removal: bool
    dsp_cutoff_hz: float


@dataclass(frozen=True)
class SessionSettings:
    gui_version: str
    settings_date: datetime  # local wall-clock time, no timezone (settings.xml stores none)
    source_processor_id: str
    source_channel_names: tuple[str, ...]  # in source order: CH1..CH16, AUX1..3, ADC1..8
    hardware_filter: HardwareFilter
    tetrodes: dict[str, tuple[str, ...]]  # e.g. {"Tetrode 1": ("CH1", "CH2", "CH3", "CH4"), ...}


def _find_processor(root: ET.Element, plugin_name: str) -> ET.Element | None:
    for processor in root.iter("PROCESSOR"):
        if processor.get("pluginName") == plugin_name:
            return processor
    return None


def read_settings(settings_path: str | Path) -> SessionSettings:
    root = ET.parse(settings_path).getroot()

    source = _find_processor(root, "Rhythm FPGA")
    if source is None:
        raise ValueError(f"No Rhythm FPGA source processor in {settings_path}")
    # The processor's direct <CHANNEL> children only hold selection state and are named "0", "1", ...;
    # the channel names (CH1, AUX1, ADC1, ...) live under <CHANNEL_INFO>.
    channel_info = source.find("CHANNEL_INFO").findall("CHANNEL")
    source_channel_names = tuple(
        channel.get("name") for channel in sorted(channel_info, key=lambda c: int(c.get("number")))
    )
    editor = source.find("EDITOR")
    hardware_filter = HardwareFilter(
        low_cut_hz=float(editor.get("LowCut")),
        high_cut_hz=float(editor.get("HighCut")),
        dsp_offset_removal=editor.get("DSPOffset") == "1",
        dsp_cutoff_hz=float(editor.get("DSPCutoffFreq")),
    )

    # Channel Map: output channel ``Number`` (0-based) takes source channel ``Mapping`` (1-based).
    channel_map = _find_processor(root, "Channel Map")
    output_to_source = {}
    if channel_map is not None:
        for channel in channel_map.find("EDITOR").findall("CHANNEL"):
            output_to_source[int(channel.get("Number"))] = int(channel.get("Mapping")) - 1

    # Spike Detector electrodes refer to channels by their index after the Channel Map.
    tetrodes = {}
    spike_detector = _find_processor(root, "Spike Detector")
    if spike_detector is not None:
        for electrode in spike_detector.iter("ELECTRODE"):
            subchannels = [int(sub.get("ch")) for sub in electrode.findall("SUBCHANNEL")]
            source_indices = [output_to_source.get(ch, ch) for ch in subchannels]
            tetrodes[electrode.get("name")] = tuple(source_channel_names[i] for i in source_indices)

    return SessionSettings(
        gui_version=root.findtext("./INFO/VERSION"),
        settings_date=datetime.strptime(root.findtext("./INFO/DATE"), "%d %b %Y %H:%M:%S"),
        source_processor_id=source.get("NodeId"),
        source_channel_names=source_channel_names,
        hardware_filter=hardware_filter,
        tetrodes=tetrodes,
    )
