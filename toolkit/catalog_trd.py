"""Render and authenticate the curated catalogue of tracked TRD/TFD images.

The JSON is reviewed provenance, not a filename-based quality classifier.
No encoding, playback, deletion, network access or Git mutation takes place.
Use --check for a read-only check; otherwise regenerate TRD_CATALOG.md.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "toolkit/trd_catalog.json"
DOCUMENT = ROOT / "TRD_CATALOG.md"
GITHUB = "https://github.com/Witali/ZX-video"


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], input=data)


def local(path: str) -> Path:
    result = (ROOT / path).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError(f"Path escapes repository: {path}")
    return result


def validate(catalog: dict) -> None:
    """Check coverage, materialized bytes, historical identity and branch evidence."""
    if catalog["schema"] != 1:
        raise ValueError("Unsupported catalogue schema")
    images = catalog["images"]
    names = [row["path"] for row in images]
    tracked = git("ls-files", "-z").decode("utf-8").split("\0")[:-1]
    expected = {p for p in tracked if Path(p).suffix.lower() in (".trd", ".tfd")}
    if len(set(names)) != len(names) or set(names) != expected:
        raise ValueError(f"Coverage mismatch; missing={sorted(expected-set(names))}, "
                         f"extra={sorted(set(names)-expected)}")
    for group in catalog["groups"].values():
        for path in group["scripts"] + ([group["guide"]] if group["guide"] else []):
            if not local(path).is_file():
                raise ValueError(f"Missing recipe reference: {path}")

    report_cache = {}
    branch_cache = {}
    ancestor_cache = {}
    by_hash = defaultdict(set)
    for row in images:
        by_hash[row["sha256"]].add(row["path"])
    queries = []
    for row in images:
        path = row["path"]
        payload = local(path).read_bytes()
        if len(payload) != row["bytes"] or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError(f"Image changed or LFS payload not materialized: {path}")
        if not re.fullmatch(r"[0-9a-f]{40}", row["commit"]):
            raise ValueError(f"Expected full artifact commit for {path}")
        if row["group"] not in catalog["groups"]:
            raise ValueError(f"Missing method for {path}")
        if not row["evidence"]:
            raise ValueError(f"Missing hash evidence for {path}")
        for report in row["evidence"]:
            if report not in report_cache:
                report_cache[report] = local(report).read_text(encoding="utf-8-sig")
            if row["sha256"] not in report_cache[report]:
                raise ValueError(f"Report does not identify {path}: {report}")
        if set(row["duplicates"]) != by_hash[row["sha256"]] - {path}:
            raise ValueError(f"Duplicate identity mismatch: {path}")
        branch = row["branch_reference"]
        if branch["evidence"] not in branch_cache:
            saved = json.loads(local(branch["evidence"]).read_text(encoding="utf-8"))
            branch_cache[branch["evidence"]] = {
                (b["name"], b["head"]) for b in saved["branches_initial"]}
        if (branch["name"], branch["head"]) not in branch_cache[branch["evidence"]]:
            raise ValueError(f"Unrecorded branch checkpoint: {path}")
        if branch["head"] not in ancestor_cache:
            ancestor_cache[branch["head"]] = set(git("rev-list", branch["head"]).decode().splitlines())
        if row["commit"] not in ancestor_cache[branch["head"]]:
            raise ValueError(f"Branch checkpoint does not contain artifact: {path}")
        queries.append(row["commit"] + ":" + path)

    # Raw blobs avoid smudge filters and distinguish a Git commit from a build
    # HEAD claim. LFS OID/size must identify the exact current materialized image.
    result = git("cat-file", "--batch", data=("\n".join(queries) + "\n").encode("utf-8"))
    offset = 0
    for row in images:
        end = result.index(b"\n", offset)
        header = result[offset:end].decode()
        if header.endswith(" missing"):
            raise ValueError(f"Missing historical Git image: {row['path']}")
        _, kind, size_text = header.split()
        size = int(size_text)
        blob = result[end + 1:end + 1 + size]
        offset = end + size + 2
        pointer = f"oid sha256:{row['sha256']}\nsize {row['bytes']}\n".encode()
        if kind != "blob" or not (pointer in blob or hashlib.sha256(blob).hexdigest() == row["sha256"]):
            raise ValueError(f"Artifact commit has different bytes: {row['path']}")


def link(path: str, label: str | None = None) -> str:
    return f"[{label or path}]({quote(path, safe='/')})"


def commit_link(sha: str) -> str:
    return f"[{sha}]({GITHUB}/commit/{sha})"


def recipe(group: dict) -> list[str]:
    lines = [group["description"], "", "Producer / orchestration: " +
             "; ".join(link(p) for p in group["scripts"]) + "."]
    if group["guide"]:
        lines.append("Method, inputs and invocation: " + link(group["guide"]) + ".")
    return lines + [""]


def entry(row: dict, level: int) -> list[str]:
    b = row["branch_reference"]
    lines = ["#" * level + " " + link(row["path"]), "",
             f"Saved change: {row['subject']}.", "",
             f"- Exact artifact commit: {commit_link(row['commit'])}.",
             f"- Recorded containing branch: `{b['name']}` at {commit_link(b['head'])}. "
             "Original build branch/HEAD: not established by this record.",
             f"- Image: {row['bytes']} bytes; SHA-256 `{row['sha256']}`.",
             "- Hash-matched evidence / build settings: " + "; ".join(link(p) for p in row["evidence"]) + "."]
    if row["duplicates"]:
        lines.append("- Byte-identical retained copies: " + "; ".join(link(p) for p in row["duplicates"]) + ".")
    return lines + [""]


def render(data: dict) -> str:
    images = data["images"]
    roots = [r for r in images if "/" not in r["path"]]
    archives = [r for r in images if "/" in r["path"]]
    branch_evidence = "docs/maintenance/2026-10-05-repository-cleanup.json"
    lines = ["# TRD image catalogue", "",
             f"Snapshot {data['date']}: **{len(images)} tracked images**, including **{len(roots)} root images** "
             f"and **{len(archives)} archived experiment/fixture images**; "
             f"{len({r['sha256'] for r in images})} distinct SHA-256 identities. "
             "No tracked `.tfd` files were found; this catalogue covers `.trd` disk images.", "",
             "The user requested purpose, production scripts, repository hash and branch for every disk. "
             "This is an inventory, not certification that every retained experiment is a recommended release.", "",
             "## Provenance and use", "",
             "An **artifact commit** is verified to contain these exact disk bytes (Git LFS OID/size or raw blob). "
             "It can be an archive/restoration commit, rather than the original encoder HEAD. The separate SHA-256 "
             "identifies the actual 640-KiB disk, not its small Git LFS pointer.", "",
             "Git commits do not store their creation branch. The **recorded containing branch** is the nearest "
             "containing non-main checkpoint in the " + link(branch_evidence, "2026-10-05 cleanup inventory") +
             ". An ancestry check authenticates this relationship; it is not proof that encoding ran on that branch. "
             "Many branches have since been merged/deleted. Original build HEAD/branch are not uniformly recorded, "
             "so they are not invented. Study baselines and source/tool hashes in reports have their own scopes.", "",
             "The inventory source revision is " + commit_link(data["snapshot_commit"]) +
             "; publication/integration branch: `main`. Each recipe names the responsible builder or orchestrator, "
             "with a guide and hash-matched report for parameters and inputs. Links to scripts use current repository "
             "paths; for historical reproduction use the recorded revision and its producer snapshots. "
             "Do not assume today's defaults recreate an old image. Saved `.gz` producers, `run-producers`, "
             "prepared PCM/IMA streams and manifests take precedence. Old absolute worktree/input paths may need "
             "restoration or explicit replacements; external source media and tools are not all included in Git.", "",
             "Archived `phase-*`, `pilot`, `control`, `history` and `paused` files are different build/calibration stages. "
             "Their path and evidence identify the stage. Equal hashes are explicitly linked; equal filenames or "
             "codec names do not imply equal sound. Individual resident-part test disks are not the whole sequential disk.", "",
             "Clearly unsuccessful payloads, including SD2, were removed: " +
             link("docs/maintenance/2026-10-05-retired-trds.md", "reasons and restoration ledger") +
             ". Historical manifests describe original bundles; restore retired payloads before replaying an old whole-bundle check. "
             "The public YouTube-linked direct IMA4 root file remains intact.", "",
             "Maintain reviewed records in " + link("toolkit/trd_catalog.json") + ", then run:", "",
             "```powershell", "python toolkit/catalog_trd.py", "python toolkit/catalog_trd.py --check", "```", "",
             "The check authenticates complete tracked-image coverage, current SHA-256/size, original Git blobs, "
             "report identities, recipe links, duplicate sets, saved branch checkpoints and ancestry. "
             "It does not rerun audio/video playback or infer sound quality.", "", "## Root images", ""]
    for row in roots:
        lines += entry(row, 3)
        lines += recipe(data["groups"][row["group"]])
    lines += ["## Archived experiments and fixtures", ""]
    grouped = defaultdict(list)
    for row in archives:
        grouped[row["group"]].append(row)
    for key, rows in sorted(grouped.items()):
        lines += ["### " + key, ""] + recipe(data["groups"][key])
        for row in rows:
            lines += entry(row, 4)
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Authenticate and compare without writing")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    rendered = render(data)
    if args.check:
        if not DOCUMENT.is_file() or DOCUMENT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("TRD_CATALOG.md is stale; run python toolkit/catalog_trd.py")
    else:
        DOCUMENT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Validated {len(data['images'])} tracked images and catalogue provenance.")


if __name__ == "__main__":
    main()
