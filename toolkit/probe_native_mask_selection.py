"""Measure exact host-selected native maps with current resident AY/ZX0.

No Z80 instruction changes. Formula CPU savings are not full playback proof.
All packet bytes outside native maps and the entire AY stream stay exact.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from inplace_keepalive_player import Builder
from native_mask_selection import maps_for_states,rewrite
from probe_tagged_noop_runs import compress

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory','states','baseline-build','zx0','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args(); old=json.loads(a.baseline_build.read_bytes())
    with np.load(a.states,allow_pickle=False) as f: states=f['states']
    if not old['complete'] or sha(states.tobytes())!=old['contract']['states_sha256']:
        raise ValueError('incomplete or different baseline')
    baseline,chosen=maps_for_states(states)
    a.output.mkdir(parents=True,exist_ok=True); a.report.parent.mkdir(parents=True,exist_ok=True)
    names=('native_mask_selection.py','probe_native_mask_selection.py','probe_cell_output_masks.py',
        'cell_screen_z80.py','bulk_frame_stream.py','probe_tagged_noop_runs.py','inplace_zx0.py',
        'probe_two_level_fragments.py','inplace_keepalive_player.py','inplace_slot_player.py','resident_audio_player.py')
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()),states_sha256=sha(states.tobytes()),
        policy='minimum existing Gray-cell output T-states per visible band',
        player_opcodes_changed=False,pixel_changes=0,ay_changes=0,full_player_verified=False,
        all_n_minus_two_host_pixel_replay_exact=True,zx0_sha256=sha(a.zx0.read_bytes()),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},volumes=[])
    def save(): a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    start=0; save()
    try:
        for part,(end,ref) in enumerate(zip(old['contract']['ends'],old['volumes'],strict=True),1):
            raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw)!=old['contract']['raw_sha256'][part-1]: raise ValueError('different source')
            candidate,rows=rewrite(raw,baseline,chosen,start,end)
            path=a.output/f'volume-{part}.raw'; path.write_bytes(candidate)
            b=Builder(candidate,states,a.zx0.resolve(),a.output/'zx0',
                series_fingerprint=b'AYH1MASKPROBE1',**old['contract']['options'])
            video,sound=b.separated(start,end)
            if sha(sound)!=ref['audio_sha256']: raise AssertionError('resident AY differs')
            row=dict(part=part,start=start,end=end,frames=end-start,raw_file=path.name,
                raw_sha256=sha(candidate),baseline_raw_sha256=sha(raw),raw_bytes=len(candidate),
                raw_video_sha256=sha(video),video_raw_bytes=len(video),audio_sha256=sha(sound),
                only_native_map_bytes_changed=True,all_ay_records_exact=True,raw_packet_lengths_unchanged=True,
                changed_frames=sum(v['changed_bands']>0 for v in rows),changed_bands=sum(v['changed_bands'] for v in rows),
                predicted_frame_delta_tstates=sum(v['delta_tstates'] for v in rows),frame_predictions=rows)
            report['volumes'].append(row); save()
            print(json.dumps({k:row[k] for k in ('part','changed_frames','changed_bands','predicted_frame_delta_tstates')}),flush=True)
            stream,blocks=compress(video,a.zx0.resolve(),a.output/'zx0',a.read_cache,a.jobs)
            (a.output/f'part{part:02}.stream').write_bytes(stream); sectors=(len(stream)+255)//256
            row.update(compressed_stream_sha256=sha(stream),stream_bytes=len(stream),blocks=blocks,
                baseline_stream_bytes=ref['video_bytes'],stream_delta_bytes=len(stream)-ref['video_bytes'],
                video_sectors=sectors,extra_video_sectors=sectors-ref['video_sectors'],
                estimated_free_sectors=ref['free_sectors']-(sectors-ref['video_sectors']),
                bootstrap_growth_included=False,all_zx0_blocks_exact_and_inplace_safe=True)
            save(); print(json.dumps({k:row[k] for k in ('part','stream_bytes','stream_delta_bytes','estimated_free_sectors')}),flush=True)
            start=end
        report.update(complete=True,frames=start,stream_bytes=sum(v['stream_bytes'] for v in report['volumes']),
            stream_delta_bytes=sum(v['stream_delta_bytes'] for v in report['volumes']),
            predicted_frame_delta_tstates=sum(v['predicted_frame_delta_tstates'] for v in report['volumes']))
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()


if __name__=='__main__': main()
