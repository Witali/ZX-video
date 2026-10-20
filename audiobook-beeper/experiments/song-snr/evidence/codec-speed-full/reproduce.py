"""Repeat frozen complete-song C trials on an authenticated original workset.

Generate the workset first with the codec-speed-profile reproduction script
using --song --workset-only. This script never changes existing evidence.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workset', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=3)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('rounds must be positive')
    scratch = args.scratch.resolve()
    if scratch.exists() and any(scratch.iterdir()):
        parser.error('scratch must be empty; preserve previous output')
    scratch.mkdir(parents=True, exist_ok=True)
    context = json.loads((HERE / 'context.json').read_bytes())
    workset = args.workset.resolve()
    assert sha(workset.read_bytes()) == context['workset']['sha256']
    assert workset.stat().st_size == context['workset']['bytes']
    dll = Path(context['matrix_library']['path'])
    assert sha(dll.read_bytes()) == context['matrix_library']['sha256']
    command = json.loads((HERE / 'build-command.json').read_bytes())['standalone_command']
    executables = {}
    for variant in ('baseline', 'selector'):
        build = scratch / variant
        build.mkdir()
        content = gzip.decompress((HERE / (variant + '.c.gz')).read_bytes())
        assert sha(content) == context[variant]['source_sha256']
        (build / 'kernel.c').write_bytes(content)
        compiled = subprocess.run(command, cwd=build, capture_output=True,
            timeout=120, creationflags=0x08000000)
        (build / 'build.log').write_bytes(compiled.stdout + compiled.stderr)
        assert compiled.returncode == 0, build / 'build.log'
        executables[variant] = build / 'kernel.exe'
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4
    api.GetProcessTimes.restype = wt.BOOL
    api.QueryProcessCycleTime.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]
    api.QueryProcessCycleTime.restype = wt.BOOL
    filetime = lambda value: (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)
    runs = []
    for turn in range(args.rounds):
        order = ('baseline', 'selector') if turn % 2 == 0 else ('selector', 'baseline')
        for variant in order:
            output = scratch / (variant + '.ima')
            started = time.perf_counter()
            child = subprocess.Popen([str(executables[variant]), str(workset), str(output), str(dll)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=0x08000000)
            stdout, stderr = child.communicate()
            elapsed = time.perf_counter()-started
            created, exited, kernel_time, user_time = (wt.FILETIME() for _ in range(4))
            handle = wt.HANDLE(int(child._handle))
            assert api.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                ctypes.byref(kernel_time), ctypes.byref(user_time)), ctypes.get_last_error()
            cycles = ctypes.c_ulonglong()
            cycles_ok = api.QueryProcessCycleTime(handle, ctypes.byref(cycles))
            assert child.returncode == 0, stderr
            packed = output.read_bytes()
            assert sha(packed) == context['expected_packed_sha256']
            row = dict(variant=variant, wall_seconds=elapsed,
                cpu_seconds=(filetime(kernel_time)+filetime(user_time))/1e7,
                process_cpu_cycles=cycles.value if cycles_ok else None,
                packed_bytes=len(packed), packed_sha256=sha(packed), statistics=json.loads(stdout))
            assert row['statistics'] == dict(samples=720384, search_iterations=1440448,
                final_predictor=0, final_index=0)
            runs.append(row)
            save(scratch / 'partial.json', dict(complete=False, runs=runs))
            print(json.dumps(row), flush=True)
    summary = {}
    for metric in ('wall_seconds', 'cpu_seconds', 'process_cpu_cycles'):
        before = [row[metric] for row in runs if row['variant'] == 'baseline']
        after = [row[metric] for row in runs if row['variant'] == 'selector']
        if any(value is None for value in before + after):
            continue
        old, new = statistics.median(before), statistics.median(after)
        summary[metric] = dict(baseline_median=old, selector_median=new,
            median_reduction_percent=100*(1-new/old), median_speedup=old/new)
    save(scratch / 'report.json', dict(complete=True, runs=runs, summary=summary))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
