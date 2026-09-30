"""Deterministic native LZSA2 boundary cases with independent author round trips."""
import argparse,json,random,struct
from pathlib import Path
from unittest.mock import patch
import benchmark_inplace_slot as base
from benchmark_row_lzsa import fixture
from probe_adaptive_block_codecs import ExternalCodec
from inplace_zx0 import layout
import lzsa2_stream


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lzsa',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rng=random.Random(924);noise=lambda n:bytes(rng.randrange(256) for _ in range(n))
    cases=[(f'constant-{n}',b'Q'*n) for n in (1,2,3,17,18,237,238,239,255,256,257,15872)]
    cases += [(f'literals-{n}',noise(n)) for n in (3,17,18,237,238,239,256,15872)]
    for distance in (32,33,511,512,513,8704,8705):
        data=noise(distance);cases.append((f'distance-{distance}',data+data[:min(distance,7000)]))
    codec=ExternalCodec('lzsa2',a.lzsa.resolve(),a.lzsa.resolve(),'pinned local upstream LZSA2')
    stream=bytearray();blocks=[]
    for name,raw in cases:
        payload=codec.encode_verified(raw,None,a.output);decoded,proof=lzsa2_stream.trace(payload,limit=len(raw))
        if decoded!=raw:raise AssertionError(name)
        space=layout(len(payload),len(raw),proof['minimum_input_start'],len(stream))
        if not space['sector_aligned_fits']:raise AssertionError((name,space))
        lzsa2_stream.trace(payload,limit=len(raw),input_start=space['input_start'])
        stream+=struct.pack('<HH',len(raw),len(payload))+payload;blocks.append((name,payload,raw))
    h,report=fixture(stream,57,0x8de0,0x8ef7)
    with patch.object(base,'trace',lzsa2_stream.trace):
        for name,payload,raw in blocks:
            try:h.block(payload,raw,len(h.results),short=(len(h.results)==1))['case']=name
            except Exception as error:
                c=h.cpu;_,proof=lzsa2_stream.trace(payload,limit=len(raw))
                raise AssertionError(dict(case=name,input=c.input_reads,wanted_input=len(payload),
                    output=c.produced,wanted_output=len(raw),digest=c.digest.hexdigest(),
                    expected_digest=proof['write_input_cursors_sha256'])) from error
    result=h.finish();result.update(scope=__doc__,cases=h.results,release=False)
    (a.output/'edges.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=result['complete'],cases=len(blocks),sector_reads=result['sector_reads'])))


if __name__=='__main__':main()
