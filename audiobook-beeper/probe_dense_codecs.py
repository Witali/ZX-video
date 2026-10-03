"""Bounded codec-only rate/distortion study; no new Z80/PDM player is implied.

Compare the same complete PCM8 excerpt. Dictionaries are transmitted in the
image and counted in the totals. Per-recording training is an encoder feature,
not free decoder state. Quality excludes the PDM modulator and actual timing.
"""
import argparse,gzip,hashlib,heapq,json,math,subprocess,time,wave
from pathlib import Path
import numpy as np
from ima_codec import STEPS,decode
from assess_snr import FILTER,ratio
from build_pdm import write_wav


def encode3(source,adjustment,width=32,block=64):
    steps=np.asarray(STEPS,dtype=np.int64)[:,None]
    codes=np.arange(8);mag=codes&3
    delta=(steps>>3)+(steps//2)*((mag&1)!=0)+steps*((mag&2)!=0)
    delta*=np.where(codes&4,-1,1)
    successor=np.clip(np.arange(89)[:,None]+np.array(adjustment)[mag],0,88)
    target=(source.astype(np.int64)-128)*256;chosen=np.empty(len(source),dtype='u1')
    predictor=index=0
    for start in range(0,len(target),block):
        values=target[start:start+block];pred=np.array([predictor]);idx=np.array([index]);cost=np.zeros(1,dtype=np.int64)
        paths=np.zeros((1,len(values)),dtype='u1')
        for position,value in enumerate(values):
            predicted=(pred[:,None]+delta[idx]).ravel();next_idx=successor[idx].ravel()
            score=(cost[:,None]+(predicted.reshape(-1,8)-value)**2).ravel()
            ids=np.flatnonzero((predicted>=-32768)&(predicted<=32767));key=(predicted[ids]+32768)*89+next_idx[ids]
            order=np.lexsort((ids,score[ids],key));ordered=ids[order]
            ordered=ordered[np.r_[True,key[order][1:]!=key[order][:-1]]]
            best=ordered[np.lexsort((ordered,score[ordered]))[:width]]
            paths=paths[best//8].copy();paths[:,position]=best%8
            pred,idx,cost=predicted[best],next_idx[best],score[best]
        chosen[start:start+len(values)]=paths[0];predictor,index=int(pred[0]),int(idx[0])
    # Independent scalar recurrence; do not use beam predictor arrays as output.
    decoded=[];predictor=index=0
    for code in chosen:
        step=STEPS[index];m=int(code)&3;d=(step>>3)+(step//2 if m&1 else 0)+(step if m&2 else 0)
        predictor+=-d if code&4 else d;assert -32768<=predictor<=32767
        index=max(0,min(88,index+adjustment[m]));decoded.append(predictor)
    return chosen,np.asarray(decoded,dtype=np.int16)


def pack_codes(codes,bits):
    array=((codes.astype(np.uint32)[:,None]>>np.arange(bits-1,-1,-1))&1).astype('u1').ravel()
    packed=np.packbits(array).tobytes()
    restored=np.unpackbits(np.frombuffer(packed,'u1'))[:len(codes)*bits].reshape(-1,bits)@(1<<np.arange(bits-1,-1,-1))
    assert np.array_equal(restored,codes)
    return packed


def vq(source,dimensions,count,iterations=24):
    missing=(-len(source))%dimensions
    x=np.pad(source,(0,missing),constant_values=128).reshape(-1,dimensions).astype(np.float32)
    rng=np.random.default_rng(1977);centers=[x[rng.integers(len(x))].copy()]
    nearest=np.sum((x-centers[0])**2,axis=1)
    for _ in range(1,count):
        total=nearest.sum()
        pick=rng.choice(len(x),p=(nearest/total).astype(float)/np.sum((nearest/total).astype(float))) if total else rng.integers(len(x))
        centers.append(x[pick].copy());nearest=np.minimum(nearest,np.sum((x-centers[-1])**2,axis=1))
    centers=np.asarray(centers);previous=None
    def assign(c):
        result=np.empty(len(x),dtype=np.int64)
        norm=np.sum(c*c,axis=1)
        for begin in range(0,len(x),4096):
            block=x[begin:begin+4096]
            result[begin:begin+len(block)]=np.argmin(norm[None,:]-2*block@c.T,axis=1)
        return result
    for iteration in range(iterations):
        ids=assign(centers)
        if previous is not None and np.array_equal(ids,previous):break
        previous=ids;totals=np.zeros_like(centers);counts=np.bincount(ids,minlength=count)
        np.add.at(totals,ids,x);active=counts>0;centers[active]=totals[active]/counts[active,None]
    # Hardware reads PCM8 dictionary bytes; measure that exact quantized book.
    book=np.clip(np.rint(centers),0,255).astype('u1');ids=assign(book.astype(np.float32))
    restored=book[ids].ravel()[:len(source)]
    return ids,book,restored,iteration+1


def filtered(values,ffmpeg):
    result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar','8000','-ac','1','-i','-',
                           '-af','aresample=44100,'+FILTER,'-f','f32le','-'],input=np.asarray(values,dtype='<f4').tobytes(),capture_output=True,check=True)
    return np.frombuffer(result.stdout,'<f4').astype(float)


def predictive_vq(source,half_predictor,count=512):
    """Three-sample residual vectors, with an integer block predictor.

    The dictionary is trained on teacher-forced residuals; encoding itself
    feeds back the actual reconstructed last sample. Invalid signed-byte
    outputs are forbidden, so a Z80 decoder would need no saturation branch.
    """
    n=len(source);x=np.pad(source,((0,(-n)%3)),constant_values=128).reshape(-1,3).astype(np.int32)-128
    previous=np.r_[0,x[:-1,-1]];base=previous//2 if half_predictor else previous
    residual=x-base[:,None];clipped=int(np.count_nonzero((residual<-128)|(residual>127)))
    training=(np.clip(residual,-128,127)+128).astype('u1').ravel()
    _,raw_book,_,iterations=vq(training,3,count)
    book=raw_book.astype(np.int32)-128;lo=book.min(axis=1);hi=book.max(axis=1)
    decoded=np.empty_like(x);indices=np.empty(len(x),dtype=np.int64);last=0
    for i,target in enumerate(x):
        base=last//2 if half_predictor else last
        error=np.sum((book-(target-base))**2,axis=1)
        valid=(lo+base>=-128)&(hi+base<=127)
        assert valid.any()
        index=int(np.argmin(np.where(valid,error,np.iinfo(np.int32).max)))
        indices[i]=index;decoded[i]=book[index]+base;last=int(decoded[i,-1])
    assert decoded.min()>=-128 and decoded.max()<=127
    return indices,book.astype('i1'),decoded.ravel()[:n],clipped,iterations


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
    with wave.open(str(a.input/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    signal=(source.astype(float)-128)/128;ref=filtered(signal,a.ffmpeg);rows=[]
    def result(name,decoded,payload,book=b'',**extra):
        actual=filtered(decoded,a.ffmpeg);edge=min(4410,len(ref)//10)
        row=dict(name=name,samples=len(source),payload_bytes=len(payload),dictionary_bytes=len(book),total_codec_bytes=len(payload)+len(book),
                 payload_bits_per_sample=len(payload)*8/len(source),codec_only_snr_db=ratio(ref[edge:-edge],actual[edge:-edge]-ref[edge:-edge]),
                 raw_pcm_snr_db=ratio(signal,np.asarray(decoded)-signal),z80_ported=False,real_time_verified=False,**extra)
        (out/(name+'.data.gz')).write_bytes(gzip.compress(payload,mtime=0))
        if book:(out/(name+'.book.gz')).write_bytes(gzip.compress(book,mtime=0))
        write_wav(out/(name+'-preview.wav'),actual)
        rows.append(row);print(json.dumps(row),flush=True)
    packed=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes());pcm,_=decode(packed)
    result('ima4',pcm/32768,packed,existing_decoder=True)
    nib=np.frombuffer(packed,'u1');nibbles=np.r_[nib&15,nib>>4]
    entropy=[]
    for title,data,symbol_bits in [('IMA nibbles',nibbles,4),('IMA bytes',nib,8)]:
        counts=np.bincount(data);counts=counts[counts>0];prob=counts/counts.sum()
        heap=list(map(int,counts));heapq.heapify(heap);total=0
        while len(heap)>1:
            joined=heapq.heappop(heap)+heapq.heappop(heap);total+=joined;heapq.heappush(heap,joined)
        entropy.append(dict(alphabet=title,entropy_bits_per_symbol=float(-sum(prob*np.log2(prob))),huffman_payload_bytes=math.ceil(total/8),codebook_not_counted=True))
    for adjustment in [(-1,-1,2,4),(-1,-1,2,6)]:
        started=time.monotonic();codes,decoded=encode3(source,adjustment)
        result('adpcm3-step'+str(adjustment[-1]),decoded/32768,pack_codes(codes,3),
               adjustment=list(adjustment),beam_width=32,encoder_seconds=time.monotonic()-started,decoder_table_bytes=89*8*4)
    for dimensions,count in [(3,256),(3,512),(4,1024)]:
        started=time.monotonic();codes,book,decoded,iterations=vq(source,dimensions,count)
        result(f'vq{dimensions}x{count}',(decoded.astype(float)-128)/128,pack_codes(codes,int(math.log2(count))),book.tobytes(),
               dimensions=dimensions,entries=count,iterations=iterations,encoder_seconds=time.monotonic()-started)
    for count in (512,1024):
        for half in (False,True):
            started=time.monotonic();codes,book,decoded,clipped,iterations=predictive_vq(source,half,count)
            result(f'pvq3x{count}-'+('half' if half else 'last'),decoded/128,pack_codes(codes,int(math.log2(count))),book.tobytes(),
                   dimensions=3,entries=count,predictor='floor(last/2)' if half else 'last',
                   teacher_residuals_clipped=clipped,decoded_samples_clipped=0,iterations=iterations,
                   encoder_seconds=time.monotonic()-started)
    report=dict(scope=__doc__,date='2026-10-03',source_directory=str(a.input),source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                rows=rows,ima_entropy=entropy,ima_gzip_bytes=len(gzip.compress(packed,mtime=0)),filter='FFmpeg 8k->44.1k, '+FILTER,
                decision='Codec-only feasibility results; do not select a new player without counted Z80 and full PDM timing/quality checks.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
