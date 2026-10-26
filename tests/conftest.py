from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
sys.path.insert(0, str(TESTS_DIR))  # for raw_openephys

FIXTURES = TESTS_DIR / "fixtures"
FULL_SESSION = TESTS_DIR.parent / "data" / "raw" / "1544_2023-04-21_09-55-34_of"


def _convert(folder: Path, output: Path) -> Path:
    from nolan_lab_to_nwb.convert import convert

    with warnings.catch_warnings():
        # Expected: NeuroConv cannot parse '95534' as a time and keeps only the date; the YAML sets it.
        warnings.filterwarnings("ignore", message="The timestamp for starting time from openephys metadata")
        return convert(folder, output, overwrite=True)


@pytest.fixture(scope="session", params=["pulse", "end"])
def converted_fixture(request, tmp_path_factory) -> tuple[Path, Path]:
    """(raw fixture folder, converted NWB path) for each fixture window."""
    folder = FIXTURES / request.param
    output = tmp_path_factory.mktemp(request.param) / f"{request.param}.nwb"
    return folder, _convert(folder, output)
