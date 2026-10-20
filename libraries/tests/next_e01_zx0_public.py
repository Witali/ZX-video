"""Authenticate six installed-source E01 builders without rerunning native CPU.

The complete native report is historical. Its executed sources retain their
own hashes; the pre-injection Maximum source is archived. Current public code
is bound by complete region bytes and every label against the independently
contracted binary oracle, including 256 alignments and four native origins.
"""
import argparse
from datetime import date
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
for package in ('zx0','lzsa'):
    sys.path.insert(0,str(ROOT/'libraries'/package/'src'))
sys.path.insert(0,str(ROOT/'libraries/tests'))
sys.path.insert(0,str(ROOT.parents[1]/'.tmp/library-test-deps'))
from zx0.maximum_branches import build
from zx0.maximum import build as maximum
import zx0.maximum as maximum_module
from zx0.export import export
from next_zx0_branches_profile import build as independent,oracle,POLICIES
from test_libraries import profiles

POLICY_MAP=dict(zip(('fast','real','corpus'),POLICIES))
PROOF=ROOT/'libraries/evidence/next_e01_zx0_branches.json.gz'
ARCHIVE=ROOT/'libraries/evidence/next_e01_zx0_public_maximum_before.py.gz'

def sha(blob):return hashlib.sha256(blob).hexdigest()
def region_rows(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]
def restore_assembly(path):
    regions=[]
    for line in path.read_text().splitlines():
        if line.startswith('org '):regions.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):regions[-1][1].extend(int(value[1:],16) for value in line[3:].split(','))
    return [(at,bytes(blob)) for at,blob in regions]

class PublicTests(unittest.TestCase):
    def test_all_legacy_defaults_exact(self):
        frozen=json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
        self.assertEqual(profiles(),frozen)
    def test_api_rejections_and_service_reservations(self):
        for kwargs in (dict(prefix_cap=31),dict(prefix_cap=63),dict(prefix_cap=227),dict(prefix_cap=True),
                dict(policy='unknown'),dict(policy=None),dict(policy=True),dict(_quota_hook=lambda *args:None),
                dict(core=-1),dict(core=65535),dict(core_limit=0x8001),dict(irq_code_bytes=-1),
                dict(irq_stack_bytes=True),dict(service_limit=10001),dict(service_limit=0)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):build(**kwargs)
        for cap in (127,228):
            for policy in POLICY_MAP:
                result=build(prefix_cap=cap,policy=policy)
                service=result[2]['service_memory_bytes']
                self.assertEqual(sum(result[2]['service_memory'].values()),service)
                self.assertEqual(result[2]['workspace_bytes'],service)
                self.assertEqual(build(prefix_cap=cap,policy=policy,service_limit=service)[0],result[0])
                self.assertEqual(build(prefix_cap=cap,policy=policy,irq_code_bytes=13,irq_stack_bytes=6)[2]['service_memory_bytes'],service+19)
                with self.assertRaises(ValueError):build(prefix_cap=cap,policy=policy,service_limit=service-1)
                with self.assertRaises(ValueError):build(prefix_cap=cap,policy=policy,irq_code_bytes=10000)
                with self.assertRaises(ValueError):build(prefix_cap=cap,policy=policy,core_limit=0x8000+service-5)
                self.assertFalse(result[2]['coroutine_supported'])
                self.assertNotIn('test_only',result[2])
    def test_api_exports_exact_regions_and_comments(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='e01-zx0-export-') as temporary:
            for cap in (127,228):
                for policy in POLICY_MAP:
                    result=build(prefix_cap=cap,policy=policy)
                    target=Path(temporary)/f'{cap}-{policy}'
                    export(target,*result)
                    self.assertEqual(restore_assembly(target/'decoder.asm'),result[0])
                    text=(target/'decoder.asm').read_text()
                    self.assertIn('Optional resident Maximum branch policy '+policy,text)
                    self.assertIn('7 T untaken / 12 T taken',text)
    def test_cli_six_public_calls_and_rejected_flags(self):
        environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT/'libraries/zx0/src'))
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='e01-zx0-cli-') as temporary:
            for cap in (127,228):
                for policy in POLICY_MAP:
                    target=Path(temporary)/f'{cap}-{policy}'
                    result=subprocess.run([sys.executable,'-B','-m','zx0','build','--variant','maximum-branches',
                        '--prefix-cap',str(cap),'--branch-policy',policy,'--output',str(target)],
                        env=environment,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(restore_assembly(target/'decoder.asm'),build(prefix_cap=cap,policy=policy)[0])
            invalid=[['--prefix-cap','63'],['--shared-prefixes'],['--fast-jumps'],['--branch-tuned'],
                     ['--literal-prefix'],['--inline-tail-refill'],['--mega-tuned'],['--prefix','0x7000'],
                     ['--prefix-limit','0x7400'],['--stack','0x6fe0'],['--output-base','0xc000']]
            for index,flags in enumerate(invalid):
                target=Path(temporary)/f'bad-{index}'
                result=subprocess.run([sys.executable,'-B','-m','zx0','build','--variant','maximum-branches',
                    '--output',str(target),*flags],env=environment,capture_output=True,text=True)
                self.assertEqual(result.returncode,2,(flags,result.stderr))
                self.assertFalse(target.exists())
            result=subprocess.run([sys.executable,'-B','-m','zx0','build','--variant','maximum',
                '--branch-policy','real','--output',str(Path(temporary)/'bad-policy')],
                env=environment,capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
    def test_package_has_no_harness_dependency(self):
        child='''import sys
sys.path.insert(0,sys.argv[1])
import zx0
before=set(sys.modules)
from zx0.maximum_branches import build
for cap in (127,228):
 for policy in ('fast','real','corpus'):build(prefix_cap=cap,policy=policy)
assert 'ast' not in set(sys.modules)-before
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') or name.startswith('next_') for name in sys.modules)
'''
        result=subprocess.run([sys.executable,'-I','-B','-c',child,str(ROOT/'libraries/zx0/src')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

def authenticate(output):
    blob=PROOF.read_bytes();native=json.loads(gzip.decompress(blob));assert native['complete']
    # These frozen test modules are the executed E01 oracle, not rewritten
    # lookalikes. Maximum's original source remains separately authenticated.
    for name in ('libraries/tests/next_zx0_branches_profile.py','libraries/tests/measure_next_zx0_branches.py',
                 'libraries/zx0/src/zx0/_shared_prefixes.py','libraries/zx0/src/zx0/_z80.py'):
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==native['source_sha256_lf'][name],name
    old=gzip.decompress(ARCHIVE.read_bytes())
    assert sha(old)==native['source_sha256_lf']['libraries/zx0/src/zx0/maximum.py']
    # Reconstruct historical labels from the executed source itself. Its
    # packaged assembler/shared transform are unchanged and authenticated
    # above. A private namespace preserves current package globals/defaults.
    historical=dict(vars(maximum_module))
    exec(compile(old,str(ARCHIVE),'exec'),historical)
    historical_maximum=historical['build']
    checks=[]
    for cap in (228,127):
        for policy,frozen_policy in POLICY_MAP.items():
            key=f'{cap}-{frozen_policy}';saved=native['profiles'][key]
            for origin,field in ((0x8000,'regions'),(0x9103,'relocated_regions'),
                                 (0x0800,'high_word_regions'),(0x0703,'high_word_relocated_regions')):
                current=build(core=origin,prefix_cap=cap,policy=policy)
                frozen=independent(core=origin,prefix_cap=cap,policy=frozen_policy)
                assert current[:2]==frozen[:2]
                assert current[:2]==oracle(historical_maximum(core=origin,prefix_cap=cap,shared_prefixes=True),
                    {row['baseline_offset'] for row in saved['changes']})
                assert region_rows(current)==saved[field]
                assert current[2]['conditional_branch_sites']==frozen[2]['next_branch_changes']
            offsets={row['baseline_offset'] for row in saved['changes']}
            alignments=[]
            for row in saved['alignments']:
                origin=row['origin'];current=build(core=origin,prefix_cap=cap,policy=policy)
                assert region_rows(current)==row['regions']
                assert current[2]['service_memory_bytes']==row['service_bytes']
                assert current[:2]==oracle(historical_maximum(core=origin,prefix_cap=cap,shared_prefixes=True),offsets)
                alignments.append(dict(origin=origin,regions=region_rows(current),
                    labels_sha256=sha(json.dumps(current[1],sort_keys=True).encode())))
            assert len(alignments)==256 and {row['origin']&255 for row in alignments}==set(range(256))
            current=build(prefix_cap=cap,policy=policy)
            meta=current[2];measured=meta['qualified_corpus']
            assert meta['service_memory_bytes']==saved['service_bytes']==measured['intrinsic_service_bytes']
            assert measured['real_tstates']==saved['real_candidate_tstates']
            assert measured['slower_cases']==len(saved['slower_cases'])
            checks.append(dict(module='zx0.maximum_branches',kwargs=dict(prefix_cap=cap,policy=policy),
                native_profile=key,regions=region_rows(current),labels=current[1],
                service_bytes=meta['service_memory_bytes'],service_memory=meta['service_memory'],
                real_cpu_tstates=measured['real_tstates'],slower_real_cases=measured['slower_real_cases'],
                slower_cases=measured['slower_cases'],maximum_case_delta_tstates=measured['maximum_case_delta_tstates'],
                native_origins_exact=4,independent_binary_and_every_label_exact=True,
                historical_source_binary_and_every_label_exact=True,
                alignments_exact=256,alignment_proof=alignments))
            print(cap,policy,'four native origins +256 alignments byte/label exact',flush=True)
    paths=list((ROOT/'libraries/zx0/src/zx0').glob('*.py'))+[Path(__file__),Path(__file__).with_name('test_next_e01_zx0_public.py')]
    result=dict(date=date.today().isoformat(),complete=True,release=False,
        current_public_calls=checks,proof_sha256=sha(blob),proof_path=str(PROOF.relative_to(ROOT)).replace('\\','/'),
        source_sha256_lf={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in paths},
        historical_maximum_source=dict(path=str(ARCHIVE.relative_to(ROOT)).replace('\\','/'),
            sha256=sha(ARCHIVE.read_bytes()),decoded_sha256=sha(old)),
        native_proof_reused_without_source_relabeling=True,
        public_module_has_no_test_ast_or_evidence_dependency=True,
        existing_package_stdlib_imports_may_include_ast=True,
        focused_tests=5,legacy_defaults_exact=31,public_calls=6,
        original_maximum_defaults_unchanged=True,
        exclusions=['no new native benchmark','no coroutine/partial-input wrapper qualification',
                    'no default promotion','no physical disk/ROM/ULA/movie qualification'])
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'libraries/evidence/next_e01_zx0_public.json')
    args=parser.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PublicTests))
    if not result.wasSuccessful():raise SystemExit(1)
    authenticate(args.output)

if __name__=='__main__':main()
