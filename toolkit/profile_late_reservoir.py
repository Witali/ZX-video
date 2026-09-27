"""Measure decoded reserve and work in the retained player's late runs.

This is an audit of complete archived Fuse playback, not a changed player.
Queue positions are reconstructed from every exact video packet and block.
Stage elapsed time includes IRQ and contention; disk service is separately
intersected and must not be added again. Saved deterministic frame CPU is
reported separately. No counterfactual timing is claimed as a release.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
import disk_layout
from profile_integrated_timing import analyze, stats, FIELD, PERIOD
from summarize_native_mask_selection import read_archive
from zx0_codec import decompress

ROOT = Path(__file__).parent
OUTPUT = ROOT/'late_reservoir_profile.json'


def window(frames, lo, hi):
    rows = frames[lo:hi]
    stage = {name:sum(r['stages'][name]['elapsed'] for r in rows)
             for name in ('transfer','metadata','prepare','draw')}
    io = {name:sum(r['stages'][name]['disk_service'] for r in rows) for name in stage}
    return dict(start=rows[0]['frame'],end_exclusive=rows[-1]['frame']+1,frames=len(rows),
        nominal_budget_tstates=len(rows)*PERIOD,work_elapsed_tstates=sum(stage.values()),
        work_excess_tstates=sum(stage.values())-len(rows)*PERIOD,
        stages_elapsed_tstates=stage,disk_service_within_stages_tstates=io,
        deterministic_frame_cpu_tstates=sum(r['stage_cpu_reference'] for r in rows),
        packet_bytes=sum(r['packet_bytes'] for r in rows),
        minimum_decoded_reserve=min(r['decoded_available_at_packet'] for r in rows),
        maximum_decoded_reserve=max(r['decoded_available_at_packet'] for r in rows),
        packets_with_zero_completed_slots=sum(r['queue_count_at_packet']==0 for r in rows),
        packet_start_phases=dict(Counter(r['producer_phase'] for r in rows)),
        maximum_late_fields=max(r['late_fields'] for r in rows),
        maximum_transfer_tstates=max(r['stages']['transfer']['elapsed'] for r in rows))


def payloads(image, m):
    start = m['video_start_sector']
    stream = b''.join(image[(start+n)*256:(start+n+1)*256]
        for n in disk_layout.positions(m['video_sectors'],start%16))[:m['video_bytes']]
    video = bytearray(); block_ends = [0]; at = 0
    while at < len(stream):
        size,packed = struct.unpack_from('<HH',stream,at); at += 4
        raw = decompress(stream[at:at+packed],limit=size); at += packed
        video.extend(raw); block_ends.append(len(video))
    if at != len(stream): raise ValueError('trailing compressed video')
    positions = [0]
    while positions[-1] < len(video):
        at = positions[-1]
        size = int.from_bytes(video[at:at+2],'little')
        minimum = m['resident_audio']['packet_minimum_bytes']
        maximum = m['resident_audio']['packet_maximum_bytes']
        if not minimum <= size <= maximum or at+2+size > len(video): raise ValueError('invalid video-only packet')
        positions.append(at+2+size)
    if len(positions)-1 != m['frames']: raise ValueError('packet coverage differs')
    return bytes(video),stream,positions,block_ends


def projected_free_transfer(frames):
    """Optimistic frozen-duration sensitivity: two-stage pipeline, free input.

    Reuse actual metadata/prepare/draw durations but remove transfer and
    control/wait work. Contention/IRQ phase would change in a real player;
    this is NOT a proven lower bound or an implemented schedule.
    """
    now = 0; late = []
    for i in range(1,len(frames)):
        now = max(now,(i-1)*PERIOD)+frames[i]['stages']['draw']['elapsed']
        deviation = max(0,now-i*PERIOD)
        if deviation: late.append(dict(frame=frames[i]['frame'],deviation_tstates=deviation))
        if i+1 < len(frames):
            now += sum(frames[i+1]['stages'][s]['elapsed'] for s in ('metadata','prepare'))
    return dict(estimated_only=True,release=False,input_and_control_work_removed=True,
        durations_frozen_from_original_run=True,late_frames=len(late),
        worst=max(late,key=lambda r:r['deviation_tstates']) if late else None,
        rows=late)


def summarize():
    ref_names = ('inplace_keepalive_build.json','inplace_keepalive_summary.json',
                 'cached_huffman_lookahead_cpu.json','optional_packet_build.json',
                 'inplace_keepalive_evidence/manifest.json','optional_packet_evidence/manifest.json')
    refs = {n:sha((ROOT/n).read_bytes()) for n in ref_names}
    build,baseline,cpu,new_build = [json.loads((ROOT/n).read_bytes()) for n in ref_names[:4]]
    if not all(r['complete'] for r in (build,baseline,cpu,new_build)):
        raise ValueError('incomplete reference')
    if baseline['references']['manifest.json'] != refs['inplace_keepalive_evidence/manifest.json']:
        raise ValueError('baseline archive changed')
    old = read_archive(ROOT/'inplace_keepalive_evidence',packed_sizes=False)
    archive = read_archive(ROOT/'optional_packet_evidence')
    volumes = []
    for part in (1,2,3):
        stem = f'part{part:02}'; m = json.loads(old[stem+'.metadata.json']); trace = json.loads(old[stem+'.json'])
        image = archive[stem+'.trd']; new_m = json.loads(archive[stem+'.metadata.json'])
        b = build['volumes'][part-1]; ref = cpu['volumes'][part-1]
        if (sha(image) != new_build['volumes'][part-1]['trd_sha256'] or
                trace['trd_sha256'] != b['trd_sha256'] or
                m['raw_sha256'] != ref['raw_sha256'] or ref['checked_frames'] != m['frames']):
            raise ValueError('different playback or CPU input')
        video,stream,positions,ends = payloads(image,new_m)
        if sha(video) != b['raw_video_sha256'] or sha(stream) != b['stream_sha256']:
            raise ValueError('experimental image must supply identical video bytes')
        if [(b['raw_start'],b['raw_end']) for b in m['blocks']] != list(zip(ends,ends[1:])):
            raise ValueError('block layout differs')
        profile = analyze(trace,m,ref); frames = profile.pop('frames')
        starts = [e for e in trace['pipeline_events'] if e['kind']=='packet_start']
        for i,(row,event) in enumerate(zip(frames,starts,strict=True)):
            completed = len(ends)-1-event['blocks_left']
            block = bisect_right(ends,positions[i])-1
            available = ends[completed]-positions[i]
            if event['phase']==2: available += event['slice_output']-0xc000
            if (event['count'] != completed-block or event['position'] != positions[i]-ends[block]
                    or not 0 <= available <= 3*15872 or event['phase'] not in (0,1,2)
                    or event['count']+(event['phase']!=0)>3):
                raise ValueError(('queue ownership/position differs',part,i,event,completed,block,available))
            row.update(packet_bytes=positions[i+1]-positions[i],decoded_available_at_packet=available,
                fully_decoded_future_packets=max(0,bisect_right(positions,positions[i]+available)-1-i),
                producer_phase=event['phase'],completed_blocks=completed,consumer_block=block,
                raw_position=positions[i])
        pressure = [dict(index=i,raw_start=lo,raw_end=hi,raw_bytes=hi-lo,
            late_packet_bytes=0,bytes_requested_without_completed_slot=0)
            for i,(lo,hi) in enumerate(zip(ends,ends[1:]))]
        for i,row in enumerate(frames):
            at,end=positions[i],positions[i+1]
            while at<end:
                block=bisect_right(ends,at)-1; stop=min(end,ends[block+1]); amount=stop-at
                pressure[block]['late_packet_bytes']+=amount*bool(row['late_fields'])
                pressure[block]['bytes_requested_without_completed_slot']+=amount*(row['queue_count_at_packet']==0)
                at=stop
        runs = []
        for run in baseline['volumes'][part-1]['keepalive']['late_runs']:
            lo,hi = run['start'],run['end']+1
            peak = max(range(lo,hi),key=lambda i:frames[i]['late_fields'])
            runs.append(dict(local_start=lo,local_end_exclusive=hi,recovered_at=run['recovered_at'],
                through_peak=window(frames,lo,peak+1),whole_run=window(frames,lo,hi),
                before_run=window(frames,max(0,lo-32),lo) if lo else None))
        windows = []
        for size in (1,4,8,16,32,64,128):
            prefix = [0]
            for r in frames: prefix.append(prefix[-1]+r['work_elapsed'])
            lo = max(range(len(frames)-size+1),key=lambda i:prefix[i+size]-prefix[i])
            windows.append(window(frames,lo,lo+size))
        volumes.append(dict(part=part,baseline_profile=profile,late_runs=runs,worst_work_windows=windows,
            block_pressure=pressure,
            packets_without_completed_slot=sum(r['queue_count_at_packet']==0 for r in frames),
            packets_with_at_most_six_ready_bytes=sum(r['decoded_available_at_packet']<=6 for r in frames),
            decoded_reserve=stats([r['decoded_available_at_packet'] for r in frames]),
            decoded_future_packets=stats([r['fully_decoded_future_packets'] for r in frames]),
            frozen_free_transfer=projected_free_transfer(frames),frames=frames))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='a84451d',
        frames=sum(len(v['frames']) for v in volumes),references=refs,
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('profile_late_reservoir.py','profile_integrated_timing.py','summarize_native_mask_selection.py')},
        deterministic_player_cpu_delta_tstates=0,stream_delta_bytes=0,player_changed=False,
        physical_drive_verified=False,volumes=volumes)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write',action='store_true'); a = p.parse_args()
    result = json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif json.loads(OUTPUT.read_bytes()) != result: raise ValueError('saved profile differs')
    for v in result['volumes']:
        print(json.dumps(dict(part=v['part'],decoded_reserve=v['decoded_reserve'],
            decoded_future_packets=v['decoded_future_packets'],
            free_transfer={k:x for k,x in v['frozen_free_transfer'].items() if k!='rows'},
            worst32=next(r for r in v['worst_work_windows'] if r['frames']==32))),flush=True)


if __name__ == '__main__': main()
