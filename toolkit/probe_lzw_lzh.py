"""Compare LZW and LZH-LH5 on the existing exact, bounded video fixture.

Host storage/round-trip evidence only. No Z80 decoder or new TRD is produced.
"""
import argparse,gzip,hashlib,importlib.metadata,io,json,random,struct,subprocess
from pathlib import Path
import lhafile,ncompress
from lzsa2_stream import trace
from lzw_probe_codec import encode,decode_independent


def sha(data):return hashlib.sha256(data).hexdigest()


def lh5(raw,encoder,work):
    source=work/'input.raw';output=work/'output.lh5';source.write_bytes(raw)
    result=subprocess.run([str(encoder.resolve()),str(source.resolve()),str(output.resolve())],check=True,capture_output=True)
    crc,packed_size,decoded_size=map(int,result.stdout.split());packed=output.read_bytes()
    if packed_size!=len(packed) or decoded_size!=len(raw):raise AssertionError('LH5 size differs')
    name=b'test.bin'
    body=b'-lh5-'+struct.pack('<IIIBBB',len(packed),len(raw),0x210000,0x20,0,len(name))+name+struct.pack('<H',crc)
    archive=bytes([len(body),sum(body)&255])+body+packed+b'\0'
    decoded=lhafile.Lhafile(io.BytesIO(archive)).read(name.decode())
    if decoded!=raw:raise AssertionError('independent LH5 decode differs')
    return packed,dict(crc16=crc)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('encoder','sevenzip','work','output','artifacts'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True);a.artifacts.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).parent;baseline=json.loads((root/'row_lzsa_optimization.json').read_text())
    refs={r['file']:r for r in baseline['archives']}
    def load(name):
        blob=(root/'row_lzsa_evidence'/(name+'.gz')).read_bytes();data=gzip.decompress(blob);r=refs[name+'.gz']
        if sha(blob)!=r['sha256'] or sha(data)!=r['raw_sha256']:raise ValueError('input SHA differs')
        return data
    stream=load('video.stream');raw=load('video.raw');blocks=[];at=0
    while at<len(stream):
        size,n=struct.unpack_from('<HH',stream,at);at+=4
        chunk=trace(stream[at:at+n],limit=size)[0];blocks.append(chunk);at+=n
    if at!=len(stream) or b''.join(blocks)!=raw:raise ValueError('raw video differs')
    reference=baseline['variants'][0]['video_bytes'];rows=[]
    for codec in ('lzw10_clear','lzw11_clear','lzw12_clear','lzw_compress16','lzh_lh5'):
        output=bytearray();records=[]
        for index,chunk in enumerate(blocks):
            if codec.startswith(('lzw10','lzw11','lzw12')):
                bits=int(codec[3:5]);packed,info=encode(chunk,bits)
                if decode_independent(packed,len(chunk))!=chunk:raise AssertionError((codec,index,'Pillow differs'))
            elif codec=='lzw_compress16':
                packed=ncompress.compress(chunk);info=dict(z_header=packed[:3].hex())
                if ncompress.decompress(packed)!=chunk:raise AssertionError('ncompress differs')
                path=a.work/'input.Z';path.write_bytes(packed)
                restored=subprocess.run([str(a.sevenzip.resolve()),'x','-so','-bd',str(path.resolve())],capture_output=True,check=True).stdout
                if restored!=chunk:raise AssertionError('independent 7-Zip LZW differs')
            else:packed,info=lh5(chunk,a.encoder,a.work)
            output+=struct.pack('<HH',len(chunk),len(packed))+packed
            records.append(dict(index=index,decoded_bytes=len(chunk),compressed_bytes=len(packed),
                raw_sha256=sha(chunk),packed_sha256=sha(packed),**info))
        packed_archive=gzip.compress(bytes(output),mtime=0);file=codec+'.stream.gz';(a.artifacts/file).write_bytes(packed_archive)
        rows.append(dict(codec=codec,stream_bytes=len(output),sectors=(len(output)+255)//256,
            delta_from_zx0_percent=100*(len(output)/reference-1),exact=True,blocks=records,
            archive=dict(file=file,sha256=sha(packed_archive),raw_sha256=sha(output))))
    rng=random.Random(71)
    cases=[bytes(rng.randrange(256) for _ in range(n)) for n in (1,2,254,255,256,257,1024,15872)]
    cases += [b'A'*15872,bytes(range(256))*62]
    for case in cases:
        for bits in (10,11,12):
            if decode_independent(encode(case,bits)[0],len(case))!=case:raise AssertionError('LZW boundary differs')
    for case in (b'A'*4096,b'A'*15872,bytes(range(256))*62):lh5(case,a.encoder,a.work)
    source=json.loads(a.encoder.with_name('source.json').read_text())
    if source['executable_sha256']!=sha(a.encoder.read_bytes()):raise ValueError('LH5 binary differs')
    names=('prepare_lzh5_probe.py','lzh5_probe.c','lzw_probe_codec.py','probe_lzw_lzh.py')
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='e394688',frames=192,decoded_bytes=len(raw),
        raw_sha256=sha(raw),block_size=15872,blocks=len(blocks),reference_zx0_bytes=reference,
        reference_lzsa2_bytes=baseline['variants'][1]['video_bytes'],candidates=rows,
        player_changed=False,player_delta_tstates=0,native_performance_measured=False,new_trd_built=False,
        exact_video_roundtrips=len(blocks)*len(rows),lzw_extra_cases=len(cases)*3,lh5_extra_cases=3,
        compression_format='Four-byte block header throughout; raw GIF-compatible LZW or raw LH5; .Z retains its 3-byte header.',
        verification='LZW10/11/12 via independent Pillow GIF decoder; ncompress via own decoder and independent 7-Zip; LH5 via independent lhafile with CRC.',
        limitations='Size only, no native T-states, input/output overlap proof, bank allocation, physical disk or frame deadlines.',
        packages={name:importlib.metadata.version(name) for name in ('ncompress','lhafile','Pillow')},
        lzh_encoder=source,sevenzip_sha256=sha(a.sevenzip.read_bytes()),
        source_sha256_lf={name:sha((root/name).read_bytes().replace(b'\r\n',b'\n')) for name in names})
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([dict(codec=r['codec'],bytes=r['stream_bytes'],sectors=r['sectors'],delta_percent=round(r['delta_from_zx0_percent'],2)) for r in rows]))


if __name__=='__main__':main()
