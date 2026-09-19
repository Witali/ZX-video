"""Audit idle-edge promises and execute selected real movie frames on Z80.

Full-movie timing is an instruction-table projection onto the previously
executed baseline. Selected frames use host-installed prior compact/native
states; these are isolated decoder checks, not continuous playback. Actual
IRQ timing is compared separately from the supplied partial clock reports.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from assess_frame_jitter import assess
from benchmark_context_huffman import word
from bulk_frame_stream import unpack as unpack_bulk
import causal_tile_z80 as machine
from cell_audio_stream import unpack as unpack_audio
from cell_screen_z80 import expected_tstates
from frame_output_pipeline import Harness,display_screen,frames,serialized_masks
from frame_packet_stream import unpack as unpack_packets
from probe_lossless_layouts import sha
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import OFFSETS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','baseline','storage','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--clock',type=Path,nargs=2,required=True,metavar=('OLD','NEW'))
    p.add_argument('--frames',type=int,nargs='+',default=[0,62,4052,4085,4086,4087,4220])
    args = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    raw = args.raw.read_bytes(); old = read(args.baseline); storage = read(args.storage)
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    if (raw[:4] != b'FAP3' or not old['complete'] or not old['skip_noop_runs']
            or old['raw_sha256'] != sha(raw) or old['states_sha256'] != sha(states.tobytes())
            or not storage['complete'] or storage['input_sha256'] != sha(raw)):
        raise ValueError('matching complete FAP3 baseline required')
    audio,cache_maps = unpack_cache(unpack_packets(unpack_bulk(raw)),32,4,return_maps=True)
    cells = unpack_audio(audio)[0]
    tables,mapping,packets = frames(cells); encoded_masks = serialized_masks(cells)
    if len(packets) != len(states) or len(old['frames']) != len(states):
        raise ValueError('different frame counts')
    rows=[]
    for i,(group,mask) in enumerate(packets):
        delta = machine.static_stripe_delta_tstates(group[3],group[4])
        before = old['frames'][i]
        output = expected_tstates(mask,fast_mask_dispatch=True,
            constant_attribute_borders=True,skip_black_borders=True)
        rows.append(dict(index=i,top_escape=bool(group[3][0]),bottom_escape=bool(group[3][176]),
            reconstruction_before=before['stages']['reconstruct'],
            reconstruction_after=before['stages']['reconstruct']+delta,reconstruction_delta=delta,
            output_tstates=output,
            projected_foreground=before['tstates']+delta+output-before['stages']['output']))
    options = dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,
        selective_cache=True,skip_noop_runs=True,constant_attribute_borders=True,skip_black_borders=True)
    executed=[]
    for i in args.frames:
        if not 0 <= i < len(states): raise ValueError('selected frame outside movie')
        results=[]; machines=[]
        for enabled in (False,True):
            h = Harness(tables,mapping,skip_static_stripes=enabled,**options)
            h.cpu.guarding = False
            if i:
                h.cpu.banks[5][0x2400:0x3300] = states[i-1].tobytes()
            target = 7 if i % 2 == 0 else 5
            for bank,previous in ((target,i-2),(12-target,i-1)):
                if previous >= 0:
                    screen = display_screen(states[previous].tobytes(),black_borders=True)
                    h.cpu.banks[bank][:6912] = screen
                    h.expected_screens[bank] = screen
            page = 0x16 if target == 7 else 0x1e
            h.cpu.port_7ffd = page
            h.cpu.write8(h.draw['saved_page'],page)
            h.cpu.write8(h.draw['screen_base'],0xc0 if target == 7 else 0x40)
            group,mask = packets[i]
            result = h.run(group,mask,states[i].tobytes(),i,
                encoded_metadata=encoded_masks[i],cache_map=cache_maps[i])
            if word(h.cpu,h.recon['vectors']) != 0xa400+192:
                raise AssertionError('edge shortcut consumed wrong vector count')
            for base,data in h.protected_regions:
                if bytes(h.cpu.read8(base+k) for k in range(len(data))) != data:
                    raise AssertionError('protected code or tables changed')
            results.append(result); machines.append(h)
        for bank in (5,7):
            if machines[0].cpu.banks[bank][:6912] != machines[1].cpu.banks[bank][:6912]:
                raise AssertionError('old/new native screens differ')
        if machines[0].cpu.banks[5][0x3400:0x3800] != machines[1].cpu.banks[5][0x3400:0x3800]:
            raise AssertionError('old/new rolling caches differ')
        if results[1]['total_tstates']-results[0]['total_tstates'] != rows[i]['reconstruction_delta']:
            raise AssertionError('instruction-table delta differs from execution')
        executed.append(dict(index=i,before=results[0],after=results[1],
            reconstruction_delta=rows[i]['reconstruction_delta'],compact_native_cache_and_cursors_equal=True))
    build_options = dict(hybrid=True,skip_empty=True,intra_above=True,intra_extended=True,
        fast_fragments=True,unrolled_motion=True,split_literals=True,raw_attributes=True,
        selective_cache=True,skip_noop_runs=True)
    sizes=[]; instruction_rows=[]
    for enabled in (False,True):
        code,labels,listing,regions = machine.build(tables,mapping,OFFSETS,
            skip_static_stripes=enabled,**build_options)
        aux = [(base,data) for base,data in regions if 0x7a00 <= base < 0x7b00]
        sizes.append(dict(main_bytes=len(code),auxiliary_bytes=sum(len(data) for _,data in aux),
            main_end=labels['end'],auxiliary_regions=[dict(base=base,code_hex=data.hex()) for base,data in aux]))
        if enabled:
            instruction_rows = [row for row in listing if row['stage'] == 'static_edge'
                or labels['stripe'] <= row['address'] < labels['regular_stripe']]
    left,right = map(read,args.clock)
    if (left['raw_sha256'] != sha(raw) or right['raw_sha256'] != sha(raw)
            or left['states_sha256'] != sha(states.tobytes()) or right['states_sha256'] != sha(states.tobytes())):
        raise ValueError('clock input differs')
    matched = min(len(left['frames']),len(right['frames'])); sums=[]
    for clock in (left,right):
        stages = Counter()
        for row in clock['frames'][:matched]: stages.update(row['stages'])
        sums.append(stages)
    total = sum(row['projected_foreground'] for row in rows)
    report = dict(scope=__doc__,complete=True,release=False,baseline_commit='a9f359f',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),cells_sha256=sha(cells),frames=len(states),
        stream_extra_bytes=0,stream_extra_sectors=0,extra_buffer_bytes=0,ay_changed=False,pixel_changes=0,
        zx0_with_headers_bytes=storage['zx0_with_headers_bytes'],
        edge_promises_verified=len(rows),escape_frames=[r['index'] for r in rows if r['top_escape'] or r['bottom_escape']],
        code_sizes=sizes,code_delta_bytes=sum(sizes[1][k]-sizes[0][k] for k in ('main_bytes','auxiliary_bytes')),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',new_instruction_listing=instruction_rows,
        projection=dict(full_execution_measured=False,
            reconstruction_before=sum(r['reconstruction_before'] for r in rows),
            reconstruction_after=sum(r['reconstruction_after'] for r in rows),
            reconstruction_delta=sum(r['reconstruction_delta'] for r in rows),
            foreground_after_black_borders_and_static_stripes=total,
            mean_tstates=total/len(rows),max_tstates=max(r['projected_foreground'] for r in rows),
            frames_above_425448=sum(r['projected_foreground']>425448 for r in rows)),
        isolated_real_frames=executed,frame_projection=rows,
        partial_clock=dict(matched_frames=matched,old_complete=left['complete'],new_complete=right['complete'],
            old_stages=dict(sums[0]),new_stages=dict(sums[1]),
            stage_delta={s:sums[1][s]-sums[0][s] for s in sums[0].keys()|sums[1].keys()},
            total_foreground_delta=sum(sums[1].values())-sum(sums[0].values()),
            old_timing=assess(left['publications'][:matched]),new_timing=assess(right['publications'][:matched]),
            old_failure=left.get('failure'),new_failure=right.get('failure')),
        disk_delivery_verified=False,cadence_verified=False,ula_measured=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('frame_projection','new_instruction_listing','isolated_real_frames')},indent=2))


if __name__ == '__main__': main()
