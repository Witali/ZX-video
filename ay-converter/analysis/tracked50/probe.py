"""Bounded channel-persistence/noise experiment, compared with the saved v1."""
import argparse
import gzip
from pathlib import Path
import subprocess
import sys
import json
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'analysis/entertainer'))
from probe import decode,onset_proxy
import music_profile as music
import channel_tracking as tracking
from ay_format import AyFrame,registers
import quality
import spectrogram
from support import save,sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','output','ffmpeg','node'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    samples = decode(args.ffmpeg,args.input,duration=32.128)
    original = samples[:1556*441]
    print('Analyse unchanged source once',flush=True)
    features = music.analyse(samples)
    reference = spectrogram.features(original)
    coarse = quality.features(original,22050,10,312)
    onsets = onset_proxy(original)
    results = {}
    for name,selection,enabled in [('music_v1',None,None),('roles_mixed','roles',True),
                                   ('dominant_tones','dominant',False),('dominant_mixed','dominant',True)]:
        print('Render '+name,flush=True)
        out = args.output/name
        out.mkdir()
        if selection is None:
            raw = gzip.decompress((args.baseline/'registers.gz').read_bytes())
            metadata = dict(control='exact saved register stream')
        else:
            p,v,paths,n,_,metadata = tracking.arrange(features,selection=selection,noise_enabled=enabled)
            raw = b''.join(registers(AyFrame(tuple(map(int,a)),tuple(map(int,b)),int(c),int(d)))
                for a,b,c,d in zip(p[:1556],v[:1556],n[:1556],metadata['mixers'][:1556]))
        (out/'registers.gz').write_bytes(gzip.compress(raw,mtime=0))
        (out/'arrangement.json.gz').write_bytes(gzip.compress(json.dumps(metadata).encode(),mtime=0))
        subprocess.run([str(args.node),str(HERE/'render_ym2149.js'),str(out/'registers.gz'),
            str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
        audio = np.frombuffer((out/'chip.f32').read_bytes(),'<f4').astype(float)
        quality.write_wav(out/'preview.wav',audio*min(.1/max(np.sqrt(np.mean(audio**2)),1e-12),.9/max(abs(audio))),44100)
        down = np.frombuffer(subprocess.run([str(args.ffmpeg),'-v','error','-nostdin','-f','f32le',
            '-ar','44100','-ac','1','-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],
            capture_output=True,check=True).stdout,'<f4').astype(float)
        result = dict(selection=selection,noise_enabled=enabled,registers_sha256=sha(raw),
            stft=spectrogram.compare(reference,spectrogram.features(down)),
            metrics=quality.compare(coarse,quality.features(down,22050,10,312)),
            onset_20ms=quality.match_onsets(onsets,onset_proxy(down),2),
            noise_ticks=sum(raw[i+6]>0 for i in range(0,len(raw),11)),
            component_count=metadata.get('component_count'),channel_migrations=metadata.get('component_channel_migrations'))
        results[name] = result
        save(args.output/'results.partial.json',results)
        print(json.dumps(dict(name=name,**result)),flush=True)
        (out/'chip.f32').unlink()
    save(args.output/'results.json',dict(date='2026-10-04',update_rate_hz=50,quantum_ms=20,
        source_sha256=sha(args.input.read_bytes()),ticks=1556,variants=results,
        scope='Four complete host renders; actual Fuse qualification is separate.',
        sources_sha256_lf={p.relative_to(HERE).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n'))
            for p in [Path(__file__),HERE/'channel_tracking.py',HERE/'ay_format.py',HERE/'music_profile.py']}))


if __name__ == '__main__':
    main()
