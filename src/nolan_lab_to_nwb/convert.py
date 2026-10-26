"""Convert the Nolan lab open-field tetrode session to NWB.

Usage: ``python -m nolan_lab_to_nwb.convert --data-dir data/raw/1544_2023-04-21_09-55-34_of --output out.nwb``
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .converter import DEFAULT_METADATA_PATH, build_metadata, make_converter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, required=True, help="Open Ephys session folder")
    parser.add_argument("--output", type=Path, required=True, help="Path of the .nwb file to write")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH, help="Metadata YAML")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite --output if it exists")
    parser.add_argument("--stub", action="store_true", help="Write only the first 100 samples (quick check)")
    return parser


def convert(data_dir: Path, output: Path, metadata_path: Path = DEFAULT_METADATA_PATH, overwrite: bool = False,
            stub: bool = False) -> Path:
    converter = make_converter(data_dir)
    metadata = build_metadata(converter, metadata_path)
    conversion_options = {name: dict(stub_test=stub) for name in converter.data_interface_objects}
    output.parent.mkdir(parents=True, exist_ok=True)
    converter.run_conversion(
        nwbfile_path=output, metadata=metadata, overwrite=overwrite, conversion_options=conversion_options
    )
    return output


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    path = convert(args.data_dir, args.output, args.metadata, args.overwrite, args.stub)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
