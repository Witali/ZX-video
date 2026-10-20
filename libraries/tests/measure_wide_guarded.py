"""Complete ordinary-format guard, producer, native-cursor and resource proof."""
import argparse
import gzip
import json
import struct
from pathlib import Path
from unittest.mock import patch

from measure_long_copy import ROOT,samples,noncanonical_cases,sha
from measure_full_token_dispatch import directed_tokens
from wide_guarded_support import wide_profile,native,Harness,guard,base
from lzsa.resumable import build as old_build
import benchmark_inplace_streaming as streaming
import lzsa2_stream
from verify_streaming_zx0_input import validate_histogram


def histogram(cpu):
    rows=[];total=0
    # These are standard UM0080 entries beyond the narrower old ZX0 table.
    extra={0x05:(4,),0x0f:(4,),0x26:(7,),0x37:(4,),0xc6:(7,),0xd6:(7,),0xd9:(4,),0xe9:(4,),0xf6:(7,)}
    for (pc,ticks),count in sorted(cpu.decoder_histogram.items()):
        code=bytes((cpu.read8(pc),cpu.read8(pc+1)))
        row=dict(pc=pc,tstates=ticks,count=count,opcode_hex=code.hex())
        if pc in (cpu.zlabels.get('header_patch'),cpu.zlabels['guard_literals']):
            # The final-input patcher changes PUSH AF11 to RET10 in place.
            # A final memory dump cannot identify the earlier executed opcode.
            assert ticks in (10,11);row['dynamic_instruction']='PUSH AF / RET'
        elif code[0] in extra:assert ticks in extra[code[0]]
        else:validate_histogram(code,pc,[row])
        total+=ticks*count;rows.append(row)
    return dict(tstates=total,rows=rows,instruction_table_checked=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    corpus=list(samples());extra=[(n,p,r) for n,p,r,v in directed_tokens()]
    cases=corpus+extra
    retained=list(guard.cases())+list(noncanonical_cases())+[r for r in corpus if r[0].startswith('real-')]
    assert len(retained)==63
    stream=b''.join(struct.pack('<HH',len(r),len(p))+p for n,p,r in retained)
    old_profiles={direct:old_build(core=0x8d74,core_limit=0x8e80,streaming=True,
                                  direct_header=direct,fast_jumps=True) for direct in (False,True)}
    old_native={};old_producer={}
    for direct in (False,True):
        h=guard.Harness(stream,57,direct_header=direct,fast_jumps=True)
        with patch.object(streaming,'trace',lzsa2_stream.trace),patch.object(base,'trace',lzsa2_stream.trace):
            for index,(name,payload,raw) in enumerate(retained):h.block(payload,raw,index,short=index==1)
        old_producer[direct]=dict(summary=h.finish(),blocks=h.results)
        assert old_producer[direct]['summary']['sector_reads']==772
    report=dict(date='2026-10-20',complete=False,release=False,goal_achieved=False,
        baseline_revision='f5a0362c',storage_budget_bytes=10000,
        scope='Identical raw-v2 blocks, quota cursors and old 32-byte/extent+7 guards; ROM/disk/ULA excluded.',
        native_cases=len(corpus),directed_cases=len(extra),placements=[0,1,252,253,254,255],
        retained_producer_cases=63,retained_stream_sha256=sha(stream),profiles={})
    for shared in (False,True):
        for direct in (False,True):
            key=('wide-shared' if shared else 'wide')+('-direct' if direct else '-call')
            profile=wide_profile(shared=shared,direct=direct)
            # Relocate below the A000 table instead of extending through the
            # fixed BC00 carry reservation. A003 correctly rejects overflow.
            moved=wide_profile(shared=shared,direct=direct,core=0x9f03)
            rows=[]
            for number,(name,payload,raw) in enumerate(cases):
                placements=[]
                for offset in report['placements']:
                    cache_key=(direct,number,offset)
                    if cache_key not in old_native:
                        old_native[cache_key]=native(old_profiles[direct],payload,raw,offset=offset)
                    before=old_native[cache_key]
                    after=native(profile,payload,raw,offset=offset)
                    assert before['input_waits']==after['input_waits']
                    assert before['output_cursors']==after['output_cursors']
                    deltas=[b-a for a,b in zip(before['slices'],after['slices'])]
                    assert len(before['slices'])==len(after['slices'])
                    if offset==253:
                        irq=native(moved,payload,raw,offset=offset,interrupts=True)
                        relocated=native(moved,payload,raw,offset=offset)
                        assert irq['input_waits']==after['input_waits']==relocated['input_waits']
                        assert irq['output_cursors']==after['output_cursors']==relocated['output_cursors']
                        assert relocated['tstates']==after['tstates']
                        irq_count=irq['injected_interrupts']
                    else:irq_count=0
                    placements.append(dict(offset=offset,input_start=after['input_start'],
                        baseline_tstates=before['tstates'],candidate_tstates=after['tstates'],
                        delta_tstates=after['tstates']-before['tstates'],slice_deltas=deltas,
                        output_cursors=after['output_cursors'],input_waits=after['input_waits'],
                        private_stack_bytes=after['private_stack_bytes'],caller_stack_bytes=after['caller_stack_bytes'],
                        guard_update_calls=after['guard_update_calls'],guard_update_tstates=after['guard_update_tstates'],
                        injected_interrupts=irq_count,exact=True))
                rows.append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                    compressed_input_bytes=len(payload),output_history_bytes=len(raw),placements=placements))
                if number%100==0:print(key,number,'/',len(cases),'native cases exact',flush=True)
            h=Harness(stream,57,shared=shared,direct=direct)
            with patch.object(streaming,'trace',lzsa2_stream.trace),patch.object(base,'trace',lzsa2_stream.trace):
                for index,(name,payload,raw) in enumerate(retained):h.block(payload,raw,index,short=index==1)
            old=old_producer[direct];new=h.finish();hist=histogram(h.cpu)
            assert hist['tstates']==new['decoder_tstates']
            assert new['sector_reads']==772 and new['sectors_exact_once']
            assert new['producer_tstates']==old['summary']['producer_tstates']
            real_old=real_new=0;producer_rows=[]
            for (name,payload,raw),a,b in zip(retained,old['blocks'],h.results):
                for field in ('decoded_bytes','payload_bytes','input_pointer','raw_sha256','payload_sha256',
                              'producer_tstates','sectors','carry_copy_bytes','input_waits',
                              'first_output_loaded_bytes','step_tstates'):
                    assert a[field]==b[field],(key,name,field)
                deltas=[y-x for x,y in zip(a['slice_tstates'],b['slice_tstates'])]
                producer_rows.append(dict(case=name,baseline=a,candidate=b,slice_deltas=deltas))
                if name.startswith('real-'):
                    real_old+=a['decoder_tstates'];real_new+=b['decoder_tstates']
            stacks={hex(top):top-low for top,low in h.cpu.stack_lows.items()}
            producer_bytes=sum(len(blob) for at,blob in h.regions)
            # Consumer code includes its callable patcher. The reference producer
            # retains its own original inline copy; count every copy plus carry.
            combined=profile[2]['service_memory_bytes']+producer_bytes+256
            combined+=max(0,stacks['0x9df0']-4)+stacks['0x9c00']
            assert combined+255<=10000,(key,combined)
            report['profiles'][key]=dict(metadata=profile[2],relocated_metadata=moved[2],
                regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]],
                native_blocks=rows,reference_producer_blocks=producer_rows,
                reference_producer_summary=new,baseline_producer_summary=old['summary'],histogram=hist,
                service=dict(consumer_bytes=profile[2]['service_memory_bytes'],
                    consumer_worst_alignment_bytes=profile[2]['service_memory_bytes']+255,
                    embedded_guard_update_code_bytes=profile[2]['guard_update_code_bytes'],
                    additional_reference_producer_code_state_bytes=producer_bytes,
                    required_reference_carry_bytes=256,reference_stacks=stacks,
                    consumer_plus_producer_carry_stacks_bytes=combined,
                    consumer_plus_producer_carry_stacks_worst_alignment_bytes=combined+255,
                    reference_producer_regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in h.regions],
                    native_irq_handler_code_bytes=13,irq_headroom_per_active_stack_bytes=6),
                summary=dict(real_decoder_baseline_tstates=real_old,real_decoder_candidate_tstates=real_new,
                    real_decoder_delta_tstates=real_new-real_old,
                    real_decoder_percent_saved=100*(real_old-real_new)/real_old,
                    native_slower_placements=[dict(case=r['case'],offset=p['offset'],delta_tstates=p['delta_tstates'])
                        for r in rows for p in r['placements'] if p['delta_tstates']>0],
                    native_slower_slices=sum(d>0 for r in rows for p in r['placements'] for d in p['slice_deltas']),
                    native_maximum_slice_delta=max(d for r in rows for p in r['placements'] for d in p['slice_deltas']),
                    actual_native_private_stack_bytes=max(p['private_stack_bytes'] for r in rows for p in r['placements']),
                    actual_native_caller_stack_bytes=max(p['caller_stack_bytes'] for r in rows for p in r['placements']),
                    reference_slower_blocks=[r['case'] for r in producer_rows if sum(r['slice_deltas'])>0],
                    reference_slower_slices=sum(d>0 for r in producer_rows for d in r['slice_deltas']),
                    reference_maximum_slice_delta=max(d for r in producer_rows for d in r['slice_deltas']),
                    input_waits_publications_producer_sectors_exact=True))
            print(key,json.dumps(report['profiles'][key]['summary']),flush=True)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode()+b'\n',mtime=0))
    report['source_sha256_lf']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n'))
        for p in (ROOT/'libraries/lzsa/src/lzsa/wide.py',ROOT/'libraries/lzsa/src/lzsa/wide_coroutine.py',
                  Path(__file__),Path(__file__).with_name('wide_guarded_support.py'))}
    report['complete']=True
    args.output.write_bytes(gzip.compress(json.dumps(report,indent=2).encode()+b'\n',mtime=0))


if __name__=='__main__':main()
