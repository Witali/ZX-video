"""Automatically build a research SNR TRD with the C or Python waveform encoder.

Examples (the default C child process does not run Python):
  python convert_snr_audio.py input.mp4 --output result --cover title.scr
  python convert_snr_audio.py prepared.wav --prepared-pcm --output result
  python convert_snr_audio.py prepared.wav --prepared-pcm --encoder python --output reference

All sources use the same frozen search parameters and instruction-derived
Pentagon clock. The automatic RAM loader supports 128/256/512/1024 KiB, but
the audio quality model applies to resident Pentagon playback only. Results
remain research artifacts: a high host SNR does not establish the flutter,
background-noise and corpus-regression release gates.
"""
import time

PROCESS_STARTED = time.perf_counter()

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
RESEARCH = HERE / 'experiments' / 'song-snr'
sys.path.insert(0, str(RESEARCH))

from build_pdm import CPU_CLOCK, write_wav
from build_stream_trd import build, sections
from clock_control import PARAMETERS, prepare as prepare_waveform
from convert_audio import pcm_wav, prepare_source
from direct_player import HOLDS
from general import models
from ima_beam import encode as encode_pcm
from ima_codec import decode, require_unclipped
from ima_waveform_encoder import encode_waveform
from native_waveform_encoder import execute_workset, write_workset
from native_ima_encoder import encode_pcm_native
from precompensate_voice import compensate
from ram_cache import PROFILES
from study import filtered, metrics, uniform
from verify_direct import reference
from verify_pcm import save


RATE = 8000
GUARD = 128
MAXIMUM_SAMPLES = 2392 * 512
BASE_AUDIO_BYTES = 91392
PRODUCERS = (
    'convert_snr_audio.py', 'convert_audio.py', 'audio_dynamics.py',
    'native_waveform_encoder.py', 'native_waveform_encoder.c',
    'native_ima_encoder.py', 'native_ima_encoder.c',
    'ima_waveform_encoder.py', 'waveform_kernel.py', 'ima_beam.py', 'ima_codec.py',
    'precompensate_voice.py', 'probe_feedback_packets.py', 'build_stream_trd.py',
    'stream-player.asm', 'stream-worker.asm', 'stream-progress.asm', 'ram-cache.asm',
    'direct_player.py', 'ima3_series.py', 'pcm_player.py', 'ram_cache.py',
    'ram_machine.py', 'audio_cover.py', 'feedback_player.py', 'packet_player.py',
    'pdm_player.py', 'build_pdm.py', 'assess_snr.py', 'convert_mulaw_audio.py',
    'probe_reconstruction_error.py', 'verify_stream_trd.py', 'verify_direct.py',
    'verify_packet.py', 'verify_pcm.py', 'verify_pdm.py',
    'experiments/song-snr/clock_control.py', 'experiments/song-snr/general.py',
    'experiments/song-snr/study.py',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def prepared_source(path):
    """Read bounded PCM8 without changing its samples, duration or guard."""
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 1, RATE, 'NONE'):
            raise ValueError('prepared PCM must be uncompressed mono PCM8 at 8000 Hz')
        count = wav.getnframes()
        if not 512 <= count <= MAXIMUM_SAMPLES or count % 512:
            raise ValueError(f'prepared PCM must have 512..{MAXIMUM_SAMPLES} samples, aligned to 512; oversized input is not truncated')
        raw = wav.readframes(count)
    if len(raw) != count:
        raise ValueError('prepared WAV is truncated: its data does not match the declared frame count')
    source = np.frombuffer(raw, 'u1').copy()
    if np.any(source[-GUARD:] != 128):
        raise ValueError('prepared PCM requires at least 128 final silent samples with value 128')
    return source, dict(input=str(path), prepared_pcm_unchanged=True,
                       prepared_samples=count, sample_rate_hz=RATE, channels=1, pcm_bits=8,
                       fixed_gain=1.0, edge_fade_samples=0, short_input_repetitions=1,
                       silence_guard_samples=GUARD, truncated=False,
                       original_content_preserved=True, selected_content_preserved=True,
                       source_sha256=sha(raw))


def ordinary_source(path, ffmpeg, duration=None):
    """Reuse conditioning, then undo the legacy phase-calibration repetition.

    The existing helper reads one extra sample to detect capacity overflow.
    An explicit duration is a user-selected excerpt; capacity overflow fails.
    Its repeated short loops have no purpose in this continuous player, so
    keep precisely one copy of the prepared source and its silent padding.
    """
    source, metadata = prepare_source(path, ffmpeg, duration=duration,
                                      maximum_samples=MAXIMUM_SAMPLES, alignment=512)
    explicit_excerpt = bool(metadata['truncated'] and duration is not None and
                            metadata['truncation_reason'] == 'requested duration')
    if metadata['truncated'] and not explicit_excerpt:
        raise ValueError('input exceeds one TRD audio capacity; use an explicit --duration to select a shorter excerpt')
    repetitions = metadata['short_input_repetitions']
    if not isinstance(repetitions, int) or repetitions < 1 or len(source) % repetitions:
        raise ValueError('source preparation returned inconsistent repetition metadata')
    if repetitions > 1:
        one = len(source) // repetitions
        if not np.array_equal(source, np.tile(source[:one], repetitions)):
            raise ValueError('source preparation repetition is not exact')
        source = source[:one].copy()
    if not 512 <= len(source) <= MAXIMUM_SAMPLES or len(source) % 512 or np.any(source[-GUARD:] != 128):
        raise ValueError('prepared source does not fit the TRD alignment and silent-guard contract')
    metadata.update(prepared_samples=len(source), short_input_repetitions=1,
                    legacy_short_input_repetitions_undone=repetitions,
                    maximum_packed_bytes=MAXIMUM_SAMPLES // 2,
                    explicit_excerpt_selected=explicit_excerpt,
                    original_content_preserved=not metadata['truncated'],
                    selected_content_preserved=True, source_sha256=sha(source.tobytes()),
                    quality_reference='One prepared PCM8 source at its original 8-kHz clock, with the same normalization, edge fades and silent padding in both candidates')
    return source, metadata


def instruction_timeline(samples):
    """Count every pulse on one resident Pentagon1024 batch, without ROM time.

    The ordinary path is 449 T (423 plus 26 in slot7); page and bank tails
    add 14 and 243 T respectively. This is identical to general.timeline for
    sources that fit Pentagon512. Larger TRDs use 56 extra physical banks,
    rather than pretending a 512-KiB refill has no physical disk latency.
    """
    if not 512 <= samples <= MAXIMUM_SAMPLES or samples % 512:
        raise ValueError('timeline requires a complete aligned one-TRD source')
    holds = np.tile(HOLDS, samples).astype(np.int64)
    holds[7::16] += 26
    batch, remaining = sections(samples // 2, 56)
    assert remaining == 0
    offset = 0
    for section in batch:
        for byte in range(256, section['bytes'] + 1, 256):
            at = (2 * (offset + byte) - 3) * 16 + 14
            if at < len(holds):
                holds[at] += 243 if byte == section['bytes'] else 14
        offset += section['bytes']
    return np.r_[0, np.cumsum(holds)] * CPU_CLOCK / 3584000


def compensated_prior(source, times):
    """Keep the original reference; zero only the search-excluded guard prior."""
    assert np.all(source[-GUARD:] == 128)
    nonzero = np.flatnonzero(source != 128)
    last_content_edge = (int(nonzero[-1]) + 1) if len(nonzero) else 0
    search_end = float(times[(len(source) - GUARD) * 16])
    assert search_end >= last_content_edge * CPU_CLOCK / RATE, 'settling guard would discard source content'
    target = compensate(source, times[::16], radius=PARAMETERS['lanczos_radius'], period=CPU_CLOCK / RATE)
    changed = int(np.count_nonzero(target[-GUARD:] != 128))
    target[-GUARD:] = 128
    return target, dict(reference_last_content_edge_sample=last_content_edge,
                        physical_search_end_seconds=search_end / CPU_CLOCK,
                        all_reference_content_precedes_settling_guard=True,
                        prior_guard_samples_zeroed_after_lanczos=changed,
                        original_reference_samples_changed=0,
                        scope='Only the compensated regularization prior guard is zeroed; the waveform search excludes these 128 samples')


def producer_snapshot(output):
    archive = output / 'producer-source'
    archive.mkdir()
    hashes = {}
    for name in PRODUCERS:
        data = (HERE / name).read_bytes()
        hashes[name] = sha(data)
        dest = archive / (name + '.gz')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(gzip.compress(data, mtime=0))
    smoke = HERE.parent / 'toolkit' / 'smoke_test_fuse.py'
    data = smoke.read_bytes()
    hashes['../toolkit/smoke_test_fuse.py'] = sha(data)
    (archive / 'smoke_test_fuse.py.gz').write_bytes(gzip.compress(data, mtime=0))
    save(archive / 'hashes.json', hashes)
    return hashes


def unchanged_producers(hashes):
    return all(sha((HERE / name).read_bytes()) == digest for name, digest in hashes.items())


def quality_measurement(source, packed, baseline, model, times, ffmpeg, scratch, output):
    """Render one fixed reference and two whole outputs with an identical filter."""
    count = (len(source) - 3) * 16 + 15
    edges = times[:count]
    values, fixed_edges = uniform(source / 256, edges[-1])
    wanted = filtered(values, fixed_edges, ffmpeg, scratch)
    _, _, _, bits = reference(packed, cycles=1, model=model)
    actual = filtered(bits[:count - 1], edges, ffmpeg, scratch)
    _, _, _, before_bits = reference(baseline, cycles=1, model=dict(models())['legacy'])
    before_actual = filtered(before_bits[:count - 1], edges, ffmpeg, scratch)
    if len(wanted) <= 8820:
        unavailable = dict(snr_db=None, error_rms=None, signal_rms=None,
                           reason='Source is too short for the fixed 100-ms crop at both edges',
                           measured_samples=0, scope='No shorter crop or fitted alignment substituted')
        after = dict(unavailable)
        before = dict(unavailable)
    else:
        after, before = metrics(wanted, actual), metrics(wanted, before_actual)
        after['measured_samples'] = before['measured_samples'] = len(wanted) - 8820
    gain = (after['snr_db'] - before['snr_db']) if after['snr_db'] is not None and before['snr_db'] is not None else None
    write_wav(output / 'reference.wav', wanted * .5)
    write_wav(output / 'host-actual.wav', actual * .5)
    write_wav(output / 'baseline-actual.wav', before_actual * .5)
    return dict(fixed_clock=after, baseline_fixed_clock=before, change_db=gain,
                snr_improvement_at_least_5_db=gain is not None and gain >= 5,
                snr_at_least_20_db=after['snr_db'] is not None and after['snr_db'] >= 20,
                source_rate_hz=RATE, source_specific_fitted_gain_delay_clock=False,
                listening_export_gain=.5, host_prediction=True,
                scope='Complete source at its original 8-kHz clock; same continuous listening filter and fixed 100-ms edges. No fitted gain, delay or clock.',
                baseline_algorithm='Uncompensated PCM-error IMA beam32/block64, legacy PDM table; generated automatically from this same prepared source')


def verify(output, disk, meta, packed, times, fuse):
    from verify_stream_trd import native_check, fuse_check
    work = output / 'verification'
    work.mkdir()
    native = [native_check(disk, meta, packed, profile, out=work / ('native-' + profile + '.json'))
              for profile in PROFILES]
    actual = []
    for profile in ('pentagon512', 'pentagon1024'):
        report = fuse_check(output / 'audio.trd', meta, packed, profile, work / profile, fuse)
        sufficient = len(packed) <= BASE_AUDIO_BYTES + PROFILES[profile]['pages'] * 16384
        if sufficient:
            raw = np.frombuffer(gzip.decompress((work / profile / 'times.u32.gz').read_bytes()), '<u4')
            np.testing.assert_array_equal(raw.astype(float) * CPU_CLOCK / 3584000, times[:report['bits_verified']])
            assert report['reloads'] == 0 and report['runtime_disk_reads_during_live_audio'] == 0
        report['complete_clock_matches_host_quality_model'] = sufficient
        report['quality_unqualified_due_to_insufficient_resident_ram'] = not sufficient
        actual.append(report)
    result = dict(complete=True, native=native, fuse=actual,
                  functional_checks_only_for_128_and_scorpion=True,
                  physical_hardware_tested=False, artifact_release_gates_unproven=True)
    save(work / 'execution.json', result)
    return result


def convert(input_path, output, *, cover=None, prepared_pcm=False, encoder='c',
            ffmpeg=None, duration=None, verify_fuse=None, started=None):
    started = time.perf_counter() if started is None else started
    if encoder not in ('c', 'python'):
        raise ValueError('encoder must be c or python')
    if prepared_pcm and duration is not None:
        raise ValueError('--duration cannot alter an explicitly prepared PCM source')
    ffmpeg = ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('FFmpeg is required for source decoding and the common quality filter')
    input_path = Path(input_path).resolve(strict=True)
    if not input_path.is_file():
        raise ValueError('input must be an audio/video file')
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output directory must be empty; existing files are not overwritten')
    cover_data = bytes(6912) if cover is None else Path(cover).read_bytes()
    if len(cover_data) != 6912:
        raise ValueError('cover must be a 6912-byte Spectrum SCR file')
    phase = time.perf_counter()
    source, preparation = prepared_source(input_path) if prepared_pcm else ordinary_source(input_path, ffmpeg, duration)
    preparation_seconds = time.perf_counter() - phase
    output.mkdir(parents=True, exist_ok=True)
    phase = time.perf_counter()
    hashes = producer_snapshot(output)
    snapshot_seconds = time.perf_counter() - phase
    parameters = dict(PARAMETERS)
    model = dict(models())[parameters['model_name']]
    frozen = dict(parameters=parameters, model=model, algorithm='joint', target_resident_profile='pentagon1024')
    save(output / 'parameters.json', dict(**frozen, sha256=sha(json.dumps(frozen, sort_keys=True).encode())))
    pcm_wav(output / 'source-preview.wav', source)
    (output / 'cover.scr').write_bytes(cover_data)
    timings = dict(source_preparation_seconds=preparation_seconds, producer_snapshot_seconds=snapshot_seconds)
    with tempfile.TemporaryDirectory(dir=output, prefix='.conversion-') as temporary:
        scratch = Path(temporary)
        assert scratch.resolve().is_relative_to(output)
        phase = time.perf_counter()
        times = instruction_timeline(len(source))
        target, coverage = compensated_prior(source, times)
        desired, features, ids, nxt, quantization = prepare_waveform(source, times, model)
        timings['model_preparation_seconds'] = time.perf_counter() - phase
        phase = time.perf_counter()
        statistics = {}
        options = dict(width=parameters['waveform_beam_width'], block_size=parameters['horizon_samples'],
                       commit_size=parameters['commit_samples'], regularization=parameters['regularization'])
        if encoder == 'c':
            workset = write_workset(scratch / 'encoder-input.bin', target, desired, features, ids, nxt, **options)
            packed = execute_workset(workset, scratch / 'encoded.ima', statistics)
            statistics.update(workset_sha256=file_sha(workset), workset_bytes=workset.stat().st_size,
                              executable_sha256=file_sha(statistics['executable']),
                              matrix_library_sha256=file_sha(statistics['matrix_library']))
        else:
            packed = encode_waveform(target, desired, features, ids, nxt, **options, backend='numpy', statistics=statistics)
            statistics.update(original_python_reference_unchanged=True,
                              optional_native_waveform_kernels=False,
                              original_python_reference_sha256=hashes['ima_waveform_encoder.py'])
        timings['waveform_encoding_seconds_including_workset_io_and_cold_compile'] = time.perf_counter() - phase
        del desired, features, ids, nxt
        pcm, indices = decode(packed)
        if len(packed) * 2 != len(source) or (int(pcm[-1]), int(indices[-1])) != (0, 0):
            raise RuntimeError('encoder did not preserve the complete source length and zero-state guard')
        saturation = require_unclipped(packed)
        phase = time.perf_counter()
        baseline_statistics = {}
        if encoder == 'c':
            baseline = encode_pcm_native(source, width=parameters['pcm_beam_width'],
                                         block_samples=parameters['pcm_block_samples'], statistics=baseline_statistics)
        else:
            baseline = encode_pcm(source, width=parameters['pcm_beam_width'], block_samples=parameters['pcm_block_samples'])
            baseline_statistics.update(backend='python-numpy', original_python_reference_unchanged=True,
                                       original_python_reference_sha256=hashes['ima_beam.py'])
        before_pcm, before_indices = decode(baseline)
        if len(before_pcm) != len(source) or (int(before_pcm[-1]), int(before_indices[-1])) != (0, 0):
            raise RuntimeError('baseline encoder did not retain the whole source and exact zero-state guard')
        require_unclipped(baseline)
        timings['baseline_encoding_seconds_including_cold_compile'] = time.perf_counter() - phase
        phase = time.perf_counter()
        disk, meta = build(packed, output / 'assembly', cover_data, model)
        (output / 'audio.trd').write_bytes(disk)
        (output / 'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
        (output / 'baseline.ima.gz').write_bytes(gzip.compress(baseline, mtime=0))
        pcm_wav(output / 'compensated-pcm.wav', target)
        save(output / 'player.json', meta)
        save(output / 'source.json', preparation)
        timings['trd_assembly_and_artifact_io_seconds'] = time.perf_counter() - phase
        phase = time.perf_counter()
        quality = quality_measurement(source, packed, baseline, model, times, ffmpeg, scratch, output)
        save(output / 'host-quality.json', quality)
        timings['host_quality_and_preview_io_seconds'] = time.perf_counter() - phase
    if not unchanged_producers(hashes):
        raise RuntimeError('producer sources changed during conversion; generated artifacts are not a reproducible completed run')
    report = dict(complete=True, encoder=encoder, parameters=parameters, model=model,
                  preparation=preparation, source_sha256=sha(source.tobytes()), packed_sha256=sha(packed),
                  trd_sha256=sha(disk), producer_sha256=hashes,
                  original_python_reference_unchanged=True,
                  original_python_reference_sha256=hashes['ima_waveform_encoder.py'],
                  statistics=statistics, baseline_statistics=baseline_statistics,
                  guard_coverage=coverage, saturation_guard=saturation,
                  runtime=dict(python=sys.version, numpy=np.__version__, ffmpeg=str(ffmpeg)),
                  source_samples=len(source), packed_bytes=len(packed), host_quality=quality,
                  search_query_quantization_max_seconds=quantization,
                  independent_boot_format=True, automatic_ram_profiles=list(PROFILES),
                  quality_target='Resident Pentagon playback at CPU 3584000 Hz; 128/Scorpion audio quality is not claimed',
                  required_resident_pentagon_ram_kib=512 if len(packed) <= BASE_AUDIO_BYTES + 24 * 16384 else 1024,
                  resident_capacities_bytes={name: BASE_AUDIO_BYTES + item['pages'] * 16384 for name, item in PROFILES.items()},
                  hot_path_instruction_delta_tstates=0,
                  ordinary_native_tstates={'128': 423, 'scorpion': 423, 'pentagon512': 449, 'pentagon1024': 449},
                  page_extra_tstates=14, bank_extra_tstates={'128': 243, 'scorpion': 267, 'pentagon512': 243, 'pentagon1024': 243},
                  release_accepted=False, status='research; artifact and corpus-regression gates remain unproven',
                  known_model_limitations=('The frozen half-recent model has measured whine/background and source regressions; automatic SNR scoring does not waive these gates'
                      if parameters['model_name'] == 'duration_zero_half_recent' else 'Artifact and source-regression release gates are not evaluated by this converter'),
                  timings=timings, complete_emulator_verification=None, physical_hardware_tested=False)
    save(output / 'conversion.json', report)
    timings['total_conversion_seconds'] = time.perf_counter() - started
    verification_seconds = 0.0
    if verify_fuse is not None:
        phase = time.perf_counter()
        report['complete_emulator_verification'] = verify(output, disk, meta, packed, times, Path(verify_fuse))
        verification_seconds = time.perf_counter() - phase
    timings['optional_verification_seconds'] = verification_seconds
    save(output / 'conversion.json', report)
    timings['grand_total_seconds_including_requested_verification'] = time.perf_counter() - started
    timings['scope'] = 'Monotonic wall time includes imports in CLI mode, source preparation, model preparation, cold compiler work, file I/O, TRD assembly, host quality and temporary cleanup; optional verification is separate and included in the grand total'
    save(output / 'conversion.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cover', type=Path, help='Optional 6912-byte Spectrum SCR; otherwise use a blank screen with runtime progress')
    parser.add_argument('--prepared-pcm', action='store_true', help='Keep mono PCM8/8000-Hz WAV bytes unchanged, including its aligned silent guard')
    parser.add_argument('--encoder', choices=('c', 'python'), default='c', help='Standalone complete C search or retained Python reference')
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--duration', type=float, help='Explicitly select this many seconds from ordinary media; capacity overflow is otherwise rejected')
    parser.add_argument('--verify-fuse', type=Path, metavar='FUSE_EXE', help='Additionally complete native four-profile and cold Pentagon Fuse checks')
    args = parser.parse_args(argv)
    try:
        result = convert(args.input, args.output, cover=args.cover, prepared_pcm=args.prepared_pcm,
                         encoder=args.encoder, ffmpeg=args.ffmpeg, duration=args.duration,
                         verify_fuse=args.verify_fuse, started=PROCESS_STARTED)
    except (ValueError, OSError, RuntimeError, wave.Error, subprocess.SubprocessError) as error:
        parser.exit(1, 'Conversion failed: ' + str(error) + '\n')
    print(json.dumps(dict(output=str(args.output.resolve()), audio_trd=str((args.output / 'audio.trd').resolve()),
                          encoder=result['encoder'], status=result['status'],
                          snr_db=result['host_quality']['fixed_clock']['snr_db'],
                          improvement_db=result['host_quality']['change_db'], timings=result['timings']), indent=2), flush=True)


if __name__ == '__main__':
    main()
