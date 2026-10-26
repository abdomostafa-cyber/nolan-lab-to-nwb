"""Cut a tiny test fixture from the real session: a window of whole records from every .continuous file.

Legacy Open Ephys .continuous layout: a 1024-byte text header, then fixed 2070-byte records
(int64 timestamp, uint16 sample count = 1024, uint16 recording number, 1024 big-endian int16
samples, 10-byte record marker). Keeping whole records leaves every file valid for neo.
The header carries no length field, so nothing in it needs rewriting.

Two windows are used in the tests:
    --start-record 185 --records 16   records 185-200 (6.31-6.86 s): contains the first ADC1 sync pulse
    --start-record -16 --records 16   the last 16 records: contains the zero-padded final record

Usage:
    python scripts/make_fixture.py --source data/raw/1544_2023-04-21_09-55-34_of \
        --dest tests/fixtures/pulse --start-record 185 --records 16
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HEADER_BYTES = 1024
RECORD_BYTES = 8 + 2 + 2 + 1024 * 2 + 10
TEXT_FILES = ("settings.xml", "Continuous_Data.openephys", "messages.events", "all_channels.events")


def trim(source: Path, dest: Path, start_record: int, n_records: int) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.continuous")):
        total = (path.stat().st_size - HEADER_BYTES) // RECORD_BYTES
        start = start_record if start_record >= 0 else total + start_record
        if not 0 <= start <= total - n_records:
            raise ValueError(f"{path}: window {start}..{start + n_records} outside 0..{total}")
        with path.open("rb") as f:
            header = f.read(HEADER_BYTES)
            f.seek(HEADER_BYTES + start * RECORD_BYTES)
            body = f.read(n_records * RECORD_BYTES)
        (dest / path.name).write_bytes(header + body)
    # Event files are tiny (2 records in this session) and copied whole; neo reads events by timestamp.
    for name in TEXT_FILES:
        shutil.copy2(source / name, dest / name)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--start-record", type=int, default=0, help="First record; negative counts from the end")
    parser.add_argument("--records", type=int, default=16, help="Records per channel (1024 samples each)")
    args = parser.parse_args(argv)
    trim(args.source, args.dest, args.start_record, args.records)
    size = sum(p.stat().st_size for p in args.dest.iterdir())
    print(f"Wrote {args.dest} ({size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
