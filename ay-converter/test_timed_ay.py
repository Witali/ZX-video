"""Real DAC ramp state/scheduling constraints and same-state chip diagnostics."""
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
import timed_ay


class TimedAyTests(unittest.TestCase):
    def controls(self, width=11):
        rows = np.zeros((10, width), np.uint8); rows[:, 0] = 252; rows[:, 2] = rows[:, 4] = 1
        rows[:, 7] = 0x3e; rows[:, 8] = np.tile([8, 15], 5)
        if width == 14: rows[:, 11] = 100; rows[:, 13] = 255
        return rows

    def test_all_target_states_and_shared_envelope_exclusion(self):
        for width in (11, 14):
            rows = self.controls(width)
            if width == 14: rows[2:5, 8] = 16; rows[2, 13] = 14
            for ms in (0., 2., 4., 8.):
                data = timed_ay.stream(rows.tobytes(), width, ms)
                checked = timed_ay.audit(data, rows.tobytes())
                self.assertEqual(checked['fields'], 10)
                self.assertEqual(checked['samples'], 8820)
                self.assertGreaterEqual(checked['serial_spacing_output_samples_min'], 1)

    def test_native_dac_changes_reduce_without_counting_square_edges(self):
        root = Path(__file__).resolve().parents[1]; temporary = root / '.tmp'; temporary.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary, prefix='timed-test-') as directory:
            folder = Path(directory); folder.resolve().relative_to(root); values = []
            for ms in (0., 4.):
                data = timed_ay.stream(self.controls().tobytes(), 11, ms)
                (folder / 'commands.gz').write_bytes(gzip.compress(data, mtime=0))
                subprocess.run(['node', str(Path(__file__).with_name('render_timed_ay.js')), str(folder / 'commands.gz'),
                                str(folder / 'audio.f32'), str(folder / 'report.json')], check=True)
                audio = np.fromfile(folder / 'audio.f32', '<f4')
                self.assertEqual(len(audio), 8820)
                self.assertTrue(np.isfinite(audio).all())
                values.append(json.loads((folder / 'report.json').read_bytes())['instant_dac_step_squared_sum'])
        self.assertLess(values[1], values[0] * .7)

    def test_invalid_registers_and_schedule_are_rejected(self):
        rows = self.controls(); rows[0, 1] = 16
        with self.assertRaises(ValueError): timed_ay.stream(rows.tobytes())
        rows = self.controls(); data = bytearray(timed_ay.stream(rows.tobytes()))
        data[22:26] = data[16:20]
        with self.assertRaises(AssertionError): timed_ay.audit(data, rows.tobytes())


if __name__ == '__main__': unittest.main()
