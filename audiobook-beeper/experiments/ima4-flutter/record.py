"""Capture the reported full IMA4 disk at normal speed, including speaker loopback.

Sparse ready/exit markers identify every part without per-pulse instrumentation.
The WASAPI endpoint is explicitly a render loopback, never the microphone.
Persisted Fuse and Windows settings are not changed.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import warnings
import wave

import numpy as np
import soundcard as sc
from record_pcm import read_fmf
from smoke_test_fuse import hidden_startupinfo


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--disk', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if digest(a.disk.read_bytes()) != 'a7e4fb4f289b036b2f84e2032938894767875db3b1e70fbe19d79780af106aa7':
        p.error('this recorder targets the reported complete five-part IMA4 disk')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    script = '''base 10
set $part 0
breakpoint 33057
condition 1 $part<4
commands 1
print 100
print $part
print spectrum:frames
print ula:tstates
continue
end
breakpoint 33015
condition 2 $part==4
commands 2
print 100
print $part
print spectrum:frames
print ula:tstates
continue
end
breakpoint 46912
commands 3
print 200
print $part
print spectrum:frames
print ula:tstates
set $part $part+1
continue
end
breakpoint 16486
condition 4 $part==5
commands 4
print 300
print $part
print spectrum:frames
print ula:tstates
exit 77
end'''
    (out / 'debugger.txt').write_text(script, encoding='utf-8')
    command = [str(a.fuse.resolve()), '--sound', '--sound-freq', '44100',
        '--no-sound-force-8bit', '--no-autosave-settings', '--no-confirm-actions',
        '--speed', '100', '--machine', '128', '--beta128',
        '--movie-start', str(out / 'capture.fmf'), '--movie-compr', 'None',
        '--debugger-command', script, str(a.disk.resolve())]
    env = dict(os.environ)
    env.pop('SDL_AUDIODRIVER', None)
    env.pop('SDL_VIDEODRIVER', None)
    speaker = sc.default_speaker()
    endpoint = sc.get_microphone(id=speaker.id, include_loopback=True)
    if not endpoint.isloopback:
        raise ValueError('Refuse a non-loopback recording endpoint')
    blocks, block_times = [], []
    started = time.monotonic()
    process = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with endpoint.recorder(samplerate=48000, channels=[0, 1], blocksize=4800) as recorder:
                with (out / 'stdout.txt').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
                    process = subprocess.Popen(command, cwd=out, stdout=stdout, stderr=stderr,
                        env=env, startupinfo=hidden_startupinfo())
                    progress = 0
                    exited = None
                    while True:
                        blocks.append(recorder.record(numframes=4800))
                        elapsed = time.monotonic() - started
                        block_times.append(elapsed)
                        if elapsed - progress >= 10:
                            print(json.dumps(dict(seconds=round(elapsed, 2), exit_code=process.poll())), flush=True)
                            progress = elapsed
                        if process.poll() is not None and exited is None:
                            exited = elapsed
                        if exited is not None and elapsed - exited > 1:
                            break
                        if elapsed > 300:
                            raise TimeoutError('Full disk did not reach END OF AUDIO')
            capture_warnings = [str(item.message) for item in caught]
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    if process.returncode != 77:
        raise ValueError(f'Unexpected Fuse exit: {process.returncode}')
    blob = (out / 'capture.fmf').read_bytes()
    pcm, chunks, timing = read_fmf(blob)
    audio = np.concatenate(blocks)
    def wav(name, values, rate, channels):
        with wave.open(str(out / name), 'wb') as w:
            w.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
            w.writeframes(values.astype('<i2').tobytes())
    wav('internal.wav', pcm, 44100, 1)
    wav('loopback.wav', np.rint(np.clip(audio, -1, 32767 / 32768) * 32768), 48000, 2)
    (out / 'capture.fmf.gz').write_bytes(gzip.compress(blob, mtime=0))
    (out / 'loopback.f32.gz').write_bytes(gzip.compress(audio.astype('<f4').tobytes(), mtime=0))
    report = dict(complete=True, disk_sha256=digest(a.disk.read_bytes()),
        fuse_sha256=digest(a.fuse.read_bytes()), command=command,
        recorder_sha256_lf=digest(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
        speaker=speaker.name, loopback=True, source_frequency=44100, capture_frequency=48000,
        timing=timing, chunks=chunks, block_times=block_times,
        elapsed_seconds=time.monotonic() - started, warnings=capture_warnings,
        capture_valid=not capture_warnings,
        scope='Complete ordinary playback capture with sparse part markers. Not an all-bit trace or a microphone/physical speaker recording.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('command', 'chunks', 'block_times')}), flush=True)


if __name__ == '__main__':
    main()
