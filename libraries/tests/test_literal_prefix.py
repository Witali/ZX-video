"""Literal prefixes must preserve one-byte runs and every coroutine quota return."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for package in ('lzsa', 'zx0'):
    sys.path.insert(0, str(ROOT/package/'src'))

import zx0
from zx0.block import build as block
from zx0.resumable import build as coroutine


class LiteralPrefixTests(unittest.TestCase):
    def test_supported_profiles_and_reservations(self):
        self.assertNotIn('literal_prefix', block()[2])
        self.assertNotIn('literal_prefix', coroutine()[2])
        for variant in ('standard', 'turbo', 'mega'):
            with self.assertRaises(ValueError):
                block(variant, literal_prefix=True)
        with self.assertRaises(ValueError):
            coroutine('turbo_tuned', literal_prefix=True)
        with self.assertRaises(ValueError):
            block(core_limit=0x8000+194, branch_tuned=True, literal_prefix=True)
        with self.assertRaises(ValueError):
            coroutine(literal_prefix=True)  # Larger untuned hot region needs explicit room.
        for builder in (block, coroutine):
            metadata = builder(core=0x9103, core_limit=0x9500, literal_prefix=True)[2]
            self.assertEqual(metadata['literal_prefix_minimum'], 2)
            self.assertEqual(metadata['literal_copy_delta_tstates'], -5)
            self.assertEqual(metadata['additional_sync_tstates'], 0 if builder is block else 26)

    def test_cli_and_commented_exact_export(self):
        with tempfile.TemporaryDirectory() as directory:
            for variant in ('fast', 'fast-block'):
                destination = Path(directory)/variant
                argv = ['zx0','build','--variant',variant,'--literal-prefix','--branch-tuned',
                        '--core','0x9103','--core-limit','0x9500','--output',str(destination)]
                script = ('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');'
                          'sys.argv='+repr(argv)+';runpy.run_module("zx0.__main__",run_name="__main__")')
                subprocess.run([sys.executable,'-I','-c',script], check=True, capture_output=True)
                metadata = json.loads((destination/'metadata.json').read_text())
                self.assertTrue(metadata['literal_prefix'])
                assembly = (destination/'decoder.asm').read_text()
                self.assertIn('saving 5 T/run', assembly)
                self.assertIn('BC=1 entry skips LDI', assembly)
                rebuilt = []
                for line in assembly.splitlines():
                    if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
                    elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
                builder = block if variant=='fast-block' else coroutine
                expected = builder(core=0x9103, core_limit=0x9500, literal_prefix=True, branch_tuned=True)
                self.assertEqual([(at,bytes(data)) for at,data in rebuilt], expected[0])

    @unittest.skipUnless(importlib.util.find_spec('z80'), 'install lzsa[native]')
    def test_counts_quota_frontiers_and_irq(self):
        from native_block import execute
        from lzsa.native import execute as resume
        for count in (1,2,3,7,255,256,257,300):
            raw = bytes(i%251 for i in range(count))
            payload = zx0.encode(raw, [zx0.Token(0,count)])
            for tuned in (False,True):
                options = dict(core=0x9103, core_limit=0x9500, branch_tuned=tuned)
                before, after = block(**options), block(literal_prefix=True, **options)
                a,b = execute(before,payload,raw),execute(after,payload,raw)
                self.assertEqual(b['tstates']-a['tstates'], -5 if count>=2 else 0)
                self.assertTrue(execute(after,payload,raw,interrupts=True)['exact'])
                before, after = coroutine(**options),coroutine(literal_prefix=True, **options)
                for demand in (1,17,256,None):
                    a = resume(*before,payload,raw,source=0x2000,slice_bytes=demand)
                    b = resume(*after,payload,raw,source=0x2000,slice_bytes=demand,interrupts=True)
                    self.assertEqual(a['output_cursors'],b['output_cursors'])
                    self.assertEqual(len(a['slices']),len(b['slices']))


if __name__ == '__main__':
    unittest.main()
