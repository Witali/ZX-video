"""Convert audio to verified Spectrum TRDs using packed IMA3 and direct PDM.

The public CLI defaults to the accepted IMA3 converter and one sequential
disk. --codec ima4 selects the four-bit player with shared waveform search.
Its implementation and shared preparation helpers remain import-compatible.
"""
import argparse
from datetime import date
from functools import partial
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import numpy as np
from analyze_voice_jitter import analyze
from direct_player import build_disk, MAX_PACKED_BYTES, MEASURED_MODEL
from ima_beam import encode
from ima_codec import decode, verification_wav
from precompensate_voice import compensate
from probe_loop_phase import measure
from verify_direct import reference, intervals, sample_positions
from verify_packet import native_check, fuse_check
from verify_pcm import save
from quality_search import host_search, search_plan, ranked_hosts

CPU = 3546900
FIELD = 70908
RATE = 8000
HERE = Path(__file__).resolve().parent


def snapshot_sources(out):
    """Keep the producer and verifier sources beside each independent result."""
    archive = out / 'producer-source'
    archive.mkdir(exist_ok=True)
    names = ('convert_audio.py', 'direct_player.py', 'direct-player.asm', 'probe_loop_phase.py',
             'precompensate_voice.py', 'analyze_voice_jitter.py', 'verify_direct.py', 'verify_packet.py',
             'ima_beam.py', 'ima_codec.py', 'feedback_player.py', 'pcm_player.py', 'pdm_player.py',
             'packet_player.py', 'probe_feedback_packets.py', 'build_pdm.py', 'assess_snr.py',
             'verify_pcm.py', 'record_pcm.py', 'quality_search.py',
             'ima_waveform_encoder.py', 'waveform_kernel.py')
    hashes = {}
    for name in names:
        data = (HERE / name).read_bytes().replace(b'\r\n', b'\n')
        hashes[name] = hashlib.sha256(data).hexdigest()
        (archive / (name + '.gz')).write_bytes(gzip.compress(data, mtime=0))
    save(archive / 'hashes.json', hashes)
    return hashes


def pcm_wav(path, samples):
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((1, 1, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(np.asarray(samples, dtype='u1').tobytes())


def prepare_source(path, ffmpeg, duration=None, maximum_samples=None, alignment=512):
    """Read only a bounded prefix; one extra sample detects truncation."""
    guard = 128
    maximum_samples = maximum_samples or MAX_PACKED_BYTES * 2
    if alignment <= 0 or maximum_samples % alignment:
        raise ValueError('sample capacity must be a positive multiple of alignment')
    limit = maximum_samples - guard
    limit_reason = 'resident RAM capacity'
    if duration is not None:
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('duration must be positive and finite')
        requested = max(1, int(duration * RATE))
        if requested < limit:
            limit, limit_reason = requested, 'requested duration'
    command = [ffmpeg, '-v', 'error', '-nostdin', '-i', str(path),
               '-map', '0:a:0', '-t', str((limit + 1) / RATE),
               '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-']
    run = subprocess.run(command, capture_output=True, check=True)
    samples = np.frombuffer(run.stdout, '<f4').astype(float)
    if not len(samples) or not np.all(np.isfinite(samples)):
        raise ValueError('input has no finite decodable audio samples')
    truncated = len(samples) > limit
    samples = samples[:limit]
    peak = float(np.max(abs(samples)))
    gain = (109 / 128) / peak if peak else 1.
    prepared = samples * gain
    # Preserve relative dynamics; only one fixed gain and short edge fades.
    fade = min(80, len(prepared) // 2)
    if fade:
        prepared[:fade] *= np.linspace(0, 1, fade)
        prepared[-fade:] *= np.linspace(1, 0, fade)
    length = max(512, (len(prepared) + guard + alignment-1) // alignment * alignment)
    pcm = np.full(length, 128, dtype='u1')
    pcm[:len(prepared)] = np.clip(np.rint(prepared * 128 + 128), 0, 255).astype('u1')
    # Repeating a very short input gives phase calibration a >=1-s loop;
    # otherwise rounding its entire loop to one field could exceed 2%.
    repetitions = max(1, math.ceil(8192 / length))
    pcm = np.tile(pcm, repetitions)
    metadata = dict(input=str(path), sample_rate_hz=RATE, channels=1, pcm_bits=8,
                    retained_input_samples=len(samples), retained_input_seconds=len(samples) / RATE,
                    truncated=truncated, truncation_reason=(limit_reason if truncated else None),
                    requested_duration_seconds=duration,
                    maximum_packed_bytes=MAX_PACKED_BYTES, prepared_samples=len(pcm),
                    maximum_prepared_samples=maximum_samples,
                    short_input_repetitions=repetitions, silence_guard_samples=guard,
                    fixed_gain=gain, original_peak=peak, edge_fade_samples=fade,
                    peak_target_fraction=109 / 128, quality_reference='Prepared PCM8, with the same gain/fades/padding',
                    source_sha256=hashlib.sha256(pcm.tobytes()).hexdigest())
    probe = Path(ffmpeg).with_name('ffprobe' + Path(ffmpeg).suffix)
    if probe.is_file():
        run = subprocess.run([str(probe), '-v', 'error', '-select_streams', 'a:0',
                              '-show_entries', 'stream=codec_name,sample_rate,channels,bits_per_sample:format=duration',
                              '-of', 'json', str(path)], capture_output=True, check=True)
        metadata['input_media'] = json.loads(run.stdout)
    return pcm, metadata


def write_candidate(out, packed, source, hot=None, pairs=0, pad=0):
    out.mkdir(parents=True, exist_ok=True)
    disk, meta = build_disk(packed, out / 'assembly', MEASURED_MODEL, hot, pairs, pad)
    meta['compensated_reference_rate_hz'] = RATE
    save(out / 'player.json', meta)
    (out / 'audiobook-preview.trd').write_bytes(disk)
    (out / 'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    pcm_wav(out / 'source-preview.wav', source)
    return disk, meta


def prepared_ima4_source(path):
    """Retain an externally normalized PCM8 reference without a second gain."""
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 1, RATE):
            raise ValueError('prepared PCM must be mono PCM8 at 8000 Hz')
        source = np.frombuffer(wav.readframes(wav.getnframes()), 'u1').copy()
    if not 8192 <= len(source) <= MAX_PACKED_BYTES * 2 or len(source) % 512:
        raise ValueError('prepared IMA4 PCM must fit RAM, have >=8192 samples and a multiple of 512 samples')
    if np.any(source[-128:] != 128):
        raise ValueError('prepared PCM requires a final 128-sample silent guard')
    return source, dict(input=str(path), prepared_pcm_unchanged=True,
                        prepared_samples=len(source), sample_rate_hz=RATE,
                        channels=1, pcm_bits=8, fixed_gain=1.,
                        silence_guard_samples=128,
                        source_sha256=hashlib.sha256(source.tobytes()).hexdigest())


def representable_pad(value):
    return value >= 0 and any(value >= 7 * b and (value - 7 * b) % 4 == 0 for b in range(4))


def calibrate(out, packed, source, fuse, hot=None, writer=write_candidate):
    """Bounded search; never reuse a phase calibration for a different stream."""
    attempts = []
    pairs = pad = 0
    fields = None
    tried = set()
    for number in range(24):
        work = out / f'phase-{number:02d}'
        disk, meta = writer(work, packed, source, hot, pairs, pad)
        if hot is None:
            hot = meta['hot_indices']
        probe = measure(work, fuse, fields)
        if fields is None:
            fields = probe['target_cycle_tstates'] // FIELD
        attempts.append(dict(number=number, **probe))
        save(out / 'calibration.json', dict(attempts=attempts, complete=False))
        delta = probe['deltas_from_target']
        # A <=3-T cold transient is separately recorded. The second complete
        # loop must repeat at exactly the same phase, not drift indefinitely.
        if abs(delta[0]) <= 3 and delta[1] == 0:
            save(out / 'calibration.json', dict(attempts=attempts, complete=True, selected=number))
            return work, meta
        tried.add((pairs, pad))
        error = -delta[0]
        if not pairs:
            pairs = max(1, min(1530, round(error / 56)))
        elif abs(error) > 180 or pad + error < 0:
            pairs = max(1, min(1530, pairs + round(error / 56)))
            pad = 0
        else:
            desired = max(0, min(260, pad + error))
            choices = sorted((v for v in range(261) if representable_pad(v) and (pairs, v) not in tried),
                             key=lambda v: (abs(v - desired), v))
            if not choices:
                raise RuntimeError('no untried phase pad remains')
            pad = choices[0]
        if (pairs, pad) in tried:
            pairs = max(1, pairs - 1)
            pad = 52
        if (pairs, pad) in tried:
            raise RuntimeError('phase calibration failed to make progress')
    raise RuntimeError('phase calibration did not converge within 24 candidates')


def validate(out, fuse, ffmpeg):
    meta = json.loads((out / 'player.json').read_bytes())
    packed = gzip.decompress((out / 'soundtrack.ima.gz').read_bytes())
    ref = partial(reference, model=meta['model'], idle_pairs=meta['loop_idle_pairs'])
    save(out / 'native.json', native_check((out / 'audiobook-preview.trd').read_bytes(), meta, packed, ref, intervals))
    result = fuse_check(fuse, out, meta, packed, False, ref, intervals)
    save(out / 'fuse.json', result)
    periods = [round(t * CPU) for t in result['cycle_durations_seconds']]
    target = round(periods[1] / FIELD) * FIELD
    phase_deltas = [t - target for t in periods]
    if abs(phase_deltas[0]) > 3 or phase_deltas[1] != 0:
        raise RuntimeError(f'complete cold trace failed repeat-phase check: {phase_deltas}')
    quality = [analyze(out, ffmpeg, loop=i) for i in range(2)]
    values = [q['fixed_mean_clock_total_snr_db'] for q in quality]
    # Silent input has no signal/noise ratio. Keep null, rather than NaN/Infinity.
    score = min(values) if all(v is not None and math.isfinite(v) for v in values) else None
    outcome = dict(two_loop_clock_aware_snr_db=values, minimum_snr_db=score,
                   snr_at_least_20_db=score is not None and score >= 20,
                   mean_prepared_sample_rate_hz=result['average_pcm_rate_hz'],
                   mean_speed_error_percent=(result['average_pcm_rate_hz'] / RATE - 1) * 100,
                   speed_within_two_percent=abs(result['average_pcm_rate_hz'] / RATE - 1) <= .02,
                   reference_rate_hz=RATE, physical_hardware_tested=False)
    outcome['complete_trace_phase_deltas_tstates'] = phase_deltas
    save(out / 'quality.json', outcome)
    print(json.dumps(dict(verified_variant=str(out), **outcome)), flush=True)
    return outcome


def independent_ima_check(packed, ffmpeg):
    pcm, indices = decode(packed)
    for start in range(0, len(packed), 30000):
        chunk = packed[start:start + 30000]
        predictor = int(pcm[start * 2 - 1]) if start else 0
        index = int(indices[start * 2 - 1]) if start else 0
        run = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'wav', '-i', '-', '-f', 's16le', '-'],
                             input=verification_wav(chunk, predictor, index), capture_output=True, check=True)
        assert np.array_equal(np.frombuffer(run.stdout, '<i2'), np.r_[predictor, pcm[start * 2:(start + len(chunk)) * 2]])
    return dict(decoder='FFmpeg IMA WAV', samples=len(pcm), every_sample_exact=True)


def convert(args):
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output must be empty; existing conversions are never overwritten')
    out.mkdir(parents=True, exist_ok=True)
    producer_hashes = snapshot_sources(out)
    if getattr(args, 'prepared_pcm', False):
        if args.duration is not None:
            raise ValueError('--prepared-pcm cannot be combined with --duration')
        source, source_meta = prepared_ima4_source(args.input.resolve())
    else:
        source, source_meta = prepare_source(args.input.resolve(), args.ffmpeg, args.duration)
    save(out / 'input.json', source_meta)
    print(json.dumps(source_meta), flush=True)
    packed = encode(source)
    pilot, meta = calibrate(out / 'pilot', packed, source, args.fuse)
    pilot_quality = validate(pilot, args.fuse, args.ffmpeg)
    pcm_wav(pilot / 'compensated-pcm.wav', source)  # Identity transform candidate.
    variants = [dict(directory=str(pilot.relative_to(out)), **pilot_quality)]
    hot = meta['hot_indices']
    for iteration in range(args.iterations):
        times = np.frombuffer(gzip.decompress((pilot / 'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
        boundaries = times[sample_positions(meta)]
        target = compensate(source, boundaries, period=CPU / RATE)
        packed = encode(target)
        folder = out / f'compensated-{iteration + 1}'
        variant, new_meta = calibrate(folder, packed, source, args.fuse, hot)
        pcm_wav(variant / 'compensated-pcm.wav', target)
        result = validate(variant, args.fuse, args.ffmpeg)
        variants.append(dict(directory=str(variant.relative_to(out)), **result))
        save(out / 'variants.json', variants)
        pilot, meta = variant, new_meta
        if (result['minimum_snr_db'] is not None and result['minimum_snr_db'] >= getattr(args,'target_snr',20.)
                and result['speed_within_two_percent']):
            break
    quality_profile = getattr(args, 'quality', 'best')
    hosts = []
    if quality_profile == 'best' and np.any(source != 128):
        # Keep the verified legacy candidates as fallbacks. Optimize against
        # the best one's actual clock; never borrow an IMA3 output schedule.
        baseline = max((r for r in variants if r['speed_within_two_percent']),
                       key=lambda r: r['minimum_snr_db'] if r['minimum_snr_db'] is not None else -math.inf)
        clock = out/baseline['directory']
        clock_meta = json.loads((clock/'player.json').read_bytes())
        for number, (width, weight, horizon) in enumerate(search_plan('ima4', quality_profile, getattr(args,'attempts',3)), 1):
            folder = out/f'encode-{number}'
            estimate = host_search(clock, folder, width, weight, horizon, args.ffmpeg, 'ima4')
            hosts.append(dict(directory=folder.name, **estimate))
            save(out/'host-search.json', hosts)
        for host in ranked_hosts(hosts, limit=len(hosts)):
            packed = gzip.decompress((out/host['directory']/'soundtrack.ima.gz').read_bytes())
            variant, new_meta = calibrate(out/f'disk-{host["directory"]}', packed, source, args.fuse, clock_meta['hot_indices'])
            result = validate(variant, args.fuse, args.ffmpeg)
            times = np.frombuffer(gzip.decompress((variant/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
            target = compensate(source, times[sample_positions(new_meta)], period=CPU/RATE)
            pcm_wav(variant/'compensated-pcm.wav', target)
            variants.append(dict(directory=str(variant.relative_to(out)), **result))
            save(out/'variants.json', variants)
        # Re-estimate once on the winner's *new* ULA timeline. Four-bit
        # decoding places some rows in contended RAM, so changing codes can
        # invalidate the pilot's pulse spacing even with identical CPU cost.
        winner = max((r for r in variants if r['speed_within_two_percent']),
                     key=lambda r:r['minimum_snr_db'] if r['minimum_snr_db'] is not None else -math.inf)
        prefix = Path(winner['directory']).parts[0]
        chosen = next((h for h in hosts if prefix == 'disk-'+h['directory']), None)
        if chosen is not None and getattr(args,'refine_clock',True):
            clock = out/winner['directory']; clock_meta=json.loads((clock/'player.json').read_bytes())
            folder=out/'encode-refined'
            estimate=host_search(clock,folder,chosen['beam_width'],chosen['control_regularization'],
                                 chosen['block_size'],args.ffmpeg,'ima4')
            hosts.append(dict(directory=folder.name,**estimate));save(out/'host-search.json',hosts)
            packed=gzip.decompress((folder/'soundtrack.ima.gz').read_bytes())
            if packed != gzip.decompress((clock/'soundtrack.ima.gz').read_bytes()):
                variant,new_meta=calibrate(out/'disk-refined',packed,source,args.fuse,clock_meta['hot_indices'])
                result=validate(variant,args.fuse,args.ffmpeg)
                times=np.frombuffer(gzip.decompress((variant/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
                pcm_wav(variant/'compensated-pcm.wav',compensate(source,times[sample_positions(new_meta)],period=CPU/RATE))
                variants.append(dict(directory=str(variant.relative_to(out)),**result));save(out/'variants.json',variants)
    eligible = [r for r in variants if r['speed_within_two_percent']]
    if not eligible:
        raise RuntimeError('no variant meets the required +/-2% mean playback speed')
    best = max(eligible, key=lambda r: r['minimum_snr_db'] if r['minimum_snr_db'] is not None else -math.inf)
    selected = out / best['directory']
    for name in ('player.json', 'audiobook-preview.trd', 'soundtrack.ima.gz', 'source-preview.wav', 'compensated-pcm.wav',
                 'native.json', 'fuse.json', 'output-times.u32.gz', 'quality.json', 'voice-jitter.json',
                 'loop-2-voice-jitter.json', 'clock-aware-output-preview.wav', 'uniform-clock-source-preview.wav'):
        shutil.copy2(selected / name, out / name)
    shutil.copytree(selected / 'assembly', out / 'assembly')
    packed = gzip.decompress((out / 'soundtrack.ima.gz').read_bytes())
    independent = independent_ima_check(packed, args.ffmpeg)
    recording = None
    if not args.no_recording:
        subprocess.run([sys.executable, str(HERE / 'record_pcm.py'), str(out), '--fuse', str(args.fuse),
                        '--output', str(out / 'sound-128'), '--machine', '128'], check=True)
        recording = json.loads((out / 'sound-128' / 'report.json').read_bytes())
        assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
        shutil.copy2(out / 'sound-128' / 'fuse-preview.wav', out / 'result-preview.wav')
    else:
        shutil.copy2(out / 'clock-aware-output-preview.wav', out / 'result-preview.wav')
    target_snr = getattr(args, 'target_snr', 20.)
    passed = best['speed_within_two_percent'] and (not np.any(source != 128) or
             best['minimum_snr_db'] is not None and best['minimum_snr_db'] >= target_snr)
    report = dict(date=date.today().isoformat(), complete=True, preview_only=not passed,
                  quality_gate_passed=passed,target_snr_db=target_snr,
                  profile='IMA4 / measured direct PDM / bounded waveform search' if quality_profile=='best' else 'IMA4 / legacy PCM beam32 and clock compensation',
                  quality_profile=quality_profile,host_search=hosts,
                  source=source_meta, selected_variant=best, variants=variants, independent_ima=independent,
                  recording=recording, wav_scope=('Actual Fuse sound generator, two loops' if recording else 'Integrated Fuse port events with measurement filter'),
                  trd_sha256=hashlib.sha256((out / 'audiobook-preview.trd').read_bytes()).hexdigest(),
                  source_sha256_lf=producer_hashes,
                  timing=dict(ordinary_native_tstates=423, delta_from_verified_player=0,
                              source_reference_rate_hz=RATE, physical_hardware_tested=False),
                  limitations=['8-kHz mono PCM8 reference; quality is not measured against full-band original input',
                               'Bounded search over the verified IMA architecture, not a universal codec optimum',
                               '20-dB end-to-end goal passes only when measured on both loops'])
    save(out / 'report.json', report)
    print(json.dumps(dict(disk=str(out / 'audiobook-preview.trd'), **best)), flush=True)
    return report


def legacy_main(argv=None, *, parents=()):
    parser = argparse.ArgumentParser(description='Four-bit IMA/direct-PDM looping preview with waveform optimization.', parents=list(parents), allow_abbrev=False)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--duration', type=float, help='keep at most this many initial seconds; always bounded by RAM')
    parser.add_argument('--iterations', type=int, choices=(1, 2), default=2)
    parser.add_argument('--quality',choices=('best','balanced'),default='best',
                        help='best: complete all requested waveform searches and verify each; balanced: legacy PCM search')
    parser.add_argument('--attempts',type=int,choices=(1,2,3),default=3,
                        help='bounded full waveform searches in best mode (default 3)')
    parser.add_argument('--target-snr',type=float,default=20.)
    parser.add_argument('--no-refine-clock',dest='refine_clock',action='store_false',
                        help='omit the final four-bit search on the measured candidate clock')
    parser.add_argument('--prepared-pcm', action='store_true', help='retain exact mono PCM8/8k levels; require RAM-sized, 512-aligned samples with a final 128-sample silent guard')
    parser.add_argument('--no-recording', action='store_true', help='skip normal-speed audible capture; keep complete native/cold-Fuse verification')
    args = parser.parse_args(argv)
    if not math.isfinite(args.target_snr) or not 20 <= args.target_snr <= 60:
        parser.error('target SNR must be 20..60 dB')
    if not args.ffmpeg:
        parser.error('FFmpeg not found; supply --ffmpeg')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be empty; existing conversions are never overwritten')
    try:
        report = convert(args)
    except Exception as error:
        if args.output.exists():
            save(args.output / 'failure.json', dict(complete=False, error=str(error), type=type(error).__name__))
        raise
    if args.quality == 'best' and not report['quality_gate_passed']:
        raise SystemExit(2)


def main(argv=None):
    # Route the generic entry point before parsing profile-specific flags.
    # Imports of preparation helpers must never launch a conversion.
    selector = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    selector.add_argument('--codec', choices=('ima3', 'ima4', 'mulaw', 'ulaw'), default='ima3',
                          help='ima3 (default): accepted packed IMA3; ima4: four-bit preview; mulaw/ulaw: compact G.711 eight-bit preview')
    selected, remaining = selector.parse_known_args(argv)
    selector.set_defaults(codec=selected.codec)
    if selected.codec == 'ima4':
        return legacy_main(remaining, parents=(selector,))
    if selected.codec in ('mulaw', 'ulaw'):
        from convert_mulaw_audio import main as mulaw_main
        return mulaw_main(remaining, parents=(selector,))
    from convert_ima3_audio import main as ima3_main
    return ima3_main(remaining, parents=(selector,))


if __name__ == '__main__':
    main()
