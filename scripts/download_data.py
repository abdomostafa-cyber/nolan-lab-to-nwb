"""Download the Nolan lab tetrode session from Zenodo into data/.

Usage:
    python scripts/download_data.py                  # full zip (~2.2 GB), verify md5, extract
    python scripts/download_data.py --metadata-only  # only settings.xml and event files, via HTTP range requests

Only the standard library is used, so this runs before the environment is set up.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

RECORD_ID = "20726062"  # Zenodo "SpikeInterface Training Dataset", version v2
FILENAME = "1544_2023-04-21_09-55-34_of.zip"
MD5 = "cc6b78838ff4c48e101fe698edff1989"  # from the Zenodo record; identical in v1 and v2
URL = f"https://zenodo.org/records/{RECORD_ID}/files/{FILENAME}?download=1"
SESSION = FILENAME.removesuffix(".zip")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
METADATA_MAX_BYTES = 200_000  # anything smaller than this in the zip is a text/metadata file


class HttpRangeFile:
    """Minimal seekable read-only file over HTTP range requests, enough for zipfile.ZipFile."""

    def __init__(self, url: str):
        self.url = url
        self.pos = 0
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as response:
            self.size = int(response.headers["Content-Length"])

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        base = {0: 0, 1: self.pos, 2: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(request) as response:
            data = response.read()
        self.pos += len(data)
        return data


def md5sum(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url) as response, partial.open("wb") as out:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e9:.2f} / {total / 1e9:.2f} GB", end="", flush=True)
    print()
    partial.replace(destination)


def extract_metadata_only(raw_dir: Path) -> None:
    archive = zipfile.ZipFile(HttpRangeFile(URL))
    for info in archive.infolist():
        if not info.is_dir() and info.file_size < METADATA_MAX_BYTES:
            print(f"  {info.filename} ({info.file_size} B)")
            archive.extract(info, raw_dir)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--metadata-only", action="store_true", help="Fetch only settings.xml and event files")
    args = parser.parse_args(argv)

    raw_dir = args.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if args.metadata_only:
        print(f"Fetching metadata files of {FILENAME} from Zenodo record {RECORD_ID}")
        extract_metadata_only(raw_dir)
        return

    session_dir = raw_dir / SESSION
    if (session_dir / "settings.xml").exists() and any(session_dir.glob("*_CH1.continuous")):
        print(f"Already extracted: {session_dir}")
        return

    downloads = args.data_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    zip_path = downloads / FILENAME
    if not zip_path.exists():
        print(f"Downloading {URL}")
        download(URL, zip_path)

    print("Verifying md5 ...")
    actual = md5sum(zip_path)
    if actual != MD5:
        sys.exit(f"md5 mismatch for {zip_path}: expected {MD5}, got {actual}. Delete it and retry.")

    print(f"Extracting to {raw_dir} ...")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(raw_dir)
    free_gb = shutil.disk_usage(raw_dir).free / 1e9
    print(f"Done: {session_dir} ({free_gb:.1f} GB free; you may delete {zip_path})")


if __name__ == "__main__":
    main()
