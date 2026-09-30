"""Bounded PC size/round-trip comparison; no Z80 speed or release claim.

Use the exact archived five-level video bytes and 15872-byte block boundaries.
All streams include the same four-byte per-block header. LZMA/DEFLATE/LZ4
are raw payloads; bzip2/Zstd/Brotli retain their normal framing. Codec options
are assumed fixed in the player, whose extra code/metadata is not included.
"""
import argparse,bz2,gzip,hashlib,importlib.metadata,json,lzma,platform,struct,time,zlib
from pathlib import Path
import brotli
import lz4.block
import zstandard as zstd
from lzsa2_stream import trace as lzsa_decode


def sha(data):return hashlib.sha256(data).hexdigest()


def parse(stream,decode):
    at=0;blocks=[]
    while at<len(stream):
        size,n=struct.unpack_from('<HH',stream,at);at+=4;packed=stream[at:at+n];at+=n
        raw=decode(packed,size)
        if len(packed)!=n or len(raw)!=size:raise ValueError('block length mismatch')
        blocks.append((raw,packed))
    if at!=len(stream):raise ValueError('trailing bytes')
    return blocks


def codecs():
    result=[]
    for name,preset,lc,method in (
        ('lzma1_fast_lc3',0,3,lzma.FILTER_LZMA1),
        ('lzma1_extreme_lc3',9|lzma.PRESET_EXTREME,3,lzma.FILTER_LZMA1),
        ('lzma1_extreme_lc0',9|lzma.PRESET_EXTREME,0,lzma.FILTER_LZMA1),
        ('lzma2_extreme_lc0',9|lzma.PRESET_EXTREME,0,lzma.FILTER_LZMA2)):
        filters=[dict(id=method,preset=preset,dict_size=16384,lc=lc,lp=0,pb=2)]
        result.append((name,dict(filters=filters,format='raw',sdk_probability_bytes=2*(1984+(768<<lc)),
            note='SDK probability array estimate only; exclude code, other state and buffers'),
            lambda raw,f=filters:lzma.compress(raw,format=lzma.FORMAT_RAW,filters=f),
            lambda packed,n,f=filters:lzma.decompress(packed,format=lzma.FORMAT_RAW,filters=f)))
    for level in (1,9):
        result.append((f'bzip2_{level}',dict(level=level,format='bz2',declared_block_bytes=level*100000),
            lambda raw,l=level:bz2.compress(raw,compresslevel=l),lambda packed,n:bz2.decompress(packed)))
        def deflate(raw,l=level):
            c=zlib.compressobj(l,zlib.DEFLATED,-14);return c.compress(raw)+c.flush()
        result.append((f'deflate_{level}',dict(level=level,wbits=-14,format='raw'),deflate,
            lambda packed,n:zlib.decompress(packed,-14)))
    for name,options in (('lz4_fast',dict(mode='default')),('lz4_hc12',dict(mode='high_compression',compression=12))):
        result.append((name,dict(options,format='raw',store_size=False),
            lambda raw,o=options:lz4.block.compress(raw,store_size=False,**o),
            lambda packed,n:lz4.block.decompress(packed,uncompressed_size=n)))
    for level in (1,19):
        params=zstd.ZstdCompressionParameters.from_level(level,window_log=14)
        c=zstd.ZstdCompressor(compression_params=params);d=zstd.ZstdDecompressor()
        result.append((f'zstd_{level}',dict(level=level,window_log=14,format='zstd-frame',
            desktop_reference_dctx_bytes=d.memory_size()),c.compress,lambda packed,n,d=d:d.decompress(packed)))
    for quality in (1,11):
        result.append((f'brotli_{quality}',dict(quality=quality,lgwin=14,format='brotli'),
            lambda raw,q=quality:brotli.compress(raw,quality=q,lgwin=14),lambda packed,n:brotli.decompress(packed)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,default=Path(__file__).with_name('row_lzsa_evidence'))
    p.add_argument('--baseline',type=Path,default=Path(__file__).with_name('row_lzsa_optimization.json'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--artifacts',type=Path,required=True)
    a=p.parse_args();a.artifacts.mkdir(parents=True,exist_ok=True)
    baseline=json.loads(a.baseline.read_text());wanted={r['file']:r for r in baseline['archives']}
    def load(name):
        path=a.evidence/(name+'.gz');blob=path.read_bytes();row=wanted[path.name]
        if sha(blob)!=row['sha256']:raise ValueError('archive SHA mismatch')
        raw=gzip.decompress(blob)
        if sha(raw)!=row['raw_sha256']:raise ValueError('input SHA mismatch')
        return raw
    stream=load('video.stream');raw=load('video.raw')
    blocks=parse(stream,lambda b,n:lzsa_decode(b,limit=n)[0])
    if b''.join(b for b,_ in blocks)!=raw:raise ValueError('LZSA2 raw mismatch')
    meta=json.loads(load('fast_zx0-metadata.json'));zx0_size=sum(b['zx0_bytes']+4 for b in meta['blocks'])
    if zx0_size!=meta['video_bytes']:raise ValueError('ZX0 size mismatch')
    rows=[dict(codec='zx0_fast_reference',stream_bytes=zx0_size,sectors=(zx0_size+255)//256,
        native_decoder_tstates=baseline['variants'][0]['decoder_tstates'],verification='archived native/Fuse run'),
        dict(codec='lzsa2_reference',stream_bytes=len(stream),sectors=(len(stream)+255)//256,
        native_decoder_tstates=baseline['variants'][1]['decoder_tstates'],verification='host plus archived native/Fuse run')]
    for name,options,encode,decode in codecs():
        output=bytearray();measurements=[];enc=dec=0
        for i,(chunk,_) in enumerate(blocks):
            start=time.perf_counter_ns();packed=encode(chunk);enc+=time.perf_counter_ns()-start
            start=time.perf_counter_ns();restored=decode(packed,len(chunk));dec+=time.perf_counter_ns()-start
            if restored!=chunk:raise AssertionError((name,i,'round trip differs'))
            if len(packed)>65535:raise ValueError('payload does not fit header')
            output+=struct.pack('<HH',len(chunk),len(packed))+packed
            measurements.append(dict(index=i,decoded_bytes=len(chunk),compressed_bytes=len(packed),
                raw_sha256=sha(chunk),compressed_sha256=sha(packed)))
        blob=gzip.compress(bytes(output),mtime=0);file=name+'.stream.gz';(a.artifacts/file).write_bytes(blob)
        rows.append(dict(codec=name,options=options,stream_bytes=len(output),sectors=(len(output)+255)//256,
            delta_from_zx0_bytes=len(output)-zx0_size,delta_from_zx0_percent=100*(len(output)/zx0_size-1),
            encode_pc_ms=enc/1e6,decode_pc_ms=dec/1e6,exact=True,blocks=measurements,
            native_decoder_tstates=None,inplace_overlap_verified=False,
            archive=dict(file=file,sha256=sha(blob),raw_sha256=sha(output))))
    reference=baseline['variants'][1]
    read_average=reference['disk_windows_elapsed_tstates']/reference['checked_sectors']
    for row in rows[2:]:
        saved=reference['video_sectors']-row['sectors']
        row['rough_break_even_decoder_tstates']=reference['decoder_tstates']+saved*read_average
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='11778ed',frames=meta['frames'],
        raw_sha256=sha(raw),decoded_bytes=len(raw),blocks=len(blocks),block_size=15872,
        player_changed=False,player_delta_tstates=0,native_performance_measured=False,new_trd_built=False,
        pc_timing_scope='One sequential run; includes Python/binding overhead, not a rigorous PC benchmark or Z80 estimate.',
        break_even_scope='Heuristic only: LZSA2 decoder T + saved sectors * observed LZSA2 mean read-window T. Not a hard bound or fps prediction; excludes changed producer/code/banking/queue/rotation/IRQ/ULA effects.',
        missing_acceptance=['Z80 decoder and instruction counts','in-place proof','128-KiB allocation','disk/IRQ/ULA and full EOF cadence'],
        python=platform.python_version(),zlib=zlib.ZLIB_RUNTIME_VERSION,zstd=zstd.ZSTD_VERSION,
        packages={name:importlib.metadata.version(name) for name in ('zstandard','lz4','brotli')},
        baseline_report_sha256=sha(a.baseline.read_bytes()),source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
        candidates=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([dict(codec=r['codec'],bytes=r['stream_bytes'],sectors=r['sectors'],
        delta_percent=round(r.get('delta_from_zx0_percent',100*(r['stream_bytes']/zx0_size-1)),2)) for r in rows]))


if __name__=='__main__':main()
