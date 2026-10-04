"""Note-oriented offline experiments using the unchanged 50-Hz AY player.

All lookahead, tracking, envelope fitting and pitch holding run on the PC.
No MIDI score or recording-specific note sequence is embedded here. The
legacy analyser remains available for source types that need continuous bends.
"""
from __future__ import annotations
from itertools import product
from pathlib import Path
import re

import numpy as np

import ay_fidelity as ay
import ay_square_fit as fit


def chip_levels(chip='YM'):
    """Read the same fixed-volume curve used by the vendored renderer."""
    if chip not in ('AY', 'YM'):
        raise ValueError('chip must be AY or YM')
    text = (Path(__file__).parent/'vendor/ayumi-js/ayumi.js').read_text()
    body = re.search(r'const '+chip+r'_DAC_TABLE = \[(.*?)\]', text, re.S).group(1)
    table = np.array([float(v) for v in body.split(',') if v.strip()])[1::2]
    if len(table) != 16 or table[0] != 0 or table[-1] != 1 or np.any(np.diff(table) <= 0):
        raise ValueError('invalid fixed-volume curve')
    return table


def short_decomposition(magnitude, sample_rate):
    """Same harmonic model at a shorter window for note-envelope evidence."""
    size = magnitude.shape[1]-1
    dictionary, useful = ay.harmonic_dictionary(sample_rate, window_size=size)
    exponent = .75
    target = magnitude[:, useful].T**exponent
    dictionary = dictionary**exponent
    norm = np.linalg.norm(dictionary, axis=0)
    dictionary /= norm
    correlation = dictionary.T@target
    gram = dictionary.T@dictionary
    activation = np.maximum(correlation, 1e-16)
    penalty = .045*np.max(correlation, axis=0, keepdims=True)
    for _ in range(80):
        activation *= np.maximum(correlation-penalty, 0)/(gram@activation+1e-16)
    return np.sum((activation/norm[:, None]).reshape(len(ay.NOTES), 3, -1), axis=1).T**(1/exponent)


def attacks(samples, sample_rate, count):
    """Resolve fast attacks with 23-ms windows on the unchanged 20-ms grid."""
    mag, _ = ay.spectra(samples, sample_rate, 50, count, window_size=512)
    frequency = np.fft.rfftfreq(1024, 1/sample_rate)
    useful = (frequency >= 100) & (frequency <= 8000)
    band = mag[:, useful]
    scale = max(float(np.percentile(np.max(band, axis=1), 95))*.05, 1e-12)
    flux = np.r_[0., np.maximum(0, np.diff(np.log1p(band/scale), axis=0)).mean(axis=1)]
    threshold = max(.025, float(np.median(flux)+1.5*np.median(np.abs(flux-np.median(flux)))))
    peaks = np.zeros(count, dtype=bool)
    last = -3
    for i in range(1, count-1):
        if i-last >= 2 and flux[i] > threshold and flux[i] > flux[i-1] and flux[i] >= flux[i+1]:
            peaks[i] = True
            last = i
    flatness = np.exp(np.mean(np.log(np.maximum(band, 1e-12)), axis=1))/np.maximum(band.mean(axis=1), 1e-12)
    return peaks, flux, flatness


def analyse(samples, sample_rate=22050):
    count = (len(samples)+round(sample_rate/50)-1)//round(sample_rate/50)
    magnitude, rms = ay.spectra(samples, sample_rate, 50, count)
    amplitude, explained = ay.decompose(magnitude, sample_rate)
    short, _ = ay.spectra(samples, sample_rate, 50, count, window_size=2048)
    short_amplitude = short_decomposition(short, sample_rate)
    onset, flux, flatness = attacks(samples, sample_rate, count)
    return dict(magnitude=magnitude, rms=rms, amplitude=amplitude, explained=explained,
                short_amplitude=short_amplitude, onset=onset, flux=flux, flatness=flatness,
                sample_rate=sample_rate)


def joint_paths(amplitude, rms, explained, seed, onset, beam_size=32):
    """Joint three-voice beam path, with no duplicated neighbouring pitches.

    Candidate notes come from the signal, the existing voice tracks and the
    strongest preceding state. Attack evidence reduces the cost of changing
    a note; otherwise continuity is favoured. Melody and bass carry more
    weight than the optional harmony. The finite beam bounds offline cost.
    """
    active = amplitude.copy()
    active[(rms < 10**(-65/20)) | (explained < .12)] = 0
    weights = np.array([1.1, .8, 1.4])
    ranges = [(33, 59), (43, 88), (55, 93)]
    previous = np.array([[-1, -1, -1]])
    scores = np.zeros(1)
    history, backs = [], []
    for tick, row in enumerate(active):
        reference = max(float(row.max()), 1e-12)
        options = []
        for voice, (low, high) in enumerate(ranges):
            allowed = np.flatnonzero((ay.NOTES >= low) & (ay.NOTES <= high))
            top = allowed[np.argsort(row[allowed], kind='stable')[-3:]]
            candidates = {int(ay.NOTES[k]) for k in top if row[k]/reference > .035}
            candidates.update((-1, int(seed[tick, voice]), int(previous[np.argmax(scores), voice])))
            options.append(sorted(candidates))
        states = np.array([s for s in product(*options) if all(
            s[a] < 0 or s[b] < 0 or abs(s[a]-s[b]) > 1
            for a, b in ((0, 1), (0, 2), (1, 2)))], dtype=int)
        emissions = np.zeros(len(states))
        for voice in range(3):
            note = states[:, voice]
            ratio = row[np.maximum(note, 33)-33]/reference
            allowed = (ay.NOTES >= ranges[voice][0]) & (ay.NOTES <= ranges[voice][1])
            rest = np.log(.07+max(0., .15-float(row[allowed].max())/reference))
            emissions += weights[voice]*np.where(note < 0, rest, np.log(.008+ratio))
            # A weak seed preference keeps roles consistent when spectra tie.
            emissions += .10*(note == seed[tick, voice])
        distance = np.abs(previous[:, None, :]-states[None, :, :])
        both = (previous[:, None, :] >= 0) & (states[None, :, :] >= 0)
        changes = previous[:, None, :] != states[None, :, :]
        penalty = np.where(both, .25*changes+np.minimum(distance, 24)*np.array([.112, .112, .14]), .30*changes)
        penalty *= (.55 if onset[tick] else 1.15)
        trial = scores[:, None]-np.sum(penalty*weights, axis=2)
        parent = np.argmax(trial, axis=0)
        new_scores = trial[parent, np.arange(len(states))]+emissions
        keep = np.argsort(new_scores, kind='stable')[-beam_size:]
        previous, scores = states[keep], new_scores[keep]
        scores -= scores.max()
        history.append(previous)
        backs.append(parent[keep])
    state = int(np.argmax(scores))
    result = np.empty(seed.shape, dtype=int)
    for tick in range(len(seed)-1, -1, -1):
        result[tick] = history[tick][state]
        state = int(backs[tick][state])
    return result


def strengths_for(paths, amplitude):
    return np.where(paths >= 0, amplitude[np.arange(len(paths))[:, None], np.maximum(paths, 33)-33], 0.)


def envelopes(paths, long_amplitude, short_amplitude, onset, blend):
    """Use note-local fast amplitude and bounded release smoothing.

    Bass keeps its long-window estimate; higher notes can use shorter-window
    evidence. New notes/attacks respond immediately. Smoothing is confined to
    a note lifetime, so it cannot carry sound past a rest or into another note.
    """
    slow = strengths_for(paths, long_amplitude)
    fast = strengths_for(paths, short_amplitude)
    amount = blend*np.clip((paths-45)/24, 0, 1)
    values = slow*(1-amount)+fast*amount
    for i in range(1, len(values)):
        same = (paths[i] >= 0) & (paths[i] == paths[i-1])
        falling = values[i] < values[i-1]
        smooth = same & falling & ~onset[i]
        values[i, smooth] = .75*values[i, smooth]+.25*values[i-1, smooth]
    return values


def hold_note_pitch(periods, volumes, noise, paths, onset):
    """One robust integer period per note; return explicit note lifetimes."""
    result = periods.copy()
    events = []
    for voice in range(3):
        keys = np.where(volumes[:, voice] > 0, paths[:, voice], -1)
        if voice == 1:
            keys[noise > 0] = -1
        repeated = onset & (np.r_[0, np.diff(volumes[:, voice])] >= 2)
        changes = np.r_[True, np.diff(keys) != 0] | repeated
        edges = np.r_[np.flatnonzero(changes), len(keys)]
        for lo, hi in zip(edges[:-1], edges[1:]):
            if keys[lo] < 0:
                continue
            period = int(np.rint(np.median(periods[lo:hi, voice])))
            result[lo:hi, voice] = period
            events.append(dict(voice=voice, note=int(keys[lo]), start_tick=int(lo), end_tick=int(hi),
                               period=period, peak_volume=int(volumes[lo:hi, voice].max())))
    return result, events


def arrange(features, *, joint=False, envelope_blend=0., noise_policy='legacy', calibrated=True):
    """Build a bounded experimental music arrangement at exactly 50 Hz."""
    if noise_policy not in ('legacy', 'transients') or not 0 <= envelope_blend <= 1:
        raise ValueError('invalid music profile settings')
    mag, rms = features['magnitude'], features['rms']
    amp, explained = features['amplitude'], features['explained']
    rate, onset = features['sample_rate'], features['onset']
    table = chip_levels() if calibrated else ay.LEVELS
    _, _, seed = ay.arrange(amp, rms, explained)
    paths = joint_paths(amp, rms, explained, seed, onset) if joint else seed.copy()
    strengths = envelopes(paths, amp, features['short_amplitude'], onset, envelope_blend) if envelope_blend else strengths_for(paths, amp)
    relative = strengths/np.maximum(np.linalg.norm(strengths, axis=1, keepdims=True), 1e-12)
    master = rms*np.sqrt(explained)
    peak = max(float(np.percentile(master, 98)), 1e-12)
    levels = np.clip(relative*(master/peak*.85)[:, None], 0, 1)
    levels[(rms < 10**(-65/20)) | (explained < .12)] = 0
    volumes = np.argmin(np.abs(levels[:, :, None]-table[None, None, :]), axis=2)
    periods = np.clip(np.rint(ay.AY_CLOCK/(16*440*2**((np.maximum(paths, 33)-69)/12))), 1, 4095).astype(int)
    legacy_volumes = np.argmin(abs(table[volumes, None]-ay.LEVELS), axis=2)
    noise, mixed_volumes, _ = ay.arrange_noise(mag, rms, explained, legacy_volumes, rate)
    if noise_policy == 'transients':
        # Retain real sustained broadband effects, but bound tonal-source noise
        # to the detected attack and its next tick (at most 40 ms per attack).
        recent = onset | np.r_[False, onset[:-1]]
        broad = (explained < .55) & (features['flatness'] > .25)
        noise[~(recent | broad)] = 0
    # Noise candidate levels were generated using the legacy table. Convert
    # their physical target into the selected chip curve before fitting.
    noisy = noise > 0
    volumes[noisy, 1] = np.argmin(abs(table[:, None]-ay.LEVELS[mixed_volumes[noisy, 1]]), axis=0)
    periods, volumes, metadata = fit.refine(mag, periods, volumes, noise, rate,
                                          tuning_cents=50, level_table=table)
    periods, events = hold_note_pitch(periods, volumes, noise, paths, onset)
    for voice in range(3):
        previous = 1
        for i in range(len(periods)):
            if volumes[i, voice] and not (voice == 1 and noise[i]):
                previous = int(periods[i, voice])
            else:
                periods[i, voice] = previous
    metadata.update(model='note_oriented_music_50hz_v1', update_rate_hz=50,
        joint_voice_path=joint, envelope_blend=envelope_blend, noise_policy=noise_policy,
        volume_curve='YM2149 Ayumi' if calibrated else 'nominal 3 dB',
        detected_attacks=int(onset.sum()), note_events=events,
        noise_ticks=int(noisy.sum()), native_instruction_delta_tstates=0,
        limitations='Automatic note estimates, not an annotated transcription; no listening acceptance implied.')
    return periods, volumes, paths, noise, explained, metadata


def convert(samples, sample_rate=22050):
    """Selected music preset; every output state lasts exactly 20 ms."""
    return arrange(analyse(samples, sample_rate), joint=True,
                   envelope_blend=.5, noise_policy='transients')
