"""Nine-channel YM3812 spectral reconstruction through actual OPL2 registers.

The source supplies fitting targets only. All preview samples come from the
pinned ymfm YM3812 core replaying a standard VGM register/wait stream.
"""
import argparse
from functools import lru_cache
import gzip
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path
import struct
import sys
import time

import numpy as np
import ymfm
import psychoacoustic
import quality
from simulation_refine import Objective, spectra, tick_rms
from support import save

CLOCK = 3579545
NATIVE_RATE = CLOCK / 72
RATE, OUT_RATE, HZ = 22050, 44100, 50
CORE = Path(__file__).resolve().parent
MOD_OFFSETS = np.array([0, 1, 2, 8, 9, 10, 16, 17, 18])
LEVELS = np.r_[10 ** (-.75 * np.arange(64) / 20), 0.]
PATCHES = [dict(name=name, wave=wave, mod_mul=1, mod_tl=63) for wave, name in
           enumerate(('carrier-sine', 'half-sine', 'absolute-sine', 'quarter-sine'))]
PATCHES += [dict(name=f'fm-{ratio}:1-tl{tl}', wave=0, mod_mul=ratio, mod_tl=tl)
            for ratio, levels in ((1, (16, 24, 32, 40)), (2, (16, 24, 32, 40)), (3, (24, 32))) for tl in levels]
for p in PATCHES: p['car_mul'] = 1
PATCHES += [dict(p, name=p['name'] + '-x2', car_mul=2, mod_mul=p['mod_mul'] * 2) for p in PATCHES.copy()]
MAX_BASE = 1023 * NATIVE_RATE / 8192


def sha(data):
    return hashlib.sha256(data).hexdigest()


def register(chip, address, value):
    chip.write_address(int(address)); chip.write_data(int(value))


def initial_registers():
    # Real OPL2 registers only: waveform select on, rhythm/CSM/AM/vibrato off.
    # Both operators sustain indefinitely (EGT=1), AR15/DR0/SL0/RR15.
    result = [(1, 0x20), (8, 0), (0xbd, 0)]
    for ch, mod in enumerate(MOD_OFFSETS):
        for offset in (int(mod), int(mod + 3)):
            result += [(0x20 + offset, 0x21), (0x40 + offset, 63),
                       (0x60 + offset, 0xf0), (0x80 + offset, 0x0f), (0xe0 + offset, 0)]
        result += [(0xc0 + ch, 0), (0xb0 + ch, 0)]
    return result


def frequency_code(frequency):
    frequency = np.asarray(frequency, float)
    if np.any(frequency <= 0) or np.any(frequency > MAX_BASE): raise ValueError('base frequency outside OPL2 range; use operator multiplier for higher tones')
    block = np.zeros(frequency.shape, dtype=np.uint8)
    fnum = np.rint(frequency * 2 ** 20 / NATIVE_RATE)
    for b in range(1, 8):
        selected = fnum > 1023
        block[selected] = b
        fnum[selected] = np.rint(frequency[selected] * 2 ** (20 - b) / NATIVE_RATE)
    return np.clip(fnum, 1, 1023).astype(np.uint16), block


def tone_patch(chip, patch, fnum=512, block=1, tl=0):
    p = PATCHES[patch]
    for address, value in initial_registers():
        register(chip, address, value)
    for address, value in ((0x20, 0x20 | p['mod_mul']), (0x23, 0x20 | p['car_mul']), (0x40, p['mod_tl']),
                           (0xe3, p['wave']), (0x43, tl), (0xa0, fnum & 255),
                           (0xb0, 0x20 | block << 2 | fnum >> 8)):
        register(chip, address, value)


def chip_audio(chip, count):
    return np.asarray(chip.generate(int(count)), dtype=np.int32)[:, 0].astype(float) / 32768


@lru_cache(maxsize=1)
def dictionary():
    """Measure real chip harmonic magnitudes, then form 512-Hann templates.

    FNUM512/BLOCK1 advances exactly1/1024 cycle per native sample. Integer
    cycles after EG settling isolate the harmonics without FFT leakage.
    Templates approximate magnitude addition; selection is judged on full
    continuous emulator audio, where phases and register changes are real.
    """
    coefficients = []
    variance = []
    for index in range(len(PATCHES)):
        chip = ymfm.YM3812(clock=CLOCK); chip.reset(); tone_patch(chip, index)
        chip_audio(chip, 4096)
        audio = chip_audio(chip, 16384)
        harmonic = abs(np.fft.rfft(audio)) / (len(audio) / 2)
        coefficients.append(harmonic[np.arange(1, 180) * 16])
        variance.append(float(np.var(audio)))
    fnum, block = frequency_code(np.geomspace(45, MAX_BASE, 2000))
    codes = np.unique(fnum | block.astype(np.uint16) << 10)
    fnum, block = codes & 1023, (codes >> 10).astype(np.uint8)
    frequency = fnum * 2. ** block * NATIVE_RATE / 2 ** 20
    order = np.argsort(frequency); frequency, fnum, block = frequency[order], fnum[order], block[order]
    hz = np.fft.rfftfreq(1024, 1 / RATE)
    useful = (hz >= 50) & (hz <= 8000); bins = np.flatnonzero(useful)
    basis = np.zeros((len(PATCHES), len(frequency), len(bins)), np.float32)
    coefficients = np.array(coefficients)
    for harmonic in range(1, 180):
        selected = np.flatnonzero(frequency * harmonic < 8050)
        if not len(selected): break
        indices = np.rint(frequency[selected, None] * harmonic / hz[1]).astype(int) + np.arange(-8, 9)
        x = (indices * hz[1] - frequency[selected, None] * harmonic) * 512 / RATE
        kernel = abs(np.sinc(x) + .5 * np.sinc(x - 1) + .5 * np.sinc(x + 1))
        valid = (indices >= bins[0]) & (indices <= bins[-1])
        rows = np.broadcast_to(selected[:, None], indices.shape)[valid]
        columns = (indices - bins[0])[valid]
        for patch in range(len(PATCHES)):
            if coefficients[patch, harmonic - 1] < 1e-6: continue
            np.add.at(basis[patch], (rows, columns), kernel[valid] * coefficients[patch, harmonic - 1])
    return frequency, fnum, block, basis, np.array(variance), hz, useful, coefficients


def assignment(cost):
    """Exact9x9 assignment with512 subset states, avoiding9! permutations."""
    best = np.full(512, np.inf); best[0] = 0
    previous = np.zeros(512, np.uint16); picked = np.zeros(512, np.uint8)
    for mask in range(1, 512):
        row = mask.bit_count() - 1
        available = [col for col in range(9) if mask & 1 << col]
        parents = [mask ^ 1 << col for col in available]
        values = best[parents] + cost[row, available]
        chosen = int(np.argmin(values))
        best[mask] = values[chosen]; previous[mask] = parents[chosen]; picked[mask] = available[chosen]
    order = np.zeros(9, np.uint8); mask = 511
    for row in range(8, -1, -1):
        order[row] = picked[mask]; mask = int(previous[mask])
    return order


def fit(source, mode):
    frequency, fnum, block, basis, variance, hz, useful, _ = dictionary()
    allowed = np.array([0, 14]) if mode == 'sine' else np.r_[np.arange(4), np.arange(14, 18)] if mode == 'waveforms' else np.arange(len(PATCHES))
    multiples = np.array([p['car_mul'] for p in PATCHES])
    count = len(source) // 441
    magnitude = spectra(source, np.arange(count), 512)[:, useful].astype(np.float32)
    masking = psychoacoustic.thresholds(magnitude, hz[useful])
    weights = psychoacoustic.error_weights(magnitude, magnitude, masking)
    peak = np.maximum(magnitude.max(axis=1), 1e-12)
    weights *= (np.maximum(magnitude, peak[:, None] * .025) / peak[:, None]) ** -1
    rms = tick_rms(source)
    index = np.full((count, 9), int(np.argmin(abs(frequency - 440))), np.uint16)
    patches = np.zeros((count, 9), np.uint8); amplitudes = np.zeros((count, 9))
    before = index[0].copy(); before_patch = patches[0].copy()
    for tick, target in enumerate(magnitude):
        if tick % 250 == 0: print(json.dumps(dict(stage='opl_fit', mode=mode, tick=tick, total=count)), flush=True)
        if rms[tick] < 1e-8: index[tick] = before; continue
        peaks = np.flatnonzero((target[1:-1] > target[:-2]) & (target[1:-1] >= target[2:])) + 1
        keep = list(peaks[np.argsort(target[peaks])[-24:]])
        for low, high in ((50, 800), (800, 1800), (1800, 3500), (3500, 8001)):
            selected = peaks[(hz[useful][peaks] >= low) & (hz[useful][peaks] < high) & (target[peaks] > target.max() * .025)]
            keep.extend(selected[np.argsort(target[selected])[-4:]])
        peaks = np.unique(keep).astype(int)
        if not len(peaks): peaks = np.array([target.argmax()])
        log = np.log(np.maximum(target, 1e-15))
        left, right = log[np.maximum(peaks - 1, 0)], log[np.minimum(peaks + 1, len(log) - 1)]
        curvature = left - 2 * log[peaks] + right
        shift = np.divide(.5 * (left - right), curvature, out=np.zeros(len(peaks)), where=abs(curvature) > 1e-12)
        observed = hz[useful][peaks] + np.clip(shift, -.5, .5) * hz[1]
        proposed = np.searchsorted(frequency, np.r_[observed, observed / 2, observed / 3, observed / 4, observed / 5, observed / 8])
        proposed = np.unique(np.clip(np.r_[proposed - 1, proposed, proposed + 1, before], 0, len(frequency) - 1))
        rows = basis[allowed[:, None], proposed[None, :]].reshape(-1, basis.shape[-1]).astype(float)
        candidates = np.column_stack((np.tile(proposed, len(allowed)), np.repeat(allowed, len(proposed))))
        weighted = rows * weights[tick]; power = np.sum(weighted * rows, axis=1)
        remaining = target.astype(float).copy(); chosen = []; coefficients = []
        excluded = np.zeros(len(rows), bool)
        for _ in range(9):
            correlation = weighted @ remaining
            score = np.maximum(correlation, 0) ** 2 / np.maximum(power, 1e-20)
            actual_frequency = frequency[candidates[:, 0]] * multiples[candidates[:, 1]]
            previous_frequency = frequency[before] * multiples[before_patch]
            held = np.any((abs(np.log2(actual_frequency[:, None] / previous_frequency)) < .015) &
                          (candidates[:, 1, None] == before_patch), axis=1)
            score *= 1 + .012 * held; score[excluded] = -1
            selected = int(score.argmax())
            if score[selected] <= max(float(np.sum(weights[tick] * target ** 2)) * .001, 1e-16): break
            coefficient = max(0., float(correlation[selected] / max(power[selected], 1e-20)))
            chosen.append(selected); coefficients.append(coefficient)
            remaining = np.maximum(remaining - coefficient * rows[selected], 0)
            excluded |= abs(np.log2(actual_frequency / actual_frequency[selected])) < .018
        padded_index = before.copy(); padded_patch = before_patch.copy(); level = np.zeros(9)
        if chosen:
            selected_rows = rows[chosen]; gram = (selected_rows * weights[tick]) @ selected_rows.T
            correlation = (selected_rows * weights[tick]) @ target; coefficients = np.array(coefficients)
            for _ in range(12):
                for j in range(len(chosen)):
                    coefficients[j] = max(0, (correlation[j] - gram[j] @ coefficients + gram[j, j] * coefficients[j]) / max(gram[j, j], 1e-20))
            selected = candidates[chosen]
            prediction = np.sqrt(np.sum(coefficients ** 2 * variance[selected[:, 1]]))
            coefficients *= np.clip(rms[tick] / max(prediction, 1e-12), .1, 10)
            padded_index[:len(selected)], padded_patch[:len(selected)] = selected.T
            level[:len(selected)] = coefficients
            previous_frequency = frequency[before] * multiples[before_patch]
            actual_frequency = frequency[padded_index] * multiples[padded_patch]
            cost = abs(np.log2(previous_frequency[:, None] / actual_frequency[None, :])) + .1 * (before_patch[:, None] != padded_patch[None, :])
            cost[:, level == 0] = 0
            order = assignment(cost)
            index[tick], patches[tick], amplitudes[tick] = padded_index[order], padded_patch[order], level[order]
        else: index[tick], patches[tick] = before, before_patch
        before, before_patch = index[tick].copy(), patches[tick].copy()
    positive = amplitudes[amplitudes > 0]
    gain = float(np.percentile(positive, 99.5) * 1.1) if len(positive) else 1.
    levels = abs(amplitudes[:, :, None] / gain - LEVELS).argmin(axis=2).astype(np.uint8)
    levels[amplitudes == 0] = 64
    return dict(fnum=fnum[index], block=block[index], patch=patches, level=levels), gain


def validate(c):
    count = len(c['fnum'])
    if not count: raise ValueError('empty controls')
    for name, lo, hi in (('fnum', 1, 1023), ('block', 0, 7), ('patch', 0, len(PATCHES) - 1), ('level', 0, 64)):
        if c[name].dtype.kind not in 'ui' or c[name].shape != (count, 9) or np.any(c[name] < lo) or np.any(c[name] > hi): raise ValueError('invalid ' + name)
    return count


def vgm(c, ramp_steps=0):
    """Export only YM3812 writes and waits: no PCM blocks or DAC commands.

    Initial silent setup is outside timed playback. Timed writes are spaced
    two44.1-kHz samples apart (45.35us), longer than OPL2 bus settling/busy
    requirements. Optional4-step/4-ms ramps are real TL-register writes, not
    an interpolation added to the emulator output.
    """
    if ramp_steps not in (0, 4): raise ValueError('supported TL ramps are0 or4 steps')
    count = validate(c); body = bytearray(); state = {}; write_count = 0
    def write(address, value, timed=True):
        nonlocal write_count
        address, value = int(address), int(value)
        if state.get(address) == value: return 0
        body.extend((0x5a, address, value)); state[address] = value; write_count += 1
        if timed: body.append(0x71)
        return 2 if timed else 0
    def wait(samples):
        if samples > 0: body.extend(struct.pack('<BH', 0x61, samples))
    for address, value in initial_registers(): write(address, value, False)
    old_level = np.full(9, 64)
    for tick in range(count):
        elapsed = 0; target = c['level'][tick]
        for ch, mod in enumerate(MOD_OFFSETS):
            p = PATCHES[int(c['patch'][tick, ch])]
            start_level = old_level[ch] if ramp_steps else target[ch]
            if start_level == 64 and target[ch] < 64: start_level = 63
            elapsed += write(0x43 + mod, min(int(start_level), 63))
            elapsed += write(0x20 + mod, 0x20 | p['mod_mul'])
            elapsed += write(0x23 + mod, 0x20 | p['car_mul'])
            elapsed += write(0x40 + mod, p['mod_tl'])
            elapsed += write(0xe3 + mod, p['wave'])
            elapsed += write(0xa0 + ch, c['fnum'][tick, ch] & 255)
            key = (target[ch] < 64) if not ramp_steps else ((old_level[ch] < 64) or (target[ch] < 64))
            elapsed += write(0xb0 + ch, (0x20 if key else 0) | int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)
        if ramp_steps:
            for step in range(1, ramp_steps + 1):
                deadline = round(OUT_RATE * .004 * step / ramp_steps)
                wait(max(deadline - elapsed, 0)); elapsed = max(deadline, elapsed)
                level = (1 - step / ramp_steps) * LEVELS[old_level] + step / ramp_steps * LEVELS[target]
                code = abs(level[:, None] - LEVELS).argmin(axis=1)
                for ch, mod in enumerate(MOD_OFFSETS):
                    elapsed += write(0x43 + mod, min(int(code[ch]), 63))
                    if step == ramp_steps and target[ch] == 64:
                        elapsed += write(0xb0 + ch, int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)
        if elapsed > 882: raise ValueError('write burst exceeds20 ms')
        wait(882 - elapsed); old_level = target.copy()
    body.append(0x66)
    header = bytearray(0x100); header[:4] = b'Vgm '
    struct.pack_into('<I', header, 4, len(header) + len(body) - 4)
    struct.pack_into('<I', header, 8, 0x171)
    struct.pack_into('<I', header, 0x18, count * 882)
    struct.pack_into('<I', header, 0x34, 0x100 - 0x34)
    struct.pack_into('<I', header, 0x50, CLOCK)
    return bytes(header + body), write_count


def smooth_vgm(c, transition_ms=2., steps=8, ordered_pitch=True):
    """Ramp sine-carrier TL with real writes, retaining the exact frame targets.

    Key-on starts at TL63 after tuning; key-off follows the quiet end of its
    ramp. Raised-cosine amplitude targets soften both ends of a transition.
    The finite 0.75-dB TL steps and 45.35-us bus slots remain observable.
    Deadlines are relative to each frame; bus writes can overrun a substep
    deadline, so transition_ms is nominal, not an atomic all-channel duration.
    Every target is attained before the next exact20-ms frame boundary.
    Frequency is phase-continuous in the chip but its split registers are
    not atomic. Choose the order with the smallest intermediate excursion
    outside the old/new frequency interval, including carrier MULT changes.
    Only the measured sine patches are supported; waveform/FM changes need
    separate transition tests. Historical vgm() stays byte-compatible.
    """
    count = validate(c)
    if not np.isin(c['patch'], [0, 14]).all(): raise ValueError('smooth export requires sine patches')
    if not np.isfinite(transition_ms) or not 1 <= transition_ms <= 8 or steps not in (4, 8, 16):
        raise ValueError('transition must be1..8 ms with4/8/16 steps')
    body = bytearray(); state = {}; writes = 0; elapsed = 0
    def write(address, value, timed=True):
        nonlocal writes, elapsed
        address, value = int(address), int(value)
        if state.get(address) == value: return
        body.extend((0x5a, address, value)); state[address] = value; writes += 1
        if timed: body.append(0x71); elapsed += 2
    def until(deadline):
        nonlocal elapsed
        if elapsed < deadline:
            body.extend(struct.pack('<BH', 0x61, deadline - elapsed)); elapsed = deadline
    for address, value in initial_registers(): write(address, value, False)
    old_level = np.full(9, 64)
    for tick in range(count):
        elapsed = 0; target = c['level'][tick]
        for ch, mod in enumerate(MOD_OFFSETS):
            p = PATCHES[int(c['patch'][tick, ch])]
            if old_level[ch] == 64: write(0x43 + mod, 63)
            write(0x20 + mod, 0x20 | p['mod_mul'])
            write(0x40 + mod, p['mod_tl']); write(0xe3 + mod, p['wave'])
            key = old_level[ch] < 64 or target[ch] < 64
            changes = [(0x23 + mod, 0x20 | p['car_mul']), (0xa0 + ch, int(c['fnum'][tick, ch]) & 255),
                       (0xb0 + ch, (0x20 if key else 0) | int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)]
            if ordered_pitch and old_level[ch] < 64:
                def frequency(s):
                    high = s.get(0xb0 + ch, 0)
                    return (s.get(0xa0 + ch, 0) | (high & 3) << 8) * 2 ** ((high >> 2) & 7) * (s[0x23 + mod] & 15)
                old = frequency(state); destination = dict(state); destination.update(changes)
                new = frequency(destination); low, high = sorted((old, new))
                def cost(order):
                    intermediate = dict(state); excursion = []; travel = []; previous = old
                    for address, value in order:
                        intermediate[address] = value; current = frequency(intermediate)
                        excursion.append(max(low - current, current - high, 0)); travel.append(abs(current - previous)); previous = current
                    return max(excursion), sum(travel)
                changes = min(itertools.permutations(changes), key=cost)
            for address, value in changes: write(address, value)
        for step in range(1, steps + 1):
            until(round(OUT_RATE * transition_ms / 1000 * step / steps))
            blend = .5 - .5 * np.cos(np.pi * step / steps)
            amplitude = (1 - blend) * LEVELS[old_level] + blend * LEVELS[target]
            code = abs(amplitude[:, None] - LEVELS).argmin(axis=1)
            for ch, mod in enumerate(MOD_OFFSETS):
                write(0x43 + mod, min(int(code[ch]), 63))
                if step == steps and target[ch] == 64:
                    write(0xb0 + ch, int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)
        if elapsed > 882: raise ValueError('write burst exceeds20 ms')
        until(882); old_level = target.copy()
    body.append(0x66)
    header = bytearray(0x100); header[:4] = b'Vgm '
    for offset, value in ((4, len(header) + len(body) - 4), (8, 0x171), (0x18, count * 882), (0x34, 0xcc), (0x50, CLOCK)):
        struct.pack_into('<I', header, offset, value)
    return bytes(header + body), writes


def replay(data):
    if len(data) < 0x100 or data[:4] != b'Vgm ' or struct.unpack_from('<I', data, 0x50)[0] != CLOCK: raise ValueError('wrong VGM chip/header')
    if struct.unpack_from('<I', data, 4)[0] != len(data) - 4: raise ValueError('wrong VGM length')
    chip = ymfm.YM3812(clock=CLOCK); chip.reset()
    pos = 0x34 + struct.unpack_from('<I', data, 0x34)[0]
    time_samples = native_samples = 0; chunks = []; writes = 0
    while pos < len(data):
        op = data[pos]; pos += 1
        if op == 0x66: break
        if op == 0x5a:
            if pos + 2 > len(data): raise ValueError('truncated register write')
            register(chip, data[pos], data[pos + 1]); pos += 2; writes += 1; continue
        if op == 0x61:
            if pos + 2 > len(data): raise ValueError('truncated wait')
            duration = struct.unpack_from('<H', data, pos)[0]; pos += 2
        elif 0x70 <= op <= 0x7f: duration = (op & 15) + 1
        else: raise ValueError('unexpected/non-OPL command')
        time_samples += duration
        target = (time_samples * CLOCK) // (72 * OUT_RATE)
        if target > native_samples:
            chunks.append(chip_audio(chip, target - native_samples)); native_samples = target
    if op != 0x66 or pos != len(data) or time_samples != struct.unpack_from('<I', data, 0x18)[0]: raise ValueError('wrong VGM end/duration')
    return np.concatenate(chunks), time_samples, writes


def playback(raw, samples):
    """Explicit fixed20-Hz AC coupling and8-kHz windowed-sinc playback filter.

    Fractional resampling follows clock/72, not the binding's truncated rate.
    The source/controls never participate in the audio filter.
    """
    pole = np.exp(-2 * np.pi * 20 / NATIVE_RATE)
    # First-order high-pass via frequency-domain zero-padded linear convolution.
    # A4096-sample impulse tail leaves <4e-5 of its initial pole response.
    impulse = np.r_[1., (pole - 1) * pole ** np.arange(4095)]
    length = 1 << (len(raw) + len(impulse) - 2).bit_length()
    filtered = np.fft.irfft(np.fft.rfft(raw, length) * np.fft.rfft(impulse, length), length)[:len(raw)]
    result = np.empty(samples); offsets = np.arange(-64, 65)
    cutoff = 8000 / NATIVE_RATE
    for start in range(0, samples, 4096):
        end = min(start + 4096, samples)
        position = np.arange(start, end) * NATIVE_RATE / OUT_RATE
        base = np.floor(position).astype(int); distance = offsets[None, :] - (position - base)[:, None]
        kernel = 2 * cutoff * np.sinc(2 * cutoff * distance) * (.5 + .5 * np.cos(np.pi * distance / 65))
        kernel /= kernel.sum(axis=1)[:, None]
        indices = base[:, None] + offsets
        values = filtered[np.clip(indices, 0, len(filtered) - 1)]
        values[(indices < 0) | (indices >= len(filtered))] = 0
        result[start:end] = np.sum(values * kernel, axis=1)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controls', type=Path, help='re-export saved sine targets with smooth register transitions')
    parser.add_argument('--gain', type=float, help='constant audition gain for saved controls')
    parser.add_argument('--transition-ms', type=float, default=2.)
    parser.add_argument('--transition-steps', type=int, default=8)
    parser.add_argument('--legacy-sine-transitions', action='store_true', help='reproduce historical abrupt sine export')
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    import experimental_six_voice as six
    import noise_colour
    source = six.read_reference(args.reference)
    if len(source) != 30 * RATE: raise ValueError('bounded experiment requires30 seconds')
    args.output.mkdir(parents=True)
    objective = Objective(source); start = time.perf_counter(); trials = []
    if args.controls:
        with np.load(args.controls) as stored: controls = {k: stored[k] for k in stored.files}
        if validate(controls) != len(source) // 441: raise ValueError('source/control duration mismatch')
        data, writes = smooth_vgm(controls, args.transition_ms, args.transition_steps)
        raw, samples, parsed_writes = replay(data); assert writes == parsed_writes
        audio = playback(raw, samples)
        gain = args.gain if args.gain is not None else min(float(np.sqrt(np.mean(source ** 2) / max(np.mean(noise_colour.downsample(audio) ** 2), 1e-20))), .95 / max(float(abs(audio).max()), 1e-12))
        if not np.isfinite(gain) or gain <= 0 or abs(audio * gain).max() >= 1: raise ValueError('invalid/clipping audition gain')
        quality.write_wav(args.output / 'ym3812-preview.wav', audio * gain, OUT_RATE)
        (args.output / 'ym3812.vgm').write_bytes(data)
        (args.output / 'ym3812.vgz').write_bytes(gzip.compress(data, mtime=0))
        np.savez_compressed(args.output / 'controls.npz', **controls)
        save(args.output / 'report.json', dict(complete=True, fields=len(controls['fnum']), output_samples=samples,
             native_samples=len(raw), writes=writes, global_playback_gain=gain, nominal_transition_ms=args.transition_ms,
             transition_steps=args.transition_steps, controls_sha256=sha(args.controls.read_bytes()),
             reference_sha256=sha(args.reference.read_bytes()), metrics=objective.measure(noise_colour.downsample(audio * gain)),
             source_pcm_in_output=False, vgm_sha256=sha(data), wave_sha256=sha((args.output / 'ym3812-preview.wav').read_bytes())))
        return
    for mode in ('sine', 'waveforms', 'fm'):
        controls, fitting_gain = fit(source, mode)
        np.savez_compressed(args.output / f'{mode}-controls.npz', **controls)
        for ramp in ((0, 4) if mode == 'fm' else (0,)):
            name = mode + ('-tl-ramp' if ramp else '')
            smooth = mode == 'sine' and not args.legacy_sine_transitions
            if smooth: name = 'sine-smooth'
            data, writes = smooth_vgm(controls, args.transition_ms, args.transition_steps) if smooth else vgm(controls, ramp)
            raw, samples, parsed_writes = replay(data)
            assert writes == parsed_writes and samples == 1323000
            audio = playback(raw, samples)
            gain = min(float(np.sqrt(np.mean(source ** 2) / max(np.mean(noise_colour.downsample(audio) ** 2), 1e-20))), .95 / max(float(abs(audio).max()), 1e-12))
            audio *= gain
            quality.write_wav(args.output / f'{name}.wav', audio, OUT_RATE)
            (args.output / f'{name}.vgm').write_bytes(data)
            coded = gzip.compress(data, mtime=0)
            (args.output / f'{name}.vgz').write_bytes(coded)
            result = dict(name=name, mode=mode, ramp_steps=ramp, global_playback_gain=gain,
                          smooth_sine_transitions=smooth, nominal_transition_ms=args.transition_ms if smooth else None,
                          transition_steps=args.transition_steps if smooth else None,
                          fitting_gain=fitting_gain, writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded),
                          wave_sha256=sha((args.output / f'{name}.wav').read_bytes()), vgm_sha256=sha(data),
                          metrics=objective.measure(noise_colour.downsample(audio)),
                          peak=float(abs(audio).max()), chip_clipping_samples=int(np.sum((raw <= -1) | (raw >= 32767 / 32768))),
                          source_pcm_in_output=False, native_samples=len(raw), complete=True)
            trials.append(result); print(json.dumps(result), flush=True)
    selected = min(trials, key=lambda r: r['metrics']['objective_db'])
    import ymfm._core
    binary = Path(ymfm._core.__file__)
    report = dict(complete=True, date='2026-10-13', reference_sha256=sha(args.reference.read_bytes()),
                  seconds=30, fields=1500, channels=9, operators_per_channel=2, chip='YM3812', clock_hz=CLOCK,
                  native_rate_exact=NATIVE_RATE, control_hz=50, real_registers=True, rhythm=False, csm=False,
                  patch_bank=PATCHES, trials=trials, selected=selected['name'],
                  output_filter='Fixed20-Hz AC coupling and8-kHz129-tap fractional resampler; constant playback gain only.',
                  emulator='ymfm-py', emulator_version=importlib.metadata.version('ymfm-py'),
                  emulator_binary_sha256=sha(binary.read_bytes()), silicon_bit_exact_claim=False,
                  physical_chip_or_z80_verified=False, no_source_pcm_in_stream=True,
                  elapsed_seconds=time.perf_counter() - start,
                  producer_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')))
    save(args.output / 'report.json', report)


if __name__ == '__main__': main()
