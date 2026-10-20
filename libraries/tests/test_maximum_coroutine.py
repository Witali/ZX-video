"""Spectrum IX-half contract, exact quotas/EOF and complete service reservation."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'zx0/src'))
from zx0.maximum_coroutine import build
from zx0.resumable import build as fast


class MaximumCoroutineTests(unittest.TestCase):
    def test_service_cap_and_reservations(self):
        for cap,size in ((31,4901),(63,6437),(127,7973)):
            profile=build(prefix_cap=cap)
            self.assertEqual(profile[2]['service_memory_bytes'],size)
            self.assertEqual(sum(profile[2]['service_memory'].values()),size)
            self.assertEqual(profile[2]['code_bytes']+4+12,size)
            self.assertEqual(profile[2]['caller_stack_bytes'],4)
            self.assertEqual(build(prefix_cap=cap,irq_code_bytes=13,irq_stack_bytes=6)[2]['service_memory_bytes'],size+25)
            self.assertEqual(build(prefix_cap=cap,service_limit=size)[2]['service_memory_bytes'],size)
            with self.assertRaises(ValueError):build(prefix_cap=cap,service_limit=size-1)
        for options in (dict(prefix_cap=228),dict(prefix_cap=True),dict(service_limit=10001),dict(irq_stack_bytes=-1),
                        dict(core_limit=0x8100),dict(prefix=0x8000),dict(stack=0x7004),dict(stack=4),dict(prefix_limit=0x7004)):
            with self.assertRaises(ValueError):build(**options)
        for options in (dict(streaming=True),dict(branch_tuned=True),dict(inline_tail_refill=True),dict(quota_mode='patched')):
            with self.assertRaises(TypeError):build(**options)

    def test_ix_half_cp_full_flags_registers_and_eight_tstates(self):
        from z80 import Z80Machine
        m=Z80Machine();stop,entry,sp=0x200,0x100,0x3000;m.set_breakpoint(stop)
        for opcode in (0xbc,0xbd):
            for value in (0,1,127,128,255):
                for accumulator in range(256):
                    results=[]
                    for code in (bytes((0xfe,value,0xc9)),bytes((0xdd,opcode,0xc9))):
                        m.set_memory_block(entry,code);m.set_memory_block(sp,stop.to_bytes(2,'little'))
                        m.pc,m.sp,m.af,m.ix=entry,sp,(accumulator<<8)|0xa5,(value<<8|0x5a) if opcode==0xbc else (0x5a00|value)
                        original_ix=m.ix;m.ticks_to_stop=100
                        while m.pc!=stop:self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                        self.assertEqual(m.ix,original_ix);self.assertEqual(m.a,accumulator)
                        results.append((m.f,100-m.ticks_to_stop))
                    self.assertEqual(results[0][0],results[1][0]);self.assertEqual(results[0][1],17);self.assertEqual(results[1][1],18)

    def test_zero_repeated_final_quotas_and_forced_ix_clobber_irq(self):
        from maximum_coroutine_native import execute
        from zx0.tokens import Token,encode
        for raw,tokens in ((b'A',[Token(0,1)]),(b'ABC'*513,[Token(0,3),Token(3,1536,3)])):
            payload=encode(raw,tokens)
            targets=[0,0,1,1]+([2,3,17,255,256] if len(raw)>1 else [])+[len(raw),len(raw)]
            before=execute(fast(core=0x8000,core_limit=0x8400),payload,raw,targets=targets)
            for cap in (31,63,127):
                after=execute(build(prefix_cap=cap),payload,raw,targets=targets,interrupts=True,force_irq=True,irq_clobber_ix=True)
                self.assertEqual(after['output_cursors'],before['output_cursors']);self.assertEqual(after['finished_states'],before['finished_states'])
                self.assertEqual(after['output_cursors'][:2],[0,0]);self.assertGreater(after['injected_interrupts'],len(targets))
                self.assertLessEqual(after['caller_stack_bytes'],12);self.assertLessEqual(after['private_stack_bytes'],20)

    def test_cli_commented_exact_export_and_incompatible_flags(self):
        def cli(args):
            code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');sys.argv='+repr(['zx0','build',*args])+';runpy.run_module("zx0.__main__",run_name="__main__")')
            return subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True)
        with tempfile.TemporaryDirectory() as directory:
            args=['--variant','maximum-coroutine','--output',directory]
            result=cli(args);self.assertEqual(result.returncode,0,result.stderr)
            metadata=json.loads((Path(directory)/'metadata.json').read_text());self.assertEqual(metadata['service_memory_bytes'],7973)
            text=(Path(directory)/'decoder.asm').read_text();self.assertIn('REQUIRES undocumented CP IXH / CP IXL, 8 T',text)
            rebuilt=[]
            for line in text.splitlines():
                if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
                elif line.startswith('db '):rebuilt[-1][1].extend(int(value[1:],16) for value in line[3:].split(','))
            self.assertEqual([(at,bytes(blob)) for at,blob in rebuilt],build()[0])
            for flags in (['--branch-tuned'],['--inline-tail-refill'],['--mega-tuned'],['--fast-jumps'],['--prefix-cap','228'],['--service-limit','10001']):
                self.assertNotEqual(cli(args+flags).returncode,0,flags)


if __name__=='__main__':unittest.main()
