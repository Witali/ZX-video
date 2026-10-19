"""Guard the pre-normalized nibble cache, especially single-nibble raw EOF."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lzsa/src'))
from lzsa.block import build as block
from lzsa.resumable import build as coroutine


class NibblePrefillContractTests(unittest.TestCase):
    def test_defaults_and_storage_contract(self):
        for builder in (block,coroutine):
            for options in ({},{'branch_tuned':True,'fast_jumps':True},
                            {'long_copy':True,'near_literals':True}):
                before=builder(core_limit=0x9000,**options)
                explicit=builder(core_limit=0x9000,nibble_prefill=False,**options)
                after=builder(core_limit=0x9000,nibble_prefill=True,**options)
                self.assertEqual(before,explicit)
                self.assertEqual(after[2]['code_bytes'],before[2]['code_bytes']+4)
                self.assertTrue(after[2]['nibble_prefill'])
                if builder is coroutine:
                    self.assertEqual(before[1]['end']-before[1]['state'],after[1]['end']-after[1]['state'])
                    self.assertEqual(before[0][0][0],after[0][0][0])
                    self.assertEqual(len(before[0][0][1]),len(after[0][0][1]))
        with self.assertRaises(ValueError):block('small',nibble_prefill=True)
        with self.assertRaises(ValueError):block(core_limit=0x8000+221,nibble_prefill=True)

    def test_cli_and_generated_explanation(self):
        with tempfile.TemporaryDirectory() as directory:
            for options in (['--profile','fast-block'],['--streaming','--direct-header','--branch-tuned']):
                path=Path(directory)/str(len(options))
                argv=['lzsa','build',*options,'--nibble-prefill','--output',str(path)]
                code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'lzsa/src'))+');'
                      'sys.argv='+repr(argv)+';runpy.run_module("lzsa.__main__",run_name="__main__")')
                subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)
                self.assertTrue(json.loads((path/'metadata.json').read_text())['nibble_prefill'])
                self.assertIn('refill 62 -> 65 T, cached 23 -> 16 T',(path/'decoder.asm').read_text())


@unittest.skipUnless(importlib.util.find_spec('z80'),'install lzsa[native]')
class NibblePrefillNativeTests(unittest.TestCase):
    def test_all_byte_values_and_both_cache_phases(self):
        from measure_nibble_prefill import primitive
        before=primitive(block());after=primitive(block(nibble_prefill=True))
        self.assertEqual(len(after),1024)
        for old,new in zip(before,after):
            self.assertEqual((old['refill_tstates'],old['cached_tstates']),(62,23))
            self.assertEqual((new['refill_tstates'],new['cached_tstates']),(65,16))

    def test_single_nibble_eof_dirty_cache_and_relocation(self):
        from native_block import execute
        from lzsa.native import execute as resume
        for payload,raw in ((bytes.fromhex('ef41f0e8'),b'A'),(bytes.fromhex('e7f0e8'),b'')):
            for core in (0x8000,0x9103):
                for alternate in (0,1,0xffff,0x5500):
                    result=execute(block(core=core,core_limit=core+0x400,nibble_prefill=True),payload,raw,alternate_af=alternate)
                    self.assertTrue(result['exact'])
                profile=coroutine(core=core,core_limit=core+0x400,nibble_prefill=True)
                self.assertTrue(resume(*profile,payload,raw,source=0x2000)['exact'])


if __name__=='__main__':unittest.main()
