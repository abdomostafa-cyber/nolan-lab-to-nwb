# Draft issue for catalystneuro/neuroconv (NOT POSTED, for review)

> **Status:** draft, not posted. Verified 2026-10-27 against `main` at `2a46c7e` (0.11.0.dev0) and the
> 0.10.2 release. Fix and tests: `neuroconv-get-metadata-after-remove-channels.patch` (same folder).
> Fields follow the repo's bug-report template. **Rewrite in your own words before posting**, and
> search the issues again first: `main` moves daily.

---

**Title:** `[Bug]: get_metadata() / run_conversion() raise AttributeError after remove_channels() (Axon, OpenEphysLegacy)`

### What happened?

After `interface.remove_channels(...)`, `get_metadata()` raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`. `run_conversion()`
without explicit metadata fails the same way, since it calls `get_metadata()`.

`remove_channels` replaces `interface.recording_extractor` with a `ChannelSliceRecording`, but
`AxonRecordingInterface.get_metadata` and `OpenEphysLegacyRecordingInterface.get_metadata` read
`self.recording_extractor.neo_reader`, which only the original extractor has.

This affects the `remove_channels` + `ConverterPipe` workflow suggested in #2137 for mixed ABF
files, and the `remove_channels` advice in the heterogeneous-offsets error message.

### Steps to Reproduce

With files from `ephy_testing_data`:

```python
from neuroconv.datainterfaces import AxonRecordingInterface

interface = AxonRecordingInterface(
    file_path=".../axon/extracellular_data/four_electrodes/24606005_SampleData.abf"
)
interface.remove_channels(channel_ids=[interface.channel_ids[-1]])  # 3 of 4 channels kept
interface.get_metadata()  # AttributeError
```

The same happens with `OpenEphysLegacyRecordingInterface(folder_path=".../openephys/OpenEphys_SampleData_1")`.

Workaround: call `get_metadata()` before `remove_channels()` and pass the result to `run_conversion(metadata=...)`.

### Traceback

```
  File ".../neuroconv/datainterfaces/ecephys/axon/axondatainterface.py", line 105, in get_metadata
    neo_reader = self.recording_extractor.neo_reader
AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'
```

(OpenEphysLegacy: same error at `openephyslegacydatainterface.py`, line 137.)

### Possible fix

The base class keeps the original extractor as `self._extractor_instance`, so reading from it is
enough:

```diff
-        neo_reader = self.recording_extractor.neo_reader
+        neo_reader = self._extractor_instance.neo_reader
```

I have this as a small PR, with a regression test for each of the two interfaces, if you'd like it.
Checked locally:

- each new test fails without the change and passes with it;
- selected tests (`-k "Axon and not Axona or OpenEphysLegacy"` plus `test_openephyslegacy.py`)
  go from 29 passed / 15 skipped to 31 passed / 15 skipped, with the same skips before and after.

**Not tested:** the same `self.recording_extractor.neo_reader` read appears in `get_metadata`, or in
helpers it calls, in the AlphaOmega, Axona, MaxOne, MEArec, Neuralynx and Plexon interfaces. I don't
have their test data set up, so I can't confirm them. Glad to include them if you want the same
change applied there.

### Operating System
Windows 11

### Python Version
3.11.7

### Package Versions
neuroconv `main` (2a46c7e) and 0.10.2 · spikeinterface 0.105.3 · neo 0.14.5 (main env) / 0.14.6

---

## Not filed: the other two rough edges

These stay in this project's DEVLOG and README; neither is a clear bug.

1. **NeuroConv: legacy start time cut to the date.** `'95534'` (09:55:34) triggers the "ambiguous"
   warning and only the date is kept. This is deliberate, and covered by
   `test_openephyslegacy_date_parse`. A possible suggestion would be to fall back to `settings.xml`
   `<INFO><DATE>`. That would first need checking against how Open Ephys GUI 0.4 formats `date_created`.
2. **NWB Inspector: the CLI exits 0 even with CRITICAL findings.** That may be intended. At most this
   is a question about whether a fail-threshold option would be welcome.
