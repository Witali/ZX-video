"""Public optional Mega must equal the independent measured prototype."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
for package in ('lzsa','zx0'):sys.path.insert(0,str(ROOT/package/'src'))
from zx0.block import build
from mega_offset_profile import build as reference


class MegaTunedTests(unittest.TestCase):
    def test_public_layout_and_cli(self):
        for fast in (False,True):
            for origin in (0x8000,0x9103):
                public=build('mega',core=origin,core_limit=origin+0x400,fast_jumps=fast,mega_tuned=True)
                expected=reference(origin=origin,fast_jumps=fast,reuse_tail_jp=True)
                self.assertEqual(public[:2],expected[:2])
                self.assertEqual(public[2]['code_bytes'],669+fast)
                self.assertEqual(public[2]['max_decoder_stack_bytes'],4)
                self.assertEqual(public[2]['workspace_bytes'],673+fast)
                self.assertFalse(public[2]['coroutine_supported'])
        with self.assertRaises(ValueError):build('fast',mega_tuned=True)
        with tempfile.TemporaryDirectory() as directory:
            argv=['zx0','build','--variant','mega','--mega-tuned','--fast-jumps',
                  '--core','0x8000','--core-limit','0x8400','--output',directory]
            code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');'
                  'sys.argv='+repr(argv)+';runpy.run_module("zx0.__main__",run_name="__main__")')
            subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)
            metadata=json.loads((Path(directory)/'metadata.json').read_text())
            self.assertTrue(metadata['mega_tuned'])
            self.assertEqual(metadata['code_bytes'],670)
            self.assertIn('No coroutine ABI',(Path(directory)/'decoder.asm').read_text())


if __name__=='__main__':unittest.main()
