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

### Smoke test results
`uv run pytest`: 3 passed (package import, `OpenEphysLegacyRecordingInterface` importable,
pinned versions match). `nwbinspector --version` gives 0.7.2. The CLI stub parses its
arguments and exits with "not implemented". `download_data.py --metadata-only` fetched the
4 metadata files (about 53 kB) into `data/raw/`. The full 2.2 GB download hasn't been run
yet.
