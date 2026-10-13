"""Compatibility import for the reusable LZSA library."""
import codec_libraries  # Locate source packages in repository checkouts.
from lzsa.distances import *
import argparse, json, struct
from pathlib import Path
from build_five_level_test_trd import save

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stream','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--block',type=int,default=11)
    a=p.parse_args();stream=a.stream.read_bytes();at=0;blocks=[];raw=bytearray()
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+size];at+=size
        blocks.append((n,payload));raw.extend(lzsa2_stream.trace(payload,limit=n)[0])
    n,payload=blocks[a.block];costs=Costs();result,report=optimize(payload,n,costs)
    candidate=bytearray()
    for i,(size,data) in enumerate(blocks):
        if i==a.block:data=result
        candidate+=struct.pack('<HH',size,len(data))+data
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'video.stream').write_bytes(candidate);(a.output/'video.raw').write_bytes(raw)
    report.update(block=a.block,native_cost_model=costs.rows,native=costs.native,
        baseline_stream_sha256=sha(stream),candidate_stream_sha256=sha(candidate))
    save(a.output/'probe.json',report)
    print(json.dumps({k:report[k] for k in ('commands','candidate_distances','peak_states','baseline_bytes',
        'candidate_bytes','modeled_delta_tstates','changed_distances','seconds')}),flush=True)


if __name__=='__main__':main()
