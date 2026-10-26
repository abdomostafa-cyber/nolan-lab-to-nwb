# Uploading to the DANDI sandbox

The [DANDI sandbox](https://sandbox.dandiarchive.org) is DANDI's test instance: same software, separate
accounts and storage. Everything below was checked with `dandi` 0.81.0 against the converted file,
except the steps that need an account (marked **you**).

## Current blocker: subject age

`dandi validate` reports the missing age as an **ERROR**, not a warning:

```
[NWBI.check_subject_age] ... Subject is missing age and date_of_birth.   (severity: ERROR)
```

`dandi upload` refuses files that fail validation unless `--validation ignore` is passed, which its
own help calls "highly discouraged". The dataset reports no age or date of birth (see DEVLOG).
So the honest options are:

1. **Wait for the lab's answer** and add `age` (ISO 8601, e.g. `P12W`) or `date_of_birth` under
   `Subject` in `src/nolan_lab_to_nwb/metadata.yaml`. Then reconvert. Remove `check_subject_age` from
   `DOCUMENTED_EXCEPTIONS` in `src/nolan_lab_to_nwb/inspection.py`;
   `test_documented_exceptions_still_apply` will remind you. Then follow the steps below.
2. **Sandbox practice only:** upload with `--validation ignore`. This is acceptable on the sandbox,
   which exists for testing, but never on the main archive. Don't put a guessed age in the file to get
   past validation.

## Steps

```bash
# 0. Install the upload extra (dandi CLI)
uv sync --extra upload
```

1. **You:** sign in at <https://sandbox.dandiarchive.org> (GitHub login) and create a new Dandiset.
   Note its 6-digit ID, shown below as `<ID>`.
2. **You:** copy your sandbox API key (user menu → API key) and set it in your own shell. Never paste
   it into a file in this repo or into a chat.

   ```bash
   export DANDI_API_KEY=...        # bash
   $env:DANDI_API_KEY = "..."      # PowerShell
   ```

3. Download the empty Dandiset. This creates `<ID>/dandiset.yaml`:

   ```bash
   cd data
   uv run dandi download "https://sandbox.dandiarchive.org/dandiset/<ID>/draft"
   cd <ID>
   ```

4. Organize the NWB file into DANDI's layout. Checked with a dry run; the result is
   `sub-1544/sub-1544_ecephys.nwb`:

   ```bash
   uv run dandi organize ../nwb/sub-1544_ses-1544-2023-04-21-09-55-34-of_ecephys.nwb --files-mode copy
   ```

5. Validate. The only remaining error should be `check_subject_age` (see above):

   ```bash
   uv run dandi validate .
   ```

6. Upload (2.1 GB):

   ```bash
   uv run dandi upload -i dandi-sandbox                         # once age is filled in
   uv run dandi upload -i dandi-sandbox --validation ignore     # sandbox practice only (option 2)
   ```

7. **You:** on the Dandiset page, fill in the metadata the file can't carry: description,
   contributors (with the Nolan lab and dataset creators credited), license (CC BY 4.0, the source
   data's license) and a link to the source dataset (`doi:10.5281/zenodo.20726062`).

## Before anything goes to the main archive

This is a conversion of someone else's published data. Publishing it on the main DANDI archive should
be agreed with the Nolan lab and the dataset curators first, even though CC BY 4.0 permits
redistribution. The sandbox is for practice only.
