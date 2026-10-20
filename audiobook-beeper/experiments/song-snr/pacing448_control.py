"""Frozen C-encoder host control for 448-T Pentagon pacing.

The first candidate intentionally retains the 449-T half-recent packet table.
Only physical scheduling changes. Each output is measured against the original
uniform 8-kHz source on its own schedule; the archived 449-T control is never
reclocked. Host evidence is not a complete player/emulator acceptance proof.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

from artifact_diagnostics import (clock_diagnostics, compare_reports,
                                  tone_diagnostics, waveform_diagnostics)
from build_pdm import CPU_CLOCK, write_wav
from build_stream_trd import sections
from clock_control import PARAMETERS, prepare, score
from convert_audio import pcm_wav
from convert_mulaw_audio import STABLE_FILTER
from direct_player import HOLDS
from general import models, timeline as historical_timeline
from ima_codec import decode, require_unclipped
from native_waveform_encoder import execute_workset, write_workset
from precompensate_voice import compensate
from probe_reconstruction_error import wav8


HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[1]
NAMES = ('silence', 'quiet440', 'loud3000', 'steps', 'quiet997',
         'multitone', 'speech', 'entertainer', 'sea_foam')
LONG_NAMES = NAMES[:6]
LONG_SAMPLES = 131072
GUARD_SAMPLES = 512
# New nominal 448-T rate is exactly 8000 Hz. The page/bank overhead remains
# explicit in the physical trace; these declared frequencies are not audio fits.
FREQUENCIES = (8000 / 32768, 2., 5., 10., 8000 / 512,
               25., 50., 8000 / 128, 100., 8000 / 64)
ARCHIVED_SNR_TOLERANCE_DB = 1e-7
ARCHIVED_RMS_TOLERANCE = 2e-10
PRODUCERS = (
    'ima_waveform_encoder.py', 'ima_beam.py', 'ima_codec.py',
    'native_waveform_encoder.py', 'native_waveform_encoder.c',
    'native_waveform_prepare.py', 'native_waveform_prepare.c',
    'waveform_kernel.py', 'precompensate_voice.py',
    'probe_feedback_packets.py', 'verify_direct.py', 'build_pdm.py',
    'convert_mulaw_audio.py', 'assess_snr.py',
    'experiments/song-snr/clock_control.py',
    'experiments/song-snr/general.py', 'experiments/song-snr/study.py',
    'experiments/song-snr/artifact_diagnostics.py',
    'experiments/song-snr/pacing448_control.py',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n',
                          encoding='utf-8')


def model_for(ordinary):
    if type(ordinary) is not int or ordinary not in (448, 449):
        raise ValueError('Need literal integer 448 or 449 ordinary T states')
    result = dict(dict(models())['duration_zero_half_recent'])
    result['holds'] = list(result['holds'])
    assert sum(result['holds']) == 449
    result['audio_progress_ui'] = True
    if ordinary == 448:
        result['pentagon_ordinary_tstates'] = 448
    return result


def instruction_timeline(samples, ordinary):
    """Count the complete resident schedule independently of the public CLI.

    A packet's slot 7 carries the 25/26-T pacing delay. The existing page and
    bank tail adds 14/243 T at the original pipeline position, including bank7's
    shorter protected allocation. Timestamps use the common renderer CPU units.
    """
    if (type(samples) is not int or samples < 512 or samples % 512 or
            type(ordinary) is not int or ordinary not in (448, 449)):
        raise ValueError('Need a complete 512-aligned source and 448/449 pace')
    holds = np.tile(HOLDS, samples).astype(np.int64)
    holds[7::16] += ordinary - sum(HOLDS)
    batch, remaining = sections(samples // 2, 56)
    if remaining:
        raise ValueError('Source exceeds resident Pentagon1024 capacity')
    offset = 0
    for section in batch:
        for byte in range(256, section['bytes'] + 1, 256):
            at = (2 * (offset + byte) - 3) * 16 + 14
            if at < len(holds):
                holds[at] += 243 if byte == section['bytes'] else 14
        offset += section['bytes']
    return np.r_[0, np.cumsum(holds)] * CPU_CLOCK / 3584000


def generated_source(name, count=LONG_SAMPLES):
    """Extend the existing generated waveform definitions without retuning."""
    if name not in LONG_NAMES or type(count) is not int or count % 512:
        raise ValueError('Need a named generated source and 512-aligned length')
    t = np.arange(count) / 8000
    tone = lambda frequency, amplitude: 128 + 128 * amplitude * np.sin(2 * np.pi * frequency * t)
    values = {
        'silence': lambda: np.full(count, 128.),
        'quiet440': lambda: tone(440, 4 / 128),
        'loud3000': lambda: tone(3000, .75),
        'steps': lambda: np.where((np.arange(count) // 256) % 2, 220., 36.),
        'quiet997': lambda: tone(997, 2 / 128),
        'multitone': lambda: 128 + 128 * (.32 * np.sin(2*np.pi*311*t)
            + .24 * np.sin(2*np.pi*1709*t) + .14 * np.sin(2*np.pi*3299*t)),
    }[name]()
    content = np.clip(np.rint(values), 0, 255).astype('u1')
    return np.r_[content, np.full(GUARD_SAMPLES, 128, 'u1')]


def verify_archived_score(actual, archived):
    """Fail on a stale packed stream, changed filter or reconstructed score."""
    before, after = archived['snr_db'], actual['snr_db']
    if (before is None) != (after is None):
        raise ValueError('Archived silence/non-silence classification changed')
    if before is not None and abs(before - after) > ARCHIVED_SNR_TOLERANCE_DB:
        raise ValueError(f'Archived 449-T SNR did not reproduce: {before} vs {after}')
    if abs(archived['error_rms'] - actual['error_rms']) > ARCHIVED_RMS_TOLERANCE:
        raise ValueError('Archived 449-T absolute error RMS did not reproduce')
    return dict(passed=True, snr_tolerance_db=ARCHIVED_SNR_TOLERANCE_DB,
                error_rms_tolerance=ARCHIVED_RMS_TOLERANCE,
                snr_delta_db=None if before is None else after-before,
                error_rms_delta=actual['error_rms']-archived['error_rms'])


def producer_hashes():
    return {name: sha((AUDIO / name).read_bytes()) for name in PRODUCERS}


def frozen_configuration(ffmpeg):
    binary = Path(ffmpeg).resolve()
    version = subprocess.run([str(binary), '-version'], check=True,
                             capture_output=True, text=True).stdout.splitlines()[0]
    return dict(schema=1, parameters=dict(PARAMETERS),
                baseline_model=model_for(449), candidate_model=model_for(448),
                source_rate_hz=8000, generated_content_samples=LONG_SAMPLES,
                generated_guard_samples=GUARD_SAMPLES,
                diagnostic_frequencies_hz=list(FREQUENCIES),
                measurement_filter=STABLE_FILTER, integration_rate_hz=768000,
                listening_rate_hz=44100, edge_exclusion_seconds=.1,
                fitted_gain_delay_clock=False, producers=producer_hashes(),
                ffmpeg=dict(path=str(binary), sha256=sha(binary.read_bytes()), version=version),
                source_specific_parameters=False, table_weights_ordinary_tstates=449,
                page_extra_tstates=14, bank_extra_tstates=243,
                emulator_verified=False, physical_hardware_tested=False)


def encode(source, times, model, scratch):
    started = time.perf_counter()
    target = compensate(source, times[::16], radius=PARAMETERS['lanczos_radius'],
                        period=CPU_CLOCK / 8000)
    # The regularization guard is outside searched content. It may not hide
    # any nonzero original sample when a faster physical schedule is used.
    last = np.flatnonzero(source != 128)
    last_edge = int(last[-1]) + 1 if len(last) else 0
    search_end = times[(len(source) - 128) * 16] / CPU_CLOCK
    if search_end < last_edge / 8000:
        raise ValueError('Physical settling guard would discard source content')
    changed_guard = int(np.count_nonzero(target[-128:] != 128))
    target[-128:] = 128
    desired, features, ids, nxt, quantization = prepare(source, times, model, backend='native')
    prepared_seconds = time.perf_counter() - started
    workset = write_workset(scratch / 'workset.bin', target, desired, features, ids, nxt,
        width=32, block_size=128, commit_size=64, regularization=.1)
    statistics = {}
    before = time.perf_counter()
    packed = execute_workset(workset, scratch / 'encoded.ima', statistics)
    statistics.update(workset_sha256=sha(workset.read_bytes()),
                      workset_bytes=workset.stat().st_size,
                      executable_sha256=sha(Path(statistics['executable']).read_bytes()),
                      matrix_library_sha256=sha(Path(statistics['matrix_library']).read_bytes()))
    pcm, indices = decode(packed)
    if len(packed) * 2 != len(source) or (int(pcm[-1]), int(indices[-1])) != (0, 0):
        raise ValueError('Incomplete stream or nonzero final settling state')
    guard = require_unclipped(packed)
    workset.unlink()
    (scratch / 'encoded.ima').unlink()
    return packed, target, dict(statistics=statistics, saturation_guard=guard,
        model_preparation_seconds=prepared_seconds,
        c_encoding_and_workset_seconds=time.perf_counter()-before,
        max_search_query_quantization_seconds=quantization,
        last_content_edge_sample=last_edge, physical_search_end_seconds=search_end,
        all_content_precedes_settling_guard=True,
        regularization_guard_samples_zeroed=changed_guard,
        original_reference_samples_changed=0)


def diagnostic(source, variant, wanted, actual, times):
    row = dict(source=source, variant=variant,
        waveform=waveform_diagnostics(wanted, actual, frequencies=FREQUENCIES),
        host_prediction=True, new_emulator_verified=False,
        reference_float64_sha256=sha(wanted.astype('<f8').tobytes()),
        actual_float64_sha256=sha(actual.astype('<f8').tobytes()))
    name = source.removeprefix('long_')
    if name in ('quiet440', 'quiet997', 'loud3000'):
        row['known_tone'] = tone_diagnostics(wanted, actual,
            dict(quiet440=440, quiet997=997, loud3000=3000)[name],
            frequencies=FREQUENCIES)
    count = (len(times)-1) // 16
    end = (count-3)*16+15
    row['clock'] = clock_diagnostics(times[:end], cpu_hz=CPU_CLOCK,
                                      frequencies=FREQUENCIES)
    return row


def fingerprint(data):
    return sha(json.dumps(data, sort_keys=True, allow_nan=False).encode())


def completed_files(folder):
    return {str(path.relative_to(folder)).replace('\\', '/'): dict(
        sha256=sha(path.read_bytes()), bytes=path.stat().st_size)
        for path in sorted(folder.rglob('*')) if path.is_file() and path.name != 'complete.json'}


def source_control(name, source, source_wav, archived, archived_packed,
                   output, scratch, ffmpeg, run_fingerprint, resume=False):
    dest = output / name
    identity = dict(source_sha256=sha(source.tobytes()),
                    source_file_sha256=sha(source_wav), samples=len(source),
                    run_fingerprint=run_fingerprint,
                    archived_host_sha256=None if archived is None else fingerprint(archived),
                    archived_packed_sha256=None if archived_packed is None else sha(archived_packed))
    marker = dest / 'complete.json'
    if resume and marker.exists():
        prior = json.loads(marker.read_bytes())
        if prior['identity'] != identity or prior['files'] != completed_files(dest):
            raise ValueError(f'Stale or modified completed evidence for {name}')
        return json.loads((dest / 'host.json').read_bytes())
    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f'Incomplete output exists for {name}; preserve it and select a fresh output')
    dest.mkdir(parents=True, exist_ok=True)
    local = scratch / name
    local.mkdir(parents=True, exist_ok=True)
    (dest / 'source-preview.wav').write_bytes(source_wav)
    save(dest / 'source-identity.json', identity)
    source_started = time.perf_counter()
    variants = {}
    archive_proof = None
    for ordinary, label in ((449, 'before449'), (448, 'candidate448')):
        model = model_for(ordinary)
        times = instruction_timeline(len(source), ordinary)
        if ordinary == 449:
            np.testing.assert_array_equal(times, historical_timeline(len(source), 'pentagon'))
        if ordinary == 449 and archived is not None:
            if (archived['source_sha256'] != identity['source_sha256'] or
                    archived['packed_sha256'] != sha(archived_packed) or
                    archived['parameters'] != PARAMETERS or
                    archived['model'] != dict(models())['duration_zero_half_recent']):
                raise ValueError(f'Archived source/model/parameters failed identity for {name}')
            packed = archived_packed
            encoding = dict(reused_archived_449_joint=True,
                            archived_host=archived,
                            saturation_guard=require_unclipped(packed))
            prior = None
        else:
            packed, prior, encoding = encode(source, times, model, local)
        (dest / (label + '.ima.gz')).write_bytes(gzip.compress(packed, mtime=0))
        if prior is not None:
            pcm_wav(dest / (label + '-prior.wav'), prior)
        result, wanted, actual = score(source, packed, model, times, ffmpeg, local)
        if ordinary == 449 and archived is not None:
            archive_proof = verify_archived_score(result, archived['fixed_clock'])
        np.save(local / (label + '-reference.npy'), wanted)
        np.save(local / (label + '-actual.npy'), actual)
        write_wav(dest / (label + '-reference.wav'), wanted * .5)
        write_wav(dest / (label + '-actual.wav'), actual * .5)
        diag = diagnostic(name, label, wanted, actual, times)
        save(dest / (label + '-diagnostics.json'), diag)
        variants[label] = dict(model=model, ordinary_tstates=ordinary,
            packed_sha256=sha(packed), fixed_clock=result, encoding=encoding,
            diagnostics=diag)
        print(json.dumps(dict(source=name, variant=label, snr_db=result['snr_db'],
            error_rms=result['error_rms'], host_only=True)), flush=True)
    comparison = compare_reports(variants['before449']['diagnostics'], variants['candidate448']['diagnostics'])
    save(dest / 'comparison.json', comparison)
    # Avoid duplicating the large diagnostics in host.json. Those separately
    # hashed records preserve every frequency, band and known-tone indicator.
    for row in variants.values():
        del row['diagnostics']
    legacy = None if archived is None else archived['baseline_fixed_clock']
    after = variants['candidate448']['fixed_clock']['snr_db']
    legacy_snr = None if legacy is None else legacy['snr_db']
    report = dict(source=name, source_identity=identity, variants=variants,
        source_sha256=identity['source_sha256'], source_samples=len(source),
        packed_sha256=variants['candidate448']['packed_sha256'],
        model=variants['candidate448']['model'], parameters=dict(PARAMETERS),
        fixed_clock=variants['candidate448']['fixed_clock'],
        archived_449_score_recheck=archive_proof, comparison=comparison,
        authenticated_legacy449_fixed_clock=legacy,
        song_gain_against_archived_legacy449_db=(after-legacy_snr
            if name == 'sea_foam' and after is not None and legacy_snr is not None else None),
        original_source_clock_hz=8000, reference_gain_changed=False,
        original_content_preserved=True, host_prediction=True,
        emulator_verified=False, physical_hardware_tested=False,
        source_specific_fitted_gain_delay_clock=False,
        elapsed_seconds=time.perf_counter()-source_started,
        scope='Whole source; separate actual448/449 instruction clocks; fixed100ms edges; continuous unchanged listening filter; no fitted gain, delay or clock',
        release_accepted=False)
    # Keep the established execution harness input contract as byte-identical
    # aliases. Both before/after streams remain explicitly named alongside it.
    (dest / 'soundtrack.ima.gz').write_bytes((dest / 'candidate448.ima.gz').read_bytes())
    save(dest / 'host.json', report)
    save(marker, dict(identity=identity, files=completed_files(dest)))
    return report


def run(evidence, output, scratch, ffmpeg, names=None, include_long=True, resume=False):
    evidence, output, scratch = map(lambda value: Path(value).resolve(), (evidence, output, scratch))
    configuration = frozen_configuration(ffmpeg)
    run_id = fingerprint(configuration)
    if output.exists() and any(output.iterdir()):
        if not resume or not (output / 'configuration.json').exists():
            raise ValueError('Output must be empty unless a fingerprint-checked resume is requested')
        if json.loads((output / 'configuration.json').read_bytes()) != dict(
                fingerprint=run_id, **configuration):
            raise ValueError('Producer, filter, FFmpeg or frozen parameters changed; stale resume refused')
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    save(output / 'configuration.json', dict(fingerprint=run_id, **configuration))
    archive_dir = output / 'producer-source'
    archive_dir.mkdir(exist_ok=True)
    for name in PRODUCERS:
        path = archive_dir / (name + '.gz')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress((AUDIO / name).read_bytes(), mtime=0))
    names = list(names or NAMES)
    if any(name not in NAMES for name in names) or len(names) != len(set(names)):
        raise ValueError('Need unique names from the frozen nine-source corpus')
    selected = names + (['long_' + name for name in LONG_NAMES] if include_long else [])
    rows = []
    for name in selected:
        long = name.startswith('long_')
        if long:
            source = generated_source(name.removeprefix('long_'))
            temporary_wav = scratch / (name + '.wav')
            pcm_wav(temporary_wav, source)
            data = temporary_wav.read_bytes()
            archived = archived_packed = None
        else:
            path = evidence / 'general' / 'inputs' / (name + '.wav')
            source, data = wav8(path), path.read_bytes()
            root = evidence / 'clock-joint' / name
            archived = json.loads((root / 'host.json').read_bytes())
            archived_packed = gzip.decompress((root / 'soundtrack.ima.gz').read_bytes())
        rows.append(source_control(name, source, data, archived, archived_packed,
            output, scratch, ffmpeg, run_id, resume=resume))
        save(output / 'partial.json', dict(complete=False, run_fingerprint=run_id, rows=rows))
        if producer_hashes() != configuration['producers']:
            raise RuntimeError('Frozen encoder/measurement producer changed during the run')
    regressions = {}
    for row in rows:
        for key, value in row['comparison']['numeric_regressions'].items():
            regressions[key] = regressions.get(key, 0) + value
    report = dict(complete=True, host_corpus_complete=len(rows) == 15,
        run_fingerprint=run_id, selected_sources=selected, rows=rows,
        regression_counts=regressions, source_independent_parameters=True,
        all_archived_scores_reproduced=True,
        both_clock_sources_original_uniform_8000_hz=True,
        physical_schedule_changed=True, table_generation_weights_changed=False,
        emulator_verified=False, physical_hardware_tested=False,
        release_accepted=False,
        decision='Host control only; compare every SNR, absolute noise, spectral, AM and delay increase before selecting full player execution. No artifact gate is waived.')
    save(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--source', action='append', choices=NAMES)
    parser.add_argument('--no-long', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error('FFmpeg is required')
    run(args.evidence, args.output, args.scratch, args.ffmpeg, names=args.source,
        include_long=not args.no_long, resume=args.resume)


if __name__ == '__main__':
    main()
