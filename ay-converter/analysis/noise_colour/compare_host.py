"""Four complete host ablations isolate level, period and their combination."""
import argparse
import gzip
from pathlib import Path
import subprocess
import sys
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'analysis/entertainer'))
from probe import decode,onset_proxy
from support import save,sha
import spectrogram
import quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','candidate','ffmpeg','node','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    old,new = [np.frombuffer(gzip.decompress((d/'registers.gz').read_bytes()),np.uint8).reshape(-1,11)
               for d in (args.baseline,args.candidate)]
    level = old.copy(); level[:,8:] = new[:,8:]
    period = old.copy(); period[:,6] = new[:,6]
    samples = decode(args.ffmpeg,args.input,duration=len(new)/50)[:len(new)*441]
    reference = spectrogram.features(samples)
    onsets = onset_proxy(samples)
    mask = old[:,6] > 0
    results = {}
    for name,raw in [('previous',old),('level_only',level),('period_only',period),('joint_fit',new)]:
        out = args.output/name
        out.mkdir(exist_ok=True)
        (out/'registers.gz').write_bytes(gzip.compress(raw.tobytes(),mtime=0))
        subprocess.run([str(args.node),str(HERE/'render_ym2149.js'),str(out/'registers.gz'),
            str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
        audio = np.frombuffer(subprocess.run([str(args.ffmpeg),'-v','error','-f','f32le','-ar','44100','-ac','1',
            '-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
        features = spectrogram.features(audio)
        results[name] = dict(registers_sha256=sha(raw.tobytes()),
            stft=spectrogram.compare(reference,features),
            noisy_stft=spectrogram.compare({k:(a[mask],r[mask]) for k,(a,r) in reference.items()},
                                          {k:(a[mask],r[mask]) for k,(a,r) in features.items()}),
            onset_20ms=quality.match_onsets(onsets,onset_proxy(audio),2))
        (out/'chip.f32').unlink()
        print(name,results[name]['stft'],flush=True)
    save(args.output/'results.json',dict(date='2026-10-04',complete=True,ticks=len(new),quantum_ms=20,
        source_sha256=sha(args.input.read_bytes()),variants=results,
        scope='Whole valid-rate Ayumi renders; level/period-only controls are host ablations, not qualified release disks. All comparisons use one global RMS and unpooled STFT bins.'))


if __name__ == '__main__':
    main()
