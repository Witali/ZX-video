"""Execute old and compiled metadata decoders on every actual volume frame.

Checks all 480 mask bytes, padding, source cursor/data, writes and individual
instruction timings. Only this stage runs; no screen, IRQ, ULA, queue or disk.
"""
import argparse
import json
from pathlib import Path

import compiled_masks_z80 as compiled
import frame_metadata_z80 as old
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from test_compiled_masks_z80 import CompiledMaskTests, INPUT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','raw-directory','output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    result = dict(complete=False, release=False, scope=__doc__, baseline_commit='5b2175f',
                  compressed_stream_delta_bytes=0, volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    try:
        next_frame = 0
        for part in (1,2,3):
            path = args.directory / f'ZX-video-huffman-preview_part{part:02}.json'
            metadata = json.loads(path.read_bytes())
            raw = (args.raw_directory / f'volume-{part}.raw').read_bytes()
            if sha(raw) != metadata['raw_sha256']: raise ValueError('raw hash differs')
            start, end = metadata['frame_start'], metadata['frame_end_exclusive']
            if start != next_frame: raise ValueError('non-contiguous volumes')
            r = Reader(raw); _,_,count,_,_ = read_header(r, magic=b'FAP3')
            h = CompiledMaskTests(); h.setUp()
            initialize_tstates = h.initialize()
            for address, expected in h.expected:
                if h.read(address, len(expected)) != expected: raise AssertionError('generator differs')
            code, labels, rows = old.build()
            h.install(old.CODE, code); h.rows.update({row['address']:row for row in rows})
            volume = dict(part=part, start=start, end=end, raw_sha256=sha(raw),
                          initialize_tstates=initialize_tstates, frames=[])
            result['volumes'].append(volume)
            for index in range(count):
                _, detail = read_packet(r, stored_guards=False)
                if not start <= index < end: continue
                position = sum(map(len, detail['ticks'])) + 8 + 192
                encoded = detail['payload'][position:position + detail['mask_bytes']]
                expected = restore(encoded, 1, 480, 4)
                ticks = []
                for entry, formula in ((labels['decode'], old.expected_tstates),
                                       (h.labels['decode'], compiled.expected_tstates)):
                    h.install(INPUT, encoded)
                    # Poison destinations to detect incomplete writes, even on repeated frames.
                    h.install(old.MASKS, bytes(v ^ 255 for v in expected))
                    h.install(old.FLAGS, bytes([0xa5]*64)); h.cpu.set_hl(INPUT)
                    value = h.run_code(entry, [(old.MASKS, old.MASKS+480), (old.FLAGS, old.FLAGS+64)])
                    if (value != formula(encoded) or h.read(old.MASKS, 480) != expected
                            or h.read(old.FLAGS+60, 4) != bytes(4) or h.cpu.hl() != INPUT+len(encoded)
                            or h.read(INPUT, len(encoded)) != encoded):
                        raise AssertionError(('metadata differs', part, index, entry))
                    ticks.append(value)
                volume['frames'].append(dict(frame=index, encoded_bytes=len(encoded),
                    baseline_tstates=ticks[0], compiled_tstates=ticks[1], delta_tstates=ticks[1]-ticks[0]))
                if len(volume['frames']) % 400 == 0:
                    save(); print(f'Exact old/new masks: part {part}, {index-start+1}/{end-start}', flush=True)
            r.end(); next_frame = end
            volume.update(checked_frames=len(volume['frames']),
                **{key:sum(f[key] for f in volume['frames']) for key in
                   ('baseline_tstates','compiled_tstates','delta_tstates')})
            if volume['checked_frames'] != end-start: raise AssertionError('missing frames')
            save()
        if next_frame != count: raise AssertionError('missing ending')
        result.update(complete=True, checked_frames=next_frame,
            all_mask_bytes_exact=True, source_unchanged=True,
            **{key:sum(v[key] for v in result['volumes']) for key in
               ('baseline_tstates','compiled_tstates','delta_tstates')})
    except Exception as exc:
        result['failure'] = repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in result.items() if k != 'volumes'}), flush=True)


if __name__ == '__main__':
    main()
