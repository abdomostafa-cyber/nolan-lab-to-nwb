# DEVLOG

A running log of decisions and of every time a person, the coding agent, or a tool got
something wrong: what happened, how it was caught, and the fix. Newest entries at the bottom.

Entry format: **What went wrong**, **How it was caught**, **Fix**, **Lesson**.

### At a glance: errors and how they were caught

| # | What went wrong | Whose | Caught by |
|---|---|---|---|
| 1 | Datasets titled "raw" were processed `.mat` exports | dataset metadata | listing actual files via the Zenodo API |
| 2 | Pinned NeuroConv + SpikeInterface set unresolvable on Python 3.14 | agent | uv's lockfile resolution across all supported Pythons |
| 3 | `settings.xml` parser read the wrong `<CHANNEL>` elements | agent | printing parsed values against the real file |
| 4 | AUX described as an accelerometer; it is pinned at int16 max | agent (assumption) | per-channel summary from the independent reader |
| 5 | Last record zero-padded (992 samples) | file format | `min=0` on channels that sit near −4 V |
| 6 | Channel IDs (`'1'`) used where names (`ADC1`) were needed | agent | assertion on the first stub conversion |
| 7 | Setting `unit` silently disables NeuroConv's scaling | NeuroConv | reading the writer's source before relying on it |
| 8 | `get_metadata()` crashes after slicing the recording | NeuroConv bug | first stub conversion; confirmed on upstream data |
| 9 | Workaround for #8 broke on a second `run_conversion` | agent | idempotency test |
| 10 | Test expected 150 ms; real pulses are 150.07–150.10 ms | agent (test) | the test failing on real data |
| 11 | Deprecated `Device.manufacturer` that the Inspector doesn't flag | agent / pynwb | DeprecationWarning in test output, now an error |
| 12 | Inspector CLI exits 0 on CRITICAL findings | NWB Inspector | checking the exit code before writing CI |
| 13 | Bad reproducer (incomplete metadata) almost reported a false bug | agent | reading where the exception was raised |
| 14 | Patch silently not applied (CRLF) | agent / Windows | the "patched" repro still failing |
| 15 | Duplicate check missed a same-day upstream fix (#2140) | agent | the user checking GitHub's activity view |

Plus smaller ones in the entries below: version drift on Zenodo, a broken remote-zip reader,
Windows path handling, a stalled interpreter download, `.gitattributes` rewriting fixtures, and
false alarms from a wheel-coverage script.

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

---

## 2026-10-27: Milestone 4, validation and tests

Test design: every expected value is either a literal confirmed by hand (from `settings.xml`,
the Zenodo record, or the raw analysis logged above) or computed by `tests/raw_openephys.py`,
a numpy-only reader written from the Open Ephys format description. Nothing is compared against
NeuroConv, neo or SpikeInterface output. The reader has its own tests: big-endian samples decoded
by hand from the bytes, rejection of truncated files, and the event records.

### Test caught a real bug: the Milestone 3 workaround broke on a second `run_conversion`
- **What went wrong:** In Milestone 3 I worked around the NeuroConv `neo_reader` bug by
  trimming the padding inside `temporally_align_data_interfaces`, "after metadata is built".
  That held for one call only. NeuroConv's `run_conversion` calls `validate_metadata` →
  `get_metadata_schema` → `get_metadata` every time. The second call on the same converter
  reached the already-sliced recording and raised the same `AttributeError`.
- **How it was caught:** `test_run_conversion_twice_is_idempotent`. I wrote it to check
  that the time shift doesn't stack; it found this instead.
- **Fix:** `SliceSafeOpenEphysLegacyRecordingInterface` overrides `get_metadata` to read
  from `self._extractor_instance`, the unwrapped extractor. It is a local backport of the
  upstream fix proposed for Milestone 5. The trim moved back into `__init__`.
- **Lesson:** A workaround that relies on call order in a framework is a guess about the
  framework. Test the second call, not just the first.

### Agent error in a test: expected pulse width was wrong, not the data
- **What went wrong:** `test_sync_pulses_match_independent_detection` asserted a width of
  0.150 s ± 2 samples. The fixture pulse is 0.1501 s (4503 samples). The full-session
  analysis in Milestone 3 had already shown widths of 0.150067–0.150100 s, and I wrote the
  test from the rounded "150 ms" instead of from that log.
- **How it was caught:** The test failed on both fixtures.
- **Fix:** Bound by the measured range, 0.1500–0.1502 s. The edge times themselves are
  compared exactly against the independent detection.
- **Lesson:** Take expected values from the measurement log, not from the summary sentence.

### Deprecated `Device.manufacturer` (pynwb 4)
- The test run showed `DeprecationWarning: The 'manufacturer' field is deprecated. Instead,
  use DeviceModel.manufacturer`. NWB Inspector 0.7.2 does not flag it.
- **Fix:** `DeviceModels` entry in the YAML, linked with `device_model_metadata_key`. The board
  is created with NeuroConv's `_add_device_to_nwbfile`, which resolves the model; it is private,
  but the public `add_device_from_metadata` only handles the old list-based metadata format.
  The suite now runs with `-W error::DeprecationWarning:hdmf.utils`, so a return of this fails.

### Rename: nwb-conversion-demo → nolan-lab-to-nwb
Renamed to follow CatalystNeuro's `<lab>-lab-to-nwb` convention. Package `nolan_lab_to_nwb`, CLI
`nolan-lab-to-nwb-convert`, git remote `abdomostafa-cyber/nolan-lab-to-nwb`. Earlier entries keep
the old names as they were at the time. The GitHub repository itself is renamed in its web
settings (no credentials are handled here). The local folder name is unchanged.

### Subject metadata: literature search found no source for mouse 1544
- A side session searched for a Vandrey/Nolan paper or preprint from 2023 onward with MEC
  tetrode open-field recordings that could cover session 1544 (April 2023). It found none.
  The session looks unpublished.
- Two lab papers describe the same rig, but they disagree on the animals. Gerlei et al.
  2020 (*Nat Commun*, doi:10.1038/s41467-020-17500-1) used the "p038 line", 4 male and 4
  female, 7–13 weeks at implant. Clark & Nolan 2024 (*eLife* 89356) used 9 male C57BL/6J.
  Neither is copied into `Subject`, which stays sex `U` with no age or strain. The missing
  age therefore remains an intentional Inspector finding (CRITICAL `check_subject_age`). The
  user is emailing the lab to ask.
- **Checked before use:** I read the Gerlei et al. 2020 Methods myself rather than citing
  the side session's summary. Confirmed: LED pulses "at random intervals (20–60 s)" to
  sync position with ephys; four tetrodes of 18 µm 90/10 Pt-Ir wire; Open Ephys board with
  an Intan RHD2000 SPI cable. *Not* stated there: the pulse duration, and whether the LED
  drive was recorded on an ADC channel.
- **What changed in the file:** The SyncPulses description says "consistent with the lab's
  published LED synchronisation procedure … not confirmed for this session". The tetrode
  drive description cites the published wire spec as lab practice, "not confirmed for this
  animal". 56 pulses in 2219.76 s (median interval 41 s, range 20–58 s) fits the published
  20–60 s.

---

## 2026-10-27: Milestone 5, upstream check before drafting anything

The user asked to be certain the NeuroConv `neo_reader` crash was not our own mistake before any
upstream text was written. What was done:

- **Separated our usage from the bug.** The way I first hit it (replacing `recording_extractor`
  with a frame slice) is ours and not a documented use. So the reproducer uses only public API:
  construct `OpenEphysLegacyRecordingInterface`, `get_metadata()`, `remove_channels()`,
  `get_metadata()`. It imports no project code (`.upstream/repro.py`).
- **Ruled out our data.** Downloaded NeuroConv's own test sample, `OpenEphys_SampleData_1` from
  GIN `NeuralEnsemble/ephy_testing_data` (7 files, 1.83 MB, with the user's OK). It reproduces
  there.
- **Ruled out a fixed-on-main bug.** Reproduced on NeuroConv `main` (2a46c7e, 0.11.0.dev0, in a
  separate venv under `.upstream/`) as well as 0.10.2. `run_conversion()` with no metadata
  crashes the same way. Passing metadata fetched *before* `remove_channels` avoids it.
- **Checked the fix like a reviewer would.** The one-line change (`self._extractor_instance.neo_reader`)
  plus a regression test. The new test **fails on the unpatched source** and passes with the fix.
  NeuroConv's own legacy tests went from 17 passed / 1 skipped to 18 / 1. All repros pass on
  the patched `main`.
- **Output:** `docs/upstream/neuroconv-issue-draft.md` and the `.patch`. Not posted. The other
  two rough edges (date-only start time; Inspector CLI exit code) are recorded there as
  discussion notes, not bugs, with the reasons.

### Mistakes made during the check (caught before they reached the draft)
- **Wrong reproducer.** My first `run_conversion` repro passed a hand-written metadata dict
  without an `Ecephys` section. It failed with an unrelated `AssertionError` (`metadata['Ecephys']
  dictionary does not contain key 'ElectricalSeries'`). Quoting it would have reported a
  bug that does not exist. Caught by reading where the exception was raised; the repro was
  rewritten to test the two realistic call patterns.
- **Patch silently not applied.** The clone has CRLF line endings (`core.autocrlf=true`), so my
  exact-match edit raised and the next test run was still on unpatched code. Caught because
  the "patched" repro still reproduced the bug. Re-applied with line-ending-aware matching
  and confirmed with `git diff` before testing.
- **Over-cautious claim in the draft.** I first wrote that Axona and Neuralynx are "possibly"
  affected. Checking `main` showed both read `neo_reader` in helpers called from `get_metadata`,
  so the draft now says so plainly. It also says the other interfaces were not run.
- **Environment friction (Windows).** A 260-character path limit in the scratchpad broke both
  the clone and the venv, and Anaconda's `cygpath` maps `/c/` to the Anaconda folder. Fixed by
  using `core.longpaths` for the clone only and a short `.upstream/` folder (gitignored).

### CI and DANDI: what the tools do on failure
- **The NWB Inspector CLI always exits 0.** With a CRITICAL finding present, `nwbinspector file.nwb`
  returned exit code 0; `_nwbinspector_cli` has no exit-code handling at all. A CI step that only
  ran it would always pass. Caught by checking `$?` before writing the workflow, not by assuming.
  **Fix:** `python -m nolan_lab_to_nwb.inspection` exits 1 on any finding at
  BEST_PRACTICE_VIOLATION or above that isn't documented. A test checks that it does fail
  (`test_gate_exits_nonzero_on_unexplained_issue`).
- **Agent error: my wheel-coverage check raised 12 false alarms.** A quick script reported missing
  CI wheels for numpy, deno, cffi, cryptography and wcwidth. Every flag was wrong: numpy is
  resolved separately for Python 3.11; deno ships `py3-none` wheels my pattern ignored; the other
  three are Linux-only and come only with the optional `upload` extra. Caught by reading the
  lockfile markers (`uv export`) instead of acting on the script.
- **DANDI rejects the missing age.** `dandi validate` rates `check_subject_age` as an **ERROR**,
  and `dandi upload` requires validation by default. Checked locally, with no account involved,
  before writing `docs/dandi_sandbox.md`. The guide says so up front and doesn't suggest
  putting a guessed age in the file.
- **Not yet verified:** the workflow has only been run step by step on Windows / Python 3.11. It
  has not run on GitHub (Ubuntu, 3.13) because nothing is pushed yet.

### Axon check before posting (user's request)
- Downloaded NeuroConv's Axon test files from GIN with the user's OK: `axon/File_axon_1.abf` (3.83 MB)
  and `axon/extracellular_data/four_electrodes/24606005_SampleData.abf` (178 kB, Dougherty Lab
  ventral roots).
- **Why the second file:** `File_axon_1.abf` has a single channel. Removing it leaves a
  zero-channel recording, a degenerate case a reviewer could fairly dismiss. The four-channel file
  lets the repro keep 3 channels, the realistic case. That's the workflow a maintainer suggested in
  neuroconv#2137 the day before.
- **Result:** `AxonRecordingInterface.get_metadata()` and `run_conversion()` both raise the same
  `AttributeError` after `remove_channels()`, on `main` and 0.10.2.
- **Fix checked the same way as before:** the new Axon test fails on unpatched source and passes
  with the fix. The selected NeuroConv tests go from 29 passed / 15 skipped to 31 / 15, with the same
  skip reasons before and after (their own markers: zarr 3, plugin loading). The difference is
  exactly the two new tests.
- The draft issue now covers both interfaces and is shorter. It still lists the other six
  interfaces as **not tested**.

### Agent error: the duplicate check missed a same-day upstream fix (caught by the user)
- **What went wrong:** I told the user a live search found no duplicate and that the Axon case was
  unreported. In fact the maintainer had opened and merged
  [#2140](https://github.com/catalystneuro/neuroconv/pull/2140), "Keep `AxonRecordingInterface.get_metadata`
  working after `remove_channels`", on 2026-10-26, within an hour of answering #2137. It landed one
  commit after the `main` I had cloned (`2a46c7e`). The draft then reported a bug that was already
  fixed.
- **How it was caught:** The user looked at the repository's activity on GitHub, saw that #2137 was
  the only recent issue, and asked me to recheck. Listing issues *and PRs* by creation date (not
  keyword search) showed #2140 at once. My keyword searches had returned only #2137, most likely
  because GitHub's search index lags behind very recent PRs. I had also searched issues where I
  should have looked at PRs and recent commits.
- **Fix:** Dropped Axon from the draft. Rebased the clone on `2c85f65` and reconfirmed that
  `OpenEphysLegacyRecordingInterface` is still affected there (`get_metadata` and plain
  `run_conversion`). Rewrote the fix in the maintainer's own style from #2140 (keep the reader
  in `__init__`) rather than mine (`_extractor_instance`), with a test mirroring theirs and a
  `changelog_entries/` fragment in their current format. The new test fails on current `main` and
  passes with the fix. The legacy tests go from 17 passed + 1 failing (the new test) to 18 passed,
  with the same Zarr skip.
- **Lesson:** Before reporting upstream, list the latest PRs and commits by date and check the
  current tip of `main`. Search is not a substitute for reading what's newest. The maintainer
  fixing the Axon case independently also confirms the bug class, which makes the remaining
  Open Ephys report much lower risk.

### Upstream PR opened
- **What:** The user opened [catalystneuro/neuroconv#2141](https://github.com/catalystneuro/neuroconv/pull/2141) on 2026-10-27 with the Open Ephys legacy fix, after rechecking
  that nothing newer than #2140 had landed (latest PRs, issues and branches listed by date; `main`
  still at `2c85f65`). The commit is authored with the email linked to the user's GitHub account
  and keeps the Claude co-author line. A second commit renamed the changelog entry from
  `PRNUMBER.bugfix.md` to `2141.bugfix.md`, which can only be done once the PR number exists.
- **Outcome:** the maintainer approved the CI workflows and merged it the same day (merge commit
  `128578d`, after merging `main` into the branch). The only failing checks were
  `run-live-service-tests` on Python 3.14, which stop at a credentials check because GitHub does
  not pass repository secrets to PRs from forks; the job's own message says this is expected for
  external contributors. The other 11 checks passed, and Codecov reported every changed line covered.
- **Not done:** the local backport (`SliceSafeOpenEphysLegacyRecordingInterface`) stays until the
  fix is in a NeuroConv release this project pins.


## 2026-10-29: Follow-up fixes for the other interfaces (held for review)

The maintainer asked for one PR per interface on #2141. AlphaOmega is #2152. Axona, MEArec, Neuralynx
and Plexon (three classes in one file) are committed locally and held until #2152 is reviewed;
MaxOne is held as a question, because its test class is skipped on every platform. Each fix follows
#2140/#2141: read what `get_metadata` needs in `__init__`, while the recording still has its
`neo_reader`. Each new test failed on `main` before the fix was applied.

### Agent error: committed after a failed pre-commit hook (caught by reading the hook output)
- **What went wrong:** The Neuralynx test had a line over the length limit. `black` failed and
  rewrote the file, but `git commit` ran in the same command and committed the unformatted version.
- **How it was caught:** Reading the hook output after the command: "black ... Failed - files were
  modified by this hook".
- **Fix:** Rewrote the line in #2140's style (a `folder_path` variable), re-ran hooks and tests, and
  amended the local, unpushed commit. Hooks and commit now run as separate steps.
- **Lesson:** Never chain the commit to the hooks; read the hook result first.

### Agent error: a test that only removed the only channel (caught by a manual conversion)
- **What went wrong:** The first Neuralynx test went into the only collected Neuralynx class, whose
  stream holds a single channel. "Remove the last channel" left an empty recording, so the test
  passed with the fix but tested a degenerate case.
- **How it was caught:** A manual `run_conversion` on that stream raised `IndexError`; listing the
  channels showed one.
- **Fix:** Moved the test to the Cheetah 5.7.4 data (5 channels). While doing so, found that the
  `V574`, `V563` and `V540` test classes have no base class or `test_` methods, so pytest collects
  nothing from them (noted in the PR draft, not changed).

### Agent error: a test inserted into the wrong class (caught by a test passing that should fail)
- **What went wrong:** My script found the end of each Plexon test class by searching for the next
  `class` line. `TestPlexonLFPInterface` is followed by a `@pytest.mark.skipif` decorator, so the
  LFP test landed inside `TestPlexon2RecordingInterface`, overriding that class's new test by name.
  There was no LFP test, and the "Plexon2" failure was really the LFP test.
- **How it was caught:** On `main`, the PlexonLFP test class passed while a manual run of the same
  steps raised the `AttributeError`. A test that passes on known-broken code is wrong.
- **Fix:** Class ends are now the next line at column 0 (decorators included). Checked the earlier
  branches' diffs: their tests sit right before the correct next class.

### Side effect: an experiment downloaded a vendor plugin
- **What happened:** MaxOne only runs on Linux. To reproduce its bug on Windows I bypassed that check
  in a scratch script. neo then auto-downloaded Maxwell's HDF5 compression plugin to
  `~/hdf5_plugin_path_maxwell/compression.dll`, its documented behaviour.
- **How it was caught:** The script's own output.
- **Fix:** Reported to the user; the folder can be deleted. Lesson: check what a library does on
  first use before running it outside its supported platform.

### Found along the way (not in these PRs)
- `AxonaUnitRecordingInterface` cannot be constructed on `main`: it passes `filename=` to a parent
  that does not accept it (`TypeError`). It has no tests.
- `TestMaxOneRecordingInterface` is skipped unconditionally and the interface is `# pragma: no cover`.

### Outcome: #2152 merged
- h-mayorquin approved #2152 ("LGTM") and merged it on 2026-10-29 with no changes to the code or
  test. The squash commit (`424eaf9`) kept the Claude co-author line this time.
- Rebased the five held branches onto the new `main` (`529e218`): no conflicts, and each interface's
  tests give the same counts as before (Axona 25, MEArec 13, Neuralynx 13, Plexon 41 passed; MaxOne
  still skipped). Still held, to be pushed one at a time with approval.
