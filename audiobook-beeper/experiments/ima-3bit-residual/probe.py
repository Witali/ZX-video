"""Bounded codec/weighting controls on the overlap disk's saved PDM clock.

These are host controls, not executable disk formats or release validation.
Use --replay to reconstruct a saved carrier without rerunning beam search.
"""
import argparse
import gzip
import itertools
import json
from pathlib import Path
import time
import types

import numpy as np
import ima_waveform_encoder as production_encoder
import ima_codec as production_codec
from build_pdm import reconstruct, write_wav
from probe_reconstruction_error import wav8, filtered
from assess_snr import ratio

HERE = Path(__file__).resolve().parent
MODULES = HERE.parents[1]
VARIANTS = ('baseline', 'less_prior', 'slope', 'slope_strong',
            'ima4', 'standard3', 'quarter6')


def private_codec(variant):
    """Isolate experimental recurrences; never patch imported production code.

    Eight actual codes still occupy the even nibbles of the host carrier.
    standard3 has WAV-IMA3's quarter-step base and [-1,-1,+1,+2] adaptation.
    quarter6 uses that base with the project's faster [-1,-1,+2,+6] steps.
    """
    def module(filename):
        source = (MODULES/filename).read_text()
        source = source.replace('(step>>3)+', '(step>>2)+')
        source = source.replace('(steps>>3)+', '(steps>>2)+')
        source = source.replace('(steps >> 3)', '(steps >> 2)')
        source = source.replace('pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)',
                                'pcm,indices=decode(packed)')
        result = types.ModuleType(variant+'_'+filename[:-3])
        exec(compile(source, str(MODULES/filename), 'exec'), result.__dict__)
        if variant == 'standard3':
            result.INDEX = (-1, -1, -1, -1, 1, 4, 2, 8)
        return result
    codec = module('ima_codec.py')
    pcm = module('ima_beam.py')
    encoder = module('ima_waveform_encoder.py')
    encoder.decode = codec.decode
    encoder.require_unclipped = codec.require_unclipped
    encoder.encode_pcm = pcm.encode
    return codec, encoder


def close_guard(packed, codec):
    """Quarter-step codes have no zero delta: end the guard at exactly 0/0."""
    pcm, indices = codec.decode(packed)
    assert indices[-7] == 0
    paths = np.asarray(list(itertools.product((0, 2, 8, 10), repeat=6)), dtype='u1')
    differences = np.where(paths & 8, -1, 1)*np.where(paths & 2, 4, 1)
    predictions = int(pcm[-7])+np.cumsum(differences, axis=1)
    valid = np.flatnonzero(predictions[:, -1] == 0)
    chosen = valid[np.argmin(np.sum(predictions[valid]**2, axis=1))]
    tail = paths[chosen]
    return packed[:-3]+bytes((tail[::2] | (tail[1::2] << 4)).tolist())


def metrics(actual, original):
    ref = original[4410:-4410]
    error = actual[4410:-4410]-ref
    size = 8192
    window = np.hanning(size)
    frequencies = np.fft.rfftfreq(size, 1/44100)
    signal_power = np.zeros(len(frequencies))
    error_power = signal_power.copy()
    for start in range(0, len(ref)-size, size//2):
        signal_power += abs(np.fft.rfft(ref[start:start+size]*window))**2
        error_power += abs(np.fft.rfft(error[start:start+size]*window))**2
    bands = {}
    for low, high in ((70, 1000), (1000, 2000), (2000, 3000), (3000, 4000)):
        use = (frequencies >= low) & (frequencies < high)
        bands[f'{low}-{high}'] = float(10*np.log10(signal_power[use].sum()/error_power[use].sum()))
    return dict(snr_db=ratio(ref, error), bands=bands)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=VARIANTS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--replay', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = HERE.parent/'ima-3bit-overlap/qualified'
    meta, times, words, nxt, source, desired, features, ids = production_encoder.prepare(base)
    count = 32768+128
    prior = wav8(base/'compensated-pcm.wav')[:count].copy()
    prior[-128:] = 128
    source = source[:count].copy()
    source[-128:] = 128
    times = times[:count*16+1]
    ids, desired = ids[:count-128], desired[:count-128]
    codec, encoder = ((private_codec(args.variant)) if args.variant in ('standard3', 'quarter6')
                       else (production_codec, production_encoder))
    regularization = .003 if args.variant == 'less_prior' else .03
    weight = {'slope': .12, 'slope_strong': .4}.get(args.variant, 0)
    # Preserve the original diagnostic's two sets of output observations,
    # including zero-weight derivative observations for the ordinary controls.
    if args.variant not in ('standard3', 'quarter6'):
        holds = np.diff(times)[:(count-128)*16].reshape(-1, 16)
        unique, local_ids = np.unique(holds, axis=0, return_inverse=True)
        signed = np.unpackbits(words.astype('>u2').view('u1'), axis=1).reshape(-1, 16).astype(float)*2-1
        derivative = production_encoder.WaveformModel()
        derivative.c = derivative.c@derivative.coefficients[1]*(8000/(2*np.pi*1000))
        queries = ((times[:(count-128)*16]+times[1:(count-128)*16+1])/2).reshape(count-128, 16)
        target = derivative.reference(wav8(base/'source-preview.wav'), queries)
        new_features = []
        for position, row in enumerate(unique):
            at = np.flatnonzero(local_ids == position)[0]
            aa, ll, rr, bb, ww = features[ids[at]]
            _, _, dl, dr = derivative.packet(row)
            new_features.append((aa, np.concatenate((ll, dl)),
                                 np.concatenate((rr, signed@dr.T), axis=1), bb, np.r_[ww, ww*weight]))
        desired = np.concatenate((desired, target), axis=1)
        features, ids = new_features, local_ids
    started = time.monotonic()
    if args.replay:
        packed = gzip.decompress(args.replay.read_bytes())
    else:
        packed = encoder.encode_waveform(prior, desired, features, ids, nxt, width=256,
                   block_size=128, commit_size=64, regularization=regularization,
                   allowed_codes=None if args.variant == 'ima4' else np.arange(0, 16, 2),
                   level_bounds=meta['model']['level_bounds'])
        if args.variant in ('standard3', 'quarter6'):
            packed = close_guard(packed, codec)
    assert len(packed)*2 == count
    pcm, indices = codec.decode(packed)
    assert (pcm[-1], indices[-1]) == (0, 0)
    codec.require_unclipped(packed)
    state, packets = 16, []
    for value in pcm:
        level = (int(value)+32768)//512
        assert meta['model']['level_bounds'][0] <= level <= meta['model']['level_bounds'][1]
        packets.append(words[level, state])
        state = int(nxt[level, state])
    bits = np.unpackbits(np.asarray(packets, dtype='>u2').view('u1'))
    actual = filtered(reconstruct(bits, times), args.ffmpeg)
    period = 3546900/8000
    segments = int(np.ceil(times[-1]/period))
    edges = np.r_[np.arange(segments)*period, times[-1]]
    values = np.pad(source/256, (0, max(0, segments-count)), constant_values=.5)[:segments]
    original = filtered(reconstruct(values, edges), args.ffmpeg)
    report = dict(variant=args.variant, scope=__doc__, player_verified=False,
                  source_samples=count, active_samples=count-128,
                  replay=bool(args.replay), seconds=time.monotonic()-started,
                  **metrics(actual, original))
    (args.output/'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    write_wav(args.output/'result.wav', actual)
    write_wav(args.output/'source.wav', original)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
