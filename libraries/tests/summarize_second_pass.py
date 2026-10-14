"""Authenticate all second-pass reports and final defaults/resources/profiles.

Observed unit counts are supplied from successful runs; this summary rechecks
emitted byte compatibility and saved evidence, not movie/physical timing.
"""
import argparse
import json
from pathlib import Path
from test_libraries import ROOT,profiles
from lzsa._z80 import sha
from lzsa.block import build as lblock
from zx0.block import build as zblock
from lzsa.resumable import build as lzsa_build
from measure_repeat_match import candidate as repeat_candidate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-tests',type=int,required=True)
    parser.add_argument('--toolkit-tests',type=int,required=True)
    parser.add_argument('--zx0-smoke',type=Path,required=True)
    parser.add_argument('--lzsa-smoke',type=Path,required=True)
    args=parser.parse_args();defaults=profiles()
    assert defaults==json.loads((ROOT/'tests/decoder_baseline.json').read_text())['profiles']
    reports=[];saved={}
    for n in range(10,30):
        name=f'evidence/trick_{n:02}.json';path=ROOT/name;item=json.loads(path.read_text())
        assert item['complete'] and item.get('release') is False
        saved[n]=item;reports.append(dict(item=n,file=name,sha256=sha(path.read_bytes()),complete=True))
    original=[]
    for resource in json.loads((ROOT/'verification.json').read_text())['upstream_resources']:
        path=ROOT/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(path.read_bytes())==resource['sha256'];original.append(dict(resource,exact=True))
    frozen=json.loads((ROOT/'tests/fixtures/item22_loop_profiles.json').read_text())['baseline']
    current=lzsa_build(long_copy=True,core_limit=0x9000)
    assert [[at,data.hex()] for at,data in current[0]]==frozen['regions'] and current[1]==frozen['labels']
    repeated=repeat_candidate();assert [[at,data.hex()] for at,data in repeated[0]]==saved[24]['candidate']['regions']
    resident=[]
    for package,variants,builder in (('zx0',('standard','turbo','fast','mega'),zblock),('lzsa',('fast','small'),lblock)):
        for variant in variants:
            regions,labels,metadata=builder(variant)
            count=sum(len(data) for _,data in regions)
            if package=='zx0':assert sha(regions[0][1])==saved[23]['profiles'][variant]['code_sha256']
            elif variant=='fast':assert count==saved[28]['codecs']['lzsa2']['candidate_bytes']
            else:assert count==saved[29]['candidate_bytes']
            resident.append(dict(package=package,variant=variant,code_bytes=count,
                standalone_raw_code_sectors=(count+255)//256,entry=metadata['entry'],
                regions=[dict(address=at,bytes=len(data),sha256=sha(data)) for at,data in regions]))
    smoke=[json.loads(path.read_text()) for path in (args.zx0_smoke,args.lzsa_smoke)]
    assert all(r['independent_wheel'] and r['cli_export'] and r['resources'] and
               all(v['exact_export'] for v in r['resident_profiles']) for r in smoke)
    added=[dict(package=p,file=f,sha256=sha((ROOT/p/'src'/p/'asm'/f).read_bytes()),source_commit=commit)
           for p,f,commit in (('zx0','dzx0_mega.asm','ecde3a2ae05061fe06469ed46df81a33b7de7d86'),
                              ('lzsa','unlzsa2_small.asm','15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5'))]
    sources={str(path.relative_to(ROOT)):sha(path.read_bytes().replace(b'\r\n',b'\n'))
             for p in ('lzsa','zx0') for path in sorted((ROOT/p/'src'/p).glob('*.py'))}
    report=dict(date='2026-10-14',branch='codex/z80-codec-tricks',initial_second_pass_revision='3f34a4a4',
        complete=True,release=False,scope=__doc__,completed_items=list(range(10,30)),
        optional_measured_groups=[10,16,20,23,28,29],default_profiles=len(defaults),
        defaults_bytes_addresses_labels_exact=True,default_instruction_delta_tstates=0,
        original_resources=original,added_pinned_resources=added,resident_profiles=resident,
        evidence=reports,source_sha256_lf=sources,
        observed_units=dict(libraries=args.library_tests,toolkit=args.toolkit_tests,
                            total=args.library_tests+args.toolkit_tests),isolated_wheels=smoke,
        guarded_evidence={str(n):saved[n]['streaming'] for n in (16,20)},
        resident_native=dict(item23_cases=saved[23]['cases'],item28={c:v['summary'] for c,v in saved[28]['codecs'].items()},
                             item29=saved[29]['summary']),
        rejected_real_regressions={str(n):saved[n]['summary']['real_delta_tstates'] for n in (22,24)},
        runtime_payload_delta_bytes=0,shared_input_producer_default_variants_exact=2,
        physical_disk_rom_ula_publication_measured=False,new_player_release=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,items=20,defaults=len(defaults),unit_tests=report['observed_units']['total'],resident_profiles=6)))

if __name__=='__main__':main()
