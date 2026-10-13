"""Bounded register proposals accepted against complete continuous chip audio.

Keep one fixed source/model calibration for the whole search. Compare absolute
20-ms levels and unpooled spectra, with source-only relative masking weights.
Every accepted change is in R0..R10; no PCM gain envelope or pitch/time warp.
"""
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import music_profile
import noise_colour
import psychoacoustic as psycho

HERE = Path(__file__).resolve().parent
SIZES = (512, 2048, 8192)


def spectra(samples, ticks, size):
    window = np.hanning(size)
    centres = np.rint((np.asarray(ticks)+.5)*441).astype(int)
    indices = centres[:, None]+np.arange(size)-size//2
    segments = samples[np.clip(indices, 0, len(samples)-1)]
    segments[(indices < 0) | (indices >= len(samples))] = 0
    return abs(np.fft.rfft(segments*window, n=size*2, axis=1))/(window.sum()/2)


def tick_rms(samples):
    return np.sqrt(np.mean(samples.reshape(-1, 441)**2, axis=1))


class Objective:
    def __init__(self, samples):
        self.samples = samples
        self.count = len(samples)//441
        self.rms = tick_rms(samples)
        self.level_floor = max(float(self.rms.max())*.001, 1e-9)
        self.reference = {}; self.masking = {}; self.floor = {}; self.useful = {}
        for size in SIZES:
            hz = np.fft.rfftfreq(size*2, 1/22050)
            useful = (hz >= 50) & (hz <= 8000)
            magnitude = np.empty((self.count, int(useful.sum())), np.float32)
            for start in range(0, self.count, 128):
                end = min(start+128, self.count)
                magnitude[start:end] = spectra(samples, np.arange(start, end), size)[:, useful]
            self.reference[size] = magnitude
            self.masking[size] = psycho.thresholds(magnitude, hz[useful])
            self.floor[size] = max(float(magnitude.max())*.001, 1e-12)
            self.useful[size] = useful

    def measure(self, audio):
        errors = {}; weighted = {}
        for size in SIZES:
            total = weight_total = plain_total = support_total = 0.
            floor = self.floor[size]
            for start in range(0, self.count, 128):
                end = min(start+128, self.count)
                wanted = self.reference[size][start:end]
                observed = spectra(audio, np.arange(start, end), size)[:, self.useful[size]]
                support = (wanted > floor) | (observed > floor)
                weights = psycho.error_weights(wanted, observed, self.masking[size][start:end])*support
                error = abs(20*np.log10(np.maximum(wanted, floor)/np.maximum(observed, floor)))
                total += float((weights*error).sum()); weight_total += float(weights.sum())
                plain_total += float((support*error).sum()); support_total += int(support.sum())
            weighted[str(size)] = total/max(weight_total, 1)
            errors[str(size)] = plain_total/max(support_total, 1)
        rms = tick_rms(audio)
        support = (self.rms > self.level_floor) | (rms > self.level_floor)
        difference = 20*np.log10(np.maximum(rms, self.level_floor)/np.maximum(self.rms, self.level_floor))
        level_error = float(abs(difference[support]).mean()) if support.any() else 0.
        return dict(objective_db=float(np.mean(list(weighted.values())))+.35*level_error,
            masked_spectral_mae_db=weighted, absolute_spectral_mae_db=errors,
            level_mae_db=level_error, level_bias_db=float(difference[support].mean()) if support.any() else 0.,
            reference_rms=float(np.sqrt(np.mean(self.samples**2))),
            model_rms=float(np.sqrt(np.mean(audio**2))))


def volume_proposal(rows, reference_rms, observed_rms, strength):
    table = music_profile.chip_levels()
    ratio = np.clip(reference_rms/np.maximum(observed_rms, 1e-12), .25, 4)**strength
    target = table[rows[:, 8:]]*ratio[:, None]
    volumes = abs(target[:, :, None]-table).argmin(axis=2)
    volumes[rows[:, 8:] == 0] = 0
    volumes[reference_rms < 1e-9] = 0
    result = rows.copy(); result[:, 8:] = volumes
    return result


def pitch_proposal(samples, rows, tuning_cents):
    import ay_square_fit
    periods = rows[:, :6:2].astype(int)+(rows[:, 1:6:2].astype(int) << 8)
    volumes = rows[:, 8:].astype(int).copy()
    for channel in range(3):
        volumes[(rows[:, 7] & (1 << channel)) != 0, channel] = 0
    magnitude = np.empty((len(rows), 2049))
    for start in range(0, len(rows), 128):
        end = min(start+128, len(rows))
        magnitude[start:end] = spectra(samples, np.arange(start, end), 2048)
    tuned, _, _ = ay_square_fit.refine(magnitude, periods, volumes, np.zeros(len(rows), int),
        noise_steps=0, tuning_cents=min(tuning_cents, 25), level_table=music_profile.chip_levels())
    result = rows.copy(); result[:, :6:2] = tuned & 255; result[:, 1:6:2] = tuned >> 8
    return result


def optimize(samples, registers, node, *, work_parent=None, rounds=2, tuning_cents=25):
    samples = np.asarray(samples, float)
    rows = np.frombuffer(registers, np.uint8).reshape(-1, 11).copy()
    if len(samples) != len(rows)*441 or not len(rows) or not np.isfinite(samples).all():
        raise ValueError('expected finite aligned 22050-Hz PCM')
    if np.any(rows[:, 1:6:2] > 15) or np.any(rows[:, 6] > 31) or np.any(rows[:, 7] > 63) or np.any(rows[:, 8:] > 15):
        raise ValueError('invalid fixed-level AY registers')
    if not np.any(samples):
        rows[:, 8:] = 0
        return rows.tobytes(), dict(model='continuous_chip_feedback_v1', skipped='silent source',
            fixed_model_gain=1., changed_volume_registers=int(np.count_nonzero(np.frombuffer(registers,np.uint8).reshape(-1,11)[:,8:])),
            changed_tone_periods=0, changed_noise_ticks=0, native_instruction_delta_tstates=0)
    initial = rows.copy(); history = []; evaluated = 0
    with tempfile.TemporaryDirectory(prefix='ay-feedback-', dir=work_parent) as directory:
        root = Path(directory)
        def render(candidate):
            nonlocal evaluated
            evaluated += 1
            (root/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(), mtime=0))
            subprocess.run([str(node), str(HERE/'render_ym2149.js'), str(root/'registers.gz'),
                str(root/'chip.f32'), '50', str(root/'render.json')], check=True)
            audio = np.fromfile(root/'chip.f32', '<f4').astype(float)
            peak = float(np.max(abs(audio)))
            return noise_colour.downsample(audio), peak
        audio, peak = render(rows)
        # One speaker/output-voltage calibration, fixed for all candidates.
        gain = min(float(np.sqrt(np.mean(samples**2)/max(np.mean(audio**2), 1e-20))), .95/max(peak, 1e-12))
        objective = Objective(samples)
        best_audio = audio*gain; best = objective.measure(best_audio); baseline = best.copy()
        pitch = pitch_proposal(samples, rows, tuning_cents) if tuning_cents else rows.copy()
        for iteration in range(rounds):
            previous = rows.copy()
            observed = tick_rms(best_audio)
            soft = volume_proposal(previous, objective.rms, observed, .5)
            full = volume_proposal(previous, objective.rms, observed, 1.)
            frequency = previous.copy(); frequency[:, :6] = pitch[:, :6]
            joint = full.copy(); joint[:, :6] = pitch[:, :6]
            proposals = [('level-half', soft), ('level-full', full), ('tone-periods', frequency), ('joint', joint)]
            audible = np.any([(previous[:, 8+c] > 0) & ((previous[:, 7] & (1 << (c+3))) == 0) for c in range(3)], axis=0)
            for delta in (-1, 1):
                noise = previous.copy()
                noise[audible, 6] = np.clip(previous[audible, 6].astype(int)+delta, 1, 31)
                proposals.append((f'noise-{delta:+d}', noise))
            seen = {previous.tobytes()}; accepted = None
            for name, proposal in proposals:
                key = proposal.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                trial_audio, trial_peak = render(proposal)
                measure = objective.measure(trial_audio*gain)
                admissible = trial_peak*gain <= .999
                improve = admissible and measure['objective_db'] < best['objective_db']-1e-6
                history.append(dict(round=iteration+1, proposal=name, peak=trial_peak*gain,
                    admissible=admissible, improved_current_best=improve, metrics=measure))
                print(json.dumps(dict(stage='chip_feedback', round=iteration+1, proposal=name,
                    objective_db=measure['objective_db'], level_mae_db=measure['level_mae_db'], accepted=improve)), flush=True)
                if improve:
                    rows, best_audio, best, accepted = proposal, trial_audio*gain, measure, name
            if accepted is None:
                break
        assert best['objective_db'] <= baseline['objective_db']+1e-12
    info = dict(model='continuous_chip_feedback_v1', update_rate_hz=50, quantum_ms=20,
        objective='mean absolute masked log-spectral MAE for 512/2048/8192 + 0.35 * 20-ms RMS log-MAE; fixed calibration',
        psychoacoustic=psycho.MODEL, fixed_model_gain=gain, calibration_changes_between_candidates=False,
        baseline=baseline, final=best, candidates_rendered=evaluated, maximum_rounds=rounds,
        proposal_tuning_radius_cents=min(tuning_cents,25), history=history,
        changed_volume_registers=int(np.count_nonzero(rows[:, 8:] != initial[:, 8:])),
        changed_tone_periods=int(np.count_nonzero(np.any(rows[:, :6].reshape(-1,3,2) != initial[:, :6].reshape(-1,3,2), axis=2))),
        changed_noise_ticks=int(np.count_nonzero(rows[:, 6] != initial[:, 6])),
        native_instruction_delta_tstates=0, no_local_pcm_gain=True,
        limitations='Bounded local proposals, not a global optimum; three channels cannot reproduce arbitrary PCM. Playback SPL and analogue circuit response are unknown.')
    return rows.tobytes(), info
