"""Compare AY square/triangle/saw harmonics with the existing CC0 cello sample.

The saved report contains normalized harmonic magnitudes, not sample audio.
The target is a stable 140-ms window of the original local reference sample.
This is a bounded timbre/pitch screen, not a perceptual quality score.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
CLOCK = 1773450


def spectrum(values, rate, fundamental, count=12):
    times = np.arange(len(values))/rate
    window = np.hanning(len(values))
    return np.array([abs(np.sum(values*window*np.exp(-2j*np.pi*fundamental*k*times)))
                     for k in range(1,count+1)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-folder', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=HERE/'reports/ay-only/timbres.json')
    args = parser.parse_args()
    manifest = json.loads((args.sample_folder/'sources.json').read_text())
    info = next(r for r in manifest['samples'] if r['instrument']=='cello')
    path = args.sample_folder/info['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
    with wave.open(str(path),'rb') as wav:
        assert wav.getnchannels()==1 and wav.getsampwidth()==2
        rate = wav.getframerate()
        raw = np.frombuffer(wav.readframes(wav.getnframes()),'<i2').astype(float)
    target = raw[round(.24*rate):round(.38*rate)]
    target -= target.mean()
    nominal = 440*2**((info['nominal_midi_root']-69)/12)
    # Identify the actual sampled root before measuring its harmonic profile.
    frequencies = np.linspace(nominal*.96,nominal*1.04,1201)
    measured = max(frequencies,key=lambda f:spectrum(target,rate,f,1)[0])
    target_h = spectrum(target,rate,measured)
    target_h /= np.linalg.norm(target_h)
    from build import AY_LEVELS
    # AYumi's AY table repeats each 16-level DAC step twice. Use the equivalent
    # 32-step half-cycle table to include the true nonlinear DAC curve.
    up = np.repeat(np.array(AY_LEVELS),2)
    curves = dict(square=np.r_[np.zeros(32),np.ones(32)],
                  triangle=np.r_[up[::-1],up], saw=up[::-1])
    candidates = []
    for name,curve in curves.items():
        harmonic = spectrum(np.tile(curve,64),len(curve),1)
        harmonic /= np.linalg.norm(harmonic)
        candidates.append(dict(wave=name,normalized_harmonics=harmonic.tolist(),
            harmonic_distance=float(np.linalg.norm(harmonic-target_h)),
            hardware_shape=dict(square=None,triangle=10,saw=8)[name]))
    tuning = []
    for note in range(35,48):
        wanted = 440*2**((note-69)/12)
        period = round(CLOCK/(512*wanted))
        actual = CLOCK/(512*period)
        tuning.append(dict(note=note,triangle_period=period,hz=actual,
            error_cents=1200*math.log2(actual/wanted)))
    report = dict(date='2026-10-26',source_sample_sha256=info['sha256'],
        source_instrument='VSCO2 CE cello',license=manifest['license'],
        source_manifest_revision=manifest['revision'],source_root_hz=float(measured),
        source_harmonics=target_h.tolist(),candidates=candidates,bass_pitch_screen=tuning,
        scope='Stable normalized 12-harmonic comparison and integer-period tuning; no listening or whole-mix quality claim.',
        triangle_frequency_formula='AY clock/(512*envelope_period); a complete up/down cycle has 64 internal steps.',
        max_triangle_pitch_error_cents=18)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(candidates=[{k:v for k,v in c.items() if k!='normalized_harmonics'} for c in candidates],tuning=tuning),indent=2))


if __name__=='__main__':
    main()
