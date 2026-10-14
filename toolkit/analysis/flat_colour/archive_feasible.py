"""Preserve a completed rejected fill search without promoting it to the CLI."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path);p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--image-log', type=Path, required=True);p.add_argument('--pack-log', type=Path, required=True)
    p.add_argument('--tests', type=Path, required=True);args = p.parse_args()
    images = json.loads((args.build/'images.json').read_bytes())
    compressed = json.loads((args.build/'compression.json').read_bytes())
    assert images['frames'] == 977 and images['every_frame_source_contracts'] and images['changed_samples'] == 0
    assert compressed['stream_delta_bytes'] == 0
    sizes = compressed['sizes'];assert sizes['baseline']['raw_sha256'] == sizes['feasible']['raw_sha256']
    assert sizes['baseline']['stream_sha256'] == sizes['feasible']['stream_sha256']
    if args.destination.exists():raise ValueError('archive already exists')
    args.destination.mkdir(parents=True)
    for name in ('images.json', 'compression.json', 'states.npz', 'baseline.raw', 'baseline.stream'):
        shutil.copyfile(args.build/name, args.destination/name)
    for path, name in ((args.image_log, 'initial-images-and-cache-error.log'), (args.pack_log, 'pack-retry.log'), (args.tests, 'tests.log')):
        shutil.copyfile(path, args.destination/name)
    for name in ('toolkit/lineart_feasible.py', 'toolkit/test_lineart_feasible.py',
                 'toolkit/analysis/flat_colour/feasible_probe.py', 'toolkit/analysis/flat_colour/archive_feasible.py'):
        target = args.destination/'producer-sources'/name;target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))
    target = args.destination/'producer-sources/toolkit/lineart_colour.py'
    target.write_bytes(subprocess.check_output(['git', 'show', '78b7a7be:toolkit/lineart_colour.py'], cwd=ROOT))
    input_path = HERE/'disk-attempts/capacity-1005/cache-inputs.npz'
    decision = dict(date='2026-10-14', complete_host_review=True, release=False,
        baseline_commit='78b7a7be', input_path=input_path.relative_to(ROOT).as_posix(), input_sha256=digest(input_path),
        frames=977, changed_samples=0, compressed_bytes_before=sizes['baseline']['stream_bytes'],
        compressed_bytes_after=sizes['feasible']['stream_bytes'], decision='Reject as an accuracy improvement: every source/native pixel remains identical on the entire qualified prefix.',
        cache_error='Initial image phase completed, then missing cache directory stopped packing. Create it and resume the authenticated saved image results; both full native-host and LZSA2 roundtrips pass.',
        scope='Actual CB46 transport before invisible-attribute selection, including dictionary and LZSA2 headers. Not the final TRD stream/allocation or new timing qualification.',
        native_instruction_delta_tstates=0, source_snapshots='Final reproducible measurement code, plus baseline line selector from the measured commit.')
    (args.destination/'decision.json').write_text(json.dumps(decision, indent=2)+'\n', encoding='utf-8')
    files = {path.relative_to(args.destination).as_posix():dict(bytes=path.stat().st_size, sha256=digest(path))
        for path in args.destination.rglob('*') if path.is_file()}
    (args.destination/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(decision, indent=2))


if __name__ == '__main__':main()
