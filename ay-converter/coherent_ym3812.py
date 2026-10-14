"""Opt-in source-confirmed trajectories for the existing nine-voice OPL2 model.

Keep historical producers/exporters unchanged. The offline lattice uses
60..100-ms context without shifting the source timeline. Every selected tone,
level and inactive state is emitted through real ordinary YM3812 registers.
"""
import numpy as np
import experimental_ym3812 as opl
import psychoacoustic
from simulation_refine import spectra, tick_rms


def path(emission, frequency, levels, confidence, strength):
    """Second-order Viterbi across the complete candidate lattice.

    State pairs retain the preceding pitch velocity for acceleration costs.
    Supported strong tones pay less continuity cost so real attacks survive.
    The zero-strength path is still emission based, not a historical replay.
    """
    count, width = emission.shape
    if count < 1 or frequency.shape != emission.shape or levels.shape != emission.shape or confidence.shape != emission.shape:
        raise ValueError('aligned nonempty lattice arrays required')
    if not np.isfinite(strength) or strength < 0 or np.any(frequency <= 0) or not all(np.isfinite(a).all() for a in (emission, frequency, confidence)):
        raise ValueError('finite costs/frequencies and nonnegative strength required')
    if count == 1: return np.array([emission[0].argmin()], np.uint8)
    pitch = 12 * np.log2(frequency)
    def transition(tick):
        difference = pitch[tick][None, :] - pitch[tick - 1][:, None]
        amount = strength * np.minimum(abs(difference), 12) * (1 - .8 * confidence[tick][None, :])
        amount += strength * .1 * np.minimum(abs(levels[tick][None, :].astype(float) - levels[tick - 1][:, None]) * .75, 24)
        amount += strength * .25 * ((levels[tick][None, :] == 64) != (levels[tick - 1][:, None] == 64))
        return amount, difference
    cost = emission[0][:, None] + emission[1][None, :] + transition(1)[0]
    back = np.zeros((count, width, width), np.uint8)
    for tick in range(2, count):
        change, velocity = transition(tick)
        previous = pitch[tick - 1][None, :] - pitch[tick - 2][:, None]
        acceleration = strength * .20 * np.minimum(abs(velocity[None, :, :] - previous[:, :, None]), 12)
        acceleration *= 1 - .8 * confidence[tick][None, None, :]
        choices = cost[:, :, None] + acceleration
        back[tick] = choices.argmin(axis=0)
        cost = choices.min(axis=0) + change + emission[tick][None, :]
    chosen = np.zeros(count, np.uint8)
    chosen[-2], chosen[-1] = np.unravel_index(cost.argmin(), cost.shape)
    for tick in range(count - 1, 1, -1): chosen[tick - 2] = back[tick, chosen[tick - 1], chosen[tick]]
    return chosen


class SourceLattice:
    def __init__(self, source, original, fitting_gain):
        self.count = opl.validate(original)
        if len(source) != self.count * 441 or not np.isfinite(source).all() or fitting_gain <= 0:
            raise ValueError('finite aligned source and positive fitting gain required')
        if not np.isin(original['patch'], [0, 14]).all(): raise ValueError('measured sine-carrier patches required')
        self.original = original; self.gain = fitting_gain; self.rms = tick_rms(source)
        self.frequency, self.fnum, self.block, self.basis, self.variance, hz, useful, _ = opl.dictionary()
        self.short = spectra(source, np.arange(self.count), 512)[:, useful].astype(np.float32)
        self.weights = psychoacoustic.error_weights(self.short, self.short, psychoacoustic.thresholds(self.short, hz[useful]))
        peak = np.maximum(self.short.max(axis=1), 1e-12)
        self.weights *= (np.maximum(self.short, peak[:, None] * .025) / peak[:, None]) ** -1
        lookup = {int(f | int(b) << 10): i for i, (f, b) in enumerate(zip(self.fnum, self.block))}
        seed_codes = original['fnum'].astype(int) | original['block'].astype(int) << 10
        self.seed = np.array([[lookup[int(value)] for value in row] for row in seed_codes], np.uint16)
        self.patch = original['patch']
        self.amplitude = opl.LEVELS[original['level']] * self.gain
        self.model = np.zeros_like(self.short)
        for channel in range(9):
            self.model += self.basis[self.patch[:, channel], self.seed[:, channel]] * self.amplitude[:, channel, None]
        self.denominator = np.maximum(np.sum(self.weights * self.short ** 2, axis=1), 1e-20)
        long = spectra(source, np.arange(self.count), 2048).astype(np.float32)
        long_hz = np.fft.rfftfreq(4096, 1 / opl.RATE)
        offsets = (0, -1, 1, -2, 2)
        indices = np.stack([self.seed[np.clip(np.arange(self.count) + offset, 0, self.count - 1)] for offset in offsets], axis=2)
        patches = np.stack([self.patch[np.clip(np.arange(self.count) + offset, 0, self.count - 1)] for offset in offsets], axis=2)
        # Add the nearest source-confirmed long-window peak. It refines pitch
        # resolution while emission remains on the attack-preserving512 window.
        snapped = self.seed.copy()
        for tick in range(self.count):
            value = long[tick]
            peaks = np.flatnonzero((value[1:-1] > value[:-2]) & (value[1:-1] >= value[2:])) + 1
            peaks = peaks[(long_hz[peaks] >= 45) & (long_hz[peaks] <= 8000) & (value[peaks] > value.max() * .025)]
            if not len(peaks): continue
            log = np.log(np.maximum(value, 1e-15)); curve = log[peaks - 1] - 2 * log[peaks] + log[peaks + 1]
            shift = np.divide(.5 * (log[peaks - 1] - log[peaks + 1]), curve, out=np.zeros(len(peaks)), where=abs(curve) > 1e-12)
            observed = (peaks + np.clip(shift, -.5, .5)) * long_hz[1]
            for channel in range(9):
                mul = opl.PATCHES[int(self.patch[tick, channel])]['car_mul']
                current = self.frequency[self.seed[tick, channel]] * mul
                nearest = int(np.argmin(abs(observed - current)))
                if abs(observed[nearest] - current) <= max(45, current * .025):
                    snapped[tick, channel] = int(np.argmin(abs(self.frequency - observed[nearest] / mul)))
        self.indices = np.concatenate((indices, snapped[:, :, None], self.seed[:, :, None]), axis=2)
        self.patches = np.concatenate((patches, self.patch[:, :, None], self.patch[:, :, None]), axis=2)
        multiples = np.array([p['car_mul'] for p in opl.PATCHES])[self.patches]
        self.actual_frequency = self.frequency[self.indices] * multiples
        self.levels = np.broadcast_to(original['level'][:, :, None], self.indices.shape).copy()
        self.levels[:, :, -1] = 64
        confidence = np.zeros(self.indices.shape, np.float32)
        for start in range(0, self.count, 128):
            ticks = np.arange(start, min(start + 128, self.count))
            centres = np.rint(self.actual_frequency[ticks] / long_hz[1]).astype(int)
            inner = np.clip(centres[..., None] + np.arange(-2, 3), 0, long.shape[1] - 1)
            outer = np.clip(centres[..., None] + np.arange(-12, 13), 0, long.shape[1] - 1)
            confirmations = []
            for offset in (-2, -1, 0, 1, 2):
                fields = np.clip(ticks + offset, 0, self.count - 1)
                maximum = long[fields[:, None, None, None], inner].max(axis=3)
                background = np.median(long[fields[:, None, None, None], outer], axis=3)
                floor = np.maximum(long[fields].max(axis=1)[:, None, None] * .0001, 1e-12)
                prominence = 20 * np.log10(np.maximum(maximum, floor) / np.maximum(background, floor))
                confirmations.append(np.clip((prominence - 4) / 10, 0, 1))
            confidence[ticks] = np.minimum(confirmations[2], np.mean(confirmations, axis=0))
        confidence[:, :, -1] = 0; self.confidence = confidence

    def fit(self, strength, inactive=False, gate=0., refit_levels=False, envelopes=False):
        if not np.isfinite(gate) or gate < 0: raise ValueError('nonnegative confidence gate required')
        count = self.count; width = self.indices.shape[2]
        chosen = np.zeros((count, 9), np.uint8)
        for channel in range(9):
            residual = np.maximum(self.short - self.model + self.basis[self.patch[:, channel], self.seed[:, channel]] * self.amplitude[:, channel, None], 0)
            emission = np.empty((count, width))
            for start in range(0, count, 128):
                ticks = np.arange(start, min(start + 128, count))
                rows = self.basis[self.patches[ticks, channel], self.indices[ticks, channel]].astype(float)
                rows[:, -1] = 0
                prediction = rows * self.amplitude[ticks, channel, None, None]
                error = np.sum(self.weights[ticks, None, :] * (residual[ticks, None, :] - prediction) ** 2, axis=2)
                emission[ticks] = error / self.denominator[ticks, None]
            emission += gate * (1 - self.confidence[:, channel])
            emission[:, -1] -= gate
            if not inactive: emission[:, -1] = 1e6
            emission[self.actual_frequency[:, channel] > 8000] = 1e6
            chosen[:, channel] = path(emission, self.actual_frequency[:, channel], self.levels[:, channel], self.confidence[:, channel], strength)
        ticks = np.arange(count)[:, None]; channels = np.arange(9)[None, :]
        indices = self.indices[ticks, channels, chosen]; patches = self.patches[ticks, channels, chosen]
        levels = self.levels[ticks, channels, chosen]
        confidence = self.confidence[ticks, channels, chosen]
        amplitudes = opl.LEVELS[levels] * self.gain
        if refit_levels:
            for tick in range(count):
                rows = self.basis[patches[tick], indices[tick]].astype(float)
                gram = (rows * self.weights[tick]) @ rows.T
                correlation = (rows * self.weights[tick]) @ self.short[tick]
                coef = amplitudes[tick].copy(); active = levels[tick] != 64
                for _ in range(12):
                    for voice in np.flatnonzero(active):
                        coef[voice] = max(0, (correlation[voice] - gram[voice] @ coef + gram[voice, voice] * coef[voice]) / max(gram[voice, voice], 1e-20))
                prediction = np.sqrt(np.sum(coef ** 2 * self.variance[patches[tick]]))
                coef *= np.clip(self.rms[tick] / max(prediction, 1e-12), .8, 1.15)
                amplitudes[tick] = coef
        if envelopes:
            frequency = self.frequency[indices] * np.array([p['car_mul'] for p in opl.PATCHES])[patches]
            for tick in range(1, count - 1):
                stable = (abs(12 * np.log2(frequency[tick] / frequency[tick - 1])) < 1) & (abs(12 * np.log2(frequency[tick + 1] / frequency[tick])) < 1)
                weak = (confidence[tick] < .5) & (levels[tick] >= 24) & (levels[tick] < 64)
                attack = self.rms[tick] > self.rms[tick - 1] * 1.4
                if not attack:
                    mask = stable & weak
                    amplitudes[tick, mask] = .2 * amplitudes[tick - 1, mask] + .6 * amplitudes[tick, mask] + .2 * amplitudes[tick + 1, mask]
        if refit_levels or envelopes:
            new = abs(amplitudes[:, :, None] / self.gain - opl.LEVELS).argmin(axis=2).astype(np.uint8)
            new[levels == 64] = 64; levels = new
        result = dict(fnum=self.fnum[indices], block=self.block[indices], patch=patches, level=levels.astype(np.uint8))
        opl.validate(result)
        return result, dict(lattice_choices=chosen, confidence=confidence)
