"""Full-movie CPU/pixel check for RAM-only idle stripe masks.

Host supplies packets and switches bank 7 for metadata (the real parser is
already there). Execute metadata, reconstruction and both screen buffers;
poison idle masks and forbid reading/writing them. Compare to saved exact
frame counts adjusted by the saved compiled-metadata delta; additionally
execute the compiled baseline for the first --paired frames of each disk.
No physical disk, ULA contention, IRQ cadence or release claim.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from benchmark_static_cache_borders import OPTIONS
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from build_fap3_trd import sha
from idle_masks_z80 import idle_stripes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','states','model','metadata-model','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int,help='Partial debugging only')
    p.add_argument('--max-frames',type=int,help='Stop after this many frames across the volume sequence; partial evidence')
    p.add_argument('--paired',type=int,default=8)
    args = p.parse_args()
    if args.max_frames is not None and args.max_frames <= 0: raise ValueError('positive frame limit required')
    model, cm = [json.loads(path.read_bytes()) for path in (args.model,args.metadata_model)]
    with np.load(args.states,allow_pickle=False) as f: states = f['states']
    if not model['complete'] or not cm['complete'] or sha(states.tobytes()) != model['states_sha256']:
        raise ValueError('incomplete or mismatching reference')
    report = dict(complete=False,release=False,scope=__doc__,baseline_commit='8c6c9f6',
        model_sha256=sha(args.model.read_bytes()),metadata_model_sha256=sha(args.metadata_model.read_bytes()),
        states_sha256=sha(states.tobytes()),raw_and_compressed_delta_bytes=0,
        disk_delivery_verified=False,frame_deadlines_verified=False,volumes=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        next_frame = 0
        for v,meta_v in zip(model['volumes'],cm['volumes']):
            checked = sum(len(v['frames']) for v in report['volumes'])
            if args.max_frames is not None and checked >= args.max_frames: break
            part,start,end = v['part'],v['start'],v['end']
            if start != next_frame or (part,start,end) != (meta_v['part'],meta_v['start'],meta_v['end']):
                raise ValueError('volume boundaries differ')
            raw = (args.directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != v['raw_sha256'] or sha(raw) != meta_v['raw_sha256']: raise ValueError('raw differs')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
            tables,mapping,packets = frames(cells); meta = serialized_masks(cells)
            r = Reader(raw); _,_,count,_,_ = read_header(r,magic=b'FAP3')
            details = [read_packet(r,stored_guards=False)[1] for _ in range(count)]; r.end()
            hs = [Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,register_fragments=True,
                          metadata_mode=mode,**OPTIONS) for mode in ('compiled','idle')]
            for h in hs:
                c = h.cpu; c.guarding = False
                if start: c.banks[5][0x2400:0x3300] = states[start-1].tobytes()
                for bank,i in ((7,start-2),(5,start-1)):
                    if i >= 0:
                        s = display_screen(states[i].tobytes(),black_borders=True)
                        s = bytes(6144)+s[6144:]
                        c.banks[bank][:6912] = s; h.expected_screens[bank] = s
            volume = dict(part=part,start=start,end=end,raw_sha256=sha(raw),frames=[],
                          compiled_initialization=hs[1].metadata_init_result,
                          instruction_listing=list(hs[1].instructions.values()))
            report['volumes'].append(volume)
            stop = min(end,start+args.limit) if args.limit else end
            if args.max_frames is not None: stop = min(stop,start+args.max_frames-checked)
            for index in range(start,stop):
                local = index-start; group,native = packets[index]
                if start and local < 2: native = b'\xff'*80
                actual = hs[1].run(group,native,states[index].tobytes(),local,
                                   encoded_metadata=meta[index],cache_map=details[index]['cache'])
                old_frame,old_meta = v['frames'][local],meta_v['frames'][local]
                if old_frame['frame'] != index or old_meta['frame'] != index: raise ValueError('model indices differ')
                before = old_frame['tstates'] + old_meta['delta_tstates']
                if local < args.paired:
                    baseline = hs[0].run(group,native,states[index].tobytes(),local,
                                         encoded_metadata=meta[index],cache_map=details[index]['cache'])
                    if baseline['total_tstates'] != before: raise AssertionError(('baseline differs',part,index,before,baseline))
                after = actual['total_tstates']; idle = idle_stripes(group[3],group[4])
                volume['frames'].append(dict(frame=index,baseline_tstates=before,tstates=after,delta_tstates=after-before,
                    baseline_metadata_tstates=old_meta['compiled_tstates'],metadata_tstates=actual['stages']['metadata'],
                    idle_stripes=sum(idle),idle_inner_stripes=sum(idle[1:-1]),stages=actual['stages']))
                if local % 200 == 0:
                    save(); print(f'Exact idle metadata, compact and both screens: part {part}, {local+1}/{end-start}',flush=True)
            volume.update(checked_frames=len(volume['frames']),
                **{key:sum(f[key] for f in volume['frames']) for key in
                   ('baseline_tstates','tstates','delta_tstates','baseline_metadata_tstates','metadata_tstates','idle_stripes','idle_inner_stripes')})
            next_frame = end; save()
        if next_frame != len(states) and args.max_frames is None: raise AssertionError('missing ending')
        all_frames = [f for v in report['volumes'] for f in v['frames']]
        report.update(complete=args.limit is None and args.max_frames is None,checked_frames=len(all_frames),
            full_compact_and_both_native_exact=True,idle_masks_never_read_or_written=True,
            paired_baseline_frames=sum(min(args.paired,v['checked_frames']) for v in report['volumes']),
            **{key:sum(f[key] for f in all_frames) for key in
               ('baseline_tstates','tstates','delta_tstates','baseline_metadata_tstates','metadata_tstates','idle_stripes','idle_inner_stripes')},
            faster_frames=sum(f['delta_tstates']<0 for f in all_frames),slower_frames=sum(f['delta_tstates']>0 for f in all_frames),
            worst_regression_tstates=max(f['delta_tstates'] for f in all_frames),
            largest_saving_tstates=min(f['delta_tstates'] for f in all_frames))
    except Exception as exc: report['failure'] = repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in report.items() if k != 'volumes'}),flush=True)


if __name__ == '__main__': main()
