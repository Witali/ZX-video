"""Archive the interrupted first detailed UI capture without claiming playback."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source = HERE / 'pentagon512'
    target = HERE / 'attempts' / 'initial-full-ui-byte-hooks'
    assert not (target / 'report.json').exists()
    assert gzip.decompress((source / 'trace.txt.gz').read_bytes()) == b''
    assert (source / 'stderr.txt').read_bytes() == b''
    if not (target / 'pentagon512').exists():
        shutil.copytree(source, target / 'pentagon512')
    else:
        assert all((target / 'pentagon512' / path.name).read_bytes() == path.read_bytes()
                   for path in source.iterdir())
    producer = target / 'producer-source'
    producer.mkdir(exist_ok=True)
    sources = (
        ROOT / 'audiobook-beeper' / 'verify_stream_trd.py',
        HERE / 'verify.py',
    )
    hashes = {}
    for path in sources:
        data = path.read_bytes()
        hashes[path.relative_to(ROOT).as_posix()] = sha(data)
        (producer / (path.name + '.gz')).write_bytes(gzip.compress(data, mtime=0))
    assert hashes['audiobook-beeper/verify_stream_trd.py'] == 'f6c97433bdf3a044ba6b19de9f930187f09d289e77a8e1be477cc98499c6cdd9'
    report = dict(
        date='2026-10-14', complete=False, profile='pentagon512',
        trd_sha256='55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d',
        start_local_time='2026-10-14T19:43:24.0782006+02:00',
        stop_local_time='2026-10-14T20:02:30+02:00',
        termination='Only authenticated Fuse PID 25436 was stopped, at root instruction, before the 1200-second timeout; producer then saved stdout/stderr and failed its exit77 check.',
        fuse_return_code=4294967295,
        captured_stdout_bytes=0, captured_stderr_bytes=0,
        terminal_fuse_cpu_seconds=1140.390625,
        process_observations=[
            dict(fuse_cpu_seconds=515.765625, fuse_working_set_bytes=122974208,
                 python_working_set_bytes=53059584),
            dict(fuse_cpu_seconds=711.3125, fuse_working_set_bytes=122974208,
                 python_working_set_bytes=53059584),
            dict(fuse_cpu_seconds=809.796875, fuse_private_bytes=112050176,
                 python_private_bytes=441389056),
            dict(fuse_cpu_seconds=844.15625, fuse_private_bytes=112050176,
                 python_private_bytes=441389056),
            dict(fuse_cpu_seconds=969.21875, fuse_private_bytes=112050176,
                 python_private_bytes=441389056),
            dict(fuse_cpu_seconds=1057.46875, fuse_private_bytes=112050176,
                 python_private_bytes=441421824),
        ],
        clean_import_memory_control=dict(working_set_bytes=44081152,
                                         private_bytes=433336320),
        capture_script_sha256=sha((source/'debugger.txt').read_bytes()),
        producer_sha256=hashes,
        observed_stage=None, actual_source_pulses_verified=0,
        decision='Failed/incomplete instrumentation attempt; no release or player-fault claim. Separate saved READY/first-source diagnostics prove those stages only.',
        limits='Empty captured pipes do not prove no debugger events occurred, because stopping a process can discard buffered output. Large Python private memory was predominantly clean-import allocation.',
    )
    (target / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(archived=str(target), **report), indent=2))


if __name__ == '__main__':
    main()
