# Draft issue for catalystneuro/neuroconv (NOT POSTED, for review)

> Status: draft, not posted. Verified 2026-10-27 against `main` at
> `2a46c7e3ef34baca4b41494ce86faa550502a2a6` and against the 0.10.2 release.
> The verified fix is in `neuroconv-legacy-get-metadata-after-remove-channels.patch` (same folder).
> Suggested route: post the issue first and offer the PR in it, so the maintainers can pick the scope.

---

**Title:** `[Bug]: OpenEphysLegacyRecordingInterface.get_metadata() raises AttributeError after remove_channels()`

### What happened?

After `interface.remove_channels(...)`, `get_metadata()` fails, and so does `run_conversion()`
called without explicit metadata, because it builds its metadata via `get_metadata()`.

`remove_channels` replaces `interface.recording_extractor` with a `ChannelSliceRecording`.
`OpenEphysLegacyRecordingInterface.get_metadata` reads `self.recording_extractor.neo_reader`
to get the session start time, and the slice has no `neo_reader`.

`remove_channels` is also what the heterogeneous-offsets error message in
`BaseRecordingExtractorInterface.add_to_nwbfile` recommends ("drop them with
`interface.remove_channels(channel_ids=[...])`"). So following that advice on a legacy Open Ephys
session leads straight into this error.

### Steps to reproduce

Using the test data in `ephy_testing_data/openephys/OpenEphys_SampleData_1`:

```python
from neuroconv.datainterfaces import OpenEphysLegacyRecordingInterface

interface = OpenEphysLegacyRecordingInterface(folder_path=".../openephys/OpenEphys_SampleData_1")
interface.get_metadata()                                          # works
interface.remove_channels(channel_ids=[interface.channel_ids[-1]])
interface.get_metadata()                                          # AttributeError
```

### Traceback

```
  File ".../neuroconv/datainterfaces/ecephys/openephys/openephyslegacydatainterface.py", line 137, in get_metadata
    neo_reader = self.recording_extractor.neo_reader
AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'
```

### Workaround

Call `get_metadata()` before `remove_channels()` and pass the result to `run_conversion(metadata=...)`.

### Proposed fix

Read the reader from `self._extractor_instance`, the extractor as constructed, which the base class
already keeps:

```diff
-        neo_reader = self.recording_extractor.neo_reader
+        neo_reader = self._extractor_instance.neo_reader
```

with a regression test in `tests/test_on_data/ecephys/test_openephyslegacy.py`:

```python
def test_openephyslegacy_get_metadata_after_remove_channels(self):
    expected_metadata = self.interface.get_metadata()
    self.interface.remove_channels(channel_ids=[self.interface.channel_ids[-1]])
    metadata = self.interface.get_metadata()
    assert metadata["NWBFile"]["session_start_time"] == expected_metadata["NWBFile"]["session_start_time"]
```

Checked locally (Windows 11, Python 3.11.7, spikeinterface 0.105.3, neo 0.14.5):

- the new test fails without the fix and passes with it;
- `pytest tests/test_on_data/ecephys/test_openephyslegacy.py tests/test_on_data/ecephys/test_recording_interfaces.py -k "OpenEphysLegacy or openephyslegacy"`
  gives 18 passed, 1 skipped (the skip is the Zarr backend test, which needs zarr 3 and isn't
  related to this change).

### Same pattern elsewhere (not tested)

`self.recording_extractor.neo_reader` is also read inside `get_metadata`, or in a helper that
`get_metadata` calls, in the AlphaOmega, Axon, Axona (`extract_nwb_file_metadata`), MaxOne, MEArec,
Neuralynx (`_extract_header_metadata`) and Plexon interfaces. The EDF, Spike2 and SpikeGLX accesses
are in `__init__`, before anything can wrap the extractor, so they look unaffected.
I haven't run those, since I don't have their test data set up, so I'm only flagging the pattern.
Happy to extend the PR to them if you'd like the same change there.

### Versions

neuroconv `main` (2a46c7e, 0.11.0.dev0) and 0.10.2 · spikeinterface 0.105.3 · neo 0.14.5 / 0.14.6 ·
Python 3.11.7 · Windows 11

---

## Not filed: notes on the other two rough edges

These stay in this project's DEVLOG and README. Neither is a clear bug.

1. **NeuroConv: legacy start time reduced to the date.** `'95534'` (09:55:34) triggers the
   "ambiguous" warning and only the date is kept. The behaviour is deliberate (it's covered by
   `test_openephyslegacy_date_parse`). The warning is also reasonable if the GUI could write
   unpadded minutes too. A possible suggestion would be to fall back to `settings.xml` `<INFO><DATE>`,
   which NeuroConv already parses for the binary format. To argue that well, someone would first
   need to confirm how Open Ephys GUI 0.4 formats `date_created`.
2. **NWB Inspector: CLI exits 0 even with CRITICAL findings.** `_nwbinspector_cli` has no exit-code
   handling. This may be intended (a report tool, not a gate). At most it's worth asking whether a
   fail-threshold option would be welcome. This project gates CI with its own wrapper instead.
