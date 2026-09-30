"""Compare the exact short-input LZSA2 oracle with the pinned author encoder.

One finite corpus: exhaustive small binary strings, seeded repeated/mutated
inputs and short excerpts of saved video. No whole-movie parameter sweep.
"""
import argparse,gzip,itertools,json,random,struct,time
from pathlib import Path
from unittest.mock import patch
import benchmark_inplace_slot as banked
from benchmark_row_lzsa import fixture
from build_fap3_trd import sha
from build_five_level_test_trd import save
from inplace_zx0 import layout
from lzsa2_oracle_host import Author
from verify_lzsa2_dispatch import execute
import lzsa2_oracle as oracle
import lzsa2_stream
import resumable_lzsa2

ROOT=Path(__file__).resolve().parent


def brute(raw):
    """Enumerate complete command lists; compare serialized byte lengths."""
    def paths(at):
        yield []
        for p in range(at,len(raw)-1):
            for d in range(1,p+1):
                for n in range(2,len(raw)-p+1):
                    if raw[p:p+n]!=raw[p-d:p+n-d]:break
                    for tail in paths(p+n):yield [(p,n,d)]+tail
    return min(len(oracle.encode(raw,path)) for path in paths(0))


def corpus(raw):
    for n in range(1,10):
        for bits in itertools.product((65,66),repeat=n):
            data=bytes(bits);yield f'binary-{n}-{data.hex()}',data
    rng=random.Random(1001)
    for i in range(256):
        size=rng.choice((32,48,64,96,128));period=rng.randrange(1,25)
        seed=bytes(rng.randrange(8) for _ in range(period));data=bytearray((seed*size)[:size])
        for _ in range(rng.randrange(1,12)):
            data[rng.randrange(size)]=rng.randrange(16)
        yield f'mutated-{i}',bytes(data)
    for block in range(21):
        lo=block*15872;extent=min(15872,len(raw)-lo)
        for offset in (0,extent//3,extent-128):
            yield f'video-{block}-{offset}',raw[lo+offset:lo+offset+128]


def writer_edges():
    rng=random.Random(1002)
    for n in (1,2,3,17,18,255,256,257,15872):
        raw=bytes(rng.randrange(256) for _ in range(n))
        yield f'literals-{n}',raw,[]
    for n in (2,3,8,9,23,24,255,256,257,15871):
        raw=b'Q'*(n+1)
        yield f'match-{n}',raw,[(1,n,1)]
    for d in (1,2,31,32,33,511,512,513,8703,8704,8705):
        seed=bytes(rng.randrange(256) for _ in range(d));raw=seed+(seed*32)[:32]
        yield f'offset-{d}',raw,[(d,32,d)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dll','raw','stream','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    author=Author(a.dll);raw=a.raw.read_bytes();stream=a.stream.read_bytes()
    at=out=0;baseline_blocks=0
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        payload=stream[at:at+size];expected=raw[out:out+n];at+=size;out+=n
        assert author.compress(expected)==payload,'DLL baseline differs'
        assert author.decompress(payload,n)==expected
        baseline_blocks+=1
    assert at==len(stream) and out==len(raw)
    rows=[];native_cases=[];start=time.perf_counter();brute_count=0
    for i,(name,data) in enumerate(corpus(raw)):
        reference=author.compress(data);payload,proof=oracle.optimal(data)
        assert len(payload)<=len(reference),(name,'oracle exceeds author')
        assert author.decompress(payload,len(data))==data
        assert lzsa2_stream.trace(payload,limit=len(data))[0]==data
        if len(data)<=6:
            assert len(payload)==brute(data),name
            brute_count+=1
        row=dict(case=name,raw_hex=data.hex(),baseline_hex=reference.hex(),oracle_hex=payload.hex(),
            saved_bytes=len(reference)-len(payload),proof=proof)
        rows.append(row)
        # Native every writer mode, every changed parse and a fixed sample.
        if payload!=reference:
            native_cases.append((name+'/baseline',data,reference));native_cases.append((name,data,payload))
        elif i%32==0:native_cases.append((name,data,payload))
        if row['saved_bytes']:print('gap',name,row['saved_bytes'],'bytes',flush=True)
        if i%256==0:print('checked',i+1,flush=True)
    edges=[]
    for name,data,matches in writer_edges():
        payload=oracle.encode(data,matches)
        assert author.decompress(payload,len(data))==data
        assert lzsa2_stream.trace(payload,limit=len(data))[0]==data
        native_cases.append((name,data,payload));edges.append(dict(case=name,decoded_bytes=len(data),payload_bytes=len(payload)))
    packed=bytearray()
    for name,data,payload in native_cases:
        _,proof=lzsa2_stream.trace(payload,limit=len(data));space=layout(len(payload),len(data),proof['minimum_input_start'],len(packed))
        assert space['sector_aligned_fits'],(name,space)
        lzsa2_stream.trace(payload,limit=len(data),input_start=space['input_start'])
        packed+=struct.pack('<HH',len(data),len(payload))+payload
    h,native=fixture(packed,57,0x8de0,0x8ef7);regions,labels,_=resumable_lzsa2.build();independent=[]
    with patch.object(banked,'trace',lzsa2_stream.trace):
        for i,(name,data,payload) in enumerate(native_cases):
            row=h.block(payload,data,i,short=i==1);row['case']=name
            check=execute(regions,labels,native,payload,data,source=0x1000)
            assert row['slice_tstates']==check['slices'],name
            independent.append(dict(case=name,**check))
    times={r['case']:r['tstates'] for r in independent}
    for row in rows:
        name=row['case']
        if name+'/baseline' in times:
            row['baseline_decoder_tstates']=times[name+'/baseline'];row['oracle_decoder_tstates']=times[name]
            row['decoder_delta_tstates']=times[name]-times[name+'/baseline']
    cpu=h.finish();cpu['blocks']=h.results;cpu['independent']=independent
    save(a.output/'cpu.json',cpu)
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='a63043a',
        raw_sha256=sha(raw),baseline_stream_sha256=sha(stream),baseline_dll_blocks_exact=baseline_blocks,
        cases=len(rows),strict_improvements=sum(r['saved_bytes']>0 for r in rows),
        video_cases=sum(r['case'].startswith('video-') for r in rows),
        video_improvements=sum(r['case'].startswith('video-') and r['saved_bytes']>0 for r in rows),
        saved_bytes_on_independent_short_cases=sum(r['saved_bytes'] for r in rows),
        changed_equal_size_parses=sum(r['baseline_hex']!=r['oracle_hex'] and r['saved_bytes']==0 for r in rows),
        faster_equal_size_parses=sum(r.get('decoder_delta_tstates',0)<0 and r['saved_bytes']==0 for r in rows),
        slower_equal_size_parses=sum(r.get('decoder_delta_tstates',0)>0 and r['saved_bytes']==0 for r in rows),
        video_faster_equal_size_parses=sum(r['case'].startswith('video-') and r.get('decoder_delta_tstates',0)<0 and r['saved_bytes']==0 for r in rows),
        best_of_decoder_saving_on_short_cases=sum(-min(r.get('decoder_delta_tstates',0),0) for r in rows),
        speed_scope='Standalone short blocks only, with a fresh offset/nibble reservoir and their own EOD. These savings cannot be added to a full video stream.',
        brute_serialization_cases=brute_count,native_cases=len(native_cases),writer_edges=edges,
        elapsed_seconds=time.perf_counter()-start,dll_sha256=sha(a.dll.read_bytes()),rows=rows,
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
            'lzsa2_oracle.py','probe_lzsa2_oracle.py','lzsa2_oracle_host.py','lzsa2_oracle_host.c','build_lzsa_oracle_host.cmd')})
    save(a.output/'probe.json',report)
    print(json.dumps({k:report[k] for k in ('complete','cases','strict_improvements','video_improvements','brute_serialization_cases','native_cases','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
