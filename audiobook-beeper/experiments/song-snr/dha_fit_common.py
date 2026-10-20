"""Fit one shared 8-kHz DHA predictor using two non-song training recordings.

This fits codec payload tables, not evaluation gain, delay, clock or a song
preset. The complete sea-foam song and all generated controls are holdouts.
Input PCM8 is already authenticated/native8k; no conversion is resampled.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import wave

import numpy as np


HERE = Path(__file__).resolve().parent
TRAINING = ('speech', 'entertainer')
HOLDOUT = ('sea_foam', 'silence', 'quiet440', 'loud3000', 'steps', 'quiet997', 'multitone')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=HERE / 'evidence/general/inputs')
    parser.add_argument('--output', type=Path, default=HERE / 'evidence/dha-common-model')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Preserve previous evidence: provide a new empty output')
    output.mkdir(parents=True, exist_ok=True)
    matrices, targets, inputs = [], [], []
    for name in TRAINING:
        path = args.inputs / (name + '.wav')
        with wave.open(str(path), 'rb') as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 1, 8000)
            raw = stream.readframes(stream.getnframes())
        q = 2 * (np.frombuffer(raw, 'u1').astype('f8') - 128)
        h0, h1, h2, h3 = q[3:-1], q[2:-2], q[1:-3], q[:-4]
        x = np.column_stack((h0, h0-h1, h0-2*h1+h2, h0-3*h1+3*h2-h3))
        matrices.append(x)
        targets.append(q[4:] - h0)
        inputs.append(dict(name=name, wav_sha256=sha(path.read_bytes()), pcm8_sha256=sha(raw),
                           samples=len(q), training_rows=len(x), sample_rate=8000))
    x, y = np.concatenate(matrices), np.concatenate(targets)
    coefficients, residuals, rank, singular = np.linalg.lstsq(x, y, rcond=None)
    assert rank == 4 and np.isfinite(coefficients).all()
    # Match DHA's four separately rounded signed-byte correction rows. Row0
    # uses odd symmetry and virtual+256 at index0; it cannot contain-128.
    # Difference rows accept the complete signed8 domain and zero at index128.
    domains = [np.r_[256, np.arange(1, 256)], *[np.arange(-128, 128)] * 3]
    rows, clamps = [], []
    for index, domain in enumerate(domains):
        unbounded = np.rint(coefficients[index] * domain).astype('i4')
        lower = -127 if index == 0 else -128
        values = np.clip(unbounded, lower, 127).astype('i1')
        rows.append(values)
        clamps.append(int(np.count_nonzero(values.astype('i4') != unbounded)))
    model = np.concatenate(rows).tobytes()
    assert len(model) == 1024 and -128 not in rows[0]
    assert all(row[128] == 0 for row in rows[1:])
    (output / 'model.bin').write_bytes(model)
    report = dict(complete=True, date='2026-10-19', sample_rate=8000, training_names=TRAINING,
                  holdout_names=HOLDOUT, inputs=inputs, training_rows=len(y),
                  mathematical_target='q_next - q_prev; q_reference=2*(PCM8-128)',
                  fit='One unweighted least-squares fit, no intercept/ridge; no source-specific refit',
                  coefficients=coefficients.tolist(), matrix_rank=int(rank),
                  singular_values=singular.tolist(), least_squares_residuals=residuals.tolist(),
                  separate_product_rounding='nearest-even np.rint; signed8 table saturation is explicit',
                  saturated_table_entries=clamps, model_bytes=len(model), model_sha256=sha(model),
                  numpy_version=np.__version__, producer_sha256=sha(Path(__file__).read_bytes()),
                  encoder_options_changed=False, sample_gain_or_rate_changed=False,
                  evaluation_fit=False, heldout_song_used_for_fit=False,
                  compression_or_quality_accepted=False,
                  limits='Raw target histories train one shared codec predictor; coding uses reconstructed histories and may still require PCM16 fallback. Table fit alone is no quality/compression/player proof.')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (output / 'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    artifacts = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                 for p in sorted(output.iterdir()) if p.is_file()}
    (output / 'manifest.json').write_text(json.dumps(dict(artifact_files=artifacts), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(complete=True, coefficients=coefficients.tolist(), saturation=clamps,
                          training_rows=len(y), model_sha256=sha(model), directory=str(output))))


if __name__ == '__main__':
    main()
