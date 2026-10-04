"""Compare bounded PC searches on saved clocks; these are not disk releases."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import ima_waveform_encoder as encoder
from ima_codec import decode
from probe_reconstruction_error import wav8, filtered
from build_pdm import reconstruct
from assess_snr import ratio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASES = {
    'music3': ('entertainer-normalized/ima3', 3),
    'music4': ('entertainer-normalized/ima4', 4),
    'speech3': ('ima-3bit-overlap/qualified', 3),
    'speech4': ('ima-waveform', 4),
}
SEARCHES = (
    ('base', 256, 128, .03, 0),
    ('wide', 1024, 256, .03, 0),
    ('low-prior', 1024, 256, .003, 0),
    ('high-prior', 1024, 256, .1, 0),
    ('history16', 256, 128, .03, 16),
    ('history64', 256, 128, .03, 64),
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--samples', type=int, default=8192)
    p.add_argument('--case', choices=CASES, action='append')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for name in a.case or CASES:
        folder, bits = CASES[name]
        pilot = HERE.parent/folder
        meta, times, words, nxt, source, desired, features, ids = encoder.prepare(pilot)
        n = a.samples
        assert n % 8 == 0 and 1600 < n < len(source)-256
        prior = np.r_[wav8(pilot/'compensated-pcm.wav')[:n], np.full(128, 128, dtype='u1')]
        values = source[:n+128].copy(); values[-128:] = 128
        times = times[:(n+128)*16+1]
        period = 3546900/8000
        segments = int(np.ceil(times[-1]/period))
        edges = np.r_[np.arange(segments)*period, times[-1]]
        original = filtered(reconstruct(np.pad(values/256, (0, max(0, segments-len(values))), constant_values=.5)[:segments], edges), a.ffmpeg)
        ref = original[4410:-4410]
        for label, width, horizon, weight, history in SEARCHES:
            started = time.monotonic()
            packed = encoder.encode_waveform(prior, desired[:n], features, ids[:n], nxt,
                width=width, block_size=horizon, commit_size=64, regularization=weight,
                history_bins=history, allowed_codes=np.arange(0, 16, 2) if bits == 3 else None,
                level_bounds=meta['model'].get('level_bounds'), backend='native')
            elapsed = time.monotonic()-started
            pcm, _ = decode(packed)
            q = 16; packets = []
            for value in pcm:
                level = (int(value)+32768)//(65536//nxt.shape[0])
                packets.append(words[level, q]); q = int(nxt[level, q])
            pulses = np.unpackbits(np.asarray(packets, dtype='>u2').view('u1'))
            actual = filtered(reconstruct(pulses, times), a.ffmpeg)
            score = ratio(ref, actual[4410:-4410]-ref)
            (a.output/f'{name}-{label}.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
            row = dict(case=name, variant=label, width=width, horizon=horizon,
                       regularization=weight, history_bins=history, host_snr_db=score,
                       seconds=elapsed, samples=n, source_sha256=hashlib.sha256(values.tobytes()).hexdigest())
            rows.append(row)
            (a.output/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
            print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
