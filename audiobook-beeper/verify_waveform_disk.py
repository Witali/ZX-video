"""Rebuild and execute a waveform-aware IMA candidate on its own ULA clock.

An offline score on a pilot's output times is never accepted as a new disk's
quality. Keep the source, length, player model and hot-row layout fixed, but
recalibrate the silent loop tail and verify every output of two cold loops.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from convert_audio import (CPU, RATE, HERE, calibrate, validate, pcm_wav,
                           snapshot_sources, independent_ima_check)
from direct_player import MEASURED_MODEL
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from verify_direct import sample_positions
from verify_pcm import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', required=True, type=Path)
    parser.add_argument('--encoded', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fuse', required=True, type=Path)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output must be empty')
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((args.pilot / 'player.json').read_bytes())
    assert meta['model'] == MEASURED_MODEL
    source = wav8(args.pilot / 'source-preview.wav')
    packed = gzip.decompress((args.encoded / 'soundtrack.ima.gz').read_bytes())
    assert len(packed) * 2 == len(source) == meta['pcm_samples']
    assert np.all(source[-128:] == 128)
    hashes = snapshot_sources(out)
    for name in ('ima_waveform_encoder.py', 'verify_waveform_disk.py',
                 'probe_packet_area.py', 'probe_reconstruction_error.py'):
        blob = (HERE / name).read_bytes().replace(b'\r\n', b'\n')
        hashes[name] = hashlib.sha256(blob).hexdigest()
        (out / 'producer-source' / (name + '.gz')).write_bytes(gzip.compress(blob, mtime=0))
    save(out / 'producer-source' / 'hashes.json', hashes)
    manifest = dict(scope=__doc__, pilot=str(args.pilot), encoded=str(args.encoded),
                    source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                    ima_sha256=hashlib.sha256(packed).hexdigest(), samples=len(source),
                    hot_rows_frozen=True, ordinary_native_tstates=423,
                    ordinary_native_tstate_delta=0, complete=False)
    save(out / 'report.json', manifest)
    selected, new_meta = calibrate(out / 'calibration', packed, source, args.fuse, meta['hot_indices'])
    quality = validate(selected, args.fuse, args.ffmpeg)
    times = np.frombuffer(gzip.decompress((selected / 'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
    target = compensate(source, times[sample_positions(new_meta)], period=CPU / RATE)
    pcm_wav(selected / 'compensated-pcm.wav', target)
    for name in ('player.json', 'audiobook-preview.trd', 'soundtrack.ima.gz', 'source-preview.wav',
                 'compensated-pcm.wav', 'native.json', 'fuse.json', 'output-times.u32.gz',
                 'quality.json', 'voice-jitter.json', 'loop-2-voice-jitter.json',
                 'clock-aware-output-preview.wav', 'uniform-clock-source-preview.wav'):
        shutil.copy2(selected / name, out / name)
    shutil.copytree(selected / 'assembly', out / 'assembly')
    independent = independent_ima_check(packed, args.ffmpeg)
    recording = None
    if args.record:
        subprocess.run([sys.executable, str(HERE / 'record_pcm.py'), str(out), '--fuse', str(args.fuse),
                        '--output', str(out / 'sound-128'), '--machine', '128'], check=True)
        recording = json.loads((out / 'sound-128' / 'report.json').read_bytes())
        assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    manifest.update(complete=True, selected=str(selected.relative_to(out)), quality=quality,
                    independent_ima=independent, recording=recording,
                    trd_sha256=hashlib.sha256((out / 'audiobook-preview.trd').read_bytes()).hexdigest())
    save(out / 'report.json', manifest)
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
