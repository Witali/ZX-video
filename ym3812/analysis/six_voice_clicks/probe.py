"""Diagnose field-boundary discontinuities in the retained six-voice audition."""
from pathlib import Path
import json
import sys
import wave
import numpy as np

CORE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CORE))
import experimental_six_voice as synth
from simulation_refine import spectra


def read_wav(path):
    with wave.open(str(path), 'rb') as stream:
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').astype(float)/32768, stream.getframerate()


def boundary_jumps(controls, gain):
    """Evaluate the old/new controls at the SAME oscillator/noise phase.

    This excludes ordinary square-wave edges and LFSR transitions. A nonzero
    result is a discontinuity introduced by control changes alone, before the
    output coupling/filter. DC steps use the ensemble mean of each mixer mode.
    """
    count = synth.validate(controls)
    phase = np.zeros(6)
    noise_phase = 0.
    noise_index = 0
    bits = synth.noise_cycle()
    jumps = []
    dc = []
    for tick in range(count):
        bit = bits[noise_index]
        if tick:
            values = []
            means = []
            for state in (tick-1, tick):
                level = synth.LEVELS[controls['volumes'][state]]*gain
                mode = controls['modes'][state]
                tone = np.array([synth.waveform(int(shape), np.array([p]))[0]
                                 for shape, p in zip(controls['shapes'][state], phase)])
                tone[mode == 1] = 1.
                tone[mode != 0] *= bit
                values.append(float(level @ tone))
                means.append(float(level @ np.where(mode == 2, .25, .5)))
            jumps.append(values[1]-values[0])
            dc.append(means[1]-means[0])
        phase = (phase + synth.CLOCK/(16*controls['periods'][tick].astype(float)*50)) % 1
        advance = noise_phase + synth.CLOCK/(16*int(controls['noise_periods'][tick])*50)
        noise_index = (noise_index+int(advance)) % len(bits)
        noise_phase = advance % 1
    jumps, dc = np.asarray(jumps), np.asarray(dc)
    top = np.argsort(abs(jumps))[-12:][::-1]
    active = controls['volumes'] > 0
    both = active[1:] & active[:-1]
    cents = abs(1200*np.log2(controls['periods'][1:].astype(float)/controls['periods'][:-1]))
    return dict(control_jump_rms=float(np.sqrt(np.mean(jumps**2))),
                control_jump_max=float(abs(jumps).max()),
                dc_step_rms=float(np.sqrt(np.mean(dc**2))),
                dc_step_max=float(abs(dc).max()),
                active_shape_changes=int(((controls['shapes'][1:] != controls['shapes'][:-1]) & both).sum()),
                active_mode_changes=int(((controls['modes'][1:] != controls['modes'][:-1]) & both).sum()),
                active_pitch_jumps_over_semitone=int(((cents > 100) & both).sum()),
                top_boundaries=[dict(seconds=float((i+1)/50), jump=float(jumps[i]), dc_step=float(dc[i])) for i in top])


def artifacts(audio, reference):
    """Signal diagnostics, not a click detector or an intelligibility score.

    Derivative energy compares equal 1-ms windows at 20-ms boundaries and
    half-field offsets. The narrow high-frequency excess proxy measures bins
    above both the reference and a source-only audibility floor; it is useful
    for synthetic ringing but also counts legitimate waveform harmonics.
    """
    from noise_colour import downsample
    model = downsample(audio)
    count = len(reference)//441
    delta = np.diff(audio)
    def window_energy(centres):
        indices = centres[:, None]+np.arange(-22, 22)
        return np.mean(delta[np.clip(indices, 0, len(delta)-1)]**2, axis=1)
    boundaries = np.arange(1, count)*882
    edge, interior = window_energy(boundaries), window_energy(boundaries+441)
    wanted = spectra(reference, np.arange(count), 512)
    observed = spectra(model, np.arange(count), 512)
    hz = np.fft.rfftfreq(1024, 1/22050)
    high = (hz >= 1800) & (hz <= 8000)
    source_floor = np.maximum(wanted.max(axis=1)*.03, 1e-5)
    excess = np.maximum(observed[:, high]-2*wanted[:, high]-source_floor[:, None], 0)
    # The previous quality objective cannot see this 9..20-kHz output band.
    window = np.hanning(2048)
    frames = audio[:len(audio)//2048*2048].reshape(-1,2048)
    power = abs(np.fft.rfft(frames*window,axis=1))**2
    frequency = np.fft.rfftfreq(2048,1/44100)
    high_fraction = power[:,frequency>=9000].sum()/max(power.sum(),1e-20)
    return dict(boundary_derivative_rms=float(np.sqrt(edge.mean())),
                interior_derivative_rms=float(np.sqrt(interior.mean())),
                boundary_to_interior_power_ratio=float(edge.mean()/max(interior.mean(), 1e-20)),
                boundary_derivative_p95=float(np.sqrt(np.percentile(edge, 95))),
                output_power_above_9khz_fraction=float(high_fraction),
                high_band_excess_rms=float(np.sqrt(np.mean(excess**2))),
                high_band_excess_fields=int((excess.max(axis=1) > .03).sum()))


if __name__ == '__main__':
    folder = CORE/'analysis/six_voice/evidence'
    info = json.loads((folder/'report.json').read_bytes())
    with np.load(folder/'selectable-controls.npz') as stored:
        controls = {name: stored[name] for name in stored.files}
    reference, _ = read_wav(folder/'reference.wav')
    audio, _ = read_wav(folder/'six-voice-preview.wav')
    result = dict(boundaries=boundary_jumps(controls, info['results']['selectable']['feedback']['voice_gain']),
                  artifacts=artifacts(audio, reference))
    print(json.dumps(result, indent=2))
