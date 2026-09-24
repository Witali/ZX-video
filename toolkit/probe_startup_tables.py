"""Reversible storage transforms for independent-boot Huffman/shift tables.

Offline size probe only. It does not implement the Z80 bootstrap transform,
nor prove a disk fit or playback timing. Every candidate is round-tripped.
"""
import argparse
import json
from pathlib import Path

from build_fap3_trd import Builder,sha,sectors
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from prefix_huffman_z80 import prepare


def difference(data,stride=1,xor=False):
    return bytes((v ^ data[i-stride]) if xor and i>=stride else
        (v-data[i-stride])&255 if i>=stride else v for i,v in enumerate(data))


def undifference(data,stride=1,xor=False):
    result=bytearray(data)
    for i in range(stride,len(result)):
        result[i]=(result[i]^result[i-stride]) if xor else (result[i]+result[i-stride])&255
    return bytes(result)


def transpose(data,columns):
    if len(data)%columns:raise ValueError('unaligned transpose')
    return b''.join(data[i::columns] for i in range(columns))


def variants(data):
    yield 'identity',data,lambda x:x
    for stride in (1,2,16,256,512):
        for xor in (False,True):
            yield f'{"xor" if xor else "delta"}-{stride}',difference(data,stride,xor),lambda x,s=stride,q=xor:undifference(x,s,q)
    yield 'delta-1-twice',difference(difference(data)),lambda x:undifference(undifference(x))
    for columns in (16,64,256):
        moved=transpose(data,columns)
        yield f'transpose-{columns}',moved,lambda x,c=columns:transpose(x,len(x)//c)
        yield f'transpose-{columns}-delta',difference(moved),lambda x,c=columns:transpose(undifference(x),len(x)//c)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','zx0','cache','report'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();raw=args.raw.read_bytes()
    _,_,frames,mapping,tables=read_header(Reader(raw),magic=b'FAP3')
    layout=prepare(tables,mapping);bank=layout['regions'][0][1]
    compressor=Builder.__new__(Builder);compressor.cache=args.cache;args.cache.mkdir(parents=True,exist_ok=True)
    compressor.zx0=args.zx0.resolve();compressor.memo={}
    report=dict(baseline_commit='b77a756',complete=False,release=False,offline_only=True,
        independently_bootable_required=True,frames=frames,raw_sha256=sha(raw),
        bank6_sha256=sha(bank),tables=len(tables),variants=[],machine_transform_implemented=False)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    def save():args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    for name,data,inverse in variants(bank):
        encoded=compressor.compress(data)
        if inverse(data)!=bank:raise AssertionError('inverse differs')
        row=dict(name=name,bytes=len(data),zx0_bytes=len(encoded),sectors=sectors(encoded),roundtrip_exact=True)
        report['variants'].append(row);save();print(json.dumps(row),flush=True)
    for name,data in [('without_generated_shifts',bank[:12288]),('canonical_lengths',b''.join(tables))]:
        encoded=compressor.compress(data)
        if name=='without_generated_shifts':
            decoded=data+b''.join(bytes((v<<r)&255 for v in range(256)) for r in range(8))+b''.join(bytes(v>>(8-r) for v in range(256)) for r in range(8))
        else:
            decoded=prepare([data[i:i+256] for i in range(0,len(data),256)],mapping)['regions'][0][1]
        if decoded!=bank:raise AssertionError('generated table differs')
        row=dict(name=name,bytes=len(data),zx0_bytes=len(encoded),sectors=sectors(encoded),roundtrip_exact=True,
            generator_size_and_cycles_not_included=True)
        report['variants'].append(row);save();print(json.dumps(row),flush=True)
    report['complete']=True;save()


if __name__=='__main__':main()
