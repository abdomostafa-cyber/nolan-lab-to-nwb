# PR description for catalystneuro/neuroconv (for review, edit before use)

> **Branch:** `fix/openephyslegacy-get-metadata-after-remove-channels`, one commit (`c85dad1`) on top of
> `main` at `2c85f65`. Push it to your fork (`abdomostafa-cyber/neuroconv`), then open the PR against
> `catalystneuro/neuroconv:main`.
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit. The file name has to be the PR number, which doesn't exist until the PR does.
> This supersedes `neuroconv-issue-draft.md`: a ready PR is less work for the maintainers than an
> issue asking whether they want one.

---

**Title:** Keep `OpenEphysLegacyRecordingInterface.get_metadata` working after `remove_channels`

**Body:**

#2140 fixed this for `AxonRecordingInterface`. `OpenEphysLegacyRecordingInterface` has the same
problem on `main`: after `remove_channels`, `get_metadata` raises
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`, because it reads the
session start time through `recording_extractor.neo_reader`. `run_conversion` without explicit
metadata fails the same way.

```python
interface = OpenEphysLegacyRecordingInterface(folder_path=OPENEPHYS_PATH / "OpenEphys_SampleData_1")
interface.remove_channels(channel_ids=[interface.channel_ids[-1]])
interface.get_metadata()  # AttributeError
```

Same approach as #2140: keep the reader in `__init__`, while the recording is still the neo
extractor. The test mirrors the one in #2140.

Checked locally:
- the new test fails on `main` and passes with the change;
- `test_openephyslegacy.py` and the OpenEphysLegacy tests in `test_recording_interfaces.py` pass,
  including `test_openephyslegacy_date_parse`, which edits the reader's annotations after
  construction;
- pre-commit hooks pass.

The same `recording_extractor.neo_reader` read inside `get_metadata` is still in the AlphaOmega,
Axona, MaxOne, MEArec, Neuralynx and Plexon interfaces. I left them out because I don't have their
test data to check them.

<!-- Optional, your call: "I found this while converting a legacy Open Ephys session, working with an
AI coding assistant; I've checked and can explain each change." -->
