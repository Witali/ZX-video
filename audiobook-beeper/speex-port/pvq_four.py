"""Compare a four-sample predictive VQ format against the selected three-sample player."""
import json
from pathlib import Path
import struct
import time
import wave
import numpy as np
from check_approx import snr
from pvq_improve import archive,check_variant,read_encoded
from verify import ROOT,HERE,sha

def vq(source,dimensions,count,iterations=24):
    """Same seeded K-means as probe_dense_codecs.vq, without its PDM/OpenCV imports."""
    x=source.reshape(-1,dimensions).astype(np.float32)
    rng=np.random.default_rng(1977);centers=[x[rng.integers(len(x))].copy()]
    nearest=np.sum((x-centers[0])**2,axis=1)
    for _ in range(1,count):
        total=nearest.sum()
        pick=rng.choice(len(x),p=(nearest/total).astype(float)/np.sum((nearest/total).astype(float))) if total else rng.integers(len(x))
        centers.append(x[pick].copy());nearest=np.minimum(nearest,np.sum((x-centers[-1])**2,axis=1))
    centers=np.asarray(centers);previous=None
    def assign(c):
        result=np.empty(len(x),dtype=np.int64);norm=np.sum(c*c,axis=1)
        for begin in range(0,len(x),4096):
            block=x[begin:begin+4096]
            result[begin:begin+len(block)]=np.argmin(norm[None,:]-2*block@c.T,axis=1)
        return result
    for iteration in range(iterations):
        ids=assign(centers)
        if previous is not None and np.array_equal(ids,previous):break
        previous=ids;totals=np.zeros_like(centers);counts=np.bincount(ids,minlength=count)
        np.add.at(totals,ids,x);active=counts>0;centers[active]=totals[active]/counts[active,None]
    book=np.clip(np.rint(centers),0,255).astype('u1');ids=assign(book.astype(np.float32))
    return ids,book,book[ids].ravel(),iteration+1


def encode(source,book):
    dimensions=book.shape[1]
    x=np.pad(source,(0,(-len(source))%dimensions),constant_values=128).reshape(-1,dimensions).astype(np.int32)-128
    book=book.astype(np.int32);lo=book.min(axis=1);hi=book.max(axis=1)
    ids=np.empty(len(x),dtype=np.int32);decoded=np.empty_like(x);last=0
    for i,target in enumerate(x):
        base=last//2
        error=np.sum((book-(target-base))**2,axis=1)
        valid=(lo+base>=-128)&(hi+base<=127)
        assert valid.any(),('no non-clipping vector',i,base)
        index=int(np.argmin(np.where(valid,error,np.iinfo(np.int32).max)))
        ids[i]=index;decoded[i]=book[index]+base;last=int(decoded[i,-1])
    padded=np.pad(ids,(0,(-len(ids))%4))
    stream=bytearray()
    for start in range(0,len(padded),4):
        group=padded[start:start+4]
        stream.append(sum(int(code>>8)<<(2*i) for i,code in enumerate(group)))
        stream.extend((group&255).tolist())
    header=struct.pack('<4sBBBBIII',b'PVQ8',1,dimensions,10,0,8000,len(source),len(stream)).ljust(32,b'\0')
    encoded=header+book.astype('i1').tobytes()+stream
    expected=bytes((decoded.ravel()[:len(source)]+128).astype('u1'))
    assert read_encoded(encoded)[2]==expected
    return encoded,expected,ids


def main():
    out=ROOT/'build/speex-port/pvq-r14';out.mkdir(parents=True,exist_ok=True)
    original=HERE/'rounds/12/report.json';baseline=json.loads(original.read_text())
    source_path=Path('C:/Work/ZX-video/audiobook-beeper/experiments/ima-waveform/source-preview.wav')
    with wave.open(str(source_path),'rb') as w:
        assert w.getparams()[:3]==(1,1,8000)
        raw=w.readframes(w.getnframes())
    assert sha(raw)==baseline['source_pcm8_sha256']
    source=np.frombuffer(raw,'u1')
    cache=out/'teacher.book';cache_meta=out/'teacher-book.json'
    training_key=dict(source_sha256=sha(raw),dimensions=4,entries=1024,seed=1977,
                      max_iterations=24,algorithm='teacher-half-predictor-kmeans-v1',numpy=np.__version__)
    started=time.monotonic()
    x=source.reshape(-1,4).astype(np.int32)-128
    base=np.r_[0,x[:-1,-1]]//2
    residual=x-base[:,None];clipped=int(np.count_nonzero((residual<-128)|(residual>127)))
    cached=json.loads(cache_meta.read_text()) if cache_meta.exists() else {}
    cached_bytes=cache.read_bytes() if cache.exists() else b''
    if (cached.get('key')==training_key and len(cached_bytes)==4096
            and cached.get('book_sha256')==sha(cached_bytes)):
        book=np.frombuffer(cached_bytes,'i1').reshape(1024,4);iterations=cached['iterations']
    else:
        _,raw_book,_,iterations=vq((np.clip(residual,-128,127)+128).astype('u1').ravel(),4,1024)
        book=(raw_book.astype(np.int32)-128).astype('i1');cache.write_bytes(book.tobytes())
        cache_meta.write_text(json.dumps(dict(key=training_key,book_sha256=sha(book.tobytes()),
                                             iterations=iterations),indent=2)+'\n')
    encoded,expected,ids=encode(source,book)
    quality=snr([x-128 for x in raw],[x-128 for x in expected])
    print('VQ4 quality',quality,'loss',baseline['raw_source_snr_db']-quality,'bytes',len(encoded),flush=True)
    (out/'audio.pvq').write_bytes(encoded)
    report=check_variant(out,encoded,tight=True)
    total=report['unpaced']['total_cpu_tstates'];loss=baseline['raw_source_snr_db']-quality
    report.update(source_pcm8_sha256=sha(raw),training='Round12 K-means method, now four teacher-forced residuals per vector',
                  teacher_residuals_clipped=clipped,decoded_samples_clipped=0,
                  training_iterations=iterations,training_key=training_key,book_sha256=sha(book.tobytes()),
                  encoder_and_verification_seconds=time.monotonic()-started,
                  raw_source_snr_db=quality,baseline_raw_source_snr_db=baseline['raw_source_snr_db'],snr_loss_db=loss,
                  mean_tstates_per_sample=total/len(raw),speed_target_pass=total/len(raw)<=80,
                  stored_size_target_bytes=62528,quality_gate_max_snr_loss_db=1,quality_gate_pass=loss<=1,
                  stored_size_target_pass=len(encoded)<=62528)
    accepted=all(report[k] for k in ('quality_gate_pass','speed_target_pass','stored_size_target_pass'))
    report['decision']=('Select four-sample format' if accepted else
                        'Reject four-sample format: one or more declared gates fail; keep round13.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    archive(out,'14',encoded,report)
    print({k:v for k,v in report.items() if k not in ('paced','unpaced','tails','instruction_audit')},flush=True)


if __name__=='__main__':main()
