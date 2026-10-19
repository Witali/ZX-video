"""Public branch policies must reproduce the independently frozen candidate bytes."""
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

from lzsa.block import build as lblock
from lzsa.resumable import build as lcoro
from zx0.block import build as zblock
from zx0.resumable import build as zcoro
import lzsa
import zx0


class BranchPolicyTests(unittest.TestCase):
    def test_public_profiles_match_frozen_candidate(self):
        frozen = json.loads((ROOT/'evidence/ten_percent_tuned_branches.json').read_text())['profiles']
        for name, builder, extra in (
                ('lzsa2-block', lblock, dict(fast_jumps=True)),
                ('lzsa2-coroutine', lcoro, dict(fast_jumps=True)),
                ('zx0-block', zblock, {}), ('zx0-coroutine', zcoro, {})):
            regions, labels, metadata = builder(core=0x8000, core_limit=0x8400, branch_tuned=True, **extra)
            expected = frozen[name]
            self.assertEqual(labels, expected['candidate']['labels'])
            self.assertEqual([[at, data.hex()] for at, data in regions],
                             [[item['address'], item['code_hex']] for item in expected['candidate']['regions']])
            self.assertEqual(metadata['branch_changes'], expected['branch_changes'])
            self.assertEqual(metadata['relative_overflow_fallbacks'], expected['relative_overflow_fallbacks'])
        with self.assertRaises(ValueError):
            zblock('mega', branch_tuned=True)
        with self.assertRaises(ValueError):
            zcoro('turbo_tuned', branch_tuned=True)
        with self.assertRaises(ValueError):
            lblock('small', branch_tuned=True)
        with self.assertRaises(ValueError):
            lblock(core_limit=0x8000+219, fast_jumps=True, branch_tuned=True)
        self.assertEqual(zblock(core_limit=0x8000+193, branch_tuned=True)[2]['code_bytes'], 193)

    def test_cli_profile_export(self):
        with tempfile.TemporaryDirectory() as directory:
            for package, options in (('lzsa', ['--streaming', '--direct-header', '--fast-jumps']),
                                     ('lzsa', ['--profile', 'fast-block']),
                                     ('zx0', ['--variant', 'fast-block']), ('zx0', [])):
                path = Path(directory)/(package+'-'.join(options))
                argv = [package, 'build', *options, '--branch-tuned', '--output', str(path)]
                code = ('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/package/'src'))+');'
                        'sys.argv='+repr(argv)+';runpy.run_module('+repr(package+'.__main__')+',run_name="__main__")')
                subprocess.run([sys.executable, '-I', '-c', code], check=True, capture_output=True)
                metadata = json.loads((path/'metadata.json').read_text())
                self.assertTrue(metadata['branch_tuned'])
                self.assertTrue(metadata['branch_changes'])
                self.assertIn('JR 7/12 T versus JP 10 T', (path/'decoder.asm').read_text())

    @unittest.skipUnless(importlib.util.find_spec('z80'), 'install lzsa[native]')
    def test_public_relocated_combined_profile_irqs(self):
        from native_block import execute
        from lzsa.native import execute as resume
        from tuned_branch_profile import build as reference
        raw = b'ABC'*1024
        lpayload = lzsa.encode(raw, [(3, len(raw)-3, 3)])
        zpayload = zx0.encode(raw, [zx0.Token(0,3), zx0.Token(3,len(raw)-3,3)])
        for resident in (True, False):
            for codec, payload, builder in (
                    ('lzsa2', lpayload, lblock if resident else lcoro),
                    ('zx0', zpayload, zblock if resident else zcoro)):
                extra = (dict(long_copy=True, near_literals=True, fast_jumps=True) if codec=='lzsa2' else {})
                if codec=='lzsa2' and not resident:
                    extra['restore_compare'] = True
                profile = builder(core=0x9103, core_limit=0x9500, branch_tuned=True, **extra)
                expected = reference(codec, resident=resident, core=0x9103, **extra)
                self.assertEqual(profile[:2], expected[:2])
                if resident:
                    self.assertTrue(execute(profile, payload, raw, interrupts=True)['exact'])
                else:
                    self.assertTrue(resume(*profile, payload, raw, source=0x2000, interrupts=True)['exact'])


if __name__ == '__main__':
    unittest.main()
