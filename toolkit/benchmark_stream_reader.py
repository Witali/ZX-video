"""Run complete ZX0 stream consumption, including Z80 block headers/copies.

Requests fixed-size byte chunks, not decoded frames. Host calls take and
provides an ideal raw ring producer; packet parsing, AY, drawing, ULA and
disk scheduling remain excluded. Every decoded byte and ring byte is checked.
"""
import argparse
import json
from pathlib import Path
import struct

from probe_lossless_layouts import sha
from stream_reader_harness import Harness


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw', 'storage-report', 'cache', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--quota', type=int, default=256)
    args = p.parse_args()
    raw = args.raw.read_bytes(); storage = json.loads(args.storage_report.read_text(encoding='utf-8'))
    if not storage['complete'] or storage['input_sha256'] != sha(raw) or not 1 <= args.quota <= 4704:
        raise ValueError('inconsistent storage input or quota')
    ring, pos = bytearray(), 0
    for block in storage['blocks']:
        expected = raw[pos:pos+block['decoded_bytes']]; pos += len(expected)
        payload = (args.cache/(block['sha256']+'.zx0')).read_bytes()
        if sha(expected) != block['sha256'] or len(payload) != block['zx0_bytes']:
            raise ValueError('cached block differs')
        ring += struct.pack('<HH', len(expected), len(payload))+payload
    if pos != len(raw): raise ValueError('incomplete block coverage')
    h = Harness(bytes(ring))
    report = dict(scope=__doc__, complete=False, baseline_commit='a0c73d7', input_sha256=sha(raw),
        ring_bytes=len(ring), quota=args.quota, requests=[], code_regions=[dict(base=b, code_hex=v.hex()) for b,v in h.regions],
        reader_labels=h.r, decoder_labels=h.z, instruction_listing=list(h.instructions.values()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', release=False, disk_delivery_verified=False)
    for index, pos in enumerate(range(0, len(raw), args.quota)):
        expected = raw[pos:pos+args.quota]
        if h.take(len(expected)) != expected: raise AssertionError('decoded stream differs')
        report['requests'].append(dict(index=index, **h.rows[-1]))
        if index % 1000 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Z80 stream reader checked {pos+len(expected)}/{len(raw)} bytes', flush=True)
    if h.cpu.consumed != len(ring) or h.blocks != len(storage['blocks']):
        raise AssertionError('unused compressed input or wrong block count')
    total = sum(r['tstates'] for r in h.rows)
    report['instruction_histogram'] = [dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())]
    if sum(r['tstates']*r['count'] for r in report['instruction_histogram']) != total:
        raise AssertionError('CPU histogram differs')
    report['summary'] = dict(decoded_bytes=len(raw), blocks=h.blocks, requests=len(h.rows), total_tstates=total,
        max_request_tstates=max(r['tstates'] for r in h.rows),
        reader_tstates=sum(r['stages'].get('reader',0) for r in h.rows),
        banked_zx0_tstates=sum(r['stages'].get('banked_zx0',0) for r in h.rows))
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
