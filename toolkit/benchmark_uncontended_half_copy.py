"""Full compact/native CPU comparison of the uncontended half-row body.

Every original frame is checked; parser/ZX0/AY/IRQ/ULA/disk delivery are not
part of this host-fed frame-stage fixture. Per-frame cache deltas are checked
against independent instruction formulas, not inferred from wall time.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from benchmark_static_cache_borders import OPTIONS
from build_fap3_trd import sha
from bulk_frame_stream import unpack as unpack_bulk, read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import Harness, frames, serialized_masks, display_screen
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from profile_frame_hotspots import install_hl_masks
import cached_huffman_lookahead as lookahead
import compact_cursor
import half_row_cache as half
import inline_huffman_patches as inline
import uncontended_frame as relocation
import uncontended_half_copy as fast

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('raw-directory', 'states', 'output'): p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--limit', type=int)
    a = p.parse_args()
    baseline_path = ROOT/'half_row_cache_cpu.json'
    baseline = json.loads(baseline_path.read_bytes())
    if not baseline['complete'] or not baseline['full_compact_and_both_native_exact']:
        raise ValueError('incomplete baseline')
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if len(states) != 4221 or sha(states.tobytes()) != baseline['states_sha256']:
        raise ValueError('different states')
    result = dict(complete=False, release=False, scope=__doc__, baseline_commit='0c674b6',
        reference_sha256=sha(baseline_path.read_bytes()), states_sha256=sha(states.tobytes()), volumes=[])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save(): a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    try:
        for volume in baseline['volumes']:
            part, start, end = (volume[k] for k in ('part', 'start', 'end'))
            raw = (a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != volume['raw_sha256']: raise ValueError('raw input changed')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)), 32, 4))[0]
            tables, mapping, packets = frames(cells); masks = serialized_masks(cells)
            reader = Reader(raw); _, _, count, _, _ = read_header(reader, magic=b'FAP3')
            details = [read_packet(reader, stored_guards=False)[1] for _ in range(count)]; reader.end()
            h = Harness(tables, mapping, static_cache_borders=True, carry_huffman=True,
                register_fragments=True, cached_huffman_byte=True, metadata_mode='compiled', **OPTIONS)
            install_hl_masks(h); c = h.cpu; c.guarding = False
            if start: c.banks[5][0x2400:0x3300] = states[start-1].tobytes()
            for bank, index in ((7, start-2), (5, start-1)):
                if index >= 0:
                    screen = display_screen(states[index].tobytes(), black_borders=True)
                    screen = bytes(6144)+screen[6144:]
                    c.banks[bank][:6912] = screen; h.expected_screens[bank] = screen
            relocation.install_stage(h); lookahead.install_frame(h)
            inline.install_stage(h, tables, mapping); compact_cursor.install_stage(h)
            half.install_stage(h)
            implementation = fast.install_stage(h)
            row = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                       implementation=implementation, frames=[])
            result['volumes'].append(row)
            for index in range(start, min(end, start+a.limit) if a.limit else end):
                local = index-start; group, native = packets[index]
                if start and local < 2: native = b'\xff'*80
                cache = half.map_for(group[3], details[index]['cache'])
                pairs = np.unpackbits(np.frombuffer(cache, dtype=np.uint8)).reshape(24, 2)
                whole = pairs.any(axis=1)
                actual = relocation.run_stage(h, group, native, states[index].tobytes(), local,
                                              masks[index], cache)
                before = volume['frames'][local]['tstates']; after = actual['total_tstates']
                old = half.copy_tstates(pairs) if group[1]&128 else 0
                new = fast.copy_tstates(pairs) if group[1]&128 else 0
                if after-before != new-old:
                    raise AssertionError(('whole-frame CPU delta differs', part, index, before, after, old, new))
                row['frames'].append(dict(frame=index, baseline_tstates=before, tstates=after,
                    delta_tstates=after-before, old_copy_tstates=old, copy_tstates=new))
                if local%100 == 0:
                    save(); print(f'Part {part}: {local+1}/{end-start} full compact/screens exact', flush=True)
            row['checked_frames'] = len(row['frames'])
            for key in ('baseline_tstates', 'tstates', 'delta_tstates', 'old_copy_tstates', 'copy_tstates'):
                row[key] = sum(f[key] for f in row['frames'])
            save()
        result.update(complete=a.limit is None, full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in result['volumes']),
            parser_extra_tstates=0,
            slower_frames=sum(f['delta_tstates']>0 for v in result['volumes'] for f in v['frames']))
        for key in ('baseline_tstates', 'tstates', 'delta_tstates', 'old_copy_tstates', 'copy_tstates'):
            result[key] = sum(v[key] for v in result['volumes'])
    except Exception as exc:
        result['failure'] = repr(exc); raise
    finally:
        result['source_sha256_lf'] = {n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('benchmark_uncontended_half_copy.py', 'uncontended_half_copy.py', 'test_uncontended_half_copy.py', 'half_row_cache.py',
             'causal_tile_z80.py', 'frame_output_pipeline.py', 'uncontended_frame.py')}
        save()
    print(json.dumps({k: v for k, v in result.items() if k not in ('volumes', 'source_sha256_lf')}), flush=True)


if __name__ == '__main__': main()
