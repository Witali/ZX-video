"""Compare native bitmap checkpoints with two complete initial redraws.

Builds real independent-boot TRDs (only if they fit), verifies every rewritten
packet byte, and optionally executes short paired Z80 profiles. These profiles
are explicitly partial; full disk timing must be measured separately in Fuse.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from build_fap3_trd import sha
from profile_fap3 import cpu_profile
from run_deferred_disk import ReadThroughBuilder
from zx0_codec import decompress


def verify_stream(builder, start, end):
    stream, blocks=builder.stream(start,end)
    decoded=bytearray(); offset=0
    while offset<len(stream):
        raw_size,packed_size=struct.unpack_from('<HH',stream,offset); offset+=4
        decoded+=decompress(stream[offset:offset+packed_size],limit=raw_size)
        offset+=packed_size
    first,last=builder.offsets[start],builder.offsets[end]
    expected=bytearray(builder.raw[first:last]); changed=[]
    if builder.cold_bitmaps and start:
        for frame in range(start,min(end,start+2)):
            pos=builder.native_map_offsets[frame]-first
            changed.extend(first+pos+i for i,x in enumerate(expected[pos:pos+80]) if x!=255)
            expected[pos:pos+80]=b'\xff'*80
    if decoded!=expected: raise AssertionError('packet bytes changed outside allowed native maps')
    return dict(exact_except_initial_native_maps=True,changed_byte_offsets=changed,
        decoded_sha256=sha(decoded),zx0_sha256=sha(stream),zx0_bytes=len(stream),blocks=len(blocks))


def weighted_ends(builder, volumes):
    weights=[0]
    for pos in range(0,len(builder.raw),8192):
        weights.append(weights[-1]+4+len(builder.compress(builder.raw[pos:pos+8192])))
    positions=[weights[o//8192]+(weights[min(o//8192+1,len(weights)-1)]-weights[o//8192])*(o%8192)/8192
        for o in builder.offsets]
    total=positions[-1]-positions[0]
    return [min(range(1,len(builder.states)),key=lambda i:abs(positions[i]-positions[0]-total*f/volumes))
        for f in range(1,volumes)]+[len(builder.states)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','zx0','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--ends',default='1269,2334,3195,4221')
    p.add_argument('--weighted-three',action='store_true')
    p.add_argument('--cpu-frames',type=int,default=8)
    args=p.parse_args()
    if args.cpu_frames<0: p.error('--cpu-frames must be nonnegative')
    raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    args.output.mkdir(parents=True,exist_ok=True); args.report.parent.mkdir(parents=True,exist_ok=True)
    builders=[]
    for cold in (False,True):
        builder=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',
            fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=cold)
        builder.read_cache=args.read_cache; builders.append(builder)
    ends=weighted_ends(builders[0],3) if args.weighted_three else [int(n) for n in args.ends.split(',')]
    if not ends or ends!=sorted(set(ends)) or ends[0]<=0 or ends[-1]!=len(states): p.error('invalid ends')
    report=dict(baseline_commit='e3cb024',complete=False,release=False,
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),frames=len(states),ends=ends,
        packet_byte_verification_complete=False,compact_frames_changed=False,ay_bytes_changed=False,
        player_machine_code_changed=False,new_ram_bytes=0,
        full_cpu_run=False,full_disk_run=False,physical_drive_verified=False,variants=[])
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    for builder in builders:
        name='cold-bitmaps' if builder.cold_bitmaps else 'baseline'
        directory=args.output/name; directory.mkdir(exist_ok=True); builder.ends=ends
        variant=dict(name=name,volumes=[],cpu=[]); report['variants'].append(variant)
        start=0; manifest=[]
        for part,end in enumerate(ends,1):
            print(f'Build {name}, part {part}: {start}..{end-1}',flush=True)
            image,meta=builder.volume(start,end,part)
            stem=f'ZX-video-optimized-preview_part{part:02}'
            (directory/(stem+'.json')).write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
            if image: (directory/(stem+'.trd')).write_bytes(image)
            manifest.append(dict(part=part,file=stem+'.trd',metadata=stem+'.json',
                frame_start=start,frame_end_exclusive=end,sha256=meta.get('trd_sha256')))
            row={k:meta[k] for k in ('part','frame_start','frame_end_exclusive','frames',
                'video_bytes','video_sectors','video_start_sector','video_physical_sectors',
                'layout_padding_sectors','used_sectors','free_sectors','sections','forced_native_map_frames')}
            row.update(fits=image is not None,trd_sha256=meta.get('trd_sha256'),
                stream_verification=verify_stream(builder,start,end))
            variant['volumes'].append(row); save()
            print(json.dumps({k:row[k] for k in ('part','video_bytes','used_sectors','free_sectors','fits')}),flush=True)
            if args.cpu_frames and start:
                stop=min(start+args.cpu_frames,end)
                print(f'CPU {name}: {start}..{stop-1} (partial disk)',flush=True)
                cpu=cpu_profile(builder,start,stop)
                # Keep executed histograms/listings in the evidence; absolute
                # and delta counts can be checked against the same Z80 table.
                target=directory/f'cpu_part{part:02}.json'
                target.write_text(json.dumps(cpu,indent=2)+'\n',encoding='utf-8')
                variant['cpu'].append({k:cpu[k] for k in ('complete','frame_start','frame_end_exclusive',
                    'frames','full_compact_and_native_comparison','ay_records_exact','played_ay_ticks',
                    'foreground_tstates','foreground_stages','irq_tstates','idle_tstates',
                    'audio_underruns','nominal_deadlines_met_with_ideal_disk','prime','runs',
                    'drain','publications','events')})
                save()
            start=end
        (directory/'volumes.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        variant['total_used_sectors']=sum(v['used_sectors'] for v in variant['volumes'])
        variant['all_fit']=all(v['fits'] for v in variant['volumes']); save()
    report['complete']=report['packet_byte_verification_complete']=True; save()


if __name__=='__main__': main()
