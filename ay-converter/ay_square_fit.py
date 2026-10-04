"""Offline register-volume fitting against AY square-wave harmonics.

The pitch tracker still models instruments, which need not be square waves.
This second stage models what the selected AY periods can actually reproduce.
It changes neither the nine-byte stream nor the 50 Hz player.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import product

import numpy as np

import ay_fidelity as ay


def recover_isolated_tones(magnitude, rms, periods, volumes, paths, sample_rate=22050):
    """Recover an off-grid pure tone that the semitone tracker called a rest.

    Require 85% of spectral power around one peak: broad noise and ordinary
    polyphony cannot trigger this fallback. Parabolic log-peak interpolation
    seeds a real integer AY period, without snapping to a musical note.
    """
    frequency = np.fft.rfftfreq((magnitude.shape[1]-1)*2, 1/sample_rate)
    valid = (frequency >= 45) & (frequency <= min(6000, sample_rate*.45))
    peak_rms = max(float(np.percentile(rms, 98)), 1e-12)
    recovered = 0
    for i in np.flatnonzero(~np.any(volumes, axis=1) & (rms > 10**(-65/20))):
        k = int(np.argmax(np.where(valid, magnitude[i], 0)))
        power = magnitude[i]**2
        if not 0 < k < len(power)-1 or power[max(0,k-3):k+4].sum() < .85*power.sum():
            continue
        left, centre, right = np.log(np.maximum(magnitude[i, k-1:k+2], 1e-15))
        curve = left-2*centre+right
        offset = np.clip(.5*(left-right)/curve, -.5, .5) if curve < -1e-12 else 0
        pitch = (k+offset)*frequency[1]
        periods[i, 2] = int(np.clip(round(ay.AY_CLOCK/(16*pitch)), 1, 4095))
        paths[i, 2] = round(69+12*np.log2(pitch/440))
        volumes[i, 2] = np.argmin(abs(ay.LEVELS-min(1, .85*rms[i]/peak_rms)))
        recovered += 1
    return recovered


def square_templates(periods, sample_rate=22050, window_size=4096):
    """Unit-volume spectra matching render(): odd 1/h partials, integer periods.

    Magnitudes add without phase cancellation. This is an offline approximation,
    not a model of the analogue board or of AY counter-write timing.
    """
    frequency = np.fft.rfftfreq(2*window_size, 1/sample_rate)
    result = np.zeros((len(periods), len(frequency)))
    for index, period in enumerate(periods):
        fundamental = ay.AY_CLOCK/(16*int(period))
        for harmonic in range(1, min(31, int(sample_rate*.48/fundamental))+1, 2):
            x = (frequency-harmonic*fundamental)*window_size/sample_rate
            peak = np.abs(np.sinc(x)+.5*np.sinc(x-1)+.5*np.sinc(x+1))
            result[index] += peak/(np.pi*harmonic)
    return result


@lru_cache(maxsize=4096)
def volume_candidates(original):
    """Preserve the fast RMS envelope within 0.25 dB, including quantization.

    The long FFT describes timbre, not the current 20 ms attack amplitude.
    Search at most one register step either way per sounding voice. Keep
    tracked rests silent and keep very quiet tones audible.
    """
    candidates = np.array(list(product(*(range(max(1, v-1), min(15, v+1)+1)
                                         for v in original))), dtype=int)
    power = np.sum(ay.LEVELS[candidates]**2, axis=1)
    reference = np.sum(ay.LEVELS[list(original)]**2)
    return candidates[np.abs(10*np.log10(power/reference)) <= .25+1e-12]


def refine(magnitude, periods, volumes, noise, sample_rate=22050, *, noise_steps=1,
           tuning_cents=50):
    """Fit actual AY periods and tone levels; lower noise by one 3 dB step.

    Trackers seed a local integer-period search, including non-concert pitches.
    Keep rests and the fast tone envelope. Joint coordinate search scores all
    active voices together, with hysteresis for stable frequencies. An independent
    level-matched rendered comparison is required to assess audible quality.
    """
    if noise_steps not in (0, 1):
        raise ValueError('noise_steps must be zero or one')
    if not 0 <= tuning_cents <= 100:
        raise ValueError('tuning_cents must be in 0..100')
    result = volumes.copy()
    tuned = periods.copy()
    used = np.unique(periods[volumes > 0])
    ratio = 2**(tuning_cents/1200)
    options = {int(p): np.arange(max(1, int(np.ceil(p/ratio))),
                                min(4095, int(np.floor(p*ratio)))+1) for p in used}
    all_periods = np.unique(np.concatenate(list(options.values()))) if len(used) else used
    templates = square_templates(all_periods, sample_rate, magnitude.shape[1]-1)
    lookup = {int(period): index for index, period in enumerate(all_periods)}
    rows = {p: np.array([lookup[int(q)] for q in choices]) for p, choices in options.items()}
    before_score = after_score = 0.0
    previous = [None]*3
    for index, (p, v) in enumerate(zip(periods, volumes)):
        voices = [j for j in range(3) if v[j] and not (j == 1 and noise[index])]
        for voice in range(3):
            if voice not in voices:
                previous[voice] = None
        if not voices:
            continue
        basis = templates[[lookup[int(p[j])] for j in voices]]
        target = magnitude[index]
        target_norm = max(np.linalg.norm(target), 1e-15)
        old_levels = ay.LEVELS[v[voices]]
        candidates = volume_candidates(tuple(map(int, v[voices])))
        levels = old_levels.copy()
        prediction = levels @ basis
        score = float(prediction @ target/max(np.linalg.norm(prediction)*target_norm, 1e-15))
        before_score += score
        for _ in range(2):
            for j, voice in enumerate(voices):
                choices = options[int(p[voice])]
                variants = templates[rows[int(p[voice])]]
                rest = prediction-levels[j]*basis[j]
                numerator = rest @ target+levels[j]*(variants @ target)
                power = (rest @ rest+2*levels[j]*(variants @ rest)+
                         levels[j]**2*np.sum(variants**2, axis=1))
                scores = numerator/(np.sqrt(np.maximum(power, 1e-30))*target_norm)
                selected = int(np.argmax(scores))
                # Prefer the preceding tick when statistically almost tied.
                held = np.flatnonzero(choices == previous[voice])
                if len(held) and scores[held[0]] >= scores[selected]-.001:
                    selected = int(held[0])
                if scores[selected] > score+.001:
                    tuned[index, voice] = choices[selected]
                    basis[j] = variants[selected]
                    prediction = rest+levels[j]*basis[j]
                    score = float(scores[selected])
            gram = basis @ basis.T
            correlation = basis @ target
            trial_levels = ay.LEVELS[candidates]
            denominator = np.sqrt(np.maximum(np.sum((trial_levels @ gram)*trial_levels, axis=1), 1e-30))
            scores = (trial_levels @ correlation)/(denominator*target_norm)
            selected = int(np.argmax(scores))
            if scores[selected] > score+.001:
                result[index, voices] = candidates[selected]
                levels = trial_levels[selected]
                prediction = levels @ basis
                score = float(scores[selected])
        after_score += score
        for voice in voices:
            previous[voice] = int(tuned[index, voice])
    active_noise = noise > 0
    result[active_noise, 1] = np.maximum(0, volumes[active_noise, 1]-noise_steps)
    metadata = dict(model='ay_square_register_fit_v2',
        tone_harmonics='odd 1/h through 31, below 0.48 sample rate, actual integer AY periods',
        noise_attenuation_register_steps=noise_steps,
        nominal_noise_attenuation_db=float(noise_steps*20*np.log10(2**.5)),
        changed_tone_registers=int(np.count_nonzero((result != volumes) &
            ~np.column_stack((np.zeros(len(noise), bool), active_noise, np.zeros(len(noise), bool))))),
        noise_ticks=int(np.count_nonzero(active_noise)),
        tuned_period_registers=int(np.count_nonzero(tuned != periods)),
        tuning_radius_cents=float(tuning_cents), frequency_score_hysteresis=.001,
        fit_spectral_cosine_sum_before=before_score, fit_spectral_cosine_sum_after=after_score,
        tone_power_tolerance_db=.25, maximum_tone_register_change=1,
        native_instruction_delta_tstates=0,
        limitations='Phase-independent magnitude fit; nominal 3 dB levels; no analogue filter model.')
    return tuned, result, metadata
