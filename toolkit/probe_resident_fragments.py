"""Remeasure the historical fast-fragment selector with current resident AY/ZX0.

Keep its 64-bit local allowance and 400-T heuristic threshold. The old
150-T/symbol heuristic is a ranking estimate, not a bound for today's
two-byte Huffman decoder. Only actual Z80 execution can establish a saving.
Every source frame and AY record is verified independently after encoding.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from inplace_keepalive_player import Builder
from probe_fragment_cost_selection import Selector
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_tagged_noop_runs import compress
from reencode_bounded_fragments import encode,validate

ROOT=Path(__file__).parent


def packets(raw):
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3'); header=raw[:r.pos]
    result=[read_packet(r,stored_guards=False)[1] for _ in range(count)]
    r.end(); return header,result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory','states','baseline-build','zx0','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args(); baseline=json.loads(a.baseline_build.read_bytes())
    with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
    if not baseline['complete'] or sha(states.tobytes())!=baseline['contract']['states_sha256']:
        raise ValueError('incomplete baseline or different states')
    historical_path=ROOT/'fragment_cost_selection_probe.json'; historical=json.loads(historical_path.read_bytes())
    historical64=next(v for v in historical['variants'] if v['allowance_bits']==64)
    a.output.mkdir(parents=True,exist_ok=True); a.report.parent.mkdir(parents=True,exist_ok=True)
    names=('probe_resident_fragments.py','probe_fragment_cost_selection.py','reencode_bounded_fragments.py',
           'probe_tagged_noop_runs.py','inplace_zx0.py','probe_two_level_fragments.py',
           'inplace_keepalive_player.py','resident_audio_player.py','inplace_slot_player.py')
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()),historical_probe_sha256=sha(historical_path.read_bytes()),
        states_sha256=sha(states.tobytes()),allowance_bits=64,minimum_heuristic_gain=400,
        player_opcodes_changed=False,zx0_sha256=sha(a.zx0.read_bytes()),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},volumes=[])
    def save(): a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save(); start=0
    try:
        for part,(end,ref) in enumerate(zip(baseline['contract']['ends'],baseline['volumes'],strict=True),1):
            source=(a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(source)!=baseline['contract']['raw_sha256'][part-1]: raise ValueError('different source')
            print(f'Part {part}: exact baseline re-encode',flush=True)
            control,_=encode(source,states)
            if control!=source: raise AssertionError('baseline replay is not byte-identical')
            selector=Selector(start,end,64,400)
            candidate,detail=encode(source,states,fragment_selector=selector)
            old_audio=validate(source,states); new_audio=validate(candidate,states)
            if old_audio!=new_audio: raise AssertionError('AY records changed')
            header,before=packets(source); new_header,after=packets(candidate)
            if header!=new_header: raise AssertionError('Huffman header changed')
            for index,(old,new) in enumerate(zip(before,after,strict=True)):
                if old['ticks']!=new['ticks']: raise AssertionError('packet AY differs')
                if not start<=index<end and old['payload']!=new['payload']:
                    raise AssertionError('modified a frame outside its volume')
            if part==3 and sha(candidate)!=historical64['sha256']:
                raise AssertionError('does not reproduce historical allowance-64 candidate')
            path=a.output/f'volume-{part}.raw'; path.write_bytes(candidate)
            b=Builder(candidate,states,a.zx0.resolve(),a.output/'zx0',
                      series_fingerprint=b'AYH1FRAGPROBE1',**baseline['contract']['options'])
            video,sound=b.separated(start,end)
            if sha(sound)!=ref['audio_sha256']: raise AssertionError('resident audio changed')
            stream,blocks=compress(video,a.zx0.resolve(),a.output/'zx0',a.read_cache,a.jobs)
            (a.output/f'part{part:02}.stream').write_bytes(stream)
            sectors=(len(stream)+255)//256
            row=dict(part=part,start=start,end=end,frames=end-start,raw_file=path.name,
                baseline_raw_sha256=sha(source),raw_sha256=sha(candidate),raw_bytes=len(candidate),
                baseline_reencode_exact=True,all_source_frames_scalar_exact=True,all_ay_records_exact=True,
                huffman_header_unchanged=True,outside_volume_packets_unchanged=True,
                historical64_exact=part==3,selected_tiles=len(selector.rows),
                selected_frames=len({r['frame'] for r in selector.rows}),modes=dict(Counter(r['new_mode'] for r in selector.rows)),
                heuristic_saved_tstates=sum(r['heuristic_saved_tstates'] for r in selector.rows),
                selections=selector.rows,max_source_packet_bytes=max(len(r['payload']) for r in after),
                video_raw_bytes=len(video),raw_video_sha256=sha(video),audio_sha256=sha(sound),
                compressed_stream_sha256=sha(stream),stream_bytes=len(stream),baseline_stream_bytes=ref['video_bytes'],
                stream_delta_bytes=len(stream)-ref['video_bytes'],video_sectors=sectors,
                extra_video_sectors=sectors-ref['video_sectors'],estimated_free_sectors=ref['free_sectors']-(sectors-ref['video_sectors']),
                bootstrap_growth_included=False,all_zx0_blocks_exact_and_inplace_safe=True,blocks=blocks)
            report['volumes'].append(row); save()
            print(json.dumps({k:row[k] for k in ('part','selected_tiles','selected_frames','stream_bytes',
                'stream_delta_bytes','video_sectors','estimated_free_sectors')}),flush=True)
            start=end
        report.update(complete=True,frames=start,pixel_changes=0,ay_changes=0,
            stream_bytes=sum(v['stream_bytes'] for v in report['volumes']),
            stream_delta_bytes=sum(v['stream_delta_bytes'] for v in report['volumes']))
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()


if __name__=='__main__': main()
