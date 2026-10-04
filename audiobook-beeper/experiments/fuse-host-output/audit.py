"""Authenticate the host-output checkpoint; optionally repeat offline analysis.

Replay never launches Fuse or changes an audio setting. It writes only to a
temporary workspace folder, preserving the original measured artifacts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = ('win32-44100', 'sdl-44100', 'win32-48000-buffered')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--write', action='store_true')
parser.add_argument('--replay', action='store_true')
parser.add_argument('--ffmpeg', type=Path)
args = parser.parse_args()
if args.replay and not args.ffmpeg:
    parser.error('--replay requires --ffmpeg')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest_path = HERE/'artifact-hashes.json'
if args.write:
    files = sorted(f for f in HERE.rglob('*') if f.is_file()
                   and f != manifest_path and '__pycache__' not in f.parts)
    inputs = ('ZX-audiobook-IMA3-overlap-test.trd',
              'audiobook-beeper/record_pcm.py', 'audiobook-beeper/build_pdm.py',
              'toolkit/smoke_test_fuse.py')
    manifest_path.write_text(json.dumps({
        'artifacts': {f.relative_to(HERE).as_posix(): digest(f) for f in files},
        'inputs': {f: digest(ROOT/f) for f in inputs},
    }, indent=2)+'\n', encoding='utf-8')
manifest = json.loads(manifest_path.read_bytes())
for group, base in (('artifacts', HERE), ('inputs', ROOT)):
    for name, expected in manifest[group].items():
        assert digest(base/name) == expected, (group, name)
disk_hash = digest(ROOT/'ZX-audiobook-IMA3-overlap-test.trd')
for name in RUNS:
    report = json.loads((HERE/name/'report.json').read_bytes())
    assert report['warnings'] == [] and report['exit_code'] == 77, name
    assert report['disk_sha256'] == disk_hash and report['loopback'], name
    with wave.open(str(HERE/name/'loopback.wav'), 'rb') as wav:
        assert wav.getframerate() == 48000 and wav.getnchannels() == 2
        assert wav.getnframes() == report['captured_samples'], name
    with wave.open(str(HERE/name/'internal.wav'), 'rb') as wav:
        assert wav.getframerate() == report['source_frequency']
        assert wav.getnframes() == report['internal_samples'], name
rejected = HERE/'rejected-48000-capture'
assert json.loads((rejected/'report.json').read_bytes())['warnings']
assert json.loads((rejected/'decision.json').read_bytes())['capture_valid'] is False

def equivalent(actual, expected, path='report'):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in expected:
            equivalent(actual[key], expected[key], f'{path}/{key}')
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, (a, e) in enumerate(zip(actual, expected)):
            equivalent(a, e, f'{path}/{i}')
    elif isinstance(expected, float):
        assert abs(actual-expected) < 1e-8, (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)

if args.replay:
    (ROOT/'.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='host-output-audit-', dir=ROOT/'.tmp') as temporary:
        work = Path(temporary)
        for name in RUNS:
            dest = work/name
            dest.mkdir()
            for file in ('report.json', 'stdout.txt', 'internal.wav',
                         'loopback.wav', 'capture.fmf.gz'):
                shutil.copyfile(HERE/name/file, dest/file)
            subprocess.run([sys.executable, str(HERE/'analyze.py'), str(dest),
                            '--ffmpeg', str(args.ffmpeg.resolve())], cwd=ROOT,
                           check=True, capture_output=True)
            subprocess.run([sys.executable, str(HERE/'fit-transfer.py'), str(dest)],
                           cwd=ROOT, check=True, capture_output=True)
            for file in ('analysis.json', 'transfer.json'):
                equivalent(json.loads((dest/file).read_bytes()),
                           json.loads((HERE/name/file).read_bytes()), f'{name}/{file}')
        speech = []
        for name in RUNS[:2]:
            with wave.open(str(work/name/'internal-speech.wav'), 'rb') as wav:
                assert wav.getsampwidth() == 2 and wav.getnchannels() == 1
                speech.append(wav.readframes(wav.getnframes())[4800*2:-4800*2])
        assert speech[0] == speech[1] and len(speech[0])//2 == 950400

print(json.dumps(dict(artifacts=len(manifest['artifacts']),
                      inputs=len(manifest['inputs']), hashes_exact=True,
                      valid_captures=3, rejected_captures=1,
                      offline_replay_verified=args.replay,
                      listening_defect_resolved=False)))
