"""Capture a short excerpt of the actual TRD through Fuse's sound generator."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import wave

from build import ROOT, sha


def record(fuse, output, song, seconds, *, captured=False):
    import numpy as np
    sys.path.insert(0, str(ROOT/'ay-converter'))
    from fmf_audio import read_fmf
    meta = json.loads((output/'build.json').read_text())
    labels = meta['player_labels']
    folder = output/'recordings'/song
    folder.mkdir(parents=True, exist_ok=True)
    movie = folder/'capture.fmf'
    script = '\n'.join([
        'set $started 0', 'set $ticks 0',
        f'br {labels["menu_ready"]}', 'com 1',
        f'set {labels["selected"]} {int(song=="alicia")}',
        f'set {labels["mode"]} 0', 'set $started 1',
        f'set z80:pc {labels["choose"]}', 'co', 'end', 'cond 1 $started==0',
        f'br {labels["ready"]}', 'com 2', 'pr 12345',
        'pr spectrum:frames', 'pr ula:tstates', 'co', 'end',
        f'br {labels["tick_done"]}', 'com 3', 'set $ticks $ticks+1',
        'co', 'end',
        f'br {labels["tick_done"]}', 'com 4', 'ex 77', 'end',
        f'cond 4 $ticks>={round(seconds*meta["control_hz"])}',
    ])
    if captured:
        assert (folder/'debugger.txt').read_text() == script+'\n'
    else:
        (folder/'debugger.txt').write_text(script+'\n', encoding='ascii')
    command = [str(fuse.resolve()), '--sound', '--sound-freq', '44100', '--no-autosave-settings',
        '--no-confirm-actions', '--speed', '100', '--machine', '128', '--beta128',
        '--movie-start', str(movie.resolve()), '--movie-compr', 'None',
        '--debugger-command', script, str((output/'ZX-Music-Menu.trd').resolve())]
    startup = None
    if sys.platform == 'win32':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    if captured:
        trace = (folder/'trace.txt').read_bytes()
    else:
        epoch = time.time()
        result = subprocess.run(command, cwd=fuse.parent, capture_output=True, startupinfo=startup,
            env=dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy'), timeout=120)
        assert result.returncode == 77, ('Fuse capture failed', result.returncode, result.stderr[:300])
        trace = result.stdout
        fallback = fuse.parent/'stdout.txt'
        if not trace and fallback.exists() and fallback.stat().st_mtime >= epoch-2:
            trace = fallback.read_bytes()
        (folder/'trace.txt').write_bytes(trace)
    numbers = [int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace)]
    assert len(numbers) == 3 and numbers[0] == 12345, numbers
    pcm, chunks, timing = read_fmf(movie.read_bytes())
    assert timing == 'B'
    chunk = next(c for c in chunks if c[0] == numbers[1])
    start = chunk[1]+round(chunk[2]*numbers[2]/meta['frame_tstates'])
    audio = pcm[start:start+round(seconds*44100)]
    assert len(audio) >= round((seconds-.1)*44100) and np.std(audio) > 20
    path = output/f'{song}-hybrid.wav'
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(audio.astype('<i2').tobytes())
    report = dict(song=song, mode='hybrid', trd_sha256=meta['trd_sha256'],
        wav_sha256=sha(path.read_bytes()), seconds=len(audio)/44100,
        rms_pcm16=float(np.std(audio)), clipped_samples=int(np.sum((audio==32767)|(audio==-32768))),
        source='Actual Fuse1.9.0 sound generator, real128 ULA, AY+beeper,100% speed,44100Hz mono.',
        scope='Short listening excerpt, not full-song or physical-board sound qualification.')
    (output/f'{song}-recording.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/music-menu')
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--song', choices=('lumiere','alicia'), required=True)
    parser.add_argument('--captured', action='store_true', help='Re-extract a matching saved capture and trace')
    parser.add_argument('--seconds', type=float, default=12)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 60:
        parser.error('--seconds must be 1..60')
    record(args.fuse,args.output,args.song,args.seconds,captured=args.captured)
