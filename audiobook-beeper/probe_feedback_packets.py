"""Bounded packet-PDM quality probe; host models, never a release proof."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np

from assess_snr import measure, FILTER, ratio
from build_pdm import reconstruct, RATE
from ima_codec import decode
from pdm_player import CPU_CLOCK

HERE = Path(__file__).resolve().parent


def table(pcm_bins, recent_bins, older_bins, beta, gain, extent, slots=16):
    """Midpoint state quantization; all arithmetic uses exact binary fractions."""
    states = recent_bins * older_bins
    recent = np.broadcast_to(((np.arange(states) // older_bins + .5) /
                              recent_bins * 2 - 1) * extent, (pcm_bins, states)).copy()
    older = np.broadcast_to(((np.arange(states) % older_bins + .5) /
                             older_bins * 2 - 1) * extent, (pcm_bins, states)).copy()
    target = .5 + gain * ((np.arange(pcm_bins)[:, None] + .5) / pcm_bins - .5)
    words = np.zeros((pcm_bins, states), dtype=np.uint16)
    peak = 0.
    for _ in range(slots):
        value = target + (1 + beta) * recent - beta * older
        bit = value >= .5
        older, recent = recent, value - bit
        words = (words << 1) | bit
        peak = max(peak, float(np.max(abs(recent))))
    r = np.clip(np.floor((recent / extent + 1) * recent_bins / 2), 0, recent_bins - 1)
    o = np.clip(np.floor((older / extent + 1) * older_bins / 2), 0, older_bins - 1)
    successor = (r * older_bins + o).astype(np.uint16)
    return words, successor, peak


def generate(levels, words, successor):
    states = words.shape[1]
    state = states // 2
    output = np.empty(len(levels), dtype='>u2')
    for i, pcm in enumerate(levels):
        row = int(pcm) * words.shape[0] // 256
        output[i] = words[row, state]
        state = int(successor[row, state])
    return np.unpackbits(output.view('u1'))


def integral_table(pcm_bins, recent_bins, beta=.5, extent=1., slots=16, holds=None, q_clip=(0,15)):
    """Preserve accumulated error q=e-beta*e_old on its exact 1/8 lattice.

    For 64 midpoint PCM bins and 16 decisions, 16*x is a multiple of 1/8.
    Unlike independent rounding of two histories, rounding recent e alone
    does not add DC error to q. q has 16 signed states in [-1,7/8].
    """
    assert pcm_bins in (64,128) and slots == 16
    states = 16 * recent_bins
    q = np.broadcast_to((np.arange(states) // recent_bins - 8) / 8,
                        (pcm_bins, states)).copy()
    recent = np.broadcast_to(((np.arange(states) % recent_bins + .5) /
                              recent_bins * 2 - 1) * extent, (pcm_bins, states)).copy()
    x = (np.arange(pcm_bins)[:, None] + .5) / pcm_bins
    words = np.zeros((pcm_bins, states), dtype=np.uint16)
    peak = 0.
    weights = np.ones(slots) if holds is None else np.asarray(holds) / np.mean(holds)
    for weight in weights:
        u = x + q / weight + beta * recent
        bit = u >= .5 - (1e-12 if pcm_bins == 128 else 0.)
        recent = u - bit
        q += weight * (x - bit)
        words = (words << 1) | bit
        peak = max(peak, float(np.max(abs(recent))))
    if holds is None and pcm_bins == 64:
        assert np.all(q * 8 == np.rint(q * 8))
    epsilon=1e-12 if pcm_bins == 128 else 0.
    qcode = np.clip(np.floor(q * 8 + 8.5 + epsilon), *q_clip)
    r = np.clip(np.floor((recent / extent + 1) * recent_bins / 2 + epsilon), 0, recent_bins - 1)
    successor = (qcode * recent_bins + r).astype(np.uint16)
    return words, successor, peak


def packet_measure(bits, decoded, source, times, ffmpeg):
    """Packet decisions have no accumulator player's three-output pipeline.

    Shifting bits across unequal holds would change their areas and invalidate
    a duration-aware table. Reconstruct the decisions at their actual holds.
    """
    signals = []
    for values in (bits, decoded / 256, source / 256):
        signal = reconstruct(values, times)
        run = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le',
                              '-ar', str(RATE), '-ac', '1', '-i', '-', '-af', FILTER,
                              '-ar', '44100', '-f', 'f32le', '-'],
                             input=signal.astype('<f4').tobytes(), capture_output=True, check=True)
        signals.append(np.frombuffer(run.stdout, '<f4').astype(float)[4410:-4410])
    out, dec, src = signals
    return dict(common_listening_filter=dict(modulator_snr_db=ratio(dec, out-dec),
                                            total_snr_db=ratio(src, out-src),
                                            codec_snr_db=ratio(src, dec-src)),
                output_latency_slots=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--family', choices=('rectangular', 'integral'), default='rectangular')
    p.add_argument('--schedule', choices=('uniform', 'estimated_packets', 'native_packets'), default='uniform')
    p.add_argument('--native-report', type=Path)
    p.add_argument('--packed', type=Path, help='Alternative IMA for the identical complete source WAV')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source_dir = HERE / 'experiments/ima-feedback64'
    packed = gzip.decompress((args.packed or (source_dir / 'soundtrack.ima.gz')).read_bytes())
    pcm, _ = decode(packed)
    levels = ((pcm.astype(np.int32) + 32768) >> 8).astype('u1')
    with wave.open(str(source_dir / 'source-preview.wav'), 'rb') as w:
        source = np.frombuffer(w.readframes(w.getnframes()), 'u1')
    assert len(source) == len(levels)
    repeated = np.repeat(levels, 16)
    reference = np.repeat(source, 16)
    times = np.arange(len(repeated) + 1) * CPU_CLOCK / 128000
    holds = None
    if args.schedule == 'estimated_packets':
        # Hand-counted first candidate, low/high tail balanced to 41 T.
        # This is explicitly NOT assembled or emulator timing evidence.
        holds = [36, 28, 28, 31, 27, 23, 23, 16, 31, 23, 27, 28, 33, 30, 35, 41]
        times = np.r_[0, np.cumsum(np.tile(holds, len(source)), dtype=np.int64)]
    if args.schedule == 'native_packets':
        if args.native_report is None:
            p.error('--native-report is required for native_packets')
        native = json.loads(args.native_report.read_text())
        assert native['complete_microkernel'] and native['every_bit_exact']
        holds = ((np.array(native['holds_low']) + native['holds_high']) / 2).tolist()
        timeline = np.tile(native['holds_low'] + native['holds_high'], len(source) // 2)
        times = np.r_[0, np.cumsum(timeline, dtype=np.int64)]
    variants = [
        dict(name='damped_64state', pcm_bins=64, recent_bins=16, older_bins=4, beta=.5, gain=1, extent=.5),
        dict(name='damped_32state', pcm_bins=64, recent_bins=16, older_bins=2, beta=.5, gain=1, extent=.5),
        dict(name='damped_128state', pcm_bins=64, recent_bins=32, older_bins=4, beta=.5, gain=1, extent=.5),
        dict(name='second_order_64state', pcm_bins=64, recent_bins=16, older_bins=4, beta=1, gain=.5, extent=1),
    ]
    if args.family == 'integral':
        variants = [dict(name=f'integral_recent{n}', pcm_bins=64, recent_bins=n,
                         beta=.5, extent=1., gain=1) for n in (2, 4)]
    report = dict(scope='Full current excerpt, ideal 128-kHz host model; no native player',
                  source_samples=len(source), source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                  packed_sha256=hashlib.sha256(packed).hexdigest(), rows=[])
    if holds is not None:
        report.update(scope='Full excerpt; hand-counted packet schedule model, not assembled or verified',
                      holds_tstates=holds, sample_tstates=sum(holds),
                      pdm_rate_hz=16 * CPU_CLOCK / sum(holds), pcm_rate_hz=CPU_CLOCK / sum(holds))
    if args.schedule == 'native_packets':
        report.update(scope='Host table on independently checked native microkernel timing; no ULA/refill/paging',
                      native_report_sha256=hashlib.sha256(args.native_report.read_bytes()).hexdigest(),
                      holds_low=native['holds_low'], holds_high=native['holds_high'])
    for spec in variants:
        params = {k: v for k, v in spec.items() if k != 'name'}
        if args.family == 'integral':
            params.pop('gain')
            words, successor, peak = integral_table(**params, holds=holds)
        else:
            words, successor, peak = table(**params)
        bits = generate(levels, words, successor)
        metrics = (packet_measure(bits, repeated, reference, times, args.ffmpeg) if holds is not None
                   else measure(bits, repeated, reference, times, args.ffmpeg, spec['gain']))
        row = dict(**spec, table_bytes=words.size * 4, peak_table_error=peak, metrics=metrics)
        report['rows'].append(row)
        print(json.dumps(row), flush=True)
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
