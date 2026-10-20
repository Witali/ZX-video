"""Wide coroutine quotas, service-memory reservations and CLI contracts."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lzsa/src'))
from lzsa.wide_coroutine import build


class WideCoroutineTests(unittest.TestCase):
    def test_memory_and_reservations(self):
        for shared,size in ((False,7185),(True,3633)):
            profile=build(shared_literals=shared)
            self.assertEqual(profile[2]['service_memory_bytes'],size)
            self.assertEqual(profile[2]['state_bytes'],15)
            self.assertEqual(profile[2]['private_stack_bytes'],16)
            self.assertEqual(profile[2]['caller_stack_bytes'],4)
            for low in range(256):
                self.assertLessEqual(build(core=0x8000+low,shared_literals=shared)[2]['service_memory_bytes'],10000)
        for kwargs in (dict(prefix_limit=0x7c10),dict(core_limit=0x8200),dict(stack=0x7c10),
                       dict(prefix=0x8000,prefix_limit=0x8100),dict(stack=1),dict(output_base=65536)):
            with self.assertRaises(ValueError):build(**kwargs)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            for profile in ('wide-coroutine','wide-shared-coroutine'):
                path=Path(directory)/profile
                argv=['lzsa','build','--profile',profile,'--core','0x8000','--core-limit','0xb000','--output',str(path)]
                code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'lzsa/src'))+');sys.argv='+repr(argv)+
                      ';runpy.run_module("lzsa.__main__",run_name="__main__")')
                subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)
                metadata=json.loads((path/'metadata.json').read_text())
                self.assertTrue(metadata['coroutine'])
                self.assertFalse(metadata['one_shot'])
                self.assertIn('private-stack and four caller-stack', (path/'decoder.asm').read_text())
                for unsupported in ('--compact-sync','--nibble-prefill','--compact-branches'):
                    rejected=code.replace(repr(argv),repr(argv+[unsupported]))
                    result=subprocess.run([sys.executable,'-I','-c',rejected],capture_output=True)
                    self.assertNotEqual(result.returncode,0)

    @unittest.skipUnless(importlib.util.find_spec('z80'),'install lzsa[native]')
    def test_guarded_memory_and_embedded_patcher(self):
        from z80 import Z80Machine
        from lzsa.native import put_word
        for shared in (False,True):
            for direct in (False,True):
                regions,z,metadata=build(shared_literals=shared,streaming=True,direct_header=direct)
                expected=(3792 if shared else 7344)-(8 if direct else 0)
                self.assertEqual(metadata['service_memory_bytes'],expected)
                self.assertEqual(metadata['consumer_service_memory_bytes'],expected)
                self.assertEqual(metadata['reference_inplace_input_supplier']['shared_sector_carry_bytes'],256)
                self.assertFalse(metadata['reference_inplace_input_supplier']['included_in_consumer_service'])
                self.assertEqual(metadata['service_memory']['internal_buffer_bytes'],0)
                self.assertEqual(metadata['private_stack_bytes'],24)
                self.assertEqual(metadata['state_bytes'],19)
                self.assertEqual(metadata['guard_update_code_bytes'],54 if direct else 57)
                self.assertLessEqual(expected+255+256,10000)
                for low in range(256):
                    moved=build(shared_literals=shared,streaming=True,direct_header=direct,core=0x8000+low)
                    self.assertEqual(moved[2]['service_memory_bytes'],expected+(-low)%256)
                machine=Z80Machine()
                for at,blob in regions:machine.set_memory_block(at,blob)
                machine.set_breakpoint(0x100)
                for complete in (0,1,0):
                    machine.af=complete<<8;machine.pc=z['update_guards'];machine.sp=0xbfee
                    put_word(machine,0xbfee,0x100);machine.ticks_to_stop=10000
                    while machine.pc!=0x100:machine.run()
                    for target,partial,full in (
                        ('token_high_target','token_guard','token_body'),
                        ('token_low_target','token_guard','token_body'),
                        ('token_end_target','token_guard','token_body'),
                        ('long8_target','guard_long8','long8_complete'),
                        ('long16_target','guard_long16','long16_complete')):
                        at=z[target]
                        self.assertEqual(int.from_bytes(machine.memory[at:at+2],'little'),z[full if complete else partial])
                with self.assertRaises(ValueError):
                    build(streaming=True,shared_literals=False,core=0xa003,core_limit=0xbc00)
        with self.assertRaises(ValueError):build(direct_header=True)

    @unittest.skipUnless(importlib.util.find_spec('z80'),'install lzsa[native]')
    def test_publication_cursor_and_actual_stacks(self):
        from lzsa import encode
        from lzsa.native import execute
        from lzsa.resumable import build as old
        raw=b'AB'*512
        payload=encode(raw,[(2,510,2),(514,510,2)])
        baseline=old(core=0x8000,core_limit=0x8400,fast_jumps=True)
        for shared in (False,True):
            candidate=build(shared_literals=shared)
            custom=build(shared_literals=shared,prefix=0x5000,prefix_limit=0x5400,
                         core=0x6000,core_limit=0x8000,stack=0x4ff0,output_base=0xa000)
            for demand in (1,2,255,256,257,None):
                before=execute(*baseline,payload,raw,source=0x2000,slice_bytes=demand)
                after=execute(*candidate,payload,raw,source=0x2000,slice_bytes=demand)
                moved=execute(*custom,payload,raw,source=0x2000,slice_bytes=demand,interrupts=True)
                self.assertEqual(before['publication_offsets'],after['publication_offsets'])
                self.assertEqual(after['publication_offsets'],moved['publication_offsets'])
                self.assertLessEqual(after['caller_stack_bytes'],4)
                self.assertLessEqual(after['private_stack_bytes'],16)
                self.assertLessEqual(moved['caller_stack_bytes'],10)
                self.assertLessEqual(moved['private_stack_bytes'],22)


if __name__=='__main__':unittest.main()
