"""C host simulation isolating SDM input precision from packet-state precision.

A reproduces the archived 64-bin/32-state beta0.5 half-recent player exactly.
B retains that state quantization while accepting all decoded PCM16 bits.
C additionally carries unquantized double state. All use the same449-T packet
weights and complete physical449-T clock with page/bank tails. Existing IMA
nibbles are frozen: none is reoptimized for B/C. These counterfactuals do not
establish a Spectrum implementation, timing feasibility or an SNR ceiling.
"""
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import time
import uuid

import numpy as np

from artifact_diagnostics import (FREQUENCIES, compare_reports,
                                  tone_diagnostics, waveform_diagnostics)
from build_pdm import write_wav
from convert_audio import pcm_wav
from convert_mulaw_audio import STABLE_FILTER
from general import models, timeline
from ima_codec import decode
from pacing448_control import verify_archived_score
from pacing448_spectrum import spectrum
from probe_feedback_packets import integral_table
from probe_reconstruction_error import wav8
from study import filtered, metrics, uniform
import waveform_kernel


HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[1]
SOURCE = HERE / 'sdm16_precision.c'
HOLDS = (36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16)
NAMES = ('sea_foam', 'silence', 'quiet440', 'loud3000', 'steps',
         'quiet997', 'multitone', 'speech', 'entertainer')
LABELS = dict(a='a_6bit_packet32', b='b_16bit_packet32', c='c_16bit_continuous')
PRODUCERS = ('sdm16_precision.py', 'sdm16_precision.c', 'artifact_diagnostics.py',
             'general.py', 'study.py', 'pacing448_spectrum.py', 'pacing448_control.py')


def producer_files():
    files = {'experiments/song-snr/'+name: HERE/name for name in PRODUCERS}
    for name in ('ima_codec.py', 'probe_feedback_packets.py', 'waveform_kernel.py',
                 'convert_mulaw_audio.py', 'assess_snr.py', 'build_pdm.py',
                 'build_stream_trd.py', 'direct_player.py', 'probe_reconstruction_error.py',
                 'convert_audio.py', 'verify_direct.py', 'verify_packet.py'):
        files[name] = AUDIO/name
    return files


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def python_packet(pcm, seed=16, full_precision=False):
    """Independent exact Fraction recurrence for one quantized A/B packet."""
    if type(pcm) is not int or not -32768 <= pcm <= 32767 or type(seed) is not int or not 0 <= seed < 32:
        raise ValueError('Need signed PCM16 and a32-state seed')
    unsigned = pcm + 32768
    x = Fraction(unsigned, 65536) if full_precision else Fraction(unsigned >> 10, 64)
    q, recent = Fraction(seed//2-8, 8), Fraction(1 if seed % 2 else -1, 4)
    epsilon, word = Fraction(1, 10**12), 0
    for hold in HOLDS:
        weight = Fraction(16*hold, 449)
        u = x + q/weight + recent/2
        bit = int(u >= Fraction(1,2)-epsilon)
        recent = u-bit
        q += weight*(x-bit)
        word = word*2+bit
    qcode = max(0, min(15, (q*8+Fraction(17,2)+epsilon).__floor__()))
    rcode = max(0, min(1, (2*recent+1+epsilon).__floor__()))
    return word, 2*qcode+rcode


def build_executable():
    """Compile only this new standalone C program; no Python DLL or BLAS."""
    command = waveform_kernel._command()
    if command is None:
        raise RuntimeError('An installed C compiler is required')
    if os.name == 'nt':
        if not isinstance(command, str) or '/LD /MT' not in command:
            raise RuntimeError('Need the installed strict MSVC command')
        command = command.replace('/LD /MT', '/MT').replace('/OUT:kernel.dll', '/OUT:kernel.exe')
        binary_name = 'kernel.exe'
    else:
        command = [shutil.which('cc'), '-O3', '-std=c99', '-fno-fast-math',
                   '-ffp-contract=off', 'kernel.c', '-lm', '-o', 'kernel']
        binary_name = 'kernel'
    key = sha(SOURCE.read_bytes()+repr(command).encode()+platform.machine().encode())[:24]
    cache = AUDIO / '.native-cache' / ('sdm16-precision-'+key)
    binary = cache / binary_name
    if not binary.exists():
        private = cache / ('build-'+uuid.uuid4().hex)
        private.mkdir(parents=True)
        (private / 'kernel.c').write_bytes(SOURCE.read_bytes())
        result = subprocess.run(command, cwd=private, capture_output=True, timeout=120,
                                 creationflags=0x08000000 if os.name == 'nt' else 0)
        (private / 'build.log').write_bytes(result.stdout+result.stderr)
        if result.returncode or not (private / binary_name).exists():
            raise RuntimeError(f'SDM precision compiler failed; see {private / "build.log"}')
        try:
            (private / binary_name).rename(binary)
        except FileExistsError:
            pass
    return binary


def execute(binary, command, mode, pcm_file, word_file, state_file):
    result = subprocess.run([str(binary), command, mode, str(pcm_file), str(word_file), str(state_file)],
        capture_output=True, text=True, creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError(f'C SDM failed ({result.returncode}): {result.stderr}')
    return np.frombuffer(Path(word_file).read_bytes(), '>u2').copy(), np.frombuffer(
        Path(state_file).read_bytes(), 'u1').copy(), json.loads(result.stdout)


def c_cells(cells, mode, binary=None):
    if mode not in ('a', 'b'):
        raise ValueError('Only quantized A/B cells have32-state seeds')
    for pcm, seed in cells:
        if type(pcm) is not int or not -32768 <= pcm <= 32767 or type(seed) is not int or not 0 <= seed < 32:
            raise ValueError('Need signed PCM16 and a32-state seed')
    root = AUDIO.parent / '.tmp'
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix='sdm-cells-') as scratch:
        scratch = Path(scratch)
        source = scratch / 'cells.bin'
        source.write_bytes(b''.join(struct.pack('<hB', *row) for row in cells))
        words, states, _ = execute(binary or build_executable(), 'cells', mode,
            source, scratch/'words.bin', scratch/'states.bin')
    return words, states


def table_parity(binary=None):
    cells = [(1024*value-32768, state) for value in range(64) for state in range(32)]
    words, successor, _ = integral_table(64, 2, holds=HOLDS, beta=.5, extent=.5, pcm_origin=0)
    independent = [python_packet(*cell) for cell in cells]
    np.testing.assert_array_equal(np.array([row[0] for row in independent]).reshape(64,32), words)
    np.testing.assert_array_equal(np.array([row[1] for row in independent]).reshape(64,32), successor)
    for mode in ('a', 'b'):
        actual_words, actual_states = c_cells(cells, mode, binary)
        np.testing.assert_array_equal(actual_words.reshape(64,32), words)
        np.testing.assert_array_equal(actual_states.reshape(64,32), successor)
    witness = [(0,16), (64,16)]
    aw, an = c_cells(witness, 'a', binary)
    bw, bn = c_cells(witness, 'b', binary)
    assert (int(aw[0]), int(an[0])) == (int(aw[1]), int(an[1]))
    assert (int(bw[0]), int(bn[0])) != (int(bw[1]), int(bn[1]))
    return dict(complete=True, cells=2048,
        exact_fraction_matches_original_table=True,
        c_a_matches_original_words_and_successors=True,
        c_b_anchors_match_original_words_and_successors=True,
        low_pcm_bits_witness=[dict(pcm16=cell[0], seed=cell[1], a_word=int(aw[k]),
            a_next=int(an[k]), b_word=int(bw[k]), b_next=int(bn[k])) for k,cell in enumerate(witness)],
        order_parameter_beta=.5, table_weights=list(HOLDS), original_encoders_changed=False)


def original_stream(pcm):
    words, successor, _ = integral_table(64, 2, holds=HOLDS, beta=.5, extent=.5, pcm_origin=0)
    output = np.empty(len(pcm), '>u2')
    states = np.empty(len(pcm), 'u1')
    state = 16
    for i, value in enumerate(pcm):
        row = (int(value)+32768) >> 10
        output[i], state = words[row,state], int(successor[row,state])
        states[i] = state
    return output, states


def run_source(name, evidence, output, scratch, binary, include_continuous):
    started = time.perf_counter()
    source_path = evidence / 'general' / 'inputs' / (name+'.wav')
    source = wav8(source_path)
    archived = evidence / 'clock-joint' / name
    host = json.loads((archived/'host.json').read_bytes())
    packed = gzip.decompress((archived/'soundtrack.ima.gz').read_bytes())
    if sha(packed) != host['packed_sha256'] or sha(source.tobytes()) != host['source_sha256']:
        raise ValueError('Archived source/packed identity mismatch')
    expected_model = dict(models())['duration_zero_half_recent']
    if host['model'] != expected_model or tuple(expected_model['holds']) != HOLDS:
        raise ValueError('Frozen packet model differs from archived half-joint')
    dest, local = output/name, scratch/name
    dest.mkdir(); local.mkdir(parents=True, exist_ok=True)
    (dest/'source-preview.wav').write_bytes(source_path.read_bytes())
    (dest/'soundtrack.ima.gz').write_bytes((archived/'soundtrack.ima.gz').read_bytes())
    pcm, _ = decode(packed)
    pcm.astype('<i2').tofile(local/'decoded-pcm16.bin')
    times = timeline(len(source), 'pentagon')
    count = (len(source)-3)*16+15
    edges = times[:count]
    sample_edges = np.r_[edges[::16], edges[-1]]
    decoded = filtered((pcm[:len(sample_edges)-1].astype(float)+32768)/65536,
                        sample_edges, shutil.which('ffmpeg'), local)
    values, fixed_edges = uniform(source/256, edges[-1])
    wanted = filtered(values, fixed_edges, shutil.which('ffmpeg'), local)
    np.save(local/'decoded-reference.npy', decoded)
    np.save(local/'original-reference.npy', wanted)
    write_wav(dest/'decoded-reference.wav', decoded*.5)
    write_wav(dest/'original-reference.wav', wanted*.5)
    old_words, old_states = original_stream(pcm)
    variants, comparison_inputs = {}, {}
    for mode in ('a','b','c') if include_continuous else ('a','b'):
        label = LABELS[mode]
        words, states, statistics = execute(binary, 'stream', mode, local/'decoded-pcm16.bin',
            local/(label+'-words.bin'), local/(label+'-states.bin'))
        if len(words) != len(source) or len(states) != len(source):
            raise ValueError('C modulator did not retain the complete decoded source')
        if mode == 'a':
            np.testing.assert_array_equal(words, old_words)
            np.testing.assert_array_equal(states, old_states)
        bits = np.unpackbits(words.view('u1'))
        actual = filtered(bits[:count-1], edges, shutil.which('ffmpeg'), local)
        np.save(local/(label+'-actual.npy'), actual)
        write_wav(dest/(label+'-actual.wav'), actual*.5)
        (dest/(label+'-words.bin.gz')).write_bytes(gzip.compress(words.tobytes(), mtime=0))
        (dest/(label+'-states.bin.gz')).write_bytes(gzip.compress(states.tobytes(), mtime=0))
        diag = dict(source=name, variant=label,
            waveform=waveform_diagnostics(wanted, actual, frequencies=FREQUENCIES),
            fullband_error_spectrum=spectrum(actual-wanted),
            pdm_error_spectrum=spectrum(actual-decoded),
            actual_float64_sha256=sha(actual.astype('<f8').tobytes()),
            reference_float64_sha256=sha(wanted.astype('<f8').tobytes()),
            decoded_reference_float64_sha256=sha(decoded.astype('<f8').tobytes()),
            host_counterfactual_only=True, emulator_verified=False)
        if name in ('quiet440','quiet997','loud3000'):
            diag['known_tone'] = tone_diagnostics(wanted, actual,
                dict(quiet440=440, quiet997=997, loud3000=3000)[name], frequencies=FREQUENCIES)
        fixed, pdm = metrics(wanted, actual), metrics(decoded, actual)
        if mode == 'a':
            archived_proof = verify_archived_score(fixed, host['fixed_clock'])
        save(dest/(label+'-diagnostics.json'), diag)
        variants[label] = dict(input_precision_bits=6 if mode == 'a' else 16,
            packet_state_quantized=mode != 'c', state_precision='q16/r2' if mode != 'c' else 'continuous f64',
            beta=.5, table_generation_ordinary_tstates=449,
            pcm_samples=len(pcm), pcm16_sha256=sha(pcm.astype('<i2').tobytes()),
            word_bytes_sha256=sha(words.tobytes()), next_state_sha256=sha(states.tobytes()),
            fixed_clock=fixed, pdm_only_decoded_ima16_diagnostic=pdm,
            c_statistics=statistics, words_changed_from_a=int(np.count_nonzero(words!=old_words)),
            successor_changes_from_a=int(np.count_nonzero(states!=old_states)) if mode != 'c' else None)
        comparison_inputs[label] = diag
        print(json.dumps(dict(source=name, variant=label, total_snr_db=fixed['snr_db'],
            pdm_snr_db=pdm['snr_db'], rms=fixed['error_rms'], host_only=True)), flush=True)
    comparisons = [compare_reports(comparison_inputs[LABELS['a']], comparison_inputs[LABELS[mode]])
                   for mode in ('b','c') if LABELS[mode] in variants]
    report = dict(source=name, source_samples=len(source), source_sha256=host['source_sha256'],
        source_file_sha256=sha(source_path.read_bytes()), packed_sha256=host['packed_sha256'],
        decoded_pcm16_sha256=sha(pcm.astype('<i2').tobytes()),
        archived449_score_recheck=archived_proof,
        complete_a_bit_and_successor_parity=True, variants=variants, comparisons=comparisons,
        original_ima_nibbles_frozen=True, ima_reoptimized_for_new_modulators=False,
        reference_gain_bandwidth_edges_and_clock_unchanged=True,
        scope='Complete frozen449clock stream; original8k source totals and decodedIMA16 shared-clock PDM diagnostics; no fitted gain/delay/clock',
        new_player_implemented=False, z80_timing_feasibility_proven=False,
        emulator_verified=False, physical_hardware_tested=False, release_accepted=False,
        no_hard_snr_upper_bound_claim=True, elapsed_seconds=time.perf_counter()-started)
    save(dest/'host.json', report)
    return report


def run(evidence, output, scratch, include_continuous=True, names=None):
    evidence, output, scratch = map(lambda value: Path(value).resolve(), (evidence, output, scratch))
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty evidence directory; incomplete experiments are preserved')
    output.mkdir(parents=True, exist_ok=True); scratch.mkdir(parents=True, exist_ok=True)
    files = producer_files()
    hashes = {name: sha(path.read_bytes()) for name,path in files.items()}
    binary = build_executable()
    parity = table_parity(binary)
    save(output/'parity.json', parity)
    ffmpeg = Path(shutil.which('ffmpeg')).resolve()
    frozen = dict(producers=hashes, source_independent_parameters=True,
        executable_sha256=sha(binary.read_bytes()), executable=str(binary),
        ffmpeg_sha256=sha(ffmpeg.read_bytes()), ffmpeg=str(ffmpeg),
        beta=.5, extent=.5, weights=list(HOLDS), pcm_origin=0,
        input_mapping='(signedPCM16+32768)/65536; A floors unsigned/1024 to64 bins',
        packet_state_mapping='qcode=clip(floor(8q+8.5+1e-12),0,15); rcode=clip(floor(2r+1+1e-12),0,1)',
        initial_state=dict(id=16, q=0, recent=-.25), threshold_epsilon=1e-12,
        listening_filter=STABLE_FILTER, integration_rate_hz=768000,
        fixed_edges_seconds=.1, order_changed=False, input_gain_changed=False,
        original_encoders_changed=False, archived_ima_frozen=True,
        continuous_counterfactual_included=include_continuous)
    save(output/'configuration.json', frozen)
    archive = output/'producer-source'; archive.mkdir()
    for name,path in files.items():
        target = archive/(name+'.gz')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
    names = list(names or NAMES)
    if any(name not in NAMES for name in names) or len(names)!=len(set(names)):
        raise ValueError('Use unique names from the archived9-source corpus')
    rows = []
    for name in names:
        rows.append(run_source(name, evidence, output, scratch, binary, include_continuous))
        save(output/'partial.json', dict(complete=False, rows=rows))
        if hashes != {name:sha(path.read_bytes()) for name,path in files.items()}:
            raise RuntimeError('Frozen precision/measurement producer changed during execution')
    regressions = {}
    for row in rows:
        for comparison in row['comparisons']:
            bucket = regressions.setdefault(comparison['to_variant'], {})
            for key,value in comparison['numeric_regressions'].items():
                bucket[key] = bucket.get(key,0)+value
    report = dict(complete=True, whole9_source_corpus=len(rows)==9, rows=rows,
        regression_counts=regressions, parity=parity,
        actual449_physical_clock_frozen=True, original_ima_nibbles_frozen=True,
        host_counterfactual_only=True, z80_player_implemented=False,
        emulator_verified=False, physical_hardware_tested=False,
        release_accepted=False, hard_upper_bound_claim=False,
        decision='Separate input precision B from continuous state C; investigate every artifact/regression. Frozen old IMA paths are not reoptimized for either counterfactual and do not establish a total-quality ceiling.')
    save(output/'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--source', action='append', choices=NAMES)
    parser.add_argument('--no-continuous', action='store_true')
    args = parser.parse_args()
    run(args.evidence, args.output, args.scratch, include_continuous=not args.no_continuous, names=args.source)
