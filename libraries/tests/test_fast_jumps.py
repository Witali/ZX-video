"""End-to-end regressions for the optional unconditional-branch speed policy."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for package in ('lzsa', 'zx0'):
    sys.path.insert(0, str(ROOT / package / 'src'))

import lzsa
import zx0
from lzsa.block import build as lblock
from lzsa.resumable import build as coroutine
from zx0.block import build as zblock


@unittest.skipUnless(importlib.util.find_spec('z80'), 'install lzsa[native]')
class FastJumpNativeTests(unittest.TestCase):
    def test_zx0_gamma_offset_overlap_and_relocation(self):
        from native_block import execute
        from measure_bit_phases import samples
        # Cover long Elias codes, offsets, overlap and phases. The benchmark
        # separately replays every authenticated real block.
        cases = [case for case in samples() if not case[0].startswith('real-')]
        for variant, growth in (('standard', 2), ('turbo', 1), ('mega', 1), ('fast', 0)):
            before = zblock(variant)
            after = zblock(variant, fast_jumps=True)
            self.assertEqual(after[2]['code_bytes'] - before[2]['code_bytes'], growth)
            for name, payload, raw in cases:
                with self.subTest(variant=variant, case=name):
                    old = execute(before, payload, raw)
                    new = execute(after, payload, raw)
                    self.assertLessEqual(new['tstates'], old['tstates'])
                    if variant in ('turbo', 'mega'):
                        self.assertEqual(new['tstates'] - old['tstates'], -2)
                    relocated = zblock(variant, core=0x9103, core_limit=0x9500, fast_jumps=True)
                    self.assertEqual(execute(relocated, payload, raw)['tstates'], new['tstates'])
            if growth:
                with self.assertRaises(ValueError):
                    zblock(variant, core_limit=0x8000 + before[2]['code_bytes'], fast_jumps=True)
            else:
                self.assertEqual(before[0], after[0])

    def test_lzsa_16bit_offsets_short_words_and_yields(self):
        from native_block import execute
        from lzsa.native import execute as resume
        from measure_long_copy import noncanonical_cases
        raw = bytes(i % 251 for i in range(8705))
        raw += (raw * 2)[:15872 - len(raw)]
        cases = [('offset16', lzsa.encode(raw, [(8705, 7167, 8705)]), raw)]
        cases += list(noncanonical_cases())
        for name, payload, raw in cases:
            with self.subTest(case=name):
                old = execute(lblock(), payload, raw)
                new = execute(lblock(fast_jumps=True), payload, raw, interrupts=True)
                # Plain timings use a separate replay, excluding injected IRQs.
                plain = execute(lblock(fast_jumps=True), payload, raw)
                self.assertEqual(plain['tstates'] - old['tstates'], -2 if name == 'offset16' else 0)
                self.assertTrue(new['exact'])
                before = resume(*coroutine(), payload, raw, source=0x2000)
                after = resume(*coroutine(fast_jumps=True), payload, raw, source=0x2000)
                self.assertEqual(len(before['slices']), len(after['slices']))
                self.assertTrue(all(b <= a for a, b in zip(before['slices'], after['slices'])))


class FastJumpExportTests(unittest.TestCase):
    def test_streaming_policy_preserves_fixed_wrapper_extent(self):
        for direct in (False, True):
            for extended in (False, True):
                options = dict(streaming=True, direct_header=direct, long_copy=extended,
                               word_state_init=extended, restore_compare=extended, core_limit=0x9000)
                before = coroutine(**options)
                after = coroutine(**options, fast_jumps=True)
                self.assertEqual(before[2]['prefix_end'], after[2]['prefix_end'])
                self.assertEqual(before[1]['state'], after[1]['state'])
                self.assertEqual(after[2]['code_bytes']-before[2]['code_bytes'], 2)
                self.assertEqual(after[2]['fast_jump_code_delta'], 2)
                self.assertTrue(all(row['address'] >= 0x8de0 for row in after[2]['fast_jump_sites']))

    def test_cli_export_and_reservation_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            for package, options, builder in (
                ('zx0', ['--variant', 'standard'], lambda: zblock('standard', fast_jumps=True)),
                ('zx0', ['--variant', 'mega'], lambda: zblock('mega', fast_jumps=True)),
                ('lzsa', ['--profile', 'fast-block'], lambda: lblock(fast_jumps=True)),
                ('lzsa', ['--streaming', '--direct-header'],
                 lambda: coroutine(core=0x8000, core_limit=0x8400, streaming=True,
                                   direct_header=True, fast_jumps=True)),
            ):
                path = Path(directory) / (package + '-'.join(options))
                argv = [package, 'build', *options, '--fast-jumps', '--core', '0x8000',
                        '--core-limit', '0x8400', '--output', str(path)]
                code = ('import sys,runpy;sys.path.insert(0,' + repr(str(ROOT/package/'src')) + ');'
                        'sys.argv=' + repr(argv) + ';runpy.run_module(' + repr(package+'.__main__')
                        + ',run_name="__main__")')
                subprocess.run([sys.executable, '-I', '-c', code], check=True, capture_output=True)
                text = (path/'decoder.asm').read_text(encoding='utf-8')
                rebuilt = []
                for line in text.splitlines():
                    if line.startswith('org '):
                        rebuilt.append((int(line[5:], 16), bytearray()))
                    elif line.startswith('db '):
                        rebuilt[-1][1].extend(int(x[1:], 16) for x in line[3:].split(','))
                self.assertEqual([(at, bytes(blob)) for at, blob in rebuilt], builder()[0])
                self.assertIn('12 -> 10 T', text)
                self.assertTrue(json.loads((path/'metadata.json').read_text())['fast_jumps'])
        with self.assertRaises(ValueError):
            lblock('small', fast_jumps=True)


if __name__ == '__main__':
    unittest.main()
