"""Locate AY starvation relative to already decoded bytes in complete traces.

Counterfactual models retain the measured producer times and charge zero
audio scanning/copying CPU. They are opportunity bounds, not new Z80 playback.
All original records, including empty ticks, are retained in order. The
record FIFO is refilled only at observed foreground service boundaries.
"""
import argparse
from bisect import bisect_left, bisect_right
import gzip
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from zx0_codec import decompress

ROOT = Path(__file__).parent
FIELD = 70908


def prefix(event, ends):
    completed = len(ends)-1-event['blocks_left']
    if not 0 <= completed < len(ends): raise ValueError('invalid completed blocks')
    count = ends[completed]
    if event['phase'] == 2:
        if completed == len(ends)-1: raise ValueError('active beyond EOF')
        decoded = (event['slice_output']+8192)&65535
        if decoded > ends[completed+1]-count: raise ValueError('invalid active prefix')
        count += decoded
    return count


def fifo_model(tick_ends, points, opportunities, origin, capacity):
    """Free scanner/copy, frozen producer schedule, no old packet eviction cost."""
    times = sorted(set(opportunities))
    point_times = [p[0] for p in points]
    available = [p[1] for p in points]
    service = played = queued = gaps = 0
    misses = []
    field = 0
    while played < len(tick_ends):
        deadline = origin+field*FIELD
        while service < len(times) and times[service] < deadline:
            n = bisect_right(point_times,times[service])-1
            produced = available[n] if n >= 0 else 0
            queued = max(queued,min(bisect_right(tick_ends,produced),played+capacity))
            service += 1
        if played < queued:
            played += 1
        else:
            gaps += 1
            misses.append(field)
        field += 1
        # Once all input has arrived, permit zero-cost foreground service
        # after every field, including after the original trace's EOF.
        if service == len(times):
            queued = min(len(tick_ends),played+capacity)
        if field > len(tick_ends)+10000: raise ValueError('model did not terminate')
    return dict(capacity_records=capacity,storage_at_existing_32_byte_slots=capacity*32,
                extra_storage_vs_31_usable_slots=max(0,capacity-31)*32,
                underruns=gaps,fields=field,missed_field_indices=misses)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'audio_lookahead_profile.json')
    a = p.parse_args()
    reference_path = ROOT/'lookahead_player_summary.json'
    reference = json.loads(reference_path.read_bytes())
    manifest_path = ROOT/'streaming_zx0_input_evidence.json'
    manifest = json.loads(manifest_path.read_bytes())
    if not reference['complete'] or not manifest['complete']: raise ValueError('incomplete baseline')
    archives = []
    def archived(entry):
        path = ROOT/entry['directory']/entry['file']
        data = path.read_bytes()
        decoded = gzip.decompress(data)
        if sha(data)!=entry['sha256'] or sha(decoded)!=entry['uncompressed_sha256']:
            raise ValueError('archive differs')
        archives.append(entry)
        return decoded
    volumes = []
    for v, entry in zip(reference['volumes'],manifest['evidence'],strict=True):
        part = v['part']
        packed = (ROOT/'streaming_zx0_input_evidence'/entry['file']).read_bytes()
        stream = gzip.decompress(packed)
        if sha(packed)!=entry['sha256'] or sha(stream)!=v['lookahead']['stream_sha256']:
            raise ValueError('stream differs')
        def trace_file(suffix):
            return next(e for e in reference['evidence'] if e['file']==f'lookahead_part{part:02}'+suffix+'.gz')
        r = json.loads(archived(trace_file('.json')))
        meta_bytes = archived(trace_file('.metadata.json'))
        m = json.loads(meta_bytes)
        if (not r['complete'] or r['failure'] or r['errors'] or not r['ay_records_exact']
                or sha(meta_bytes)!=r['integrated_bootstrap_metadata_sha256']
                or r['frames']!=m['frames'] or r['debugger_installed_bytes']):
            raise ValueError('invalid complete playback')
        raw = bytearray(); ends = [0]; pos = 0
        while pos < len(stream):
            size,length = struct.unpack_from('<HH',stream,pos); pos += 4
            data = decompress(stream[pos:pos+length],limit=size); pos += length
            if len(data)!=size: raise ValueError('invalid decoded block')
            raw.extend(data); ends.append(len(raw))
        if pos!=len(stream) or len(ends)-1!=entry['blocks']: raise ValueError('block coverage differs')
        reader = Reader(bytes(raw)); ticks = []; tick_ends = []; packet_starts = []
        for i in range(m['frames']):
            start = reader.pos
            _,packet = read_packet(reader,stored_guards=False)
            at = start+2
            for tick in packet['ticks']:
                at += len(tick); tick_ends.append(at); ticks.append(tick)
                packet_starts.append(start)
        reader.end()
        if len(ticks)!=r['ay_ticks']: raise ValueError('AY coverage differs')
        points = []; calls = []; previous = 0
        events = r['queue_call_events']
        if len(events)%2: raise ValueError('unmatched queue calls')
        for begin,end in zip(events[::2],events[1::2],strict=True):
            lo,hi = prefix(begin,ends),prefix(end,ends)
            if lo!=previous or hi<lo or end['tstate']<begin['tstate']:
                raise ValueError('non-monotonic decoded prefix')
            points.extend([(begin['tstate'],lo),(end['tstate'],hi)])
            calls.append(dict(start=begin['tstate'],end=end['tstate'],before=lo,after=hi))
            previous = hi
        if previous!=len(raw): raise ValueError('producer did not reach EOF')
        byte_counts = [c['after'] for c in calls]
        point_times = [p[0] for p in points]
        origin = r['audio_tick_tstates'][0]//FIELD*FIELD
        rows = []
        for index,endpoint in enumerate(tick_ends):
            call = calls[bisect_left(byte_counts,endpoint)]
            rows.append(dict(tick=index,local_frame=index//6,packet_start=packet_starts[index],
                record_end=endpoint,record_hex=ticks[index].hex(),nominal_tstate=origin+index*FIELD,
                earliest_ready_tstate=call['start'],latest_ready_tstate=call['end']))
        starvation = []
        for at in r['audio_underrun_tstates']:
            played = bisect_right(r['audio_tick_tstates'],at)
            n = bisect_right(point_times,at)-1
            produced = points[n][1] if n>=0 else 0
            ready = bisect_right(tick_ends,produced)
            starvation.append(dict(tstate=at,next_record=played,decoded_prefix=produced,
                next_record_end=tick_ends[played],already_decoded_records=max(0,ready-played),
                certainly_not_decoded=rows[played]['earliest_ready_tstate']>at,
                inside_producing_call=rows[played]['earliest_ready_tstate']<=at<rows[played]['latest_ready_tstate']))
        opportunities = [p[0] for p in points]
        opportunities.extend(e['tstate'] for e in r['pipeline_events'])
        models = [fifo_model(tick_ends,points,opportunities,origin,capacity)
                  for capacity in (12,18,31,63,127,255)]
        row = dict(part=part,frames=m['frames'],ticks=len(ticks),audio_bytes=sum(map(len,ticks)),
            audio_sha256=sha(b''.join(ticks)),stream_sha256=sha(stream),baseline_underruns=r['audio_underruns'],
            underruns_with_next_record_already_decoded=sum(s['already_decoded_records']>0 for s in starvation),
            underruns_certainly_not_decoded=sum(s['certainly_not_decoded'] for s in starvation),
            underruns_inside_producing_call=sum(s['inside_producing_call'] for s in starvation),
            certainly_late_decoded_records=sum(t['earliest_ready_tstate']>t['nominal_tstate'] for t in rows),
            possibly_late_decoded_records=sum(t['latest_ready_tstate']>t['nominal_tstate'] for t in rows),
            models=models,records=rows,starvation=starvation)
        volumes.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('models','records','starvation')})
              +' models='+str([(c['capacity_records'],c['underruns']) for c in models]),flush=True)
    report = dict(complete=True,release=False,scope=__doc__,baseline_commit='8bc6a09',
        frames=sum(v['frames'] for v in volumes),ticks=sum(v['ticks'] for v in volumes),volumes=volumes,
        source_sha256={name:sha((ROOT/name).read_bytes()) for name in
                       ('profile_audio_lookahead.py','bulk_frame_stream.py','zx0_codec.py')},
        reference_sha256={path.name:sha(path.read_bytes()) for path in (reference_path,manifest_path)},
        evidence=archives,player_changed=False,new_z80_executed=False,new_disk_playback_measured=False,
        model_assumptions=['frozen measured producer schedule','zero scan, copy and paging CPU',
            'refill at observed foreground queue/pipeline boundaries','no raw slot eviction penalty',
            'original 50 Hz deadlines, every tick retained, no dropped/merged AY records'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__ == '__main__': main()
