"""Execute run tags against every compact frame and both native screens.

Reference timings are the complete retained two-byte Huffman frame stage.
ZX0, packet transfer, queues, AY/IRQ cadence, ULA and disk are excluded.
Every measured delta must match the independently counted run paths.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_static_cache_borders import OPTIONS
from build_fap3_trd import sha
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from profile_frame_hotspots import install_hl_masks
import compact_cursor
import cached_huffman_lookahead as lookahead
import inline_huffman_patches as inline
import uncontended_frame as relocation
import tagged_noop_runs as tags

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory','states','output'): p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--minimum',type=int,default=4)
    p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.limit is not None and a.limit<1: p.error('--limit must be positive')
    reference=ROOT/'cached_huffman_lookahead_cpu.json'; old=json.loads(reference.read_bytes())
    if not old['complete'] or not old['full_compact_and_both_native_exact']: raise ValueError('incomplete baseline')
    # The saved baseline pins exact historical file bytes. Current source
    # pins below are normalized for portable Git LF/CRLF checkouts.
    for name,digest in {**old['source_sha256'],**old['baseline_source_sha256']}.items():
        raw=(ROOT/name).read_bytes()
        if digest not in (sha(raw),sha(raw.replace(b'\r\n',b'\n'))): raise ValueError(('reference source changed',name))
    with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
    if sha(states.tobytes())!=old['states_sha256']: raise ValueError('different states')
    names=('tagged_noop_runs.py','benchmark_tagged_noop_runs.py','test_tagged_noop_runs.py',
           *old['source_sha256'],*old['baseline_source_sha256'])
    report=dict(complete=False,release=False,scope=__doc__,minimum_run=a.minimum,
        baseline_commit='a84451d',reference_sha256=sha(reference.read_bytes()),
        states_sha256=old['states_sha256'],source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},
        disk_delivery_verified=False,volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for ref in old['volumes']:
            part,start,end=(ref[k] for k in ('part','start','end'))
            raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw)!=ref['raw_sha256']: raise ValueError('different raw')
            cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
            tables,mapping,packets=frames(cells); masks=serialized_masks(cells)
            reader=Reader(raw); _,_,count,_,_=read_header(reader,magic=b'FAP3')
            details=[read_packet(reader,stored_guards=False)[1] for _ in range(count)]; reader.end()
            h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,
                register_fragments=True,cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
            install_hl_masks(h); c=h.cpu; c.guarding=False
            if start: c.banks[5][0x2400:0x3300]=states[start-1].tobytes()
            for bank,index in ((7,start-2),(5,start-1)):
                if index>=0:
                    screen=display_screen(states[index].tobytes(),black_borders=True)
                    screen=bytes(6144)+screen[6144:]
                    c.banks[bank][:6912]=screen; h.expected_screens[bank]=screen
            relocation.install_stage(h); lookahead.install_frame(h)
            inline.install_stage(h,tables,mapping); compact_cursor.install_stage(h)
            implementation=tags.install_stage(h)
            row=dict(part=part,start=start,end=end,raw_sha256=sha(raw),implementation=implementation,frames=[])
            report['volumes'].append(row)
            for index in range(start,min(end,start+a.limit) if a.limit else end):
                local=index-start; group,native=packets[index]
                if start and local<2: native=b'\xff'*80
                tagged=(*group[:3],tags.encode(group[3],group[4],a.minimum),*group[4:])
                result=relocation.run_stage(h,tagged,native,states[index].tobytes(),local,masks[index],details[index]['cache'])
                prediction=tags.cycle_counts(group[3],group[4],a.minimum)
                before=ref['frames'][local]['tstates']; after=result['total_tstates']
                if after-before != prediction['delta_tstates']:
                    raise AssertionError(('frame cycle delta differs',part,index,before,after,prediction))
                row['frames'].append(dict(frame=index,baseline_tstates=before,tstates=after,
                    **prediction,stages=result['stages']))
                if local%100==0:
                    save(); print(f'Part {part}: {local+1}/{end-start} exact frames and cycles',flush=True)
            row['checked_frames']=len(row['frames'])
            for key in ('baseline_tstates','tstates','delta_tstates','runs','skipped_tiles','fast_fragments'):
                row[key]=sum(f[key] for f in row['frames'])
            save()
        report.update(complete=a.limit is None,full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            slower_frames=sum(f['delta_tstates']>0 for v in report['volumes'] for f in v['frames']))
        for key in ('baseline_tstates','tstates','delta_tstates','runs','skipped_tiles','fast_fragments'):
            report[key]=sum(v[key] for v in report['volumes'])
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()
    print(json.dumps({k:report[k] for k in ('complete','checked_frames','baseline_tstates','tstates','delta_tstates')}),flush=True)


if __name__=='__main__': main()
