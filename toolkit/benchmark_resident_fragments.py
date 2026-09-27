"""Execute every cost-selected frame with the retained complete CPU stage.

All compact bytes and both full native screens must match the original
states. Same opcode templates, tables and options as the complete baseline;
only encoded packets change. ZX0/queues/IRQ/ULA/ROM/disk are excluded here.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_static_cache_borders import OPTIONS
from build_fap3_trd import sha
from bulk_frame_stream import unpack as unpack_bulk,read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness,frames,serialized_masks,display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from profile_frame_hotspots import install_hl_masks
import compact_cursor
import cached_huffman_lookahead as lookahead
import inline_huffman_patches as inline
import uncontended_frame as relocation

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory','states','probe','output'): p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.limit is not None and a.limit<1: p.error('--limit must be positive')
    reference_path=ROOT/'cached_huffman_lookahead_cpu.json'; old=json.loads(reference_path.read_bytes())
    probe=json.loads(a.probe.read_bytes())
    if not old['complete'] or not old['full_compact_and_both_native_exact'] or not probe['complete']:
        raise ValueError('incomplete reference/probe')
    for name,digest in {**old['source_sha256'],**old['baseline_source_sha256']}.items():
        raw=(ROOT/name).read_bytes()
        if digest not in (sha(raw),sha(raw.replace(b'\r\n',b'\n'))): raise ValueError(('reference source changed',name))
    with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
    if not sha(states.tobytes())==old['states_sha256']==probe['states_sha256']: raise ValueError('different states')
    names=('benchmark_resident_fragments.py',*old['source_sha256'],*old['baseline_source_sha256'])
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        reference_sha256=sha(reference_path.read_bytes()),probe_sha256=sha(a.probe.read_bytes()),
        states_sha256=old['states_sha256'],player_opcode_templates_unchanged=True,
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},
        disk_delivery_verified=False,volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for ref,encoded in zip(old['volumes'],probe['volumes'],strict=True):
            part,start,end=(ref[k] for k in ('part','start','end'))
            if (part,start,end)!=tuple(encoded[k] for k in ('part','start','end')) or ref['raw_sha256']!=encoded['baseline_raw_sha256']:
                raise ValueError('volume ranges differ')
            raw=(a.raw_directory/encoded['raw_file']).read_bytes()
            if sha(raw)!=encoded['raw_sha256']: raise ValueError('different candidate')
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
            inlined=inline.install_stage(h,tables,mapping); compact_cursor.install_stage(h)
            row=dict(part=part,start=start,end=end,raw_sha256=sha(raw),baseline_raw_sha256=ref['raw_sha256'],
                inline_code_bytes=inlined['code_bytes'],frames=[])
            report['volumes'].append(row)
            for index in range(start,min(end,start+a.limit) if a.limit else end):
                local=index-start; group,native=packets[index]
                if start and local<2: native=b'\xff'*80
                actual=relocation.run_stage(h,group,native,states[index].tobytes(),local,masks[index],details[index]['cache'])
                before=ref['frames'][local]['tstates']; after=actual['total_tstates']
                row['frames'].append(dict(frame=index,baseline_tstates=before,tstates=after,
                    delta_tstates=after-before,stages=actual['stages']))
                if local%100==0:
                    save(); print(f'Part {part}: {local+1}/{end-start} exact compact and both native screens',flush=True)
            row['checked_frames']=len(row['frames'])
            for key in ('baseline_tstates','tstates','delta_tstates'): row[key]=sum(f[key] for f in row['frames'])
            save()
        report.update(complete=a.limit is None,full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            slower_frames=sum(f['delta_tstates']>0 for v in report['volumes'] for f in v['frames']))
        for key in ('baseline_tstates','tstates','delta_tstates'): report[key]=sum(v[key] for v in report['volumes'])
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()
    print(json.dumps({k:report[k] for k in ('complete','checked_frames','baseline_tstates','tstates','delta_tstates')}),flush=True)


if __name__=='__main__': main()
