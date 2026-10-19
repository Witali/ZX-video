"""The optional inline repeat-gamma refill retains old bytes and exact quotas."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for package in ('lzsa', 'zx0'):
    sys.path.insert(0, str(ROOT/package/'src'))

from zx0.block import build as block
from zx0.resumable import build as coroutine


class TailRefillTests(unittest.TestCase):
    def test_frozen_profiles_and_restrictions(self):
        frozen = json.loads((ROOT/'evidence/ten_percent_tail_refill.json').read_text())['profiles']
        for tuned in (False, True):
            for resident in (True, False):
                builder = block if resident else coroutine
                profile = builder(core=0x8000, core_limit=0x8400,
                                  branch_tuned=tuned, inline_tail_refill=True)
                key = ('block' if resident else 'coroutine')+('-branch-tuned' if tuned else '')
                expected = frozen[key]['candidate']
                self.assertEqual(profile[1], expected['labels'])
                self.assertEqual([(at, blob.hex()) for at,blob in profile[0]],
                                 [(row['address'], row['code_hex']) for row in expected['regions']])
                self.assertTrue(profile[2]['inline_tail_refill'])
                self.assertEqual(profile[2]['tail_refill_code_delta_bytes'], 3)
        for builder, variant in ((block, 'mega'), (coroutine, 'turbo_tuned')):
            with self.assertRaises(ValueError):
                builder(variant, inline_tail_refill=True)
        with self.assertRaises(ValueError):
            block(core_limit=0x8000+209, inline_tail_refill=True)

    def test_cli_exact_export(self):
        with tempfile.TemporaryDirectory() as directory:
            for variant in ('fast', 'fast-block'):
                destination = Path(directory)/variant
                argv = ['zx0','build','--variant',variant,'--inline-tail-refill',
                        '--branch-tuned','--output',str(destination)]
                code = ('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');'
                        'sys.argv='+repr(argv)+';runpy.run_module("zx0.__main__",run_name="__main__")')
                subprocess.run([sys.executable,'-I','-c',code], check=True, capture_output=True)
                metadata = json.loads((destination/'metadata.json').read_text())
                self.assertTrue(metadata['inline_tail_refill'])
                lines = (destination/'decoder.asm').read_text()
                self.assertIn('save 18/5 T', lines)
                self.assertIn('partial length', lines)
                rebuilt = []
                for line in lines.splitlines():
                    if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
                    elif line.startswith('db '):rebuilt[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
                builder = block if variant=='fast-block' else coroutine
                expected = builder(core=0x8df2, core_limit=0x8f09,
                                   branch_tuned=True, inline_tail_refill=True)
                self.assertEqual([(at,bytes(blob)) for at,blob in rebuilt], expected[0])


if __name__ == '__main__':
    unittest.main()
