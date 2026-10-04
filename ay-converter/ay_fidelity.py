"""Audio analysis and three-voice arrangement, preserved from toolkit/ay_fidelity.py.

The spectral fit and tracking routines are unchanged. Video input/output helpers
are excluded so this folder can run without the parent video project.
"""
from __future__ import annotations
import numpy as np

AY_CLOCK = 1_773_400
LEVELS = np.r_[0.0, 2.0 ** ((np.arange(1, 16)-15)/2.0)]
NOTES = np.arange(33, 94)


def spectra(samples, sample_rate, rate, count, window_size=4096):
    """Centred Hann windows; zero-padding improves fractional-bin sampling."""
    window = np.hanning(window_size)
    result = np.empty((count, window_size+1), dtype=np.float64)
    rms = np.empty(count)
    for i in range(count):
        first = round((i+.5)*sample_rate/rate)-window_size//2
        lo, hi = max(0, first), min(len(samples), first+window_size)
        segment = np.zeros(window_size)
        if hi > lo: segment[lo-first:hi-first] = samples[lo:hi]
        result[i] = np.abs(np.fft.rfft(segment*window, n=window_size*2))/(window.sum()/2)
        a, b = round(i*sample_rate/rate), round((i+1)*sample_rate/rate)
        frame = samples[a:b]
        rms[i] = np.sqrt(np.mean(frame*frame)) if len(frame) else 0
    return result, rms


def harmonic_dictionary(sample_rate, window_size=4096, notes=NOTES):
    """Several spectral envelopes per pitch; finite-window Hann peak shape."""
    frequencies = np.fft.rfftfreq(window_size*2, 1/sample_rate)
    useful = (frequencies >= 45) & (frequencies <= 6000)
    f = frequencies[useful]
    columns = []
    for note in notes:
        fundamental = 440*2.0**((note-69)/12)
        for slope in (.65, 1.2, 2.0):
            template = np.zeros(len(f))
            for h in range(1, min(16, int(6000/fundamental))+1):
                x = (f-h*fundamental)*window_size/sample_rate
                # Fourier transform of the centred Hann window.
                peak = np.abs(np.sinc(x)+.5*np.sinc(x-1)+.5*np.sinc(x+1))
                template += h**(-slope)*peak
            columns.append(template)
    return np.stack(columns, axis=1), useful


def decompose(magnitude, sample_rate=22050, iterations=80):
    """Nonnegative sparse fit of competing harmonic templates (no ML model)."""
    dictionary, useful = harmonic_dictionary(sample_rate)
    target = magnitude[:, useful].T
    flatness = np.exp(np.mean(np.log(np.maximum(target, 1e-12)), axis=0))/np.maximum(np.mean(target, axis=0), 1e-12)
    # Partial compression reduces domination by loud low-frequency instruments.
    exponent = .75
    target = target**exponent
    dictionary = dictionary**exponent
    norm = np.sqrt(np.sum(dictionary*dictionary, axis=0))
    dictionary /= norm
    correlation = dictionary.T @ target
    gram = dictionary.T @ dictionary
    penalty = .045*np.max(correlation, axis=0, keepdims=True)
    activation = np.maximum(correlation, 1e-16)
    for _ in range(iterations):
        activation *= np.maximum(correlation-penalty, 0)/(gram@activation+1e-16)
    fitted = dictionary@activation
    energy = np.sum(target*target, axis=0)
    explained = np.where(energy>1e-16,
                         1-np.sum((target-fitted)**2, axis=0)/np.maximum(energy, 1e-16), 0)
    # Recover approximate fundamental amplitude from column normalisation.
    amplitude = np.sum((activation/norm[:, None]).reshape(len(NOTES), 3, -1), axis=1).T**(1/exponent)
    # Broadband noise has no reliable note: do not turn it into a chord.
    amplitude[flatness>.75] = 0
    return amplitude, np.clip(explained, 0, 1)


def track(amplitude, low, high, reference=None, change_cost=.25, jump_cost=.14, transition_scale=1.0):
    """Viterbi voice with a real rest state and modest continuity preference."""
    allowed = (NOTES >= low) & (NOTES <= high)
    notes = NOTES[allowed]
    local = amplitude[:, allowed]
    if reference is None: reference = np.max(amplitude, axis=1, keepdims=True)
    reference = np.maximum(reference, 1e-12)
    ratio = local/reference
    emissions = np.log(.008+ratio)
    rest = np.log(.07+np.maximum(0, .15-np.max(ratio, axis=1)))
    emissions = np.column_stack((emissions, rest))
    distance = np.abs(notes[:, None]-notes[None, :])
    transitions = np.full((len(notes)+1, len(notes)+1), -.30)
    transitions[:-1, :-1] = -change_cost*(distance>0)-jump_cost*np.minimum(distance, 24)
    transitions[-1, -1] = 0
    transitions *= transition_scale
    score = emissions[0].copy(); back = np.zeros(emissions.shape, dtype=np.int16)
    for i in range(1, len(emissions)):
        choices = score[:, None]+transitions
        back[i] = np.argmax(choices, axis=0)
        score = choices[back[i], np.arange(len(score))]+emissions[i]
    state = int(np.argmax(score)); path = np.empty(len(amplitude), dtype=int)
    for i in range(len(path)-1, -1, -1):
        path[i] = notes[state] if state<len(notes) else -1
        state = back[i, state]
    return path


def arrange(amplitude, rms, explained, *, transition_scale=1.0):
    """Allocate melody, bass, harmony, suppressing already assigned notes."""
    active = amplitude.copy()
    active[(rms < 10**(-65/20)) | (explained < .12)] = 0
    reference = np.max(active, axis=1, keepdims=True)
    bass = track(active, 33, 59, reference, jump_cost=.112, transition_scale=transition_scale)
    residual = active.copy()
    for i, note in enumerate(bass):
        if note>=0: residual[i, np.abs(NOTES-note)<=1] = 0
    melody = track(residual, 55, 93, reference, transition_scale=transition_scale)
    for i, note in enumerate(melody):
        if note>=0: residual[i, np.abs(NOTES-note)<=1] = 0
    harmony = track(residual, 43, 88, reference, jump_cost=.112, transition_scale=transition_scale)
    paths = np.column_stack((bass, harmony, melody))
    strengths = np.zeros(paths.shape)
    for i, notes in enumerate(paths):
        for voice, note in enumerate(notes):
            if note>=0: strengths[i, voice] = active[i, note-NOTES[0]]
    # Preserve independent note dynamics instead of making every voice follow
    # the full 5.1 mix (which also contains dialogue and sound effects).
    relative = strengths/np.maximum(np.linalg.norm(strengths, axis=1, keepdims=True), 1e-12)
    master = rms*np.sqrt(explained)
    peak = max(float(np.percentile(master, 98)), 1e-12)
    levels = np.clip(relative*(master/peak*.85)[:, None], 0, 1)
    volumes = np.argmin(np.abs(levels[:, :, None]-LEVELS[None, None, :]), axis=2)
    periods = np.rint(AY_CLOCK/(16*440*2.0**((np.maximum(paths, 33)-69)/12)))
    periods = np.clip(periods, 1, 4095).astype(int)
    # Hold a silent channel's pitch; this also avoids needless entropy on disk.
    for voice in range(3):
        previous = 1
        for i in range(len(paths)):
            if volumes[i, voice]: previous = periods[i, voice]
            else: periods[i, voice] = previous
    return periods, volumes, paths


def arrange_noise(magnitude, rms, explained, volumes, sample_rate=22050):
    """Use broad spectral energy only when it outweighs the harmony voice.

    A frequency median rejects narrow harmonic peaks. Fit the colour of the
    remaining noise to the expected sample-and-hold noise spectra of AY R6.
    Melody and bass remain intact; channel B is tone OR noise, never both.
    """
    frequencies = np.fft.rfftfreq((magnitude.shape[1]-1)*2, 1/sample_rate)
    useful = (frequencies >= 150) & (frequencies <= 9000)
    frequency = frequencies[useful]
    templates = np.array([np.abs(np.sinc(frequency/(AY_CLOCK/(16*n)))) for n in range(1,32)])
    templates /= np.maximum(np.linalg.norm(templates, axis=1, keepdims=True), 1e-12)
    share = np.empty(len(magnitude))
    periods = np.empty(len(magnitude), dtype=int)
    # The 17-bin median needs a temporary copy. Bound it independently of
    # duration/update rate (100 Hz over two minutes otherwise needs >6 GiB).
    for first in range(0,len(magnitude),128):
        last=min(first+128,len(magnitude))
        power = magnitude[first:last]*magnitude[first:last]
        padded = np.pad(power, ((0, 0), (8, 8)), mode='edge')
        floor = np.median(np.lib.stride_tricks.sliding_window_view(padded, 17, axis=1), axis=-1)/.7
        broad = np.minimum(power, floor)
        share[first:last] = np.sum(broad[:, useful], axis=1)/np.maximum(np.sum(power, axis=1), 1e-16)
        periods[first:last] = np.argmax(np.sqrt(broad[:,useful]) @ templates.T, axis=1)+1
    # The clipped median is conservative: tonal leakage must not trigger hiss.
    noise_rms = rms*np.sqrt(share)
    peak = max(float(np.percentile(rms*np.sqrt(explained), 98)), 1e-12)
    level = np.clip(noise_rms/peak*.85, 0, 1)
    selected = (share>.16) & (rms>10**(-55/20)) & (level>np.maximum(.012, LEVELS[volumes[:,1]]*1.35))
    periods[~selected] = 0
    result = volumes.copy()
    result[selected,1] = np.argmin(np.abs(level[selected,None]-LEVELS[None,:]), axis=1)
    return periods, result, share


def arrange_for_chip(magnitude, rms, sample_rate=22050, *, noise=True, square_fit=True,
                     noise_steps=1, tuning_cents=50):
    """Track instrument pitches, then fit the output chip's square harmonics.

    square_fit=False reproduces the previous converter for controlled A/B tests.
    The generic converter calls this at 50 Hz, independently of video cadence.
    """
    amplitude, explained = decompose(magnitude, sample_rate)
    periods, volumes, paths = arrange(amplitude, rms, explained)
    recovered = 0
    if square_fit:
        from ay_square_fit import recover_isolated_tones
        recovered = recover_isolated_tones(magnitude, rms, periods, volumes, paths, sample_rate)
    noise_periods = np.zeros(len(rms), dtype=int)
    if noise:
        noise_periods, volumes, _ = arrange_noise(magnitude, rms, explained, volumes, sample_rate)
    fit = dict(model='legacy_instrument_amplitude')
    if square_fit:
        from ay_square_fit import refine
        periods, volumes, fit = refine(magnitude, periods, volumes, noise_periods,
                                      sample_rate, noise_steps=noise_steps, tuning_cents=tuning_cents)
        fit['recovered_isolated_tone_ticks'] = recovered
    # Noise-only B and silent channels retain unused tone periods on disk.
    for voice in range(3):
        previous = 1
        for i in range(len(rms)):
            if not volumes[i, voice] or (voice == 1 and noise_periods[i]):
                periods[i, voice] = previous
            else:
                previous = periods[i, voice]
    return periods, volumes, paths, noise_periods, explained, fit
