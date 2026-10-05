"""Reproduce exact codec checks and three bounded native optimization rounds."""
import argparse
from pathlib import Path
import time

import numpy as np
from g726.codec import (Codec, build_host, build_z80, ffmpeg_decode, ffmpeg_encode,
                        pack, unpack, save, sha, annotate_assembly)
from convert_g726_audio import convert


def host_checks(codecs, ffmpeg):
    rng = np.random.default_rng(726)
    n = 8192
    t = np.arange(n)/8000
    fixtures = {
        'silence': np.zeros(n, dtype='<i2'),
        'dc_positive': np.full(n, 32767, dtype='<i2'),
        'dc_negative': np.full(n, -32768, dtype='<i2'),
        'alternating_extremes': np.tile(np.array([-32768, 32767], dtype='<i2'), n//2),
        'impulse': np.r_[32767, np.zeros(n-1)].astype('<i2'),
        'ramp': np.linspace(-32768, 32767, n).astype('<i2'),
        'sine': np.rint(26000*np.sin(2*np.pi*733*t)).astype('<i2'),
        'chirp': np.rint(24000*np.sin(2*np.pi*(50*t+1900*t*t))).astype('<i2'),
        'random_pcm': rng.integers(-32768, 32768, n, dtype=np.int16),
    }
    rows = []
    for little in (False, True):
        # Exhaust all possible bytes in both standardized transport packings.
        raw = bytes(range(256))
        assert pack(unpack(raw, little), little)==raw
    for name, pcm in fixtures.items():
        base = codecs[0].encode(pcm)
        decoded, state = codecs[0].decode(base)
        for little in (False, True):
            payload = pack(base, little)
            assert payload==ffmpeg_encode(pcm, ffmpeg, little), name
            np.testing.assert_array_equal(decoded, ffmpeg_decode(payload, ffmpeg, little))
        for codec in codecs[1:]:
            np.testing.assert_array_equal(codec.encode(pcm), base)
            other, raw = codec.decode(base)
            np.testing.assert_array_equal(other, decoded)
            assert raw.raw==state.raw
        rows.append(dict(name=name, samples=len(pcm), encoder_exact=True, decoder_exact=True,
                         msb_and_lsb_checked=True, all_optimization_states_exact=True))
    codes = np.concatenate([unpack(bytes(range(256))),
        *(np.full(8192, i, dtype='u1') for i in range(4)),
        rng.integers(0, 4, 262144, dtype='u1')])
    expected, state = codecs[0].decode(codes)
    np.testing.assert_array_equal(expected, ffmpeg_decode(pack(codes), ffmpeg))
    for codec in codecs:
        actual, raw = codec.decode(codes)
        np.testing.assert_array_equal(actual, expected)
        assert raw.raw==state.raw
        streaming_state = codec.state()
        pieces = []
        # Deliberately not byte-aligned: the decoded state has no packet reset.
        for start in range(0, len(codes), 257):
            part, streaming_state = codec.decode(codes[start:start+257], streaming_state)
            pieces.append(part)
        np.testing.assert_array_equal(np.concatenate(pieces), expected)
        assert streaming_state.raw==state.raw
    for invalid in (np.array([0, 1, 2]), np.array([0, 1, 2, 4])):
        try:
            pack(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid packed codes accepted')
    return dict(passed=True, pcm_fixtures=rows, arbitrary_code_samples=len(codes),
        all_four_optimizations_exact=True, streamed_state_matches_whole=True,
        invalid_packing_rejected=True, ffmpeg_sha256=sha(ffmpeg),
        scope='FFmpeg compatibility and cross-optimization tests; not official ITU conformance vectors.')


def run(args):
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    variants = []
    for opt in range(4):
        folder = out/f'opt{opt}'
        host = folder/'host'
        native = folder/'z80'
        if not args.reuse:
            library = build_host(host, opt)
            build_z80(native, args.sdcc, opt)
        else:
            import os
            library = host/('kernel.dll' if os.name=='nt' else 'kernel.so')
            assert library.is_file() and (native/'decoder.ihx').is_file()
            annotate_assembly(native/'decoder.asm')
        variants.append((Codec(library), native, library))
        print(f'Compiled opt{opt}', flush=True)
    checks = host_checks([r[0] for r in variants], args.ffmpeg)
    save(out/'host-checks.json', checks)
    print('All host compatibility/state checks passed', flush=True)
    audition = convert(args.source, out/'audition', args.ffmpeg, 60, variants[3][2])
    codes = unpack((out/'audition/soundtrack.g726').read_bytes())
    from g726.verify_z80 import verify
    rows = []
    for opt, (codec, native, _) in enumerate(variants):
        started = time.perf_counter()
        # All four versions use exactly the same complete prefix and chunk size.
        report = verify(native, codes[:8192], codec, chunk=2048, audit_count=32)
        report['host_execution_seconds'] = time.perf_counter()-started
        save(out/f'opt{opt}/speech-prefix.json', report)
        rows.append(dict(opt=opt, **{k:report[k] for k in (
            'average_tstates_per_sample', 'maximum_sustainable_pcm_hz',
            'code_and_constants_bytes', 'state_bytes', 'stack_bytes')}))
        print(f"opt{opt}: {report['average_tstates_per_sample']:.3f} T/sample", flush=True)
    # Complete selected recording, not only a favorable timing window.
    selected = verify(variants[3][1], codes, variants[3][0], chunk=2048, audit_count=32)
    save(out/'native-full.json', selected)
    # A separate arbitrary-code stream visits extremes unreachable in this speech.
    micro = np.concatenate([unpack(bytes(range(256))),
        *(np.full(1024, i, dtype='u1') for i in range(4)),
        np.random.default_rng(727).integers(0, 4, 3072, dtype='u1')])
    save(out/'native-edge-cases.json', verify(variants[3][1], micro, variants[3][0],
         chunk=1024, audit_count=64))
    for i, row in enumerate(rows):
        baseline = rows[0]['average_tstates_per_sample']
        previous = rows[max(0, i-1)]['average_tstates_per_sample']
        row['delta_from_baseline_tstates_per_sample'] = row['average_tstates_per_sample']-baseline
        row['delta_from_previous_tstates_per_sample'] = row['average_tstates_per_sample']-previous
    save(out/'summary.json', dict(audition=audition, optimization_rounds=rows,
        full_selected_average_tstates_per_sample=selected['average_tstates_per_sample'],
        full_selected_cpu_seconds=selected['total_seconds_at_spectrum128'],
        live_budget_tstates=selected['live_8000_hz_budget_tstates'],
        slowdown_without_pdm=selected['average_tstates_per_sample']/selected['live_8000_hz_budget_tstates'],
        no_new_trd=True, decision='Exact executable codec retained as research; this Z80 port fails live and preload time budgets.'))
    print('Complete codec, native timing, memory/state and instruction checks passed; live timing failed.', flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--sdcc', type=Path, required=True)
    parser.add_argument('--reuse', action='store_true', help='Reuse explicitly supplied compiled snapshots')
    run(parser.parse_args())
