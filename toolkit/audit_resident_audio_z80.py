"""Rebuild bank images and audit saved resident-AY instruction counts.

Checks pinned inputs/sources, runtime layout, listings and timing arithmetic.
It does not replay the complete CPU run; use benchmark_resident_audio_z80.py
for that. Harness construction executes the independent initial AY writes.
"""
from collections import Counter
import json
from pathlib import Path

from benchmark_resident_audio_z80 import Harness
from build_fap3_trd import sha
from resident_audio_z80 import tables

ROOT = Path(__file__).parent


def main():
    report = json.loads((ROOT/'resident_audio_z80.json').read_bytes())
    source = json.loads((ROOT/'resident_audio_probe.json').read_bytes())
    if not report['complete'] or report['release']:
        raise ValueError('incomplete or unexpected release report')
    for name in ('source_sha256_lf','reference_sha256'):
        for filename, digest in report[name].items():
            content = (ROOT/filename).read_bytes()
            if name == 'source_sha256_lf': content = content.replace(b'\r\n',b'\n')
            if sha(content) != digest:
                raise ValueError(('source/input changed', filename))
    for saved, row in zip(report['volumes'], source['volumes'], strict=True):
        blob = bytes.fromhex(row['coded_hex'])
        if saved['part'] != row['part'] or sha(blob) != row['coded_sha256']:
            raise ValueError('volume identity differs')
        h = Harness(blob, paging=True)
        built = {k:v for k,v in h.build.items() if k not in ('image_hex','listing')}
        bridge = {k:v for k,v in h.bridge.items() if k not in ('code_hex','listing')}
        if built != saved['build'] or bridge != saved['bridge'] or h.init_tstates != saved['init_tstates']:
            raise ValueError('assembled bank, bridge or initializer differs')
        if (sha(b''.join(h.records)) != saved['raw_sha256'] or saved['raw_sha256'] != row['raw_sha256']
                or saved['records'] != len(h.records) or saved['initial_registers'] != h.initial.hex()):
            raise ValueError('original AY records differ')
        stages, counts = Counter(), Counter()
        for item in saved['dynamic_instruction_counts']:
            pc, ticks, count = item['address'], item['tstates'], item['executions']
            instruction = h.cpu.listing[pc]
            allowed = instruction['tstates']
            if ticks not in (allowed if isinstance(allowed,list) else [allowed]) or count <= 0:
                raise ValueError('invalid instruction count/timing')
            stages[instruction['stage']] += ticks*count
            counts[pc] += count
        expected_listing = [dict(h.cpu.listing[pc],executions=count) for pc,count in sorted(counts.items())]
        if expected_listing != saved['instructions'] or dict(stages) != saved['stage_tstates']:
            raise ValueError('executed instruction listing differs')
        calls, payload = saved['fill_call_tstates'], tables(blob)[3]
        writes = sum(r[0] for r in h.records)
        ones = sum(b.bit_count() for b in payload)
        old = 1705*len(calls)+42*writes
        local = 109*len(calls)+789*len(h.records)+137*writes+71*built['input_bits']+17*ones+32*len(payload)
        wrapper = bridge['overhead_tstates']*len(calls)
        values = dict(fill_calls=len(calls), register_writes=writes, coded_one_bits=ones,
            old_enqueue_tstates=old, bank_local_fill_tstates=local, wrapper_tstates=wrapper,
            fill_tstates=local+wrapper, delta_producer_tstates=local+wrapper-old,
            fill_call_min_tstates=min(calls), fill_call_max_tstates=max(calls))
        if (any(saved[k] != v for k,v in values.items()) or len(calls)*6 != len(h.records)
                or sum(calls) != local+wrapper or sum(stages.values()) != sum(calls)):
            raise ValueError('cycle formula or full-batch coverage differs')
    for name in ('records','fill_tstates','old_enqueue_tstates','delta_producer_tstates'):
        if sum(v[name] for v in report['volumes']) != report[name]:
            raise ValueError(('total differs',name))
    print(json.dumps(dict(scope=__doc__, input_records=report['records'],
        rebuilt_banks=len(report['volumes']), source_hashes_exact=True,
        all_generated_images_and_instruction_counts_match=True,
        minimum_spare_bank_bytes=min(v['build']['spare_bank_bytes'] for v in report['volumes']),
        producer_delta_tstates=report['delta_producer_tstates'], release=False)), flush=True)


if __name__ == '__main__': main()
