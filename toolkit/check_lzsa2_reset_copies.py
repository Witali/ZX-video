"""Compare reset-placement packet copies with actual native bridge instructions.

Uses cost-only metadata derived from a validated stream, not a built disk.
Reproduces the retained fixed-block report before evaluating variable blocks.
"""
import argparse,json
from copy import deepcopy
from pathlib import Path
from build_five_level_test_trd import save
from build_fap3_trd import sha
from probe_lzsa2_resets import blocks
from verify_borrowed_literals import copy_cases
from inplace_zx0 import layout
import lzsa2_stream


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('work','metadata','baseline-cpu'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();meta=json.loads(a.metadata.read_bytes());raw=(a.work/'video.raw').read_bytes()
    saved=json.loads(a.baseline_cpu.read_bytes());probe=json.loads((a.work/'probe.json').read_bytes())
    assert saved['video_sha256']==sha(raw)==probe['input_raw_sha256']
    assert saved['metadata_sha256']==sha(a.metadata.read_bytes())
    old=copy_cases(meta,raw)
    assert old==saved['copy'], 'fixed-boundary verifier regression'
    candidate=deepcopy(meta);candidate['blocks']=[]
    for block in blocks((a.work/'video.stream').read_bytes()):
        n=block['end']-block['start'];data=block['payload'];decoded,proof=lzsa2_stream.trace(data,limit=n)
        assert decoded==raw[block['start']:block['end']]
        space=layout(len(data),n,proof['minimum_input_start'],block['stream_start'])
        candidate['blocks'].append(dict(raw_start=block['start'],raw_end=block['end'],decoded_bytes=n,
            codec='lzsa2',compressed_bytes=len(data),sha256=sha(decoded),inplace_proof=proof,inplace_layout=space))
    candidate['video_bytes']=probe['candidate_stream_bytes'];candidate['video_sectors']=probe['candidate_sectors']
    new=copy_cases(candidate,raw)
    save(a.work/'cost-metadata.json',candidate)
    result=dict(complete=True,release=False,scope=__doc__,baseline=old,candidate=new,
        copy_delta_tstates=new['tstates']-old['tstates'],
        baseline_borrowed_packets=old['borrowed_packets'],candidate_borrowed_packets=new['borrowed_packets'],
        frame_reconstruction_remeasured=False,producer_remeasured=False,
        decoder_plus_copy_delta_tstates=probe['decoder_delta_tstates']+new['tstates']-old['tstates'],
        raw_sha256=sha(raw),candidate_stream_sha256=probe['candidate_stream_sha256'])
    save(a.work/'copies.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('baseline','candidate','scope')}))


if __name__=='__main__':main()
