"""Fit shared-noise colour against actual, continuous Ayumi chip renders.

Only R6 and the already selected noise carrier's shared volume may change.
The 93 candidates cover periods 1..31 and 0..2 downward volume steps; limiting
attenuation protects the carrier's tone. Each candidate renders the complete
sequence, so tone gates, DAC levels, phase, counters and filters participate.
Selection is a spectral approximation: splicing candidate periods changes the
final pseudorandom sequence. Always evaluate the newly rendered final stream.
"""
import gzip
from pathlib import Path
import subprocess
import tempfile
import numpy as np

HERE = Path(__file__).resolve().parent
PERIODS = np.tile(np.arange(1,32),3)
DELTAS = np.repeat([-2,-1,0],31)
SIZES = (512,2048,8192)


def spectra_at(samples, ticks, size):
    """The same centred Hann/2x FFT convention as the independent evaluator."""
    window = np.hanning(size)
    centres = np.rint((np.asarray(ticks)+.5)*441).astype(int)
    padded = np.pad(samples,(size//2,size//2))
    segments = padded[centres[:,None]+np.arange(size)]
    hz = np.fft.rfftfreq(size*2,1/22050)
    return abs(np.fft.rfft(segments*window,n=size*2,axis=1))[:,(hz>=50)&(hz<=8000)]/(window.sum()/2)


def choose_path(cost, ticks):
    """Minimize spectral dB error plus a small period/level jump penalty.

    Dynamic programming restarts at every gap in detected noise. Costs are
    per 20-ms state. .15 dB per octave of R6 movement and per volume step
    discourages chatter without moving attacks or imposing a coarser grid.
    """
    if cost.shape != (len(ticks),len(PERIODS)):
        raise ValueError('wrong candidate cost dimensions')
    if not np.isfinite(cost).all():
        raise ValueError('nonfinite noise fit cost')
    transition = .15*abs(np.log2(PERIODS[:,None]/PERIODS[None,:]))+.15*abs(DELTAS[:,None]-DELTAS[None,:])
    selected = np.empty(len(ticks),dtype=int)
    start = 0
    while start < len(ticks):
        end = start+1
        while end < len(ticks) and ticks[end] == ticks[end-1]+1:
            end += 1
        previous,history = cost[start].copy(),[]
        for t in range(start+1,end):
            edges = previous[:,None]+transition
            best = edges.argmin(axis=0)
            history.append(best)
            previous = cost[t]+edges[best,np.arange(len(PERIODS))]
        selected[end-1] = previous.argmin()
        for t in range(end-2,start-1,-1):
            selected[t] = history[t-start][selected[t+1]]
        start = end
    return selected


def apply_choices(raw, ticks, selected):
    result = raw.copy()
    for tick,choice in zip(ticks,selected):
        result[tick,6] = PERIODS[choice]
        for channel in range(3):
            if not raw[tick,7] & (1 << (channel+3)):
                result[tick,8+channel] = max(1,int(raw[tick,8+channel])+int(DELTAS[choice]))
    return result


def optimize(samples, registers, node, *, work_parent=None):
    """Return fitted R0..R10 bytes and a compact reproducible search report.

    One fixed source/model RMS ratio is calibrated from the input stream;
    there is no per-frame gain fitting. Equal weights on three full-bin STFT
    log errors distinguish broadband excess between strong harmonic peaks.
    Bound memory by evaluating at most 128 noisy states per FFT batch.
    """
    raw = np.frombuffer(registers,dtype=np.uint8).reshape(-1,11)
    samples = np.asarray(samples,dtype=float)
    if len(samples) != len(raw)*441 or not np.isfinite(samples).all():
        raise ValueError('expected finite mono 22050-Hz audio, 441 samples per state')
    ticks = np.flatnonzero(raw[:,6])
    info = dict(model='Ayumi continuous YM2149 spectral noise fit v1',
        update_rate_hz=50,quantum_ms=20,candidate_count=93,period_range=[1,31],
        shared_volume_deltas=[-2,-1,0],window_sizes=list(SIZES),frequency_hz=[50,8000],
        objective='mean of three unpooled log-magnitude MAE values; source-relative -60 dB floor',
        transition_penalty_db_per_octave_and_volume_step=.15,noise_ticks=len(ticks),
        limitations='Candidate streams have continuous phase; the chosen sequence has a different LFSR history. Final rendering and independent emulator validation are required. No analogue circuit or source-separation accuracy claim.')
    if not len(ticks):
        return registers,dict(info,skipped='no detected noise',changed_period_ticks=0,changed_volume_ticks=0)
    # This stage must not change the tracker or silently route a new channel.
    for tick in ticks:
        enabled = [c for c in range(3) if not raw[tick,7] & (1 << (c+3))]
        if len(enabled) != 1 or raw[tick,8+enabled[0]] == 0:
            raise ValueError('noise fit requires exactly one audible existing carrier')
    cost = np.empty((len(ticks),93))
    sources = []
    floors = []
    for size in SIZES:
        parts = [spectra_at(samples,ticks[a:a+128],size) for a in range(0,len(ticks),128)]
        sources.append(parts)
        floors.append(max(max(float(part.max()) for part in parts)*.001,1e-15))
    with tempfile.TemporaryDirectory(prefix='ay-noise-',dir=work_parent) as temporary:
        root = Path(temporary)
        input_path = root/'registers.gz'
        input_path.write_bytes(gzip.compress(registers,mtime=0))
        subprocess.run([str(node),str(HERE/'render_ym2149.js'),str(input_path),
            str(root/'baseline.f32'),'50',str(root/'baseline.json')],check=True)
        baseline = np.fromfile(root/'baseline.f32',dtype='<f4')[::2].astype(float)
        gain = float(np.sqrt(np.mean(samples**2)/max(np.mean(baseline**2),1e-20)))
        for group,delta in enumerate((-2,-1,0)):
            print(f'Noise colour: render and compare 31 periods, volume delta {delta}',flush=True)
            subprocess.run([str(node),str(HERE/'render_noise_candidates.js'),str(input_path),str(root),str(delta)],check=True)
            for period in range(1,32):
                path = root/f'noise-{period}.f32'
                audio = np.fromfile(path,dtype='<f4').astype(float)*gain
                path.unlink()
                if len(audio) != len(samples) or not np.isfinite(audio).all():
                    raise ValueError('incomplete or invalid noise model render')
                for part,start in enumerate(range(0,len(ticks),128)):
                    errors = []
                    for size,reference,floor in zip(SIZES,sources,floors):
                        a = reference[part]
                        b = spectra_at(audio,ticks[start:start+128],size)
                        support = (a > floor) | (b > floor)
                        error = abs(20*np.log10(np.maximum(a,floor)/np.maximum(b,floor)))
                        errors.append((error*support).sum(axis=1)/np.maximum(support.sum(axis=1),1))
                    cost[start:start+128,group*31+period-1] = np.mean(errors,axis=0)
    selected = choose_path(cost,ticks)
    result = apply_choices(raw,ticks,selected)
    info.update(global_source_model_rms_gain=gain,
        changed_period_ticks=int(np.sum(raw[:,6] != result[:,6])),
        changed_volume_ticks=int(np.any(raw[:,8:] != result[:,8:],axis=1).sum()),
        period_histogram={str(p):int(np.sum(result[ticks,6] == p)) for p in range(1,32)},
        volume_delta_histogram={str(d):int(np.sum(DELTAS[selected] == d)) for d in (-2,-1,0)},
        mean_selected_candidate_error_db=float(cost[np.arange(len(ticks)),selected].mean()),
        states=[dict(tick=int(t),old_period=int(raw[t,6]),period=int(result[t,6]),
            volume_delta=int(DELTAS[c]),candidate_error_db=float(cost[j,c])) for j,(t,c) in enumerate(zip(ticks,selected))])
    return result.tobytes(),info
