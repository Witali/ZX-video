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
           noise_fit='chip', noise_steps=1, tuning_cents=50, cache_dir=None,
           mixer_search='fast', simulation_feedback=True, hardware_envelopes=True,
           chip='AY-3-8910',dynamics='compact'):
    import chip_model
    with chip_model.select(chip):
        return _encode(samples,node,output,profile=profile,start_tick=start_tick,ticks=ticks,
            noise_fit=noise_fit,noise_steps=noise_steps,tuning_cents=tuning_cents,cache_dir=cache_dir,
            mixer_search=mixer_search,simulation_feedback=simulation_feedback,hardware_envelopes=hardware_envelopes,dynamics=dynamics)


def _encode(samples, node, output, *, profile='auto', start_tick=0, ticks=None,
           noise_fit='chip', noise_steps=1, tuning_cents=50, cache_dir=None,
           mixer_search='fast', simulation_feedback=True, hardware_envelopes=True,dynamics='compact'):
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
    normalization = None
    if profile == 'auto':
        if mixer_search not in ('fast', 'full'):
            raise ValueError('mixer_search must be fast or full')
        import pcm_levels
        samples,normalization=pcm_levels.process(samples,start_tick,ticks,dynamics=dynamics)
        save(out/'pcm-level.json', normalization)
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
        if mixer_search == 'fast':
            import fast_mixer
            optimize_mixer = fast_mixer.optimize
        else:
            optimize_mixer = mixer_fit.optimize
        initial = b''.join(frame_registers(AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),int(m)))
            for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],fit['mixers'][lo:lo+ticks]))
        fitted, mixer_info = optimize_mixer(samples[first:first+ticks*441], initial, node,
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
        fit['input_normalization'] = normalization
        if simulation_feedback:
            import simulation_refine
            fitted, feedback = simulation_refine.optimize(samples[first:first+ticks*441], fitted,
                node, work_parent=out, tuning_cents=tuning_cents)
            rows = np.frombuffer(fitted, np.uint8).reshape(-1, 11)
            periods[lo:lo+ticks] = rows[:, :6:2].astype(int)+(rows[:, 1:6:2].astype(int) << 8)
            noise[lo:lo+ticks], volumes[lo:lo+ticks] = rows[:, 6], rows[:, 8:]
            fit['mixers'][lo:lo+ticks] = rows[:, 7].astype(int).tolist()
            save(out/'simulation-feedback.json', feedback)
            fit['simulation_feedback'] = feedback
            fit['model'] = 'persistent_components_and_perceptual_chip_feedback_v5'
        import noise_gate
        fitted,noise_policy=noise_gate.optimize(samples[first:first+ticks*441],fitted,node,
            noise_shares=fit['noise_shares'][lo:lo+ticks],work_parent=out,
            calibration_gain=fit.get('simulation_feedback',{}).get('fixed_model_gain'))
        save(out/'necessary-noise.json',noise_policy)
        fit['necessary_noise']=noise_policy
        rows=np.frombuffer(fitted,np.uint8).reshape(-1,11)
        volumes[lo:lo+ticks]=rows[:,8:11]
        fit['mixers'][lo:lo+ticks]=rows[:,7].astype(int).tolist()
        if hardware_envelopes:
            import hardware_envelope
            fitted, envelope_info = hardware_envelope.optimize(samples[first:first+ticks*441],fitted,
                node,work_parent=out,calibration_gain=fit.get('simulation_feedback',{}).get('fixed_model_gain'))
            save(out/'hardware-envelope.json',envelope_info)
            fit['hardware_envelope'] = envelope_info
            if envelope_info.get('selected'):
                rows = np.frombuffer(fitted,np.uint8).reshape(-1,14)
                volumes[lo:lo+ticks] = rows[:,8:11]
                fit['mixers'][lo:lo+ticks] = rows[:,7].astype(int).tolist()
                fit['model'] = 'persistent_components_and_running_hardware_envelope_v6'
        if simulation_feedback:
            width=14 if fit.get('hardware_envelope',{}).get('selected') else 11
            fitted,final_feedback=simulation_refine.optimize(samples[first:first+ticks*441],fitted,node,
                work_parent=out,register_bytes=width,calibration_gain=feedback['fixed_model_gain'],tuning_cents=tuning_cents)
            save(out/'final-feedback.json',final_feedback)
            fit['final_feedback']=final_feedback
            rows=np.frombuffer(fitted,np.uint8).reshape(-1,width)
            periods[lo:lo+ticks]=rows[:,:6:2].astype(int)+(rows[:,1:6:2].astype(int)<<8)
            noise[lo:lo+ticks],volumes[lo:lo+ticks]=rows[:,6],rows[:,8:11]
            fit['mixers'][lo:lo+ticks]=rows[:,7].astype(int).tolist()
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
        if profile=='auto' and fit.get('hardware_envelope',{}).get('selected'):
            for state,row in zip(states,rows):
                state.update(envelope_period=int(row[11])+(int(row[12])<<8),
                    envelope_shape_write=int(row[13]),envelope_channels=[c for c in range(3) if row[8+c]&16])
        (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(dict(
            quantum_ms=20,update_rate_hz=50,states=states),separators=(',',':')).encode(),mtime=0))
        fit['channel_states_file'] = 'channel-states.json.gz'
        fit['analysis_context_component_count'] = fit['component_count']
        fit['component_count'] = len({track for state in states for track in state['component_ids'] if track})
        fit['noise_ticks'] = sum(any(state['volumes'][c] and not state['mixer']&(1<<(c+3)) for c in range(3)) for state in states)
        fit['tone_plus_noise_ticks'] = sum(any(state['volumes'][c] and not state['mixer'] & (1 << c) and not state['mixer'] & (1 << (c+3)) for c in range(3)) for state in states)
        fit['noise_only_ticks'] = fit['noise_ticks']-fit['tone_plus_noise_ticks']
    if profile in ('music', 'auto'):
        # Analysis includes context; exported note intervals refer only to the
        # selected excerpt, with integer ticks and exclusive end boundaries.
        events = []
        for event in fit.pop('note_events'):
            start, end = max(lo, event['start_tick']), min(lo+ticks, event['end_tick'])
            if start < end:
                exported = dict(event, start_tick=start-lo, end_tick=end-lo)
                if profile == 'auto' and simulation_feedback:
                    values = periods[start:end, event['voice']]
                    exported.update(rendered_period_range=[int(values.min()), int(values.max())],
                                    pitch_held=bool(np.all(values == values[0])))
                events.append(exported)
        save(out/'note-events.json', dict(update_rate_hz=50, quantum_ms=20,
             duration_ticks=ticks, end_tick_exclusive=True, estimated_not_ground_truth=True, events=events))
        fit['note_events_file'] = 'note-events.json'
    frames = [AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),None if m is None else int(m))
              for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],mixers[lo:lo+ticks])]
    if profile=='auto' and fit.get('hardware_envelope',{}).get('selected'):
        frames = [AyFrame(frame.periods,frame.volumes,frame.noise_period,frame.mixer_override,
            int(row[11])+(int(row[12])<<8),int(row[13]),12) for frame,row in zip(frames,rows)]
    if len(frames) != ticks:
        raise AssertionError('wrong exported state count')
    from spectral_patterns import stats
    fit['spectral_pattern_cache'] = stats()
    fit.update(profile=profile, shared_core='ay-converter/engine.py',
               update_rate_hz=50, sound_quantum_ms=20,packed_state_bytes=frames[0].state_bytes,
               register_bytes_per_state=14 if frames[0].state_bytes==12 else 11)
    import chip_model
    fit['target_chip']=chip_model.current()
    fit['distinct_hardware_envelope_levels']=32 if chip_model.current()=='YM2149' else 16
    fit['player_timing_note']='AY12 resident fields add 192 T without shape restart, 232 T with restart; movie IRQ remains 367+83*n T and AYH2 decoding adds three register checks.'
    return frames, fit
