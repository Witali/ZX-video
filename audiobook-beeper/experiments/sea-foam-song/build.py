"""Cut the main sea-foam song and use the user's preferred original direct IMA4.

This bounded artifact build deliberately preserves the old preparation, beam32
PCM encoder, native-weight PDM table and uncorrected sample clock. The existing
series controller supplies one independently bootable disk and automatic RAM
reloads; it changes only the silent tail, never source-bearing pulse code.
"""
import argparse
from functools import partial
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
BEEPER = HERE.parents[1]
ROOT = BEEPER.parent
sys.path[:0] = [str(BEEPER), str(ROOT / 'toolkit')]
from build_ima import ffmpeg_check
from build_packet import render
from build_pdm import RATE, pcm8k
from convert_audio import pcm_wav
from direct_player import HOLDS, build_disk
from ima_beam import encode
from ima_codec import decode
from ima4_series import build_volume, plan_parts, plan_volumes
from verify_direct import intervals, reference
from verify_packet import native_check, fuse_check
from verify_pcm import save
import verify_ima3_series as series_verifier

START = 133.6
STOP = 223.6
REFERENCE_SHA = '9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013'
SOURCE_SHA = '995ddb8988fd57f5d718df9f4811faf7d7dc68999164116effe04ce1178bd931'
MODEL = dict(holds=HOLDS, beta=.5, extent=1.)
SOURCE_FILTER = 'highpass=f=70,lowpass=f=3800:p=2,lowpass=f=3800:p=2'
LIMITER = 'volume=4,alimiter=limit=0.85:attack=5:release=100:level=0:latency=1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage(name, **values):
    print(json.dumps(dict(stage=name, **values)), flush=True)


def qualify(path, fuse, ffmpeg, *, phase=None):
    """Verify both complete legacy loops without imposing a modern phase lock.

    Every pulse, predictor, index, paging and protected-memory gate is retained.
    The requested old disk has no silent phase-lock filler or offline clock
    compensation. A forced ready phase selects a naturally occurring cold
    boot; it does not change the playback code or insert live CPU delay.
    """
    meta = json.loads((path / 'player.json').read_bytes())
    assert meta['model'] == MODEL and meta['loop_idle_pairs'] == 0
    assert meta['loop_idle_pad_tstates'] == 0
    packed = gzip.decompress((path / 'soundtrack.ima.gz').read_bytes())
    ref = partial(reference, model=MODEL)
    save(path / 'native.json', native_check((path / 'audiobook-preview.trd').read_bytes(),
                                           meta, packed, ref, intervals))
    native = fuse_check(fuse, path, meta, packed, False, ref, intervals, ready_phase=phase)
    assert abs(native['average_pcm_rate_hz'] / 8000 - 1) <= .02
    save(path / 'fuse.json', native)
    renders = [render(path, ffmpeg, False, ref, intervals, loop=i) for i in range(2)]
    result = dict(complete=True, legacy_model=True, phase_locked=False,
                  offline_clock_compensation=False, speed_within_two_percent=True,
                  loop_renders=renders, fuse=native,
                  minimum_sample_boundary_snr_db=min(r['total_snr_db'] for r in renders))
    save(path / 'qualification.json', result)
    return result


def qualify_legacy_phase(selected, out, fuse, ffmpeg, phase):
    """Keep the series verifier's exact 8-T comparison on legacy pulse code."""
    out.mkdir(parents=True, exist_ok=True)
    names = ('player.json', 'soundtrack.ima.gz', 'source-preview.wav', 'audiobook-preview.trd')
    for name in names:
        shutil.copy2(selected / name, out / name)
    result = qualify(out, fuse, ffmpeg, phase=phase)
    assert all((selected / name).read_bytes() == (out / name).read_bytes() for name in names)
    save(out / 'qualified-reference.json', dict(complete=True, ready_phase=phase,
         unchanged_preview_sha256=digest(selected / 'audiobook-preview.trd'),
         quality=result, scope='Complete additional cold two-loop legacy proof; no changed CPU/ULA time'))
    return out


def prepare(args, out):
    """Use the historical voice preparation unchanged on the selected song.

    Gain is measured once over the complete selected song. Filter context is
    retained before the cut. Original WAV has neither this gain nor filtering.
    The old 20-ms fades precede its limiter; each RAM part additionally fades
    its last 160 source samples into the independent silent IMA reset guard.
    """
    original = out / 'original-song.wav'
    if not original.exists():
        subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(START),
            '-i', str(args.source), '-t', str(STOP-START), '-map', '0:a:0', '-vn',
            '-c:a', 'pcm_s16le', str(original)], check=True)
    marker = out / 'preparation.json'
    if marker.exists():
        saved = json.loads(marker.read_bytes())
        assert digest(out / 'prepared-song.wav') == saved['prepared_wav_sha256']
        return saved
    context = 1.
    raw = subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(START-context),
        '-i', str(args.source), '-t', str(context+STOP-START+1), '-map', '0:a:0',
        '-ac', '1', '-af', SOURCE_FILTER, '-ar', str(RATE), '-f', 'f32le', '-'],
        capture_output=True, check=True).stdout
    signal = np.frombuffer(raw, '<f4').astype(float)[round(context*RATE):round((context+STOP-START)*RATE)]
    assert len(signal) == round((STOP-START)*RATE) and np.isfinite(signal).all()
    gain = .65 / max(float(np.max(abs(signal))), 1e-12)
    signal *= gain
    t = np.arange(len(signal)) / RATE
    signal *= np.maximum(0, np.minimum(1, np.minimum(t/.020, ((STOP-START)-t)/.020)))
    limited = subprocess.run([args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le',
        '-ar', str(RATE), '-ac', '1', '-i', '-', '-af', LIMITER, '-f', 'f32le', '-'],
        input=signal.astype('<f4').tobytes(), capture_output=True, check=True).stdout
    conditioned = np.frombuffer(limited, '<f4').astype(float)
    assert len(conditioned) == len(signal)
    _, pcm = pcm8k(conditioned, args.ffmpeg, out / 'prepared-song.wav')
    saved = dict(source_interval_seconds=[START, STOP], duration_seconds=STOP-START,
        source_sha256=digest(args.source), original_wav_sha256=digest(original),
        source_filter=SOURCE_FILTER, normalizing_peak=.65, normalization_gain=gain,
        normalization_scope='whole selected song', edge_fade_seconds=.020,
        limiter=LIMITER, preparation_rate_hz=RATE, pcm=pcm,
        prepared_wav_sha256=digest(out / 'prepared-song.wav'),
        encoder=dict(type='historical PCM beam search', width=32, block_samples=64),
        pdm_model=MODEL, offline_clock_compensation=False, phase_lock=False,
        reference_disk_sha256=REFERENCE_SHA, explicit_user_selected_settings=True)
    save(marker, saved)
    return saved


def build(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert digest(args.reference_disk) == REFERENCE_SHA, 'different preferred disk'
    assert digest(args.source) == SOURCE_SHA, 'different cartoon source'
    producers = {p.name: digest(p) for p in BEEPER.iterdir() if p.suffix in ('.py', '.asm')}
    identity = dict(source_sha256=SOURCE_SHA, reference_sha256=REFERENCE_SHA,
        interval=[START, STOP], script_sha256=digest(__file__), producers=producers,
        ffmpeg_sha256=digest(args.ffmpeg), fuse_sha256=digest(args.fuse))
    manifest = out / 'run.json'
    if manifest.exists():
        assert args.resume and json.loads(manifest.read_bytes()) == identity, 'resume changed'
    else:
        assert not any(out.iterdir()), 'output must be empty'
        save(manifest, identity)
    stage('prepare', source_interval_seconds=[START, STOP])
    prep = prepare(args, out)
    with wave.open(str(out / 'prepared-song.wav'), 'rb') as wav:
        assert wav.getparams()[:3] == (1, 1, 8000)
        source = np.frombuffer(wav.readframes(wav.getnframes()), 'u1').copy()
    parts = plan_parts(len(source))
    volumes = plan_volumes(parts)
    assert len(volumes) == 1 and volumes[0] == list(range(len(parts)))
    save(out / 'parts.json', parts)
    selected = []
    for i, part in enumerate(parts):
        path = out / 'selected' / f'part-{i+1:05d}'
        path.mkdir(parents=True, exist_ok=True)
        stage('part', number=i+1, total=len(parts), source_seconds=[part['start']/8000, part['stop']/8000])
        marker = path / 'qualification.json'
        if not marker.exists():
            if not (path / 'player.json').exists():
                pcm = np.full(part['samples'], 128, dtype='u1')
                count = part['stop'] - part['start']
                pcm[:count] = source[part['start']:part['stop']]
                fade = min(160, count)
                pcm[count-fade:count] = np.rint(128 + (pcm[count-fade:count].astype(float)-128)*np.linspace(1,0,fade)).astype('u1')
                pcm_wav(path / 'source-preview.wav', pcm)
                packed = encode(pcm, width=32, block_samples=64)
                disk, meta = build_disk(packed, path / 'assembly', model=None)
                assert meta['model'] == MODEL and meta['ordinary_tstates'] == 423
                (path / 'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
                (path / 'audiobook-preview.trd').write_bytes(disk)
                save(path / 'player.json', meta)
                decoded, indices = decode(packed)
                save(path / 'independent-ima.json', ffmpeg_check(packed, decoded, indices, args.ffmpeg, path))
            qualify(path, args.fuse, args.ffmpeg)
        assert json.loads(marker.read_bytes())['complete']
        selected.append(path)
    stage('assemble-volume', parts=len(parts))
    disk, metadata = build_volume(selected, out / 'volume', bytes.fromhex(digest(out / 'prepared-song.wav'))[:16], 1, 1)
    (out / 'audio.trd').write_bytes(disk)
    save(out / 'volumes.json', [dict(file='audio.trd', **metadata)])
    # The standard series verifier remains intact. Only its additional legacy
    # preview qualification avoids the modern phase-lock requirement absent
    # from the exact reference selected by the user. No pulse tolerance changes.
    series_verifier.qualify_ready_phase = qualify_legacy_phase
    stage('verify-complete-volume')
    verified = series_verifier.verify_series(out, args.fuse, args.ffmpeg)
    assert verified['complete'] and verified['volumes'][0]['ended_at'] == 'end_of_audio'
    actual = verified['volumes'][0]
    report = dict(complete=True, disk_count=1, source_seconds=STOP-START,
        full_selected_song_retained=parts[-1]['stop'] == len(source), parts=parts,
        reference_disk_sha256=REFERENCE_SHA, selected_legacy_model=MODEL,
        preparation=prep, trd_sha256=digest(out / 'audio.trd'), verification=verified,
        ordinary_tstates=423, ordinary_delta_tstates=0,
        page_extra_tstates=14, page_delta_tstates=0, bank_extra_tstates=140, bank_delta_tstates=0,
        hot_path_scope='source-bearing decoder and PDM instructions; series exit is in silent guard',
        between_part_pause_seconds=actual['between_part_pause_seconds'],
        quality_reference='fixed 8-kHz conditioned PCM8; original full-band song retained separately',
        fixed_clock_snr_db=[p['fixed_clock_snr_db'] for p in actual['parts']],
        speed_error_percent=[p['speed_error_percent'] for p in actual['parts']],
        sample_boundary_snr_db=[json.loads((p/'qualification.json').read_bytes())['minimum_sample_boundary_snr_db'] for p in selected],
        preview_only=True, listening_acceptance_pending=True, physical_hardware_tested=False)
    save(out / 'report.json', report)
    stage('complete', disk_count=1, seconds=STOP-START, trd_sha256=report['trd_sha256'],
          loading_pauses_seconds=report['between_part_pause_seconds'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference-disk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    try:
        build(args)
    except Exception as error:
        if args.output.is_dir():
            save(args.output / 'failure.json', dict(complete=False, error_type=type(error).__name__, error=str(error)))
        raise
