"""Canonical PCM-to-AY analysis shared by audio and movie entry points.

Only this folder owns synthesis. The movie bridge invokes encode_pcm.py in
an isolated Python process, so older toolkit modules cannot shadow this core.
Every exported state lasts one 50-Hz field; disk layout belongs to the caller.
"""
import gzip
import json
from pathlib import Path
import numpy as np
import ay_fidelity as ay
from ay_format import AyFrame, registers as frame_registers
from support import save


def encode(samples, node, output, *, profile='auto', start_tick=0, ticks=None,
           noise_fit='chip', noise_steps=1, tuning_cents=50, cache_dir=None):
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all():
        raise ValueError('expected finite mono PCM')
    if profile not in ('legacy', 'music', 'auto'):
        raise ValueError('unknown audio profile')
    rate = 22050
    count = (len(samples)+440)//441
    samples = np.pad(samples, (0,count*441-len(samples)))
    ticks = count-start_tick if ticks is None else ticks
    if start_tick < 0 or ticks < 1 or start_tick+ticks > count:
        raise ValueError('invalid 20-ms source interval')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    if profile in ('music', 'auto'):
        import music_profile
        periods, volumes, notes, noise, explained, fit = music_profile.convert(samples, rate)
    else:
        magnitude, rms = ay.spectra(samples, rate, 50, count)
        periods, volumes, notes, noise, explained, fit = ay.arrange_for_chip(magnitude, rms, rate, noise_steps=noise_steps, tuning_cents=tuning_cents)
    lo = start_tick
    first = lo*441
    if profile in ('music', 'auto') and noise_fit == 'chip':
        import noise_colour
        initial = b''.join(frame_registers(AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),int(m)))
            for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],fit['mixers'][lo:lo+ticks]))
        fitted,noise_fit = noise_colour.optimize(samples[first:first+ticks*441],initial,node,work_parent=out)
        rows = np.frombuffer(fitted,dtype=np.uint8).reshape(-1,11)
        noise[lo:lo+ticks] = rows[:,6]
        volumes[lo:lo+ticks] = rows[:,8:]
        (out/'noise-fit.json.gz').write_bytes(gzip.compress(json.dumps(noise_fit,separators=(',',':')).encode(),mtime=0))
        fit['noise_colour_fit'] = {k:v for k,v in noise_fit.items() if k != 'states'}
        fit['noise_colour_fit_file'] = 'noise-fit.json.gz'
        fit['model'] = 'persistent_components_and_chip_noise_colour_v3'
    if profile == 'auto':
        import mixer_fit
        initial = b''.join(frame_registers(AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),int(m)))
            for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],fit['mixers'][lo:lo+ticks]))
        fitted, mixer_info = mixer_fit.optimize(samples[first:first+ticks*441], initial, node,
            tone_volumes=fit['base_tone_volumes'][lo:lo+ticks],
            noise_shares=fit['noise_shares'][lo:lo+ticks], carriers=fit['noise_carriers'][lo:lo+ticks],
            work_parent=out, cache_dir=cache_dir if cache_dir is not None else Path(__file__).parent/'.cache/mixer')
        rows = np.frombuffer(fitted, np.uint8).reshape(-1,11)
        noise[lo:lo+ticks], volumes[lo:lo+ticks] = rows[:,6], rows[:,8:]
        fit['mixers'][lo:lo+ticks] = rows[:,7].astype(int).tolist()
        (out/'mixer-fit.json.gz').write_bytes(gzip.compress(json.dumps(mixer_info,separators=(',',':')).encode(),mtime=0))
        fit['automatic_mixer_fit'] = {k:v for k,v in mixer_info.items() if k != 'states'}
        fit['automatic_mixer_fit_file'] = 'mixer-fit.json.gz'
        fit['model'] = 'persistent_components_and_automatic_mixer_v4'
    mixers = fit.pop('mixers', [None]*len(periods))
    component_tracks = fit.pop('component_tracks', None)
    if component_tracks is not None:
        shares = fit.pop('noise_shares')
        carriers = fit.pop('noise_carriers')
        base_volumes = fit.pop('base_tone_volumes')
        states = [dict(tick=i-lo, component_ids=component_tracks[i],
                       periods=list(map(int,periods[i])), volumes=list(map(int,volumes[i])),
                       tone_volumes=base_volumes[i], mixer=int(mixers[i]),
                       noise_period=int(noise[i]), noise_share=float(shares[i]),
                       noise_channel=next((c for c in range(3) if noise[i] and
                           not mixers[i] & (1 << (c+3))), -1)) for i in range(lo,lo+ticks)]
        (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(dict(
            quantum_ms=20,update_rate_hz=50,states=states),separators=(',',':')).encode(),mtime=0))
        fit['channel_states_file'] = 'channel-states.json.gz'
        fit['analysis_context_component_count'] = fit['component_count']
        fit['component_count'] = len({track for state in states for track in state['component_ids'] if track})
        fit['noise_ticks'] = sum(bool(state['noise_period']) for state in states)
        fit['tone_plus_noise_ticks'] = sum(any(state['volumes'][c] and not state['mixer'] & (1 << c) and not state['mixer'] & (1 << (c+3)) for c in range(3)) for state in states)
        fit['noise_only_ticks'] = fit['noise_ticks']-fit['tone_plus_noise_ticks']
    if profile in ('music', 'auto'):
        # Analysis includes context; exported note intervals refer only to the
        # selected excerpt, with integer ticks and exclusive end boundaries.
        events = []
        for event in fit.pop('note_events'):
            start, end = max(lo, event['start_tick']), min(lo+ticks, event['end_tick'])
            if start < end:
                events.append(dict(event, start_tick=start-lo, end_tick=end-lo))
        save(out/'note-events.json', dict(update_rate_hz=50, quantum_ms=20,
             duration_ticks=ticks, end_tick_exclusive=True, estimated_not_ground_truth=True, events=events))
        fit['note_events_file'] = 'note-events.json'
    frames = [AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),None if m is None else int(m))
              for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],mixers[lo:lo+ticks])]
    if len(frames) != ticks:
        raise AssertionError('wrong exported state count')
    from spectral_patterns import stats
    fit['spectral_pattern_cache'] = stats()
    fit.update(profile=profile, shared_core='ay-converter/engine.py',
               update_rate_hz=50, sound_quantum_ms=20)
    return frames, fit
