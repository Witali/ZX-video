"""Try nonlinear 64-level maps with unchanged table/dispatch instruction counts.

Full-source host estimates on an old measured timeline only. New tables can
change memory contention and must undergo a new complete playback test.
"""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from ima_codec import decode
from build_pdm import reconstruct,write_wav
from probe_reconstruction_error import wav8,filtered
from probe_packet_area import render_levels
from pdm_player import CPU_CLOCK
from assess_snr import ratio
from probe_feedback_packets import integral_table


def make_table(numerators,model):
    x=np.asarray(numerators,dtype=float)[:,None]/128
    q=np.broadcast_to((np.arange(32)//2-8)/8,(64,32)).copy()
    recent=np.broadcast_to((np.arange(32)%2-.5)*model['extent'],(64,32)).copy()
    words=np.zeros((64,32),dtype='u2')
    for weight in np.asarray(model['holds'])/np.mean(model['holds']):
        u=x+q/weight+model['beta']*recent;bit=u>=.5
        recent=u-bit;q+=weight*(x-bit);words=(words<<1)|bit
    nxt=(np.clip(np.floor(q*8+8.5),0,15)*2+np.clip(np.floor(recent/model['extent']+1),0,1)).astype('u1')
    mapping=np.argmin(abs(np.arange(256)[:,None]+.5-2*np.asarray(numerators)[None,:]),axis=1).astype('u1')
    reachable={16}
    while True:
        more=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if more==reachable:break
        reachable=more
    first=len(set(map(int,(words[:,sorted(reachable)]>>8).ravel())))
    second=len(set(map(int,(words[:,sorted(reachable)]&255).ravel())))
    pointers=(0x8400+first*41+second*64+255)&~255
    reserve=((pointers+256+1024+1088+255)&~255)-0x8000
    layout=dict(reachable_states=len(reachable),first_patterns=first,second_patterns=second,
                required_resident_bytes=reserve,fits_current_layout=len(reachable)*6<=128 and reserve<=14336)
    return words,nxt,mapping,layout


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta=json.loads((a.input/'player.json').read_bytes());count=meta['outputs_per_cycle']
    packed=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes());pcm,_=decode(packed)
    pcm8=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    t=np.frombuffer(gzip.decompress((a.input/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count+1];t-=t[0]
    source=wav8(a.input/'source-preview.wav');period=CPU_CLOCK/8000;segments=int(np.ceil(t[-1]/period))
    edges=np.r_[np.arange(segments)*period,t[-1]];values=np.pad(source/256,(0,max(0,segments-len(source))),constant_values=.5)[:segments]
    original=filtered(reconstruct(values,edges),a.ffmpeg);ref=original[4410:-4410]
    magnitudes=dict(weak=np.r_[np.arange(1,9),np.arange(10,41,2),np.arange(44,63,3)],
                    medium=np.r_[np.arange(1,17),np.arange(18,33,2),np.arange(36,61,4)],
                    strong=np.r_[np.arange(1,25),[28,32,36,40,46,54,62]])
    variants={'linear':np.arange(1,128,2)}
    for name,positive in magnitudes.items():
        assert len(positive)==31
        variants[name]=np.r_[64-positive[::-1],64,64,64+positive]
    rows=[]
    for name,targets in variants.items():
        words,nxt,mapping,layout=make_table(targets,meta['model'])
        if name=='linear':
            old_w,old_n,_=integral_table(64,2,holds=meta['model']['holds'],beta=meta['model']['beta'],extent=meta['model']['extent'])
            assert np.array_equal(words,old_w) and np.array_equal(nxt,old_n) and np.array_equal(mapping,np.arange(256)//4)
        bits,end=render_levels(mapping[pcm8],meta,words,nxt);actual=filtered(reconstruct(bits,t),a.ffmpeg)
        row=dict(name=name,fixed_clock_snr_db=ratio(ref,actual[4410:-4410]-ref),target_numerators_128=targets.tolist(),
                 final_state=end,**layout,new_timeline_verified=False,planned_ordinary_native_tstate_delta=0)
        rows.append(row);write_wav(a.output/(name+'-preview.wav'),actual);print(json.dumps(row),flush=True)
    (a.output/'report.json').write_text(json.dumps(dict(scope=__doc__,input=str(a.input),rows=rows),indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
