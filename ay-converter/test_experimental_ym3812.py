"""Independent chip constraints, quantization and actual register-stream checks."""
import struct
import unittest

import numpy as np
import ymfm
import experimental_ym3812 as opl


def audit(data, controls):
    """Independent VGM walk: check all9 target states at every20-ms boundary."""
    state = np.zeros(256, np.uint8); pos = 0x100; elapsed = 0; fields = 0
    last_timed_write = None; writes = 0
    while pos < len(data):
        command = data[pos]; pos += 1
        if command == 0x66: break
        if command == 0x5a:
            address, value = data[pos:pos + 2]; pos += 2
            if elapsed > 0 and last_timed_write is not None:
                assert elapsed - last_timed_write >= 2
            last_timed_write = elapsed; writes += 1; state[address] = value
            assert state[1] == 0x20 and state[8] == state[0xbd] == 0
        elif command == 0x61:
            duration = struct.unpack_from('<H', data, pos)[0]; pos += 2; elapsed += duration
        elif 0x70 <= command <= 0x7f: elapsed += (command & 15) + 1
        else: raise AssertionError('non-OPL/PCM command')
        if elapsed and elapsed % 882 == 0 and fields < elapsed // 882:
            assert elapsed // 882 == fields + 1
            for ch, mod in enumerate(opl.MOD_OFFSETS):
                patch = opl.PATCHES[int(controls['patch'][fields, ch])]
                assert int(state[0xa0 + ch]) | (int(state[0xb0 + ch]) & 3) << 8 == controls['fnum'][fields, ch]
                assert (state[0xb0 + ch] >> 2) & 7 == controls['block'][fields, ch]
                assert bool(state[0xb0 + ch] & 0x20) == (controls['level'][fields, ch] < 64)
                assert state[0x43 + mod] == min(int(controls['level'][fields, ch]), 63)
                assert state[0x20 + mod] == 0x20 | patch['mod_mul']
                assert state[0x23 + mod] == 0x20 | patch['car_mul']
                assert state[0x40 + mod] == patch['mod_tl'] and state[0xe3 + mod] == patch['wave']
                assert state[0xc0 + ch] == 0
            fields += 1
    assert pos == len(data) and fields == len(controls['fnum']) and elapsed == fields * 882
    return dict(fields=fields, writes=writes, all_channel_states_exact=True, timed_write_spacing_samples_min=2)


class Ym3812Tests(unittest.TestCase):
    def tone(self, patch=0, tl=0, waveform_enable=True):
        chip = ymfm.YM3812(clock=opl.CLOCK); chip.reset()
        opl.tone_patch(chip, patch if waveform_enable else 0, tl=tl)
        if not waveform_enable:
            opl.register(chip, 1, 0); opl.register(chip, 0xe3, patch)
        opl.chip_audio(chip, 4096)
        return opl.chip_audio(chip, 32768)

    def test_frequency_codes_and_real_total_level_steps(self):
        wanted = np.array([55., 440., 1000., 6200.])
        fnum, block = opl.frequency_code(wanted)
        realized = fnum * 2. ** block * opl.NATIVE_RATE / 2 ** 20
        self.assertLess(float(np.max(abs(realized / wanted - 1))), .001)
        fnum, block = opl.frequency_code(np.array([7900. / 2]))
        self.assertAlmostEqual(float(fnum[0] * 2. ** block[0] * opl.NATIVE_RATE / 2 ** 20 * 2), 7900, delta=7)
        chip = ymfm.YM3812(clock=opl.CLOCK)
        opl.tone_patch(chip, 14, int(fnum[0]), int(block[0]), 12)
        opl.chip_audio(chip, 4096); signal = opl.chip_audio(chip, 65536)
        peak = int(abs(np.fft.rfft(signal * np.hanning(len(signal)))).argmax())
        expected = float(fnum[0] * 2. ** block[0] * opl.NATIVE_RATE / 2 ** 20 * 2)
        self.assertAlmostEqual(peak * opl.NATIVE_RATE / len(signal), expected, delta=1)
        a, b = self.tone(tl=0), self.tone(tl=8)
        ratio = np.sqrt(np.mean(b ** 2) / np.mean(a ** 2))
        self.assertAlmostEqual(float(ratio), 10 ** (-6 / 20), delta=.003)

    def test_four_real_waveforms(self):
        for patch in (1, 2, 3):
            signal = self.tone(patch)
            self.assertGreater(float(signal.mean()), .015)
        for patch, harmonic in ((0, 1), (1, 1), (2, 2), (3, 2)):
            signal = self.tone(patch)
            spectrum = abs(np.fft.rfft(signal - signal.mean()))
            self.assertEqual(int(spectrum.argmax()), harmonic * 32)

    def test_nine_distinct_native_channels(self):
        chip = ymfm.YM3812(clock=opl.CLOCK); chip.reset()
        for address, value in opl.initial_registers(): opl.register(chip, address, value)
        fnum, block = opl.frequency_code(np.array([107., 137., 173., 211., 277., 353., 461., 599., 787.]))
        actual = fnum * 2. ** block * opl.NATIVE_RATE / 2 ** 20
        for ch, mod in enumerate(opl.MOD_OFFSETS):
            for address, value in ((0x43 + mod, 12), (0xa0 + ch, int(fnum[ch]) & 255),
                                   (0xb0 + ch, 0x20 | int(block[ch]) << 2 | int(fnum[ch]) >> 8)):
                opl.register(chip, address, value)
        opl.chip_audio(chip, 4096); signal = opl.chip_audio(chip, 65536)
        spectrum = abs(np.fft.rfft(signal * np.hanning(len(signal)))) / (len(signal) / 4)
        for frequency in actual:
            index = round(frequency * len(signal) / opl.NATIVE_RATE)
            self.assertGreater(float(spectrum[index - 1:index + 2].max()), .02)
        self.assertLess(float(abs(signal).max()), 1)

    def controls(self):
        fnum, block = opl.frequency_code(np.array([440., 660., 220., 880.]))
        return dict(fnum=np.tile(fnum[:, None], (1, 9)), block=np.tile(block[:, None], (1, 9)),
                    patch=np.tile(np.array([0, 1, 7, 2], np.uint8)[:, None], (1, 9)),
                    level=np.tile(np.array([16, 64, 24, 8], np.uint8)[:, None], (1, 9)))

    def test_vgm_timing_states_and_replay(self):
        controls = self.controls()
        for ramp in (0, 4):
            data, writes = opl.vgm(controls, ramp)
            self.assertEqual(audit(data, controls)['writes'], writes)
            first, samples, count = opl.replay(data)
            second, *_ = opl.replay(data)
            self.assertTrue(np.array_equal(first, second))
            self.assertEqual((samples, count), (4 * 882, writes))
            self.assertEqual(len(first), samples * opl.CLOCK // (72 * opl.OUT_RATE))

    def test_invalid_controls_and_vgm_are_rejected(self):
        original = self.controls()
        for name, value in (('fnum', 1024), ('block', 8), ('patch', len(opl.PATCHES)), ('level', 65)):
            bad = {k: v.copy() for k, v in original.items()}; bad[name][0, 0] = value
            with self.assertRaises(ValueError): opl.validate(bad)
        with self.assertRaises(ValueError): opl.vgm(original, -1)
        with self.assertRaises(ValueError): opl.replay(b'Vgm ')
        data, _ = opl.vgm(original)
        with self.assertRaises(ValueError): opl.replay(data[:-1])
        altered = bytearray(data); altered[0x100] = 0x67
        with self.assertRaises(ValueError): opl.replay(altered)


if __name__ == '__main__': unittest.main()
