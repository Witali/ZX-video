"""Measure invisible attribute removal on one cached CB46 input scope.

Retain each original block's output range after deleted bytes are removed,
and require no larger compressed block or decoder CPU count. Host-only
evidence is not a release or a physical disk/timing claim.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from build_fap3_trd import sha
from convert_video import write_json
from dynamic_row_dictionary import decode_check
from inplace_zx0 import layout
from invisible_attribute_writes import transform_states, transform_stream, verify_rgb
from probe_adaptive_block_codecs import ExternalCodec
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','lzsa','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--fit-cpu-budget',action='store_true',help='reuse the verified two-byte-match fitter for slower blocks')
    p.add_argument('--frozen-frames',type=Path,help='JSON list of absolute frames whose original writes must be retained')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True)
    m=json.loads(a.metadata.read_bytes());work=a.metadata.parent/'work'/a.metadata.stem
    raw=(work/'codebook.raw').read_bytes();old_stream=(work/'codebook.stream').read_bytes()
    rows=json.loads((work/'rows.json').read_bytes())
    with np.load(work/'states.npz',allow_pickle=False) as saved:frames=saved['states']
    assert sha(frames.tobytes())==m['states_sha256']
    start,end=m['frame_start'],m['frame_end_exclusive']
    frozen=set(json.loads(a.frozen_frames.read_bytes())) if a.frozen_frames else set()
    if any(not isinstance(f,int) or not start<=f<end for f in frozen):raise ValueError('invalid frozen frame')
    states=transform_states(frames,start,end,frozen)
    rgb=verify_rgb(frames,states,start,end)
    candidate,mapping,details=transform_stream(raw,frames,states,start,end,frozen)
    proof=decode_check(candidate,states,start,end,rows)
    regions,z,native=resumable_lzsa2.build(core=m['decoder_labels']['start'],core_limit=0x8e80)
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'existing pinned LZSA2 executable')
    if a.fit_cpu_budget:
        from fit_lzsa2_cpu_budget import fit
        from lzsa2_distance_cost import Costs
        costs=Costs()
    report=dict(complete=False,release=False,baseline_commit='32c6649',metadata_sha256=sha(a.metadata.read_bytes()),
        scope=__doc__,start=start,end=end,frames=end-start,details=details,rgb_proof=rgb,proof=proof,
        frozen_frames=sorted(frozen),cpu_fitter_enabled=a.fit_cpu_budget,
        raw_sha256=sha(candidate),baseline_raw_sha256=sha(raw),baseline_stream_sha256=sha(old_stream),
        original_states_sha256=sha(frames.tobytes()),states_sha256=sha(states.tobytes()),
        row_dictionary_unchanged=True,cell_dictionary_unchanged=raw[:2056]==candidate[:2056],
        player_instructions_changed=False,bitmap_operations_unchanged=True,ay_changed=False,
        codec=codec.identity,blocks=[])
    stream=bytearray();at=out=0
    while at<len(old_stream):
        count,size=struct.unpack_from('<HH',old_stream,at);at+=4
        payload=old_stream[at:at+size];at+=size
        lo,hi=int(mapping[out]),int(mapping[out+count])
        old_part=raw[out:out+count];part=candidate[lo:hi];out+=count
        old_cpu=execute(regions,z,native,payload,old_part)
        coded=codec.encode_verified(part,None,cache)
        fitting=None
        if a.fit_cpu_budget:
            coded,_,fitting=fit(coded,part,size,old_cpu['tstates'],costs,regions,z,native)
        exact,inplace=lzsa2_stream.trace(coded,limit=len(part));assert exact==part
        place=layout(len(coded),len(part),inplace['minimum_input_start'],len(stream))
        assert place['sector_aligned_fits']
        lzsa2_stream.trace(coded,limit=len(part),input_start=place['input_start'])
        cpu=execute(regions,z,native,coded,part)
        block=dict(index=len(report['blocks']),raw_start=lo,raw_end=hi,decoded_bytes=len(part),
            compressed_bytes=len(coded),codec='lzsa2',sha256=sha(part),inplace_proof=inplace,
            inplace_layout=place,native=cpu,baseline_native=old_cpu,baseline_bytes=size,
            bytes_delta=len(coded)-size,decoder_delta_tstates=cpu['tstates']-old_cpu['tstates'],
            budget_met=len(coded)<=size and cpu['tstates']<=old_cpu['tstates'])
        if fitting is not None:block['cpu_budget_fit']=fitting
        report['blocks'].append(block)
        stream+=struct.pack('<HH',len(part),len(coded))+coded
        print(block['index'],block['bytes_delta'],'bytes;',block['decoder_delta_tstates'],'T;',block['budget_met'],flush=True)
        write_json(a.output/'report.json',report)
    assert at==len(old_stream) and out==len(raw)
    (a.output/'video.raw').write_bytes(candidate);(a.output/'video.stream').write_bytes(stream)
    write_json(a.output/'rows.json',rows);np.savez_compressed(a.output/'states.npz',states=states)
    report.update(complete=True,raw_bytes_before=len(raw),raw_bytes_after=len(candidate),
        stream_bytes_before=len(old_stream),stream_bytes_after=len(stream),stream_sha256=sha(stream),
        sectors_before=(len(old_stream)+255)//256,sectors_after=(len(stream)+255)//256,
        decoder_tstates_before=sum(b['baseline_native']['tstates'] for b in report['blocks']),
        decoder_tstates_after=sum(b['native']['tstates'] for b in report['blocks']),
        every_block_no_larger_or_slower=all(b['budget_met'] for b in report['blocks']),
        renderer_tstates_saved=-sum(d['attribute_stage_delta_tstates'] for d in details),
        removed_attribute_writes=sum(d['removed'] for d in details),
        source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('invisible_attribute_writes.py','probe_invisible_attributes.py','cell_codebook_z80.py','resumable_lzsa2.py')})
    report['host_candidate_eligible']=report['every_block_no_larger_or_slower'] and len(stream)<len(old_stream)
    write_json(a.output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('complete','stream_bytes_before','stream_bytes_after',
        'decoder_tstates_before','decoder_tstates_after','removed_attribute_writes','renderer_tstates_saved','host_candidate_eligible')}))


if __name__=='__main__':main()
