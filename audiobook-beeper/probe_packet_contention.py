"""Bounded host diagnosis on the delivered full-loop Fuse timeline.

No changed table is a native release: new patterns/layout and any phase
selection must be assembled and checked independently before delivery.
"""
import argparse,gzip,json,wave
from pathlib import Path
import numpy as np
from ima_codec import decode
from packet_player import HOLDS
from probe_feedback_packets import integral_table,generate,packet_measure


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta=json.loads((a.input/'player.json').read_bytes())
    packed=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes());pcm,_=decode(packed)
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    with wave.open(str(a.input/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    times=np.frombuffer(gzip.decompress((a.input/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:len(pcm)*16+1]
    holds=np.diff(times).reshape(-1,16)
    ordinary=holds[holds[:,14]<45] if meta.get('direct') else holds[holds[:,-1]<60]
    native=np.array(meta['ordinary_holds_tstates'])
    mean=ordinary.mean(axis=0);median=np.median(ordinary,axis=0)
    rows=[]
    variants=[('native',native,.5),('mean',mean,.5),('median',median,.5),
              ('half_correction',(mean+native)/2,.5),('double_correction',mean*2-native,.5)]
    if meta.get('direct'):
        rounded=np.rint(mean*8).astype(int)
        variants += [(f'mean_eighth_beta{beta}',rounded,beta) for beta in (.25,.375,.5,.625,.75)]
    variants=[(*v,1.) for v in variants]
    if meta.get('direct'):
        variants += [(f'mean_eighth_extent{extent}',rounded,.5,extent) for extent in (.5,.75,1.25,1.5)]
    for name,weights,beta,extent in variants:
        words,successors,peak=integral_table(64,2,holds=weights,beta=beta,extent=extent)
        bits=generate(levels,words,successors)
        metric=packet_measure(bits,np.repeat(levels,16),np.repeat(source,16),times,a.ffmpeg)
        states={16}
        while True:
            expanded=states|set(map(int,successors[:,sorted(states)].ravel()))
            if expanded==states:break
            states=expanded
        selected=words[:,sorted(states)] if meta.get('direct') else words
        first=len(np.unique(selected>>8));second=len(np.unique(selected&255))
        reserve=(((1024+first*41+second*64+255)//256)*256+256+1024+1088+255)//256*256 if meta.get('direct') else ((1024+first*40+second*72+255)//256)*256+1024
        row=dict(name=name,holds=list(map(float,weights)),beta=beta,extent=extent,reachable_states=sorted(states),first_patterns=first,second_patterns=second,
                 resident_bytes=reserve,metrics=metric)
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(scope=__doc__,samples=len(pcm),source_directory=str(a.input),rows=rows,
                per_slot_min=holds.min(axis=0).tolist(),per_slot_max=holds.max(axis=0).tolist())
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
