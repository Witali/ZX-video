"""Measure selective old-frame cache fills without changing video/AY bytes.

Experimental SC08/SC32/SC04 containers retain the FSA2 header and insert a packed
96-row source coverage map AFTER each frame's six AY records. SC08 has four
bits per row (48 bytes/frame); SC32 one bit per row (12 bytes/frame);
SC04 one bit per four rows (3 bytes/frame). This
storage/causal-cache probe has no Z80 implementation or playback claim.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from cell_audio_stream import take_tick
from probe_lossless_layouts import sha, measure
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, OFFSETS
from raw_attribute_stream import read_packet


def coverage(vectors, chunk_bytes=8):
    if len(vectors) != 192 or chunk_bytes not in (8, 32):
        raise ValueError('wrong vector count or chunk size')
    flags = np.zeros((96, 32//chunk_bytes), dtype=np.uint8)
    for tile, v in enumerate(vectors):
        if not 1 <= v <= 80:
            continue
        ty, tx = divmod(tile, 16)
        dx, dy = OFFSETS[v]
        first = tx*2+(-dx//4)
        width = 3 if dx % 4 else 2
        for y in range(max(0, ty*8-dy), min(96, ty*8+8-dy)):
            for x in range(max(0, first), min(32, first+width)):
                flags[y, x//chunk_bytes] = 1
    return flags


def verify_cache(previous, vectors, flags, chunk_bytes):
    # Dirty all slots initially so missing fills cannot be masked by zero RAM.
    cache = bytearray(b'\xa5'*1024)
    for row in range(16):
        cache[row*64] = 0
        cache[row*64+33:row*64+64] = bytes(31)

    def fill(first, last):
        for y in range(first, last):
            target = (y % 16)*64+1
            if not 0 <= y < 96:
                cache[target:target+32] = bytes(32)
                continue
            for part in range(32//chunk_bytes):
                if flags[y, part]:
                    offset = part*chunk_bytes
                    cache[target+offset:target+offset+chunk_bytes] = previous[y*32+offset:y*32+offset+chunk_bytes]

    fill(-4, 12)
    reads = 0
    for stripe in range(12):
        if stripe:
            fill(stripe*8+4, stripe*8+12)
        for col in range(16):
            v = vectors[stripe*16+col]
            if not 1 <= v <= 80:
                continue
            dx, dy = OFFSETS[v]
            first = col*2+(-dx//4)
            for y in range(stripe*8-dy, stripe*8+8-dy):
                for x in range(first, first+(3 if dx % 4 else 2)):
                    expected = previous[y*32+x] if 0 <= y < 96 and 0 <= x < 32 else 0
                    if cache[(y % 16)*64+1+x] != expected:
                        raise AssertionError('selective cache differs from previous picture')
                    reads += 1
    return reads


def magic(chunk_bytes, group_rows):
    if (chunk_bytes, group_rows) not in ((8, 1), (32, 1), (32, 4)):
        raise ValueError('unsupported coverage granularity')
    return b'SC04' if group_rows == 4 else b'SC08' if chunk_bytes == 8 else b'SC32'


def pack(source, states, chunk_bytes, group_rows=1):
    r = Reader(source)
    _, _, count, _, _ = read_header(r, magic=b'FSA2')
    if states.shape != (count, 3840):
        raise ValueError('different source frame count')
    result = bytearray(magic(chunk_bytes, group_rows)+source[4:r.pos])
    previous, rows = bytes(3840), []
    for index, state in enumerate(states):
        for _ in range(6):
            result += take_tick(r)
        start = r.pos
        group, _ = read_packet(r, count-index)
        flags = coverage(group[3], chunk_bytes)
        grouped = np.any(flags.reshape(96//group_rows, group_rows, -1), axis=1).astype(np.uint8)
        flags = np.repeat(grouped, group_rows, axis=0)
        if bool(flags.any()) != bool(group[1] & 128):
            raise AssertionError('cache enable bit differs')
        reads = verify_cache(previous, group[3], flags, chunk_bytes)
        packed = np.packbits(grouped).tobytes()
        result += packed+source[start:r.pos]
        rows.append(dict(index=index, cache_enabled=bool(group[1] & 128),
            source_rows=int(np.any(flags, axis=1).sum()), copied_chunks=int(flags.sum()),
            old_bytes_required=int(flags.sum())*chunk_bytes, verified_source_reads=reads))
        previous = state.tobytes()
    r.end()
    return bytes(result), rows


def unpack(data, chunk_bytes, group_rows=1):
    r = Reader(data)
    _, _, count, _, _ = read_header(r, magic=magic(chunk_bytes, group_rows))
    output = bytearray(b'FSA2'+data[4:r.pos])
    for index in range(count):
        for _ in range(6):
            output += take_tick(r)
        packed = r.take(96//group_rows*(32//chunk_bytes)//8)
        start = r.pos
        group, _ = read_packet(r, count-index)
        # Independent scalar verification of every required original pixel;
        # harmless overfetch is allowed, missing coverage is rejected.
        for tile, v in enumerate(group[3]):
            if not 1 <= v <= 80:
                continue
            dx, dy = OFFSETS[v]; ty, tx = divmod(tile, 16)
            for y in range(ty*8-dy, ty*8+8-dy):
                for x in range(tx*8-dx, tx*8+8-dx):
                    if 0 <= y < 96 and 0 <= x < 128:
                        bit = (y//group_rows)*(32//chunk_bytes)+x//(4*chunk_bytes)
                        if not packed[bit//8] & (128 >> (bit % 8)):
                            raise AssertionError('missing required cache pixel')
        output += data[start:r.pos]
    r.end()
    return bytes(output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stream', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--chunk-bytes', type=int, choices=(8, 32), required=True)
    p.add_argument('--group-rows', type=int, choices=(1, 4), default=1)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    source = args.stream.read_bytes()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    data, rows = pack(source, states, args.chunk_bytes, args.group_rows)
    if unpack(data, args.chunk_bytes, args.group_rows) != source:
        raise AssertionError('original video/AY bytes changed')
    active = sum(r['cache_enabled'] for r in rows)
    baseline = 3072*active
    copied = sum(r['old_bytes_required'] for r in rows)
    report = dict(scope=__doc__, complete=True, baseline_commit='1ebb4ec',
        source_sha256=sha(source), states_sha256=sha(states.tobytes()), stream_sha256=sha(data),
        chunk_bytes=args.chunk_bytes, group_rows=args.group_rows,
        raw_bytes=len(data), added_raw_bytes=len(data)-len(source),
        deflate_8192_bytes=measure(data, 8192), frames=rows,
        summary=dict(frames=len(rows), active_frames=active,
            baseline_old_bytes_copied=baseline, old_bytes_copied=copied,
            old_bytes_saved=baseline-copied, needed_rows_per_active_frame=sum(r['source_rows'] for r in rows)/active,
            needed_chunks_per_active_frame=copied/args.chunk_bytes/active,
            source_reads_verified=sum(r['verified_source_reads'] for r in rows)),
        original_fsa2_roundtrip=True, causal_rolling_cache_verified=True,
        cpu_measured=False, zx0_measured=False, release=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frames'}, indent=2))


if __name__ == '__main__':
    main()
