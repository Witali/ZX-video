"""Read or restore archived TRDs stored as exact aliases or sparse byte edits.

The reviewed manifest replaces redundant 640-KiB images. A timing candidate
is reconstructed exactly, never silently replaced by a similar player.
The default --check operation is read-only; --restore requires a new output.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/maintenance/2026-10-12-trd-deduplication.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repository_path(name: str) -> Path:
    path = (ROOT / name).resolve()
    if Path(name).is_absolute() or PureWindowsPath(name).drive or not path.is_relative_to(ROOT):
        raise ValueError(f"Invalid repository-relative image path: {name}")
    return path


@lru_cache(maxsize=1)
def records() -> dict[str, dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["schema"] != 1:
        raise ValueError("Unsupported TRD alias schema")
    result = {row["path"]: row for row in manifest["files"]}
    if len(result) != len(manifest["files"]):
        raise ValueError("Duplicate archived path")
    for row in result.values():
        repository_path(row["path"])
        repository_path(row["retained"])
        if row["retained"] in result:
            raise ValueError("Aliases must refer directly to retained images")
    return result


def reconstruct(row: dict, base: bytes) -> bytes:
    """Validate the retained image and every edit before returning original bytes."""
    if len(base) != row["bytes"] or digest(base) != row["retained_sha256"]:
        raise ValueError(f"Retained TRD identity changed: {row['retained']}")
    output = bytearray(base)
    previous_end = 0
    changed = 0
    for offset, hexadecimal in row["edits"]:
        value = bytes.fromhex(hexadecimal)
        if not value or offset < previous_end or offset + len(value) > len(base):
            raise ValueError("Invalid, overlapping or out-of-bounds sparse edit")
        output[offset:offset + len(value)] = value
        previous_end = offset + len(value)
        changed += sum(a != b for a, b in zip(base[offset:previous_end], value))
    if changed != row["changed_bytes"] or changed > 2048:
        raise ValueError("Changed-byte count does not match reviewed scope")
    result = bytes(output)
    if digest(result) != row["sha256"]:
        raise ValueError(f"Reconstructed TRD identity mismatch: {row['path']}")
    return result


def read_bytes(path: str | Path) -> bytes:
    """Read an ordinary artifact, or authenticate/reconstruct a missing archived TRD.

    Existing files retain normal read semantics. Only an explicitly reviewed
    missing .trd inside this repository may be resolved through the manifest.
    This lets archive verifiers authenticate their original immutable hashes.
    """
    path = Path(path)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        absolute = path.resolve()
        if absolute.suffix.lower() != ".trd" or not absolute.is_relative_to(ROOT):
            raise
        row = records().get(absolute.relative_to(ROOT).as_posix())
        if row is None:
            raise
        return reconstruct(row, repository_path(row["retained"]).read_bytes())


def check() -> int:
    """Authenticate all virtual images independently of any restored local copy."""
    for row in records().values():
        original = reconstruct(row, repository_path(row["retained"]).read_bytes())
        restored = repository_path(row["path"])
        if restored.exists() and restored.read_bytes() != original:
            raise ValueError(f"Existing restored image has changed: {row['path']}")
    return len(records())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--restore", metavar="OLD_REPOSITORY_PATH")
    parser.add_argument("--output", type=Path, help="New destination for exactly one restored image")
    args = parser.parse_args()
    if args.check:
        if args.output:
            parser.error("--output requires --restore")
        print(f"Authenticated {check()} archived TRDs without duplicate disk files.")
        return
    if not args.output:
        parser.error("--restore requires --output; existing files are never overwritten")
    old = repository_path(args.restore)
    row = records().get(old.relative_to(ROOT).as_posix())
    if row is None:
        parser.error("Path is not listed in the deduplication manifest")
    data = reconstruct(row, repository_path(row["retained"]).read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(data)
    print(f"Restored {len(data)} bytes; SHA-256 {digest(data)} to {args.output}")


if __name__ == "__main__":
    main()
