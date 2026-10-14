"""Reconstruct the complete archived sea-foam song with nine OPL2 sine voices.

Use the unprocessed stereo song, not the separately limited 8-kHz beeper
preparation. Fit one continuous 90-second control stream; the reference is
only an analysis target. Export real YM3812 writes with the previously chosen
eight-step TL transitions, retaining an abrupt same-target control.
"""
import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import wave

import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
sys.path.insert(0, str(CORE / 'analysis/ym3812_clicks'))
import experimental_ym3812 as opl
import experimental_six_voice as six
import noise_colour
import quality
from analyze import diagnostic, plot, read
from compare import register_perturbations
from support import save
from test_experimental_ym3812 import audit

SONG_SHA = 'bf2218324c29575d3360d67d995012db43d27f5deb6aed9721aa9809d1c49190'
SECONDS = 90


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--song', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    if opl.sha(args.song.read_bytes()) != SONG_SHA: raise ValueError('wrong archived original song')
    if importlib.metadata.version('ymfm-py') != '0.2.0': raise ValueError('requires pinned ymfm-py0.2.0')
    with wave.open(str(args.song), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (2, 2, 44100, SECONDS * 44100)
    args.output.mkdir(parents=True)
    start = time.perf_counter()
    reference = args.output / 'reference.wav'
    filters = 'pan=mono|c0=0.5*c0+0.5*c1,aresample=22050'
    subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(args.song),
                    '-af', filters, '-c:a', 'pcm_s16le', '-bitexact', str(reference)], check=True)
    source = six.read_reference(reference)
    assert len(source) == SECONDS * opl.RATE
    controls, fitting_gain = opl.fit(source, 'sine')
    assert opl.validate(controls) == SECONDS * opl.HZ
    np.savez_compressed(args.output / 'controls.npz', **controls)
    print(json.dumps(dict(stage='full_song_fit_complete', fields=len(controls['fnum']), seconds=time.perf_counter() - start)), flush=True)
    rendered = []
    for name, exporter in (('abrupt', opl.vgm), ('smooth', opl.smooth_vgm)):
        data, writes = exporter(controls)
        checked = audit(data, controls)
        assert checked['writes'] == writes
        raw, samples, parsed = opl.replay(data)
        assert samples == SECONDS * opl.OUT_RATE and parsed == writes
        assert len(raw) == samples * opl.CLOCK // (72 * opl.OUT_RATE)
        assert not np.any(abs(raw) >= 1), 'native chip clipping'
        audio = opl.playback(raw, samples)
        rendered.append((name, data, writes, raw, audio, checked))
    # One fixed gain for the complete song and both exports. Do not hide a
    # transition tradeoff with separate normalization, clipping or source mixing.
    selected = rendered[-1][4]
    rms_gain = np.sqrt(np.mean(source ** 2) / max(np.mean(noise_colour.downsample(selected) ** 2), 1e-20))
    peak_gain = .95 / max(float(abs(item[4]).max()) for item in rendered)
    gain = float(min(rms_gain, peak_gain))
    trials = []
    for name, data, writes, raw, audio, checked in rendered:
        wave_name = 'ym3812-preview.wav' if name == 'smooth' else 'abrupt.wav'
        quality.write_wav(args.output / wave_name, audio * gain, opl.OUT_RATE)
        coded = gzip.compress(data, mtime=0)
        (args.output / (name + '.vgz')).write_bytes(coded)
        effects, independent = register_perturbations(data, gain)
        assert np.array_equal(raw, independent), 'complete independent native replay differs'
        observed = read(args.output / wave_name)
        trials.append(dict(name=name, writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded),
                           vgm_sha256=opl.sha(data), native_samples=len(raw), output_samples=len(audio),
                           peak=float(abs(audio * gain).max()), native_clipping_samples=int(np.sum(abs(raw) >= 1)),
                           clipping_samples=int(np.sum(abs(audio * gain) >= 1)),
                           complete_independent_native_replay_exact=True, audit=checked,
                           write_effects=effects, diagnostics=diagnostic(source, observed)))
        print(json.dumps(dict(stage='complete_trial', name=name, writes=writes, bytes=len(coded))), flush=True)
    data = rendered[-1][1]
    (args.output / 'ym3812.vgm').write_bytes(data)
    (args.output / 'ym3812.vgz').write_bytes(gzip.compress(data, mtime=0))
    versions = [('YM3812 nine sine carriers, smooth TL', read(args.output / 'ym3812-preview.wav'))]
    plot(source, versions, args.output / 'spectrogram-full.png')
    plot(source, versions, args.output / 'spectrogram-detail.png', trials[-1]['diagnostics']['worst_interval_seconds'])
    # Exact prepared source, one second of silence, then the complete chip WAV.
    # This comparison does not apply another gain or align pitch/time.
    comparison_source = args.output / 'comparison-source.wav'
    subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(reference),
                    '-ar', '44100', '-c:a', 'pcm_s16le', '-bitexact', str(comparison_source)], check=True)
    with wave.open(str(comparison_source), 'rb') as stream:
        assert stream.getnframes() == SECONDS * 44100
        source_44100 = stream.readframes(stream.getnframes())
    with wave.open(str(args.output / 'ym3812-preview.wav'), 'rb') as stream:
        output_pcm = stream.readframes(stream.getnframes())
    with wave.open(str(args.output / 'source-versus-ym3812.wav'), 'wb') as stream:
        stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
        stream.writeframes(source_44100 + bytes(88200) + output_pcm)
    producers = [Path(__file__), CORE / 'experimental_ym3812.py', CORE / 'analysis/ym3812_clicks/compare.py',
                 CORE / 'analysis/six_voice_spectral/analyze.py', CORE / 'test_experimental_ym3812.py']
    native_core = next(Path(ymfm.__file__).parent.glob('*.pyd'))
    result = dict(complete=True, date='2026-10-14', source_interval_seconds=[133.6, 223.6],
                  seconds=SECONDS, fields=4500, selected='smooth', fitting_mode='sine',
                  source_pcm_in_output=False, original_song_sha256=SONG_SHA,
                  source_preparation=filters + '; PCM16; no limiter, normalization, fades or beeper preparation',
                  reference_sha256=opl.sha(reference.read_bytes()), fitting_gain=fitting_gain,
                  global_playback_gain=gain, rms_matching_gain=float(rms_gain), peak_limit_gain=float(peak_gain),
                  nominal_transition_ms=2., transition_steps=8, ordered_pitch=True,
                  output_filter='Fixed20-Hz AC coupling and8-kHz129-tap fractional resampling; constant gain.',
                  chip_clock_hz=opl.CLOCK, ymfm_py_version='0.2.0', native_core_sha256=opl.sha(native_core.read_bytes()),
                  ffmpeg_version=subprocess.check_output([args.ffmpeg, '-version'], text=True).splitlines()[0],
                  trials=trials, elapsed_seconds=time.perf_counter() - start,
                  physical_chip_or_z80_player_qualified=False, release_player_hot_path_changed=False,
                  producer_sources_sha256_lf={str(p.relative_to(CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in producers},
                  artifacts_sha256={p.name: opl.sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()})
    save(args.output / 'report.json', result)
    print(json.dumps(dict(complete=True, seconds=SECONDS, fields=4500, gain=gain, elapsed_seconds=result['elapsed_seconds'])), flush=True)


if __name__ == '__main__': main()
