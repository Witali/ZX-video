"""Verify the complete beam-encoded stream with independent FFmpeg decoding."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from ima_codec import decode, require_unclipped, verification_wav


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--ffmpeg', required=True)
    args = p.parse_args()
    report = json.loads((args.directory / 'report.json').read_bytes())
    packed = gzip.decompress((args.directory / 'soundtrack.ima.gz').read_bytes())
    assert hashlib.sha256(packed).hexdigest() == report['packed_sha256']
    pcm, indices = decode(packed)
    blocks = 0
    for start in range(0, len(packed), 30000):
        chunk = packed[start:start+30000]
        predictor = int(pcm[2*start-1]) if start else 0
        index = int(indices[2*start-1]) if start else 0
        riff = verification_wav(chunk, predictor, index)
        result = subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'wav', '-i', '-',
                                 '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
                                input=riff, capture_output=True, check=True)
        independently_decoded = np.frombuffer(result.stdout, '<i2')
        expected = np.r_[predictor, pcm[2*start:2*(start+len(chunk))]].astype('<i2')
        assert np.array_equal(independently_decoded, expected), start
        blocks += 1
    proof = dict(complete=True, decoder='FFmpeg IMA WAV', independently_checked_samples=len(pcm),
                 wav_blocks=blocks, all_pcm16_samples_exact=True,
                 packed_sha256=report['packed_sha256'], guard=require_unclipped(packed),
                 ffmpeg_sha256=hashlib.sha256(Path(args.ffmpeg).read_bytes()).hexdigest())
    (args.directory / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    main()
