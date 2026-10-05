"""Public-command smoke tests: resampling, silence, padding and validation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np
from g726.codec import save


def check(out, ffmpeg, library):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    cases = [('unaligned_pcm8', 8000, 1, 1, 1001), ('stereo_silence_44100', 44100, 2, 2, 11025)]
    converter = Path(__file__).resolve().parents[1]/'convert_g726_audio.py'
    for name, rate, channels, width, count in cases:
        source = out/(name+'.wav')
        values = ((np.sin(np.arange(count)*2*np.pi*731/rate)*70+128).astype('u1')
                  if width==1 else np.zeros(count*channels, dtype='<i2'))
        with wave.open(str(source), 'wb') as stream:
            stream.setnchannels(channels)
            stream.setsampwidth(width)
            stream.setframerate(rate)
            stream.writeframes(values.tobytes())
        command = [sys.executable, str(converter), str(source), '--ffmpeg', str(ffmpeg),
                   '--library', str(library), '--outdir', str(out/name)]
        run = subprocess.run(command, capture_output=True, text=True, check=True)
        report = json.loads((out/name/'report.json').read_text(),
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        expected = count if rate==8000 else 2000
        assert report['original_samples']==expected
        assert report['padding_samples']==(-expected)%4
        assert report['payload_bytes']*4==report['samples']
        assert not report['native_pdm_qualified']
        if width==2:
            assert report['quality']['raw_pcm_snr_db'] is None
        invalid = subprocess.run(command+['--seconds', 'nan'], capture_output=True, text=True)
        assert invalid.returncode!=0 and 'finite and positive' in invalid.stderr
        rows.append(dict(case=name, passed=True, original_samples=expected,
                         padding_samples=report['padding_samples'], invalid_duration_rejected=True,
                         console=run.stdout))
    save(out/'report.json', dict(passed=True, cases=rows))
    return rows


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    args = parser.parse_args()
    check(args.outdir.resolve(), args.ffmpeg.resolve(), args.library.resolve())
    print('Public CLI smoke checks passed')
