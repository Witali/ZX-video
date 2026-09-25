"""Audit unchanged FAP3/ZX0 disks and assembled decoder code for a speed plan.

Static token/packet counts and existing measured Huffman symbol counts only.
Copy savings are an optimistic analytical bound, not new Z80/Fuse timings.
No player, stream, image, audio or release artifact is modified.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import player_harness, sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
import bank_local_zx0
import prefix_huffman_z80
from zx0_speed import parse


def token_stats(tokens):
    result = {}
    for name, subset in (('literal', [t for t in tokens if not t.offset]),
                         ('match', [t for t in tokens if t.offset])):
        lengths = Counter(t.length for t in subset)
        # The existing queue's 32-LDI loop: entry 48, loop tail 18/group.
        # Optimistic free selection: unchanged LDIR for all unprofitable runs.
        # Dispatch, registers/AF, placement, IRQ and boundary work excluded.
        result[name] = dict(tokens=len(subset), bytes=sum(t.length for t in subset),
            lengths=dict(sorted(lengths.items())),
            ldir_copy_only_tstates=sum((21*n-5)*count for n, count in lengths.items()),
            optimistic_copy_saving_tstates=sum(max(0, 5*n-53-18*((n+31)//32))*count
                                              for n, count in lengths.items()),
            tokens_below_16=sum(count for n, count in lengths.items() if n < 16),
            tokens_at_least_16=sum(count for n, count in lengths.items() if n >= 16),
            bytes_at_least_16=sum(n*count for n, count in lengths.items() if n >= 16))
    return result


def save_listing(path, frame, zxcode, zxlabels):
    rows = sorted((r for r in frame.instructions.values() if r['phase'] == 'reconstruct'),
                  key=lambda r: r['address'])
    lines = ['; Assembled reconstruction: actual bytes + generator instruction/timing table.',
             '; This is an assembler listing, not an independent disassembler.',
             '; T values are uncontended instruction timings; list means branch alternatives.']
    labels = {}
    for name, address in frame.recon.items():
        labels.setdefault(address, []).append(name)
    for index, row in enumerate(rows):
        address = row['address']
        stop = rows[index+1]['address'] if index+1 < len(rows) else frame.recon['state']
        if not 1 <= stop-address <= 4:
            # Recon helpers can end in a separate fixed-RAM region before
            # the main primitive. Do not print intervening padding as code.
            tail_length = {0xc3: 3, 0xc9: 1, 0xc8: 1, 0xd0: 1, 0xd8: 1, 0x76: 1, 0xe9: 1}
            if frame.cpu.read8(address) not in tail_length:
                raise AssertionError(('unexpected instruction span', address, stop))
            stop = address+tail_length[frame.cpu.read8(address)]
        lines.extend(name+':' for name in labels.get(address, []))
        blob = bytes(frame.cpu.read8(i) for i in range(address, stop))
        lines.append(f'{address:04X}  {blob.hex(" ").upper():11}  {row["instruction"]:34} ; {row["tstates"]} T')
    lines += ['', '; ZX0 exact symbol/byte map (includes state and self-modifying operands).',
              '; See incremental_zx0.py and zx0_codec.py for instruction expansion.']
    names = {}
    for name, address in zxlabels.items():
        names.setdefault(address, []).append(name)
    addresses = sorted(set(names) | {bank_local_zx0.CODE, bank_local_zx0.CODE+len(zxcode)})
    for first, last in zip(addresses, addresses[1:]):
        lines.append('/'.join(names.get(first, []))+':')
        for at in range(first, last, 16):
            blob = zxcode[at-bank_local_zx0.CODE:min(last, at+16)-bank_local_zx0.CODE]
            lines.append(f'{at:04X}  db '+blob.hex(' ').upper())
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    return dict(file=path.name, sha256=sha(path.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--raw-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('toolkit/decode_speed_audit.json'))
    parser.add_argument('--listings', type=Path, default=Path('toolkit/decode_speed_listings'))
    args = parser.parse_args()
    args.listings.mkdir(parents=True, exist_ok=True)
    symbol_path = Path(__file__).with_name('carry_huffman_symbols.json')
    symbols = json.loads(symbol_path.read_bytes())
    if not symbols['complete'] or symbols['source_streams_changed']:
        raise ValueError('need complete unchanged Huffman symbol evidence')
    result = dict(scope=__doc__, complete=False, release=False, player_changed=False,
                  new_cpu_execution=False, new_fuse_execution=False,
                  source_sha256=sha(Path(__file__).read_bytes()),
                  symbol_report_sha256=sha(symbol_path.read_bytes()), volumes=[])
    for part in (1, 2, 3):
        meta, stream, blocks = disk_blocks(args.directory, part)
        source = (args.raw_directory/f'volume-{part}.raw').read_bytes()
        if sha(source) != meta['raw_sha256']:
            raise ValueError('different volume source')
        _, _, _, mapping, tables = read_header(Reader(source), magic=b'FAP3')
        symbol = symbols['volumes'][part-1]
        if (symbol['raw_sha256'] != sha(source) or symbol['start'] != meta['frame_start']
                or symbol['end'] != meta['frame_end_exclusive']):
            raise ValueError('symbol evidence has different input range')
        all_tokens = []
        for compressed, raw in blocks:
            decoded, tokens = parse(compressed)
            if decoded != raw:
                raise AssertionError('token parser differs from reference decompressor')
            all_tokens.extend(tokens)
        raw = b''.join(raw for _, raw in blocks)
        reader, modes, totals, payloads = Reader(raw), Counter(), Counter(), []
        for _ in range(meta['frames']):
            _, detail = read_packet(reader, stored_guards=False)
            ay_bytes = sum(map(len, detail['ticks']))
            offset = ay_bytes+5+3
            modes.update(detail['payload'][offset:offset+192])
            totals.update(dict(length=2, ay=ay_bytes, flags_and_lengths=5,
                cache_map=3, vectors=192, masks=detail['mask_bytes'], native_map=80,
                huffman=detail['coded_bytes'], literals=detail['literal_bytes']))
            payloads.append(len(detail['payload']))
        reader.end()
        if sum(totals.values()) != len(raw) or max(modes) > 88:
            raise AssertionError('packet accounting differs')
        options = {key: meta[key] for key in ('inline_matches', 'fast_noop_scan', 'irq_safe_paging',
            'static_cache_borders', 'carry_huffman', 'register_fragments')}
        h = player_harness(bytes(4), tables, mapping, meta['frames'], **options)
        layout = prefix_huffman_z80.prepare(tables, mapping, carry_huffman=True)
        root = layout['regions'][0][1]
        long_prefixes = [sum(n == 0 for n in root[i*512+256:(i+1)*512]) for i in range(len(tables))]
        code, labels = bank_local_zx0.build(dynamic_input=True)
        # These are the actual fast-copy opcodes after the boundary checks.
        for name in ('slice_copy_fast', 'match_copy_fast'):
            at = labels[name]-bank_local_zx0.CODE
            if code[at:at+3] != bytes.fromhex('08 ed b0'):
                raise AssertionError('ZX0 no longer uses EX AF,AF\' / LDIR')
        literal_call = labels['dzx0t_literals_skip']+3
        at = literal_call-bank_local_zx0.CODE
        if code[at:at+3] != b'\xcd'+labels['slice_copy'].to_bytes(2, 'little'):
            raise AssertionError('literal copy no longer calls the bounded helper')
        huffcode, hufflabels, _, _ = prefix_huffman_z80.build(tables, mapping, carry_huffman=True)
        primitive = huffcode[:hufflabels['primitive_end']-prefix_huffman_z80.CODE]
        if h.frame.recon_code[:len(primitive)] != primitive:
            raise AssertionError('player Huffman differs from audited primitive')
        rows = list(h.frame.instructions.values())
        calls = [r['address'] for r in rows if r['phase'] == 'reconstruct'
                 and h.frame.cpu.read8(r['address']) == 0xcd
                 and (h.frame.cpu.read8(r['address']+1) | h.frame.cpu.read8(r['address']+2) << 8)
                 in (hufflabels['bitmap'], hufflabels['attribute'])]
        volume = dict(part=part, frames=meta['frames'], blocks=len(blocks),
            frame_start=meta['frame_start'], stream_sha256=sha(stream), stream_bytes=len(stream),
            packet_sha256=sha(raw), packet_bytes=len(raw), source_sha256=sha(source),
            packet_components=dict(totals), payload_min=min(payloads), payload_max=max(payloads),
            vector_modes=dict(sorted(modes.items())), zx0_tokens=token_stats(all_tokens),
            huffman=dict(contexts=len(tables), max_code_bits=layout['depth'],
                table_body_bytes=layout['body_bytes'], unused_before_shift_pages=12288-layout['body_bytes'],
                long_root_prefixes=long_prefixes,
                secondary_4bit_table_bytes_excluding_directory=32*sum(long_prefixes),
                values=symbol['values'], short_values=symbol['one_byte']+symbol['short_fallback'],
                long_values=symbol['long_fallback'], measured_primitive_tstates=symbol['tstates'],
                cached_current_byte_estimate=dict(short_no_cross=symbol['one_byte'],
                    short_cross=symbol['short_fallback'], long=symbol['long_fallback'],
                    initializations=meta['frames'],
                    delta_tstates=-15*symbol['one_byte']+4*(symbol['short_fallback']+symbol['long_fallback'])+19*meta['frames'],
                    measured=False, assumes_B_survives_callers_and_IRQ=True),
                theoretical_call_ret_saving_ceiling=27*symbol['values']),
            generated=dict(options=options, reconstruction_bytes=len(h.frame.recon_code),
                reconstruction_end=h.frame.recon['end'], free_before_renderer=0x9000-h.frame.recon['end'],
                reconstruction_sha256=sha(h.frame.recon_code), huffman_primitive_bytes=len(primitive),
                huffman_primitive_sha256=sha(primitive), huffman_call_sites=calls,
                zx0_bytes=len(code), zx0_end=labels['end'], zx0_sha256=sha(code),
                zx0_literal_copy_call=literal_call,
                free_before_producer=0x7d50-labels['end'],
                listing=save_listing(args.listings/f'part{part:02}.txt', h.frame, code, labels)))
        result['volumes'].append(volume)
    result['complete'] = True
    result['totals'] = {name: sum(v[name] for v in result['volumes'])
                        for name in ('frames', 'blocks', 'stream_bytes', 'packet_bytes')}
    for name in ('values', 'short_values', 'long_values', 'measured_primitive_tstates',
                 'theoretical_call_ret_saving_ceiling'):
        result['totals']['huffman_'+name] = sum(v['huffman'][name] for v in result['volumes'])
    result['totals']['optimistic_zx0_copy_saving_tstates'] = sum(
        v['zx0_tokens'][kind]['optimistic_copy_saving_tstates']
        for v in result['volumes'] for kind in ('literal', 'match'))
    result['totals']['zx0_literal_runs'] = sum(v['zx0_tokens']['literal']['tokens'] for v in result['volumes'])
    result['totals']['inline_literal_call_ret_only_saving_tstates'] = 27*result['totals']['zx0_literal_runs']
    result['totals']['cached_huffman_byte_estimate_delta_tstates'] = sum(
        v['huffman']['cached_current_byte_estimate']['delta_tstates'] for v in result['volumes'])
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result['totals'], indent=2))


if __name__ == '__main__':
    main()
