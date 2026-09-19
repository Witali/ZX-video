"""Sensitivity model using measured full-block FAP3 ZX0 Turbo durations.

No player changes. Native frame 0 and compact frame 1 are precomputed.
Compare free preemption within a block with whole-block decoding that may
start in idle time only if it fits. Uniform intra-block progress is an
optimistic assumption, not an instruction-level trace. Source-copy cost is
a sensitivity parameter, not measured transport. Current reader/packet/
AY/reconstruction costs remain charged; new setup, paging, disk, ULA and
IRQ screen publication are unimplemented and excluded.
"""
import argparse
import json
from pathlib import Path

from probe_decoded_queue_schedule import BLOCK,Decoder,simulate
from probe_lossless_layouts import sha


class WholeBlockDecoder(Decoder):
    """A block yields all its bytes together; partial blocks cannot be read."""
    def __init__(self,ends,costs,capacity):
        super().__init__(ends,costs,capacity)
        self.next_block = 0

    def advance(self,budget,until=None):
        limit = min(self.ends[-1],((int(self.consumed)//BLOCK)+self.capacity)*BLOCK)
        used = 0.0
        while self.next_block < len(self.ends):
            end,cost = self.ends[self.next_block],self.costs[self.next_block]
            if end > limit or cost > budget or until is not None and self.position >= until:
                break
            self.position = float(end); self.next_block += 1
            budget -= cost; used += cost
        allocated = (int(self.position-1e-7)//BLOCK+1 if self.position else 0)-int(self.consumed)//BLOCK
        self.peak_blocks = max(self.peak_blocks,allocated)
        if allocated > self.capacity: raise AssertionError('decoded queue overflow')
        self.work_done += used
        return used


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','static-summary','packets','turbo','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    old,static,packets,turbo = map(read,(args.baseline,args.static_summary,args.packets,args.turbo))
    if (not all(r['complete'] for r in (old,static,packets,turbo))
            or len(old['frames']) != len(static['frame_projection'])
            or not old['raw_sha256'] == static['raw_sha256'] == packets['output_sha256'] == turbo['input_sha256']
            or old['states_sha256'] != static['states_sha256']):
        raise ValueError('matching full reports required')
    ends = [packets['packets'][0]['offset']]+[r['consumed_raw_bytes'] for r in old['frames']]
    draw = [r['output_tstates'] for r in static['frame_projection']]
    pre = [r['tstates']-r['stages']['output']-r['stages']['banked_zx0']+s['reconstruction_delta']
        for r,s in zip(old['frames'],static['frame_projection'])]
    irq = [r['irq_tstates'] for r in old['frames']]
    original_costs = [sum(r['stages']['banked_zx0'] for r in old['header_results'])]+[
        r['stages']['banked_zx0'] for r in old['frames']]
    block_ends=[]; offset=0
    for b in turbo['blocks']:
        offset += b['raw_bytes']; block_ends.append(offset)
    if (offset != ends[-1] or any(b['raw_bytes'] != BLOCK for b in turbo['blocks'][:-1])
            or max(b['compressed_bytes'] for b in turbo['blocks']) > BLOCK):
        raise ValueError('8-KiB block/input slot assumption differs')
    scenarios=[]
    for transport in (0,16):
        costs = [b['tstates']+transport*b['compressed_bytes'] for b in turbo['blocks']]
        for model,decoder_type in (('uniform_free_preemption',Decoder),('whole_block',WholeBlockDecoder)):
            for extra in (0,5000,10000,20000):
                for capacity in range(1,8):
                    result = simulate(ends,costs,pre,draw,irq,capacity,extra,
                        decoder_ends=block_ends,decoder_type=decoder_type)
                    result.update(model=model,source_copy_tstates_per_byte=transport,
                        total_decode_and_source_copy_tstates=sum(costs),
                        fits_three_16k_input_output_banks=capacity<=3)
                    scenarios.append(result)
    control = simulate(ends,[0]*len(block_ends),pre,draw,irq,len(block_ends),0,decoder_ends=block_ends)
    if control['late_frames'] or control['forced_decode_tstates_estimate']:
        raise AssertionError('free predecode control failed')
    report = dict(scope=__doc__,complete=True,estimated_only=True,release=False,player_changed=False,
        player_delta_tstates=0,baseline_commit='f28a6b9',raw_sha256=old['raw_sha256'],
        states_sha256=old['states_sha256'],turbo_report_sha256=sha(args.turbo.read_bytes()),
        full_frame_count=len(pre),period_tstates=425448,
        banked_decode_including_header_tstates=sum(original_costs),
        turbo_core_tstates=turbo['summary']['total_tstates'],
        core_only_delta_tstates=turbo['summary']['total_tstates']-sum(original_costs),
        maximum_turbo_block_tstates=turbo['summary']['max_block_tstates'],
        maximum_compressed_block_bytes=max(b['compressed_bytes'] for b in turbo['blocks']),
        hypothetical_memory=dict(raw_ring_bank=0,raw_ring_bytes=16384,
            combined_input_output_banks=[1,3,4],input_bytes_per_bank=8192,output_bytes_per_bank=8192,
            decoded_queue_slots_without_extra_copy=3,remaining_banks_unchanged=[2,5,6,7],
            slots_above_three_are_capacity_sensitivity_only=True,
            source_copy_16T_is_lower_bound_without_loop_or_paging=True,
            disk_delivery_verified=False),
        banked_uniform_control=[simulate(ends,original_costs,pre,draw,irq,c,0) for c in (1,3,7)],
        free_predecode_control=control,scenarios=scenarios)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'scenarios'},indent=2))
    for r in scenarios:
        if r['decoded_blocks'] in (3,7) and r['extra_work_per_frame']==0: print(json.dumps(r))


if __name__ == '__main__': main()
