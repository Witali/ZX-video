"""Measure real optimal ZX0 at different grid phases on all independent volumes.

Keep every FAP3/AY byte, tables, native cold-start maps and 8192-byte slot
limits. This measures storage only; CPU and sustained disk delivery must
be checked separately. Each candidate fully round-trips the volume packets.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import struct
import numpy as np
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from probe_two_level_fragments import compress_chunk
from zx0_block_phase import Builder,ranges


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw-directory','directory','states','zx0','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--phases',type=int,nargs='+',default=list(range(0,8192,1024)))
    p.add_argument('--jobs',type=int,default=4)
    args=p.parse_args()
    if args.jobs<1 or any(not 0<=phase<8192 for phase in args.phases):p.error('invalid workers or phases')
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    args.output.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    cache=args.output/'zx0';cache.mkdir(exist_ok=True)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='5bad85f',
        states_sha256=sha(states.tobytes()),compressor_sha256=sha(args.zx0.read_bytes()),
        block_size=8192,player_opcodes_changed=False,actual_cpu_measured=False,
        full_player_verified=False,volumes=[])
    def save():args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for part in (1,2,3):
            meta,original,old_blocks=disk_blocks(args.directory,part)
            raw=(args.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw)!=meta['raw_sha256'] or meta['states_sha256']!=result['states_sha256']:
                raise ValueError('wrong input')
            b=Builder(raw,states,args.zx0.resolve(),cache,cold_bitmaps=True)
            start,end=meta['frame_start'],meta['frame_end_exclusive']
            lo,hi=b.offsets[start],b.offsets[end]
            expected=b.stream_block(lo,hi,start,end)
            if b''.join(data for _,data in old_blocks)!=expected:raise AssertionError('baseline packet bytes differ')
            volume=dict(part=part,start=start,end=end,raw_sha256=sha(raw),packet_sha256=sha(expected),
                packet_bytes=len(expected),baseline_stream_bytes=len(original),baseline_stream_sha256=sha(original),
                variants=[])
            result['volumes'].append(volume);save()
            phases=sorted(set([0,lo%8192]+args.phases))
            for phase in phases:
                spans=list(ranges(lo,hi,phase));chunks=[b.stream_block(a,z,start,end) for a,z in spans]
                if b''.join(chunks)!=expected:raise AssertionError('reblocking changed packet bytes')
                pending={};stream=bytearray();sizes=[]
                with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                    for chunk in chunks:
                        digest=sha(chunk)
                        if digest not in pending:
                            pending[digest]=executor.submit(compress_chunk,chunk,args.zx0.resolve(),cache,args.read_cache)
                    for i,chunk in enumerate(chunks):
                        packed=pending[sha(chunk)].result()
                        if len(packed)>8192:raise ValueError('compressed block exceeds input slot')
                        stream+=struct.pack('<HH',len(chunk),len(packed))+packed
                        sizes.append(dict(raw_start=spans[i][0],decoded_bytes=len(chunk),zx0_bytes=len(packed),raw_sha256=sha(chunk)))
                        if (i+1)%64==0:print(f'ZX0 part {part}, phase {phase}: {i+1}/{len(chunks)} blocks',flush=True)
                if phase==0 and bytes(stream)!=original:raise AssertionError('phase zero does not reproduce baseline disk stream')
                row=dict(phase=phase,volume_start_aligned=phase==lo%8192,stream_bytes=len(stream),
                    stream_sha256=sha(stream),sectors=(len(stream)+255)//256,blocks=sizes,
                    delta_bytes=len(stream)-len(original),all_zx0_blocks_exact=True,packet_bytes_unchanged=True)
                volume['variants'].append(row);save()
                print(json.dumps({k:v for k,v in row.items() if k!='blocks'}),flush=True)
            chosen=min(volume['variants'],key=lambda v:(v['stream_bytes'],len(v['blocks']),v['phase']))
            volume.update(selected_phase=chosen['phase'],selected_stream_bytes=chosen['stream_bytes'],
                          delta_bytes=chosen['delta_bytes'])
            save()
        result.update(complete=True,frames=len(states),
            baseline_stream_bytes=sum(v['baseline_stream_bytes'] for v in result['volumes']),
            selected_stream_bytes=sum(v['selected_stream_bytes'] for v in result['volumes']),
            delta_bytes=sum(v['delta_bytes'] for v in result['volumes']))
    except Exception as exc:result['failure']=repr(exc);save();raise
    save();print(json.dumps({k:v for k,v in result.items() if k!='volumes'}),flush=True)


if __name__=='__main__':main()
