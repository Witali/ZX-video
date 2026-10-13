"""Choose tone, noise or Boolean tone/noise against actual YM2149 renders.

Search one tracked carrier per state, all 31 shared-noise periods and six
nearby DAC levels. Tone pitches and component channels stay fixed. Continuous
candidate renders include the chip gates, counters, DAC and filters. A final
complete render is essential: the selected R6 path changes the LFSR history.
"""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

import numpy as np

import music_profile
import noise_colour
import spectrogram

HERE = Path(__file__).resolve().parent
DELTAS = (-3, -2, -1, 0, 1, 2)
OPTIONS = [('seed', 0, 0), ('tone', 0, 0)] + [
    (mode, period, delta) for mode in ('noise', 'mixed')
    for delta in DELTAS for period in range(1, 32)]


def choose_path(cost):
    """Viterbi path on the original 20-ms grid, with weak mode/level inertia."""
    if cost.ndim != 2 or cost.shape[1] != len(OPTIONS) or not np.isfinite(cost).all():
        raise ValueError('expected finite costs for every mixer candidate')
    modes = np.array([o[0] for o in OPTIONS])
    periods = np.maximum(1, [o[1] for o in OPTIONS])
    deltas = np.array([o[2] for o in OPTIONS])
    transition = (.3*(modes[:, None] != modes[None, :]) +
                  .1*abs(np.log2(periods[:, None]/periods[None, :])) +
                  .12*abs(deltas[:, None]-deltas[None, :]))
    previous, history = cost[0].copy(), []
    for row in cost[1:]:
        edges = previous[:, None]+transition
        best = edges.argmin(axis=0)
        history.append(best)
        previous = row+edges[best, np.arange(len(OPTIONS))]
    path = np.empty(len(cost), dtype=int)
    path[-1] = previous.argmin()
    for t in range(len(cost)-2, -1, -1):
        path[t] = history[t][path[t+1]]
    return path


def apply_choices(raw, tones, route, selected):
    result = raw.copy()
    for t, choice in enumerate(selected):
        mode, period, delta = OPTIONS[int(choice)]
        if mode == 'seed':
            continue
        result[t] = tones[t]
        if mode == 'tone' or not route['eligible'][t]:
            continue
        c = route['carriers'][t]
        result[t, 6] = period
        result[t, 7] &= np.uint8(63 ^ (1 << (c+3)))
        if mode == 'noise':
            result[t, 7] |= 1 << c
        result[t, 8+c] = np.clip(route['levels'][t]+delta, 1, 15)
    return result


def mode_counts(raw):
    counts = dict(tone=0, noise=0, mixed=0, silent=0)
    for row in raw:
        for c in range(3):
            if not row[8+c]:
                counts['silent'] += 1
                continue
            tone, noise = not row[7] & (1 << c), not row[7] & (1 << (c+3))
            counts['mixed' if tone and noise else 'tone' if tone else 'noise' if noise else 'silent'] += 1
    return counts


def cache_key(samples, registers, tone_volumes, noise_shares, carriers, node):
    """Exact context cache; nearby spectra never authorize an unchecked reuse.

    Include the full PCM context, registers, routing, interpreter/renderer
    versions and all analysis sources. Models start from Ayumi's documented
    initial state; no live hardware/LFSR state is cached or reset by playback.
    """
    digest = hashlib.sha256()
    for array, dtype in [(samples, '<f8'), (tone_volumes, 'u1'),
                         (noise_shares, '<f8'), (carriers, '<i4')]:
        data = np.asarray(array, dtype=dtype)
        digest.update(str(data.shape).encode())
        digest.update(data.tobytes())
    digest.update(registers)
    import chip_model
    digest.update(chip_model.current().encode())
    digest.update(np.__version__.encode())
    digest.update(subprocess.check_output([str(node), '--version']))
    for source in [*sorted(HERE.glob('*.py')), *sorted(HERE.glob('*.js')),
                   HERE/'vendor/ayumi-js/ayumi.js']:
        digest.update(source.name.encode())
        digest.update(source.read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def optimize(samples, registers, node, *, tone_volumes, noise_shares, carriers,
             work_parent=None, cache_dir=None):
    started = time.perf_counter()
    path = None
    if cache_dir is not None:
        key = cache_key(samples, registers, tone_volumes, noise_shares, carriers, node)
        path = Path(cache_dir)/f'{key}.json.gz'
        if path.exists():
            cached = json.loads(gzip.decompress(path.read_bytes()))
            result = bytes.fromhex(cached['registers'])
            if (cached.get('key') == key and len(result) == len(registers) and
                    hashlib.sha256(result).hexdigest() == cached.get('registers_sha256')):
                info = cached['info']
                info.update(cache_hit=True, cache_key=key, elapsed_seconds=time.perf_counter()-started)
                return result, info
    result, info = _optimize(samples, registers, node, tone_volumes=tone_volumes,
                             noise_shares=noise_shares, carriers=carriers, work_parent=work_parent)
    info.update(cache_hit=False, elapsed_seconds=time.perf_counter()-started)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        info['cache_key'] = key
        cached = dict(key=key, registers=result.hex(), info=info,
                      registers_sha256=hashlib.sha256(result).hexdigest())
        # Atomic replace prevents an interrupted write becoming a usable entry.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(gzip.compress(json.dumps(cached).encode(), mtime=0))
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    return result, info


def _optimize(samples, registers, node, *, tone_volumes, noise_shares, carriers,
              work_parent=None):
    raw = np.frombuffer(registers, np.uint8).reshape(-1, 11).copy()
    samples = np.asarray(samples, dtype=float)
    count = len(raw)
    volumes = np.asarray(tone_volumes, dtype=np.uint8)
    shares = np.asarray(noise_shares, dtype=float)
    if (not count or len(samples) != count*441 or volumes.shape != (count, 3) or
            shares.shape != (count,) or len(carriers) != count or not np.isfinite(samples).all()):
        raise ValueError('expected aligned finite 22050-Hz PCM and whole 20-ms states')
    tones = raw.copy()
    tones[:, 6:8] = [0, 0x38]
    tones[:, 8:] = volumes
    rms = np.sqrt(np.mean(samples.reshape(-1, 441)**2, axis=1))
    # Candidate evaluation also covers quieter broadband evidence rejected by
    # the original event threshold. Exact source silence must remain silent.
    eligible = (rms > 10**(-55/20)) & ((shares > .04) | (raw[:, 6] > 0))
    route = np.asarray(carriers, dtype=int).copy()
    route[route < 0] = volumes[route < 0].argmin(axis=1)
    if np.any((route < 0) | (route > 2)):
        raise ValueError('invalid noise carrier')
    levels = raw[np.arange(count), 8+route].astype(int)
    table = music_profile.chip_levels()
    estimated = np.clip(.85*rms/max(float(np.percentile(rms, 98)), 1e-12), 0, 1)
    fallback = abs(estimated[:, None]-table).argmin(axis=1)
    levels[levels == 0] = fallback[levels == 0]
    routing = dict(carriers=route.tolist(), levels=levels.tolist(), eligible=eligible.tolist())
    info = dict(model='automatic_boolean_mixer_fit_v1', update_rate_hz=50,
                quantum_ms=20, candidate_count=len(OPTIONS), noise_period_range=[1, 31],
                shared_volume_deltas=list(DELTAS), eligible_ticks=int(eligible.sum()),
                modes=['tone', 'noise', 'mixed'], routing='one tracked noise carrier per state',
                tone_periods_changed=0, component_channel_migrations=0,
                native_instruction_delta_tstates=0,
                limitations='Bounded search with one carrier, fixed tracked pitches and nearby shared DAC levels; no independent tone/noise gains. Candidate LFSR histories differ from the final sequence. Metrics are not perceptual fidelity.')
    if not eligible.any():
        return registers, dict(info, skipped='no broadband evidence', modes_before=mode_counts(raw),
                               modes_after=mode_counts(raw), changed_ticks=0)
    cost = np.empty((count, len(OPTIONS)))
    ticks = np.arange(count)
    parts = [(start, min(start+128, count)) for start in range(0, count, 128)]
    references = [[noise_colour.spectra_at(samples, ticks[a:b], size) for a, b in parts]
                  for size in noise_colour.SIZES]
    floors = [max(max(float(p.max()) for p in ref)*.001, 1e-15) for ref in references]
    with tempfile.TemporaryDirectory(prefix='ay-mixer-', dir=work_parent) as temporary:
        root = Path(temporary)
        for name, rows in [('seed', raw), ('tones', tones)]:
            (root/f'{name}.gz').write_bytes(gzip.compress(rows.tobytes(), mtime=0))
        (root/'route.json').write_text(json.dumps(routing), encoding='utf-8')

        def render(rows, name):
            path = root/f'{name}.gz'
            path.write_bytes(gzip.compress(rows.tobytes(), mtime=0))
            subprocess.run([str(node), str(HERE/'render_ym2149.js'), str(path),
                            str(root/f'{name}.f32'), '50', str(root/f'{name}.json')], check=True)
            audio = noise_colour.downsample(np.fromfile(root/f'{name}.f32', '<f4').astype(float))
            if len(audio) != len(samples) or not np.isfinite(audio).all():
                raise ValueError('invalid complete chip render')
            return audio

        baseline = render(raw, 'baseline')
        gain = float(np.sqrt(np.mean(samples**2)/max(np.mean(baseline**2), 1e-20)))

        def score(audio):
            result = np.empty(count)
            for part, (a, b) in enumerate(parts):
                errors = []
                for size, ref, floor in zip(noise_colour.SIZES, references, floors):
                    observed = noise_colour.spectra_at(audio*gain, ticks[a:b], size)
                    wanted = ref[part]
                    support = (wanted > floor) | (observed > floor)
                    error = abs(20*np.log10(np.maximum(wanted, floor)/np.maximum(observed, floor)))
                    errors.append((error*support).sum(axis=1)/np.maximum(support.sum(axis=1), 1))
                result[a:b] = np.mean(errors, axis=0)
            return result

        cost[:, 0] = score(baseline)
        pure = render(tones, 'pure-tone')
        cost[:, 1] = score(pure)
        for mode in ('noise', 'mixed'):
            for delta in DELTAS:
                print(f'AY mixer: {mode}, shared volume delta {delta}, 31 periods', flush=True)
                subprocess.run([str(node), str(HERE/'render_mixer_candidates.js'),
                                str(root/'seed.gz'), str(root/'tones.gz'), str(root/'route.json'),
                                str(root), mode, str(delta)], check=True)
                for period in range(1, 32):
                    path = root/f'candidate-{period}.f32'
                    audio = noise_colour.downsample(np.fromfile(path, '<f4').astype(float))
                    path.unlink()
                    index = OPTIONS.index((mode, period, delta))
                    cost[:, index] = score(audio)
                    if mode == 'mixed':
                        # No invented tonal fundamental on an unvoiced carrier.
                        cost[(volumes[np.arange(count), route] == 0) & eligible, index] = 1e6
        selected = choose_path(cost)
        proposal = apply_choices(raw, tones, routing, selected)
        proposed_audio = render(proposal, 'proposal')
        # The acceptance evaluator uses unpooled FFT bins and the final whole
        # stream, rather than the search's smoothed candidate costs. Keep the
        # seed as an explicit fallback when stochastic phase invalidates a gain.
        reference = spectrogram.features(samples)
        measures = {name: spectrogram.compare(reference, spectrogram.features(audio))
                    for name, audio in [('seed', baseline), ('tone', pure), ('automatic', proposed_audio)]}
        errors = {name: float(np.mean([p['log_magnitude_mae_db'] for p in metrics.values()]))
                  for name, metrics in measures.items()}
        decision = min(errors, key=errors.get)
        result = {'seed': raw, 'tone': tones, 'automatic': proposal}[decision]
        info.update(global_source_model_rms_gain=gain, final_decision=decision,
                    final_multiresolution_log_mae_db=errors, final_metrics=measures,
                    mean_selected_candidate_error_db=float(cost[np.arange(count), selected].mean()),
                    modes_before=mode_counts(raw), modes_after=mode_counts(result),
                    changed_ticks=int(np.any(raw != result, axis=1).sum()),
                    states=[dict(tick=int(t), candidate=OPTIONS[int(c)], carrier=int(route[t]),
                                 candidate_error_db=float(cost[t, c]), mixer=int(result[t, 7]),
                                 noise_period=int(result[t, 6]), volumes=result[t, 8:].tolist())
                            for t, c in enumerate(selected)])
        return result.tobytes(), info
