"""Integration/placement/export contracts of the measured shared Maximum."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'zx0/src'))
from zx0.maximum import build
from shared_zero_prefix_profile import build as independent


class SharedMaximumTests(unittest.TestCase):
    def test_public_profile_and_service_limit(self):
        for cap,size in ((31,2810),(63,3578),(127,5114),(227,7554),(228,7578)):
            for origin in (0x0800,0x8000,0x9103):
                current=build(core=origin,prefix_cap=cap,shared_prefixes=True)
                self.assertEqual(current[:2],independent(origin=origin,prefix_cap=cap)[:2])
                self.assertEqual(current[2]['service_memory_bytes'],size)
                self.assertEqual(sum(current[2]['service_memory'].values()),size)
                self.assertEqual(build(core=origin,prefix_cap=cap,shared_prefixes=True,
                    irq_code_bytes=13,irq_stack_bytes=6)[2]['service_memory_bytes'],size+19)
                self.assertEqual(build(core=origin,prefix_cap=cap,shared_prefixes=True,
                    service_limit=size)[2]['service_memory_bytes'],size)
                with self.assertRaises(ValueError):
                    build(prefix_cap=cap,shared_prefixes=True,service_limit=size-1)
                with self.assertRaises(ValueError):
                    build(core=origin,core_limit=origin+size-5,prefix_cap=cap,shared_prefixes=True)
        for options in (dict(shared_prefixes=1),dict(shared_prefixes='yes'),
                        dict(shared_prefixes=True,_quota_hook=lambda a,site:None)):
            with self.assertRaises(ValueError):build(**options)

    def test_cli_standalone_export_and_coroutine_rejection(self):
        def cli(arguments):
            source=('import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'zx0/src'))+');'
                'sys.argv='+repr(['zx0','build']+arguments)+';runpy.run_module("zx0.__main__",run_name="__main__")')
            return subprocess.run([sys.executable,'-I','-c',source],capture_output=True,text=True)
        with tempfile.TemporaryDirectory() as temporary:
            for cap in (31,63,127,227,228):
                destination=Path(temporary)/str(cap)
                result=cli(['--variant','maximum','--shared-prefixes','--prefix-cap',str(cap),
                    '--core','0x9103','--output',str(destination)])
                self.assertEqual(result.returncode,0,result.stderr)
                metadata=json.loads((destination/'metadata.json').read_text())
                self.assertTrue(metadata['shared_prefixes'])
                text=(destination/'decoder.asm').read_text()
                self.assertIn('cloned LDIR/command continuations',text)
                restored=[]
                for line in text.splitlines():
                    if line.startswith('org '):restored.append((int(line[5:],16),bytearray()))
                    elif line.startswith('db '):restored[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
                self.assertEqual([(at,bytes(blob)) for at,blob in restored],
                    build(core=0x9103,prefix_cap=cap,shared_prefixes=True)[0])
            for variant in ('fast','maximum-coroutine'):
                self.assertEqual(cli(['--variant',variant,'--shared-prefixes','--output',temporary]).returncode,2)


if __name__=='__main__':unittest.main()
