"""Measure larger overlap-safe ZX0 reservoirs on complete resident-video streams.

All original independently bootable volumes are decoded and compared. This
host/storage probe does not install a new decoder, producer or scheduler.
Conditional disk estimates hold the old bootstrap and video start fixed.
"""
import argparse
import bisect
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from disk_layout import required_sectors
from inplace_zx0 import trace, layout, OverlapError
from zx0_codec import decompress

ROOT = Path(__file__).parent


def packet_ends(raw, count):
    ends = []; at = 0
    while at < len(raw):
        if at+2>len(raw): raise ValueError('truncated packet size')
        size = int.from_bytes(raw[at:at+2], 'little')
        if not 288<=size<=4702 or at+2+size>len(raw): raise ValueError('invalid video packet')
        at += 2+size; ends.append(at)
    if len(ends)!=count: raise ValueError('frame count differs')
    return ends


def archive(path, raw):
    packed = gzip.compress(raw, mtime=0)
    if path.exists() and path.read_bytes()!=packed: raise ValueError(('archive already differs', path.name))
    path.write_bytes(packed)
    return dict(file=path.name, sha256=sha(packed), decoded_sha256=sha(raw),
                decoded_bytes=len(raw), packed_bytes=len(packed))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'zx0', 'cache', 'evidence', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--block-bytes', type=int, nargs='+', default=[8192, 12288, 15872, 16384])
    p.add_argument('--jobs', type=int, choices=range(1, 5), default=4)
    a = p.parse_args()
    if len(set(a.block_bytes))!=len(a.block_bytes) or any(not 1<=n<=16384 for n in a.block_bytes):
        p.error('block sizes must be unique and inside a 16-KiB bank')
    a.cache.mkdir(parents=True, exist_ok=True); a.evidence.mkdir(parents=True, exist_ok=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = []; memo = {}
    for part in (1, 2, 3):
        m, stream, blocks = disk_blocks(a.directory, part)
        if not m['resident_audio']['enabled'] or not m['independently_bootable']:
            raise ValueError('requires independent resident-AY baseline')
        if m.get('half_row_cache'): raise ValueError('use the smaller resident baseline')
        raw = b''.join(decoded for _, decoded in blocks)
        for payload, decoded in blocks: memo[sha(decoded)] = payload
        inputs.append((m, raw, packet_ends(raw, m['frames'])))
    report = dict(complete=False, release=False, scope=__doc__, baseline_variant_commit='da369e6',
        encoder_sha256=sha(a.zx0.read_bytes()), encoder_mode='optimal ZX0 v2', bank_bytes=16384,
        video_banks=[0, 1, 3], old_ready_bytes=24576, unchanged_fixed_carry_bytes=256,
        player_changed=False, player_instruction_delta_tstates=0, cadence_verified=False,
        sources=[], variants=[], archives=[])
    for m, raw, ends in inputs:
        report['sources'].append(dict(part=m['part'], frames=m['frames'], frame_start=m['frame_start'],
            frame_end_exclusive=m['frame_end_exclusive'], raw_video_sha256=sha(raw), raw_video_bytes=len(raw),
            trd_sha256=m['trd_sha256'], video_bytes=m['video_bytes'], video_sectors=m['video_sectors'],
            video_physical_sectors=m['video_physical_sectors'], used_sectors=m['used_sectors'],
            video_start_sector=m['video_start_sector'], resident_audio_bytes=m['resident_audio']['compiled']['image_bytes']))

    def save(): a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    def compress(raw):
        key = sha(raw); cached = a.cache/(key+'.zx0')
        if key in memo: payload = memo[key]
        elif cached.exists(): payload = cached.read_bytes()
        else:
            with tempfile.TemporaryDirectory(dir=a.cache) as temporary:
                source, target = Path(temporary)/'input.raw', Path(temporary)/'output.zx0'
                source.write_bytes(raw)
                subprocess.run([str(a.zx0.resolve()), '-f', str(source.resolve()), str(target.resolve())],
                               check=True, capture_output=True)
                payload = target.read_bytes()
            with tempfile.NamedTemporaryFile(dir=a.cache, delete=False) as handle:
                handle.write(payload); temporary = handle.name
            os.replace(temporary, cached)
        if decompress(payload, limit=len(raw))!=raw: raise AssertionError('independent roundtrip differs')
        decoded, detail = trace(payload, limit=len(raw))
        if decoded!=raw: raise AssertionError('traced roundtrip differs')
        return payload, detail

    try:
        for size in a.block_bytes:
            variant = dict(block_bytes=size, nominal_ready_bytes=3*size, volumes=[])
            report['variants'].append(variant)
            for m, raw, ends in inputs:
                row = dict(part=m['part'], frames=m['frames'], blocks=[])
                variant['volumes'].append(row)
                chunks = [raw[i:i+size] for i in range(0, len(raw), size)]
                stream = bytearray(); reconstructed = bytearray()
                with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                    for index, (payload, detail) in enumerate(pool.map(compress, chunks)):
                        chunk = chunks[index]; plan = layout(len(payload), len(chunk), detail['minimum_input_start'], len(stream))
                        replayed = False
                        if plan['sector_aligned_fits']:
                            shared, repeated = trace(payload, limit=len(chunk), input_start=plan['input_start'])
                            if (shared!=chunk or repeated['write_input_cursors_sha256']!=detail['write_input_cursors_sha256']):
                                raise AssertionError('shared-memory replay differs')
                            replayed = True
                        elif plan['sector_span_bytes']<=16384:
                            try: trace(payload, limit=len(chunk), input_start=plan['input_start'])
                            except OverlapError: pass
                            else: raise AssertionError('unsafe layout was not rejected')
                        row['blocks'].append(dict(index=index, raw_start=index*size, raw_end=index*size+len(chunk),
                            stream_offset=len(stream), raw_sha256=sha(chunk), payload_sha256=sha(payload),
                            trace=detail, layout=plan, shared_memory_replay_exact=replayed))
                        stream += struct.pack('<HH', len(chunk), len(payload))+payload
                        reconstructed += decompress(payload, limit=len(chunk))
                        if index%25==0:
                            save(); print(f'{size} bytes: disk {m["part"]}, block {index+1}/{len(chunks)} exact', flush=True)
                if reconstructed!=raw: raise AssertionError('whole video changed')
                ns = (len(stream)+255)//256
                physical = required_sectors(ns, m['video_start_sector']%16)
                used = m['used_sectors']+physical-m['video_physical_sectors']
                starts = [0]+ends[:-1]
                coverage = [max(0, bisect.bisect_right(ends, min(len(raw), (i+3)*size))
                    -bisect.bisect_left(starts, i*size)) for i in range(max(1, len(chunks)-2))]
                row.update(complete=True, stream_bytes=len(stream), stream_sha256=sha(stream), video_sectors=ns,
                    video_sector_delta=ns-m['video_sectors'], video_physical_sectors=physical,
                    used_sectors_if_bootstrap_unchanged=used, free_sectors_if_bootstrap_unchanged=2544-used,
                    unsafe_sector_layout_blocks=sum(not b['layout']['sector_aligned_fits'] for b in row['blocks']),
                    unsafe_exact_end_blocks=sum(not b['layout']['exact_end_fits'] for b in row['blocks']),
                    minimum_sector_slack=min(b['layout']['slack_bytes'] for b in row['blocks']),
                    maximum_footprint=max(b['trace']['minimum_footprint'] for b in row['blocks']),
                    shared_tail_copy_bytes=sum(b['layout']['carry_copy_bytes'] for b in row['blocks']),
                    initial_prefill_complete_frames=bisect.bisect_right(ends, min(len(raw), 3*size)),
                    minimum_complete_frames_in_three_slots=min(coverage),
                    whole_video_exact=True, independently_partitioned=True)
                report['archives'].append(archive(a.evidence/f'block{size}-part{m["part"]:02}.stream.gz', bytes(stream)))
                save()
            variant.update(complete=True, stream_bytes=sum(v['stream_bytes'] for v in variant['volumes']),
                video_sectors=sum(v['video_sectors'] for v in variant['volumes']),
                all_sector_layouts_safe=all(v['unsafe_sector_layout_blocks']==0 for v in variant['volumes']))
            print(json.dumps({k:v for k,v in variant.items() if k!='volumes'}), flush=True)
        report['complete'] = True
    except Exception as exc:
        report['failure'] = repr(exc); raise
    finally:
        report['source_sha256_lf'] = {n:sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('probe_inplace_zx0.py', 'inplace_zx0.py', 'test_inplace_zx0.py', 'zx0_codec.py',
             'benchmark_bank_local_zx0.py', 'disk_layout.py')}
        save()


if __name__ == '__main__': main()
