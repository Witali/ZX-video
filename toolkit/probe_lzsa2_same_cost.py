"""Minimize LZSA2 bytes without slowing any token, using a single saved window.

Only match distances may change. Commands retain their positions and lengths,
so decode quotas have identical token boundaries. Verify every 256-byte native
slice independently and recheck full in-place layout after changed block sizes.
"""
import argparse
import itertools
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from inplace_zx0 import layout
from lzsa2_distance_cost import Costs,mode
from lzsa2_oracle import encode,offset_extra
from optimize_lzsa2_distances import optimize,parse,candidates,body_units
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2


def tokens(rows,distances,tail,costs):
    used=last=0;result=[]
    for r,d in zip(rows,distances):
        result.append(costs.token(r['literals'],r['length'],mode(d,last),used&1))
        used+=body_units(r)+(0 if d==last else offset_extra(d));last=d
    return result+[costs.token(tail,0,7,used&1)]


def brute(costs):
    checked=alternatives=0
    for raw in (b'A'*10,b'AB'*6,b'ABC'*4,b'AABAABAAB',b'ABCDEFGHI'):
        positions=[p for p in range(1,len(raw)-1) if candidates(raw,p,2)]
        for count in range(4):
            for ps in itertools.combinations(positions,count):
                if any(b<a+2 for a,b in zip(ps,ps[1:])):continue
                choices=[candidates(raw,p,2) for p in ps]
                baseline=encode(raw,[(p,2,d[0]) for p,d in zip(ps,choices)])
                _,rows,tail=parse(baseline,len(raw));limits=tokens(rows,[d[0] for d in choices],tail,costs)
                best=None
                for ds in itertools.product(*choices):
                    coded=encode(raw,[(p,2,d) for p,d in zip(ps,ds)]);cycles=tokens(rows,ds,tail,costs)
                    assert lzsa2_stream.trace(coded,limit=len(raw))[0]==raw
                    alternatives+=1
                    if any(a>b for a,b in zip(cycles,limits)):continue
                    value=(len(coded),sum(cycles));best=value if best is None else min(best,value)
                result,r=optimize(baseline,len(raw),costs,objective='size-no-slower-tokens')
                assert (len(result),r['candidate_token_tstates'])==best
                checked+=1
    return dict(layouts=checked,alternatives=alternatives)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('stream','raw','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    costs=Costs();checks=brute(costs)
    stream=a.stream.read_bytes();raw=a.raw.read_bytes();at=out=0;result=bytearray();rows=[]
    regions,z,native=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80)
    report=dict(complete=False,release=False,scope=__doc__,brute=checks,blocks=rows,
        source_stream_sha256=sha(stream),source_raw_sha256=sha(raw),player_code_changed=False,
        native_code_sha256=sha(b''.join(b for _,b in regions)))
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4;payload=stream[at:at+size];at+=size
        expected=raw[out:out+n];out+=n
        coded,row=optimize(payload,n,costs,objective='size-no-slower-tokens')
        decoded,proof=lzsa2_stream.trace(coded,limit=n);assert decoded==expected
        place=layout(len(coded),n,proof['minimum_input_start'],len(result));assert place['sector_aligned_fits']
        lzsa2_stream.trace(coded,limit=n,input_start=place['input_start'])
        old=execute(regions,z,native,payload,expected);new=execute(regions,z,native,coded,expected)
        assert len(old['slices'])==len(new['slices']) and all(a<=b for a,b in zip(new['slices'],old['slices']))
        assert new['tstates']-old['tstates']==row['modeled_delta_tstates']
        row.update(index=len(rows),independent_baseline=old,independent_candidate=new,inplace_layout=place,proof=proof)
        rows.append(row);result+=struct.pack('<HH',n,len(coded))+coded
        write_json(a.output/'report.json',report)
        print(len(rows)-1,len(coded)-len(payload),'bytes;',new['tstates']-old['tstates'],'T',flush=True)
    assert out==len(raw) and at==len(stream)
    (a.output/'video.stream').write_bytes(result)
    report.update(complete=True,source_bytes=len(stream),candidate_bytes=len(result),saved_bytes=len(stream)-len(result),
        source_sectors=(len(stream)+255)//256,candidate_sectors=(len(result)+255)//256,
        candidate_sha256=sha(result),baseline_decoder_tstates=sum(r['independent_baseline']['tstates'] for r in rows),
        candidate_decoder_tstates=sum(r['independent_candidate']['tstates'] for r in rows),
        individual_tokens_and_slices_no_slower=True,native_cost_model=costs.rows,native=native,
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('probe_lzsa2_same_cost.py','optimize_lzsa2_distances.py','lzsa2_distance_cost.py','lzsa2_oracle.py','lzsa2_stream.py','resumable_lzsa2.py')})
    write_json(a.output/'report.json',report)
    print({k:report[k] for k in ('saved_bytes','source_sectors','candidate_sectors','baseline_decoder_tstates','candidate_decoder_tstates')})


if __name__=='__main__':main()
