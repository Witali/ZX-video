"""Archive a complete resident-player attempt before changing its generator.

Preserves source snapshots, build/metadata, read-only debugger commands,
complete Fuse reports and raw traces. TRD images stay in the build directory;
this evidence is not a release package. Gzip contents and hashes are stable.
"""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','directory','fuse','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();report=json.loads(a.build.read_bytes())
    if not report['complete']:raise ValueError('incomplete build')
    a.output.mkdir(parents=True,exist_ok=True);entries=[]
    def save(path,name):
        raw=path.read_bytes();packed=gzip.compress(raw,mtime=0)
        target=a.output/(name+'.gz')
        if target.exists() and target.read_bytes()!=packed:raise ValueError(('refuse to replace evidence',target))
        target.write_bytes(packed)
        entries.append(dict(file=target.name,sha256=sha(packed),decoded_sha256=sha(raw),decoded_bytes=len(raw)))
    for name,digest in report['source_sha256_lf'].items():
        path=ROOT/name
        if sha(path.read_bytes().replace(b'\r\n',b'\n'))!=digest:raise ValueError(('source differs',name))
        save(path,'source-'+name)
    save(a.build,'build.json')
    for part in (1,2,3):
        metadata=a.directory/f'ZX-video-huffman-preview_part{part:02}.json'
        m=json.loads(metadata.read_bytes())
        if sha((a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes())!=m['trd_sha256']:
            raise ValueError('TRD differs from metadata')
        fuse=json.loads((a.fuse/f'part{part:02}.json').read_bytes())
        if not fuse['complete'] or fuse['failure'] or fuse['errors']:raise ValueError('incomplete or inexact Fuse run')
        save(metadata,f'part{part:02}.metadata.json')
        for suffix in ('json','trace.txt','debugger.txt'):
            save(a.fuse/f'part{part:02}.{suffix}',f'part{part:02}.{suffix}')
    manifest=dict(complete=True,release=False,scope=__doc__,files=entries,
        snapshot_script_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(directory=str(a.output),files=len(entries),packed_bytes=sum((a.output/e['file']).stat().st_size for e in entries))),flush=True)


if __name__=='__main__':main()
