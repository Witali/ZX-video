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
    data=json.loads((EVIDENCE/name).read_text(encoding='utf-8'))
    assert data['complete'],name
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-tests',type=int,required=True)
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
        frozen=item.get('candidate',item)
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

    archived={};destination=EVIDENCE/'frontier_integration';destination.mkdir(exist_ok=True)
    for name,count in (('frontier-integration-library.log',args.library_tests),('frontier-integration-toolkit.log',67)):
        raw=(args.directory/name).read_bytes();text=raw.decode('utf-8',errors='replace')
        assert re.search(rf'Ran {count} tests in ',text) and text.rstrip().endswith('OK'),name
        p=destination/(name+'.gz');p.write_bytes(gzip.compress(raw,mtime=0));archived[p.name]=sha(p.read_bytes())
    wheels={}
    for package in ('zx0','lzsa'):
        wheel=next((args.directory/'frontier-integration-wheels').glob(f'zxvideo_{package}-*.whl'))
        smoke=json.loads((args.directory/f'frontier-integration-smoke-{package}'/'report.json').read_text())
        assert smoke['independent_wheel'] and len(smoke['combined_profiles'])==2
        if package=='lzsa':assert len(smoke['compact_policy_profiles'])==4
        else:assert len(smoke['maximum_profiles'])==5
        exact=[]
        with ZipFile(wheel) as archive:
            for source in sorted((ROOT/'libraries'/package/'src'/package).rglob('*')):
                if source.is_file() and '__pycache__' not in source.parts:
                    member=source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                    assert archive.read(member)==source.read_bytes(),member
                    exact.append(dict(file=member,sha256=sha(source.read_bytes())))
        wheels[package]=dict(sha256=sha(wheel.read_bytes()),exact_members=exact,smoke=smoke)
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
                'No physical disk/ROM/ULA timing or player/movie publication qualification.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,profiles=len(results),library_tests=args.library_tests,toolkit_tests=67)))


if __name__=='__main__':main()
