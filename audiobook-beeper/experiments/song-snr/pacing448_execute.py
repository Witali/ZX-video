"""Completely execute the frozen 448-T timing control on its own clock.

This script deliberately leaves the accepted 449-T duration-aware modulation
table unchanged. Only the explicit Pentagon pacing option changes. The pulse
schedule below is derived independently of general.timeline and of the host
encoder. Cold installed Fuse traces authenticate every source pulse, all IMA
states and the actual loading/playback UI; physical hardware is not measured.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import traceback

import numpy as np

from build_pdm import CPU_CLOCK, write_wav
from build_stream_trd import build
from probe_reconstruction_error import wav8
from verify_direct import reference
from verify_pcm import save
from verify_stream_trd import fuse_check, native_check
from study import filtered, metrics, uniform


FUSE_SHA256 = 'e7aba457ea405f8e2fcab9d4bc703e9f1013453726e178d8c7333ce9685a1266'
MODEL_HOLDS = [36, 28, 28, 31, 24, 26, 22, 46, 22, 26, 22, 30, 31, 27, 34, 16]
NATIVE_PROFILES = ('128', 'scorpion', 'pentagon512', 'pentagon1024')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def independent_pentagon_timestamps(samples, packed_bytes, profile):
    """Count the exact full-RAM source schedule in physical Pentagon T-states.

    Ordinary source intervals sum to 423 T in the shared instruction core.
    Replacing the Pentagon JP(IY) dispatch (8 T) by its 33-T padding gives
    +25 T at interval 7, hence 448 T. A 256-byte source-page boundary adds
    14 T; the fixed descriptor/bank tail instead adds 243 T. Both extras
    replace the ordinary tail, and their pulse position follows the three
    prefetched IMA samples: (2*consumed_bytes-3)*16+14. Neither ULA/ROM time
    nor insufficient-RAM refill latency is folded into this schedule.
    """
    assert profile in ('pentagon512', 'pentagon1024')
    assert samples == packed_bytes * 2 and packed_bytes % 256 == 0
    # This literal is the independently counted common instruction schedule;
    # it is not the modulation model's duration weights.
    core = np.array([36, 28, 28, 31, 24, 26, 22, 20,
                     22, 26, 22, 30, 31, 27, 34, 16], dtype=np.int64)
    assert int(core.sum()) == 423
    core[7] += 25
    assert int(core.sum()) == 448
    count = (samples - 3) * 16 + 15
    holds = np.tile(core, samples)[:count - 1]
    remaining = packed_bytes
    offset = 0
    maximum_extra_pages = 24 if profile == 'pentagon512' else 56
    # Base banks are 0,4,6,1,3,7; bank7 starts at DB00 after the protected
    # cover. Extended pages follow consecutively, with no source copies.
    capacities = [16384] * 5 + [9472] + [16384] * maximum_extra_pages
    sections = []
    for capacity in capacities:
        size = min(capacity, remaining)
        if not size:
            break
        assert size % 256 == 0
        sections.append(size)
        remaining -= size
    assert remaining == 0, 'this proof requires all compressed source bytes resident'
    for size in sections:
        for consumed in range(256, size + 1, 256):
            interval = (2 * (offset + consumed) - 3) * 16 + 14
            if interval < len(holds):
                holds[interval] += 243 if consumed == size else 14
        offset += size
    result = np.r_[0, np.cumsum(holds)]
    assert len(result) == count and int(result[-1]) < 2**32
    return result


def load_cover(evidence):
    meta = json.loads((evidence / 'study/inputs/song/player.json').read_bytes())
    disk = (evidence / 'study/inputs/current-main.trd').read_bytes()
    entry = next(item for item in meta['directory'] if item['name'] == 'COVER')
    at = (entry['track'] * 16 + entry['sector']) * 256
    cover = disk[at:at + 6912]
    assert len(cover) == 6912
    return cover


def prepare(inputs, output, name, cover, *, progress_ui=True):
    source_dir = inputs / name
    host_raw = (source_dir / 'host.json').read_bytes()
    host = json.loads(host_raw)
    packed_gzip = (source_dir / 'soundtrack.ima.gz').read_bytes()
    packed = gzip.decompress(packed_gzip)
    source_wav = (source_dir / 'source-preview.wav').read_bytes()
    source = wav8(source_dir / 'source-preview.wav').astype('u1')
    assert len(source) == len(packed) * 2
    assert sha(source.tobytes()) == host['source_sha256']
    assert sha(packed) == host['packed_sha256']
    assert host['source_samples'] == len(source)
    # Freeze the same source-independent PDM table as the previous release.
    # A new duration-weight table would be a separate experiment.
    model = dict(holds=MODEL_HOLDS, beta=.5, extent=.5, pcm_origin=0,
                 pentagon_ordinary_tstates=448, audio_progress_ui=progress_ui)
    if 'model' in host:
        for key in ('holds', 'beta', 'extent', 'pcm_origin'):
            assert host['model'][key] == model[key], ('host modulation model', key)
    dest = output / name
    dest.mkdir(parents=True, exist_ok=True)
    disk, meta = build(packed, dest / 'assembly', cover, model)
    identity = dict(source=name, source_sha256=sha(source.tobytes()),
                    packed_sha256=sha(packed), host_sha256=sha(host_raw),
                    source_wav_sha256=sha(source_wav), cover_sha256=sha(cover),
                    trd_sha256=sha(disk), model=model)
    for filename, raw in [('source-preview.wav', source_wav),
                          ('soundtrack.ima.gz', packed_gzip),
                          ('host.json', host_raw), ('audio.trd', disk)]:
        target = dest / filename
        if target.exists():
            assert target.read_bytes() == raw, ('existing experiment identity', str(target))
        else:
            target.write_bytes(raw)
    for filename, value in [('identity.json', identity), ('player.json', meta)]:
        target = dest / filename
        if target.exists():
            assert json.loads(target.read_bytes()) == value, ('existing metadata', str(target))
        else:
            save(target, value)
    (dest / 'verification').mkdir(exist_ok=True)
    return dest, source, packed, disk, meta, host


def measure_actual(dest, source, packed, meta, profile, actual, expected, ffmpeg, scratch, host):
    count = actual['bits_verified']
    raw = gzip.decompress((dest / 'verification' / profile / 'times.u32.gz').read_bytes())
    times_raw = np.frombuffer(raw, '<u4').astype(np.int64)
    assert len(times_raw) == count == len(expected)
    np.testing.assert_array_equal(times_raw, expected)
    assert actual['reloads'] == actual['runtime_disk_reads_during_live_audio'] == 0
    ui = actual.get('audio_progress_ui')
    if meta.get('audio_progress_ui'):
        assert ui['complete'] and ui['loading_gray_attributes_exact'] and ui['live_green_prefixes_exact']
    # Capture already checks a green prefix; additionally prove its length
    # equals the exact consumed compressed byte count at every bank handoff.
    progress = []
    for update in ui['live_progress'] if ui else []:
        pulse = update['pulse']
        assert (pulse + 33) % 32 == 0, ('progress source boundary', profile, pulse)
        consumed = (pulse + 33) // 32
        wanted = 32 * consumed // len(packed)
        assert update['filled_columns'] == wanted, ('progress geometry', profile, update, wanted)
        progress.append(dict(pulse=pulse, consumed_audio_bytes=consumed, filled_columns=wanted))
    pcm, _, _, bits = reference(packed, cycles=1, model=meta['model'])
    times = times_raw.astype(float) * CPU_CLOCK / 3584000
    observed = filtered(bits[:count - 1], times, ffmpeg, scratch)
    values, edges = uniform(source / 256., times[-1])
    wanted = filtered(values, edges, ffmpeg, scratch)
    fixed = metrics(wanted, observed)
    sample_edges = np.r_[times[::16], times[-1]]
    samples = len(sample_edges) - 1
    decoded = filtered((pcm[:samples].astype(float) + 32768) / 65536,
                       sample_edges, ffmpeg, scratch)
    shared = filtered(source[:samples] / 256., sample_edges, ffmpeg, scratch)
    predicted = host['fixed_clock']
    assert abs(fixed['error_rms'] - predicted['error_rms']) < 1e-10, ('host score mismatch', profile, fixed, predicted)
    write_wav(dest / (profile + '-actual.wav'), observed * .5)
    report = dict(complete=True, measured_on_own_complete_cold_fuse_clock=True,
                  every_source_timestamp_matches_independently_counted_448_schedule=True,
                  timestamp_count=count, relative_source_timestamps_sha256=sha(raw),
                  maximum_timestamp_error_tstates=0, reloads=0, live_rom_calls=0,
                  exact_progress_geometry=progress, host_prediction_reproduced=True,
                  audio_progress_ui_captured=bool(ui),
                  fixed_clock=fixed, total_on_shared_clock_diagnostic=metrics(shared, observed),
                  pdm_only_diagnostic=metrics(decoded, observed),
                  source_samples=len(source), trd_sha256=meta['trd_sha256'],
                  original_source_content_preserved=True, modulation_table_unchanged=True,
                  fitted_gain_delay_clock=False, physical_hardware_tested=False)
    save(dest / 'verification' / profile / 'quality.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=Path(__file__).parent / 'evidence')
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--fuse', type=Path, default=Path('C:/Program Files (x86)/Fuse/fuse.exe'))
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--source', action='append', default=[])
    parser.add_argument('--phase', choices=('native', 'fuse', 'all'), default='all')
    parser.add_argument('--captured', action='store_true')
    parser.add_argument('--without-ui', action='store_true',
                        help='Explicitly test shorter artifact controls without the two-cell UI bank-handoff contract; song UI proof remains separate')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    assert 1 <= args.jobs <= 4 and args.ffmpeg
    evidence = args.evidence.resolve()
    inputs = (args.inputs or evidence / 'pacing448-control').resolve()
    output = (args.output or evidence / 'pacing448-execution').resolve()
    output.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    assert sha(args.fuse.read_bytes()) == FUSE_SHA256, 'installed Fuse identity differs; do not substitute portable Fuse'
    cover = load_cover(evidence)
    names = args.source or ['sea_foam']
    assert len(names) == len(set(names)), 'duplicate sources share mutable outputs'
    prepared = {}
    for name in names:
        prepared[name] = prepare(inputs, output, name, cover, progress_ui=not args.without_ui)
        print('Built complete candidate: ' + name, flush=True)
    jobs = []
    for name in names:
        if args.phase in ('native', 'all'):
            jobs.extend((name, 'native', profile) for profile in NATIVE_PROFILES)
        if args.phase in ('fuse', 'all'):
            profiles = ('pentagon512', 'pentagon1024') if name == 'sea_foam' else ('pentagon512',)
            jobs.extend((name, 'fuse', profile) for profile in profiles)
    def run(job):
        name, phase, profile = job
        dest, source, packed, disk, meta, host = prepared[name]
        try:
            if phase == 'native':
                report = native_check(disk, meta, packed, profile,
                                      out=dest / 'verification' / ('native-' + profile + '.json'))
            else:
                report = fuse_check(dest / 'audio.trd', meta, packed, profile,
                                    dest / 'verification' / profile, args.fuse,
                                    captured=args.captured, capture_ui=bool(meta.get('audio_progress_ui')))
                expected = independent_pentagon_timestamps(len(source), len(packed), profile)
                quality = measure_actual(dest, source, packed, meta, profile, report, expected,
                                         args.ffmpeg, args.scratch, host)
                report = dict(fuse=report, quality=quality)
            print('Complete: ' + '/'.join(job), flush=True)
            return dict(source=name, phase=phase, profile=profile, report=report)
        except Exception:
            failure = dict(complete=False, source=name, phase=phase, profile=profile,
                           traceback=traceback.format_exc(), trd_sha256=meta['trd_sha256'])
            save(dest / 'verification' / ('failure-' + phase + '-' + profile + '.json'), failure)
            raise
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run, jobs))
    report = dict(complete=True, phase=args.phase, sources=names, runs=results,
                  installed_fuse_sha256=FUSE_SHA256, source_specific_modulation_parameters=False,
                  ordinary_tstates=dict(pentagon=448, other_native=423),
                  page_extra_tstates=14, bank_extra_tstates=dict(pentagon=243, scorpion=267),
                  scope='Complete listed source/profile execution only; wider corpus and physical hardware remain separate',
                  no_unconditional_release_claim=True, physical_hardware_tested=False)
    save(output / ('report-' + args.phase + '-' + '-'.join(names) + '.json'), report)
    print(json.dumps(dict(complete=True, phase=args.phase, sources=names, runs=len(results))), flush=True)


if __name__ == '__main__':
    main()
