"""Compare absolute and low-period-delta audio on the selected full-movie quarters.

Only host coding is measured here. Native size includes an explicit reserve,
not a measured decoder or a timing/release claim.
"""
import argparse
import gzip
import json
from pathlib import Path

import ay_huffman_stream
import ay_interrupt
import ay_period_delta as delta
from build_fap3_trd import sha
from build_long_video_trd import AyFrame
from convert_video import write_json
import resident_audio_z80 as resident


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','metadata','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    prep=json.loads(args.prepared.read_bytes());m=json.loads(args.metadata.read_bytes())
    audio=(args.prepared.parent/'audio.bin').read_bytes();assert sha(audio)==prep['ay_sha256']
    frames=[AyFrame.deserialize(audio[i:i+9]) for i in range(0,len(audio),9)]
    records=ay_interrupt.encode_ticks(frames)
    boundaries=[round(prep['frames']*i/4) for i in range(5)];result=[]
    for part,(lo,hi) in enumerate(zip(boundaries,boundaries[1:]),1):
        selected=records[lo*5:hi*5]
        initial=ay_interrupt.registers(frames[lo*5-1]) if lo else bytes(11)
        variants={}
        for name,coder in (('absolute',ay_huffman_stream),('period_delta',delta)):
            data,meta=coder.encode(selected,initial)
            assert coder.decode(data)==(initial,selected)
            huffman=delta.huffman_bytes(data) if name=='period_delta' else data
            first,ticks,trees,payload=resident.tables(huffman)
            _,labels,_=resident.code(m['audio_labels'],len(ticks),first,0,0,batch=31)
            roots=(labels['end']+255)&~255
            _,nodes=resident.tree_bytes(trees,roots+26)
            native_base=roots-resident.ORIGIN+26+len(nodes)+len(payload)
            # Reserve a full extra alignment page for the unimplemented
            # predictor instructions and state. The native build must replace
            # this estimate before accepting any volume.
            reserved=native_base+(256 if name=='period_delta' else 0)
            path=args.output/f'part-{part}-{name}.bin.gz'
            path.write_bytes(gzip.compress(data,mtime=0))
            variants[name]=dict(coded_bytes=len(data),native_base_bytes=native_base,
                reserved_native_bytes=reserved,reserved_bank_fits=reserved<=16384,
                ticks=len(selected),records_exact=True,sha256=sha(data),
                archive=path.name,archive_sha256=sha(path.read_bytes()),metadata=meta)
        result.append(dict(part=part,start=lo,end=hi,variants=variants))
    report=dict(complete=True,release=False,date='2026-10-01',scope=__doc__,ay_sha256=sha(audio),
        full_movie_ticks=len(frames),original_tick_records_exact=True,parts=result,
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('ay_period_delta.py','probe_ay_period_delta.py','resident_audio_z80.py')})
    write_json(args.output/'report.json',report)
    print(json.dumps([dict(part=row['part'],absolute=row['variants']['absolute']['native_base_bytes'],
        delta_reserved=row['variants']['period_delta']['reserved_native_bytes']) for row in result]))


if __name__=='__main__':main()
