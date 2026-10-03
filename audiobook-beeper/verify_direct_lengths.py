"""Check short/partial-bank audio, fixed-cycle decoding and legacy binaries."""
import argparse
from functools import partial
import gzip
import hashlib
import json
from pathlib import Path
import wave
import numpy as np
from direct_player import build_disk, MEASURED_MODEL
from ima_beam import encode
from verify_direct import reference, intervals
from verify_packet import native_check, fuse_check
from verify_pcm import save
from convert_audio import pcm_wav


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fuse', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    with wave.open(str(here / 'experiments/ima-direct-weighted/source-preview.wav'), 'rb') as wav:
        source = np.frombuffer(wav.readframes(wav.getnframes()), 'u1')
    report = dict(binary_regressions=[], variable_lengths=[])
    for name in ('ima-direct-weighted', 'ima-direct-locked'):
        old = here / 'experiments' / name
        meta = json.loads((old / 'player.json').read_bytes())
        packed = gzip.decompress((old / 'soundtrack.ima.gz').read_bytes())
        disk, _ = build_disk(packed, args.output / name, meta['model'], meta['hot_indices'],
                             meta.get('loop_idle_pairs', 0), meta.get('loop_idle_pad_tstates', 0))
        assert disk == (old / 'audiobook-preview.trd').read_bytes()
        report['binary_regressions'].append(dict(name=name, identical=True, sha256=hashlib.sha256(disk).hexdigest()))
    for size in (256, 16640):
        samples = source[:size * 2].copy()
        samples[-128:] = 128
        packed = encode(samples)
        out = args.output / str(size)
        disk, meta = build_disk(packed, out / 'assembly', MEASURED_MODEL, idle_pairs=3, idle_pad=12)
        (out / 'audiobook-preview.trd').write_bytes(disk)
        (out / 'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
        pcm_wav(out / 'source-preview.wav', samples)
        save(out / 'player.json', meta)
        ref = partial(reference, model=meta['model'], idle_pairs=3)
        native = native_check(disk, meta, packed, ref, intervals)
        actual = fuse_check(args.fuse, out, meta, packed, False, ref, intervals)
        save(out / 'native.json', native)
        save(out / 'fuse.json', actual)
        report['variable_lengths'].append(dict(packed_bytes=size, sections=meta['sections'], native=native, fuse=actual))
        print(json.dumps(dict(packed_bytes=size, native_complete=native['complete'], fuse_complete=actual['complete'])), flush=True)
    save(args.output / 'report.json', report)


if __name__ == '__main__':
    main()
