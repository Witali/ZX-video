"""Measure lossless dense-band overdraw opportunities in all archived TRD packets.

The renderer currently uses its dense path only for four FF mask bytes.
OR-ing a constant with their AND can admit nearly full bands: ignored bits
allow writes to unchanged cells, using the already reconstructed exact frame.
With at most two ignored bit positions, every newly accepted band has at
least 24 marked cells. This is a cycle-formula estimate, not executed new Z80.
"""
from collections import Counter
import gzip
import itertools
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from zx0_codec import decompress

ROOT = Path(__file__).parent


def main():
    manifest_path = ROOT / 'streaming_zx0_input_evidence.json'
    manifest = json.loads(manifest_path.read_bytes())
    reference = json.loads((ROOT / 'hl_mask_reader_summary.json').read_bytes())
    choices = [0] + [sum(1 << b for b in bits) for n in (1, 2) for bits in itertools.combinations(range(8), n)]
    volumes = []
    for entry, v in zip(manifest['evidence'], reference['volumes'], strict=True):
        packed = (ROOT / 'streaming_zx0_input_evidence' / entry['file']).read_bytes()
        stream = gzip.decompress(packed)
        if sha(packed) != entry['sha256'] or sha(stream) != v['hl']['stream_sha256']:
            raise ValueError('archived stream differs')
        raw = bytearray()
        pos = 0
        blocks = 0
        while pos < len(stream):
            size, length = struct.unpack_from('<HH', stream, pos)
            pos += 4
            data = decompress(stream[pos:pos + length], limit=size)
            if len(data) != size:
                raise ValueError('block size differs')
            raw += data
            pos += length
            blocks += 1
        if pos != len(stream) or blocks != entry['blocks']:
            raise ValueError('incomplete block input')
        r = Reader(bytes(raw))
        frames = []
        histogram = Counter()
        group_histogram = Counter()
        for index in range(v['hl']['frames']):
            _, packet = read_packet(r, stored_guards=False)
            end = packet['coded_offset']
            native = packet['payload'][end - 80:end]
            if len(native) != 80:
                raise ValueError('bad native map')
            bands = []
            for band in range(1, 19):
                group = native[4 * band:4 * band + 4]
                common = group[0] & group[1] & group[2] & group[3]
                marked = sum(b.bit_count() for b in group)
                if common != 255:
                    group_histogram.update(group)
                histogram[common, marked, band & 1] += 1
                bands.append((common, marked, band & 1))
            frames.append(dict(local_frame=index, bands=bands))
        r.end()
        volumes.append(dict(part=entry['part'], frames=frames, stream_sha256=sha(stream),
            partial_band_group_histogram=dict(sorted(group_histogram.items())),
            band_histogram=[dict(common=c, marked=m, odd=o, count=n) for (c, m, o), n in sorted(histogram.items())]))
    summary = []
    for mask in choices:
        per_volume = []
        for v in volumes:
            rows = []
            for frame in v['frames']:
                delta = 18 * 7 if mask else 0  # Seven T per visible band.
                accepted = 0
                for common, marked, odd in frame['bands']:
                    if common != 255 and common | mask == 255:
                        if marked < 24:
                            raise ValueError('unsafe break-even bound')
                        delta += 5853 + 4 * odd - 261 * marked
                        accepted += 1
                rows.append(dict(delta_tstates=delta, new_dense_bands=accepted))
            per_volume.append(rows)
        rows = [r for group in per_volume for r in group]
        summary.append(dict(mask=mask, delta_tstates=sum(r['delta_tstates'] for r in rows),
            additional_dense_bands=sum(r['new_dense_bands'] for r in rows),
            slower_frames=sum(r['delta_tstates'] > 0 for r in rows),
            max_frame_penalty=max(r['delta_tstates'] for r in rows),
            per_volume_delta=[sum(r['delta_tstates'] for r in group) for group in per_volume]))
    report = dict(complete=True, release=False, scope=__doc__, frames=sum(len(v['frames']) for v in volumes),
        implemented=False, actual_playback_measured=False, cpu_formula_only=True, compressed_stream_delta_bytes=0,
        band_tuple_fields=['common_bits', 'marked_cells', 'band_parity'],
        formula='126 T/frame dispatch + sum(5853 + 4*band_parity - 261*marked_cells) over newly dense bands; mask zero adds no dispatch.',
        excludes=['IRQ', 'ULA', 'disk', 'ROM', 'bootstrap size effects'],
        source_sha256={n: sha((ROOT / n).read_bytes()) for n in ('profile_dense_band_threshold.py',
            'cell_screen_z80.py', 'bulk_frame_stream.py', 'zx0_codec.py', 'hl_mask_reader_summary.json')},
        manifest_sha256=sha(manifest_path.read_bytes()),
        dense_eight_cell_candidate=dict(implemented=False,
            note='Analytical 1919-T helper including a final JP versus 8*(4+17+254+4+4)=2264 T; adds CP FF/JP Z at 17 T for every nonzero partial-band group. Requires an actual assembly/placement/IRQ test.',
            baseline_group_tstates=2264, candidate_helper_tstates=1919,
            predicted_delta_tstates=sum(17*sum(n for b,n in v['partial_band_group_histogram'].items() if b) -
                                       345*v['partial_band_group_histogram'].get(255,0) for v in volumes),
            full_groups=sum(v['partial_band_group_histogram'].get(255,0) for v in volumes),
            nonzero_groups=sum(sum(n for b,n in v['partial_band_group_histogram'].items() if b) for v in volumes)),
        candidates=sorted(summary, key=lambda r: r['delta_tstates']), volumes=volumes)
    (ROOT / 'dense_band_threshold_profile.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report['candidates'][:8], indent=2), flush=True)
    print(json.dumps(report['dense_eight_cell_candidate'], indent=2), flush=True)


if __name__ == '__main__':
    main()
