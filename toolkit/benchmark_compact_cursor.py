"""Execute compact-cursor replacements across the three exact baseline volumes.

All compact bytes, both complete screens, input/cursor/paging contracts and
per-frame deterministic T-states are checked. Host-supplied packets exclude
ZX0, queue copies, AY/IRQ cadence, ULA, TR-DOS and physical disk latency.
This CPU-stage benchmark does not qualify a playback release.
"""
import argparse
from collections import Counter
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
import compact_cursor
import inline_huffman_patches as inline
import uncontended_frame as relocation

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-directory', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'compact_cursor_cpu.json')
    p.add_argument('--limit', type=int, help='Per-volume smoke only, never complete')
    a = p.parse_args()
    if a.limit is not None and a.limit < 1: p.error('--limit must be positive')
    baseline = ROOT / 'frame_hotspot_profile.json'
    model = json.loads(baseline.read_bytes())
    if not model['complete'] or not model['full_compact_and_both_native_exact']:
        raise ValueError('incomplete baseline')
    for name, expected in model['source_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('baseline source differs',name))
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if len(states) != model['checked_frames'] or sha(states.tobytes()) != model['states_sha256']:
        raise ValueError('different frame states')
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='b3f33fc',
        model_sha256=sha(baseline.read_bytes()), states_sha256=model['states_sha256'],
        source_sha256={name: sha((ROOT/name).read_bytes()) for name in
            ('benchmark_compact_cursor.py','compact_cursor.py','test_compact_cursor.py')},
        baseline_sources=model['source_sha256'], compressed_stream_delta_bytes=0,
        new_playback_measured=False, physical_drive_verified=False, volumes=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)

    def save():
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')

    save()
    try:
        for volume in model['volumes']:
            part, start, end = (volume[k] for k in ('part','start','end'))
            raw = (a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != volume['raw_sha256']: raise ValueError('raw volume differs')
            cells = unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
            tables,mapping,packets = frames(cells)
            masks = serialized_masks(cells)
            reader = Reader(raw)
            _,_,count,_,_ = read_header(reader,magic=b'FAP3')
            details = [read_packet(reader,stored_guards=False)[1] for _ in range(count)]
            reader.end()
            h = Harness(tables,mapping,static_cache_borders=True,carry_huffman=True,
                register_fragments=True,cached_huffman_byte=True,metadata_mode='compiled',**OPTIONS)
            install_hl_masks(h)
            c = h.cpu
            c.guarding = False
            if start: c.banks[5][0x2400:0x3300] = states[start-1].tobytes()
            for bank,index in ((7,start-2),(5,start-1)):
                if index >= 0:
                    screen = display_screen(states[index].tobytes(),black_borders=True)
                    screen = bytes(6144)+screen[6144:]
                    c.banks[bank][:6912] = screen
                    h.expected_screens[bank] = screen
            relocation.install_stage(h)
            inline.install_stage(h,tables,mapping)
            patches = compact_cursor.install_stage(h)
            entry_names = {r['start']: r['name'] for r in patches['patches']}
            saved = dict(part=part,start=start,end=end,raw_sha256=sha(raw),patches=patches,frames=[])
            report['volumes'].append(saved)
            previous = Counter()
            for index in range(start,min(end,start+a.limit) if a.limit else end):
                local = index-start
                group,native = packets[index]
                if start and local < 2: native = b'\xff'*80
                actual = relocation.run_stage(h,group,native,states[index].tobytes(),local,
                                              masks[index],details[index]['cache'])
                cumulative = Counter()
                for (pc,ticks),n in h.histogram.items():
                    if pc in entry_names: cumulative[entry_names[pc]] += n
                counts = cumulative-previous
                previous = cumulative
                before = volume['frames'][local]['tstates']
                after = actual['total_tstates']
                wanted = compact_cursor.delta(counts)
                if after-before != wanted:
                    raise AssertionError(('frame cycle delta differs',part,index,before,after,counts,wanted))
                saved['frames'].append(dict(frame=index,baseline_tstates=before,tstates=after,
                    delta_tstates=wanted,ordinary_tiles=counts['tile'],noop_runs=counts['noop_run']))
                if local % 100 == 0:
                    save()
                    print(f'part {part}: {local+1}/{end-start} exact compact/screens/cursor cycles',flush=True)
            saved['checked_frames'] = len(saved['frames'])
            for key in ('baseline_tstates','tstates','delta_tstates','ordinary_tiles','noop_runs'):
                saved[key] = sum(row[key] for row in saved['frames'])
            if a.limit is None:
                old_counts = Counter()
                for row in volume['instruction_histogram']:
                    if row['bank'] == -1 and row['address'] in entry_names:
                        old_counts[entry_names[row['address']]] += row['count']
                if old_counts != previous: raise AssertionError('cursor call frequencies differ')
            save()
            print(json.dumps({k:v for k,v in saved.items() if k not in ('frames','patches')}),flush=True)
        report.update(complete=a.limit is None,full_compact_and_both_native_exact=True,
            checked_frames=sum(v['checked_frames'] for v in report['volumes']),
            slower_frames=sum(f['delta_tstates']>0 for v in report['volumes'] for f in v['frames']))
        for key in ('baseline_tstates','tstates','delta_tstates','ordinary_tiles','noop_runs'):
            report[key] = sum(v[key] for v in report['volumes'])
    except Exception as exc:
        report['failure'] = repr(exc)
        save()
        raise
    save()
    print(json.dumps({k:report[k] for k in ('complete','checked_frames','baseline_tstates','tstates','delta_tstates')}),flush=True)


if __name__ == '__main__':
    main()
