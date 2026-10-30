# PR description for catalystneuro/neuroconv: Plexon (for review, edit before use)

> **Branch:** `fix/plexon-get-metadata-after-remove-channels`, one commit (`d2af67b`) on top of
> `main` at `529e218`. One of the six follow-ups from #2141 (AlphaOmega #2152 merged; Axona #2159 open).
> **Pushed** to the fork on 2026-10-30, ready to open.
> **After opening:** rename `changelog_entries/PRNUMBER.bugfix.md` to `<PR number>.bugfix.md` in a
> second commit.

---

**Title:** Keep the Plexon interfaces' `get_metadata` working after `remove_channels`

**Body:**

Follow-up to #2141, like #2152 and #2159. `PlexonRecordingInterface`, `PlexonLFPInterface` and
`Plexon2RecordingInterface` read `recording_extractor.neo_reader` and `recording_extractor.block_index`
in `get_metadata`, so after `remove_channels` all three raise
`AttributeError: 'ChannelSliceRecording' object has no attribute 'neo_reader'`.

They share the same code, so they are in one PR. Same approach as #2141: keep the reader (and the
block index) in `__init__`, while the recording is still the neo extractor; the rest of `get_metadata`
is unchanged. One test per class, mirroring #2140.

Checked locally (Windows, so the Plexon2 tests run):
- the three new tests fail on `main` and pass with the change;
- the Plexon recording tests go from 38 passed + the 3 new tests failing to 41 passed, with the same
  Zarr skips;
- `run_conversion` after `remove_channels`, without passing metadata, writes 3 of the 4 channels with
  the same start time for each of the three interfaces;
- pre-commit hooks pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
