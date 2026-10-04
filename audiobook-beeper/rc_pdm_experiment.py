"""RC-aware PDM generation on the host; independent of the release ASM.

Predict exact capacitor charge/discharge for each port hold. Integrate the
voltage error as well: greedy endpoint tracking alone need not preserve DC.
The reference voltage is the same RC applied to the intended PCM levels.
Actual saved Fuse hold times are reused as an offline scheduling assumption;
they are not a timing result for this new, as yet unported, modulator.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

from apply_rc_filter import inspect
from build_pdm import write_wav
from ima_player import CPU_CLOCK
from verify_ima import reference

HERE = Path(__file__).resolve().parent
WAV_RATE = 44100


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rc_coefficients(holds, tau):
    if tau == 0:  # Experimental control: same timing/feedback, RC omitted internally.
        return np.zeros_like(holds), np.zeros_like(holds), holds.copy()
    a = np.exp(-holds / tau)
    c = -tau * np.expm1(-holds / tau)
    return a, c, holds - c


def modulate(target, holds, tau, feedback_weight=.5):
    """Choose the bit minimizing integrated RC voltage error at next edge.

    w = desired capacitor voltage - actual capacitor voltage.
    e = integral of w over time. Both capacitor models start at zero.
    For constant x/bit over h: w' = a*w + (1-a)*(x-bit),
    e' = e + c*w + (h-c)*(x-bit), c=tau*(1-a).
    Compare e' for bit=0 and bit=1; update both states with the chosen bit.
    Weight b replaces e with (1+b)*e-b*older. b=0 is first order, b=1 is
    second order, and intermediate b damps the added feedback to avoid
    overload. Integrated physical error then equals e-b*older.
    The first three low bits preserve the current player's pipeline priming.
    """
    a, c, k = rc_coefficients(holds, tau)
    bits = np.empty(len(target), dtype=np.uint8)
    w = e = older = peak_w = peak_e = 0.0
    for i, (x, aa, cc, kk) in enumerate(zip(target, a, c, k)):
        feedback = (1 + feedback_weight) * e - feedback_weight * older
        unquantized = feedback + cc * w + kk * x
        bit = int(unquantized >= kk / 2) if i >= 3 else 0
        older, e = e, unquantized - kk * bit
        w = aa * w + (1 - aa) * (x - bit)
        peak_w, peak_e = max(peak_w, abs(w)), max(peak_e, abs(e))
        bits[i] = bit
    if not np.isfinite(e + w) or peak_w > 1 + 1e-12 or peak_e > 8 * np.max(holds):
        raise AssertionError('RC/error state invalid')
    return bits, dict(feedback_weight=feedback_weight,peak_voltage_error=peak_w,peak_error_feedback_seconds=peak_e,
                      peak_error_feedback_in_average_slots=peak_e/float(np.mean(holds)),
                      final_voltage_error=w,final_error_feedback_seconds=e,
                      final_integral_error_seconds=e-feedback_weight*older)


def capacitor_states(levels, holds, tau):
    """Exact capacitor voltage at every hold boundary; zero initial voltage."""
    a, c, _ = rc_coefficients(holds, tau)
    states = np.empty(len(levels) + 1, dtype=np.float64)
    states[0] = 0
    for i, (x, aa) in enumerate(zip(levels, a)):
        states[i + 1] = x + (states[i] - x) * aa
    areas = np.r_[0., np.cumsum(levels * holds + (states[:-1] - levels) * c)]
    return states, areas


def render_rc(levels, times, tau, rate, states=None, areas=None):
    """Analytically integrate capacitor voltage into uniform PCM bins.

    No approximation of pulse widths on a uniform grid precedes the RC model.
    Only the final waveform export is sampled; an antialias resampler follows.
    """
    holds = np.diff(times)
    if states is None:
        states, areas = capacitor_states(levels, holds, tau)
    count = int(np.floor(times[-1] * rate))
    result = np.empty(count, dtype=np.float32)
    for start in range(0, count, 500000):
        end = min(start + 500000, count)
        # PCM samples represent bin centres at n/rate. Centring the bins is
        # essential when comparing different export rates: otherwise their
        # half-bin time advances differ before the common resampler.
        edges = (np.arange(start, end + 1, dtype=np.float64)-.5) / rate
        indices = np.clip(np.searchsorted(times, edges, side='right') - 1, 0, len(levels) - 1)
        elapsed = np.maximum(0., edges - times[indices])
        integrals = (areas[indices] + levels[indices] * elapsed
                     - tau * (states[indices] - levels[indices]) * np.expm1(-elapsed / tau))
        # Unipolar physical voltage 0..1 becomes bipolar audio around 0.5.
        result[start:end] = 2 * np.diff(integrals) * rate - 1
    return result


def resample(signal, rate, ffmpeg):
    command = [ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le', '-ar', str(rate),
               '-ac', '1', '-i', '-', '-af',
               f'aresample={WAV_RATE}:resampler=soxr:precision=28', '-f', 'f32le', '-']
    result = subprocess.run(command, input=signal.astype('<f4', copy=False).tobytes(),
                            capture_output=True, check=True)
    return np.frombuffer(result.stdout, '<f4').astype(float)


def speech_band(signal, ffmpeg):
    result = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le',
                            '-ar', str(WAV_RATE), '-ac', '1', '-i', '-', '-af',
                            'highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2',
                            '-f', 'f32le', '-'], input=signal.astype('<f4').tobytes(),
                            capture_output=True, check=True)
    return np.frombuffer(result.stdout, '<f4').astype(float)


def metrics(wanted, actual):
    a, b = wanted[4410:-4410], actual[4410:-4410]
    error = b - a
    return dict(snr_db=float(10 * np.log10(np.mean(a * a) / np.mean(error * error))),
                error_rms=float(np.sqrt(np.mean(error * error))),
                correlation=float(np.corrcoef(a, b)[0, 1]),
                dc_error=float(np.mean(error)))


def analytic_checks(tau, feedback_weight):
    """Independent closed-form charging check and DC level preservation."""
    times = np.r_[0., np.cumsum(np.array([.7, .2, 1.3, .4, 2.]) * tau)]
    levels = np.ones(len(times)-1)
    states, areas = capacitor_states(levels, np.diff(times), tau)
    expected_states = 1-np.exp(-times/tau)
    expected_areas = times+tau*np.expm1(-times/tau)
    state_error = float(np.max(abs(states-expected_states)))
    area_error = float(np.max(abs(areas-expected_areas)))
    rate = WAV_RATE*16
    bins = render_rc(levels, times, tau, rate)
    edges = np.maximum(0.,(np.arange(len(bins)+1)-.5)/rate)
    exact = 2*np.diff(edges+tau*np.expm1(-edges/tau))*rate-1
    bin_error = float(np.max(abs(bins-exact)))
    if state_error>1e-13 or area_error>1e-15 or bin_error>1e-6:
        raise AssertionError('analytic RC step check failed')
    holds = np.tile(np.array([72,74,76,80],dtype=float)/CPU_CLOCK,8192)
    dc = []
    for level in (0.,.125,.5,.875,1.):
        target = np.full(len(holds),level);target[:3]=0
        bits, state = modulate(target,holds,tau,feedback_weight)
        _, ideal_area = capacitor_states(target,holds,tau)
        _, bit_area = capacitor_states(bits,holds,tau)
        mean_error = float((ideal_area[-1]-bit_area[-1])/sum(holds))
        if abs(mean_error)>1e-4:
            raise AssertionError('DC voltage tracking failed')
        dc.append(dict(target=level,mean_voltage_error=mean_error))
    return dict(analytic_step_state_error=state_error,analytic_step_area_error_seconds=area_error,
                analytic_bin_error=bin_error,dc_voltage_checks=dc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cutoff', type=float, default=20000)
    parser.add_argument('--feedback-weight', type=float, default=.5)
    parser.add_argument('--seconds', type=float, default=None)
    args = parser.parse_args()
    if not 0 < args.cutoff < WAV_RATE / 2:
        parser.error('cutoff must be below WAV Nyquist')
    if not 0 <= args.feedback_weight <= 1:
        parser.error('feedback weight must be in 0..1')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('use a new or empty output directory')
    args.output.mkdir(parents=True, exist_ok=True)
    source = HERE / 'ima-preview'
    archive = json.loads((source / 'report.json').read_bytes())
    for name in ('player.json', 'verification.json', 'soundtrack.ima.gz', 'output-times.u32.gz'):
        if sha((source / name).read_bytes()) != archive['artifacts'][name]['sha256']:
            raise AssertionError(f'baseline artifact changed: {name}')
    meta = json.loads((source / 'player.json').read_bytes())
    proof = json.loads((source / 'verification.json').read_bytes())
    disk = source / 'audiobook-preview.trd'
    if sha(disk.read_bytes()) != proof['fuse']['trd_sha256']:
        raise AssertionError('release disk changed')
    packed = gzip.decompress((source / 'soundtrack.ima.gz').read_bytes())
    _, _, levels, baseline_bits, count = reference(packed, meta)
    all_times = np.frombuffer(gzip.decompress((source / 'output-times.u32.gz').read_bytes()), '<u4')
    times = all_times[:count + 1].astype(np.float64) / CPU_CLOCK
    if args.seconds is not None:
        count = min(count, int(np.searchsorted(times, args.seconds)))
        times = times[:count + 1]
    if count < 10000 or times[0] != 0 or np.any(np.diff(times) <= 0):
        raise ValueError('invalid or too short timeline')
    baseline_bits = baseline_bits[:count]
    target = np.r_[np.zeros(3), levels[:count - 3].astype(float) / 256]
    holds = np.diff(times)
    tau = 1 / (2 * math.pi * args.cutoff)
    checks = analytic_checks(tau,args.feedback_weight)
    candidate_bits, generator = modulate(target, holds, tau, args.feedback_weight)
    control_bits, _ = modulate(target,holds,0,args.feedback_weight)
    rate = WAV_RATE * 16
    signals, states_for_check = {}, {}
    for name, samples in (('reference', target), ('baseline', baseline_bits),
                          ('rc-aware', candidate_bits),('same-feedback-no-rc',control_bits)):
        states, areas = capacitor_states(samples, holds, tau)
        if states.min() < -1e-12 or states.max() > 1 + 1e-12:
            raise AssertionError('capacitor voltage left supply rails')
        print(f'Rendering {name}: {count} holds', flush=True)
        signals[name] = resample(render_rc(samples, times, tau, rate, states, areas), rate, args.ffmpeg)
        if name == 'rc-aware':
            states_for_check = dict(states=states, areas=areas)
    frames = min(map(len, signals.values()))
    if max(map(len, signals.values())) != frames:
        raise AssertionError('rendered lengths differ')
    peaks = {name: float(np.max(abs(signal))) for name, signal in signals.items()}
    print('Rendered peaks: ' + json.dumps(peaks), flush=True)
    # Common attenuation also allows for antialias-resampler overshoot.
    # No independent normalization and no speech filter in the listening WAVs.
    gain = min(.8, .9 / max(peaks.values()))
    for name in ('baseline', 'rc-aware'):
        signal = signals[name] * gain
        if np.max(abs(signal)) >= 1:
            raise AssertionError('listening export would clip')
        write_wav(args.output / f'{name}-rc-preview.wav', signal)
        blob = np.packbits(baseline_bits if name == 'baseline' else candidate_bits).tobytes()
        (args.output / f'{name}.pdm.gz').write_bytes(gzip.compress(blob, mtime=0))
    filtered = {name: speech_band(signal, args.ffmpeg) for name, signal in signals.items()}
    rows = {name: dict(wideband=metrics(signals['reference'], signals[name]),
                       speech_band=metrics(filtered['reference'], filtered[name]))
            for name in ('baseline', 'rc-aware','same-feedback-no-rc')}
    for name in ('baseline','rc-aware'):
        signal = filtered[name]*gain
        if np.max(abs(signal))>=1:
            raise AssertionError('speech-band export would clip')
        write_wav(args.output/f'{name}-speech-preview.wav',signal)
    # Double the rendering rate for the full candidate, keeping pulse edges
    # and analytic capacitor states exact. This checks waveform export error.
    fine = resample(render_rc(candidate_bits,times,tau,rate*2,**states_for_check),rate*2,args.ffmpeg)
    common = min(len(fine),len(signals['rc-aware']))
    difference = fine[4410:common-4410]-signals['rc-aware'][4410:common-4410]
    checks['double_render_rate_difference_rms'] = float(np.sqrt(np.mean(difference*difference)))
    checks['double_render_rate_difference_peak'] = float(np.max(abs(difference)))
    print('Validation: '+json.dumps(checks),flush=True)
    print('Comparison: '+json.dumps(rows),flush=True)
    if checks['double_render_rate_difference_rms']>5e-4:
        raise AssertionError('RC waveform export has not converged')
    # Separate physical model conservation check: accumulated voltage error
    # equals the difference of the two independently rendered area totals.
    target_state, target_area = capacitor_states(target, holds, tau)
    actual_error = float(target_area[-1] - states_for_check['areas'][-1])
    if abs(actual_error - generator['final_integral_error_seconds']) > 1e-8:
        raise AssertionError('independent integrated RC error mismatch')
    if abs(float(target_state[-1] - states_for_check['states'][-1])
           - generator['final_voltage_error']) > 1e-10:
        raise AssertionError('independent capacitor state mismatch')
    report = dict(date='2026-10-02',host_experiment_complete=True,release=False,z80_ported=False,
                  trd_sha256=sha(disk.read_bytes()),duration_seconds=float(times[-1]),
                  source_start_seconds=60,slots=count,pdm_rate_hz=count/float(times[-1]),
                  cutoff_hz=args.cutoff,resistance_ohms=1000,capacitance_farads=tau/1000,
                  tau_seconds=tau,initial_capacitor_voltage=0,internal_render_rate_hz=rate,
                  generator='RC capacitor model plus damped error feedback on voltage area; causal one-slot bit choice',
                  reference='same RC driven by delayed decoded PCM8; not unfiltered original AAC',
                  target_delay_slots=3,generator_state=generator,
                  differing_bits=int(np.count_nonzero(candidate_bits != baseline_bits)),
                  packed_bit_order='MSB first; ignore padding bits beyond slots',
                  common_listening_gain=gain,independent_normalization=False,
                  unscaled_render_peaks=peaks,
                  listening_filters=f'ideal {args.cutoff:g} Hz RC and SOXR antialias resampling only',
                  speech_preview_and_analysis_filters='70 Hz highpass, two 2-pole 4.5 kHz lowpasses after RC',
                  excluded_edge_seconds=.1,metrics=rows,
                  validation=checks,
                  independent_area_error_difference_seconds=actual_error-generator['final_integral_error_seconds'],
                  sources={name:sha((source/name).read_bytes()) for name in
                           ('player.json','verification.json','soundtrack.ima.gz','output-times.u32.gz')},
                  producer_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
                  model_reference='https://openstax.org/books/university-physics-volume-2/pages/10-5-rc-circuits',
                  limitations=['New bits generated on PC, not by Z80 or Fuse',
                               'Saved baseline timings assumed; no new cycle counts or TRD',
                               'Ideal unloaded RC, not a measured Spectrum speaker circuit'],
                  files={f.name: inspect(f) for f in args.output.glob('*.wav')})
    report['speech_band_snr_change_db'] = rows['rc-aware']['speech_band']['snr_db'] - rows['baseline']['speech_band']['snr_db']
    report['rc_model_only_snr_change_db'] = rows['rc-aware']['speech_band']['snr_db']-rows['same-feedback-no-rc']['speech_band']['snr_db']
    report['bitstreams'] = {f.name:dict(sha256=sha(f.read_bytes()),bits=count) for f in args.output.glob('*.pdm.gz')}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(metrics=rows,change_db=report['speech_band_snr_change_db'],generator=generator)),flush=True)


if __name__ == '__main__':
    main()
