"""Model a three-slot predecode queue using current volume-specific CPU costs.

This is a scheduling experiment, not an integrated player. Source blocks are
the actual independently bootable TRD streams. Per-frame stage costs replace
only the Huffman primitive in the complete volume-1 execution report, then
adjust the first two cold frames' native maps/attribute-list warmup. The
primitive formulas were checked against Z80 opcodes in carry_huffman_symbols.

Packet copying is charged at 16 T/byte, AY enqueue and AY/old-clock IRQ at
their instruction formulas. Reader setup/loops, new queue control/paging,
video IRQ/progress, ULA, ROM and disk latency are excluded. Transport 32 T/B
is a lower bound on TWO LDI copies, not a measured complete loader. Constant
extra T/frame is only sensitivity. Baseline stage wrappers are retained;
only six nominal IRQs/frame are charged, not additional ticks after a delay.
This model is not a formal impossibility proof or release check.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path

import numpy as np
from benchmark_prefix_huffman import Harness as PrefixHarness
from build_fap3_trd import sha
from cell_screen_z80 import expected_tstates
from attribute_groups_z80 import prepare_tstates
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from probe_volume_huffman import collect,retable
from profile_volume_huffman import costs

PERIOD=425448


def entropy_costs(packets,tables,mapping):
    base=costs(packets,tables,PrefixHarness(tables,mapping).layout)
    lengths=np.array([list(t) for t in tables],np.int32)
    for row,p in zip(base,packets):
        n=lengths[p['contexts'],p['values']]; offset=(np.cumsum(n)-n)%8
        row['primitive_tstates']+=-8*int(np.count_nonzero(n<=8))+8*int(np.count_nonzero((n>8)&(offset!=0)))
    return [r['primitive_tstates'] for r in base]


def output_costs(packets,start=0,end=None):
    result=[];counts=[0,0]
    for local,p in enumerate(packets[start:end]):
        d=p['detail'];body=d['payload'];at=p['ay_bytes']+200
        masks=restore(body[at:at+d['mask_bytes']],1,480,4)[384:]
        flags=np.packbits(np.frombuffer(masks,dtype=np.uint8)!=0).tobytes()[1:11]
        raw=bool(d['flags']&64)
        counts[local%2]=72 if raw or local<2 else sum(v.bit_count() for v in flags)
        native=body[d['coded_offset']-80:d['coded_offset']]
        if start and local<2: native=b'\xff'*80
        result.append(dict(draw=expected_tstates(native,fast_mask_dispatch=True,
            constant_attribute_borders=True,skip_black_borders=True,attribute_group_counts=counts,gray_cells=True),
            prepare=prepare_tstates(flags,raw=raw,warmup=local<2)))
    return result


class Queue:
    """Fixed bank slots; cold leading/trailing partial blocks still occupy a slot."""
    def __init__(self,blocks,slots,transport,atomic):
        self.slots,self.atomic=slots,atomic
        self.ends=[];self.costs=[];self.chunks=[];pos=0
        for b in blocks:
            end=pos+b['raw_bytes'];self.ends.append(end)
            cost=b['tstates']+transport*b['compressed_bytes'];self.costs.append(cost)
            for j,s in enumerate(b['slices']):
                self.chunks.append((len(self.ends)-1,pos+s['produced'],
                    s['tstates']+(transport*b['compressed_bytes'] if j==0 else 0)))
            pos=end
        self.position=self.consumed=self.work=0.0;self.next=0;self.peak=0

    def advance(self,budget,until=None):
        first=bisect_right(self.ends,self.consumed)
        limit=self.ends[min(len(self.ends),first+self.slots)-1]
        used=0.0
        if self.atomic:
            while self.next<len(self.chunks):
                block,end,cost=self.chunks[self.next]
                if block>=first+self.slots or cost>budget or until is not None and self.position>=until:break
                self.position=end;self.next+=1;used+=cost;budget-=cost
                self.peak=max(self.peak,block-first+1)
        else:
            if until is not None:limit=min(limit,until)
            while self.position<limit and budget>0:
                block=bisect_right(self.ends,self.position)
                begin=0 if block==0 else self.ends[block-1]
                end=min(self.ends[block],limit);rate=self.costs[block]/(self.ends[block]-begin)
                amount=end-self.position;cost=amount*rate
                if cost>budget:amount=budget/rate;cost=budget
                self.position+=amount;budget-=cost;used+=cost
                if abs(self.position-end)<1e-7:self.position=float(end)
                self.peak=max(self.peak,block-first+1)
        self.work+=used
        if self.peak>self.slots:raise AssertionError('slot overflow')
        return used

    def require(self,end):
        used=0.0;self.consumed=min(end,self.position)
        while self.position<end:
            before=self.position;used+=self.advance(float('inf'),end)
            self.consumed=min(end,self.position)
            if self.position==before:raise AssertionError('deadlock')
        self.consumed=end
        return used


def simulate(blocks,frames,slots,transport,extra,atomic):
    q=Queue(blocks,slots,transport,atomic)
    startup=q.advance(float('inf'))
    # Native 0 and compact 1 have been prepared before starting the clock.
    startup+=q.require(frames[1]['end'])
    now=0.0;late=[];runs=[];run=None;forced=0.0
    for i in range(1,len(frames)):
        free_at=(i-1)*PERIOD
        if now<free_at:q.advance(free_at-now);now=float(free_at)
        now+=frames[i]['draw']+frames[i]['irq']+extra
        delay=max(0,now-i*PERIOD)
        if delay>0.001:
            late.append(dict(frame=frames[i]['frame'],tstates=round(delay,3)))
            if run is None:run=dict(first=frames[i]['frame'],recovered_at=None);runs.append(run)
        elif run is not None:run['recovered_at']=frames[i]['frame'];run=None
        if i+1<len(frames):
            t=q.require(frames[i+1]['end']);forced+=t;now+=t+frames[i+1]['pre']
    # Complete any final zero-output calls, preserving all measured work.
    tail=q.advance(float('inf'))
    if q.consumed!=q.ends[-1] or abs(q.work-sum(q.costs))>0.01:
        raise AssertionError(('coverage/work conservation',q.consumed,q.ends[-1],q.work,sum(q.costs)))
    return dict(slots=slots,decoded_capacity_bytes=slots*8192,transport_tstates_per_byte=transport,
        extra_tstates_per_frame=extra,model='measured_atomic_slices' if atomic else 'uniform_free_preemption',
        fits_proposed_three_slot_map=slots<=3,late_frames=len(late),first_late=late[0] if late else None,
        worst_late=max(late,key=lambda r:r['tstates']) if late else None,
        recovered_runs=sum(r['recovered_at'] is not None for r in runs),
        unrecovered_runs=sum(r['recovered_at'] is None for r in runs),
        late_runs=runs,startup_decode_tstates=round(startup,3),forced_decode_tstates=round(forced,3),
        unused_final_call_tstates=tail,peak_slots=q.peak,total_decoder_tstates=round(q.work,3))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','states','decoder','stage','symbols','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    decoder,stage,symbols=[json.loads(path.read_bytes()) for path in (args.decoder,args.stage,args.symbols)]
    if not all(r['complete'] for r in (decoder,stage,symbols)):raise ValueError('partial input')
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if sha(states.tobytes())!=stage['states_sha256'] or len(stage['frames'])!=len(states):raise ValueError('stage scope differs')
    source=(args.directory/'volume-1.raw').read_bytes()
    if sha(source)!=stage['raw_sha256']:raise ValueError('stage entropy differs')
    header,mapping,original,packets,_=collect(source,states)
    base=entropy_costs(packets,original,mapping);global_draw=output_costs(packets)
    result=dict(complete=False,release=False,estimated_only=True,scope=__doc__,baseline_commit='a562c4d',
        states_sha256=stage['states_sha256'],frames=len(states),volumes=[],
        actual_publication_verified=False,fallback_jitter_verified=False,
        memory=dict(compressed_ring_bank=0,compressed_ring_bytes=16384,slot_banks=[1,3,4],
            compressed_slot_bytes=8192,decoded_slot_bytes=8192,unchanged_banks=[2,5,6,7],
            unchanged_private_stack=[0x7b70,0x7be0],decoder_code=[0x7c00,decoder['local_labels']['end']],
            queue_and_transport_code_not_implemented=True,smaller_disk_ring_delivery_verified=False),
        inputs={name:dict(file=getattr(args,name).name,sha256=sha(getattr(args,name).read_bytes()))
            for name in ('decoder','stage','symbols')})
    for volume in decoder['volumes']:
        part,start,end=volume['part'],volume['frame_start'],volume['frame_end_exclusive']
        raw=(args.directory/f'volume-{part}.raw').read_bytes()
        _,_,count,m,tables=read_header(Reader(raw),magic=b'FAP3')
        if (m!=mapping or count!=len(states) or sha(raw)!=volume['raw_sha256']
                or retable(header,mapping,original,packets,tables)[0]!=raw):
            raise ValueError('volume differs from stage except entropy')
        entropy=entropy_costs(packets,tables,mapping)
        verified=symbols['volumes'][part-1]
        if (verified['raw_sha256']!=sha(raw) or verified['start']!=start or verified['end']!=end
                or [r['tstates'] for r in verified['frames']]!=entropy[start:end]):
            raise ValueError('primitive formula differs from exhaustive opcode evidence')
        draws=output_costs(packets,start,end);frames=[];position=0
        for local,i in enumerate(range(start,end)):
            p=packets[i];detail=p['detail']
            # All non-entropy bytes are exact; only encoded length changes.
            length=2+len(detail['payload'])+(sum(tables[int(c)][int(v)] for c,v in zip(p['contexts'],p['values']))+7)//8-(p['bits']+7)//8
            position+=length
            s=stage['frames'][i]
            if s['frame']!=i:raise ValueError('stage order differs')
            stage_pre=s['tstates']-global_draw[i]['draw']+entropy[i]-base[i]+draws[local]['prepare']-global_draw[i]['prepare']
            changed=sum(t[0] for t in detail['ticks'])
            irq=6*(19+116+17)+sum(367+83*t[0] if t[0] else 377 for t in detail['ticks'])
            frames.append(dict(frame=i,end=position,packet_bytes=length,
                pre=stage_pre+16*length+1705+42*changed,draw=draws[local]['draw'],irq=irq,
                stage_tstates=stage_pre+draws[local]['draw'],entropy_delta_tstates=entropy[i]-base[i]))
        if position!=sum(b['raw_bytes'] for b in volume['blocks']):raise ValueError('packet/block coverage differs')
        scenarios=[simulate(volume['blocks'],frames,slots,transport,extra,atomic)
            for atomic in (False,True) for transport in (0,32) for extra in (0,5000,10000)
            for slots in (1,3,4,7)]
        row=dict(part=part,start=start,end=end,raw_sha256=sha(raw),frames=frames,scenarios=scenarios)
        result['volumes'].append(row)
        for scenario in scenarios:
            if scenario['slots']==3 and scenario['extra_tstates_per_frame']==0:
                print(json.dumps(dict(part=part,**{k:v for k,v in scenario.items() if k!='late_runs'})),flush=True)
    result['complete']=True
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
