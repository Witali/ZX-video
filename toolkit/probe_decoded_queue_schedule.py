"""Estimate a pipelined player with a bounded queue of 8-KiB decoded blocks.

No player changes or speed verification. Distribute measured per-frame ZX0
T uniformly over the raw byte interval that frame consumed. This preserves
the total work but approximates its placement, especially at block edges.
Decoding is arbitrarily preemptible, resumes/paging/IRQ publication are free,
and compressed bytes are supplied instantly. The optional constant work per
frame is a sensitivity parameter, NOT a measured disk/ULA cost.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path

PERIOD, BLOCK = 6*70908,8192


class Decoder:
    def __init__(self, ends, costs, capacity):
        self.ends,self.costs,self.capacity=ends,costs,capacity
        self.position=self.consumed=0.0
        self.peak_blocks=0
        self.work_done=0.0

    def advance(self,budget,until=None):
        limit=min(self.ends[-1],((int(self.consumed)//BLOCK)+self.capacity)*BLOCK)
        if until is not None: limit=min(limit,until)
        used=0.0
        while self.position < limit and budget>0:
            i=bisect_right(self.ends,self.position)
            first=0 if i==0 else self.ends[i-1]
            end=min(self.ends[i],limit)
            rate=self.costs[i]/(self.ends[i]-first)
            amount=end-self.position
            duration=amount*rate
            if duration>budget:
                amount=budget/rate; duration=budget
            self.position+=amount; used+=duration; budget-=duration
            if abs(self.position-end)<1e-7: self.position=float(end)
        allocated=(int(self.position-1e-7)//BLOCK+1 if self.position else 0)-int(self.consumed)//BLOCK
        self.peak_blocks=max(self.peak_blocks,allocated)
        if allocated>self.capacity: raise AssertionError('decoded queue overflow')
        self.work_done+=used
        return used

    def require(self,end):
        used=0.0
        self.consumed=min(end,self.position)
        while self.position<end:
            before=self.position
            used+=self.advance(float('inf'),end)
            self.consumed=min(end,self.position)
            if self.position==before: raise AssertionError('decoded queue deadlock')
        self.consumed=float(end)
        return used


def simulate(ends,costs,pre,draw,irq,capacity,extra,*,decoder_ends=None,decoder_type=Decoder):
    decoder=decoder_type(ends if decoder_ends is None else decoder_ends,costs,capacity)
    startup_decode=decoder.advance(float('inf'))
    # Native frame 0 and compact frame 1 are ready before the clock starts.
    startup_decode+=decoder.require(ends[2])
    now=0.0; late=[]; forced=0.0
    for i in range(1,len(pre)):
        free_at=(i-1)*PERIOD
        if now<free_at:
            decoder.advance(free_at-now)
            now=float(free_at)
        now+=draw[i]+irq[i]+extra
        delay=max(0.0,now-i*PERIOD)
        if delay>0.001: late.append(dict(frame=i,tstates=round(delay,3)))
        if i+1<len(pre):
            spent=decoder.require(ends[i+2]); forced+=spent
            now+=spent+pre[i+1]
    if decoder.consumed!=ends[-1] or decoder.position!=ends[-1]:
        raise AssertionError('incomplete model input')
    if abs(decoder.work_done-sum(costs))>0.01:
        raise AssertionError('decode work was lost or duplicated')
    return dict(decoded_blocks=capacity,decoded_bytes=capacity*BLOCK,extra_work_per_frame=extra,
        late_frames=len(late),first_late=late[0] if late else None,
        worst_late=max(late,key=lambda r:r['tstates']) if late else None,
        startup_decode_tstates_estimate=round(startup_decode,3),
        forced_decode_tstates_estimate=round(forced,3),peak_allocated_blocks=decoder.peak_blocks)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','noop-summary','packets','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    old,summary,packets=read(args.baseline),read(args.noop_summary),read(args.packets)
    if (not old['complete'] or not packets['complete']
            or old['states_sha256']!=summary['states_sha256'] or old['raw_sha256']!=packets['output_sha256']):
        raise ValueError('matching full reports required')
    ends=[packets['packets'][0]['offset']]+[r['consumed_raw_bytes'] for r in old['frames']]
    costs=[sum(r['stages']['banked_zx0'] for r in old['header_results'])]+[
        r['stages']['banked_zx0'] for r in old['frames']]
    draw=[r['stages']['output'] for r in old['frames']]
    irq=[r['irq_tstates'] for r in old['frames']]
    pre=[r['tstates']-d-4481+s['reconstruction_delta']-r['stages']['banked_zx0']
        for r,d,s in zip(old['frames'],draw,summary['frame_deltas'])]
    results=[simulate(ends,costs,pre,draw,irq,capacity,extra)
        for extra in (0,5000,10000,20000) for capacity in range(1,8)]
    unbounded=simulate(ends,costs,pre,draw,irq,(ends[-1]+BLOCK-1)//BLOCK,0)
    if unbounded['forced_decode_tstates_estimate'] or unbounded['late_frames']:
        raise AssertionError('unbounded predecode disagrees with the free-ZX0 estimate')
    report=dict(scope=__doc__,complete=True,estimated_only=True,release=False,player_changed=False,
        player_delta_tstates=0,states_sha256=old['states_sha256'],raw_sha256=old['raw_sha256'],
        proposed_memory=dict(raw_ring_bank=0,raw_ring_bytes=16384,
            decoded_banks=[1,3,4],decoded_bytes=49152,existing_bank7_history_bytes=8192,
            total_history_bytes=57344,actual_bank_switching_implemented=False,
            disk_delivery_verified=False),scenarios=results,
        impossible_unbounded_predecode_control=unbounded)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for row in results: print(json.dumps(row))


if __name__=='__main__': main()
