"""Separate waveform modulation, cyclic error power and Windows transport.

Fitted AM/delay indicators are diagnostics, not codec SNR or a pitch tracker.
They are never applied to delivered listening audio. All five parts are used.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import wave

import numpy as np
from audit_direct_regression import fixed_reference
from build_pdm import write_wav
from record_pcm import read_fmf

CPU, FIELD, RATE = 3546900, 70908, 44100


def wav(data):
    with wave.open(io.BytesIO(data), 'rb') as w:
        width, channels, rate = w.getsampwidth(), w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), 'u1' if width == 1 else '<i2')
        x = x.reshape(-1, channels).mean(axis=1)
    return ((x - 128) / 128 if width == 1 else x / 32768), rate


def cyclic_fit(x, y, hz, rate=RATE):
    """Linearized y = gain*x + delay*x' + sinusoidal AM and delay terms.

    The 100-us derivative scale keeps the normal matrix well conditioned.
    A fitted constant gain/delay removes static transfer differences only for
    this diagnostic; no fitted signal is used as the quality reference.
    """
    count = min(len(x), len(y))
    select = np.arange(round(.1 * rate), count - round(.1 * rate), 2)
    derivative = np.gradient(x[:count]) * rate * 1e-4
    t = select / rate
    x, d, y = x[:count][select], derivative[select], y[:count][select]
    c, s = np.cos(2*np.pi*hz*t), np.sin(2*np.pi*hz*t)
    matrix = np.array([x, d, x*c, x*s, d*c, d*s]).T
    gram, rhs = matrix.T @ matrix, matrix.T @ y
    coeff = np.linalg.solve(gram, rhs)
    error = y - matrix @ coeff
    base = y - matrix[:, :2] @ np.linalg.solve(gram[:2, :2], rhs[:2])
    return dict(hz=hz, fitted_constant_gain=float(coeff[0]),
        am_peak_percent=float(100 * np.hypot(*coeff[2:4]) / abs(coeff[0])),
        linearized_delay_peak_us=float(100 * np.hypot(*coeff[4:6]) / abs(coeff[0])),
        error_power_reduction_db=float(10*np.log10(np.dot(base, base) / max(np.dot(error, error), 1e-30))))


def self_check():
    """Recover known injected modulation; constant gain/delay must not mimic it."""
    t = np.arange(RATE * 2) / RATE
    x = .4*np.sin(2*np.pi*317*t) + .2*np.sin(2*np.pi*937*t)
    d = np.gradient(x)*RATE
    f = CPU/FIELD
    y = 1.2*(x + .02*x*np.cos(2*np.pi*f*t) + 20e-6*d*np.sin(2*np.pi*f*t))
    result = cyclic_fit(x, y, f)
    assert abs(result['am_peak_percent'] - 2) < 1e-8
    assert abs(result['linearized_delay_peak_us'] - 20) < 1e-8
    control = cyclic_fit(x, 1.2*x + 10e-6*d, f)
    assert control['am_peak_percent'] < 1e-8 and control['linearized_delay_peak_us'] < 1e-8
    return dict(known_am_percent=2, known_delay_us=20, recovered=result, constant_control=control)


def waveform_metrics(x, y):
    count = min(len(x), len(y))
    x, y = x[:count], y[:count]
    crop = slice(4410, -4410)
    error = (y - x)[crop]
    ref = x[crop]
    phase = ((np.arange(len(error)) + 4410) * CPU/RATE % FIELD / FIELD * 128).astype(int)
    def fold(e, phases):
        return np.bincount(phases, weights=e*e, minlength=128) / np.bincount(phases, minlength=128)
    power = fold(error, phase)
    reference_power = fold(ref, phase)
    split = len(error)//2
    early, late = fold(error[:split], phase[:split]), fold(error[split:], phase[split:])
    size = 32768
    window = np.hanning(size)
    spectrum = np.mean([abs(np.fft.rfft(error[i:i+size]*window))**2
        for i in range(0, len(error)-size, size//2)], axis=0) / (RATE*np.dot(window, window)/2)
    frequencies = np.fft.rfftfreq(size, 1/RATE)
    peaks = np.argsort(spectrum)[-12:][::-1]
    return dict(source_rms=float(np.sqrt(np.mean(ref*ref))), error_rms=float(np.sqrt(np.mean(error*error))),
        total_snr_db=float(10*np.log10(np.mean(ref*ref)/np.mean(error*error))),
        cyclic_error_power_max_min=float(power.max()/power.min()),
        cyclic_error_to_signal_max_min=float((power/reference_power).max()/(power/reference_power).min()),
        early_late_power_profile_correlation=float(np.corrcoef(early, late)[0, 1]),
        cyclic_error_power=power.tolist(), cyclic_source_power=reference_power.tolist(),
        strongest_error_bins=[dict(hz=float(frequencies[i]), power_density=float(spectrum[i])) for i in peaks],
        modulation=[cyclic_fit(x, y, f) for f in (5, 10, 25, 49, 50, CPU/FIELD, 51, 100, 2*CPU/FIELD)])


def resample(x, source_rate, target_rate, ffmpeg):
    result = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'f64le', '-ar', str(source_rate),
        '-ac', '1', '-i', '-', '-ar', str(target_rate), '-f', 'f64le', '-'],
        input=x.astype('<f8').tobytes(), capture_output=True, check=True)
    return np.frombuffer(result.stdout, '<f8')


def correlate(signal, reference):
    nfft = 1 << (len(signal)+len(reference)-2).bit_length()
    return np.fft.irfft(np.fft.rfft(signal, nfft)*np.fft.rfft(reference[::-1], nfft), nfft)[len(reference)-1:len(signal)]


def transport(reference, actual):
    """Measure 20-ms transport windows; exclude near-silent/ambiguous matches.

    Reference and output have different stationary colour. The integer-lag
    estimate includes that bias; changes are useful, absolute lag is not a
    sample-clock measurement. Searching +/-48 samples prevents jumping to a
    different voice period. Full capture alignment is established separately.
    """
    n = min(len(reference), len(actual))
    window, search = 960, 48
    rows = []
    for start in range(4800, n - window - search, window):
        ref = reference[start:start+window]
        if np.std(ref) < .001:
            continue
        part = actual[start-search:start+window+search]
        cross = correlate(part, ref)
        power = np.convolve(part*part, np.ones(window), 'valid')
        norm = cross / np.sqrt(np.maximum(power*np.dot(ref, ref), 1e-30))
        peak = int(np.argmax(norm))
        if norm[peak] < .8 or peak in (0, 2*search):
            continue
        gain = np.dot(part[peak:peak+window], ref) / np.dot(ref, ref)
        rows.append(dict(second=start/48000, delay_samples=peak-search,
            correlation=float(norm[peak]), gain=float(gain)))
    if not rows:
        raise ValueError('No reliable transport windows')
    lag = np.array([r['delay_samples'] for r in rows])
    return dict(window_ms=20, accepted_windows=len(rows), window_hop_ms=20,
        delay_range_samples=[int(lag.min()), int(lag.max())],
        delay_range_ms=float(np.ptp(lag)/48),
        delay_percentile_samples={str(p):float(np.percentile(lag, p)) for p in (1, 50, 99)},
        median_correlation=float(np.median([r['correlation'] for r in rows])),
        scope='Endpoint-vs-internal transport diagnostic with fitted alignment/gain; not codec SNR, and 20-ms windows cannot exclude faster artifacts.', windows=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent.parent/'ima4-full-disk'
    manifest = json.loads((root/'artifact-hashes.json').read_bytes())
    hashes = {}
    def read(name):
        data = (root/name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest[name]:
            raise ValueError(f'Historical input changed: {name}')
        hashes[name] = digest
        return data
    capture = json.loads((a.capture/'report.json').read_bytes())
    if not capture['capture_valid'] or capture['warnings'] or capture['timing'] != 'B':
        raise ValueError('Incomplete/discontinuous/wrong-machine capture')
    words = [int(s, 0) for s in re.findall(r'(?m)^(0x[\da-fA-F]+|\d+)\s*$', (a.capture/'stdout.txt').read_text())]
    events = np.array(words).reshape(-1, 4)
    if list(events[:, 0]) != [100, 200]*5 + [300] or list(events[:, 1]) != [0,0,1,1,2,2,3,3,4,4,5]:
        raise ValueError('Did not record exactly five complete parts and END OF AUDIO')
    if (a.capture/'internal.wav').exists():
        internal, rate = wav((a.capture/'internal.wav').read_bytes())
    else:
        pcm, _, _ = read_fmf(gzip.decompress((a.capture/'capture.fmf.gz').read_bytes()))
        internal, rate = pcm.astype(float)/32768, 44100
    endpoint_file = a.capture/'loopback.wav'
    endpoint_data = (endpoint_file.read_bytes() if endpoint_file.exists() else
                     gzip.decompress((a.capture/'loopback.wav.gz').read_bytes()))
    speaker, speaker_rate = wav(endpoint_data)
    assert rate == 44100 and speaker_rate == 48000
    chunks = {frame:(offset, count) for frame, offset, count in capture['chunks']}
    def position(event):
        _, _, frame, tick = event
        offset, count = chunks[int(frame)]
        return offset + round(count*int(tick)/FIELD)
    rows, transport_rows, extracted = [], [], []
    for number in range(1, 6):
        source, source_rate = wav(read(f'selected/part-{number:05d}/source-preview.wav'))
        assert source_rate == 8000
        source = np.rint(source*128+128).astype('u1')
        timeline = np.frombuffer(gzip.decompress(read(f'release/verification/cold-0001/part-{number:02d}-times.u32.gz')), '<u4').astype(np.int64)
        actual, _ = wav(read(f'release/verification/cold-0001/part-{number:02d}-output.wav'))
        fixed = fixed_reference(source, timeline[-1]-timeline[0], 8000, a.ffmpeg)
        metrics = waveform_metrics(fixed, actual)
        rows.append(dict(part=number, **metrics))
        start, end = map(position, events[(number-1)*2:number*2])
        normal = internal[start:end]
        # Align each part globally inside its expected region. This preserves
        # actual capture bytes and detects gross host clock drift separately.
        ref = resample(normal, 44100, 48000, a.ffmpeg)
        offset = 48000
        fragment = ref[offset:offset+96000]
        expected = round(start/44100*48000)
        left, right = max(0, expected-48000*3), min(len(speaker), expected+len(ref)+48000*3)
        cross = correlate(speaker[left:right], fragment)
        aligned = left + int(np.argmax(cross)) - offset
        endpoint = speaker[aligned:aligned+len(ref)]
        transport_rows.append(dict(part=number, alignment_sample=aligned,
            expected_movie_start_sample=expected, **transport(ref, endpoint)))
        write_wav(out/f'part-{number:02d}-internal.wav', normal)
        write_wav(out/f'part-{number:02d}-speaker.wav', endpoint, 48000)
        extracted.append(dict(part=number, start_frame=int(events[(number-1)*2, 2]),
            ready_tstate=int(events[(number-1)*2, 3]), playback_seconds=len(normal)/44100))
        print(json.dumps(dict(part=number, snr=metrics['total_snr_db'],
            cyclic_power_ratio=metrics['cyclic_error_power_max_min'],
            half_profile_correlation=metrics['early_late_power_profile_correlation'],
            field_modulation=metrics['modulation'][5],
            transport_range_ms=transport_rows[-1]['delay_range_ms'])), flush=True)
    result = dict(date='2026-10-05', complete_five_part_capture=True,
        self_check=self_check(), field_frequency_hz=CPU/FIELD,
        source_hashes=hashes, disk_sha256=capture['disk_sha256'],
        normal_playback_parts=extracted, waveform_diagnostics=rows, transport=transport_rows,
        limitations='Cyclic power is not a pitch excursion. AM/delay fits are small-signal indicators. Transport fits are not source SNR. No claim that the listening symptom is eliminated.',
        analyzer_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    (out/'report.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
