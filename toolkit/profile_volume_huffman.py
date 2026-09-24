"""Count isolated prefix-decoder T-states for every original entropy symbol.

Formula is from benchmark_prefix_huffman.py / the Z80 instruction table.
Check the actual decoder opcodes at all eight bit offsets for each used
context/symbol, then sum data-dependent costs for every real frame.
Excluded: wrappers, motion, ZX0, output, IRQ/ULA, ROM and physical disk.
This is not a full-player speed prediction or a release check.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_prefix_huffman import Harness
from probe_motion_entropy import Reader, codes_for
from probe_hybrid_tiles import Writer
from probe_spatial_contexts import read_header
from probe_volume_huffman import collect
from build_fap3_trd import sha


def verify_symbols(tables, mapping, histogram):
    h = Harness(tables, mapping)
    representatives = {context: mapping.index(context) for context in set(mapping)}
    cases = 0
    for context, value in np.argwhere(histogram):
        context, value = int(context), int(value)
        pair = (1, 0) if context == len(tables)-1 else (0, representatives[context])
        code, length = codes_for(255, tables[context])[value]
        for offset in range(8):
            w = Writer()
            if offset: w.put(0, offset)
            w.put(code, length)
            h.begin(w.finish())
            h.cpu.write8(h.labels['bit_page'], 0xf0+offset)
            h.run([pair], bytes([value]))
            cases += 1
    return h.layout, cases


def costs(packets, tables, layout):
    lengths = np.asarray([list(t) for t in tables], np.int32)
    carry = np.zeros_like(lengths)
    for context, indices in enumerate(layout['indices']):
        for value, index in indices.items():
            carry[context,value] = (layout['symbols'][context] & 255)+index > 255
    rows = []
    for index, packet in enumerate(packets):
        c, v = packet['contexts'], packet['values']; length = lengths[c,v]
        start = (np.cumsum(length)-length) % 8; end = (start+length) % 8
        attribute = (c == len(tables)-1).astype(np.int32)
        available = np.where(start != 0, 8-start, 0)
        refills = (np.maximum(0, length-8-available)+7)//8
        ticks = np.where(length <= 8, 168+5*(start+length >= 8)-attribute,
            420+53*(length-9)+32*refills-carry[c,v]+70*(start > 0)+5*(end > 0)-attribute)
        rows.append(dict(frame=index, values=len(v), bits=int(length.sum()),
            long_values=int(np.count_nonzero(length > 8)), primitive_tstates=int(ticks.sum())))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('probe','directory','states','output'): p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args(); probe = json.loads(args.probe.read_text())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if not probe['complete']: raise ValueError('storage experiment incomplete')
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    source = (args.directory/'baseline.raw').read_bytes()
    if sha(source) != probe['raw_sha256'] or sha(states.tobytes()) != probe['states_sha256']:
        raise ValueError('profile inputs do not match storage experiment')
    _,mapping,_,packets,histogram = collect(source,states)
    report = dict(complete=False, release=False, scope=__doc__, timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        raw_sha256=probe['raw_sha256'], states_sha256=probe['states_sha256'], ends=probe['ends'], variants=[])
    baseline = None
    for variant in probe['variants']:
        raw = (args.directory/variant['raw_file']).read_bytes()
        if sha(raw) != variant['raw_sha256']: raise ValueError('candidate hash differs')
        _,_,_,candidate_mapping,tables = read_header(Reader(raw),magic=b'FAP3')
        if candidate_mapping != mapping: raise ValueError('changed predictor mapping')
        layout,cases = verify_symbols(tables,mapping,histogram)
        frames = costs(packets,tables,layout)
        if sum(r['bits'] for r in frames) != variant['bits']: raise AssertionError('bit budget differs')
        if baseline is None: baseline = frames
        row = dict(name=variant['name'], actual_opcode_cases=cases, volumes=[])
        for volume in variant['volumes']:
            part = volume['part']; start = probe['ends'][part-2] if part > 1 else 0; end = probe['ends'][part-1]
            current = frames[start:end]; previous = baseline[start:end]
            before = sum(r['primitive_tstates'] for r in previous); after = sum(r['primitive_tstates'] for r in current)
            row['volumes'].append(dict(part=part,frame_start=start,frame_end_exclusive=end,
                values=sum(r['values'] for r in current),bits=sum(r['bits'] for r in current),
                baseline_bits=sum(r['bits'] for r in previous),
                long_values=sum(r['long_values'] for r in current),
                baseline_long_values=sum(r['long_values'] for r in previous),
                baseline_primitive_tstates=before,primitive_tstates=after,delta_tstates=after-before))
        report['variants'].append(row)
        print(json.dumps(row),flush=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    report['complete'] = True; args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__': main()
