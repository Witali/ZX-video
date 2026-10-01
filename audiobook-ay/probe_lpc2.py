"""One bounded comparison: movie AY versus formant mapping from the user's LPC2."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'toolkit'))
import ay_fidelity as ay
import ay_interrupt
from build_long_video_trd import AyFrame
import compare_ay_fidelity as quality
from build_preview import save, sha
from player import build_disk


def formant_frames(records, samples, rate=8000, *, hop=160, clock_hz=ay.AY_CLOCK, levels=ay.LEVELS):
    """Map the decoded LPC2 spectral envelope and excitation class onto AY.

    LPC2 remains an offline analyser. AY has no LPC synthesis filter. This
    single candidate preserves the first three envelope peaks without musical
    note quantisation; its one noise source replaces B only on nonvoiced ticks.
    """
    frequency = np.arange(150, 3901, 10, dtype=float)
    w = 2*np.pi*frequency/rate
    exponent = np.exp(-1j*w[:, None]*np.arange(11))
    if len(samples) != len(records)*hop:
        raise ValueError('LPC records and source samples do not cover the same interval')
    rms = np.array([np.sqrt(np.mean(samples[i*hop:(i+1)*hop]**2)) for i in range(len(records))])
    peak = max(float(np.percentile(rms, 98)), 1e-12)
    frames, details = [], []
    previous = np.array([500., 1500., 2600.])
    for i, record in enumerate(records):
        envelope = 1/np.maximum(np.abs(exponent @ record['coefficients']), 1e-8)
        # Frequency peaks use pre-emphasised LPC, avoiding F0 dominance.
        maxima = np.flatnonzero((envelope[1:-1] >= envelope[:-2]) & (envelope[1:-1] >= envelope[2:]))+1
        selected = []
        for voice, (lo, hi) in enumerate(((180, 1050), (850, 2650), (1900, 3800))):
            lo = max(lo, selected[-1]+250 if selected else lo)
            valid = maxima[(frequency[maxima] >= lo) & (frequency[maxima] <= hi)]
            if len(valid):
                # Prefer persistent resonances when peak strengths are similar.
                scores = np.log(envelope[valid])-.6*np.abs(np.log(frequency[valid]/previous[voice]))
                f = frequency[valid[np.argmax(scores)]]
            else:
                valid = np.flatnonzero((frequency >= lo) & (frequency <= hi))
                f = frequency[valid[np.argmax(envelope[valid])]]
            selected.append(float(f))
        current = np.array(selected)
        previous = current.copy()
        periods = np.clip(np.rint(clock_hz/(16*current)), 1, 4095).astype(int)
        # Integrate de-emphasised spectral power around each selected resonance.
        power = (envelope / np.maximum(abs(1-.85*np.exp(-1j*w)), 1e-8))**2
        boundaries = [150, (current[0]+current[1])/2, (current[1]+current[2])/2, 3901]
        strength = np.array([np.sqrt(np.sum(power[(frequency >= boundaries[j]) & (frequency < boundaries[j+1])]))
                             for j in range(3)])
        strength /= max(float(np.linalg.norm(strength)), 1e-12)
        level = min(.9, .85*rms[i]/peak)
        volumes = np.argmin(abs(levels[None, :]-level*strength[:, None]), axis=1)
        noise = 0
        if record['mode'] in (0, 3):
            # AY cannot reproduce LPC's filtered noise. Use only B for these
            # consonants instead of retaining unrelated bass/melody tones.
            volumes[:] = 0
            volumes[1] = np.argmin(abs(levels-level))
            centroid = float(np.sum(frequency*power)/max(np.sum(power), 1e-12))
            noise = int(np.clip(round(clock_hz/(16*max(centroid*4, 1000))), 1, 31))
        if record['energy'] == 0:
            volumes[:] = 0
            noise = 0
        frames.append(AyFrame(tuple(map(int, periods)), tuple(map(int, volumes)), noise))
        details.append(dict(formants_hz=current.tolist(), mode=record['mode'], rms=float(rms[i])))
    return frames, details


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--lpc-source', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--start', type=float, default=60)
    p.add_argument('--duration', type=float, default=24)
    args = p.parse_args()
    if args.start < 0 or args.duration <= 0 or args.start+args.duration > 120:
        p.error('comparison must stay within the saved first 120 seconds')
    if any(abs(round(x*50)-x*50)>1e-8 for x in (args.start,args.duration)):
        p.error('start and duration must align to 20 ms')
    if args.output.exists() and any(args.output.iterdir()):
        p.error('output must be new or empty')
    args.output.mkdir(parents=True, exist_ok=True)
    command = [args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(args.start),
               '-i', str(args.input.resolve()), '-t', str(args.duration), '-map', '0:a:0',
               '-ac', '1', '-ar', '8000', '-f', 'f32le', '-']
    raw = subprocess.run(command, check=True, capture_output=True).stdout
    samples = np.frombuffer(raw, '<f4').astype(float)
    ticks = round(args.duration*50)
    if len(samples) != ticks*160:
        raise ValueError('incomplete source excerpt')
    pcm = args.output/'source.f32'; pcm.write_bytes(raw)
    subprocess.run([args.node, str(HERE/'lpc2_bridge.js'), str(args.lpc_source.resolve()),
                    str(pcm.resolve()), str(args.output.resolve())], check=True)
    analysis = json.loads((args.output/'lpc2-analysis.json').read_bytes())
    frames, details = formant_frames(analysis['frames'], samples)
    packed = b''.join(frame.serialize() for frame in frames)
    regs = b''.join(ay_interrupt.registers(frame) for frame in frames)
    (args.output/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
    old = gzip.decompress((HERE/'preview/soundtrack.ay9.gz').read_bytes())
    lo, hi = round(args.start*50)*9, round((args.start+args.duration)*50)*9
    old_frames = [AyFrame.deserialize(old[i:i+9]) for i in range(lo, hi, 9)]
    source_report = json.loads((HERE/'preview/report.json').read_bytes())
    with args.input.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if source_hash != source_report['source_sha256']:
        raise ValueError('baseline and comparison must use the identical audiobook')
    # Render every comparison at 22050 Hz, then apply one common RMS.
    def resample(blob):
        return np.frombuffer(subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin',
            '-f', 'f32le', '-ar', '8000', '-ac', '1', '-i', '-', '-ar', '22050', '-f', 'f32le', '-'],
            input=blob, capture_output=True, check=True).stdout, '<f4').astype(float)
    signals = {'original':resample(raw), 'old-ay':ay.render(old_frames, 50, 22050),
               'lpc2-reference':resample((args.output/'lpc2-reference.f32').read_bytes()),
               'lpc2-ay':ay.render(frames, 50, 22050)}
    levels = {k:float(np.sqrt(np.mean(s*s))) for k,s in signals.items()}
    common = min(.10, *(0.9*levels[k]/max(float(np.max(abs(s))),1e-12) for k,s in signals.items()))
    for name, signal in signals.items():
        quality.write_wav(args.output/f'{name}-preview.wav', signal*common/max(levels[name],1e-12), 22050)
    reference = quality.features(signals['original'], 22050, 10, round(args.duration*10))
    metrics = {k:quality.compare(reference, quality.features(s,22050,10,round(args.duration*10)))
               for k,s in signals.items() if k != 'original'}
    disk, metadata = build_disk(regs)
    (args.output/'audiobook-preview.trd').write_bytes(disk)
    save(args.output/'player.json', metadata)
    save(args.output/'formants.json', details)
    report = dict(complete=True, preview_only=True, speech_intelligibility_verified=False,
        selected_as_improvement=False,
        decision='Keep as diagnostic: formant mapping worsens signal proxies; listener assessment is pending',
        source=str(args.input.resolve()), source_sha256=source_hash, start_seconds=args.start,
        duration_seconds=args.duration, ticks=ticks, update_rate_hz=50,
        objective='reuse existing LPC2, then assess a three-formant AY mapping against rejected movie AY',
        lpc_source_sha256=analysis['source_sha256'], lpc_bitstream_bytes=analysis['stats']['actualBytes'],
        lpc_bitstream_roundtrip=analysis['bitstream_roundtrip'], mode_counts=dict(Counter(r['mode'] for r in analysis['frames'])),
        lpc_is_offline_only=True, native_lpc_decoder=False, pcm_dac_player=False,
        producer_sources_sha256_lf={name:sha((HERE/name).read_bytes().replace(b'\r\n', b'\n'))
                                   for name in ('probe_lpc2.py','lpc2_bridge.js')},
        registers_sha256=sha(regs), packed_sha256=sha(packed), metrics=metrics,
        metrics_scope='spectral/rhythm proxies only; user listening decides intelligibility',
        equal_rms_preview=common, disk_timing_verified=False,
        player_hot_path_delta_tstates=0,
        artifacts={f.name:dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes())) for f in args.output.iterdir()
                   if f.is_file() and f.suffix != '.f32'})
    save(args.output/'report.json', report)
    print(json.dumps(dict(metrics=metrics, mode_counts=report['mode_counts'], lpc_bytes=report['lpc_bitstream_bytes'])), flush=True)


if __name__ == '__main__':
    main()
