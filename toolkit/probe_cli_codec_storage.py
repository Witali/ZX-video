"""Measure ZX1/LZSA2 on identical ZX0 blocks; verify with the author's PC decoder.

Storage only: no Z80 T-state, IRQ, ULA, disk or release claim. Four bytes per
block match the comparison container allowance; codec dispatch is not built.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

def sha(data): return sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','baseline','encoder','decoder','cache','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--codec',choices=('zx1','lzsa2'),required=True)
    p.add_argument('--revision',required=True)
    p.add_argument('--jobs',type=int,choices=range(1,5),default=2)
    args=p.parse_args(); data=args.raw.read_bytes()
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'))
    if not baseline['complete'] or baseline['input_sha256']!=sha(data):
        raise ValueError('matching complete baseline required')
    parts=[]; offset=0
    for block in baseline['blocks']:
        chunk=data[offset:offset+block['decoded_bytes']]; offset+=len(chunk)
        if sha(chunk)!=block['sha256']: raise ValueError('wrong block boundary')
        parts.append(chunk)
    if offset!=len(data): raise ValueError('incomplete baseline')
    args.cache.mkdir(parents=True,exist_ok=True)
    encoder,decoder=str(args.encoder.resolve()),str(args.decoder.resolve())
    encflags=['-f'] if args.codec=='zx1' else ['-r','-f','2','--prefer-ratio']
    decflags=['-f'] if args.codec=='zx1' else ['-d','-r','-f','2']
    def worker(chunk):
        digest=sha(chunk); cached=args.cache/(digest+'.'+args.codec)
        with tempfile.TemporaryDirectory(dir=args.cache) as tmp:
            src,packed,out=[Path(tmp)/name for name in ('input.raw','packed.bin','restored.raw')]
            if cached.exists(): packed.write_bytes(cached.read_bytes())
            else:
                src.write_bytes(chunk)
                subprocess.run([encoder,*encflags,str(src.resolve()),str(packed.resolve())],check=True,capture_output=True)
            subprocess.run([decoder,*decflags,str(packed.resolve()),str(out.resolve())],check=True,capture_output=True)
            if out.read_bytes()!=chunk: raise AssertionError('PC decompression differs')
            encoded=packed.read_bytes()
            if not cached.exists():
                with tempfile.NamedTemporaryFile(dir=args.cache,delete=False) as stream:
                    stream.write(encoded); temporary=Path(stream.name)
                temporary.replace(cached)
        return dict(sha256=digest,decoded_bytes=len(chunk),encoded_bytes=len(encoded),encoded_sha256=sha(encoded))
    report=dict(scope=__doc__,complete=False,codec=args.codec,source_revision=args.revision,
        encoder_sha256=sha(args.encoder.read_bytes()),decoder_sha256=sha(args.decoder.read_bytes()),
        encoder_flags=encflags,decoder_flags=decflags,input_sha256=sha(data),input_bytes=len(data),
        block_bytes=baseline['block_bytes'],blocks_expected=len(parts),blocks=[],
        player_changed=False,player_delta_tstates=0,speed_measured=False,release=False,
        verification='author PC decoder, byte-exact per block; not an independent Z80 decoder')
    def save():
        rows=report['blocks']; old=baseline['blocks'][:len(rows)]
        report['encoded_with_headers_bytes']=sum(r['encoded_bytes']+4 for r in rows)
        report['stored_fallback_with_headers_bytes']=sum(min(r['encoded_bytes'],r['decoded_bytes'])+4 for r in rows)
        report['mixed_zx0_codec_with_headers_bytes']=sum(min(r['encoded_bytes'],o['zx0_bytes'])+4 for r,o in zip(rows,old))
        report['blocks_smaller_than_zx0']=sum(r['encoded_bytes']<o['zx0_bytes'] for r,o in zip(rows,old))
        report['delta_from_zx0_bytes']=report['encoded_with_headers_bytes']-sum(o['zx0_bytes']+4 for o in old)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i,row in enumerate(pool.map(worker,parts)):
            report['blocks'].append(row)
            if i%20==0:
                save(); print(f'{args.codec}: verified {i+1}/{len(parts)}',flush=True)
    report['complete']=True; save()
    print(json.dumps({k:v for k,v in report.items() if k!='blocks'}),flush=True)


if __name__=='__main__': main()
