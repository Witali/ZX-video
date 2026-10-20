"""Bind current public generators to saved complete native frontier proofs.

This does not relabel historical source authentication. It checks emitted
regions against each original replay, then authenticates the combined source,
legacy defaults, installed wheels and current regression logs separately.
"""
import argparse
from datetime import date
from functools import partial
import gzip
import json
from pathlib import Path
import re
from zipfile import ZipFile

from measure_long_copy import ROOT, sha
from test_libraries import profiles
from zx0.block import build as zb
from zx0.resumable import build as zc
from zx0.maximum import build as zm
from lzsa.block import build as lb
from lzsa.resumable import build as lc
from lzsa.wide_coroutine import build as lwc


EVIDENCE=ROOT/'libraries/evidence'
zb=partial(zb,core=0x8000,core_limit=0x8400)
zc=partial(zc,core=0x8000,core_limit=0x8400)
lb=partial(lb,core=0x8000,core_limit=0xb000)
lc=partial(lc,core=0x8000,core_limit=0x8400)


def load(name):
    raw=(EVIDENCE/name).read_bytes()
    data=json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
    assert data['complete'],name
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-tests',type=int,required=True)
    parser.add_argument('--extended',action='store_true',help='also bind completed guarded/maximum-coroutine profiles')
    args=parser.parse_args()
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    resources=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=resources['original_resources']+resources['added_pinned_resources']
    for resource in resources:
        p=ROOT/'libraries'/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(p.read_bytes())==resource['sha256']
    baseline=load('compact_frontier.json')['profiles']
    goal_rows={key:{row['case']:row for row in item['blocks']} for key,item in baseline.items()}
    results={};proofs={}

    def record(name,codec,kind,profile,proof_name,proof_key,caller,private,*,extra=0):
        proof=load(proof_name);item=proof['profiles'][proof_key]
        regions,labels,meta=profile
        frozen=item.get('candidate',item.get('layout',item))
        actual=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions]
        expected=[{k:region[k] for k in ('address','bytes','sha256')} for region in frozen['regions']]
        assert actual==expected,(name,'generated regions differ from native replay')
        if 'labels' in frozen:assert labels==frozen['labels'],name
        if 'patched_addresses' in frozen:assert meta.get('patched_addresses',[])==frozen['patched_addresses'],name
        summary=item['summary'];rows=item['blocks']
        real=[row for row in rows if row['case'].startswith('real-')]
        assert all(row['exact'] for row in rows),name
        cpu=sum(row['candidate_tstates'] for row in real)
        assert cpu==summary.get('real_candidate_tstates',summary.get('candidate_tstates')),name
        frozen_goal=goal_rows[codec+'-'+kind]
        for row in rows:
            old=frozen_goal.get(row['case'])
            if old:assert row['payload_sha256']==old['payload_sha256'] and row['raw_sha256']==old['raw_sha256'],name
        old_cpu=sum(frozen_goal[row['case']]['baseline_tstates'] for row in real)
        emitted=sum(len(blob) for _,blob in regions);service=emitted+caller+private+extra
        if 'service_memory_bytes' in meta:assert meta['service_memory_bytes']==service,name
        assert service<=10000,(name,service)
        stack_count=1+bool(private)
        directed=item.get('directed_blocks',[])
        assert all(row['exact'] and row['relocated_exact'] for row in directed),name
        goal_slower=[row['case'] for row in rows if row['case'] in frozen_goal and
                     row['candidate_tstates']>frozen_goal[row['case']]['baseline_tstates']]
        results[name]=dict(codec=codec,kind=kind,real_blocks=len(real),real_baseline_tstates=old_cpu,
            real_candidate_tstates=cpu,real_delta_tstates=cpu-old_cpu,gain_percent=100*(1-cpu/old_cpu),
            emitted_regions=actual,code_table_alignment_state_bytes=emitted,
            embedded_state_bytes_already_in_regions=meta.get('state_bytes',0),
            patched_operand_bytes_already_in_regions=len(set(meta.get('patched_addresses',[]))),
            caller_stack_bytes=caller,private_stack_bytes=private,extra_required_service_bytes=extra,
            requires_undocumented_ix_halves=meta.get('requires_undocumented_ix_halves',False),
            library_service_bytes=service,alignment_padding_bytes=meta.get('alignment_padding',0),
            service_with_sample_irq_bytes=service+13+6*stack_count,
            sample_irq_is_separate_application_contract=True,
            slower_complete_corpus_cases_vs_goal=goal_slower,
            additional_directed_proof=dict(cases=len(directed) or item.get('directed',{}).get('cases',0),
                slower_cases_vs_original_proof_baseline=[dict(case=row['case'],delta_tstates=row['delta_tstates'])
                    for row in directed if row['delta_tstates']>0],
                summary=item.get('directed',{}),
                exact=True,
                comparison_scope='additional directed rows retain their original native-proof baseline'),
            native_proof=dict(file=proof_name,profile=proof_key,summary=summary,
                              slice_comparison='original proof baseline; do not relabel as goal-baseline slices'),
            input_output_history_excluded=True,payload_delta_bytes=0,
            current_generated_regions_equal_complete_native_proof=True)
        proofs[proof_name]=sha((EVIDENCE/proof_name).read_bytes())

    record('zx0-small-fast','zx0','block',zb(branch_tuned=True),'ten_percent_tuned_branches.json','zx0-block',4,0)
    for kind,builder,private in (('block',zb,0),('coroutine',zc,12)):
        record('zx0-compact-'+kind,'zx0',kind,builder(branch_tuned=True,literal_prefix=True,inline_tail_refill=True),
               'compact_frontier.json','zx0-'+kind,4,private)
    record('zx0-compact-coroutine-smaller','zx0','coroutine',zc(branch_tuned=True,inline_tail_refill=True),
           'ten_percent_tail_refill.json','coroutine-branch-tuned',4,12)
    record('zx0-tuned-mega','zx0','block',zb('mega',fast_jumps=True,mega_tuned=True),
           'ten_percent_mega_offset.json','combined',4,0)
    for cap in (31,63,127,227,228):
        proof='ten_percent_maximum.json' if cap<=127 else 'ten_percent_maximum_word_prefix.json'
        record('zx0-maximum-'+str(cap),'zx0','block',zm(prefix_cap=cap),proof,str(cap),4,0)
    record('lzsa-small-fast','lzsa2','block',lb(fast_jumps=True,compact_branches=True),
           'compact_branches_native.json','block1',4,0)
    record('lzsa-compact-block','lzsa2','block',lb(fast_jumps=True,branch_tuned=True,nibble_prefill=True),
           'compact_frontier.json','lzsa2-block',4,0)
    for policy,key,proof in (('compact_branches','coroutine2','compact_branches_native.json'),
                             ('branch_tuned','tuned','compact_sync_native.json')):
        record('lzsa-'+policy+'-coroutine','lzsa2','coroutine',
               lc(fast_jumps=True,nibble_prefill=True,compact_sync=True,**{policy:True}),proof,key,4,14)
    for shared,key in ((False,'expanded'),(True,'shared-literal-bodies')):
        name='wide-shared' if shared else 'wide'
        record('lzsa-'+name+'-block','lzsa2','block',lb(name),
               'ten_percent_full_token_dispatch.json',key,6,0)
        name+='-coroutine'
        record('lzsa-'+name,'lzsa2','coroutine',lwc(shared_literals=shared),'wide_coroutine.json',name,4,16)

    if args.extended:
        from zx0.maximum_coroutine import build as maximum_coroutine
        for cap in (31,63,127):
            record('zx0-maximum-coroutine-'+str(cap),'zx0','coroutine',maximum_coroutine(prefix_cap=cap),
                   'maximum_coroutine/maximum-coroutine-native.json.gz',str(cap),4,12)
        high=load('maximum_coroutine/maximum-coroutine-high-word.json.gz')
        demands=load('maximum_coroutine/maximum-coroutine-demands.json.gz')
        assert all(high['profiles'][str(cap)]['summary']['cases']==56 for cap in (31,63,127))
        for cap in (31,63,127):
            item=high['profiles'][str(cap)]
            public=maximum_coroutine(core=0x0800,core_limit=0x2a00,prefix=0x2b00,prefix_limit=0x2c00,
                                     stack=0x2af0,output_base=0x3000,prefix_cap=cap)
            expected=[{k:region[k] for k in ('address','bytes','sha256')} for region in item['layout']['regions']]
            assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in public[0]]==expected
            assert all(row['exact'] and row['relocated_exact'] and row['same_fast_return_cursors']
                       and row['same_fast_eof_states'] for row in item['blocks'])
            results['zx0-maximum-coroutine-'+str(cap)]['high_word_generated_regions_equal_complete_native_proof']=True
        assert len(demands['inplace_minimum_start_cases'])==417
        for case in demands['inplace_minimum_start_cases']:
            assert len(case['profiles'])==3
            assert all(item['exact'] and item['every_fast_return_exact'] and item['unread_input_never_overwritten']
                       for item in case['profiles'].values())
        assert len(demands['forced_all_phase_comparisons'])==12 and demands['all_caller_ix_iy_alternate_pairs_preserved']
        for name in ('maximum_coroutine/maximum-coroutine-high-word.json.gz',
                     'maximum_coroutine/maximum-coroutine-demands.json.gz','maximum_coroutine_verification.json'):
            proofs[name]=sha((EVIDENCE/name).read_bytes())
        guarded=load('wide_guarded_native.json.gz')
        relocated=load('wide_guarded_relocation.json.gz')
        audited=load('wide_guarded_verification.json')
        for shared in (False,True):
            for direct in (False,True):
                key=('wide-shared-' if shared else 'wide-')+('direct' if direct else 'call')
                item=guarded['profiles'][key];audit=audited['profiles'][key]
                kwargs=dict(core=0xa000,core_limit=0xbc00,prefix=0x7000,prefix_limit=0x7400,
                    stack=0x7be0,shared_literals=shared,streaming=True,direct_header=direct)
                profile=lwc(**kwargs);regions,labels,meta=profile
                actual=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions]
                assert actual==item['regions'],key
                moved=lwc(**dict(kwargs,core=0x9e00))
                assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in moved[0]]==relocated['profiles'][key]['regions']
                assert relocated['profiles'][key]['live_code_shift_bytes']==-512
                assert meta['consumer_service_memory_bytes']==meta['service_memory_bytes']==audit['consumer_bytes']
                assert sum(len(blob) for _,blob in regions)+4+24==audit['consumer_bytes']
                full=audit['aligned_with_reference_workspace_and_probe_irq_example_bytes']
                assert sum(region['bytes'] for region in audit['reserved_region_inventory'])==full<=10000
                rows=item['reference_producer_blocks'];real=[row for row in rows if row['case'].startswith('real-')]
                for row in rows:
                    assert row['candidate']['exact']
                    for field in ('producer_tstates','input_pointer','payload_sha256','raw_sha256','sectors','carry_copy_bytes','input_waits'):
                        assert row['baseline'][field]==row['candidate'][field],(key,row['case'],field)
                before=sum(row['baseline']['decoder_tstates'] for row in real)
                after=sum(row['candidate']['decoder_tstates'] for row in real)
                assert (before,after)==(item['summary']['real_decoder_baseline_tstates'],item['summary']['real_decoder_candidate_tstates'])
                results['lzsa-'+key+'-guarded']=dict(codec='lzsa2',kind='guarded',real_blocks=len(real),
                    real_baseline_tstates=before,real_candidate_tstates=after,real_delta_tstates=after-before,
                    gain_percent=100*(1-after/before),emitted_regions=actual,
                    library_consumer_service_bytes=audit['consumer_bytes'],
                    consumer_scope=meta['service_memory_scope'],
                    required_reference_carry_bytes=audit['required_reference_carry_bytes'],
                    full_reference_service_with_workspace_and_irq_bytes=full,
                    full_reference_scope='aligned consumer plus retained supplier, carry, I/O code/state,1280-byte workspace and explicit IRQ/stacks',
                    memory_inventory=audit['reserved_region_inventory'],
                    proof_summary=item['summary'],main_and_directed_cases=len(item['native_blocks']),
                    native_placements_per_case=guarded['native_placements_per_case'] if 'native_placements_per_case' in guarded else len(guarded['placements']),
                    live_code_relocation_bytes=-512,current_generated_regions_equal_complete_native_proof=True,
                    sector_reads=item['reference_producer_summary']['sector_reads'],
                    physical_rom_disk_latency_measured=False,input_output_history_excluded=True)
        for name in ('wide_guarded_native.json.gz','wide_guarded_relocation.json.gz','wide_guarded_verification.json'):
            proofs[name]=sha((EVIDENCE/name).read_bytes())

    logs=[]
    for name,count in (('frontier-integration-library.log',args.library_tests),('frontier-integration-toolkit.log',67)):
        raw=(args.directory/name).read_bytes();text=raw.decode('utf-8',errors='replace')
        assert re.search(rf'Ran {count} tests in ',text) and text.rstrip().endswith('OK'),name
        logs.append((name,raw))
    wheels={}
    for package in ('zx0','lzsa'):
        wheel=next((args.directory/'frontier-integration-wheels').glob(f'zxvideo_{package}-*.whl'))
        smoke=json.loads((args.directory/f'frontier-integration-smoke-{package}'/'report.json').read_text())
        assert smoke['independent_wheel'] and len(smoke['combined_profiles'])==2
        if package=='lzsa':assert len(smoke['compact_policy_profiles'])==4
        else:assert len(smoke['maximum_profiles'])==5
        if args.extended:
            if package=='lzsa':assert len(smoke['wide_profiles'])==8
            else:assert len(smoke['maximum_coroutine_profiles'])==3
        exact=[]
        with ZipFile(wheel) as archive:
            for source in sorted((ROOT/'libraries'/package/'src'/package).rglob('*')):
                if source.is_file() and '__pycache__' not in source.parts:
                    member=source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                    assert archive.read(member)==source.read_bytes(),member
                    exact.append(dict(file=member,sha256=sha(source.read_bytes())))
        wheels[package]=dict(sha256=sha(wheel.read_bytes()),exact_members=exact,smoke=smoke)
    archived={}
    destination=EVIDENCE/('frontier_completed_profiles' if args.extended else 'frontier_integration')
    destination.mkdir(exist_ok=True)
    for name,raw in logs:
        p=destination/(name+'.gz');p.write_bytes(gzip.compress(raw,mtime=0));archived[p.name]=sha(p.read_bytes())
    sources=[p for package in ('zx0','lzsa') for p in (ROOT/'libraries'/package/'src'/package).rglob('*.py')]
    sources += [Path(__file__),ROOT/'libraries/tests/smoke_install.py',ROOT/'libraries/tests/native_block.py']
    report=dict(date=date.today().isoformat(),complete=True,release=False,goal_achieved=False,
        scope='Combined public profile byte equivalence to saved complete native replays, plus current regression/package checks',
        baseline_revision='f5a0362c',service_limit_bytes=10000,input_output_history_excluded=True,
        default_profiles_exact=31,upstream_resources_exact=len(resources),library_tests=args.library_tests,toolkit_tests=67,
        profiles=results,native_proof_sha256=proofs,wheels=wheels,archived_logs_sha256=archived,
        source_sha256_lf={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sources},
        limits=['A finite measured frontier; global optimality is not established.',
                'Original native source/wheel authentication remains historical; this report binds current emitted code to it.',
                'Coroutine and guarded features are separate comparisons; raw gains do not prove guarded performance.',
                'Application IRQ code/headroom is additional; cap228 with the 13-byte/6-stack probe exceeds10,000.',
                'Maximum ZX0 coroutine explicitly requires Spectrum-style undocumented CP IXH/IXL and live-IX preservation in IRQ.',
                'No physical disk/ROM/ULA timing or player/movie publication qualification.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,profiles=len(results),library_tests=args.library_tests,toolkit_tests=67)))


if __name__=='__main__':main()
