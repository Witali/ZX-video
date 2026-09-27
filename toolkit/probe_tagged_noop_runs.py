"""Lossless interior run tags: current three-volume byte and cycle tradeoff.

ZX0 uses the retained in-place player's 15872-byte video-only blocks.
Frame CPU deltas are predictions until the native benchmark confirms them.
Compression, host inverses and in-place safety do not establish playback.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from inplace_slot_input_z80 import MAX_OUTPUT
from inplace_zx0 import trace, layout
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from probe_two_level_fragments import compress_chunk
from tagged_noop_runs import encode, cycle_counts, decode_vectors

ROOT = Path(__file__).parent


def volume(raw, start, end, minimum):
    r = Reader(raw); _,_,count,_,_ = read_header(r, magic=b'FAP3')
    original, tagged, audio, rows = bytearray(), bytearray(), bytearray(), []
    alternatives = {m:Counter() for m in (1,2,3,4,6,8,12,16)}
    if not 0 <= start < end <= count: raise ValueError('invalid range')
    for index in range(count):
        _, packet = read_packet(r, stored_guards=False)
        if not start <= index < end: continue
        ticks = b''.join(packet['ticks']); audio += ticks
        body = packet['payload'][len(ticks):]
        if start and index < start+2:
            at = 200+packet['mask_bytes']
            body = body[:at]+b'\xff'*80+body[at+80:]
        vectors = body[8:200]
        masks = restore(body[200:200+packet['mask_bytes']],1,480,4)[:384]
        new = encode(vectors,masks,minimum)
        candidate = body[:8]+new+body[200:]
        recovered = candidate[:8]+decode_vectors(candidate[8:200],masks,inplace=True)[0]+candidate[200:]
        if recovered != body: raise AssertionError('video packet roundtrip differs')
        original += struct.pack('<H',len(body))+body
        tagged += struct.pack('<H',len(candidate))+candidate
        for m, stats in alternatives.items(): stats.update(cycle_counts(vectors,masks,m))
        rows.append(dict(frame=index,**cycle_counts(vectors,masks,minimum)))
    r.end()
    if len(original) != len(tagged): raise AssertionError('packet lengths changed')
    return bytes(original), bytes(tagged), dict(start=start,end=end,frames=end-start,
        original_video_sha256=sha(original), tagged_video_sha256=sha(tagged),
        raw_video_bytes=len(tagged), raw_video_delta_bytes=0, ay_records=6*(end-start),
        ay_records_sha256=sha(audio), exact_packet_inverse=True,
        frame_cycle_predictions=rows, thresholds={m:dict(stats) for m,stats in alternatives.items()})


def compress(data, executable, cache, read_cache, jobs):
    cache.mkdir(parents=True,exist_ok=True)
    chunks=[data[i:i+MAX_OUTPUT] for i in range(0,len(data),MAX_OUTPUT)]
    stream=bytearray(); blocks=[]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures={sha(raw):pool.submit(compress_chunk,raw,executable,cache,read_cache)
                 for raw in {sha(c):c for c in chunks}.values()}
        for index,raw in enumerate(chunks):
            payload=futures[sha(raw)].result(); exact,proof=trace(payload,limit=len(raw))
            plan=layout(len(payload),len(raw),proof['minimum_input_start'],len(stream))
            if exact != raw or not plan['sector_aligned_fits']:
                raise AssertionError(('unsafe or inexact in-place block',index))
            blocks.append(dict(index=index,decoded_bytes=len(raw),zx0_bytes=len(payload),
                raw_sha256=sha(raw),zx0_sha256=sha(payload),inplace_layout=plan))
            stream += struct.pack('<HH',len(raw),len(payload))+payload
            if index%16 == 0: print(f'ZX0 blocks {index+1}/{len(chunks)} exact',flush=True)
    return bytes(stream),blocks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory','baseline-build','output','zx0','cache'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--minimum',type=int,default=4)
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--skip-compression',action='store_true')
    a=p.parse_args(); baseline=json.loads(a.baseline_build.read_bytes())
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()),minimum_run=a.minimum,
        source_sha256_lf={name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('tagged_noop_runs.py','probe_tagged_noop_runs.py','vector_run_stream.py',
             'probe_fast_noop_scan.py','inplace_zx0.py','probe_two_level_fragments.py')},
        zx0_sha256=sha(a.zx0.read_bytes()),native_frame_cpu_verified=False,
        disk_delivery_verified=False,volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save(); start=0
    try:
        for part,(end,ref) in enumerate(zip(baseline['contract']['ends'],baseline['volumes'],strict=True),1):
            raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != baseline['contract']['raw_sha256'][part-1]: raise ValueError('different input')
            old,new,row=volume(raw,start,end,a.minimum)
            if sha(old) != ref['raw_video_sha256']: raise AssertionError('baseline separated video differs')
            row.update(part=part,raw_sha256=sha(raw)); report['volumes'].append(row); save()
            print(json.dumps(dict(part=part,thresholds=row['thresholds'])),flush=True)
            if not a.skip_compression:
                stream,blocks=compress(new,a.zx0.resolve(),a.cache,a.read_cache,a.jobs)
                sectors=(len(stream)+255)//256
                row.update(compressed_stream_sha256=sha(stream),blocks=blocks,
                    compressed_stream_bytes=len(stream),baseline_stream_bytes=ref['video_bytes'],
                    compressed_delta_bytes=len(stream)-ref['video_bytes'],video_sectors=sectors,
                    baseline_video_sectors=ref['video_sectors'],extra_video_sectors=sectors-ref['video_sectors'],
                    estimated_free_sectors=ref['free_sectors']-(sectors-ref['video_sectors']),
                    bootstrap_growth_included=False,all_blocks_exact_and_inplace_safe=True)
            start=end; save()
        report.update(complete=True,frames=start,compression_measured=not a.skip_compression,
            thresholds={m:{key:sum(v['thresholds'][m][key] for v in report['volumes'])
                           for key in report['volumes'][0]['thresholds'][m]}
                        for m in report['volumes'][0]['thresholds']})
    except Exception as exc:
        report['failure']=repr(exc); raise
    finally: save()
    print(json.dumps({k:v for k,v in report.items() if k not in ('volumes','source_sha256_lf','scope')}),flush=True)


if __name__ == '__main__': main()
