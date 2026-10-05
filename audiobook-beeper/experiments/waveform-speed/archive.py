"""Archive and authenticate the completed exact-output speed comparison."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREVIOUS=HERE.parent/'entertainer-normalized'


def digest(blob):return hashlib.sha256(blob).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def verify():
    report=read(HERE/'report.json')
    assert report['complete'] and len(report['full'])==3
    assert report['source_sha256']==read(PREVIOUS/'normalization.json')['pcm_sha256']
    assert report['native_tstate_delta']==0 and not report['changed_player']
    hashes={row['packed_sha256'] for row in report['short']}
    assert len(hashes)==1 and all(row['byte_exact'] for row in report['short'])
    for row in report['full']:
        n=row['attempt']
        packed=gzip.decompress((HERE/f'encode-{n}.ima.gz').read_bytes())
        old=PREVIOUS/'ima3/attempts'/f'encode-{n}'/'soundtrack.ima.gz'
        assert packed==gzip.decompress(old.read_bytes())
        assert digest(packed)==row['packed_sha256'] and row['byte_exact']
        assert len(packed)*2==row['samples']==186880
    for name,expected in report['producer_sha256_lf'].items():
        assert digest(gzip.decompress((HERE/'producer-source'/(name+'.gz')).read_bytes()))==expected
    source=ast.parse(gzip.decompress((HERE/'producer-source/waveform_kernel.py.gz').read_bytes()))
    embedded=next(ast.literal_eval(node.value) for node in source.body
                  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE' for t in node.targets))
    assert digest(embedded.encode())==read(HERE/'native-build.json')['embedded_c_sha256']
    old_producers=read(PREVIOUS/'ima3/run.json')['producer_sha256']
    for name,expected in read(HERE/'unchanged-player.json').items():assert expected==old_producers[name]
    for codec,previous in read(PREVIOUS/'comparison.json')['codecs'].items():
        assert digest((ROOT/previous['trd']).read_bytes())==previous['trd_sha256'],codec
    timing={row['backend']:row['median_seconds'] for row in report['short']}
    return dict(complete=True,full_streams_byte_exact=3,
                native_speedup=timing['baseline']/timing['native'],
                numpy_speedup=timing['baseline']/timing['numpy'],
                unchanged_release_disks=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--write-manifest',action='store_true')
    args=parser.parse_args()
    if args.archive:
        work=args.archive.resolve()
        report=read(work/'report.json')
        assert report['complete'] and len(report['full'])==3
        for name in ('report.json','short.json','full.json','encode-1.ima.gz','encode-2.ima.gz','encode-3.ima.gz'):
            dest=HERE/name
            if dest.exists():assert dest.read_bytes()==(work/name).read_bytes(),name
            shutil.copyfile(work/name,dest)
        folder=HERE/'producer-source';folder.mkdir(exist_ok=True)
        for name,expected in report['producer_sha256_lf'].items():
            blob=(ROOT/'audiobook-beeper'/name).read_bytes().replace(b'\r\n',b'\n')
            assert digest(blob)==expected,name
            (folder/(name+'.gz')).write_bytes(gzip.compress(blob,mtime=0))
        previous=read(PREVIOUS/'ima3/run.json')['producer_sha256']
        player={}
        for name in ('ima3_direct_player.py','ima3-direct-player.asm','ima_codec.py','build_ima3_direct.py'):
            current=digest((ROOT/'audiobook-beeper'/name).read_bytes())
            assert current==previous[name],name
            player[name]=current
        save(HERE/'unchanged-player.json',player)
    result=verify()
    manifest=HERE/'artifact-hashes.json'
    if args.write_manifest:
        files=sorted(p for p in HERE.rglob('*') if p.is_file() and p!=manifest and '__pycache__' not in p.parts)
        save(manifest,{p.relative_to(HERE).as_posix():digest(p.read_bytes()) for p in files})
    for name,expected in read(manifest).items():assert digest((HERE/name).read_bytes())==expected,name
    print(json.dumps(dict(**result,artifacts=len(read(manifest)))))


if __name__=='__main__':main()
