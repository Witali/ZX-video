"""Compare verified ZX0 sizes and instruction-derived reconstruction deltas.

Reconstruction deltas are projections from tested exact instruction formulas.
Total input/ZX0 time is not inferred from bytes. No disk/cadence release claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header,OFFSETS
from probe_lossless_layouts import sha
from vector_run_stream import transcode
import causal_tile_z80 as machine


def packets(data):
    r = Reader(data); _,_,count,_,_ = read_header(r,magic=data[:4]); result=[]
    for _ in range(count):
        _,p = read_packet(r,stored_guards=False)
        start = sum(map(len,p['ticks']))+8
        result.append((p['payload'][start:start+192],
            restore(p['payload'][start+192:start+192+p['mask_bytes']],1,480,4)[:384]))
    r.end(); return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','cpu','storage','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--trial',type=Path,nargs=2,action='append',required=True,metavar=('RAW','STORAGE'))
    p.add_argument('--clock',type=Path,nargs=2,metavar=('OLD','NEW'))
    args = p.parse_args(); source = args.source.read_bytes()
    old = json.loads(args.cpu.read_text(encoding='utf-8'))
    storage = json.loads(args.storage.read_text(encoding='utf-8'))
    if not old['complete'] or not old['skip_noop_runs'] or old['raw_sha256'] != sha(source):
        raise ValueError('full FAP3 scanned baseline required')
    if not storage['complete'] or storage['input_sha256'] != sha(source): raise ValueError('wrong storage baseline')
    r = Reader(source); _,_,count,mapping,tables = read_header(r,magic=b'FAP3')
    before = packets(source); trials=[]
    options = dict(hybrid=True,skip_empty=True,intra_above=True,intra_extended=True,fast_fragments=True,
        unrolled_motion=True,split_literals=True,raw_attributes=True,selective_cache=True)
    old_code,_,_,old_regions = machine.build(tables,mapping,OFFSETS,skip_noop_runs=True,**options)
    old_aux = sum(len(blob) for base,blob in old_regions if 0x7a00 <= base < 0x7b00)
    for raw_path,storage_path in args.trial:
        raw = raw_path.read_bytes(); size = json.loads(storage_path.read_text(encoding='utf-8'))
        if transcode(raw,inverse=True)[0] != source: raise AssertionError('trial source differs')
        if not size['complete'] or size['input_sha256'] != sha(raw): raise ValueError('incomplete/mismatched storage')
        inplace = raw[:4] == b'FAP5'; after = packets(raw)
        for scan in (False,True):
            rows=[]; lengths=Counter()
            for index,((vectors,masks),(commands,restored_masks)) in enumerate(zip(before,after)):
                if masks != restored_masks: raise AssertionError('masks changed')
                lengths.update(v-128 for v in commands if 129 <= v <= 144)
                delta = (machine.encoded_run_delta_tstates(vectors,masks,commands=commands,inplace=inplace,scan_uncoded=scan)
                    -machine.noop_run_delta_tstates(vectors,masks))
                baseline = old['frames'][index]['stages']['reconstruct']
                rows.append(dict(index=index,baseline_tstates=baseline,projected_tstates=baseline+delta,delta_tstates=delta))
            code,labels,_,regions = machine.build(tables,mapping,OFFSETS,encoded_noop_runs='inplace' if inplace else True,
                skip_noop_runs=scan,**options)
            aux = sum(len(blob) for base,blob in regions if 0x7a00 <= base < 0x7b00)
            packed_bytes = size['zx0_with_headers_bytes']; old_bytes = storage['zx0_with_headers_bytes']
            trials.append(dict(input=raw_path.as_posix(),raw_sha256=sha(raw),format=raw[:4].decode(),scan_uncoded=scan,
                frames=count,exact_roundtrip=True,encoded_run_lengths=dict(sorted(lengths.items())),
                zx0_with_headers_bytes=packed_bytes,delta_storage_bytes=packed_bytes-old_bytes,
                delta_sectors=(packed_bytes+255)//256-(old_bytes+255)//256,
                preliminary_three_disk_margin=1937664-packed_bytes,
                code_bytes=len(code),auxiliary_code_bytes=aux,delta_code_bytes=len(code)+aux-len(old_code)-old_aux,
                code_end=labels['end'],run_code_end=labels['encoded_run_end'],
                reconstruction_baseline=sum(r['baseline_tstates'] for r in rows),
                reconstruction_projected=sum(r['projected_tstates'] for r in rows),
                reconstruction_delta=sum(r['delta_tstates'] for r in rows),
                slower_frames=sum(r['delta_tstates']>0 for r in rows),frame_deltas=rows))
    result = dict(scope=__doc__,complete=True,release=False,baseline_commit='2f8535e',
        source_sha256=sha(source),full_execution_measured=False,cadence_verified=False,disk_delivery_verified=False,
        always_noop_stripes=[stripe for stripe in range(12) if all(
            not any(v[stripe*16:stripe*16+16]) and not any(m[stripe*32:stripe*32+32]) for v,m in before)],
        border_stripes=[dict(stripe=stripe,nonzero_vectors=dict(Counter(
            code for v,m in before for code in v[stripe*16:stripe*16+16] if code)),
            nonzero_vector_frames=[i for i,(v,m) in enumerate(before) if any(v[stripe*16:stripe*16+16])],
            frames_with_corrections=sum(any(m[stripe*32:stripe*32+32]) for v,m in before)) for stripe in (0,11)],
        trials=trials)
    if args.clock:
        from assess_frame_jitter import assess
        left,right = [json.loads(path.read_text(encoding='utf-8')) for path in args.clock]
        if left['states_sha256'] != right['states_sha256']: raise ValueError('clock states differ')
        count = min(len(left['frames']),len(right['frames']))
        sums=[]
        for clock in (left,right):
            stages = Counter()
            for frame in clock['frames'][:count]: stages.update(frame['stages'])
            sums.append(stages)
        result['partial_clock'] = dict(matched_frames=count,old_complete=left['complete'],new_complete=right['complete'],
            old_stages=dict(sums[0]),new_stages=dict(sums[1]),
            stage_delta={stage:sums[1][stage]-sums[0][stage] for stage in sums[0].keys()|sums[1].keys()},
            total_foreground_delta=sum(sums[1].values())-sum(sums[0].values()),
            old_timing=assess(left['publications'][:count]),new_timing=assess(right['publications'][:count]),
            old_failure=left.get('failure'),new_failure=right.get('failure'),
            limit='Matched prefix only. Work decoded ahead may differ; no complete-movie or disk timing claim.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for row in trials: print(json.dumps({k:v for k,v in row.items() if k != 'frame_deltas'}))
    print('Always unchanged compact stripes:',result['always_noop_stripes'])
    print('Border stripe operations:',result['border_stripes'])
    if args.clock: print(json.dumps(result['partial_clock']))


if __name__ == '__main__': main()
