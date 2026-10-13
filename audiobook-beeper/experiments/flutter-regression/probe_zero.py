"""Bounded host check of PCM-bin centering on one saved, complete output clock."""
from fractions import Fraction as F
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

from audit import read, metrics, BEEPER, CPU
from ima_codec import decode
from convert_mulaw_audio import filter_signal
from audit_direct_regression import fixed_reference
from build_pdm import write_wav


def exact_table(model, origin):
    holds = model['holds']
    weights = [F(16*h,sum(holds)) for h in holds]
    words = np.empty((64,32),dtype='>u2')
    nxt = np.empty((64,32),dtype='u1')
    for v in range(64):
        x = (F(v)+origin)/64
        for state in range(32):
            q = F(state//2-8,8)
            recent = F(1 if state%2 else -1,2)*F(model['extent'])
            word = 0
            for w in weights:
                u = x+q/w+F(model['beta'])*recent
                bit = int(u>=F(1,2))
                recent = u-bit
                q += w*(x-bit)
                word = word*2+bit
            code = max(0,min(15,(q*8+F(17,2)).__floor__()))
            words[v,state] = word
            nxt[v,state] = code*2+int(recent>=0)
    states = {16}
    while True:
        expanded = states|set(map(int,nxt[:,sorted(states)].ravel()))
        if expanded==states:
            break
        states=expanded
    return words,nxt,sorted(states)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args()
    root=args.repository
    source=root/'audiobook-beeper/experiments/quality-max/evidence/ima4/selected'
    out=args.output
    out.mkdir(parents=True,exist_ok=False)
    meta=json.loads(read(source/'player.json',root))
    packed=gzip.decompress(read(source/'soundtrack.ima.gz',root))
    decoded,_=decode(packed)
    levels=((decoded.astype(np.int32)+32768)>>8).astype('u1')
    count=meta['outputs_per_cycle']
    times=np.frombuffer(gzip.decompress(read(source/'output-times.u32.gz',root)),'<u4').astype(np.int64)[:count+1]
    times-=times[0]
    import io,wave
    with wave.open(io.BytesIO(read(source/'source-preview.wav',root)),'rb') as wav:
        pcm=np.frombuffer(wav.readframes(wav.getnframes()),'u1')
    ffmpeg=args.ffmpeg
    fixed=fixed_reference(pcm,times[-1],8000,ffmpeg)
    rows=[]
    for label,origin,rounding in [('midpoint',F(1,2),False),('zero-rounded',F(0),True),('zero-floor',F(0),False)]:
        words,nxt,states=exact_table(meta['model'],origin)
        codes=np.minimum(63,(levels.astype(int)+(2 if rounding else 0))//4)
        q=16
        packets=np.empty(len(codes),dtype='>u2')
        for i,v in enumerate(codes):
            packets[i]=words[v,q]
            q=int(nxt[v,q])
        bits=np.unpackbits(packets.view('u1'))
        at=(len(levels)-3)*16+15
        bits=np.r_[bits[:at],np.tile([1,0],meta['loop_idle_pairs']),bits[at:]]
        output=filter_signal(bits,times,ffmpeg,768000)
        held=filter_signal(np.repeat(levels/256.,16) if not meta['loop_idle_pairs'] else
            np.r_[np.repeat(levels/256.,16)[:at],np.full(meta['loop_idle_pairs']*2,.5),np.repeat(levels/256.,16)[at:]],times,ffmpeg,768000)
        first=len(set(map(int,(words[:,states]>>8).ravel())))
        second=len(set(map(int,(words[:,states]&255).ravel())))
        def reservation(start_padding):
            pointers=(start_padding+first*41+second*64+255)//256*256
            return (pointers+256+1024+1088+255)//256*256
        old_reserve=reservation(0x400)
        reserve=reservation(0x380 if origin==0 else 0x400)
        row=dict(name=label,reachable_states=len(states),first_patterns=first,second_patterns=second,
            minimum_reserve_before_padding_reclaim_bytes=old_reserve,
            minimum_reserve_with_padding_reclaim_bytes=reserve,
            fits_existing_tables=len(states)*6<=128 and reserve<=14336,
            fixed_clock=metrics(fixed,output),pdm_only=metrics(held,output),
            measured_new_timeline=False,original_payload_unchanged=True)
        write_wav(out/(label+'-output.wav'),output*.8)
        rows.append(row)
        print(json.dumps({k:({kk:vv for kk,vv in v.items() if kk!='field_error_power'} if k in ('fixed_clock','pdm_only') else v) for k,v in row.items()}),flush=True)
    (out/'report.json').write_text(json.dumps(dict(scope=__doc__,rows=rows),indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
