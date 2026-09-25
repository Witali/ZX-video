"""Execute cached-byte reconstruction and both screens on all independent volumes.

Compare each frame with saved complete CPU counts plus the compiled-mask
delta, and pair the first frames again. Check symbol counts and the exact
cache delta against all real symbols. Host supplies packets; no disk/ULA,
ZX0, IRQ cadence, bootstrap capacity or release claim.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from benchmark_static_cache_borders import OPTIONS
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from build_fap3_trd import sha
from test_cached_huffman_byte import paired_codes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'states', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--model', type=Path, default=Path('toolkit/uncontended_frame_cpu.json'))
    p.add_argument('--metadata-model', type=Path, default=Path('toolkit/compiled_masks_cpu.json'))
    p.add_argument('--symbols', type=Path, default=Path('toolkit/carry_huffman_symbols.json'))
    p.add_argument('--paired', type=int, default=8)
    p.add_argument('--limit', type=int, help='Per-volume smoke limit; never complete')
    p.add_argument('--skip-primitive-cases', action='store_true', help='Smoke only; never complete')
    args = p.parse_args()
    model, masks, symbols = [json.loads(path.read_bytes()) for path in (args.model, args.metadata_model, args.symbols)]
    with np.load(args.states, allow_pickle=False) as f:
        states = f['states']
    if not all(r['complete'] for r in (model, masks, symbols)) or sha(states.tobytes()) != model['states_sha256']:
        raise ValueError('incomplete or different reference')
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='ab76fa1',
        source_sha256=sha(Path(__file__).read_bytes()), states_sha256=sha(states.tobytes()),
        reference_sha256={k:sha(v.read_bytes()) for k,v in
                         dict(cpu=args.model, masks=args.metadata_model, symbols=args.symbols).items()},
        raw_and_compressed_delta_bytes=0, extra_table_bytes=0, extra_stack_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    try:
        for v, mv, sv in zip(model['volumes'], masks['volumes'], symbols['volumes']):
            part, start, end = v['part'], v['start'], v['end']
            if (part,start,end) != (mv['part'],mv['start'],mv['end']) or (start,end) != (sv['start'],sv['end']):
                raise ValueError('different volume bounds')
            raw = (args.directory/f'volume-{part}.raw').read_bytes()
            if any(sha(raw) != row['raw_sha256'] for row in (v, mv, sv)):
                raise ValueError('different entropy input')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)), 32, 4))[0]
            tables, mapping, packets = frames(cells)
            meta = serialized_masks(cells)
            r = Reader(raw); _, _, count, _, _ = read_header(r, magic=b'FAP3')
            details = [read_packet(r, stored_guards=False)[1] for _ in range(count)]; r.end()
            hs = [Harness(tables, mapping, static_cache_borders=True, carry_huffman=True,
                  register_fragments=True, cached_huffman_byte=cached, metadata_mode='compiled', **OPTIONS)
                  for cached in (False, True)]
            for h in hs:
                c = h.cpu; c.guarding = False
                if start:
                    c.banks[5][0x2400:0x3300] = states[start-1].tobytes()
                for bank, i in ((7,start-2), (5,start-1)):
                    if i >= 0:
                        screen = display_screen(states[i].tobytes(), black_borders=True)
                        screen = bytes(6144)+screen[6144:]
                        c.banks[bank][:6912] = screen; h.expected_screens[bank] = screen
            old, h = hs
            volume = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                baseline_code_bytes=len(old.recon_code), code_bytes=len(h.recon_code),
                code_end=h.recon['end'], code_sha256=sha(h.recon_code), labels=h.recon,
                instruction_listing=list(h.instructions.values()),
                primitive_cases=None if args.skip_primitive_cases else paired_codes(tables, mapping), frames=[])
            report['volumes'].append(volume); save()
            print(f'Part {part}: primitive cases complete; executing frames', flush=True)
            previous = (0,0,0)
            for i in range(start, min(end,start+args.limit) if args.limit else end):
                local = i-start; group, native = packets[i]
                if start and local < 2:
                    native = bytes([255])*80
                actual = h.run(group, native, states[i].tobytes(), local,
                               encoded_metadata=meta[i], cache_map=details[i]['cache'])
                before = v['frames'][local]['tstates']+mv['frames'][local]['delta_tstates']
                if local < args.paired:
                    paired = old.run(group, native, states[i].tobytes(), local,
                                     encoded_metadata=meta[i], cache_map=details[i]['cache'])
                    if paired['total_tstates'] != before:
                        raise AssertionError(('saved baseline differs', part, i))
                current = (h.histogram[h.recon['short_position'],7],
                    h.histogram[h.recon['cache_short_refresh'],19],
                    h.histogram[h.recon['cache_long_refresh'],19])
                short, cross, long = [a-b for a,b in zip(current, previous)]; previous = current
                symbol = sv['frames'][local]
                if (symbol['frame'] != i or short-cross != symbol['one_byte']
                        or cross != symbol['short_fallback'] or long != symbol['long_fallback']):
                    raise AssertionError(('different symbol paths', part, i, short, cross, long))
                delta = 19-15*short+19*cross+4*long
                if actual['total_tstates'] != before+delta:
                    raise AssertionError(('different full frame cost', part, i, before, actual, delta))
                volume['frames'].append(dict(frame=i, short_inside=short-cross, short_cross=cross,
                    long=long, baseline_tstates=before, tstates=actual['total_tstates'], delta_tstates=delta))
                if local % 200 == 0:
                    save(); print(f'Exact compact/both screens/cycles: part {part}, {local+1}/{end-start}', flush=True)
            volume['checked_frames'] = len(volume['frames'])
            for key in ('baseline_tstates', 'tstates', 'delta_tstates'):
                volume[key] = sum(row[key] for row in volume['frames'])
            save()
        report.update(complete=not args.limit and not args.skip_primitive_cases,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            full_compact_and_both_native_exact=True,
            slower_frames=sum(f['delta_tstates'] > 0 for v in report['volumes'] for f in v['frames']))
        for key in ('baseline_tstates', 'tstates', 'delta_tstates'):
            report[key] = sum(v[key] for v in report['volumes'])
    except Exception as exc:
        report['failure'] = repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in report.items() if k != 'volumes'}), flush=True)


if __name__ == '__main__':
    main()
