"""Inspect the approximate rabbit-exit cue in the unchanged released AY stream."""
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path
import numpy as np
from build_preview import save,sha,quality,ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('movie',type=Path); p.add_argument('--node',required=True); p.add_argument('--ffmpeg',required=True)
    p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    if args.output.exists() and any(args.output.iterdir()): p.error('output must be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    start,duration=36,16
    with args.movie.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    edit=json.loads((ROOT/'toolkit/movie_no_credits.json').read_bytes())
    if digest!=edit['source_video_sha256']: raise ValueError('movie source changed')
    archive=ROOT/'toolkit/refined_four_evidence/source-registers.bin.gz'
    regs=gzip.decompress(archive.read_bytes())
    if sha(regs)!='dab68198caaa020f4a36d45226a12e5be81da58231ca3cb194ef6a765aa9b531':
        raise ValueError('released movie register stream changed')
    # Render from the beginning to retain oscillator/noise history at the cue.
    prefix=args.output/'movie-prefix-registers.gz'
    prefix.write_bytes(gzip.compress(regs[:(start+duration)*50*11],mtime=0))
    rendered=args.output/'movie-prefix.f32'
    subprocess.run([args.node,str(ROOT/'audiobook-ay/render_ym2149.js'),str(prefix.resolve()),str(rendered.resolve()),
        '50',str((args.output/'render.json').resolve())],check=True)
    ay=np.frombuffer(rendered.read_bytes(),'<f4').astype(float)[start*44100:]
    raw=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-ss',str(start),'-i',str(args.movie.resolve()),
        '-t',str(duration),'-map','0:a:0','-ac','1','-ar','44100','-f','f32le','-'],capture_output=True,check=True).stdout
    original=np.frombuffer(raw,'<f4').astype(float)
    assert len(original)==len(ay)==duration*44100
    signals=dict(original=original,ay=ay)
    rms={n:float(np.sqrt(np.mean(s*s))) for n,s in signals.items()}
    gain=min(.1,*(.9*rms[n]/max(float(np.max(abs(s))),1e-12) for n,s in signals.items()))
    for n,s in signals.items(): quality.write_wav(args.output/f'movie-{n}-preview.wav',s*gain/rms[n],44100)
    cue=np.frombuffer(regs,dtype=np.uint8).reshape(-1,11)[start*50:(start+duration)*50]
    active=[]; low=[]
    for row in cue:
        tones=[1773450/(16*max(1,int(row[c*2])+(int(row[c*2+1])<<8)))
               for c in range(3) if row[8+c] and not(row[7]&(1<<c))]
        active.append(len(tones))
        if tones: low.append(min(tones))
    report=dict(source=str(args.movie.resolve()),source_sha256=digest,start_seconds=start,duration_seconds=duration,
        identification='approximate scene located from user disk-relative cue and opening source images; not an isolated vocal stem',
        movie_disk_1_seconds=131.2,one_third_of_disk_1_seconds=131.2/3,
        unchanged_registers=True,full_movie_registers_sha256=sha(regs),cue_registers_sha256=sha(cue.tobytes()),
        average_active_tones=float(np.mean(active)),minimum_active_tone_percentiles_hz=np.percentile(low,[10,50,90]).tolist(),
        ticks_with_active_noise=int(sum(any(row[8+c] and not(row[7]&(1<<(3+c))) for c in range(3)) for row in cue)),
        scope='mixed music and voice; low-frequency tones alone do not identify a vocal fundamental',
        encoder='unchanged musical bass/harmony/melody tracker; compare with LPC mapper that discards pitch_hz',
        renderer='same YM2149 model as speech; actual saved movie registers, phase continuous from time zero',
        producer_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
        artifacts={f.name:dict(bytes=f.stat().st_size,sha256=sha(f.read_bytes())) for f in args.output.iterdir() if f.suffix!='.f32'})
    save(args.output/'report.json',report)
    print(json.dumps({k:report[k] for k in ('start_seconds','duration_seconds','average_active_tones','minimum_active_tone_percentiles_hz','ticks_with_active_noise')}))


if __name__=='__main__': main()
