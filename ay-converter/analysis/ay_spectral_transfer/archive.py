"""Preserve each completed milestone after exact stream/audio/hash checks."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys

import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]; sys.path.insert(0, str(CORE))
from ay_format import AyFrame, registers
from support import sha, save
from verify_preview import expected_registers
from run import render
import quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--stage', required=True, choices=('stage1', 'stage2', 'stage3'))
    parser.add_argument('--node', default='node')
    parser.add_argument('--tests', type=Path)
    args = parser.parse_args(); target = HERE / 'evidence' / args.stage
    if target.exists(): raise ValueError('archive already exists')
    report = json.loads((args.build / 'report.json').read_bytes())
    assert report['complete'] and report['fields'] == 1500
    for relative, expected in report['producer_sha256_lf'].items():
        p = CORE / relative if relative != 'run.py' else HERE / relative
        assert sha(p.read_bytes().replace(b'\r\n', b'\n')) == expected, relative
    target.mkdir(); shutil.copyfile(args.build / 'report.json', target / 'report.json')
    for name in ('baseline.wav', 'spectrogram-full.png', 'spectrogram-detail.png'):
        shutil.copyfile(args.build / name, target / name)
    streams = []
    for trial in report['trials']:
        original = args.build / trial['name']; saved = target / trial['name']; saved.mkdir()
        raw = gzip.decompress((original / 'registers.gz').read_bytes())
        width = trial['metadata'].get('register_bytes', 11)
        rows = np.frombuffer(raw, np.uint8).reshape(-1, width)
        assert len(rows) == 1500 and np.all(rows[:, 1:6:2] < 16) and np.all(rows[:, 8:11] < (32 if width == 14 else 16))
        periods = rows[:, :6:2].astype(int) + 256 * rows[:, 1:6:2].astype(int)
        packed = b''.join(AyFrame(tuple(map(int, p)), tuple(map(int, r[8:11])), int(r[6]), int(r[7]),
                                  int(r[11]) + 256 * int(r[12]) if width == 14 else 0,
                                  int(r[13]) if width == 14 else 255, 12 if width == 14 else 9).serialize()
                          for p, r in zip(periods, rows))
        assert expected_registers(packed, 12 if width == 14 else 9) == raw and sha(raw) == trial['registers_sha256']
        replay = render(raw, args.node, original / 'independent-replay', width) * trial['gain']
        replay_path = original / 'independent-replay' / 'replay.wav'; quality.write_wav(replay_path, replay, 44100)
        assert replay_path.read_bytes() == (original / 'ay-preview.wav').read_bytes()
        assert sha(replay_path.read_bytes()) == trial['wave_sha256'] and len(replay) == 1323000
        for name in ('registers.gz', 'fit-controls.npz', 'report.json', 'ay-preview.wav', 'chip-render.json'):
            shutil.copyfile(original / name, saved / name)
        (saved / ('soundtrack.ay12.gz' if width == 14 else 'soundtrack.ay9.gz')).write_bytes(gzip.compress(packed, mtime=0))
        streams.append(dict(name=trial['name'], fields=1500, packed_registers_exact=True,
                            complete_wav_replay_exact=True, clipping_samples=int((abs(replay) >= 1).sum())))
    if args.tests: shutil.copyfile(args.tests, target / 'tests.log')
    save(target / 'verification.json', dict(complete=True, streams=streams, source_model_default_unchanged=True,
         native_instruction_delta_tstates=0, physical_chip_or_fuse_audio_verified=False,
         artifacts_sha256={str(p.relative_to(target)).replace('\\', '/'): sha(p.read_bytes())
                           for p in sorted(target.rglob('*')) if p.is_file()}))
    print(json.dumps(dict(complete=True, stage=args.stage, streams=len(streams), selected=report['selected'])))


if __name__ == '__main__': main()
