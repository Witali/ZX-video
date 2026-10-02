"""Build, verify and render the separate live block-feedback experiment."""
import argparse,gzip,hashlib,json,subprocess,sys,wave
from pathlib import Path
import numpy as np
from feedback_player import HERE,prepare
from verify_feedback import reference,intervals,native_check,fuse_check
from verify_ima import reference as old_reference
from build_pdm import reconstruct,write_wav,RATE
from assess_snr import first_order,FILTER,ratio
from pdm_player import CPU_CLOCK
from verify_pdm import save


def sha(data):return hashlib.sha256(data).hexdigest()


def render(out,ffmpeg,native=False):
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    pcm,_,levels,weights,bits=reference(packed,meta);count=8*int(weights.sum())
    if native:times=np.r_[0,np.cumsum(intervals(meta))]
    else:times=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count+1]
    with wave.open(str(out/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    d=np.repeat(levels,weights*8);s=np.repeat(source,weights*8)
    signals=dict(feedback=reconstruct(bits[:count],times),decoded=reconstruct(d/256,times),
                 source=reconstruct(s/256,times),ordinary_same_timing=reconstruct(first_order(d),times))
    # Match the unchanged release to the same prefix (last .1 s is excluded).
    baseline=HERE/'experiments/ima-uniform73';oldmeta=json.loads((baseline/'player.json').read_bytes())
    oldpacked=gzip.decompress((baseline/'soundtrack.ima.gz').read_bytes())
    assert oldpacked[:len(packed)-80]==packed[:-80],'source changed before the final 20-ms fade'
    _,_,oldd,oldbits,_=old_reference(oldpacked,oldmeta)
    oldweights=np.full(oldmeta['pcm_samples'],6,dtype=np.int32);offset=0
    for section in oldmeta['sections']:
        for end in range(offset+256,offset+section['bytes'],256):oldweights[2*end-2]=7
        offset+=section['bytes'];oldweights[2*offset-2]=11
    oldcount=int(oldweights[:len(source)].sum())
    oldt=np.frombuffer(gzip.decompress((baseline/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:oldcount+1]
    oldsource=np.repeat(source,oldweights[:len(source)])
    signals['old_pdm']=reconstruct(oldbits[:oldcount],oldt)
    signals['old_decoded']=reconstruct(np.r_[np.zeros(3),oldd[:oldcount-3]/256],oldt)
    signals['old_source']=reconstruct(np.r_[np.zeros(3),oldsource[:-3]/256],oldt)
    filtered={}
    for name,signal in signals.items():
        result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                               '-af',FILTER,'-ar','44100','-f','f32le','-'],
                              input=signal.astype('<f4').tobytes(),capture_output=True,check=True)
        filtered[name]=np.frombuffer(result.stdout,'<f4').astype(float)
    def snr(signal,ref):
        a=filtered[ref][4410:-4410];b=filtered[signal][4410:-4410]
        return ratio(a,b-a)
    gain=min(1,.9/max(np.max(abs(filtered[k])) for k in ('feedback','old_pdm','source')))
    for key in ('feedback','old_pdm','source'):write_wav(out/(key.replace('_','-')+'-bandlimited-preview.wav'),filtered[key]*gain)
    return dict(scope='Native timing model' if native else 'Measured full Fuse timing; integrated port output, not a speaker or RC model',
                filter=FILTER,common_gain=float(gain),excluded_edge_seconds=.1,
                feedback_modulator_snr_db=snr('feedback','decoded'),feedback_total_snr_db=snr('feedback','source'),
                old_pdm_modulator_snr_db=snr('old_pdm','old_decoded'),old_pdm_total_snr_db=snr('old_pdm','old_source'),
                ordinary_same_timing_model_modulator_snr_db=snr('ordinary_same_timing','decoded'),
                duration_seconds=float(times[-1]/CPU_CLOCK),old_duration_seconds=float(oldt[-1]/CPU_CLOCK),
                time_alignment='each reference follows its own sample schedule; no fitted phase/gain or tempo correction')


def finish(out,ffmpeg):
    proof=json.loads((out/'verification.json').read_bytes());assert proof['complete']
    metrics=render(out,ffmpeg);capture=out/'sound-128/fuse-preview.wav';delivery=None
    if capture.exists():
        with wave.open(str(capture),'rb') as w:
            params=w.getparams();count=round(proof['fuse']['cycle_durations_seconds'][0]*params.framerate);raw=w.readframes(count)
        assert (params.nchannels,params.sampwidth,params.framerate)==(1,2,44100)
        assert len(raw)==count*2
        with wave.open(str(out/'result-preview.wav'),'wb') as w:w.setparams(params);w.writeframes(raw)
        delivery=dict(scope='Ready-aligned actual Fuse audio, first loop; no added gain or filter',frames=count,
                      sample_rate_hz=44100,pcm_sha256=sha(raw),
                      peak_pcm16=int(np.max(abs(np.frombuffer(raw,'<i2').astype(np.int32)))))
    sources={};archive=out/'producer-source';archive.mkdir(exist_ok=True)
    for name in ('ima-feedback-player.asm','feedback_player.py','verify_feedback.py','build_feedback.py','test_feedback.py','pack_ima.py',
                 'ima_codec.py','ima_player.py','pdm_player.py','record_pcm.py','build_pdm.py','assess_snr.py','verify_ima.py'):
        data=(HERE/name).read_bytes().replace(b'\r\n',b'\n');sources[name]=sha(data)
        (archive/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    save(out/'report.json',dict(date='2026-10-02',complete=True,preview_only=True,verification=proof,render=metrics,
                               delivery=delivery,source_sha256_lf=sources,
                               artifacts={p.relative_to(out).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
                                          for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('report.json','fuse-stderr.txt','capture.fmf')}))
    return metrics


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path);p.add_argument('--ffmpeg',required=True);p.add_argument('--record',action='store_true')
    args=p.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):p.error('output must be empty')
    disk,meta,packed=prepare(out)
    native=native_check(disk,meta,packed);print(json.dumps(native),flush=True)
    actual=fuse_check(args.fuse,out,meta,packed);save(out/'verification.json',dict(complete=True,native=native,fuse=actual))
    print(json.dumps(actual),flush=True)
    if args.record:subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),
                                  '--output',str(out/'sound-128'),'--machine','128'],check=True)
    print(json.dumps(finish(out,args.ffmpeg)),flush=True)


if __name__=='__main__':main()
