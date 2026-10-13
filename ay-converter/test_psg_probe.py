"""Execute the optional startup probe in an independent Z80 with bus fixtures."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from z80 import Z80Machine


def execute(code, initial, kind):
    machine = Z80Machine(); machine.set_memory_block(0x8000, code)
    machine.pc = 0x8000; machine.sp = 0xb000
    machine.memory[0xb000:0xb002] = bytes((0, 0x90)); machine.set_breakpoint(0x9000)
    value = initial; writes = []; selected = None
    def output(port, data):
        nonlocal value, selected
        if port == 0xfffd: selected = data; assert data == 1
        else:
            assert port == 0xbffd and selected == 1
            writes.append(data); value = data
    def input_(port):
        assert port == 0xfffd and selected == 1
        if kind == 'absent': return 255
        if kind == 'stuck': return 15
        if kind == 'ay': return value & 15
        if kind == 'ym': return value & 15 if value == 255 else value & 31
        return 16
    machine.set_output_callback(output); machine.set_input_callback(input_)
    machine.ticks_to_stop = 1000
    while machine.pc != 0x9000:
        if machine.run() & machine._TICKS_LIMIT_HIT: raise AssertionError('probe did not return')
    assert machine.sp == 0xb002 and len(writes) == 4 and writes[:3] == [0, 15, 31]
    if kind in ('ay', 'ym'): assert value & 15 == initial & 15
    return machine.a, 1000 - machine.ticks_to_stop


class PsgProbeTests(unittest.TestCase):
    def test_actual_assembled_probe_restores_register_and_classifies_bus(self):
        root = Path(__file__).resolve().parents[1]; temporary = root / '.tmp'; temporary.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary, prefix='probe-test-') as directory:
            folder = Path(directory)
            folder.resolve().relative_to(root)
            subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=' + str(folder / 'probe.bin'),
                            str(Path(__file__).with_name('psg_probe.asm'))], check=True, capture_output=True)
            code = (folder / 'probe.bin').read_bytes()
        for kind, wanted in (('ay', 1), ('ym', 2), ('absent', 0), ('stuck', 0), ('unknown', 0)):
            for initial in (0, 1, 15, 31, 128, 255):
                result, cycles = execute(code, initial, kind)
                self.assertEqual(result, wanted)
                # Independent instruction-table sums, including RET but not
                # caller CALL/DI: AY265, YM279, first failed bus check226 T.
                self.assertEqual(cycles, 265 if kind == 'ay' else 279 if kind == 'ym' else 226)


if __name__ == '__main__': unittest.main()
