"""Persistent tonal components and independently detected AY noise at 50 Hz.

Channel assignment uses pitch continuity, never current amplitude rank.
AY has one shared noise generator and Boolean tone/noise gates: enabling
noise on an occupied channel preserves its tone but is not an independent
fourth voice. Fit that channel's shared volume to this physical limitation.
"""
from itertools import permutations
import numpy as np
import ay_fidelity as ay
import ay_square_fit as fit
import music_profile as music


def dominant_notes(amplitude, rms, explained):
    """Three strong harmonic components, with a small retention hysteresis.

    These are fitted fundamentals, not the three loudest raw FFT harmonics.
    A 15% continuity bonus prevents tiny rank fluctuations selecting a new
    fourth component. It does not force an inaudible component to survive.
    """
    output = np.full((len(amplitude),3),-1,dtype=int)
    previous = []
    for tick, row in enumerate(amplitude):
        if rms[tick] < 10**(-65/20) or explained[tick] < .12:
            previous = []
            continue
        score = row.copy()
        for note in previous:
            score[abs(ay.NOTES-note) <= 1] *= 1.15
        chosen = []
        for _ in range(3):
            index = int(np.argmax(score))
            if row[index] < max(float(row.max())*.06,1e-12) or score[index] <= 0:
                break
            note = int(ay.NOTES[index])
            chosen.append(note)
            score[abs(ay.NOTES-note) <= 1] = 0
        output[tick,:len(chosen)] = sorted(chosen)
        previous = chosen
    return output


def assign_channels(notes, strengths, gate_semitones=2.):
    """Match all permutations by pitch before assigning new component IDs.

    Small pitch motion retains the old ID/channel even if amplitudes swap
    order. An unmatched old component ends; a new component takes a free
    slot. No spectral method can identify two exactly coincident sources.
    Integer IDs explicitly describe this estimate and permit a no-migration
    invariant independent of the musical score.
    """
    paths = np.full_like(notes,-1)
    levels = np.zeros_like(strengths)
    tracks = np.zeros(notes.shape,dtype=int)
    previous = np.full(3,-1.,dtype=float)
    previous_ids = np.zeros(3,dtype=int)
    previous_delta = np.zeros(3)
    next_id = 1
    for tick, row in enumerate(notes):
        best = None
        predicted = previous+np.clip(previous_delta,-.5,.5)
        for order in permutations(range(3)):
            current = row[list(order)]
            same = (previous >= 0) & (current >= 0)
            distance = abs(current-predicted)
            cost = np.where(same, np.where(abs(current-previous) <= gate_semitones,
                distance, gate_semitones*3), gate_semitones*((previous >= 0) | (current >= 0)))
            key = (float(cost.sum()), order)
            if best is None or key < best[0]:
                best = (key,current,order)
        _,current,order = best
        paths[tick] = current
        levels[tick] = strengths[tick,list(order)]
        ids = np.zeros(3,dtype=int)
        for channel in range(3):
            if current[channel] < 0:
                continue
            if previous[channel] >= 0 and abs(current[channel]-previous[channel]) <= gate_semitones:
                ids[channel] = previous_ids[channel]
            else:
                ids[channel] = next_id
                next_id += 1
        previous_delta = np.where((current >= 0) & (previous >= 0), current-previous, 0.)
        previous,previous_ids = current,ids
        tracks[tick] = ids
    return paths,levels,tracks


def noise_component(magnitude, rms, explained, sample_rate=22050):
    """Estimate broadband residual power and the colour of shared AY noise.

    A frequency median rejects narrow harmonic peaks. Use independent noise
    evidence rather than requiring it to overpower a particular tone voice.
    Hysteresis (.18 on / .12 off) limits threshold chatter at the 20-ms grid.
    """
    frequencies = np.fft.rfftfreq((magnitude.shape[1]-1)*2,1/sample_rate)
    useful = (frequencies >= 150) & (frequencies <= 9000)
    frequency = frequencies[useful]
    templates = np.array([abs(np.sinc(frequency/(ay.AY_CLOCK/(16*n)))) for n in range(1,32)])
    templates /= np.maximum(np.linalg.norm(templates,axis=1,keepdims=True),1e-12)
    share = np.empty(len(magnitude))
    period = np.empty(len(magnitude),dtype=int)
    for start in range(0,len(magnitude),128):
        end = min(start+128,len(magnitude))
        power = magnitude[start:end]**2
        padded = np.pad(power,((0,0),(8,8)),mode='edge')
        floor = np.median(np.lib.stride_tricks.sliding_window_view(padded,17,axis=1),axis=-1)/.7
        broad = np.minimum(power,floor)
        share[start:end] = broad[:,useful].sum(axis=1)/np.maximum(power.sum(axis=1),1e-16)
        period[start:end] = np.argmax(np.sqrt(broad[:,useful])@templates.T,axis=1)+1
    master = rms*np.sqrt(explained)
    peak = max(float(np.percentile(master,98)),float(np.percentile(rms,98))*.1,1e-12)
    level = np.clip(rms*np.sqrt(share)/peak*.85,0,1)
    present = False
    for tick in range(len(period)):
        present = bool(share[tick] > (.12 if present else .18) and
                       rms[tick] > 10**(-55/20) and level[tick] > .02)
        if not present:
            period[tick] = 0
            level[tick] = 0
    return period,level,share


def add_noise(volumes, noise_period, noise_level, table):
    """Keep every active tone enabled, routing each noise event consistently.

    Prefer an unused channel, otherwise choose the closest achievable shared
    tone/noise balance. For uncorrelated binary T,N, TN halves coherent tone
    amplitude and has added noise equivalent to M/sqrt(2) at channel level M.
    The shared volume minimizes 4*(M/2-tone)^2+(M/sqrt(2)-noise)^2. It cannot
    set independent tone/noise levels; report this limitation explicitly.
    """
    result = volumes.copy()
    mixers = np.full(len(volumes),0x38,dtype=int)
    carriers = np.full(len(volumes),-1,dtype=int)
    carrier = -1
    for tick, row in enumerate(volumes):
        if not noise_period[tick]:
            carrier = -1
            continue
        if carrier < 0:
            free = np.flatnonzero(row == 0)
            if len(free):
                carrier = int(free[0])
            else:
                losses = [np.min(4*(table/2-table[v])**2+(table/np.sqrt(2)-noise_level[tick])**2) for v in row]
                carrier = int(np.argmin(losses))
        carriers[tick] = carrier
        mixers[tick] &= ~(1 << (carrier+3))
        if row[carrier]:
            loss = 4*(table/2-table[row[carrier]])**2+(table/np.sqrt(2)-noise_level[tick])**2
        else:
            mixers[tick] |= 1 << carrier
            loss = (table-noise_level[tick])**2
        result[tick,carrier] = int(np.argmin(loss))
    return result,mixers,carriers


def arrange(features, *, selection='dominant', noise_enabled=True):
    amp,rms,explained = (features[k] for k in ('amplitude','rms','explained'))
    onset,mag,rate = (features[k] for k in ('onset','magnitude','sample_rate'))
    if selection == 'dominant':
        notes = dominant_notes(amp,rms,explained)
    elif selection == 'roles':
        _,_,seed = ay.arrange(amp,rms,explained)
        notes = music.joint_paths(amp,rms,explained,seed,onset)
    else:
        raise ValueError('unknown component selection')
    strengths = music.envelopes(notes,amp,features['short_amplitude'],onset,.5)
    paths,strengths,tracks = assign_channels(notes,strengths)
    relative = strengths/np.maximum(np.linalg.norm(strengths,axis=1,keepdims=True),1e-12)
    master = rms*np.sqrt(explained)
    level = np.clip(relative*(master/max(float(np.percentile(master,98)),1e-12)*.85)[:,None],0,1)
    level[(rms < 10**(-65/20)) | (explained < .12)] = 0
    table = music.chip_levels()
    volumes = np.argmin(abs(level[:,:,None]-table[None,None,:]),axis=2)
    periods = np.clip(np.rint(ay.AY_CLOCK/(16*440*2**((np.maximum(paths,33)-69)/12))),1,4095).astype(int)
    periods,volumes,metadata = fit.refine(mag,periods,volumes,np.zeros(len(paths),int),rate,level_table=table)
    periods,events = music.hold_note_pitch(periods,volumes,np.zeros(len(paths),int),paths,onset)
    noise,noise_level,share = noise_component(mag,rms,explained,rate)
    if not noise_enabled:
        noise[:] = 0
        noise_level[:] = 0
    mixed,mixers,carriers = add_noise(volumes,noise,noise_level,table)
    for channel in range(3):
        previous = 1
        for tick in range(len(periods)):
            if volumes[tick,channel]:
                previous = int(periods[tick,channel])
            else:
                periods[tick,channel] = previous
    # Every ID belongs to exactly one hardware channel for its whole life.
    owners = {}
    for row in tracks:
        for channel,track in enumerate(row):
            if track:
                if int(track) in owners:
                    assert owners[int(track)] == channel
                owners[int(track)] = channel
    active = volumes > 0
    tone_disabled = (mixers[:,None] & (1 << np.arange(3))) != 0
    assert not np.any(active & tone_disabled)
    mixed_ticks = sum(bool(n and volumes[i,c]) for i,(n,c) in enumerate(zip(noise,carriers)))
    metadata.update(model='persistent_components_and_shared_noise_v2',update_rate_hz=50,
        selection=selection,volume_curve='YM2149 Ayumi',channel_assignment='pitch continuity, 2-semitone gate; amplitude rank never changes channel',
        component_count=len(owners),component_channel_migrations=0,
        noise_ticks=int(np.count_nonzero(noise)),tone_plus_noise_ticks=mixed_ticks,
        noise_only_ticks=int(np.count_nonzero(noise))-mixed_ticks,
        note_events=events,component_tracks=tracks.tolist(),mixers=mixers.tolist(),
        noise_shares=share.tolist(),noise_carriers=carriers.tolist(),
        base_tone_volumes=volumes.tolist(),native_instruction_delta_tstates=0,
        limitations='Estimated fundamentals and noise; AY Boolean mixer shares one volume with the tone and cannot add an independently controlled fourth voice. No listening acceptance implied.')
    return periods,mixed,paths,noise,explained,metadata
