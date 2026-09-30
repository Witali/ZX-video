"""Compare ZX0 and LZSA2 bytes on the exact bounded row-video stream."""
import argparse,json,struct
from pathlib import Path
from build_fap3_trd import sha
from profile_fast_reservoir import payloads
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trd','metadata','lzsa','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    m=json.loads(a.metadata.read_text());video,baseline,_,ends=payloads(a.trd.read_bytes(),m)
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'local pinned codec_sources/lzsa checkout')
    stream=bytearray();rows=[]
    for i,(lo,hi) in enumerate(zip(ends,ends[1:])):
        raw=video[lo:hi];packed=codec.encode_verified(raw,None,a.output)
        (a.output/f'{i:03}.lzsa2').write_bytes(packed)
        stream+=struct.pack('<HH',len(raw),len(packed))+packed
        rows.append(dict(index=i,decoded_bytes=len(raw),packed_bytes=len(packed),raw_sha256=sha(raw),packed_sha256=sha(packed)))
    (a.output/'video.stream').write_bytes(stream);(a.output/'video.raw').write_bytes(video)
    result=dict(complete=True,release=False,scope=__doc__,frames=m['frames'],input_trd_sha256=sha(a.trd.read_bytes()),
        zx0_bytes=len(baseline),lzsa2_bytes=len(stream),lzsa2_sectors=(len(stream)+255)//256,
        codec=codec.identity,blocks=rows,raw_sha256=sha(video),stream_sha256=sha(stream))
    (a.output/'probe.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('blocks','codec','scope')}))


if __name__=='__main__':main()
