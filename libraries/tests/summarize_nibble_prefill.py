"""Authenticate nibble prefill reports, prior guarded inputs and unchanged defaults."""
import argparse
import gzip
import json
from pathlib import Path
from measure_long_copy import ROOT,sha
from measure_fast_jumps import layout
from test_libraries import profiles
from lzsa.block import build as block
from lzsa.resumable import build as coroutine
from test_streaming_lzsa2 import independent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    evidence=ROOT/'libraries/evidence';archives=[]
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    previous=json.loads((evidence/'ten_percent_branch_verification.json').read_text())
    nativepath=evidence/'ten_percent_nibble_prefill.json'
    native=json.loads(nativepath.read_text())
    assert native['complete'] and len(native['profiles'])==8
    count=0
    for name,item in native['profiles'].items():
        builder=block if name.startswith('block') else coroutine
        assert layout(builder(core=0x8000,core_limit=0x8400,**item['options']))==item['baseline']
        assert layout(builder(core=0x8000,core_limit=0x8400,nibble_prefill=True,**item['options']))==item['candidate']
        assert len(item['blocks'])==97 and all(r['exact'] and r['relocated_exact'] for r in item['blocks'])
        count+=len(item['blocks'])
    for stage,pair in (('before',(62,23)),('after',(65,16))):
        assert len(native['primitive'][stage])==1024
        assert all((r['refill_tstates'],r['cached_tstates'])==pair for r in native['primitive'][stage])
    def archive(path):
        raw=path.read_bytes();packed=gzip.compress(raw,mtime=0)
        folder=evidence/'nibble_prefill';folder.mkdir(exist_ok=True)
        destination=folder/(path.name+'.gz');destination.write_bytes(packed)
        archives.append(dict(file=str(destination.relative_to(ROOT/'libraries')).replace('\\','/'),
                             sha256=sha(packed),decoded_sha256=sha(raw)))
    streaming={}
    for mode in ('call','direct'):
        oldpath=evidence/'tuned_branches'/f'tuned-branch-{mode}.json.gz'
        index=next(row for row in previous['archives'] if row['file'].endswith(oldpath.name))
        assert sha(oldpath.read_bytes())==index['sha256']
        old=json.loads(gzip.decompress(oldpath.read_bytes()))
        newpath=evidence/f'nibble_prefill_streaming_{mode}.json'
        new=json.loads(newpath.read_text())
        assert old['complete'] and new['complete'] and old['cases']==new['cases']==63
        assert old['stream_sha256']==new['stream_sha256'] and old['baseline']==new['baseline']
        assert old['layout']['prefix_end']==new['layout']['prefix_end']
        assert new['layout']['core_end']==old['layout']['core_end']+4
        slow=slices=irqs=real_slow=0;largest=0;real_delta=0
        for before,after,a,b in zip(old['blocks'],new['blocks'],old['independent'],new['independent']):
            assert a['case']==b['case'] and before['exact'] and after['exact']
            for field in ('payload_sha256','raw_sha256','producer_tstates','sectors','step_tstates',
                          'input_waits','carry_copy_bytes','first_output_loaded_bytes','input_pointer'):
                assert before[field]==after[field],(mode,a['case'],field)
            assert len(before['slice_tstates'])==len(after['slice_tstates'])
            delta=[y-x for x,y in zip(before['slice_tstates'],after['slice_tstates'])]
            assert sum(delta)==after['decoder_tstates']-before['decoder_tstates']
            slow+=sum(t>0 for t in delta);slices+=len(delta);largest=max(largest,max(delta))
            if a['case'].startswith('real-'):
                real_delta+=sum(delta);real_slow+=sum(delta)>0
            assert len(a['full_flags'])==len(b['full_flags'])==6
            for x,y in zip(a['full_flags'],b['full_flags']):
                assert x['exact'] and y['exact'] and x['input_waits']==y['input_waits'] and x['input_start']==y['input_start']
                irqs+=y['injected_interrupts']
        before,after=old['candidate'],new['candidate']
        assert before['producer_tstates']==after['producer_tstates']
        assert before['sector_reads']==after['sector_reads']==772 and after['sectors_exact_once']
        streaming[mode]=dict(cases=63,real_cases=21,placements_per_case=6,
            baseline_total_tstates=before['total_tstates'],candidate_total_tstates=after['total_tstates'],
            baseline_decoder_tstates=before['decoder_tstates'],candidate_decoder_tstates=after['decoder_tstates'],
            delta_tstates=after['total_tstates']-before['total_tstates'],real_delta_tstates=real_delta,
            slower_real_blocks=real_slow,producer_tstates=after['producer_tstates'],sector_reads=772,
            sectors_exact_once=True,input_waits_and_producer_exact=True,slices=slices,slower_slices=slow,
            largest_slice_delta=largest,injected_interrupts=irqs,core_code_delta_bytes=4,
            wrapper_state_extent_unchanged=True)
        archive(newpath)
    eof=[]
    for direct in (False,True):
        for payload,raw in ((bytes.fromhex('ef41f0e8'),b'A'),(bytes.fromhex('e7f0e8'),b'')):
            for offset in (0,1,252,253,254,255):
                result=independent(payload,raw,offset=offset,interrupts=offset==253,
                    direct_header=direct,fast_jumps=True,branch_tuned=True,nibble_prefill=True)
                eof.append(dict(payload_hex=payload.hex(),raw_hex=raw.hex(),offset=offset,direct_header=direct,**result))
    combined_path=args.directory/'nibble-stream-combinations.json'
    combined=json.loads(combined_path.read_text());assert combined['complete']
    combined_summary={}
    for name,profile in combined['profiles'].items():
        assert len(profile['cases'])==65
        entries=[r for c in profile['cases'] for r in c['placements']]
        assert len(entries)==390 and all(r['exact'] for r in entries)
        combined_summary[name]=dict(cases=65,placements_per_case=6,all_exact=True,
            delta_tstates=sum(r['delta_tstates'] for r in entries),
            slower_placements=sum(r['delta_tstates']>0 for r in entries),
            largest_delta_tstates=max(r['delta_tstates'] for r in entries),
            injected_interrupts=sum(r['injected_interrupts'] for r in entries))
    archive(combined_path)
    log=args.directory/'nibble-library-tests.log';text=log.read_text(encoding='utf-8')
    assert 'Ran 29 tests in ' in text and text.rstrip().endswith('OK');archive(log)
    frozen=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=frozen['original_resources']+frozen['added_pinned_resources']
    for item in resources:
        assert sha((ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']).read_bytes())==item['sha256']
    sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n'))
        for p in [*(ROOT/'libraries/lzsa/src/lzsa').glob('*.py'),ROOT/'toolkit/test_streaming_lzsa2.py',
                  ROOT/'libraries/tests/measure_nibble_prefill.py',ROOT/'libraries/tests/test_nibble_prefill.py',
                  ROOT/'libraries/tests/measure_nibble_stream_combinations.py',
                  ROOT/'libraries/tests/summarize_nibble_prefill.py']}
    report=dict(date='2026-10-19',baseline_revision='674a1fc8',goal_baseline='f5a0362c',complete=True,
        release=False,goal_achieved=False,scope=__doc__,native_profile_comparisons=count,
        native_report=dict(file='evidence/ten_percent_nibble_prefill.json',sha256=sha(nativepath.read_bytes())),
        primitive_byte_site_pairs_per_profile=1024,guarded_single_nibble_eof=eof,
        streaming=streaming,streaming_combined_options=combined_summary,archives=archives,source_sha256_lf=sources,default_profiles_exact=31,
        upstream_resources_exact=6,library_unit_tests=29,payload_delta_bytes=0,state_delta_bytes=0,
        stack_delta_bytes=0,default_instruction_delta_tstates=0,physical_disk_rom_ula_publication_measured=False,
        isolated_wheels_not_retested=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,goal_achieved=False,native_profile_comparisons=count,streaming=streaming)))


if __name__=='__main__':main()
