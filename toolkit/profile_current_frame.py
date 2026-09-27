"""Profile every instruction of the current direct-HL frame CPU prototype.

Execute all frames with exact compact/native comparisons. Reconstruct the
retained disk player's phase costs by adding its proven 21-T motion delta;
that reconstruction is distinguished from this fresh opcode execution.
No IRQ cadence, disk, ZX0, packet transport or ULA time is included.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from benchmark_direct_motion_target import (Harness, OPTIONS, Reader, display_screen,
    frames, install_hl_masks, read_header, read_packet, serialized_masks,
    unpack, unpack_audio, unpack_bulk, unpack_cache, sha)
from profile_frame_hotspots import instrument
import cached_huffman_lookahead as lookahead
import compact_cursor
import direct_motion_target as direct
import inline_huffman_patches as inline
import uncontended_frame as relocation

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-directory',type=Path,default=ROOT.parent/'.worktree/volume-huffman/.tmp/probe')
    p.add_argument('--states',type=Path,default=ROOT.parent/'.worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz')
    p.add_argument('--output',type=Path,default=ROOT/'current_frame_profile.json')
    p.add_argument('--limit',type=int)
    a = p.parse_args()
    if a.output.exists(): p.error('output already exists')
    if a.limit is not None and a.limit<1: p.error('positive limit required')
    ref = ROOT/'direct_motion_target_cpu.json'
    baseline = json.loads(ref.read_bytes())
    if not baseline['complete'] or not baseline['full_compact_and_both_native_exact']:
        raise ValueError('incomplete reference')
    sources = baseline['source_sha256'] | baseline['baseline_sources']
    for name,digest in sources.items():
        if sha((ROOT/name).read_bytes())!=digest: raise ValueError(('source changed',name))
    with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
    if sha(states.tobytes())!=baseline['states_sha256']: raise ValueError('states changed')
    sources.update({n:sha((ROOT/n).read_bytes()) for n in ('profile_current_frame.py','profile_frame_hotspots.py')})
    report = dict(complete=False,release=False,scope=__doc__,baseline_commit='f701c54',
        reference_sha256=sha(ref.read_bytes()),source_sha256=sources,states_sha256=baseline['states_sha256'],
        player_cpu_delta_tstates=0,stream_delta_bytes=0,actual_new_playback_measured=False,volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for v in baseline['volumes']:
            part,start,end=(v[k] for k in ('part','start','end'))
            raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw)!=v['raw_sha256']: raise ValueError('raw changed')
            cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
            tables,mapping,packets=frames(cells); masks=serialized_masks(cells)
            reader=Reader(raw); _,_,count,_,_=read_header(reader,magic=b'FAP3')
            details=[read_packet(reader,stored_guards=False)[1] for _ in range(count)]; reader.end()
            h=Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,
                register_fragments=True,cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
            install_hl_masks(h); c=h.cpu; c.guarding=False
            if start:c.banks[5][0x2400:0x3300]=states[start-1].tobytes()
            for bank,index in ((7,start-2),(5,start-1)):
                if index>=0:
                    screen=display_screen(states[index].tobytes(),black_borders=True)
                    screen=bytes(6144)+screen[6144:]; c.banks[bank][:6912]=screen; h.expected_screens[bank]=screen
            relocation.install_stage(h); lookahead.install_frame(h); direct.install_stage(h)
            generated=inline.install_stage(h,tables,mapping); compact_cursor.install_stage(h)
            hist,stages,fixed,bank6=instrument(h,generated)
            out=dict(part=part,start=start,end=end,raw_sha256=sha(raw),frames=[])
            report['volumes'].append(out); previous=Counter()
            for index in range(start,min(end,start+a.limit) if a.limit else end):
                local=index-start; group,native=packets[index]
                if start and local<2:native=b'\xff'*80
                actual=relocation.run_stage(h,group,native,states[index].tobytes(),local,masks[index],details[index]['cache'])
                delta=stages-previous; previous=stages.copy(); expected=v['frames'][local]
                if sum(delta.values())!=actual['total_tstates'] or actual['total_tstates']!=expected['tstates']:
                    raise AssertionError(('frame profile differs',part,index))
                retained=dict(delta)
                retained['reconstruct/motion']=retained.get('reconstruct/motion',0)-expected['delta_tstates']
                if sum(retained.values())!=expected['baseline_tstates']:raise AssertionError('baseline reconstruction differs')
                out['frames'].append(dict(frame=index,tstates=actual['total_tstates'],stages=dict(delta),
                    retained_baseline_tstates=expected['baseline_tstates'],retained_baseline_stages=retained))
                if local%200==0:
                    save(); print(f'part {part}: {local+1}/{end-start} exact frames/instruction profile',flush=True)
            rows=[]
            for (bank,pc,ticks),n in sorted(hist.items()):
                row=bank6[pc] if bank==6 and pc in bank6 else fixed[pc]
                rows.append(dict(bank=bank,address=pc,instruction=row['instruction'],
                    stage=row['phase']+'/'+row['stage'],tstates=ticks,count=n,total=ticks*n))
            total=sum(f['tstates'] for f in out['frames'])
            if sum(r['total'] for r in rows)!=total:raise AssertionError('instruction sum differs')
            out.update(checked_frames=len(out['frames']),tstates=total,stages=dict(stages),instruction_histogram=rows)
            save(); print(json.dumps(dict(part=part,tstates=total,stages=dict(stages))),flush=True)
        report.update(complete=a.limit is None,checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            tstates=sum(v['tstates'] for v in report['volumes']),full_compact_and_both_native_exact=True)
    except Exception as exc:
        report['failure']=repr(exc); save(); raise
    save()


if __name__=='__main__':main()
