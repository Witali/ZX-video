"""Unfitted error, physical clock and explicitly fitted artifact diagnostics.

The fits below are indicators, never corrections to listening audio or SNR.
They separate constant drift from periodic clock disturbance and separate
linearized AM/delay from coherent additive hum. A finite corpus cannot prove
that an arbitrary source has no audible artifact. In particular a poor fixed-
clock match makes a small-signal modulation fit inapplicable, rather than good.
All levels are relative to a full-scale amplitude of 1; callers must use the
same gain, bandwidth, duration and fixed edge policy for every variant.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


RATE = 44100
# Commit/horizon, page and bank frequencies are based on the counted Pentagon
# average source rate, rather than selected from a favorable audio spectrum.
# Callers may pass exact instruction-derived frequencies for another machine.
FREQUENCIES = (.2436, 2., 5., 10., 15.589, 25., 50., 62.356, 100., 124.712)


def db(value):
    """Amplitude in dBFS; exact numerical zero is represented by None."""
    return float(20 * np.log10(value)) if value > 0 else None


def _crop_pair(reference, actual, rate, edge_seconds):
    x, y = np.asarray(reference, dtype=float), np.asarray(actual, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
        raise ValueError('The complete mono reference/output lengths must agree')
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError('Nonfinite audio samples')
    edge = round(edge_seconds * rate)
    stop = len(x) - edge if edge else len(x)
    if stop <= edge:
        raise ValueError('Signal is shorter than the fixed edge exclusion')
    return x[edge:stop], y[edge:stop], edge


def _harmonic(values, time, hz):
    """Least-squares DC + sine/cosine on the declared clock, not FFT bins."""
    phase = 2 * np.pi * hz * time
    matrix = np.column_stack((np.ones(len(time)), np.cos(phase), np.sin(phase)))
    gram, rhs = matrix.T @ matrix, matrix.T @ values
    coefficients = np.linalg.solve(gram, rhs)
    return dict(hz=float(hz), peak=float(np.hypot(*coefficients[1:])),
                cosine=float(coefficients[1]), sine=float(coefficients[2]))


def error_spectrum(error, *, rate=RATE, maximum_window=32768):
    """Whole-error Hann Welch bands and peaks, including tonal idle noise.

    DC is retained. A strongest-bin report is not an exact sinusoidal amplitude
    because a line can straddle neighboring bins. The three-bin energy fraction
    makes narrow whistles visible without relying exclusively on mains hum.
    """
    e=np.asarray(error,dtype=float)
    size=min(maximum_window,2**int(np.floor(np.log2(len(e)))))
    if size<16:
        return dict(available=False,reason='Signal too short for spectrum')
    window=np.hanning(size); spectrum=np.zeros(size//2+1); count=0
    starts=list(range(0,len(e)-size+1,size//2))
    if starts[-1]+size<len(e):starts.append(len(e)-size)
    for first in starts:
        spectrum+=np.abs(np.fft.rfft(e[first:first+size]*window))**2
        count+=1
    spectrum/=count*rate*float(window @ window)
    spectrum[1:-1]*=2
    frequencies=np.fft.rfftfreq(size,1/rate); width=rate/size
    power=spectrum*width;total=float(power.sum())
    bands=[]
    for low,high in ((0,20),(20,200),(200,1000),(1000,3500),(3500,4500),(4500,rate/2+1)):
        p=float(power[(frequencies>=low)&(frequencies<high)].sum())
        bands.append(dict(low_hz=low,high_hz=min(high,rate/2),rms=float(np.sqrt(p)),
                          rms_dbfs=db(np.sqrt(p))))
    eligible=np.flatnonzero((frequencies>=20)&(frequencies<=4500))
    peaks=eligible[np.argsort(power[eligible])[-8:][::-1]]
    return dict(available=True,window_samples=size,windows=count,bin_width_hz=width,
                window='Hann;50-percent overlap;one-sided density',bands=bands,
                every_error_sample_inside_a_window=True,
                spectral_total_error_rms=float(np.sqrt(total)),
                strongest_error_bins=[dict(hz=float(frequencies[i]),
                    density_per_hz=float(spectrum[i]),
                    three_bin_error_power_fraction=float(power[max(0,i-1):i+2].sum()/max(total,1e-30))) for i in peaks],
                caveat='On non-silent sources these are error peaks, not independently identified background. Welch windows include the whole declared edge-cropped scope.')


def cyclic_fit(reference, actual, hz, *, rate=RATE, edge_seconds=.1,
               stride=4, block=65536):
    """Fit gain, delay, sinusoidal AM/delay and additive DC/50/100-Hz hum.

    Delay is linearized at the original source clock. The derivative is scaled
    by 100 us to keep the normal matrix well conditioned. Normal equations are
    accumulated in bounded blocks so whole-song evaluation does not need a
    second full Nx11 matrix. The hum terms prevent injected additive hum being
    automatically interpreted as AM. Static gain/delay are nuisance terms only
    in this diagnostic; unfitted error remains the quality measurement.
    """
    whole = np.asarray(reference, dtype=float)
    x, y, edge = _crop_pair(whole, actual, rate, edge_seconds)
    derivative = np.gradient(whole) * rate * 1e-4
    ids = np.arange(0, len(x), stride)
    time = (ids + edge) / rate
    xs, ys, ds = x[ids], y[ids], derivative[ids + edge]
    width = 11
    gram = np.zeros((width, width)); rhs = np.zeros(width); yy = 0.
    for first in range(0, len(ids), block):
        part = slice(first, first + block)
        t, v, d = time[part], xs[part], ds[part]
        c, s = np.cos(2*np.pi*hz*t), np.sin(2*np.pi*hz*t)
        matrix = np.column_stack((v, d, v*c, v*s, d*c, d*s,
                                  np.ones(len(t)), np.cos(2*np.pi*50*t),
                                  np.sin(2*np.pi*50*t), np.cos(2*np.pi*100*t),
                                  np.sin(2*np.pi*100*t)))
        gram += matrix.T @ matrix; rhs += matrix.T @ ys[part]
        yy += float(ys[part] @ ys[part])
    norms = np.sqrt(np.maximum(np.diag(gram), 1e-30))
    normalized = gram / np.outer(norms, norms)
    eigenvalues = np.linalg.eigvalsh(normalized)
    condition = float(eigenvalues[-1] / max(eigenvalues[0], 1e-30))
    if eigenvalues[0] < 1e-10:
        return dict(hz=float(hz), available=False, reason='Rank-deficient source/diagnostic matrix',
                    condition=condition, fitted_diagnostic_only=True)
    coefficients = np.linalg.solve(normalized, rhs/norms) / norms
    base = [0, 1, 6, 7, 8, 9, 10]
    g0 = gram[np.ix_(base, base)]; r0 = rhs[base]
    b0 = np.linalg.solve(g0, r0)
    static_error = max(0., yy - float(b0 @ r0))
    full_error = max(0., yy - float(coefficients @ rhs))
    gain = float(coefficients[0])
    amplitude = abs(gain)
    # A low correlation or a vanishing fitted gain invalidates the small-
    # signal assumption. Do not call a wildly drifted old stream flutter-free.
    correlation = float(np.dot(xs, ys) / max(np.linalg.norm(xs)*np.linalg.norm(ys), 1e-30))
    cycles=hz*len(x)/rate
    applicable = abs(correlation) >= .8 and amplitude >= .1 and cycles>=3
    return dict(hz=float(hz), available=True, small_signal_applicable=applicable,
                fitted_constant_gain=gain, unfitted_correlation=correlation,
                frequency_cycles_observed=float(cycles),periodic_estimate_well_observed=cycles>=3,
                fitted_constant_linearized_delay_us=float(coefficients[1]/max(amplitude, 1e-30)*100),
                am_peak_percent=float(np.hypot(*coefficients[2:4])/max(amplitude, 1e-30)*100),
                linearized_delay_peak_us=float(np.hypot(*coefficients[4:6])/max(amplitude, 1e-30)*100),
                linearized_speed_peak_percent=float(2*np.pi*hz*np.hypot(*coefficients[4:6])/max(amplitude, 1e-30)*.01),
                fitted_hum_peak={str(f):float(np.hypot(*coefficients[k:k+2])) for f,k in ((50,7),(100,9))},
                fitted_residual_rms=float(np.sqrt(full_error/len(ids))),
                diagnostic_error_power_reduction_db=float(10*np.log10(max(static_error, 1e-30)/max(full_error, 1e-30))),
                condition=condition, fitted_diagnostic_only=True,
                caveat='Linearized source-correlated indicators; not a pitch tracker, noise guarantee or fitted SNR')


def waveform_diagnostics(reference, actual, *, rate=RATE, edge_seconds=.1,
                         frequencies=FREQUENCIES):
    """Whole filtered fixed-clock waveform error and modulation indicators."""
    x, y, edge = _crop_pair(reference, actual, rate, edge_seconds)
    error = y - x
    signal_power = float(np.mean(x*x)); error_power = float(np.mean(error*error))
    source_rms, noise_rms = np.sqrt(signal_power), np.sqrt(error_power)
    # Coherent additive components are measured directly in the unfitted
    # error. On music they may include pre-existing source content changed by
    # transfer error; silence and known-tone controls identify added hum.
    ids = np.arange(0, len(error), 4)
    time = (ids + edge)/rate
    hum = [_harmonic(error[ids], time, f) for f in (50., 100., 150., 200.)]
    for row in hum:
        row['peak_dbfs'] = db(row['peak'])
    return dict(samples=len(reference), measured_samples=len(x), rate_hz=rate,
                edge_exclusion_seconds=edge_seconds,
                scope='Original source clock; complete signal except fixed edges; no fitted gain/delay/clock',
                source_rms=float(source_rms), error_rms=float(noise_rms),
                error_rms_dbfs=db(noise_rms), error_peak=float(np.max(np.abs(error))),
                output_dc=float(np.mean(y)), error_dc=float(np.mean(error)),
                fixed_clock_snr_db=(float(10*np.log10(signal_power/error_power))
                                    if signal_power > 1e-24 and error_power > 0 else None),
                silence_reference=signal_power <= 1e-24,
                coherent_unfitted_error_components=hum,
                error_spectrum=error_spectrum(error,rate=rate),
                modulation=[cyclic_fit(reference, actual, f, rate=rate,
                                       edge_seconds=edge_seconds) for f in frequencies],
                limitations='Fits are diagnostic only. Inapplicable/rank-deficient fits are inconclusive. Music error harmonics alone cannot distinguish added hum from changed source content. Silence absolute noise and generated tone controls are required.')


def tone_diagnostics(reference, actual, carrier_hz, *, rate=RATE,
                     edge_seconds=.1, frequencies=FREQUENCIES):
    """Known-tone narrowband amplitude/phase and average frequency drift.

    Four carrier cycles per local quadrature fit isolate the fundamental from
    DC and much of the quantizer noise. The window response is reported rather
    than quietly fitted away. Fast artifact decisions use cyclic_fit above;
    these overlapping windows show slower phase/amplitude trends and drift.
    A weak/noisy fundamental makes phase unwrapping unreliable and is labelled.
    """
    x, y, edge = _crop_pair(reference, actual, rate, edge_seconds)
    size = max(32, round(4*rate/carrier_hz)); hop = max(1, size//4)
    centers = []; amplitudes = [[], []]; phases = [[], []]; correlations = []
    for first in range(0, len(x)-size+1, hop):
        t = (np.arange(first, first+size) + edge)/rate
        matrix = np.column_stack((np.cos(2*np.pi*carrier_hz*t),
                                  np.sin(2*np.pi*carrier_hz*t), np.ones(size)))
        gram = matrix.T @ matrix
        coefficients = np.linalg.solve(gram, matrix.T @ np.column_stack((x[first:first+size], y[first:first+size])))
        fitted = matrix[:,:2] @ coefficients[:2]
        for k in (0, 1):
            amplitudes[k].append(float(np.hypot(*coefficients[:2,k])))
            phases[k].append(float(np.arctan2(coefficients[0,k], coefficients[1,k])))
        correlations.append(float(np.mean(fitted[:,1]**2)/max(np.mean(y[first:first+size]**2),1e-30)))
        centers.append(float(t.mean()))
    if len(centers) < 8:
        raise ValueError('Too few complete tone windows')
    t = np.asarray(centers)
    amplitude = np.asarray(amplitudes[1])/np.maximum(amplitudes[0],1e-30)
    phase = np.unwrap(phases[1])-np.unwrap(phases[0])
    design = np.column_stack((np.ones(len(t)), t-t.mean()))
    constant, slope = np.linalg.lstsq(design, phase, rcond=None)[0]
    residual = phase-design @ np.array([constant,slope])
    harmonic = []
    for f in frequencies:
        am = _harmonic(amplitude/amplitude.mean()-1,t,f)
        pm = _harmonic(residual,t,f)
        harmonic.append(dict(hz=float(f), am_peak_percent=100*am['peak'],
                             phase_peak_radians=pm['peak'],
                             phase_equivalent_delay_peak_us=pm['peak']/(2*np.pi*carrier_hz)*1e6,
                             window_response_estimate=float(abs(np.sinc(f*size/rate))),
                             periodic_estimate_well_observed=bool(f*(t[-1]-t[0])>=3)))
    quality = float(np.median(correlations))
    return dict(carrier_hz=float(carrier_hz), window_samples=size, hop_samples=hop,
                average_frequency_shift_hz=float(slope/(2*np.pi)),
                average_speed_shift_percent=float(slope/(2*np.pi*carrier_hz)*100),
                fundamental_fit_output_power_fraction_median=quality,
                phase_tracking_reliable=quality >= .8 and float(np.median(amplitudes[0]))>1e-9,
                amplitude_ratio_median=float(np.median(amplitude)),
                amplitude_ratio_p01_p99=np.percentile(amplitude,[1,99]).tolist(),
                phase_residual_p01_p99_radians=np.percentile(residual,[1,99]).tolist(),
                modulation=harmonic, fitted_diagnostic_only=True,
                caveat='Local fundamental fits and average drift removal are diagnostics only; short-window response attenuates fast modulation. Use unfitted SNR and cyclic-fit controls for acceptance.')


def clock_diagnostics(pulse_edges, *, cpu_hz, source_rate_hz=8000,
                      pulses_per_sample=16, frequencies=FREQUENCIES):
    """Measure every actual pulse/sample interval without using audio values.

    Input must include the final pulse endpoint in native CPU T-states (or use
    the corresponding reference CPU when a trace has been normalized). Sparse
    bank/page tails remain in the statistics. Complete groups only define the
    sample clock; a final partial group is reported, not silently completed.
    """
    edges = np.asarray(pulse_edges,dtype=float)
    if edges.ndim != 1 or len(edges) < pulses_per_sample+1 or not np.all(np.isfinite(edges)) or np.any(np.diff(edges)<=0):
        raise ValueError('Expected strictly increasing complete actual pulse edges')
    seconds = (edges-edges[0])/cpu_hz
    sample_edges = seconds[::pulses_per_sample]
    durations = np.diff(sample_edges)
    mean = float(durations.mean()); interval_error = durations/mean-1
    centers = (sample_edges[:-1]+sample_edges[1:])/2
    ideal = np.arange(len(sample_edges))/source_rate_hz
    average_rate = 1/mean
    drift_removed = sample_edges-np.arange(len(sample_edges))*mean
    periodic = [_harmonic(interval_error,centers,f) for f in frequencies]
    windows=[]
    for milliseconds in (5,20):
        count=max(1,round(milliseconds*.001*source_rate_hz))
        if len(sample_edges)<=count:
            windows.append(dict(window_ms=milliseconds,available=False,
                                reason='Trace is shorter than the declared window'))
            continue
        span=sample_edges[count:]-sample_edges[:-count]
        speeds=count/span/source_rate_hz-1
        windows.append(dict(window_ms=milliseconds, measured_intervals=count,
                            speed_deviation_percent_min_max=(100*np.array([speeds.min(),speeds.max()])).tolist(),
                            speed_deviation_percent_p01_p99=(100*np.percentile(speeds,[1,99])).tolist()))
    holds=np.diff(seconds)
    return dict(cpu_hz=float(cpu_hz), source_rate_hz=source_rate_hz,
                complete_samples=len(durations), final_partial_pulses=(len(edges)-1)%pulses_per_sample,
                duration_seconds=float(seconds[-1]), average_sample_rate_hz=average_rate,
                average_speed_deviation_percent=(average_rate/source_rate_hz-1)*100,
                accumulated_time_drift_ms=float((sample_edges[-1]-ideal[-1])*1000),
                drift_removed_time_excursion_us=float(np.ptp(drift_removed)*1e6),
                largest_actual_pulse_hold_us=float(holds.max()*1e6),
                pulse_hold_percentiles_us={str(p):float(np.percentile(holds,p)*1e6) for p in (50,99,99.99,100)},
                sample_interval_percentiles_us={str(p):float(np.percentile(durations,p)*1e6) for p in (0,50,99,99.99,100)},
                periodic_interval_deviation=[dict(hz=r['hz'],peak_percent=r['peak']*100,
                    periodic_estimate_well_observed=bool(r['hz']*(sample_edges[-1]-sample_edges[0])>=3)) for r in periodic],
                window_speed=windows,
                scope='All actual transport intervals; source independent; mean drift separated from periodic disturbance; no waveform or fitted SNR',
                limitation='A transport irregularity may be compensated by offline waveform encoding; this does not make the physical sample clock uniform. The largest hold is evidence, not by itself proof of an audible pause.')


def compare_reports(before, after):
    """Expose numerical regressions; do not silently invent an audible gate."""
    a,b=before['waveform'],after['waveform']
    result=dict(from_variant=before['variant'],to_variant=after['variant'],
                fixed_snr_change_db=(b['fixed_clock_snr_db']-a['fixed_clock_snr_db']
                                     if a['fixed_clock_snr_db'] is not None and b['fixed_clock_snr_db'] is not None else None),
                error_rms_change_db=(20*np.log10(b['error_rms']/a['error_rms'])
                                     if min(a['error_rms'],b['error_rms'])>0 else None),
                modulation=[],coherent_error=[])
    for old,new in zip(a['modulation'],b['modulation']):
        valid=old.get('small_signal_applicable',False) and new.get('small_signal_applicable',False)
        row=dict(hz=old['hz'],both_small_signal_applicable=valid)
        if valid:
            row['am_peak_percent_change']=new['am_peak_percent']-old['am_peak_percent']
            row['linearized_delay_peak_us_change']=new['linearized_delay_peak_us']-old['linearized_delay_peak_us']
        else:row['reason']='At least one source-clock fit is inapplicable or rank deficient; absence is unproven'
        result['modulation'].append(row)
    for old,new in zip(a['coherent_unfitted_error_components'],b['coherent_unfitted_error_components']):
        result['coherent_error'].append(dict(hz=old['hz'],peak_change=new['peak']-old['peak'],
                                            peak_ratio_db=(20*np.log10(new['peak']/old['peak'])
                                                           if min(old['peak'],new['peak'])>0 else None)))
    result['numeric_regressions']=dict(
        unfitted_snr=int(result['fixed_snr_change_db'] is not None and result['fixed_snr_change_db'] < -1e-10),
        absolute_error_rms=int(b['error_rms']>a['error_rms']+1e-10),
        applicable_am=sum(r.get('am_peak_percent_change',0)>1e-10 for r in result['modulation']),
        applicable_delay=sum(r.get('linearized_delay_peak_us_change',0)>1e-10 for r in result['modulation']),
        coherent_error_lines=sum(r['peak_change']>1e-10 for r in result['coherent_error']),
        inconclusive_modulation=sum(not r['both_small_signal_applicable'] for r in result['modulation']))
    result['interpretation']='Numerical increases above1e-10 are disclosed, not an audibility threshold. Any SNR gain alone is insufficient to accept a candidate. Inapplicable legacy drift fits are missing artifact evidence.'
    return result


def corpus_diagnostics(evidence, cache, scratch, output, *, ffmpeg=None):
    """Reproduce before/compensation/joint diagnostics from completed controls.

    Existing NPY arrays preserve the exact unscaled renderer output. A legacy
    baseline is rendered with the original packed stream and common timeline.
    New whole-corpus controls remain host predictions; only the historical
    whole-song timeline has separately authenticated full-emulator provenance.
    Calling again after another host.json arrives fills missing candidates.
    """
    from build_pdm import CPU_CLOCK
    from clock_control import score
    from convert_mulaw_audio import STABLE_FILTER
    from general import models,timeline
    from probe_reconstruction_error import wav8
    evidence,cache,scratch,output=map(Path,(evidence,cache,scratch,output))
    output.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    baseline_cache=scratch/'baseline-arrays';baseline_cache.mkdir(exist_ok=True)
    ffmpeg=ffmpeg or shutil.which('ffmpeg')
    names=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam')
    report=dict(complete=False,source_independent_diagnostic_settings=True,
                frequencies_hz=list(FREQUENCIES),edge_exclusion_seconds=.1,
                fitted_snr=False,new_emulator_verification=False,sources=[],
                acceptance_ambiguities=[
                    'The5-dB whole-song target uses unfitted original-clock SNR; shared-clock codec scores cannot satisfy it.',
                    'A finite corpus plus diagnostic fits cannot establish absence on every possible source.',
                    'Strict absence of introduced AM/FM has no supplied audibility threshold. Every numerical increase is disclosed; an inapplicable fit is missing proof, not a pass.',
                    'Music coherent error lines are not uniquely added hum. Silence absolute noise and quiet known-tone spectra are the decisive background controls.',
                    'The physical sample clock retains deterministic page/bank irregularities even if the offline encoder compensates their waveform effect.',
                    'Whole new cold-boot emulator traces and bank/refill proofs are required before any host candidate is accepted.',
                    'Tone phase tracking is inconclusive when the carrier explains less than80-percent of output power.'],
                candidate_gates=dict(snr='Whole sea-foam unfitted source-clock improvement>=5dB; common settings on all sources',
                                     noise='Silence absolute error RMS and idle-whistle energy must not increase; compare coherent error lines on known controls',
                                     modulation='Compare only applicable fits and reliable known-tone phase tracking; investigate every increase; missing proof must remain explicit',
                                     timing='Actual native/Fuse pulse schedule and largest hold; no new disk/RAM-bank pause; average source drift and periodic disturbance reported separately'))
    totals={};hashes={}
    for name in names:
        source_path=evidence/'general/inputs'/(name+'.wav')
        packed_path=evidence/'general/inputs'/(name+'.ima.gz')
        source=wav8(source_path);packed=gzip.decompress(packed_path.read_bytes())
        times=timeline(len(source),'pentagon')
        # Cache reuse requires identical renderer/table producers, schedule,
        # source and legacy model, rather than merely a matching audio name.
        digest=hashlib.sha256(packed+source.tobytes())
        digest.update(memoryview(times))
        digest.update(json.dumps(dict(model=dict(models())['legacy'],filter=STABLE_FILTER),sort_keys=True).encode())
        for producer in ('clock_control.py','study.py','general.py'):
            digest.update((Path(__file__).parent/producer).read_bytes().replace(b'\r\n',b'\n'))
        for producer in ('probe_feedback_packets.py','verify_direct.py','convert_mulaw_audio.py'):
            digest.update((Path(__file__).parent.parent.parent/producer).read_bytes().replace(b'\r\n',b'\n'))
        key=digest.hexdigest()
        baseline_path=baseline_cache/(name+'-'+key+'-actual.npy')
        reference_path=baseline_cache/(name+'-'+key+'-reference.npy')
        if baseline_path.exists() and reference_path.exists():
            wanted=np.load(reference_path);actual=np.load(baseline_path)
        else:
            _,wanted,actual=score(source,packed,dict(models())['legacy'],times,ffmpeg,scratch)
            np.save(reference_path,wanted);np.save(baseline_path,actual)
        hashes[name]=dict(source_file_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                          source_pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                          legacy_packed_sha256=hashlib.sha256(packed).hexdigest())
        variants={}
        for label in ('before','compensation','joint'):
            if label=='before':ref,y,host=wanted,actual,None
            else:
                folder='clock-'+label
                hostpath=evidence/folder/name/'host.json'
                candidate=cache/folder/(name+'-'+label+'-actual.npy')
                refpath=cache/folder/(name+'-reference.npy')
                if not(hostpath.exists() and candidate.exists() and refpath.exists()):continue
                ref,y=np.load(refpath),np.load(candidate)
                np.testing.assert_array_equal(ref,wanted)
                host=json.loads(hostpath.read_bytes())
            data=dict(source=name,variant=label,source_identity=hashes[name],
                      actual_float64_sha256=hashlib.sha256(y.astype('<f8').tobytes()).hexdigest(),
                      reference_float64_sha256=hashlib.sha256(ref.astype('<f8').tobytes()).hexdigest(),
                      waveform=waveform_diagnostics(ref,y),
                      new_emulator_verified=False,host_metadata=host)
            if name in ('quiet440','quiet997','loud3000'):
                data['known_tone']=tone_diagnostics(ref,y,dict(quiet440=440,quiet997=997,loud3000=3000)[name])
            variants[label]=data
            (output/(name+'-'+label+'.json')).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        comparisons=[]
        for old,new in (('before','compensation'),('before','joint'),('compensation','joint')):
            if old not in variants or new not in variants:continue
            comparison=compare_reports(variants[old],variants[new]);comparisons.append(comparison)
            pair=old+'->'+new
            bucket=totals.setdefault(pair,dict(source_comparisons=0))
            bucket['source_comparisons']+=1
            for k,v in comparison['numeric_regressions'].items():bucket[k]=bucket.get(k,0)+int(v)
        (output/(name+'-comparisons.json')).write_text(json.dumps(comparisons,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        report['sources'].append(dict(source=name,available_variants=list(variants),comparisons=comparisons))
        print(json.dumps(dict(source=name,variants={k:v['waveform']['fixed_clock_snr_db'] for k,v in variants.items()})),flush=True)
        report['regression_counts']=totals
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    count=(len(source)-3)*16+15
    # The source-independent schedule is identical for every candidate stream.
    report['whole_song_instruction_derived_clock']=clock_diagnostics(times[:count],cpu_hz=CPU_CLOCK)
    recorded=evidence/'study/inputs/song/verification/pentagon512/times.u32.gz'
    if recorded.exists():
        raw=np.frombuffer(gzip.decompress(recorded.read_bytes()),'<u4').astype(float)
        np.testing.assert_allclose(times[:count]*3584000/CPU_CLOCK,raw,rtol=0,atol=1e-7)
        report['whole_song_authenticated_legacy_clock']=clock_diagnostics(raw,cpu_hz=3584000)
        report['every_new_host_interval_matches_authenticated_legacy_clock']=True
    report['source_identities']=hashes
    report['producer_sha256_lf']=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    report['complete']=all(len(row['available_variants'])==3 for row in report['sources'])
    report['decision']='No unconditional new release passes all artifact requirements on these host diagnostics. SNR gains and every diagnostic regression remain separate; full new emulator and missing artifact proof are required.'
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-npy',type=Path)
    parser.add_argument('--actual-npy',type=Path)
    parser.add_argument('--pulse-times-gz',type=Path)
    parser.add_argument('--cpu-hz',type=float)
    parser.add_argument('--carrier-hz',type=float)
    parser.add_argument('--corpus-evidence',type=Path)
    parser.add_argument('--cache',type=Path)
    parser.add_argument('--scratch',type=Path)
    parser.add_argument('--ffmpeg')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(); result={}
    if args.corpus_evidence:
        if not(args.cache and args.scratch):parser.error('Corpus mode requires --cache and --scratch')
        corpus_diagnostics(args.corpus_evidence,args.cache,args.scratch,args.output,ffmpeg=args.ffmpeg)
        return
    if args.reference_npy or args.actual_npy:
        if not(args.reference_npy and args.actual_npy):parser.error('Supply both audio NPY files')
        x,y=np.load(args.reference_npy),np.load(args.actual_npy)
        result['waveform']=waveform_diagnostics(x,y)
        if args.carrier_hz:result['tone']=tone_diagnostics(x,y,args.carrier_hz)
    if args.pulse_times_gz:
        if not args.cpu_hz:parser.error('Native pulse timestamps require --cpu-hz')
        times=np.frombuffer(gzip.decompress(args.pulse_times_gz.read_bytes()),'<u4')
        result['clock']=clock_diagnostics(times,cpu_hz=args.cpu_hz)
    if not result:parser.error('Supply audio or actual pulse timestamps')
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':main()
