"""Eight-bit G.711 in RAM, calibrated approximately128-kHz packet PDM."""
from functools import partial
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave
import numpy as np
from convert_mulaw_audio import prepare,filter_signal
from convert_audio import calibrate,snapshot_sources
from g711_codec import encode,verify_tables
from mulaw_packet import MODEL,CPU,build_disk,layout,reference
from verify_mulaw_packet import native_check,fuse_check,rational_check
from verify_pdm import save
from assess_snr import ratio
from build_pdm import write_wav

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_bytes())


def snapshot(out):
    """Extend the common producer snapshot with this profile's dependencies."""
    snapshot_sources(out)
    archive=out/'producer-source';hashes=read(archive/'hashes.json')
    names=('convert_mulaw_packet.py','convert_mulaw_audio.py','mulaw_packet.py',
        'mulaw-packet-player.asm','mulaw_packet_encoder.py','verify_mulaw_packet.py',
        'mulaw_player.py','mulaw-player.asm','verify_mulaw.py',
        'mulaw_waveform_encoder.py','g711_codec.py','verify_pdm.py')
    for name in names:
        data=(HERE/name).read_bytes().replace(b'\r\n',b'\n')
        hashes[name]=hashlib.sha256(data).hexdigest()
        (archive/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    save(archive/'hashes.json',hashes)


def write_candidate(out,payload,pcm,hot=None,pairs=0,pad=0,model=MODEL):
    out.mkdir(parents=True,exist_ok=True)
    disk,meta=build_disk(payload,out/'assembly',model,pairs,pad)
    (out/'audiobook-preview.trd').write_bytes(disk);(out/'soundtrack.mulaw').write_bytes(payload);save(out/'player.json',meta)
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(pcm.astype('<i2').tobytes())
    return disk,meta

def score(out,meta,payload,pcm,ffmpeg):
    timeline=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    bits,_=reference(payload,meta['model'],idle_pairs=meta['loop_idle_pairs'])
    n=meta['outputs_per_cycle'];rows=[]
    for cycle in range(2):
        t=timeline[cycle*n:(cycle+1)*n+1].copy();t-=t[0]
        period=CPU/8000;count=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(count)*period,t[-1]]
        values=np.pad((pcm.astype(float)+32768)/65536,(0,max(0,count-len(pcm))),constant_values=.5)[:count]
        source=filter_signal(values,edges,ffmpeg,768000)
        actual=filter_signal(bits[cycle*n:(cycle+1)*n],t,ffmpeg,768000)
        cut=slice(4410,-4410)
        # SNR is undefined for a silent reference. Keep valid JSON and do
        # not claim a quality target from zero signal power.
        rows.append(ratio(source[cut],actual[cut]-source[cut]) if np.any(source[cut]) else None)
        if cycle==0:
            write_wav(out/'reference-preview.wav',source*.5);write_wav(out/'output-preview.wav',actual*.5)
    measured=[r for r in rows if r is not None]
    result=dict(two_loop_fixed_clock_snr_db=rows,minimum_snr_db=min(measured) if measured else None,reference_rate_hz=8000,
        integration_rate_hz=768000,filter_precision='f64',listening_gain=.5,fitted_gain_delay_or_time_stretch=False)
    save(out/'quality.json',result);return result

def qualify(out,payload,pcm,fuse,ffmpeg,model=MODEL):
    chosen,meta=calibrate(out/'calibration',payload,pcm,fuse,hot=[],writer=partial(write_candidate,model=model))
    disk=(chosen/'audiobook-preview.trd').read_bytes()
    native=native_check(disk,meta,payload);save(chosen/'native.json',native)
    actual=fuse_check(fuse,chosen,meta,payload);save(chosen/'fuse.json',actual)
    periods=[round(s*CPU) for s in actual['cycle_durations_seconds']];target=round(periods[1]/70908)*70908
    deltas=[p-target for p in periods];assert abs(deltas[0])<=3 and deltas[1]==0,('phase drift',deltas)
    quality=score(chosen,meta,payload,pcm,ffmpeg)
    for p in chosen.iterdir():
        if p.is_file():shutil.copy2(p,out/p.name)
    shutil.copytree(chosen/'assembly',out/'assembly')
    report=dict(complete=True,quality=quality,fuse=actual,native=native,phase_deltas_tstates=deltas,
        selected=str(chosen.relative_to(out)),trd_sha256=hashlib.sha256(disk).hexdigest())
    save(out/'report.json',report);print(dict(packet_candidate=str(out),snr=quality['minimum_snr_db'],
        rate=actual['signal_pdm_rate_hz'],speed=actual['speed_error_percent']),flush=True)
    return report

def convert(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    capacity=sum(size for _,_,size in layout()[-1])
    pcm,preparation=prepare(args.input,args.ffmpeg,args.duration,args.prepared_pcm,capacity=capacity,dynamics=getattr(args,'dynamics','gentle'))
    save(out/'preparation.json',preparation);snapshot(out)
    save(out/'rational-tables.json',rational_check(MODEL));verify_tables(args.ffmpeg)
    payload=encode(pcm,'mulaw',args.ffmpeg)
    pilot=out/'pilot';initial=qualify(pilot,payload,pcm,args.fuse,args.ffmpeg)
    candidates=[dict(directory='pilot',**initial)]
    if args.quality=='best' and np.any(pcm):
        from mulaw_packet_encoder import encode as waveform
        meta=read(pilot/'player.json')
        times=np.frombuffer(gzip.decompress((pilot/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
        for width,horizon,weight in ((16,16,.1),(64,32,.03)):
            folder=out/f'waveform-{width}';folder.mkdir()
            statistics={};packed=waveform(pcm,meta,times,width=width,horizon=horizon,commit=8,regularization=weight,statistics=statistics)
            statistics.update(source_sha256=preparation['source_sha256'],
                clock_sha256=hashlib.sha256((pilot/'output-times.u32.gz').read_bytes()).hexdigest(),
                payload_sha256=hashlib.sha256(packed).hexdigest())
            save(folder/'search.json',statistics)
            result=qualify(folder,packed,pcm,args.fuse,args.ffmpeg)
            candidates.append(dict(directory=folder.name,**result));save(out/'candidates.json',candidates)
    best=max(candidates,key=lambda c:c['quality']['minimum_snr_db']
             if c['quality']['minimum_snr_db'] is not None else -math.inf)
    selected=out/best['directory']
    for p in selected.iterdir():
        if p.is_file():shutil.copy2(p,out/p.name)
    shutil.copytree(selected/'assembly',out/'assembly')
    recording=None
    if not args.no_recording:
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(args.fuse),'--output',str(out/'recording')],check=True)
        recording=read(out/'recording/report.json')
        assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
    report=dict(complete=True,codec='mulaw',pdm_profile='sixteen-pulse packets',requested_pdm_rate_hz=128000,
        source=preparation,selected=best,candidates=candidates,recording=recording,
        target_30_db_passed=(best['quality']['minimum_snr_db'] is not None and best['quality']['minimum_snr_db']>=30),physical_hardware_tested=False,
        limitations=['Bounded measured search; no universal optimum or30-dB guarantee',
            'Packet feedback is quantized; standard G.711 levels enter the tables at full16-bit precision',
            'One resident looping prefix; table space reduces duration relative to the64-kHz control'])
    save(out/'report.json',report)
    print(dict(complete=True,disk=str(out/'audiobook-preview.trd'),snr_db=best['quality']['minimum_snr_db'],
        pdm_rate_hz=best['fuse']['signal_pdm_rate_hz']),flush=True)
    return report
