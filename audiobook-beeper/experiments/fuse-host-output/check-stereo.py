"""Check whether the mono audition hid a significant channel difference."""
import json
from pathlib import Path
import wave

import numpy as np

root = Path(__file__).resolve().parent
rows = []
for name in ('win32-44100', 'sdl-44100', 'win32-48000-buffered'):
    analysis = json.loads((root/name/'analysis.json').read_bytes())
    with wave.open(str(root/name/'loopback.wav'), 'rb') as wav:
        assert wav.getframerate() == 48000 and wav.getnchannels() == 2
        x = np.frombuffer(wav.readframes(wav.getnframes()), '<i2').reshape(-1, 2).astype(float)
    start = analysis['start_sample']
    x = x[start:start+8*48000]
    difference = x[:, 0]-x[:, 1]
    mono = x.mean(axis=1)
    rows.append(dict(run=name, frames=len(x),
                     maximum_pcm16_channel_difference=float(abs(difference).max()),
                     rms_pcm16_channel_difference=float(np.sqrt(np.mean(difference**2))),
                     rms_pcm16_mono=float(np.sqrt(np.mean(mono**2))),
                     channel_correlation=float(np.corrcoef(x.T)[0, 1])))
report = dict(scope=__doc__, seconds=8, sample_rate=48000, runs=rows)
(root/'stereo-check.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
