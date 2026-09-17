"""Joint harmonic analysis and three-voice arrangement for the fixed AY stream.

Offline only: the player still receives nine register bytes per video frame.
Harmonic templates compete for the same spectrum, so one instrument's partials
do not independently become three voices. Silence is an explicit track state.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import wave

import numpy as np

AY_CLOCK = 1_773_400
# Nominal 3 dB fixed-volume steps. Actual AY/YM chips and analogue boards vary.
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


def track(amplitude, low, high, reference=None, change_cost=.25, jump_cost=.14):
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


def arrange(amplitude, rms, explained):
    """Allocate melody, bass, harmony, suppressing already assigned notes."""
    active = amplitude.copy()
    active[(rms < 10**(-65/20)) | (explained < .12)] = 0
    reference = np.max(active, axis=1, keepdims=True)
    bass = track(active, 33, 59, reference, jump_cost=.112)
    residual = active.copy()
    for i, note in enumerate(bass):
        if note>=0: residual[i, np.abs(NOTES-note)<=1] = 0
    melody = track(residual, 55, 93, reference)
    for i, note in enumerate(melody):
        if note>=0: residual[i, np.abs(NOTES-note)<=1] = 0
    harmony = track(residual, 43, 88, reference, jump_cost=.112)
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
    power = magnitude*magnitude
    padded = np.pad(power, ((0, 0), (8, 8)), mode='edge')
    floor = np.median(np.lib.stride_tricks.sliding_window_view(padded, 17, axis=1), axis=-1)/.7
    broad = np.minimum(power, floor)
    useful = (frequencies >= 150) & (frequencies <= 9000)
    share = np.sum(broad[:, useful], axis=1)/np.maximum(np.sum(power, axis=1), 1e-16)
    # The clipped median is conservative: tonal leakage must not trigger hiss.
    noise_rms = rms*np.sqrt(share)
    peak = max(float(np.percentile(rms*np.sqrt(explained), 98)), 1e-12)
    level = np.clip(noise_rms/peak*.85, 0, 1)
    selected = (share>.16) & (rms>10**(-55/20)) & (level>np.maximum(.012, LEVELS[volumes[:,1]]*1.35))
    frequency = frequencies[useful]
    templates = np.array([np.abs(np.sinc(frequency/(AY_CLOCK/(16*n)))) for n in range(1,32)])
    templates /= np.maximum(np.linalg.norm(templates, axis=1, keepdims=True), 1e-12)
    periods = np.argmax(np.sqrt(broad[:,useful]) @ templates.T, axis=1)+1
    periods[~selected] = 0
    result = volumes.copy()
    result[selected,1] = np.argmin(np.abs(level[selected,None]-LEVELS[None,:]), axis=1)
    return periods, result, share


def analyse(source: Path, start: float, duration: float, fps: float, *, noise=False):
    import build_long_video_trd as video
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('ffmpeg is not available')
    rate = 22050; count = round(duration*fps)
    if count<1: raise ValueError('audio duration must contain at least one frame')
    samples = video.decode_analysis_audio(ffmpeg, source, start, duration, rate, True)
    magnitude, rms = spectra(samples, rate, fps, count)
    amplitude, explained = decompose(magnitude, rate)
    periods, volumes, paths = arrange(amplitude, rms, explained)
    noise_periods = np.zeros(count, dtype=int)
    if noise:
        noise_periods, volumes, _ = arrange_noise(magnitude, rms, explained, volumes, rate)
        # A noise-only channel need not change its unused tone period.
        previous = 1
        for i in range(count):
            if noise_periods[i]: periods[i,1] = previous
            else: previous = periods[i,1]
    frames = [video.AyFrame(tuple(map(int,p)), tuple(map(int,v)), int(n))
              for p,v,n in zip(periods, volumes, noise_periods)]
    changes = np.diff(paths[:, 2])
    voiced_pairs = (paths[:-1, 2]>=0) & (paths[1:, 2]>=0)
    rms_db = 20*np.log10(np.maximum(rms, 1e-8))
    audible = rms_db[rms_db>-70]
    peak_volumes = np.max(volumes, axis=1)
    sounding_notes = (volumes>0) & (paths>=0)
    sounding_notes[noise_periods>0,1] = False
    stats = dict(mode='joint_harmonic_sparse_three_voice', update_rate_hz=float(fps),
                 pitch_mix='front_left_right', clock_hz=AY_CLOCK,
                 mean_harmonic_explained=float(np.mean(explained)),
                 distinct_notes=len(set(paths[sounding_notes].tolist())),
                 active_frame_ratio=float(np.mean(np.any(volumes>0,axis=1))),
                 melody_note_changes=int(np.count_nonzero(changes)),
                 melody_large_jumps=int(np.count_nonzero((np.abs(changes)>7)&voiced_pairs)),
                 melody_mean_hold_frames=count/max(1, int(np.count_nonzero(changes))+1),
                 source_quiet_dbfs=float(np.percentile(audible,10)) if len(audible) else -70.,
                 source_loud_dbfs=float(np.percentile(audible,98)) if len(audible) else -70.,
                 master_volume_min=int(peak_volumes.min()),master_volume_max=int(peak_volumes.max()),
                 master_volume_mean=float(peak_volumes.mean()),
                 volume_model='nominal_3dB_steps', frames=count,
                 noise_frames=int(np.count_nonzero(noise_periods)),
                 noise_seconds=float(np.count_nonzero(noise_periods)/fps),
                 noise_mode='channel_B_replaces_weaker_harmony' if noise else 'disabled',
                 required_fast_stream_version=10 if np.any(noise_periods) else 9,
                 noise_analysis=dict(frequency_median_bins=17,median_power_scale=.7,
                                     minimum_broadband_share=.16,harmony_replacement_ratio=1.35,
                                     minimum_rms_dbfs=-55,noise_period_range=[1,31]) if noise else None,
                 analysis=dict(sample_rate=rate,window_samples=4096,fft_samples=8192,
                               harmonic_slopes=[.65,1.2,2.0],harmonics_limit=16,
                               amplitude_exponent=.75,sparsity_penalty=.045,iterations=80,
                               noise_flatness_limit=.75,silence_dbfs=-65,
                               melody_jump_cost=.14,support_jump_cost=.112,note_change_cost=.25))
    return frames, stats


def noise_sequence():
    """Maximal 17-bit x^17+x^14+1 LFSR; period and seed are deterministic."""
    sequence = np.empty(131071)
    state = 1
    for i in range(len(sequence)):
        sequence[i] = 1.0 if state & 1 else -1.0
        state = (state >> 1) | (((state ^ (state >> 3)) & 1) << 16)
    return sequence


def render(frames, update_rate, sample_rate=44100):
    """AY approximation: band-limited tones, 4x sampled shared noise, log levels.

    Noise state continues across video frames; the preview is not a cycle-exact
    emulation of counter writes or the analogue output circuit.
    """
    result = np.zeros(round(len(frames)*sample_rate/update_rate))
    phase = np.zeros(3)
    noise_phase = 0.0
    sequence = noise_sequence() if any(f.noise_period for f in frames) else None
    for i, frame in enumerate(frames):
        start, end = round(i*sample_rate/update_rate), round((i+1)*sample_rate/update_rate)
        t = np.arange(1, end-start+1)/sample_rate
        for voice in range(3):
            frequency = AY_CLOCK/(16*max(1, frame.periods[voice]))
            cycles = phase[voice]+t*frequency
            if frame.volumes[voice] and not (voice==1 and frame.noise_period):
                wave_values = np.zeros(len(t))
                for h in range(1, min(31, int(sample_rate*.48/frequency))+1, 2):
                    wave_values += np.sin(2*np.pi*h*cycles)/h
                result[start:end] += wave_values*(4/np.pi)*LEVELS[frame.volumes[voice]]/4
            phase[voice] = (phase[voice]+len(t)*frequency/sample_rate)%1
        if sequence is not None:
            frequency = AY_CLOCK/(16*max(1, frame.noise_period))
            if frame.noise_period and frame.volumes[1]:
                clock = noise_phase+np.arange(1,len(t)*4+1)*frequency/(sample_rate*4)
                values = sequence[np.floor(clock).astype(np.int64)%len(sequence)].reshape(-1,4).mean(axis=1)
                result[start:end] += values*LEVELS[frame.volumes[1]]/4
            noise_phase = (noise_phase+len(t)*frequency/sample_rate)%len(sequence)
    return result


def write_preview(path, frames, update_rate, sample_rate=44100):
    samples = render(frames, update_rate, sample_rate)
    pcm = np.clip(np.rint(samples*32767), -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())
