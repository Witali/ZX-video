"""Read-only audit of the authenticated tester DHA1 ROM and ZX port budget.

Never imports or runs tester builders. All writes are beneath --output. The
literal wire reader and predictor are independent of the tester Python/C
decoder; the native certificate is authenticated, not rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def audit(root, output):
    if output.exists():
        raise FileExistsError('Preserve completed evidence: ' + str(output))
    output.mkdir(parents=True)
    consumed = {}

    def read(relative):
        path = root / relative
        data = path.read_bytes()
        consumed[str(path)] = dict(bytes=len(data), sha256=sha(data), sha256_LF=sha(data.replace(b'\r\n', b'\n')))
        return data

    def js(relative):
        return json.loads(read(relative))

    base = 'audio/music/sea-foam/recorded-difference-history'
    release = base + '/r2r/25k/artifacts/'
    recipe = js(release + 'selection.json')
    meta = js(release + 'sea-foam-difference-r2r.json')
    rom = read(release + 'sea-foam-difference-r2r.bin')
    assert len(rom) == 65536 and sha(rom) == recipe['ROM_sha256'] == meta['rom_sha256']
    candidate = js(recipe['candidate_report'])
    native_raw = read(recipe['native_proof_report'])
    native = json.loads(native_raw)
    assert sha(native_raw.replace(b'\r\n', b'\n')) == recipe['native_proof_sha256_LF']
    assert native == recipe['native_proof']
    assert sha(read(recipe['candidate_report']).replace(b'\r\n', b'\n')) == recipe['expected_candidate_sha256_LF']
    assert native['candidate_ROM_sha256'] == recipe['ROM_sha256']

    # Authenticate only the retained executed source identities; no library or
    # builder is loaded and no native execution is claimed by this audit.
    for collection in (recipe['source_hashes_LF'], recipe['source_reports_LF'], native['source_hashes_LF']):
        for relative, digest in collection.items():
            assert sha(read(relative).replace(b'\r\n', b'\n')) == digest, relative
    for relative in (
        'AGENTS.md', base + '/README.md', base + '/src/kernel.py', base + '/src/probe.py',
        'audio/music/sea-foam/recorded-difference-25db/src/build.py',
        'audio/music/sea-foam/recorded-difference-25db/src/shared_parser.py',
        'audio/lib/dha-codec/README.md', 'audio/lib/dha-codec/FORMAT.md',
        'audio/lib/dha-codec/include/dha_codec.h', 'audio/lib/dha-codec/src/dha_common.c',
        'audio/lib/dha-codec/src/dha_decode.c', 'audio/lib/dha-codec/src/dha_encode.c',
        'audio/lib/dha-codec/src/dha_tables.inc.h',
    ):
        read(relative)

    replay_path = root / (release + 'replay.npz')
    assert sha(read(release + 'replay.npz')) == recipe['replay_sha256']
    with np.load(replay_path, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    assert set(arrays) == {'q', 'symbols', 'gains', 'model', 'decoder'}
    for key, array in arrays.items():
        identity = recipe['arrays'][key]
        assert list(array.shape) == identity['shape'] and array.dtype.str == identity['dtype']
        assert sha(array.tobytes()) == identity['sha256']
    q, symbols, gains, model, decoder = (arrays[key] for key in ('q', 'symbols', 'gains', 'model', 'decoder'))
    n = recipe['samples']
    assert n == len(q) == 375000 and recipe['sample_rate_hz'] == 25000
    start, stop = recipe['code_bytes'], recipe['code_bytes'] + recipe['payload_bytes']
    payload = rom[start:stop]
    assert sha(payload) == recipe['payload_sha256'] == meta['stream_sha256']
    assert rom[recipe['model_address']:recipe['model_address'] + 1024] == model.tobytes()
    # This compiled ROM stores quotient and dispatch planes rather than the
    # C library's packed(symbol,N)/base pairs. Bind both to the exact replay.
    pairs = sorted({(int(s), int(bits)) for s, bits, _ in decoder})
    ans_address = recipe['model_address'] + 1024
    quotient = np.asarray([int(base) >> int(bits) for _, bits, base in decoder], np.uint8)
    dispatch = np.asarray([recipe['dispatch_addresses'][pairs.index((int(s), int(bits)))] for s, bits, _ in decoder], np.uint8)
    assert rom[ans_address:ans_address + 256] == quotient.tobytes()
    assert rom[ans_address + 256:ans_address + 512] == dispatch.tobytes()

    wire = recipe['wire']
    cursor = 0
    stream = ''.join(f'{byte:08b}' for byte in payload)

    def bits(count):
        nonlocal cursor
        assert cursor + count <= len(stream)
        value = int(stream[cursor:cursor + count] or '0', 2)
        cursor += count
        return value

    # q,d1,d2,d3 are explicitly wider Python integers until bounds are proved.
    state = [0, 0, 0, 0]
    decoded = np.empty(n, '<i2')
    ans = wire['first_ans_state_after']
    control, gain = wire['initial_C'], wire['first_gain']
    ans_bits = gain_bits = 0
    ranges = [[10**9, -10**9] for _ in range(5)]
    suffix_counts = [0] * 7
    blocks = (n + 255) // 256
    for at in range(n):
        if at == 0:
            value = wire['first_sample']
            assert value == (0, 1, -1, 2, -2)[int(symbols[0])] * gain
            prediction = 0
        else:
            block, offset = divmod(at, 256)
            if offset == 0:
                tag = control & 31
                if block == blocks - 1:
                    assert tag == 31
                    gain, control = wire['final_gain'], 32
                else:
                    assert tag == int(gains[block])
                    gain, control = tag, 1
            if 1 <= offset <= 5 and not control & 32:
                control = (control << 1) | bits(1)
                gain_bits += 1
            label, count, base_value = map(int, decoder[ans])
            ans = base_value + bits(count)
            ans_bits += count
            suffix_counts[count] += 1
            assert label == int(symbols[at]) and gain == int(gains[block])
            oldq, d1, d2, d3 = state
            correction = 0 if oldq == 0 else int(model[0, abs(oldq) & 255]) * (1 if oldq > 0 else -1)
            prediction = oldq + correction + sum(int(model[row, d + 128]) for row, d in enumerate((d1, d2, d3), 1))
            value = prediction + (0, 1, -1, 2, -2)[label] * gain
        oldq, d1, d2, _ = state
        state = [value, value - oldq, value - oldq - d1, value - oldq - d1 - d2]
        assert -256 <= prediction <= 254 and -256 <= value <= 254
        assert all(-128 <= d <= 127 for d in state[1:])
        assert value == int(q[at]), at
        decoded[at] = value
        for span, value in zip(ranges, (prediction, *state)):
            span[0], span[1] = min(span[0], value), max(span[1], value)
    assert ans == 0 and control == 32 and cursor == meta['finite_wire']['payload_bits']
    assert len(stream) - cursor == 7 and '1' not in stream[cursor:]
    assert ans_bits == meta['finite_wire']['ans_bits'] and gain_bits == meta['finite_wire']['metadata_bits']
    assert sha(decoded.tobytes()) == recipe['arrays']['q']['sha256']
    dac = ((decoded.astype(np.int32) + 257) // 2).astype(np.uint8)
    assert sha(dac.tobytes()) == recipe['quality']['dac_codes_sha256']

    reference_path = Path(candidate['reference_path'])
    if not reference_path.is_absolute():
        reference_path = root / reference_path
    quality = recipe['quality']
    reference_available = reference_path.is_file()
    signal_ss, error_ss = quality['signal_sum_squares_pcm16'], quality['error_sum_squares_pcm16']
    assert sum(row['signal_sum_squares_pcm16'] for row in quality['per_second']) == signal_ss
    assert sum(row['error_sum_squares_pcm16'] for row in quality['per_second']) == error_ss
    assert sum(row['samples'] for row in quality['per_second']) == n
    assert math.isclose(10*math.log10(signal_ss/error_ss), quality['metrics']['output_ser_db'], abs_tol=1e-12)
    if reference_available:
        reference_raw = reference_path.read_bytes()
        consumed[str(reference_path)] = dict(bytes=len(reference_raw), sha256=sha(reference_raw))
        assert sha(reference_raw) == quality['reference_full_15_seconds_sha256']
        reference = np.frombuffer(reference_raw, '<i2').astype(np.int64)
        actual = (dac.astype(np.int64) - 128) * 256
        error = actual - reference
        assert int(np.dot(reference, reference)) == signal_ss
        assert int(np.dot(error, error)) == error_ss

    clock_hash = sha((822 + np.arange(2*n + 1, dtype=np.uint64)*800).astype('<u8').tobytes())
    output_hash = sha(dac.tobytes()*2 + dac[:1].tobytes())
    assert len(native['engines']) == 3
    for engine in native['engines']:
        assert engine['verified_outputs'] == 2*n + 1 and engine['full_loops'] == 2
        assert engine['all_intervals_tstates'] == 800 and engine['memory_writes'] == engine['lost_events'] == 0
        assert engine['DAC_sha256'] == output_hash and engine['output_timestamps_sha256'] == clock_hash

    ledger = candidate['timing']['predictor_ledger']
    for group in ledger['groups']:
        if 'operations' in group:
            assert sum(t for _, t in group['operations']) == group['tstates']
    assert [group['tstates'] for group in ledger['groups']] == [87, 51, 51, 59, 19, 29, 54, 51]
    assert sum(group['tstates'] for group in ledger['groups']) == 401
    parser = candidate['selected']['parser_clock_ledger']
    assert 87 + parser['lookup_T'] + parser['reader_T'] + parser['finish_T'] + 57 == 399
    assert all(row['reader_tstates'] == 157 for row in parser['reader_paths'])
    assert all(row['total_tstates'] == 57 for row in parser['handler_paths'])

    # Resident capacities are inherited from the existing player, not a proof
    # that a new decoded-PCM player can reuse every byte without new code.
    full_n = 720384
    ram_rows = []
    for machine, capacity in [('128', 91392), ('scorpion256', 222464), ('pentagon512', 484608), ('pentagon1024', 1008896)]:
        ram_rows.append(dict(machine=machine, inherited_audio_capacity_bytes=capacity,
                             pcm8_bytes=full_n, pcm8_fits_size_only=full_n <= capacity,
                             packed_q9_bytes=(full_n*9+7)//8, packed_q9_fits_size_only=(full_n*9+7)//8 <= capacity,
                             pcm16_bytes=full_n*2, pcm16_fits_size_only=full_n*2 <= capacity))

    report = dict(
        status='read-only-authenticated-architecture-audit', native_execution_rerun=False,
        tester_root=str(root), samples=n, seconds=n/25000,
        independent_whole_wire=dict(samples=n, exact_q=True, exact_symbols=True, exact_gains=True,
            exact_DAC=True, ROM_tables_exact=True, terminal_ans=ans, gain_control=control,
            consumed_bits=cursor, ANS_bits=ans_bits, gain_bits=gain_bits, padding_bits=7,
            suffix_length_histogram=suffix_counts, prediction_q_d1_d2_d3_ranges=ranges),
        identities=dict(ROM_sha256=sha(rom), payload_sha256=sha(payload), q_sha256=sha(decoded.tobytes()),
            DAC_sha256=sha(dac.tobytes()), model_sha256=sha(model.tobytes()),
            retained_reference_sha256=quality['reference_full_15_seconds_sha256']),
        published_quality_recheck=dict(measurement=recipe['quality']['measurement'],
            source_start_seconds=56, source_end_seconds=71, sample_rate_hz=25000,
            signal_sum_squares=signal_ss, error_sum_squares=error_ss,
            SER_dB=10*math.log10(signal_ss/error_ss), rms_error_pcm16=math.sqrt(error_ss/n),
            peak_error_pcm16=quality['metrics']['peak_abs_error_pcm16'],
            prepared_reference_path=str(reference_path), prepared_reference_available=reference_available,
            scalar_quality_recomputed_from_reference=reference_available,
            retained_sufficient_statistics_rechecked=True,
            note='R2R8 / 15-second excerpt only; not whole-song ZX filtered beeper SNR. When the prepared reference is absent, only retained sufficient-statistic arithmetic is rechecked.'),
        packing=dict(payload_bytes=len(payload), meaningful_bits=cursor, bits_per_sample=cursor/n,
            stored_bits_per_sample=len(payload)*8/n, bytes_per_second_25000=len(payload)/15,
            hypothetical_bytes_per_second_8000_same_bits_per_sample=cursor/n*8000/8,
            extrapolation_is_not_measured_8k_compression_or_quality=True,
            IMA4_at_8000_bytes_per_second=4000,
            fixed_model_bytes=1024, fixed_ANS_bytes=512, startup_code_padding_bytes=577, free_ROM_bytes=140,
            host_DHAF_header_bytes=1572, host_frame_header_bytes=32,
            host_max_frame_samples=4096, host_PCM16_fallback_bits_per_sample=16,
            board_wire_and_DHAF_are_distinct_formats=True),
        CPU=dict(tester_cpu_hz=20000000, native_period_T=800, parser_T=399,
            predictor_R2R_return_T=401, predictor_groups=ledger['groups'],
            current_parser_normalized=True, parser_399_is_not_a_lower_bound=True,
            parser_components_T=dict(preface=87, lookup=70, reader=157, finish=28, residual_handler=57),
            ZX_cpu_hz=3584000, ZX_rate=8000, ZX_budget_T=448,
            current_decoder_utilization=800/448, decoder_only_max_rate_hz=3584000/800,
            remaining_T_after_unchanged_predictor=47, decoder_over_budget_T=352,
            minimum_16_OUT_immediate_T=176, minimum_16_OUT_C_T=192,
            predictor_before_final_OUT_and_return_T=380,
            unchanged_predictor_plus_16_immediate_OUT_T=556,
            note='Counts exclude Spectrum contention, paging, UI and disk work. Not an impossibility bound for a redesigned decoder or predecode.'),
        register_contract=dict(main='BC=q+256; D=d1+128; E=d2+128; IXL=d3+128; HL scratch; SP residual/accumulator/new d1',
            alternate='HL=ROM bit cursor; B=sentinel bit reservoir; C=pending gain; D=current G; E=block count',
            additional="AF'=ANS state; IXH=current G; IYH=0; IYL=residual handler; I=free8",
            incompatibility='SP is arithmetic state; all normal main/alternate data registers are occupied. Existing IMA/SDM lookup ABI cannot be kept by substitution.'),
        precision=dict(predictive_q_range=[-256,254], predictive_state_bits_about=9,
            predictive_PCM16_formula='(((q+257)//2)-128)*256', predictive_low8_bits_zero=True,
            PCM16_container_does_not_mean_16bit_predictive_precision=True,
            raw_q9_possible_but_changes_output_objective=True,
            PDM_library_helper='first-order unsigned8 phase accumulator; schedule provided by caller'),
        model_provenance=dict(model_sha256=sha(model.tobytes()),
            training_source='sea-foam original source 56..71 seconds, 375000 samples at 25 kHz',
            method='Ordinary least squares, q1/d1/d2/d3 frozen-history features; each signed8 correction table rounded separately with np.rint',
            library_default_is_frozen_not_refitted_per_upload=True,
            general_source_quality_not_established_by_training_excerpt=True),
        predecode_size_only=dict(full_ZX_source_samples=full_n, sample_rate_hz=8000,
            rows=ram_rows, native25000_full_90_seconds_PCM8_bytes=2250000,
            caveat='Inherited IMA audio capacity is an estimate for a different PCM player. Need new code/table/workspace ledger, compressed/decoded coexistence strategy, actual loading speed and seamless playback proof.'),
        decision='Test the fixed C library on unchanged 8-kHz complete sources and holdouts first. If quality/size gates pass, predecode to RAM or design a new fused decoder; the published 20-MHz decoder cannot be inserted in the current 448-T SDM loop.',
    )
    # Verify the read-only promise with every consumed byte identity, including
    # the replay/reference. This checks mutation only for the audited files.
    after = {path: sha(Path(path).read_bytes()) for path in consumed}
    assert all(after[path] == row['sha256'] for path, row in consumed.items())
    report['all_consumed_tester_files_unchanged'] = True
    report['authenticated_native_outputs'] = sum(row['verified_outputs'] for row in native['engines'])
    save(output/'report.json', report)
    save(output/'inputs.json', consumed)
    save(output/'native-certificate.json', native)
    save(output/'parser-ledger.json', parser)
    save(output/'source-selection.json', recipe)
    save(output/'manifest.json', dict(schema='DHA-architecture-audit-1',
        producer=str(Path(__file__).resolve()), producer_sha256=sha(Path(__file__).read_bytes()),
        artifacts={path.name: dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes())) for path in sorted(output.iterdir()) if path.is_file()},
        tester_files_unchanged=True, no_tester_builder_encoder_native_process_run=True))
    print(json.dumps(dict(status=report['status'], samples=n, SER_dB=report['published_quality_recheck']['SER_dB'],
        bits_per_sample=cursor/n, decoder_T=800, ZX_budget_T=448,
        tester_files_unchanged=True, output=str(output)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tester-root', type=Path, default=Path('C:/Work/z80-tester'))
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'evidence/dha-architecture')
    args = parser.parse_args()
    audit(args.tester_root.resolve(), args.output.resolve())
