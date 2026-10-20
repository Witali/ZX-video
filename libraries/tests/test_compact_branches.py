"""The smaller conditional policy preserves default and previous tuned profiles."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lzsa/src'))
from lzsa.block import build as block
from lzsa.resumable import build


class CompactBranchTests(unittest.TestCase):
    def test_one_site_size_and_incompatible_options(self):
        for builder in (block,build):
            for options in ({},dict(fast_jumps=True,nibble_prefill=True,long_copy=True,near_literals=True)):
                old=builder(core=0x9103,core_limit=0x9500,**options)
                new=builder(core=0x9103,core_limit=0x9500,compact_branches=True,**options)
                self.assertEqual(new[2]['code_bytes'],old[2]['code_bytes']-1)
                self.assertEqual(new[2]['branch_changes'],[dict(address=new[1]['Case1xx']+2,target='Case11x',before='jp',after='jr')])
                self.assertFalse(new[2].get('branch_tuned',False))
                self.assertEqual(old,builder(core=0x9103,core_limit=0x9500,compact_branches=False,**options))
            with self.assertRaisesRegex(ValueError,'one conditional branch policy'):
                builder(branch_tuned=True,compact_branches=True)
        with self.assertRaises(ValueError):block('small',compact_branches=True)

    def test_cli_export_and_policy_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            for options in ([],['--profile','fast-block'],['--streaming','--direct-header','--compact-sync']):
                argv=['lzsa','build','--compact-branches',*options,'--output',directory]
                code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'lzsa/src'))+');'
                    'sys.argv='+repr(argv)+';runpy.run_module("lzsa.__main__",run_name="__main__")')
                subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)
                self.assertTrue(json.loads((Path(directory)/'metadata.json').read_text())['compact_branches'])
                self.assertIn('Case11x JP NC -> JR NC',(Path(directory)/'decoder.asm').read_text())
                for bad in (['--branch-tuned'],['--profile','small-block']):
                    reject=code.replace(repr(argv),repr(argv+bad))
                    result=subprocess.run([sys.executable,'-I','-c',reject],capture_output=True)
                    self.assertNotEqual(result.returncode,0)

    @unittest.skipUnless(importlib.util.find_spec('z80'),'install lzsa[native]')
    def test_pending_registers_and_tiny_eof(self):
        from measure_compact_sync import execute
        from lzsa import encode
        raw=b'ABC'*171;payload=encode(raw,[(3,len(raw)-3,3)])
        targets=[0,0,1,1,2,3,17,255,256,len(raw)]
        for compact_sync in (False,True):
            options=dict(compact_sync=compact_sync)
            old=execute(build(**options),payload,raw,targets=targets)
            new=execute(build(compact_branches=True,**options),payload,raw,targets=targets,interrupts=True)
            self.assertEqual(old['output_cursors'],new['output_cursors'])
            for packed,expected in ((bytes.fromhex('e7f0e8'),b''),(bytes.fromhex('ef41f0e8'),b'A')):
                self.assertTrue(execute(build(compact_branches=True,**options),packed,expected)['exact'])


if __name__=='__main__':unittest.main()
