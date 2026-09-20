"""Size a partially decoded ring using current FAP3 and exact compact frames.

Also replay a proposed in-RAM cell-command representation, not an on-disk
codec. Its producer would run ZX0, metadata, Huffman and prediction ahead;
its consumer would expand queued 2-bit cells and copy attributes. Python
roundtrip is not a Z80 implementation or a playback timing verification.
ZX0-only queue timing reuses the explicitly approximate uniform-work model.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path
import struct

import numpy as np
from bulk_frame_stream import read_packet,unpack as unpack_bulk
from cell_audio_stream import unpack as unpack_audio,take_tick
from frame_packet_stream import unpack
from frame_output_pipeline import frames
from probe_decoded_queue_schedule import simulate
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from stream_reader_z80 import copy_tstates


def capacity(sizes,budget):
    """Complete consecutive records fitting from each start (EOF tails excluded)."""
    prefix=[0]
    for n in sizes: prefix.append(prefix[-1]+n)
    windows=[]
    for start in range(len(sizes)):
        stop=bisect_right(prefix,prefix[start]+budget)-1
        if stop==len(sizes): continue
        windows.append(dict(start=start,frames=stop-start,bytes=prefix[stop]-prefix[start]))
    if not windows: raise ValueError('budget holds entire input')
    return dict(budget_bytes=budget,min_frames=min(r['frames'] for r in windows),
        median_frames=float(np.median([r['frames'] for r in windows])),
        max_frames=max(r['frames'] for r in windows),
        worst_window=min(windows,key=lambda r:r['frames']),
        average_sizing_frames=budget/(sum(sizes)/len(sizes)),
        minimum_seconds=min(r['frames'] for r in windows)*0.12,
        excludes_final_short_tail=True,descriptor_bytes_excluded=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','cpu','storage','copy-report','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes()
    old=json.loads(args.cpu.read_text()); storage=json.loads(args.storage.read_text())
    copied=json.loads(args.copy_report.read_text())
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    if not all(x['complete'] for x in (old,storage,copied)): raise ValueError('incomplete source report')
    if not sha(raw)==old['raw_sha256']==storage['input_sha256']==copied['raw_sha256']:
        raise ValueError('different raw streams')
    if sha(states.tobytes())!=old['states_sha256']: raise ValueError('different states')
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    _,_,groups=frames(cells)
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3'); header_end=r.pos
    if count!=len(states) or count!=len(old['frames']) or count!=len(groups): raise ValueError('different frame counts')
    ends=[]; pos=0
    for block in storage['blocks']: pos+=block['decoded_bytes']; ends.append(pos)
    if pos!=len(raw): raise ValueError('incomplete block coverage')
    raw_sizes=[]; command_sizes=[]; rows=[]; copy_delta=[]; commands_hash=bytearray()
    histories=[bytearray(3072)+bytearray([1]*768) for _ in range(2)]
    for i,(state,(_,native),cpu) in enumerate(zip(states,groups,old['frames'])):
        start=r.pos; _,packet=read_packet(r,stored_guards=False); raw_sizes.append(r.pos-start)
        if r.pos!=cpu['consumed_raw_bytes']: raise AssertionError('frame cursor mismatch')
        mask=native[4:76]; ay=b''.join(packet['ticks']); pixels=bytearray()
        for band in range(18):
            for col in range(32):
                if mask[band*4+col//8] & (128>>(col%8)):
                    for line in range(4):
                        location=(12+band*4+line)*32+col
                        pixels.append(int(state[location]))
        body=ay+mask+state[3168:3744].tobytes()+pixels
        command=struct.pack('<H',len(body))+body; command_sizes.append(len(command)); commands_hash+=command
        # Independent consumer cursor: AY stays encoded as six original updates;
        # replay cells in the native-mask order onto the screen used two frames ago.
        q=Reader(command); n=q.u16(); payload=q.take(n); q.end(); q=Reader(payload)
        ticks=[take_tick(q) for _ in range(6)]
        if ticks!=packet['ticks']: raise AssertionError('AY changed')
        replay_mask=q.take(72); target=histories[i%2]; target[3168:3744]=q.take(576)
        for band in range(18):
            for col in range(32):
                if replay_mask[band*4+col//8] & (128>>(col%8)):
                    values=q.take(4)
                    for line,value in enumerate(values): target[(12+band*4+line)*32+col]=value
        q.end()
        if target[384:2688]!=state[384:2688].tobytes() or target[3168:3744]!=state[3168:3744].tobytes():
            raise AssertionError(('prepared-cell replay differs',i))
        parts=[]; at=start
        for request in (2,len(packet['payload'])):
            left=request
            while left:
                block=bisect_right(ends,at); amount=min(left,ends[block]-at)
                parts.append(amount); at+=amount; left-=amount
        delta=sum(copy_tstates(n,unrolled=True)-copy_tstates(n) for n in parts); copy_delta.append(delta)
        rows.append(dict(index=i,packet_bytes=raw_sizes[-1],prepared_cell_bytes=len(command),
            marked_cells=len(pixels)//4,ay_bytes=len(ay),copy_delta_tstates=delta,
            foreground_after_copy_tstates=cpu['tstates']+delta,
            zx0_tstates=cpu['stages'].get('banked_zx0',0),reconstruct_tstates=cpu['stages']['reconstruct'],
            output_tstates=cpu['stages']['output']))
    r.end()
    if sum(copy_delta)!=copied['copy_delta_tstates']: raise AssertionError('copy projection differs')
    positions=[header_end]+[f['consumed_raw_bytes'] for f in old['frames']]
    costs=[sum(h['stages'].get('banked_zx0',0) for h in old['header_results'])]+[x['zx0_tstates'] for x in rows]
    draw=[x['output_tstates'] for x in rows]; irq=[x['irq_tstates'] for x in old['frames']]
    pre=[x['foreground_after_copy_tstates']-x['zx0_tstates']-x['output_tstates'] for x in rows]
    scenarios=[simulate(positions,costs,pre,draw,irq,slots,extra)
        for extra in (0,5000,10000) for slots in (1,3,4,5,7)]
    free=simulate(positions,[0]*len(costs),pre,draw,irq,len(ends)+1,0)
    if free['late_frames'] or free['forced_decode_tstates_estimate']:
        raise AssertionError('free predecode control differs')
    result=dict(scope=__doc__,baseline_commit='fa7cfb7',complete=True,estimated_only=True,release=False,
        player_changed=False,player_delta_tstates=0,raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        frames=count,compressed_stream_bytes=copied['compressed_bytes'],compressed_stream_delta_bytes=0,
        prepared_cells_python_roundtrip_frames=count,prepared_ay_ticks_checked=count*6,
        prepared_command_sha256=sha(commands_hash),z80_prepared_cell_consumer_implemented=False,
        design_constraints=dict(build_native_directly_in_hidden_bank=True,
            final_full_screen_copy_allowed=False,screen_banks=[5,7],
            queued_data='compressed/intermediate records, never a FIFO of full native screens',
            fixed_compact_prediction_state_is_not_a_native_screen_copy=True,
            minimum_banked_staging_requires_measurement=True),
        comparison_policy=dict(winner='undetermined',keep_existing_player_until_measured=True,
            native_full_screen_copies_in_existing_pipeline=0,
            do_not_credit_existing_zero_copy_screen_flip_as_new_saving=True,
            require_total_producer_consumer_transport_cost=True,
            require_complete_actual_publication_and_disk_verification=True),
        sizing={name:dict(total_bytes=sum(sizes),mean_bytes=sum(sizes)/count,min_bytes=min(sizes),max_bytes=max(sizes),
            capacity_30k=capacity(sizes,30*1024),capacity_32k=capacity(sizes,32*1024))
            for name,sizes in (('after_zx0',raw_sizes),('prepared_cells',command_sizes))},
        flat_screen_capacity_30k=dict(native_bytes=6912,native_frames=30720//6912,
            compact_bytes=3840,compact_frames=30720//3840),
        model_scope='Uniform ZX0 work per consumed byte; arbitrarily preemptible; one compact frame ahead. '
            'Includes full old frame/IRQ costs adjusted by verified unrolled-copy delta. '
            'Excludes new pipeline/paging/control, transport, ULA, ROM and disk. '
            'Extra per-frame T is sensitivity, not measured overhead. Prepared-cell FIFO timing is NOT modeled.',
        zx0_queue_scenarios=scenarios,impossible_free_predecode_control=free,
        memory_proposal=dict(compressed_ring_banks=[0,1],compressed_ring_bytes=32768,
            prepared_ring_banks=[3,4],prepared_ring_bytes=30720,management_reserve_bytes=2048,
            unchanged_banks=[2,5,6,7],existing_zx0_work_history_bytes=8192,
            banked_transport_implemented=False,sustained_disk_delivery_verified=False),
        frames_detail=rows)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames_detail','zx0_queue_scenarios')},indent=2))
    for s in scenarios:
        if s['extra_work_per_frame']==0: print(json.dumps(s))


if __name__=='__main__': main()
