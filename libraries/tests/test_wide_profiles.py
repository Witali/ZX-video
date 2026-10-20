"""Wide public decoders preserve the independently measured raw implementation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lzsa/src'))
from lzsa.block import build
from full_token_dispatch import build as independent


class WideProfileTests(unittest.TestCase):
    def test_public_matches_independent_and_all_alignment_sizes(self):
        for variant, shared, size in (('wide', False, 6998), ('wide-shared', True, 3446)):
            for core in (0x8000, 0x9103):
                regions, labels, metadata = build(variant, core=core, core_limit=0xb000)
                expected, oldlabels, _ = independent(core=core, shared_literals=shared)
                self.assertEqual(regions, expected)
                self.assertTrue(all(labels[k]==v for k, v in oldlabels.items()))
                self.assertEqual(labels['dispatch_low']%256, 0)
                self.assertEqual(labels['dispatch_high']-labels['dispatch_low'], 256)
                self.assertEqual(metadata['code_bytes'], size+metadata['alignment_padding'])
                self.assertEqual(metadata['total_storage_bytes'], metadata['code_bytes']+6)
                self.assertEqual(metadata['storage_budget_bytes'], 10000)
            for low in range(256):
                _, _, metadata = build(variant, core=0x8000+low, core_limit=0xb000)
                self.assertLessEqual(metadata['total_storage_bytes'], 10000)
                self.assertEqual(metadata['alignment_padding'], (-low)&255)
            with self.assertRaises(ValueError):
                build(variant)
            with self.assertRaises(ValueError):
                build(variant, core_limit=0x8000+size-1)
            self.assertEqual(build(variant, core_limit=0x8000+size)[2]['code_bytes'], size)
            for option in ('long_copy', 'near_literals', 'fast_jumps', 'branch_tuned', 'nibble_prefill', 'compact_branches'):
                with self.assertRaises(ValueError):
                    build(variant, core_limit=0xb000, **{option:True})
        for core, limit in ((-1, 0xb000), (0x8000, 0x8000), (0x8000, 65537), (0xf000, 65536)):
            with self.assertRaises(ValueError):
                build('wide', core=core, core_limit=limit)

    def test_cli_and_commented_exact_export(self):
        with tempfile.TemporaryDirectory() as temp:
            for variant in ('wide', 'wide-shared'):
                path = Path(temp)/variant
                argv = ['lzsa', 'build', '--profile', variant+'-block', '--core', '0x9103',
                        '--core-limit', '0xb000', '--output', str(path)]
                code = ('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'lzsa/src'))+');'
                        'sys.argv='+repr(argv)+';runpy.run_module("lzsa.__main__",run_name="__main__")')
                subprocess.run([sys.executable, '-I', '-c', code], check=True, capture_output=True)
                metadata = json.loads((path/'metadata.json').read_text())
                self.assertTrue(metadata['full_token_dispatch'])
                self.assertLessEqual(metadata['total_storage_bytes'], 10000)
                text = (path/'decoder.asm').read_text()
                self.assertIn('IRQ must preserve both main and alternate', text)
                self.assertIn('wrap BC', text)
                rebuilt = []
                for line in text.splitlines():
                    if line.startswith('org '):rebuilt.append((int(line[5:], 16), bytearray()))
                    elif line.startswith('db '):rebuilt[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
                self.assertEqual([(at,bytes(data)) for at,data in rebuilt],
                                 build(variant,core=0x9103,core_limit=0xb000)[0])


if __name__ == '__main__':
    unittest.main()
