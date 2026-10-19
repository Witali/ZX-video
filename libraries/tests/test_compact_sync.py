"""Compact-sync checks cover full target words and saved live decoder BC."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lzsa/src'))
from lzsa.resumable import build
from lzsa import encode


class CompactSyncExportTests(unittest.TestCase):
    def test_size_and_default_profiles(self):
        for streaming in (False,True):
            for restored in (False,True):
                options=dict(streaming=streaming,restore_compare=restored)
                before=build(**options);after=build(compact_sync=True,**options)
                expected=(-1 if restored else -3) if streaming else (-3 if restored else -5)
                self.assertEqual(after[2]['code_bytes']-before[2]['code_bytes'],expected)
                self.assertEqual(build(compact_sync=False,**options),before)
                self.assertEqual(after[1]['end']-after[1]['state'],before[1]['end']-before[1]['state'])
                self.assertEqual(after[2]['compact_sync_returns_target_in_de'],not streaming)
                if restored:self.assertTrue(after[2]['restore_compare_superseded_by_compact_sync'])

    def test_cli_export_and_resident_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            argv=['lzsa','build','--compact-sync','--output',directory]
            code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'lzsa/src'))+');'
                  'sys.argv='+repr(argv)+';runpy.run_module("lzsa.__main__",run_name="__main__")')
            subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)
            self.assertTrue(json.loads((Path(directory)/'metadata.json').read_text())['compact_sync'])
            self.assertIn('BC is scratch',(Path(directory)/'decoder.asm').read_text())
            code=code.replace(repr(argv),repr(argv+['--profile','fast-block']))
            self.assertNotEqual(subprocess.run([sys.executable,'-I','-c',code],capture_output=True).returncode,0)


@unittest.skipUnless(importlib.util.find_spec('z80'),'install lzsa[native]')
class CompactSyncNativeTests(unittest.TestCase):
    def test_every_target_word_and_final_sentinel(self):
        from z80 import Z80Machine
        for streaming in (False,True):
            regions,z,meta=build(compact_sync=True,streaming=streaming)
            m=Z80Machine()
            for at,data in regions:m.set_memory_block(at,data)
            stop,stack=0x100,0x2000;m.set_breakpoint(stop)
            for end in (0xc000,0xffff):
                m.set_memory_block(z['block_end'],end.to_bytes(2,'little'))
                for target in range(65536):
                    m.set_memory_block(z['slice_target'],target.to_bytes(2,'little'))
                    m.set_memory_block(stack,stop.to_bytes(2,'little'))
                    m.sp,m.pc,m.af=stack,z['sync'],0xffff;m.ticks_to_stop=1000
                    while m.pc!=stop:self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                    expected=target if target!=end else 65535
                    self.assertEqual((m.memory[z['high_operand']]<<8)|m.memory[z['low_operand']],expected)
                    self.assertEqual(bool(m.f&0x40),target==end)
                    if not streaming:self.assertEqual(m.de,target)
                    self.assertEqual(1000-m.ticks_to_stop,(116 if target==end else 111)+(0 if streaming else 8))

    def test_pending_bc_survives_zero_and_repeated_demands(self):
        from measure_compact_sync import execute
        raw=b'ABC'*171;payload=encode(raw,[(3,len(raw)-3,3)])
        targets=[0,0,1,1,2,3,17,255,256,len(raw)]
        for restored in (False,True):
            before=execute(build(restore_compare=restored),payload,raw,targets=targets)
            after=execute(build(restore_compare=restored,compact_sync=True),payload,raw,targets=targets,interrupts=True)
            self.assertEqual(before['output_cursors'],after['output_cursors'])
            self.assertEqual(after['output_cursors'][:2],[0,0])
            for core in (0x8000,0x9103):
                self.assertTrue(execute(build(core=core,core_limit=core+0x400,compact_sync=True),bytes.fromhex('e7f0e8'),b'')['exact'])


if __name__=='__main__':unittest.main()
