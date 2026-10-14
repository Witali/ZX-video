"""Native sine purity, real-register attenuation and source-tone fitting checks."""
import unittest
import numpy as np
import ymfm
import overtones as h
import refit_overtones as refit
import experimental_ym3812 as opl


def oscillator(pure, block, mod_level=63):
    chip = ymfm.YM3812(clock=opl.CLOCK); chip.reset()
    for address, value in opl.initial_registers():
        if pure and address == 0x60: value = 0
        if pure and address == 0xc0: value = 1
        opl.register(chip, address, value)
    for address, value in ((0x40, mod_level), (0x43, 0), (0xa0, 0), (0xb0, 0x22 | block << 2)):
        opl.register(chip, address, value)
    opl.chip_audio(chip, 4096)
    return opl.chip_audio(chip, 32768)


def harmonic_ratio(audio):
    # FNUM512 gives an integer number of cycles. No window/leakage estimate
    # contaminates the bin sum; omit DC and the fundamental.
    spectrum = abs(np.fft.rfft(audio)); peak = int(spectrum.argmax())
    harmonics = np.arange(2, min(50, (len(spectrum) - 1) // peak + 1)) * peak
    return float(np.sum(spectrum[harmonics] ** 2) / spectrum[peak] ** 2)


class OvertonesTests(unittest.TestCase):
    def controls(self, count=32):
        fnum, block = opl.frequency_code(np.array([440., 4000.]))
        return dict(fnum=np.tile(np.r_[fnum, np.full(7, fnum[0])][None, :], (count, 1)).astype(np.uint16),
                    block=np.tile(np.r_[block, np.full(7, block[0])][None, :], (count, 1)).astype(np.uint8),
                    patch=np.zeros((count, 9), np.uint8),
                    level=np.tile(np.array([12, 24] + [64] * 7, np.uint8)[None, :], (count, 1)))

    def test_native_purity_and_modulator_silence_at_four_frequencies(self):
        for block in (1, 3, 4, 5):
            old = oscillator(False, block)
            pure = oscillator(True, block)
            self.assertTrue(np.array_equal(pure, oscillator(True, block, 0)))
            self.assertLess(harmonic_ratio(pure), harmonic_ratio(old) * .001)
            self.assertGreater(float(np.std(pure)), float(np.std(old)) * .95)

    def test_source_cap_changes_only_unsupported_high_tl(self):
        controls = self.controls(); t = np.arange(32 * 441) / opl.RATE
        source = .1 * np.sin(2 * np.pi * 440 * t)
        observed = source + .1 * np.sin(2 * np.pi * 4000 * t)
        altered = h.cap_high_controls(source, observed, controls, 1.)
        self.assertTrue(np.array_equal(altered['level'][:, 0], controls['level'][:, 0]))
        self.assertGreater(int(np.min(altered['level'][4:-4, 1])), 24)
        for key in ('fnum', 'block', 'patch'): self.assertTrue(np.array_equal(altered[key], controls[key]))
        self.assertTrue(np.array_equal(altered['level'][:, 2:], controls['level'][:, 2:]))
        for key, value in h.cap_high_controls(source, observed, controls, 0.).items(): self.assertTrue(np.array_equal(value, controls[key]))
        data, writes = h.pure_vgm(altered)
        self.assertEqual(h.audit(data, altered)['writes'], writes)
        bad = bytearray(data); offset = data.index(bytes((0x5a, 0xc0, 1)), 256); bad[offset + 2] = 0
        with self.assertRaises(AssertionError): h.audit(bytes(bad), altered)

    def test_resolved_fit_preserves_a_source_sine_without_upper_voices(self):
        t = np.arange(60 * 441) / opl.RATE
        controls = refit.fit(.1 * np.sin(2 * np.pi * 440 * t), 1024, 0., 3.535606377250534)
        self.assertEqual(opl.validate(controls), 60)
        frequency = controls['fnum'] * 2. ** controls['block'] * np.where(controls['patch'] == 14, 2, 1) * opl.NATIVE_RATE / 2 ** 20
        active = controls['level'][5:-5] < 64
        self.assertTrue(np.any(active))
        self.assertLess(float(np.max(abs(frequency[5:-5][active] - 440))), 5)
        self.assertTrue(np.isin(controls['patch'], [0, 14]).all())

    def test_invalid_cap_and_fit_inputs(self):
        controls = self.controls(); source = np.zeros(32 * 441)
        for strength in (float('nan'), -1, 2):
            with self.assertRaises(ValueError): h.cap_high_controls(source, source, controls, strength)
        with self.assertRaises(ValueError): h.cap_high_controls(source[:-1], source, controls, 1.)
        bad = source.copy(); bad[0] = np.nan
        with self.assertRaises(ValueError): h.cap_high_controls(bad, source, controls, 1.)
        for window, exponent, gain in ((100, 0., 1.), (1024, 2., 1.), (1024, 0., 0.)):
            with self.assertRaises(ValueError): refit.fit(source, window, exponent, gain)


if __name__ == '__main__': unittest.main()
