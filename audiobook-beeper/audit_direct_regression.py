"""Rebuild the user-approved direct disk and compare authenticated historical clocks.

This is a historical regression audit, not a new player or a universal quality
ranking. A successful rebuild is byte-identical to the previously cold-booted
reference; listening reconstructions use saved complete Fuse OUT timelines.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import wave

import numpy as np
from assess_snr import ratio
from build_pdm import write_wav
from convert_mulaw_audio import filter_signal, STABLE_FILTER
from direct_player import build_disk
from verify_direct import reference
from verify_pcm import save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CPU = 3546900
GOOD_SHA = '9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013'
STAGES = (
    ('original', 'ima-direct'),
    ('weighted', 'ima-direct-weighted'),
    ('locked', 'ima-direct-locked'),
    ('current', 'quality-max/evidence/ima4/selected'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_evidence(directory, name, hashes):
    """Authenticate materialized LFS files before reusing any measured evidence."""
    path = directory / name
    data = path.read_bytes()
    if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
        raise ValueError(f'Materialize this Git LFS file first: {path}')
    if (directory / 'artifacts.json').exists():
        manifest = json.loads((directory / 'artifacts.json').read_bytes())
        expected = manifest[name]['sha256']
    else:
        manifest = json.loads((HERE / 'experiments/quality-max/manifest.json').read_bytes())
        expected = manifest[path.relative_to(ROOT).as_posix()]
    if sha(data) != expected:
        raise ValueError(f'Archived evidence hash mismatch: {path}')
    hashes[path.relative_to(ROOT).as_posix()] = expected
    return data


def read_pcm(data):
    with wave.open(io.BytesIO(data), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 1, 8000):
            raise ValueError('Expected mono unsigned PCM8 at 8000 Hz')
        return np.frombuffer(wav.readframes(wav.getnframes()), 'u1').copy()


def fixed_reference(source, duration_tstates, rate, ffmpeg):
    period = CPU / rate
    count = int(np.ceil(duration_tstates / period))
    edges = np.r_[np.arange(count) * period, duration_tstates]
    values = np.pad(source / 256., (0, max(0, count - len(source))), constant_values=.5)[:count]
    return filter_signal(values, edges, ffmpeg, 768000)


def source_preparation(source_path, source, ffmpeg, out):
    """Compare the same 60-second offset, without attributing all differences to IMA.

    The historical normalization window was longer than this resident prefix.
    The current preparation here normalizes only this prefix; that distinction
    is intentional and recorded, rather than hidden by a fitted listening gain.
    """
    preparation = json.loads((HERE / 'ima-preview/preparation.json').read_bytes())
    if sha(source_path.read_bytes()) != preparation['source']['source_sha256']:
        raise ValueError('This comparison requires the archived source audiobook')
    count = len(source) - 128
    raw = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-ss', '60',
        '-i', str(source_path), '-map', '0:a:0', '-t', str(count / 8000),
        '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'],
        capture_output=True, check=True).stdout
    samples = np.frombuffer(raw, '<f4').astype(float)
    if len(samples) != count:
        raise ValueError('Incomplete matched source excerpt')
    gain = (109 / 128) / max(abs(samples))
    samples *= gain
    samples[:80] *= np.linspace(0, 1, 80)
    samples[-80:] *= np.linspace(1, 0, 80)
    pcm = np.full(len(source), 128, dtype='u1')
    pcm[:count] = np.clip(np.rint(samples * 128 + 128), 0, 255).astype('u1')
    old = (source.astype(float) - 128) / 128
    new = (pcm.astype(float) - 128) / 128
    a, b = (float(np.sqrt(np.mean(x[800:-800] ** 2))) for x in (old, new))
    write_wav(out / 'source-old-conditioned.wav', old * .8, 8000)
    write_wav(out / 'source-current-peak-only.wav', new * .8, 8000)
    return dict(source_file_sha256=sha(source_path.read_bytes()), start_seconds=60,
        current_retained_seconds=count / 8000, current_peak_gain=float(gain),
        old_conditioned_rms=a, current_peak_only_rms=b,
        old_to_current_level_db=float(20 * np.log10(a / b)),
        rms_excludes_edge_seconds=.1, historical_preparation=preparation,
        current_pcm_sha256=sha(pcm.tobytes()),
        interpretation='Matched source position, different preparation. Level difference is not a measured PDM SNR gain or a causal isolation of the limiter alone.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-disk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--source', type=Path, help='Optional original audiobook for matched preparation comparison')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must not already exist')
    good = args.reference_disk.read_bytes()
    if sha(good) != GOOD_SHA:
        parser.error('reference is not the user-approved direct IMA4 disk')
    args.output.mkdir(parents=True)
    out = args.output.resolve()
    hashes, results = {}, []
    common_source = None
    for label, relative in STAGES:
        directory = HERE / 'experiments' / relative
        source = read_pcm(read_evidence(directory, 'source-preview.wav', hashes))
        packed = gzip.decompress(read_evidence(directory, 'soundtrack.ima.gz', hashes))
        meta = json.loads(read_evidence(directory, 'player.json', hashes))
        proof = json.loads(read_evidence(directory, 'fuse.json', hashes))
        native = json.loads(read_evidence(directory, 'native.json', hashes))
        if not all(p['complete'] and p['cycles_verified'] == 2 and
                   p['every_pdm_bit_exact'] and p['every_predictor_and_index_exact']
                   for p in (proof, native)) or not proof['cold_boot']:
            raise ValueError('Need complete independent native and cold Fuse proof')
        if common_source is None:
            common_source = source
            disk, rebuilt = build_disk(packed, out / 'assembly')
            if disk != good:
                raise ValueError('Current assembler no longer reproduces the reference byte for byte')
            (out / 'restored-direct.trd').write_bytes(disk)
            save(out / 'rebuilt-player.json', rebuilt)
        elif not np.array_equal(source, common_source):
            raise ValueError('Historical stages do not use identical PCM source bytes')
        timeline = np.frombuffer(gzip.decompress(read_evidence(directory, 'output-times.u32.gz', hashes)), '<u4').astype(np.int64)
        _, _, _, bits = reference(packed, cycles=2, model=meta.get('model'), idle_pairs=meta.get('loop_idle_pairs', 0))
        count = meta.get('outputs_per_cycle', len(source) * 16)
        if len(timeline) != 2 * count + 1 or len(bits) != len(timeline):
            raise ValueError('Incomplete two-loop timing evidence')
        cycles = []
        for loop in range(2):
            times = timeline[loop * count:(loop + 1) * count + 1].copy()
            times -= times[0]
            output = filter_signal(bits[loop * count:(loop + 1) * count], times, args.ffmpeg, 768000)
            fixed = fixed_reference(source, times[-1], 8000, args.ffmpeg)
            mean_rate = len(source) * CPU / times[-1]
            mean = fixed_reference(source, times[-1], mean_rate, args.ffmpeg)
            cut = slice(4410, -4410)
            declared = fixed if meta.get('compensated_reference_rate_hz') else mean
            row = dict(loop=loop + 1, duration_seconds=float(times[-1] / CPU),
                mean_sample_rate_hz=mean_rate,
                fixed_8000_snr_db=ratio(fixed[cut], output[cut] - fixed[cut]),
                fixed_mean_snr_db=ratio(mean[cut], output[cut] - mean[cut]),
                declared_reference_rate_hz=meta.get('compensated_reference_rate_hz', mean_rate),
                declared_clock_snr_db=ratio(declared[cut], output[cut] - declared[cut]),
                declared_error_rms=float(np.sqrt(np.mean((output[cut] - declared[cut]) ** 2))))
            cycles.append(row)
            print(json.dumps(dict(stage=label, **row)), flush=True)
            if loop == 0:
                write_wav(out / f'{label}-output.wav', output * .8)
                if label == 'current':
                    write_wav(out / 'reference-fixed-8k.wav', fixed * .8)
        results.append(dict(stage=label, archived_path=relative, source_pcm_sha256=sha(source.tobytes()),
            packed_sha256=sha(packed), cold_fuse_proof_reused=True, native_proof_reused=True,
            native_ordinary_tstates=meta['ordinary_tstates'], cycles=cycles))
    report = dict(date='2026-10-05', reference_sha256=GOOD_SHA, exact_rebuild=True,
        differing_disk_bytes=0, native_ordinary_tstates=423, player_tstate_delta=0,
        filter=STABLE_FILTER, integration_rate_hz=768000, excluded_edge_seconds=.1,
        common_listening_gain=.8, fitted_gain_or_delay=False, stages=results,
        input_hashes=hashes, verification='Authenticated archived complete native/cold Fuse runs. No new emulator run; exact byte-identical disk rebuild.',
        quality_scope='Reported SNR includes distortion. Fixed 8000 penalizes accumulated speed offset; fixed mean removes overall speed offset only. Declared reference uses 8000 for compensated streams and measured mean for older unwarped streams. Do not compare different clocks without this qualification.',
        physical_hardware_tested=False)
    if args.source:
        report['preparation_comparison'] = source_preparation(args.source, common_source, args.ffmpeg, out)
    report['python_version'] = platform.python_version()
    report['ffmpeg_version'] = subprocess.run([args.ffmpeg, '-version'], capture_output=True,
                                               text=True, check=True).stdout.splitlines()[0]
    report['producer_sha256_lf'] = {name: sha((HERE / name).read_bytes().replace(b'\r\n', b'\n'))
        for name in ('audit_direct_regression.py', 'direct_player.py', 'direct-player.asm',
                     'verify_direct.py', 'verify_packet.py', 'probe_feedback_packets.py',
                     'convert_mulaw_audio.py', 'build_pdm.py', 'assess_snr.py')}
    save(out / 'report.json', report)


if __name__ == '__main__':
    main()
