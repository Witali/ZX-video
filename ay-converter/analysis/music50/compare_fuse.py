"""Compare complete normal-speed Fuse loops and draw matched spectrograms.

Matplotlib is an optional analysis-only dependency. Both captures use the
same Spectrum 128 clock correction, derived from hardware constants rather
than fitted to the music. Save raw-time metrics too; never use dynamic warping.
"""
import argparse
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE/'analysis/entertainer'))
from probe import decode, onset_proxy
import ay_fidelity as ay
import spectrogram
import quality
from support import save, sha


def normalized(samples):
    return samples/max(float(np.sqrt(np.mean(samples*samples))), 1e-12)*.1


def draw(signals, output, start, end, size, subtitle):
    spectra = []
    for samples in signals.values():
        mag, _ = ay.spectra(normalized(samples), 22050, 50, 1556, window_size=size)
        spectra.append(mag)
    hz = np.fft.rfftfreq(size*2, 1/22050)
    useful = (hz >= 80) & (hz <= 6000)
    lo, hi = round(start*50), min(1556, round(end*50))
    peak = max(float(spectra[0].max()), 1e-12)
    fig, axes = plt.subplots(len(signals), 1, figsize=(15, 9), sharex=True, sharey=True)
    fig.subplots_adjust(left=.065, right=.86, bottom=.07, top=.89, hspace=.24)
    for axis, (label, _), mag in zip(axes, signals.items(), spectra):
        db = 20*np.log10(np.maximum(mag[lo:hi, useful], peak*.001)/peak)
        picture = axis.pcolormesh((np.arange(lo,hi)+.5)/50, hz[useful], db.T,
                                  shading='auto', cmap='magma', vmin=-60, vmax=0, rasterized=True)
        axis.set_yscale('log')
        axis.set_yticks([100,250,500,1000,2000,4000], labels=['100','250','500','1k','2k','4k'])
        axis.set_ylabel('Hz')
        axis.set_title(label, loc='left', fontsize=11)
        axis.set_xlim(start,end)
    axes[-1].set_xlabel('Source time (seconds); all register updates on the 20-ms grid')
    fig.suptitle('The Entertainer — source / previous AY / music profile\n'+subtitle, fontsize=14)
    bar = fig.add_axes([.89,.14,.016,.67])
    fig.colorbar(picture, cax=bar, label='dB relative to source STFT peak; common RMS and scale')
    fig.savefig(output, dpi=130)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','candidate','ffmpeg','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ticks, rate = 1556, 22050
    count = ticks*441
    original = decode(args.ffmpeg, args.input, duration=31.12)[:count]
    reference = spectrogram.features(original)
    onset_reference = onset_proxy(original)
    # Fuse Spectrum 128: 70908 CPU T per field, CPU clock 3546900 Hz.
    # A physical loop is slightly shorter than the nominal 31.12 seconds.
    ratio = 50*70908/3546900
    signals = {'Original keyboard performance': original}
    results = {}
    for name, directory in [('Previous AY',args.baseline),('Music profile AY',args.candidate)]:
        path = directory/'fuse-preview.wav'
        audio = decode(args.ffmpeg, path)
        assert len(audio) >= count*ratio*2
        loops = []
        for loop in range(2):
            sample_indices = (np.arange(count)+loop*count)*ratio
            aligned = np.interp(sample_indices, np.arange(len(audio)), audio)
            loops.append(dict(stft=spectrogram.compare(reference, spectrogram.features(aligned)),
                onset_20ms=quality.match_onsets(onset_reference, onset_proxy(aligned),2),
                metrics=quality.compare(quality.features(original,rate,10,(ticks+4)//5),
                                        quality.features(aligned,rate,10,(ticks+4)//5))))
            if loop == 0:
                signals[name+' — cold Fuse, first complete loop'] = aligned
        results[name] = dict(capture_sha256=sha(path.read_bytes()), loops=loops,
            raw_first_31_12s_stft=spectrogram.compare(reference, spectrogram.features(audio[:count])))
    save(args.output/'fuse-spectrogram.json', dict(date='2026-10-04', complete=True,
        source_sha256=sha(args.input.read_bytes()), duration_ticks=ticks, update_rate_hz=50,
        fixed_clock_mapping_ratio=ratio, actual_loop_seconds=ticks/50*ratio,
        alignment='One fixed known clock mapping for both full captures, not estimated from signal; no time warp, pitch shift or local gain. Raw-time first-31.12-s scores also saved.',
        normalization='One global RMS per complete loop; STFT union support above source-relative -60 dB; 50..8000 Hz',
        comparisons=results))
    draw(signals,args.output/'spectrogram-full.png',0,31.12,2048,
         'Complete first Fuse loops; 92.88-ms window /20-ms hop; fixed Spectrum clock mapping')
    # Fixed regions span the intro, a busy phrase and the end, avoiding a
    # cherry-picked best improvement. Short window exposes attack timing.
    for start,end in [(0,4),(12,16),(27,31.12)]:
        draw(signals,args.output/f'spectrogram-{start:02d}-{end:g}s.png',start,end,2048,
             'Same scale and clock mapping; 92.88-ms window /20-ms hop')
    draw(signals,args.output/'spectrogram-attacks-12-16s.png',12,16,512,
         'Attack detail; 23.22-ms window /20-ms hop; same scale and clock mapping')
    # An equal-loudness A/B/C audition, separated by one second of silence.
    chunks = []
    for samples in signals.values():
        chunks.extend([normalized(samples),np.zeros(rate)])
    joined = np.concatenate(chunks[:-1])
    quality.write_wav(args.output/'comparison-original-old-new.wav', joined*min(1.,.95/max(abs(joined))),rate)
    print(json.dumps(results),flush=True)


if __name__ == '__main__':
    main()
