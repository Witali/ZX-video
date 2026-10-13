"""Trade selected two-byte matches for literals within each original CPU budget.

Use a smaller dictionary-numbered stream as the starting point. Dropping a
short match can save token dispatch at a small byte cost. Exact suffix costs
retain nibble phase and repeat-offset effects; independent native execution
decides whether each block meets its original decoding budget.
"""
import argparse
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from inplace_zx0 import layout
from lzsa2_distance_cost import Costs,mode
from lzsa2_oracle import encode,literal_extra,match_extra,offset_extra
from optimize_lzsa2_distances import parse
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2


from lzsa.budget import model, fit as _library_fit

def fit(payload,raw,byte_budget,cpu_budget,costs,regions,z,native,*,source=0x4000):
    return _library_fit(payload,raw,byte_budget,cpu_budget,costs,regions,z,native,
                        source=source,execute=execute)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('metadata','directory'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.metadata.read_bytes());report=json.loads((a.directory/'report.json').read_bytes())
    flat=report['variants']['flat'];source=a.directory/'flat';raw=(source/'video.raw').read_bytes();stream=(source/'video.stream').read_bytes()
    assert sha(a.metadata.read_bytes())==report['metadata_sha256'] and sha(stream)==flat['stream_sha256']
    costs=Costs();regions,z,native=resumable_lzsa2.build(core=m['decoder_labels']['start'],core_limit=0x8e80)
    at=out=0;result=bytearray();blocks=[];changes=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+size];at+=size
        data=raw[out:out+n];index=len(blocks);baseline=report['baseline_blocks'][index]
        coded,cpu,change=fit(payload,data,m['blocks'][index]['compressed_bytes'],baseline['tstates'],costs,regions,z,native)
        restored,proof=lzsa2_stream.trace(coded,limit=n);assert restored==data
        place=layout(len(coded),n,proof['minimum_input_start'],len(result));assert place['sector_aligned_fits']
        lzsa2_stream.trace(coded,limit=n,input_start=place['input_start'])
        blocks.append(dict(index=index,decoded_bytes=n,compressed_bytes=len(coded),native=cpu,
            inplace_layout=place,sha256=sha(data),codec='lzsa2',inplace_proof=proof,raw_start=out,raw_end=out+n))
        changes.append(change);result+=struct.pack('<HH',n,len(coded))+coded;out+=n
        print(index,len(coded)-size,'bytes;',cpu['tstates']-baseline['tstates'],'T vs original;',change['budget_met'],flush=True)
    assert out==len(raw)
    folder=a.directory/'budgeted';folder.mkdir(exist_ok=True)
    (folder/'video.raw').write_bytes(raw);(folder/'video.stream').write_bytes(result)
    (folder/'rows.json').write_bytes((source/'rows.json').read_bytes())
    cpu=sum(b['native']['tstates'] for b in blocks)
    row=dict(flat,bytes=len(result),sectors=(len(result)+255)//256,decoder_tstates=cpu,
        bytes_delta=len(result)-report['baseline_bytes'],decoder_delta_tstates=cpu-report['baseline_decoder_tstates'],
        stream_sha256=sha(result),blocks=blocks,changes=changes,
        every_block_within_original_byte_and_cpu_budget=all(c['budget_met'] for c in changes),
        host_candidate_eligible=len(result)<report['baseline_bytes'] and all(c['budget_met'] for c in changes))
    report['variants']['budgeted']=row;write_json(a.directory/'report.json',report)
    print({k:row[k] for k in ('bytes','sectors','bytes_delta','decoder_delta_tstates','host_candidate_eligible')})


if __name__=='__main__':main()
