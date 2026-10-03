"""LPS1: LPC2 analysis, fixed-point lattice synthesis, then greedy IMA.

LPS1 is a Spectrum-specific LPC storage format, not a renamed LPC2 file.
Each 20-ms record holds ten Q15 reflection coefficients, a Q8 pitch period,
two chirp amplitudes and a noise amplitude: 28 bytes. LSF conversion runs on
the PC; excitation, synthesis and IMA encoding run on the Z80 before playback.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import wave

import numpy as np
from ima_codec import STEPS, INDEX, decode, require_unclipped
from convert_audio import pcm_wav
from verify_pcm import save

CHIRP = (1, 1, 1, 1, -1, -1, -1, 1, -1, -1, 1, 1, -1, 1, -1)
HEADER = struct.Struct('<4sHHIIHH12x')
RECORD = struct.Struct('<10hHhhh')
HOP = 160
GUARD = 128


def reflection(coefficients):
    a = np.asarray(coefficients, dtype=float).copy()
    k = np.zeros(10)
    for m in range(10, 0, -1):
        k[m - 1] = np.clip(a[m], -.995, .995)
        a = np.r_[1., (a[1:m] - k[m - 1] * a[m-1:0:-1]) / (1-k[m - 1]**2)]
    return np.rint(k * 32768).astype(int)


def table(k):
    x = np.arange(256, dtype=np.int64)
    x[x >= 128] -= 256
    return (k * x // 128).astype(np.int16)


def multiply(t, x):
    """Two table reads approximate (k*x)>>15 with <2 units of error.

    Signed high byte contributes directly. The even part of the unsigned
    low byte uses the same table, divided by128. No overflow/clamping occurs
    in this primitive; every lattice state is separately saturated.
    """
    return int(t[(x >> 8) & 255]) + (int(t[(x & 255) >> 1]) >> 7)


def clip(x):
    return max(-16384, min(16383, x))


def synthesize(records, audible_samples):
    history = [0] * 11
    seed = 0xACE1
    phase = 0
    chirp = 15
    de = dc = previous = 0
    deemphasis = table(27853)  # round(0.85 * 32768)
    output = []
    clips = 0
    for row in records:
        ks, period, positive, negative, noise = row[:10], *row[10:]
        tabs = [table(k) for k in ks]
        for _ in range(min(HOP, audible_samples - len(output))):
            seed = (seed >> 1) ^ (0xB400 if seed & 1 else 0)
            signed_noise = (seed >> 8) - 128
            excitation = noise * signed_noise // 128
            if phase < 256:
                phase = (phase + period - 256) & 65535
                chirp = 0
            else:
                phase -= 256
            if chirp < 15:
                excitation += positive if CHIRP[chirp] > 0 else negative
                chirp += 1
            f = clip(excitation)
            for m in range(9, -1, -1):
                raw = f - multiply(tabs[m], history[m])
                clips += raw != clip(raw)
                f = clip(raw)
                history[m + 1] = clip(history[m] + multiply(tabs[m], f))
            history[0] = f
            de = clip(f + multiply(deemphasis, de))
            dc = clip(clip(clip(de - previous) + dc) - (dc >> 8))
            previous = de
            output.append(max(1, min(255, 128 + (dc >> 5))))
    assert len(output) == audible_samples
    return np.r_[np.asarray(output, dtype='u1'), np.full(GUARD, 128, dtype='u1')], clips


def encode_ima(pcm):
    """Standard threshold IMA encoder, exactly matched by preload assembly."""
    predictor = index = 0
    codes = []
    for value in pcm:
        error = (int(value) - 128) * 256 - predictor
        code = 8 if error < 0 else 0
        error = abs(error)
        step = STEPS[index]
        delta = step >> 3
        for bit, threshold in ((4, step), (2, step >> 1), (1, step >> 2)):
            if error >= threshold:
                code |= bit
                error -= threshold
                delta += threshold
        predictor += -delta if code & 8 else delta
        if not -32768 <= predictor <= 32767:
            raise ValueError('IMA encoder would require player saturation')
        index = max(0, min(88, index + INDEX[code & 7]))
        codes.append(code)
    assert (predictor, index) == (0, 0), (predictor, index)
    return bytes(codes[i] | (codes[i+1] << 4) for i in range(0, len(codes), 2))


def pack(records, samples):
    data = HEADER.pack(b'LPS1', 8000, HOP, samples, len(records), GUARD, 28)
    return data + b''.join(RECORD.pack(*row) for row in records)


def unpack(blob):
    magic, rate, hop, samples, count, guard, size = HEADER.unpack_from(blob)
    if (magic, rate, hop, guard, size) != (b'LPS1', 8000, 160, 128, 28):
        raise ValueError('unsupported LPS1 header')
    if count != (samples - guard + hop - 1) // hop or len(blob) != 32 + count*28:
        raise ValueError('invalid LPS1 length')
    return [RECORD.unpack_from(blob, 32+i*28) for i in range(count)], samples


def prepare(source, out, node, lpc_source):
    with wave.open(str(source), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        pcm = np.frombuffer(w.readframes(w.getnframes()), 'u1')
    assert len(pcm) <= 186880 and len(pcm) % 512 == 0 and np.all(pcm[-128:] == 128)
    out.mkdir(parents=True, exist_ok=True)
    core = out / 'lpc2'; core.mkdir()
    (core / 'input.f32').write_bytes(((pcm[:-128].astype(float)-128)/128).astype('<f4').tobytes())
    bridge = Path(__file__).resolve().parents[1] / 'audiobook-ay/lpc2_bridge.js'
    subprocess.run([node, str(bridge), str(lpc_source / 'index.html'), str(core/'input.f32'), str(core), 'detail50'], check=True)
    analysis = json.loads((core/'lpc2-analysis.json').read_bytes())
    records = []
    # A conservative excitation scale keeps lattice state below its Q11 guard.
    for f in analysis['frames']:
        k = reflection(f['coefficients']) if f['energy'] else np.zeros(10, dtype=int)
        period = 8000/f['pitch_hz'] if f['pitch_hz'] else 8000/120
        pulse_weight, noise_weight = {0:(0,1), 1:(.58,.62), 2:(.94,.12), 3:(0,1.2)}[f['mode']]
        gain = f['gain'] * .35
        pulse = gain*np.sqrt(period)*2048*pulse_weight
        records.append([*map(int,k), round(period*256), round(pulse*.2415), round(pulse*-.276), round(gain*np.sqrt(3)*2048*noise_weight)])
    decoded, clips = synthesize(records, len(pcm)-128)
    peak = max(abs(decoded.astype(int)-128))
    gain = min(109/max(peak, 1), 32700/max(1, max(abs(x) for r in records for x in r[11:])))
    normalized = [r[:11] + [round(x*gain) for x in r[11:]] for r in records]
    decoded, clips = synthesize(normalized, len(pcm)-128)
    if clips:
        raise ValueError('normalized excitation saturates the lattice; reduce the fixed gain')
    records = normalized
    packed = encode_ima(decoded)
    data = pack(records, len(pcm))
    recovered, size = unpack(data)
    assert recovered == [tuple(r) for r in records] and size == len(pcm)
    assert len(data) <= 32768
    (out/'soundtrack.lps').write_bytes(data)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    pcm_wav(out/'source-preview.wav', decoded)
    pcm_wav(out/'original-source-preview.wav', pcm)
    save(out/'lpc.json', dict(format='LPS1', sample_rate=8000, samples=len(pcm), frames=len(records),
         lpc_bytes=len(data), ima_bytes=len(packed), saving_percent=100*(1-len(data)/len(packed)),
         source_sha256=hashlib.sha256(pcm.tobytes()).hexdigest(), pcm_sha256=hashlib.sha256(decoded.tobytes()).hexdigest(),
         ima_sha256=hashlib.sha256(packed).hexdigest(), lattice_clips=clips, pcm_min=int(decoded.min()), pcm_max=int(decoded.max()),
         reference='Fixed-point LPS1 synthesis; original PCM retained separately',
         fixed_excitation_normalization=gain, ima_saturation_guard=require_unclipped(packed),
         lpc2_source_sha256=analysis['source_sha256']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--node', required=True); p.add_argument('--lpc-source', type=Path, default=Path('C:/Work/LPC-sound-codec'))
    a = p.parse_args()
    if a.output.exists() and any(a.output.iterdir()): p.error('output must be empty')
    prepare(a.source, a.output, a.node, a.lpc_source)
