#!/usr/bin/env python3
"""Run a TRD until the streaming player's main loop is reached in Fuse."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


BREAKPOINT_EXIT = 77
FORBIDDEN_READ_EXIT = 99


def hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if sys.platform != "win32":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fuse", type=Path, help="path to fuse.exe")
    parser.add_argument("trd", type=Path)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--mode", choices=("128", "pentagon"), default="128")
    parser.add_argument(
        "--breakpoint",
        type=lambda value: int(value, 0),
        help="override the metadata main_loop address (diagnostics)",
    )
    parser.add_argument(
        "--hits",
        type=int,
        default=1,
        help="stop on this breakpoint hit (default: 1)",
    )
    parser.add_argument(
        "--forbid-read-after-preload",
        action="store_true",
        help=(
            "fail if read_n is called after its two startup preload calls; "
            "requires player_labels.read_n in metadata"
        ),
    )
    parser.add_argument(
        "--forbid-underflow",
        action="store_true",
        help="fail if the ring-buffer player waits for a missing packet",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if args.hits < 1:
        parser.error("--hits must be at least 1")

    fuse = args.fuse.resolve(strict=True)
    trd = args.trd.resolve(strict=True)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    main_loop = (
        args.breakpoint
        if args.breakpoint is not None
        else int(metadata["player_labels"]["main_loop"])
    )

    debugger_commands: list[str] = []
    main_breakpoint = 1
    next_breakpoint = 1
    if args.forbid_read_after_preload:
        read_n = int(metadata["player_labels"]["read_n"])
        debugger_commands += (
            f"breakpoint 0x{read_n:04X}",
            "ignore 1 2",
            "commands 1",
            f"exit {FORBIDDEN_READ_EXIT}",
            "end",
        )
        next_breakpoint += 1

    if args.forbid_underflow:
        underflow = int(metadata["player_labels"]["wait_packet_fill"])
        debugger_commands += (
            f"breakpoint 0x{underflow:04X}",
            f"commands {next_breakpoint}",
            f"exit {FORBIDDEN_READ_EXIT}",
            "end",
        )
        next_breakpoint += 1

    main_breakpoint = next_breakpoint

    debugger_commands.append(f"breakpoint 0x{main_loop:04X}")
    if args.hits > 1:
        debugger_commands.append(
            f"ignore {main_breakpoint} {args.hits - 1}"
        )
    debugger_commands += (
        f"commands {main_breakpoint}",
        f"exit {BREAKPOINT_EXIT}",
        "end",
    )
    debugger_script = "\n".join(debugger_commands)
    command = [
        str(fuse),
        "--no-sound",
        "--no-autosave-settings",
        "--no-confirm-actions",
        "--speed",
        "1000",
        "--debugger-command",
        debugger_script,
    ]
    if args.mode == "128":
        command += ["--machine", "128", "--beta128", str(trd)]
    else:
        command += ["--betadisk", str(trd)]

    try:
        completed = subprocess.run(
            command,
            cwd=fuse.parent,
            startupinfo=hidden_startupinfo(),
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"Fuse did not reach player main_loop at 0x{main_loop:04X} "
            f"within {args.timeout:g} seconds ({args.mode} mode)"
        ) from exc

    if completed.returncode == FORBIDDEN_READ_EXIT:
        if args.forbid_underflow:
            raise SystemExit("Fuse reached the ring-buffer underflow path")
        raise SystemExit("Fuse reached read_n after the two startup preload calls")
    if completed.returncode != BREAKPOINT_EXIT:
        raise SystemExit(
            f"Fuse exited with {completed.returncode}, expected "
            f"{BREAKPOINT_EXIT} from the main_loop breakpoint"
        )
    print(
        f"Fuse reached player main_loop hit {args.hits} at "
        f"0x{main_loop:04X} ({args.mode} mode)"
    )
    if args.forbid_read_after_preload:
        print("No disk read occurred during playback")
    if args.forbid_underflow:
        print("No ring-buffer underflow occurred during playback")


if __name__ == "__main__":
    main()
