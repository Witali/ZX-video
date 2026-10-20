"""E00: authenticate and profile current raw Hybrid decoders, without edits.

Observers attach only to real instruction boundaries after the target table.
Every watched complete-case CPU count and both region placements must match
the frozen 9c28b01f proof. IRQ/relocation correctness is reused from that exact
proof; this run adds branch/helper/cache observers, not another decoder trial.
"""
import argparse
from collections import Counter,defaultdict
from datetime import date
import gzip
import json
from pathlib import Path
import subprocess

from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from profile_branch_mix import instructions,condition
from native_block import execute
from lzsa.hybrid import build

CONDITIONS=('NZ','Z','NC','C','PO','PE','P','M')


def region_manifest(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


def serial_counter(counter):
    return {str(k):v for k,v in sorted(counter.items(),key=lambda pair:str(pair[0]))}


class Observer:
    def __init__(self,profile):
        self.profile=profile
        self.labels=profile[1]
        self.metadata=profile[2]
        origin,blob=profile[0][0]
        self.origin=origin;self.blob=blob
        start=self.labels['start']-origin
        self.code=dict(instructions(blob[start:],origin+start))
        self.token_pcs={self.labels['token_'+str(value)]:value for value in range(256)}
        self.contexts={};self.token_context={}
        for body in self.metadata['body_layout']:
            base=body['base_token']
            for index,group in enumerate(body['groups']):
                name=f'body_{base}_{index}'
                at=self.labels[name]
                self.contexts[name]=dict(name=name,address=at,end=at+group['body_bytes'],
                    base_token=base,literals=group['literals'],fallthrough=group['fallthrough'],
                    code_bytes=group['body_bytes'])
                for literal in group['literals']:self.token_context[base|(literal<<3)]=name
        self.body_pcs={item['address']:name for name,item in self.contexts.items()}
        self.branches={};self.flows={};self.nibbles={}
        for at,code in self.code.items():
            op=code[0]
            if op&0xc7==0xc2:
                index=(op>>3)&7;kind='jp';target=int.from_bytes(code[1:],'little')
            elif op in (0x20,0x28,0x30,0x38):
                index=(op-0x20)//8;kind='jr'
                target=at+2+int.from_bytes(code[1:],'little',signed=True)
            else:index=None
            if index is not None:
                span=target-(at+2)
                shrink_span=span-(1 if kind=='jp' and target>at else 0)
                self.branches[at]=dict(address=at,opcode_hex=code.hex(),kind=kind,
                    condition_index=index,condition=CONDITIONS[index],target=target,
                    target_labels=[key for key,value in self.labels.items() if value==target],
                    current_relative_span=span,single_jp_shrink_relative_span=shrink_span,
                    single_jp_shrink_fits=-128<=shrink_span<=127,
                    context=self.context_at(at))
                if (op==0x30 and self.code.get(at-2)==b'\x37' and self.code.get(at-1)==b'\x08'
                        and self.code.get(target)==bytes.fromhex('f6f0')):
                    self.nibbles[at]=dict(address=at,start=at-2,merge=target,
                        context=self.context_at(at),target_labels=self.branches[at]['target_labels'])
            if op in (0xc3,0xcd,0xc9,0xe9):
                target=int.from_bytes(code[1:],'little') if op in (0xc3,0xcd) else None
                self.flows[at]=dict(address=at,kind={0xc3:'jp',0xcd:'call',0xc9:'ret',0xe9:'jp_hl'}[op],
                    target=target,context=self.context_at(at),
                    target_labels=[key for key,value in self.labels.items() if value==target] if target else [])
        self.nibble_starts={v['start']:k for k,v in self.nibbles.items()}
        self.nibble_merges={v['merge']:k for k,v in self.nibbles.items()}
        self.helper_calls={at for at,flow in self.flows.items()
                           if flow['kind']=='call' and flow['target']==self.labels['LongLiterals']}
        first_handler=min(self.token_pcs)
        self.helper_rets={at for at,flow in self.flows.items()
                          if flow['kind']=='ret' and self.labels['LongLiterals']<=at<first_handler}
        self.helper_paths={self.labels['LongLiterals']:'nibble',self.labels['ManyLiterals']:'byte',
                           self.labels['WordLiterals']:'word'}
        named=('start','done','ReadToken','CopyMatchA','MatchUseC','LongerMatch','LongLiterals','ManyLiterals','WordLiterals')
        self.named_pcs=defaultdict(list)
        for name in named:self.named_pcs[self.labels[name]].append(name)
        watched=(set(self.branches)|set(self.flows)|set(self.token_pcs)|set(self.body_pcs)|
                 set(self.nibble_starts)|set(self.nibble_merges)|set(self.named_pcs))
        self.watch={at:self.callback(at) for at in watched}

    def context_at(self,at):
        for name,item in self.contexts.items():
            if item['address']<=at<item['end']:return name
        for name,next_name in (('LongerMatch','ReadToken'),('LongLiterals','ManyLiterals'),
                               ('ManyLiterals','WordLiterals')):
            if self.labels[name]<=at<self.labels[next_name]:return name
        if self.labels['WordLiterals']<=at<min(self.token_pcs):return 'WordLiterals'
        return 'shared-setup-exit'

    def callback(self,at):
        return lambda machine:self.observe(at,machine)

    def reset(self):
        self.branches_hit=Counter();self.flows_hit=Counter();self.tokens=Counter();self.bodies=Counter()
        self.named=Counter();self.cache=Counter();self.cache_values=Counter();self.cache_contexts=Counter()
        self.helper=Counter();self.helper_literals=Counter();self.helper_cpu=Counter();self.helper_length=Counter()
        self.pending_nibbles={};self.active_helper=None;self.current_token=None
        self.start_tick=None;self.first_token_tick=None;self.done_tick=None

    def observe(self,at,m):
        if at in self.token_pcs:
            self.current_token=self.token_pcs[at];self.tokens[self.current_token]+=1
        if at in self.body_pcs:
            name=self.body_pcs[at];context=self.contexts[name]
            assert self.current_token is not None
            assert self.current_token&0xe7==context['base_token']
            assert (self.current_token>>3)&3 in context['literals']
            self.bodies[name]+=1
        for name in self.named_pcs.get(at,()):
            self.named[name]+=1
            if name=='start':self.start_tick=m.ticks_to_stop
            elif name=='ReadToken' and self.first_token_tick is None:self.first_token_tick=m.ticks_to_stop
            elif name=='done':self.done_tick=m.ticks_to_stop
        if at in self.helper_calls:
            assert self.active_helper is None and (self.current_token>>3)&3==3
            self.active_helper=dict(call=at,token=self.current_token,
                context=self.token_context[self.current_token],tick=m.ticks_to_stop,
                de=m.de,sp=m.sp,path=None)
        if at in self.helper_paths:
            assert self.active_helper is not None
            self.active_helper['path']=self.helper_paths[at]
            if at==self.labels['LongLiterals']:
                assert m.sp==self.active_helper['sp']-2
        if at in self.nibble_starts:
            branch=self.nibble_starts[at]
            assert branch not in self.pending_nibbles
            self.pending_nibbles[branch]=dict(tick=m.ticks_to_stop,hl=m.hl,phase=None,
                context=self.token_context[self.current_token])
        if at in self.branches:
            branch=self.branches[at]
            taken=condition(m.f,branch['condition_index'])
            self.branches_hit[at,int(taken)]+=1
            if at in self.nibbles:
                self.pending_nibbles[at]['phase']='cached' if taken else 'refill'
        if at in self.nibble_merges:
            branch=self.nibble_merges[at]
            pending=self.pending_nibbles.pop(branch)
            phase=pending['phase'];assert phase in ('cached','refill')
            ticks=pending['tick']-m.ticks_to_stop+7
            assert ticks==(27 if phase=='cached' else 66),(branch,phase,ticks)
            assert (m.hl-pending['hl'])&65535==(0 if phase=='cached' else 1)
            self.cache[branch,phase]+=1
            self.cache_values[branch,phase,m.a&15]+=1
            self.cache_contexts[branch,phase,pending['context']]+=1
        if at in self.flows:self.flows_hit[at]+=1
        if at in self.helper_rets:
            pending=self.active_helper;assert pending is not None and pending['path'] is not None
            assert m.sp==pending['sp']-2
            returned=m.memory[m.sp]|(m.memory[m.sp+1]<<8)
            assert returned==pending['call']+3
            literal_bytes=(m.de-pending['de'])&65535
            assert literal_bytes>0
            key=(pending['call'],pending['context'],pending['path'])
            self.helper[key]+=1;self.helper_literals[key]+=literal_bytes
            self.helper_cpu[key]+=pending['tick']-m.ticks_to_stop+10
            self.helper_length[pending['path'],literal_bytes]+=1
            self.active_helper=None

    def finish(self,result):
        assert self.active_helper is None and not self.pending_nibbles
        assert self.named['start']==self.named['done']==1
        assert self.named['ReadToken']==sum(self.tokens.values())
        assert self.start_tick-self.first_token_tick==44
        assert self.start_tick-self.done_tick+28==result['tstates']
        assert sum(self.helper.values())==sum(self.flows_hit[at] for at in self.helper_calls)
        return dict(branches=serial_counter(self.branches_hit),flow_hits=serial_counter(self.flows_hit),
            token_counts=serial_counter(self.tokens),body_counts=serial_counter(self.bodies),
            setup_exit_hits=serial_counter(self.named),nibble_phases=serial_counter(self.cache),
            nibble_values=serial_counter(self.cache_values),nibble_contexts=serial_counter(self.cache_contexts),
            ll3_context_paths=serial_counter(self.helper),ll3_context_literal_bytes=serial_counter(self.helper_literals),
            ll3_context_cpu=serial_counter(self.helper_cpu),ll3_literal_lengths=serial_counter(self.helper_length),
            setup_tstates=44,exit_tstates=28)


def scopes_add(aggregates,observer,real):
    names=('branches_hit','flows_hit','tokens','bodies','named','cache','cache_values','cache_contexts',
           'helper','helper_literals','helper_cpu','helper_length')
    for scope in ('all','real') if real else ('all',):
        for name in names:aggregates[scope][name].update(getattr(observer,name))


def scope_summary(observer,counters):
    branches=[]
    for at,site in observer.branches.items():
        taken=counters['branches_hit'][at,1];not_taken=counters['branches_hit'][at,0]
        old=(12*taken+7*not_taken) if site['kind']=='jr' else 10*(taken+not_taken)
        alternative=10*(taken+not_taken) if site['kind']=='jr' else 12*taken+7*not_taken
        eligible=(site['kind']=='jp' and site['condition_index']<4 and
                  site['single_jp_shrink_fits'] and alternative<old)
        branches.append(dict(site,taken=taken,not_taken=not_taken,
            taken_probability=taken/(taken+not_taken) if taken+not_taken else None,
            observed_tstates=old,alternative_delta_tstates=alternative-old,
            alternative_code_delta_bytes=-1 if site['kind']=='jp' else 1,
            jp_to_jr_strictly_faster_and_smaller=eligible))
    nibbles=[]
    for at,site in observer.nibbles.items():
        cached=counters['cache'][at,'cached'];refill=counters['cache'][at,'refill']
        contexts=Counter()
        for (branch,phase,context),count in counters['cache_contexts'].items():
            if branch==at:contexts[context]+=count
        nibbles.append(dict(site,cached=cached,refill=refill,total=cached+refill,
            cpu_tstates=27*cached+66*refill,hot_contexts=contexts.most_common(8),
            cached_nibbles={str(n):counters['cache_values'][at,'cached',n] for n in range(16)},
            refill_nibbles={str(n):counters['cache_values'][at,'refill',n] for n in range(16)}))
    helpers=[]
    for (at,context,path),count in counters['helper'].items():
        helpers.append(dict(call_address=at,continuation_address=at+3,context=context,path=path,
            calls=count,literal_bytes=counters['helper_literals'][at,context,path],
            total_call_helper_ret_tstates=counters['helper_cpu'][at,context,path],
            call_ret_overhead_tstates=27*count))
    flows=[dict(site,hits=counters['flows_hit'][at]) for at,site in observer.flows.items()]
    total_cached=sum(count for (at,phase),count in counters['cache'].items() if phase=='cached')
    total_refill=sum(count for (at,phase),count in counters['cache'].items() if phase=='refill')
    return dict(branches=sorted(branches,key=lambda row:row['alternative_delta_tstates']),
        nibble_sites=sorted(nibbles,key=lambda row:row['total'],reverse=True),
        nibble_totals=dict(cached=total_cached,refill=total_refill,reads=total_cached+total_refill,
            cpu_tstates=27*total_cached+66*total_refill,cached_tstates=27,refill_tstates=66),
        ll3_helpers=sorted(helpers,key=lambda row:row['calls'],reverse=True),
        ll3_path_calls=serial_counter(Counter({path:sum(count for (at,context,p),count in counters['helper'].items() if p==path)
            for path in ('nibble','byte','word')})),
        ll3_calls=sum(counters['helper'].values()),
        setup_exit_hits=serial_counter(counters['named']),token_counts=serial_counter(counters['tokens']),
        body_hits=[dict(observer.contexts[name],hits=count) for name,count in counters['bodies'].most_common()],
        flow_sites=sorted(flows,key=lambda row:row['hits'],reverse=True),
        eligible_jp_to_jr_sites=[row for row in branches if row['jp_to_jr_strictly_faster_and_smaller']])


def compact_scope(scope):
    """Keep the overview small; the archive retains every site and histogram."""
    contexts={}
    for item in scope['ll3_helpers']:
        row=contexts.setdefault(item['context'],dict(context=item['context'],calls=0,
            literal_bytes=0,total_call_helper_ret_tstates=0,path_calls={}))
        for key in ('calls','literal_bytes','total_call_helper_ret_tstates'):row[key]+=item[key]
        row['path_calls'][item['path']]=row['path_calls'].get(item['path'],0)+item['calls']
    return dict(token_count=sum(scope['token_counts'].values()),
        ll3_calls=scope['ll3_calls'],ll3_path_calls=scope['ll3_path_calls'],
        ll3_call_ret_overhead_tstates=27*scope['ll3_calls'],
        top3_ll3_contexts=sorted(contexts.values(),key=lambda row:row['calls'],reverse=True)[:3],
        nibble_totals=scope['nibble_totals'],
        top3_nibble_sites=[{key:item[key] for key in ('address','context','cached','refill','total','cpu_tstates')}
            |dict(hot_contexts=item['hot_contexts'][:3]) for item in scope['nibble_sites'][:3]],
        setup_exit_hits=scope['setup_exit_hits'],setup_tstates_per_block=44,exit_tstates_per_block=28,
        eligible_jp_to_jr_sites=scope['eligible_jp_to_jr_sites'])


def write_reports(report,output):
    """Save complete observations plus a compact, linked decision overview."""
    leads=[]
    for name,profile in report['profiles'].items():
        real_site=next(row for row in profile['real']['branches']
            if row['kind']=='jp' and row['condition']=='C' and 'CopyMatchA' in row['target_labels'])
        all_site=next(row for row in profile['all']['branches'] if row['address']==real_site['address'])
        leads.append(dict(profile=name,status='unimplemented analytical E01 lead',
            change='Move the extended match-length block intact after done RET; invert the initial JP C into JR NC and let short matches fall through.',
            predicted_code_delta_bytes=-1,
            predicted_real_cpu_delta_tstates=-3*real_site['taken']+2*real_site['not_taken'],
            predicted_all_cpu_delta_tstates=-3*all_site['taken']+2*all_site['not_taken'],
            assumptions='JR reaches the moved block; no extra exit jump; unchanged extended exits and MatchUseC-to-ReadToken fallthrough.',
            acceptance='Requires future native correctness, actual final service bytes and complete per-case CPU verification; no gain is accepted here.'))
    report['future_E01_leads']=leads
    output.parent.mkdir(parents=True,exist_ok=True)
    archive=output.with_name(output.stem+'_full.json.gz')
    archive.write_bytes(gzip.compress((json.dumps(report,indent=2)+'\n').encode(),mtime=0))
    overview={key:value for key,value in report.items() if key not in ('profiles','task_head')}
    overview['observation_head']=report['task_head']
    overview['baseline_note']='Decoder proof is fixed at 9c28b01f; observation_head also includes later documentation commits.'
    overview['profiles']={}
    for name,item in report['profiles'].items():
        overview['profiles'][name]={key:item[key] for key in ('builder','kwargs','regions','relocated_regions',
            'labels_sha256','service_memory','intrinsic_service_bytes','actual_probe_irq_code_bytes',
            'actual_probe_irq_stack_headroom_bytes','worst_alignment_bytes','external_input_max',
            'external_output_history_max','all_case_tstates','real_tstates','instruction_sites',
            'static_conditional_sites','watch_sites','reused_frozen_coverage')}
        overview['profiles'][name]['real']=compact_scope(item['real'])
        overview['profiles'][name]['all']=dict(cases=675,
            nibble_totals=item['all']['nibble_totals'],ll3_calls=item['all']['ll3_calls'],
            ll3_path_calls=item['all']['ll3_path_calls'],
            eligible_jp_to_jr_sites=item['all']['eligible_jp_to_jr_sites'])
    overview['full_evidence']=dict(path=str(archive.relative_to(ROOT)).replace('\\','/'),sha256=sha(archive.read_bytes()))
    output.write_text(json.dumps(overview,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output=args.output.resolve()
    evidence=ROOT/'libraries/evidence'
    vectors=json.loads((evidence/'wide_hybrid_experiment_selectors.json').read_text())
    native_path=evidence/'wide_hybrid/wide_hybrid_experiment_short.json.gz'
    native=json.loads(gzip.decompress(native_path.read_bytes()))
    public_proof=json.loads((evidence/'hybrid_public_verification.json').read_text())
    assert public_proof['evidence_sha256']['wide_hybrid/wide_hybrid_experiment_short.json.gz']==sha(native_path.read_bytes())
    corpus=[(n,p,r,None) for n,p,r in samples()]
    cases=corpus+list(directed_tokens());assert len(cases)==675
    report=dict(date=date.today().isoformat(),stage='E00',complete=False,release=False,
        baseline_revision='9c28b01f',task_head=subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip(),
        public_decoder_changes=0,corpus_cases=95,directed_cases=580,
        evidence_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes()) for p in
            (native_path,evidence/'wide_hybrid_experiment_selectors.json',evidence/'hybrid_public_verification.json')},
        profiles={},proposed_E01_sets=[])
    for name,key,total in (('fast','short-budget-9500',14944429),('balanced','short-budget-6500',14983119),
                           ('compact','short-budget-5000',15048469)):
        vector=vectors['profiles'][key];frozen=native['profiles'][vector['report_profile']]
        profile=build(name);moved=build(name,core=0x9103)
        assert region_manifest(profile)==frozen['layout']['regions']
        assert region_manifest(moved)==frozen['relocated_layout']['regions']
        assert profile[2]['service_memory_bytes']==vector['service_memory_bytes']
        golden={row['case']:row for row in frozen['full_blocks']+frozen['directed_blocks']}
        assert len(golden)==675
        observer=Observer(profile)
        aggregate={scope:defaultdict(Counter) for scope in ('real','all')}
        rows=[]
        for case,payload,raw,wanted in cases:
            previous=golden[case]
            assert sha(payload)==previous['payload_sha256'] and sha(raw)==previous['raw_sha256']
            observer.reset()
            result=execute(profile,payload,raw,watch=observer.watch)
            assert result['tstates']==previous['candidate_tstates'],(name,case,result['tstates'],previous['candidate_tstates'])
            if wanted is not None:assert observer.tokens[wanted]
            counts=observer.finish(result)
            scopes_add(aggregate,observer,case.startswith('real-'))
            rows.append(dict(case=case,real=case.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
                compressed_input_bytes=len(payload),output_history_bytes=len(raw),tstates=result['tstates'],
                exact=True,proof_cpu_exact=True,stack_bytes=result['stack_bytes'],observers=counts))
        real=[row for row in rows if row['real']]
        assert sum(row['tstates'] for row in real)==total
        real_summary=scope_summary(observer,aggregate['real'])
        assert real_summary['ll3_calls']==4870
        assert sum(aggregate['real']['tokens'].values())==45247
        assert real_summary['nibble_totals']['reads']==39512
        all_summary=scope_summary(observer,aggregate['all'])
        report['profiles'][name]=dict(builder='lzsa.hybrid.build',kwargs=dict(profile=name),
            regions=region_manifest(profile),relocated_regions=region_manifest(moved),
            labels=profile[1],labels_sha256=sha(json.dumps(profile[1],sort_keys=True).encode()),
            service_memory=profile[2]['service_memory'],intrinsic_service_bytes=profile[2]['service_memory_bytes'],
            actual_probe_irq_code_bytes=13,actual_probe_irq_stack_headroom_bytes=6,
            worst_alignment_bytes=255,external_input_max=max(len(p) for n,p,r,w in cases),
            external_output_history_max=max(len(r) for n,p,r,w in cases),
            all_case_tstates=sum(row['tstates'] for row in rows),real_tstates=total,
            instruction_sites=len(observer.code),static_conditional_sites=len(observer.branches),
            watch_sites=len(observer.watch),real=real_summary,all=all_summary,blocks=rows,
            reused_frozen_coverage=dict(cases=675,relocation=True,irq=True,input_output_exact=True))
        eligible=real_summary['eligible_jp_to_jr_sites']
        for site in eligible[:3]:
            report['proposed_E01_sets'].append(dict(profile=name,sites=[site['address']],
                predicted_cpu_delta_tstates=site['alternative_delta_tstates'],predicted_service_delta_bytes=-1,
                status='hypothesis only; no candidate emitted',rejection='reject unless full native CPU and service both decrease'))
        print(name,json.dumps(dict(cases=len(rows),real_tstates=total,ll3=real_summary['ll3_calls'],
            nibble=real_summary['nibble_totals'],eligible_real_jp_to_jr=len(eligible))),flush=True)
    report['proposed_E01_sets']=report['proposed_E01_sets'][:3]
    report['E01_conditional_decision']='No JP-to-JR site wins on the real corpus and shrinks code.' if not report['proposed_E01_sets'] else 'At most three unimplemented hypotheses selected.'
    sources=[ROOT/'libraries/lzsa/src/lzsa'/name for name in ('hybrid.py','wide.py','_wide_kernels.py','_z80.py')]
    sources += [ROOT/'libraries/tests/native_block.py',ROOT/'libraries/tests/profile_branch_mix.py',Path(__file__),ROOT/'libraries/Z80_TIMINGS.md']
    report['source_sha256_lf']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sources}
    report['public_source_matches_9c28_proof']={name:digest==public_proof['source_sha256_lf'].get(name)
        for name,digest in report['source_sha256_lf'].items() if name.startswith('libraries/lzsa/src/')}
    report['limitations']=['Baseline observers only; no decoder candidate or E01/E02/E03 experiment implemented.',
        'All675 watched CPU totals match frozen native proof; previous IRQ/relocation runs are reused unchanged.',
        'Real and synthetic/direct cases are separate; an all-cases-only JP/JR gain cannot hide a real-corpus slowdown.',
        'Timing excludes IRQ service, ULA/WAIT, ROM/disk latency and movie publication timing.']
    report['complete']=True
    write_reports(report,args.output)


if __name__=='__main__':main()
