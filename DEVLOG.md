# DEVLOG

A running log of decisions and of every time a person, the coding agent, or a tool got
something wrong: what happened, how it was caught, and the fix. Newest entries at the bottom.

Entry format: **What went wrong**, **How it was caught**, **Fix**, **Lesson**.

---

## 2026-10-26: Milestone 1, choosing the dataset

### Decision
Picked the Nolan lab tetrode session (Open Ephys legacy format) from the SpikeInterface
Training Dataset, Zenodo record 20726062. Runners-up: a Spike2 slow-oscillation LFP set
(Zenodo 4456700) and Minian's Miniscope V3 demo videos (Zenodo 20484805).

### Datasets labelled "raw" that were processed MATLAB files
- **What went wrong:** Several search hits looked like raw recordings in formats NeuroConv
  supports. Their titles or summaries said "raw" or "recorded with SpikeGLX". Examples:
  "Raw experimental data for 'Auditory cortex neurons that encode negative prediction
  errors…'" (Zenodo 15531781), a Froemke-lab "Raw fiber photometry dataset" (8060338),
  and the ZETA Neuropixels set (Dryad / Zenodo 4106086). All three contain only `.mat`
  exports or analysis files.
- **How it was caught:** Listing each record's actual files through the Zenodo REST API
  (`/api/records/<id>`) and its zip preview pages, instead of trusting titles or
  search summaries.
- **Fix:** Screened every candidate on its file list, not its description.
- **Lesson:** "Raw" in a repository title tells you nothing about the file format. Read
  the file list.

### Zenodo version drift
- **What went wrong:** The first record I read (20662886, v1) lists the Neuropixels
  session zip at 5.9 GB. The current version (20726062, v2) lists it at 15.1 GB. Quoting
  v1 would have understated the size by about 2.5×.
- **How it was caught:** Following the record's `/latest` redirect before writing up sizes.
- **Fix:** The download script pins record 20726062 and the zip's md5. The tetrode zip's
  md5 (`cc6b7883…`) is the same in both versions, so the choice of session is unaffected.
- **Lesson:** Pin the record version and checksum, not just the DOI concept.

### Agent bug: remote-zip reader crashed on first run
- **What went wrong:** To read `settings.xml` without downloading 2.2 GB, I wrote a
  seekable HTTP-range file object for `zipfile`. My first version subclassed
  `io.RawIOBase`, implemented `read()` but not `readinto()`, and wrapped it in
  `io.BufferedReader`. `BufferedReader` calls `readinto()`, so it raised
  `NotImplementedError` inside `zipfile._EndRecData64`.
- **How it was caught:** The traceback on the first run.
- **Fix:** Dropped the `RawIOBase` base class and the buffer. `zipfile` only needs
  duck-typed `seek`/`tell`/`read`. The working version is `HttpRangeFile` in
  `scripts/download_data.py`.
- **Lesson:** Implementing one method of a stdlib abstract base class doesn't make a
  working file object. Which method the wrapper actually calls matters.

### Agent bug: POSIX path passed to Windows Python
- **What went wrong:** From Git Bash I passed a `/c/Users/...` path into
  `exec(open(path).read())` inside Windows Python, which raised `FileNotFoundError`.
  Paths given on the command line are converted automatically; a path inside a `-c`
  string is not.
- **How it was caught:** The traceback.
- **Fix:** Pass paths as command-line arguments, or convert them with `cygpath -w`.
- **Lesson:** On Windows with Git Bash, assume every embedded path string needs conversion.

### Pitfalls confirmed from the real metadata (before any conversion code)
Read from `settings.xml`, `Continuous_Data.openephys` and `messages.events`:
- **Mixed units.** `bitVolts` is 0.195 for CH1–16 (µV per bit), 3.74e-5 for AUX (V per
  bit) and 1.526e-4 for ADC (V per bit). Treating them the same is a 10³–10⁶× scaling
  error.
- **Non-zero start.** `Processor: 100 start time: 107400@30000Hz`: the first sample is
  3.58 s after acquisition start. The NWB timestamps must handle this deliberately.
- **Tetrode grouping.** Tetrodes 1–4 are defined in the Spike Detector settings, and a
  Channel Map processor sits upstream. The channel-to-tetrode mapping must be read from
  the file, not assumed to be CH1–4 → tetrode 1.
- **Expected duration.** Each `.continuous` file is 134,619,334 B. Minus the 1024 B
  header, that is exactly 65,033 records of 2070 B (1024 samples each), so 66,593,792
  samples ≈ 2219.8 s at 30 kHz. The round-trip test can check this independently.
  *Correction (2026-10-27):* the last 992 of those samples are zero padding (see
  Milestone 3), so the recorded duration is 66,592,800 samples = 2219.76 s.
- **Few events.** `all_channels.events` holds 2 records (1056 B). Behavioural sync, if
  any, must be on the ADC channels; this is unconfirmed until the full download.
- **Subject metadata missing.** No sex, age or strain in the record. To be sourced or
  explicitly marked unknown.

---

## 2026-10-27: Milestone 2, scaffold

- `uv` was not installed; installed with `python -m pip install uv` (uv 0.13.5). Direct
  dependencies are exact-pinned in `pyproject.toml`, and `uv.lock` pins the rest.

### Stalled interpreter download
- **What went wrong:** I pinned Python 3.12 in `.python-version`. 3.12 wasn't installed, so
  `uv sync` tried to download a managed CPython 3.12.15 (21 MB). The download stalled with
  no output; I let the first attempt run 10 minutes before noticing.
- **How it was caught:** No `.venv` and no `uv.lock` existed after 10 minutes. A
  `timeout 90 uv python install 3.12 -v` run logged to a file showed it stuck at
  "Downloading cpython-3.12.15".
- **Fix:** Pinned 3.11 and pointed uv at the local Anaconda CPython 3.11.7. CI will
  install its own interpreter.
- **Lesson:** Run long installs with a timeout and verbose logging to a file. Piping into
  `tail` hides all progress until the process exits.

### Agent error: pinned an unresolvable dependency set
- **What went wrong:** I pinned `neuroconv[openephys]==0.10.2` and, separately, the newest
  `spikeinterface==0.105.3`, without checking that they agree on shared dependencies.
  uv resolves the lockfile for every Python version `requires-python` allows, not just
  the active one. On Python ≥ 3.14 the two conflict: neuroconv 0.10.2 requires
  `numcodecs<0.16.0` with no version marker, and spikeinterface 0.105.3 requires
  `numcodecs>=0.16.5` on Python 3.14 (it moves to zarr 3 there).
- **How it was caught:** `uv sync` refused to lock ("No solution found … for split
  (markers: python_full_version >= '3.14')"), even though the active Python was 3.11.
  pip would have installed fine on 3.11, and the problem would have surfaced for the first
  user on 3.14.
- **Fix:** `requires-python = ">=3.11,<3.14"`, with a comment pointing here.
- **Upstream check:** NeuroConv `main` already makes the cap conditional
  (`numcodecs<0.16.0; python_version < '3.14'`) as part of its zarr-3 port (catalystneuro/neuroconv#2105,
  closed 2026-10-14), but no release includes it yet. Not a PR opportunity; lift the
  upper bound when the next NeuroConv release is out.
- **Lesson:** Exact-pinning "latest" for several packages is not the same as a
  consistent set. Let the resolver prove it over the whole supported Python range.

### Smoke test results (Milestone 2)
`uv run pytest`: 3 passed (package import, `OpenEphysLegacyRecordingInterface` importable,
pinned versions match). `nwbinspector --version` gives 0.7.2. The CLI stub parses its
arguments and exits with "not implemented". `download_data.py --metadata-only` fetched the
4 metadata files (about 53 kB) into `data/raw/`. The full 2.2 GB download hasn't been run
yet.

---

## 2026-10-27: Milestone 3, conversion pipeline

### Agent bug: settings.xml parser read the wrong `<CHANNEL>` elements
- **What went wrong:** My first `read_settings()` took channel names from the Rhythm FPGA
  processor's direct `<CHANNEL>` children. Those elements only hold selection state and are
  named `"0"`, `"1"`, … The real names (`CH1`, `AUX1`, `ADC1`, …) sit under `<CHANNEL_INFO>`.
  The tetrode map came out as `{'Tetrode 1': ('0', '1', '2', '3'), …}`. It looked plausible
  and would have failed only later, when matched against the recording's channel IDs.
- **How it was caught:** Printing the parsed result against the real `settings.xml` before
  using it. `'0'` is not a channel name in the `.continuous` files.
- **Fix:** Read `CHANNEL_INFO/CHANNEL`. A unit test will pin the mapping (Milestone 4).
- **Lesson:** XML with repeated tag names at different depths: check the parsed values,
  not just that the parse ran.

### Read before trusting: what the signal chain says about the recorded data
- Only `100_*.continuous` files exist, and processor 100 is the Rhythm FPGA **source**. So
  the recorded data are wideband and sit upstream of the software band-pass filters
  (300–6000 Hz and 0.5–300 Hz) and the Channel Map. The only filtering applied is the Intan
  on-chip band-pass (1.96–7604 Hz) and DSP offset removal (0.146 Hz). This goes in the
  ElectricalSeries description. Claiming the data were 300–6000 Hz filtered would be wrong.
- The Channel Map is the identity (output *n* ← source *n*), with no re-referencing
  (`REFERENCE Channel="0"` means none). The parser still composes Channel Map →
  Spike Detector rather than assuming identity.

### NeuroConv trap found by reading source: passing `unit` silently drops scaling
- **What I found:** In `_add_time_series_segment_to_nwbfile` (NeuroConv 0.10.2), the
  recording's gain is turned into `conversion` only `if "unit" not in user_metadata`. Set
  `unit: volts` in metadata without also setting `conversion`, and the int16 counts are
  written with `conversion=1.0`. Nothing warns. The ADC data would then read as about
  6500× too large (1 / 1.526e-4).
- **How it was caught:** Reading the writer before relying on it, because the metadata
  needed `unit: "volts"` (SpikeInterface reports `"V"`).
- **Fix:** `OpenEphysLegacyAnalogInterface.get_metadata()` always sets `unit`,
  `conversion` and `offset` together. The round-trip test checks `data * conversion`
  against `bitVolts` from the raw headers (Milestone 4).

### My own pre-download claim was wrong: AUX is not accelerometer data
- **What went wrong:** In Milestone 1 and in the first converter draft I described AUX1–3
  as the "headstage accelerometer" and planned to write them as behaviour (head motion).
  The real data contain exactly two values: +32767 (the int16 maximum = 1.2255 V) for every
  sample except the final 992, which are 0.
- **How it was caught:** A per-channel summary (min/max/mean/number of unique values)
  from the independent raw reader (`tests/raw_openephys.py`), run before writing any
  NWB. `n_unique=2` gave it away.
- **Fix:** The AUX series is kept, as "auxiliary inputs", with a description stating that
  it is pinned at the int16 maximum and carries no recoverable signal. It is not called
  an accelerometer and is not placed under behaviour.
- **Lesson:** Hardware conventions (Intan AUX = accelerometer) are hypotheses about a
  file, not facts. Summarise every channel before giving it a name.

### Finding: the last record is zero-padded
- **What:** In all 27 files, the final 992 samples are exactly 0 on every channel. The last
  record (whose header says 1024 samples) holds only 32 real samples. Real wideband
  tetrode data are never exactly zero on 16 channels for 33 ms.
- **How it was caught:** The "unique values" summary showed `min=0` on the ADC4–8
  channels, whose signal sits around −4 V. Locating the zeros showed they all start at
  sample 66,592,800.
- **Fix:** The converter counts trailing samples that are zero on every channel of every
  stream within the final record and trims them from all streams together. The count is
  stated in the ElectricalSeries description.

### Finding: no TTL events; sync pulses are on an analog input
- `all_channels.events` holds 2 records, both type 5 (network/message events) at sample
  107400 from processors 100 and 136. These are recording-start markers, not TTLs.
- ADC1 shows 56 pulses, each 150.07–150.10 ms wide, 20–58 s apart (median 41 s), at 0 V /
  about 4.6 V. This matches random sync pulses for a tracking camera. The dataset doesn't
  say what they are, so the NWB descriptions say "matches the pattern of" and nothing more.
- A custom `SyncPulseInterface` writes them as a `SyncPulses` TimeIntervals table
  (start = rising edge, stop = falling edge, 2.5 V threshold). The raw ADC trace is kept,
  so the detection can be redone from the NWB file.

### Agent bug: channel IDs are not channel names
- **What went wrong:** `SyncPulseInterface` selected `channel_ids=["ADC1"]`, and the
  tetrode mapping keyed on `"CH1"` etc. The SpikeInterface legacy extractor's channel *IDs*
  are `'1'`, `'2'`, … with the prefix stripped, in every stream. The names live in the
  `channel_name` property.
- **How it was caught:** `AssertionError: ChannelSliceRecording : channel ids ['ADC1'] are
  not all in parent ids ['1' … '8']` on the first stub conversion.
- **Fix:** A `channel_names()` helper reads the `channel_name` property, and everything
  that identifies a channel uses it.

### NeuroConv bug (reproduced, unreported): wrapping the recording breaks `get_metadata()`
- **What happened:** To trim the padding I replaced the interface's `recording_extractor`
  with `recording.frame_slice(...)`. Then `get_metadata()` raised
  `AttributeError: 'FrameSliceRecording' object has no attribute 'neo_reader'`, because
  `OpenEphysLegacyRecordingInterface.get_metadata` reads
  `self.recording_extractor.neo_reader`.
- **It isn't just my code:** NeuroConv's own public `interface.remove_channels(...)` does
  the same thing (it returns a `ChannelSliceRecording`). Reproduced on the fixture:
  `remove_channels(["16"])` followed by `get_metadata()` gives the same `AttributeError`.
  The same `self.recording_extractor.neo_reader` access appears in the `get_metadata` of
  the Plexon, Neuralynx, AlphaOmega, Axon, Axona, MaxOne and MEArec interfaces. The legacy
  Open Ephys line is unchanged on `main`. No matching issue found in the repo.
- **Workaround here:** Trim inside `temporally_align_data_interfaces`, which runs after
  metadata is built.
- **Upstream candidate (Milestone 5):** Read from `self._extractor_instance`, the
  unwrapped extractor the base class already keeps.

### NeuroConv rough edge confirmed: start time silently reduced to date-only
- As predicted from reading the source, the legacy interface warns
  `The timestamp for starting time from openephys metadata is ambiguous ('95534')! Only
  the date will be auto-populated`. The `.continuous` header writes 09:55:34 as `95534`,
  without zero padding. Meanwhile `settings.xml` has the unambiguous `21 Apr 2023 9:55:34`,
  and NeuroConv already has a parser for it (`_get_session_start_time`, used by the binary
  interfaces).
- **Here:** `session_start_time` comes from the YAML (`2023-04-21T09:55:34+01:00`).
- **Upstream candidate:** Fall back to `settings.xml` in the legacy interface.

### Inspector preview on the stub file (full report in Milestone 4)
- BEST_PRACTICE_VIOLATION `check_electrodes_location_allen_ccf`: the electrodes table's
  `location` column was `unknown`. NeuroConv fills it from the recording's `brain_area`
  property, not from the group's location. Fixed by copying each group's location
  (Allen CCF term "Entorhinal area"; the dataset gives no dorsal/ventral zone, so the
  parent term is used) into `brain_area`.
- CRITICAL `check_subject_age`: no age or date of birth in the dataset. Open; needs a
  decision rather than a guess.
- The acquisition-board Device was missing from the file: NeuroConv creates devices only
  when an electrode group references one. The converter now adds it explicitly.

### Agent near-miss: `.gitattributes` would have rewritten the fixtures
- **What went wrong:** The Milestone 2 `.gitattributes` (`* text=auto eol=lf`) applies to the
  fixtures' `settings.xml` and `Continuous_Data.openephys`, which have CRLF line endings
  (written on Windows 7). Git would have stored them with LF, so the committed fixtures
  would no longer be byte-identical to the source data. The fixture README says they are.
- **How it was caught:** `git add` printed "CRLF will be replaced by LF in
  tests/fixtures/…/settings.xml".
- **Fix:** `tests/fixtures/** -text`. Checked with `cmp` that the staged copies equal the
  raw files.

### End-to-end result
- Full conversion: 122 s, 2.14 GB NWB from 3.6 GB of `.continuous` files.
- Spot-check against the independent raw reader (`tests/raw_openephys.py`):
  - 66,592,800 samples per stream.
  - `rate` 30 kHz and `starting_time` 0.
  - `conversion` equals header `bitVolts` for all three streams.
  - 0 mismatched samples in ten 1 s blocks per stream; first column of each stream
    identical over the full length.
  - Electrode → tetrode mapping matches `settings.xml`.
  - 56/56 sync pulses with identical edge times.
- NWB Inspector on the full file: 1 issue, CRITICAL `check_subject_age` (open).
