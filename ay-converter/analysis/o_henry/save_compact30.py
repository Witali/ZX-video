"""Check and preserve the requested 30-second current-engine speech audition."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
from verify_preview import expected_registers


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path);parser.add_argument('--log',type=Path,required=True);args=parser.parse_args()
    report=json.loads((args.build/'report.json').read_bytes())
    previous=json.loads((HERE/'evidence/release/report.json').read_bytes())
    assert report['complete'] and report['source_sha256']==previous['source_sha256']
    assert report['start_seconds']==60 and report['duration_seconds']==30 and report['ticks']==1500
    assert report['profile']=='auto' and report['target_chip']=='AY-3-8910' and report['dynamics']=='compact'
    width=report['square_fit']['packed_state_bytes']
    packed=gzip.decompress((args.build/f'soundtrack.ay{width}.gz').read_bytes())
    raw=gzip.decompress((args.build/'registers.gz').read_bytes())
    assert len(packed)==1500*width and raw==expected_registers(packed,width)
    assert sha(raw)==report['registers_sha256']
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert sha((CORE/name).read_bytes().replace(b'\r\n',b'\n'))==digest,name
    waves={}
    for name,rate in (('ay-preview.wav',44100),('original-preview.wav',22050)):
        with wave.open(str(args.build/name),'rb') as audio:
            assert audio.getframerate()==rate and audio.getnframes()==30*rate
            assert audio.getnchannels()==1 and audio.getsampwidth()==2
            samples=np.frombuffer(audio.readframes(audio.getnframes()),'<i2').astype(float)/32768
        waves[name]=dict(seconds=30,rate=rate,peak=float(abs(samples).max()),rms=float(np.sqrt(np.mean(samples**2))),
            clipped_samples=int(np.count_nonzero(abs(samples)>=32767/32768)),sha256=sha((args.build/name).read_bytes()))
        assert waves[name]['clipped_samples']==0
    for name,item in report['artifacts'].items():
        data=(args.build/name).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],name
    target=HERE/'evidence/compact30'
    if target.exists():raise ValueError('archive already exists')
    shutil.copytree(args.build,target);shutil.copyfile(args.log,target/'conversion.log')
    result=dict(complete=True,date='2026-10-13',baseline_commit='38514c98',source_interval_seconds=[60,90],
        duration_seconds=30,ticks=1500,target_chip='AY-3-8910',dynamics='compact',
        packed_state_bytes=width,register_bytes_per_state=len(raw)//1500,waves=waves,
        source_and_producer_hashes_exact=True,packed_registers_exact=True,
        scope='Current public converter simulation WAV. Generated player is retained as a build artifact; no new Fuse or physical-hardware qualification requested or claimed.')
    (target/'audition-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in target.rglob('*') if p.is_file()}
    (target/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__=='__main__':main()
