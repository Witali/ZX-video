"""Build and verify packed IMA3 playback, with no Spectrum-side expansion.

The input directory supplies the host reference IMA nibbles and the unchanged
PCM8 source. Only the packed three-bit representation is placed on the TRD.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from functools import partial

from convert_audio import calibrate, validate, pcm_wav, independent_ima_check
from ima3_direct_player import build_disk, pack3, MEASURED_MODEL
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from verify_direct import sample_positions
from verify_pcm import save
import numpy as np


def write_candidate(out, packed, source, hot=None, pairs=0, pad=0, model=MEASURED_MODEL):
    out.mkdir(parents=True, exist_ok=True)
    disk, meta = build_disk(packed, out/'assembly', model, hot, pairs, pad)
    meta['compensated_reference_rate_hz'] = 8000
    save(out/'player.json', meta)
    (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    (out/'soundtrack.ima3.gz').write_bytes(gzip.compress(pack3(packed), mtime=0))
    pcm_wav(out/'source-preview.wav', source)
    return disk, meta


def build_verified(source, packed, out, fuse, ffmpeg, model=MEASURED_MODEL):
    """One complete calibrated disk measurement; shared with the converter."""
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output must be empty')
    out.mkdir(parents=True, exist_ok=True)
    if len(source) != len(packed)*2:
        raise ValueError('source and encoded sample counts differ')
    selected, meta = calibrate(out/'calibration', packed, source, fuse,
                               writer=partial(write_candidate, model=model))
    quality = validate(selected, fuse, ffmpeg)
    times = np.frombuffer(gzip.decompress((selected/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
    target = compensate(source, times[sample_positions(meta)], period=3546900/8000)
    pcm_wav(selected/'compensated-pcm.wav', target)
    for path in selected.iterdir():
        if path.is_file():
            shutil.copy2(path, out/path.name)
    shutil.copytree(selected/'assembly', out/'assembly')
    save(out/'independent-ima.json', independent_ima_check(packed, ffmpeg))
    report=dict(complete=True, quality=quality,
         source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
         resident_audio_bytes=len(pack3(packed)), reference_ima_bytes=len(packed),
         spectrum_expansion=False, pcm_buffer_bytes=0, pdm_buffer_bytes=0,
         native_mean_tstates=meta['ordinary_tstates'],
         delta_from_expanding_player_tstates=meta['ordinary_tstates']-423,
         selected=str(selected.relative_to(out)), physical_hardware_tested=False)
    save(out/'report.json', report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--encoded', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--fuse', required=True, type=Path)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--model', type=Path, help='Measured PDM hold model JSON')
    a = p.parse_args()
    source = wav8(a.input/'source-preview.wav')
    packed = gzip.decompress(((a.encoded or a.input)/'soundtrack.ima.gz').read_bytes())
    model=json.loads(a.model.read_bytes()) if a.model else MEASURED_MODEL
    build_verified(source,packed,a.output,a.fuse,a.ffmpeg,model)


if __name__ == '__main__':
    main()
