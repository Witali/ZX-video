"""Public maximum frontier equals the independent native prototype exactly."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'zx0/src'))
from zx0.maximum import build
from mega_prefix_profile import build as reference


class MaximumTests(unittest.TestCase):
    def test_independent_layout_and_complete_service_bound(self):
        for cap,code in ((31,4450),(63,5986),(127,7522),(227,9962),(228,9986)):
            irq_code,irq_stack=(3,2) if cap==228 else (13,6)
            for origin in (0x8000,0x9103):
                profile=build(core=origin,prefix_cap=cap,irq_code_bytes=irq_code,irq_stack_bytes=irq_stack)
                self.assertEqual(profile[:2],reference(origin=origin,prefix_cap=cap)[:2])
                meta=profile[2]
                self.assertEqual(meta['code_bytes'],code)
                self.assertEqual(meta['workspace_bytes'],code+4)
                self.assertEqual(sum(meta['service_memory'].values()),code+4+irq_code+irq_stack)
                self.assertEqual(meta['service_memory_bytes'],code+4+irq_code+irq_stack)
                self.assertFalse(meta['coroutine_supported'])
                self.assertTrue(meta['input_output_history_counted_separately'])
                self.assertFalse(meta['globally_optimal'])
            self.assertEqual(build(prefix_cap=cap,service_limit=code+4)[2]['service_memory_bytes'],code+4)
            with self.assertRaises(ValueError):build(prefix_cap=cap,service_limit=code+3)
        # The cap includes declared caller IRQ storage, not just decoder code.
        self.assertEqual(build(prefix_cap=127,irq_code_bytes=2474)[2]['service_memory_bytes'],10000)
        self.assertEqual(build(prefix_cap=227,irq_code_bytes=13,irq_stack_bytes=6)[2]['service_memory_bytes'],9985)
        self.assertEqual(build(irq_code_bytes=3,irq_stack_bytes=2)[2]['service_memory_bytes'],9995)
        self.assertEqual(build(irq_code_bytes=10)[2]['service_memory_bytes'],10000)
        with self.assertRaises(ValueError):build(irq_code_bytes=11)
        with self.assertRaises(ValueError):build(irq_code_bytes=13,irq_stack_bytes=6)
        for options in (dict(irq_code_bytes=2475),dict(service_limit=10001),dict(service_limit=0),
                        dict(irq_stack_bytes=-1),dict(irq_code_bytes=1.5),dict(prefix_cap=15),
                        dict(prefix_cap=True),dict(core=-1),dict(core=0xffff),
                        dict(core_limit=0x8000+7521),dict(core_limit=0x10001)):
            with self.assertRaises(ValueError):build(**options)
        with self.assertRaises(TypeError):build(branch_tuned=True)

    def test_native_dirty_offset_and_short_gamma(self):
        from native_block import execute
        from zx0.tokens import Token,encode
        for cap in (31,63,127,227,228):
            regions,labels,meta=build(prefix_cap=cap)
            address,blob=regions[0];dirty=bytearray(blob)
            offset=labels['dzx0m_last_offset+1']-address
            dirty[offset:offset+2]=b'\x23\x81'
            profile=([(address,bytes(dirty))],labels,meta)
            for length in (1,2,3,4,7,8,15,16,31,32,63,64,127,128,255,256,257):
                raw=b'A'*(length+1)
                payload=encode(raw,[Token(0,1),Token(1,length,1)])
                result=execute(profile,payload,raw,interrupts=True)
                self.assertTrue(result['exact'])
                self.assertLessEqual(result['stack_bytes'],10)
        profile=build(core=0x0800)
        raw=b'AB'*256;payload=encode(raw,[Token(0,2),Token(2,510,2)])
        self.assertTrue(execute(profile,payload,raw,source=0x0400,output=0x3000,
                                caller_stack=0x2ff0,interrupts=True)['exact'])
        for options in (dict(caller_stack=0x3004),dict(output=0x0900),dict(caller_stack=0x10001)):
            placement=dict(source=0x0400,output=0x3000,caller_stack=0x2ff0)
            placement.update(options)
            with self.assertRaises(AssertionError):execute(profile,payload,raw,**placement)

    def test_cli_exact_commented_export_and_rejected_flags(self):
        def run(arguments):
            code=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');'
                  'sys.argv='+repr(['zx0','build']+arguments)+';'
                  'runpy.run_module("zx0.__main__",run_name="__main__")')
            return subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True)
        with tempfile.TemporaryDirectory() as directory:
            for cap in (31,63,127,227,228):
                destination=Path(directory)/str(cap)
                irq_code,irq_stack=(3,2) if cap==228 else (13,6)
                args=['--variant','maximum','--prefix-cap',str(cap),
                      '--irq-code-bytes',str(irq_code),'--irq-stack-bytes',str(irq_stack),'--output',str(destination)]
                result=run(args);self.assertEqual(result.returncode,0,result.stderr)
                meta=json.loads((destination/'metadata.json').read_text())
                profile=build(prefix_cap=cap,irq_code_bytes=irq_code,irq_stack_bytes=irq_stack)
                self.assertEqual(meta['service_memory_bytes'],profile[2]['service_memory_bytes'])
                lines=(destination/'decoder.asm').read_text()
                self.assertIn('Gamma-proven',lines)
                self.assertIn('eighth data bit',lines)
                self.assertIn('Input/output/history are separate',lines)
                rebuilt=[]
                for line in lines.splitlines():
                    if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
                    elif line.startswith('db '):rebuilt[-1][1].extend(int(value[1:],16) for value in line[3:].split(','))
                self.assertEqual([(at,bytes(blob)) for at,blob in rebuilt],profile[0])
            for flags in (['--fast-jumps'],['--branch-tuned'],['--inline-tail-refill'],['--mega-tuned'],
                          ['--prefix','0x7000'],['--prefix-limit','0x7400'],['--stack','0xbff0'],
                          ['--output-base','0xc000'],['--irq-stack-bytes','-1'],['--service-limit','10001'],
                          ['--core-limit','0x8100']):
                self.assertEqual(run(['--variant','maximum','--output',directory]+flags).returncode,2,flags)
            for flags in (['--prefix-cap','31'],['--irq-code-bytes','13'],['--irq-stack-bytes','6'],
                          ['--service-limit','10000']):
                self.assertEqual(run(['--variant','mega','--output',directory]+flags).returncode,2,flags)


if __name__=='__main__':unittest.main()
