"""Host-only F2L1 experiment: exact two-level masks for FAP3 raw tiles.

An 8x8 logical tile occupies sixteen 2bpp bytes. If it contains exactly
two levels, experimental vector 89 stores a palette byte (low<<2|high)
and eight MSB-first mask bytes. Existing fragment modes remain unchanged.
F2L1 is deliberately NOT accepted by the Z80 player or the TRD builder.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from bulk_frame_stream import read_packet, unpack
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from zx0_codec import decompress

SIZES = {85: 16, 86: 2, 87: 5, 88: 1, 89: 9}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pack_tile(fragment):
    if len(fragment) != 16:
        raise ValueError('expected sixteen 2bpp bytes')
    pixels = [(value >> shift) & 3 for value in fragment for shift in (6, 4, 2, 0)]
    levels = sorted(set(pixels))
    if len(levels) != 2:
        return None
    low, high = levels
    return bytes([low << 2 | high] + [
        sum((pixels[row*8+x] == high) << (7-x) for x in range(8))
        for row in range(8)])


def unpack_tile(encoded):
    if len(encoded) != 9 or encoded[0] >= 16:
        raise ValueError('invalid two-level fragment')
    low, high = encoded[0] >> 2, encoded[0] & 3
    if low >= high:
        raise ValueError('noncanonical palette')
    pixels = [high if mask & (1 << bit) else low
              for mask in encoded[1:] for bit in range(7, -1, -1)]
    return bytes(sum(pixels[i+j] << (6-2*j) for j in range(4))
                 for i in range(0, 64, 4))


def transform(source, *, restore=False):
    r = Reader(source)
    magic, target = (b'F2L1', b'FAP3') if restore else (b'FAP3', b'F2L1')
    _, _, count, _, _ = read_header(r, magic=magic)
    out = bytearray(target + source[4:r.pos])
    modes, palettes, per_frame = Counter(), Counter(), []
    ay = bytearray()
    for _ in range(count):
        _, packet = read_packet(r, stored_guards=False)
        body = packet['payload']
        ticks = b''.join(packet['ticks'])
        ay += ticks
        vector_offset = len(ticks)+5+3
        prefix = bytearray(body[:packet['literal_offset']])
        cursor, literals, changed = packet['literal_offset'], bytearray(), 0
        for tile, mode in enumerate(body[vector_offset:vector_offset+192]):
            if mode > (89 if restore else 88):
                raise ValueError('unknown fragment mode')
            modes[mode] += 1
            if mode <= 84:
                continue
            length = SIZES[mode]
            fragment = body[cursor:cursor+length]
            if len(fragment) != length:
                raise ValueError('truncated fragment')
            cursor += length
            if restore and mode == 89:
                fragment = unpack_tile(fragment)
                prefix[vector_offset+tile] = 85
                changed += 1
            elif not restore and mode == 85:
                packed = pack_tile(fragment)
                if packed is not None:
                    fragment = packed
                    prefix[vector_offset+tile] = 89
                    palettes[f'{packed[0] >> 2},{packed[0] & 3}'] += 1
                    changed += 1
            literals += fragment
        attributes = body[cursor:]
        if len(attributes) != (768 if packet['flags'] & 64 else 0):
            raise ValueError('unexpected literal tail')
        result = prefix+literals+attributes
        if not 294 <= len(result) <= 4703:
            raise ValueError('transformed packet does not fit')
        out += struct.pack('<H', len(result))+result
        per_frame.append(changed)
    r.end()
    return bytes(out), dict(frames=count, ay_records=count*6, ay_sha256=sha(ay),
        input_modes=dict(sorted(modes.items())), palettes=dict(sorted(palettes.items())),
        replaced_tiles=sum(per_frame), frames_with_replacements=sum(n > 0 for n in per_frame),
        max_replacements_per_frame=max(per_frame, default=0))


def compress_chunk(raw, executable, cache, read_cache):
    digest = sha(raw)
    path = cache / (digest+'.zx0')
    cached = next((directory / path.name for directory in (cache, *read_cache)
                   if (directory / path.name).is_file()), None)
    if cached is not None:
        encoded = cached.read_bytes()
    else:
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            source, output = Path(tmp)/'input.raw', Path(tmp)/'output.zx0'
            source.write_bytes(raw)
            subprocess.run([str(executable), '-f', str(source.resolve()), str(output.resolve())],
                           check=True, capture_output=True)
            encoded = output.read_bytes()
        path.write_bytes(encoded)
    if decompress(encoded, limit=len(raw)) != raw:
        raise AssertionError('ZX0 block roundtrip failed')
    return encoded


def measure_zx0(data, executable, cache, block_size, *, read_cache=(), jobs=4):
    cache.mkdir(parents=True, exist_ok=True)
    reader = Reader(data)
    read_header(reader, magic=data[:4])
    header_bytes = reader.pos
    blocks, chunks = [], []
    combined = bytearray()
    start = header_bytes
    while start < len(data):
        # Match Builder.stream: tables belong to startup RAM, and the first
        # block ends at the next absolute file boundary, not header+8192.
        stop = min(len(data), (start//block_size+1)*block_size)
        chunks.append((stop, data[start:stop]))
        start = stop
    # Only one job per digest can write a cache file, even for repeated chunks.
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        pending = {}
        for _, raw in chunks:
            digest = sha(raw)
            if digest not in pending:
                pending[digest] = executor.submit(compress_chunk, raw, executable, cache, read_cache)
        for stop, raw in chunks:
            encoded = pending[sha(raw)].result()
            combined += struct.pack('<HH', len(raw), len(encoded))+encoded
            blocks.append(len(encoded))
            if len(blocks) % 64 == 0:
                print(f'  ZX0 {stop}/{len(data)} bytes', flush=True)
    return dict(file_bytes=len(data), file_sha256=sha(data), excluded_header_bytes=header_bytes,
        raw_packet_bytes=len(data)-header_bytes, block_count=len(blocks),
        zx0_payload_bytes=sum(blocks), block_header_bytes=4*len(blocks),
        stream_bytes=len(combined), stream_sha256=sha(combined),
        rounded_256_byte_sectors=(len(combined)+255)//256,
        all_blocks_roundtrip=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'output', 'report', 'zx0', 'cache'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--label', required=True, help='Input scope saved in report')
    p.add_argument('--block-size', type=int, default=8192, choices=(4096, 8192))
    p.add_argument('--read-cache', type=Path, action='append', default=[],
                   help='Optional existing optimal ZX0 cache; every reused block is decoded and checked')
    p.add_argument('--jobs', type=int, default=4, choices=range(1, 9))
    args = p.parse_args()
    if len({path.resolve() for path in (args.source, args.output, args.report)}) != 3:
        p.error('source, output and report must be different paths')
    source = args.source.read_bytes()
    unpack(source)  # Validate the original format before experimenting.
    candidate, stats = transform(source)
    restored, restored_stats = transform(candidate, restore=True)
    if restored != source or restored_stats['ay_sha256'] != stats['ay_sha256']:
        raise AssertionError('full FAP3/AY stream changed')
    print(json.dumps(stats), flush=True)
    options = dict(read_cache=args.read_cache, jobs=args.jobs)
    baseline = measure_zx0(source, args.zx0.resolve(), args.cache.resolve(), args.block_size, **options)
    alternative = measure_zx0(candidate, args.zx0.resolve(), args.cache.resolve(), args.block_size, **options)
    delta = alternative['stream_bytes']-baseline['stream_bytes']
    report = dict(scope=args.label, date=date.today().isoformat(), baseline_commit='f7b4547',
        experiment='F2L1: exact two-level 8x8 masks replacing raw sixteen-byte fragments only',
        complete_host_probe=True, block_size=args.block_size,
        compressor=dict(command='zx0 -f', jobs=args.jobs, executable_sha256=sha(args.zx0.read_bytes())),
        fragments=stats, baseline=baseline, candidate=alternative,
        raw_delta_bytes=len(candidate)-len(source), zx0_delta_bytes=delta,
        zx0_delta_percent=100*delta/baseline['stream_bytes'],
        exact_fap3_roundtrip=True, exact_ay_records=True, additional_pixel_changes=0,
        z80_decoder_implemented=False, integrated_player_delta_tstates=0,
        candidate_tstates=None, physical_disk_latency_measured=False,
        trd_count_measured=False, release=False,
        limitations='Global block stream only: no bootstrap, per-volume restart, sector interleave, '
                    'new Z80 opcode, RAM layout or playback timing. Existing mode selection is fixed; '
                    'not a bound for every palette codec or a direct H.263 benchmark.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
