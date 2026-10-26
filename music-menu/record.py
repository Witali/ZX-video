"""Capture actual AY-only TRD output through Fuse's normal sound path."""
import argparse
import json
from pathlib import Path
import re
import sys
import wave

from build import ROOT, HERE, CPU_HZ, sha, triangle_period
from arrangement import timeline
from verify import run_fuse


def record(fuse,output,song,seconds,*,captured=False):
    import numpy as np
    sys.path.insert(0,str(ROOT/'ay-converter'))
    from fmf_audio import read_fmf
    meta = json.loads((output/'build.json').read_text())
    labels = meta['player_labels']
    folder = output/'recordings'/song
    folder.mkdir(parents=True,exist_ok=True)
    movie = folder/'capture.fmf'
    script = '\n'.join([
        'set $started 0','set $ticks 0',
        f'br {labels["key_changed"]}','com 1',
        f'set z80:a {1+int(song=="alicia")}','set $started 1','co','end','cond 1 $started==0',
        f'br {labels["song_started"]}','com 2','pr 12345','pr spectrum:frames','pr ula:tstates','co','end',
        f'br {labels["music_tick"]}','com 3','set $ticks $ticks+1','co','end',
        f'br {labels["menu_frame_done"]}','com 4','ex 77','end',
        f'cond 4 $ticks>={round(seconds*meta["control_hz"])}',
    ])
    if captured:
        assert (folder/'debugger.txt').read_text()==script+'\n'
        identity = json.loads((folder/'capture.json').read_text())
        assert identity['trd_sha256']==meta['trd_sha256'] and identity['script_sha256']==sha(script.encode())
        trace = (folder/'trace.txt').read_bytes()
    else:
        (folder/'debugger.txt').write_text(script+'\n',encoding='ascii')
        result,trace = run_fuse(fuse,output,script,sound=True,timeout=120,
            extra=['--sound-freq','44100','--movie-start',str(movie.resolve()),'--movie-compr','None'])
        assert result.returncode==77,('Fuse capture failed',result.returncode,result.stderr[:300])
        (folder/'trace.txt').write_bytes(trace)
        (folder/'capture.json').write_text(json.dumps(dict(trd_sha256=meta['trd_sha256'],
            script_sha256=sha(script.encode())),indent=2)+'\n',encoding='utf-8',newline='\n')
    numbers = [int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace)]
    assert len(numbers)==3 and numbers[0]==12345,numbers
    pcm,chunks,timing = read_fmf(movie.read_bytes())
    assert timing=='B'
    chunk = next(c for c in chunks if c[0]==numbers[1])
    start = chunk[1]+round(chunk[2]*numbers[2]/meta['frame_tstates'])
    audio = pcm[start:start+round(seconds*44100)]
    assert len(audio)>=round((seconds-.1)*44100) and np.std(audio)>20
    path = output/f'{song}-ay.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(audio.astype('<i2').tobytes())
    first_bass = timeline(json.loads((HERE/'scores'/f'{song}.json').read_text()))[0][2][0][2]
    expected_bass = (CPU_HZ/2)/(512*triangle_period(first_bass)[0])
    excerpt = audio[:44100].astype(float)
    frequencies = np.fft.rfftfreq(524288,1/44100)
    spectrum = abs(np.fft.rfft((excerpt-excerpt.mean())*np.hanning(len(excerpt)),n=524288))
    low_bins = np.flatnonzero((frequencies>45)&(frequencies<140))
    measured_bass = float(frequencies[low_bins[np.argmax(spectrum[low_bins])]])
    assert abs(measured_bass-expected_bass)<.2,('Unexpected triangle bass pitch',measured_bass,expected_bass)
    report = dict(song=song,mode='AY only',trd_sha256=meta['trd_sha256'],wav_sha256=sha(path.read_bytes()),
        seconds=len(audio)/44100,rms_pcm16=float(np.std(audio)),
        clipped_samples=int(np.sum((audio==32767)|(audio==-32768))),
        first_bass_peak_hz=measured_bass,first_bass_expected_hz=expected_bass,
        source='Actual Fuse 1.9.0 real128 AY sound at 100% speed; 44100 Hz mono; live menu retained.',
        scope='Short actual sound-generator excerpt; not physical-board audio or perceptual quality qualification.')
    (output/f'{song}-recording.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-ay-only')
    parser.add_argument('--fuse',type=Path,required=True)
    parser.add_argument('--song',choices=('lumiere','alicia'),required=True)
    parser.add_argument('--seconds',type=float,default=12)
    parser.add_argument('--captured',action='store_true')
    args = parser.parse_args()
    if not 1<=args.seconds<=60:
        parser.error('--seconds must be 1..60')
    record(args.fuse,args.output,args.song,args.seconds,captured=args.captured)
