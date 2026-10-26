"""Command-line entry point: ``python -m nwb_conversion_demo.convert --data-dir ... --output ...``.

The conversion itself is implemented in Milestone 3; this module only fixes the CLI contract.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, required=True, help="Open Ephys session folder")
    parser.add_argument("--output", type=Path, required=True, help="Path of the .nwb file to write")
    parser.add_argument("--metadata", type=Path, default=None, help="Metadata YAML (defaults to the packaged one)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite --output if it exists")
    return parser


def main(argv: list[str] | None = None) -> None:
    build_parser().parse_args(argv)
    raise SystemExit("Conversion not implemented yet (Milestone 3).")


if __name__ == "__main__":
    main()
