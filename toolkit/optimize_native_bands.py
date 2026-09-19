"""Use the dense Z80 writer when redrawing a whole band costs fewer cycles.

Only native output maps change; reconstructed pixels, coded data and AY do
not. Setting extra map bits redraws cells whose back-screen pixels are
already correct. Compare the exact current writer formulas per band, then
save FAP1 for a separate actual ZX0 size and integrated CPU measurement.
"""
import argparse
import json
from pathlib import Path
import struct

from cell_audio_stream import take_tick
from cell_screen_z80 import expected_tstates
from frame_packet_stream import unpack
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha


def optimize(mask):
    if len(mask) != 80: raise ValueError('80-byte native map required')
    out = bytearray(mask)
    bands = []
    for band in range(20):
        flags = mask[band*4:band*4+4]
        if flags == b'\xff'*4: continue
        partial = 296*sum(value.bit_count() for value in flags)-136*flags.count(0)
        dense = 5853+4*(band & 1)
        if dense < partial:
            out[band*4:band*4+4] = b'\xff'*4
            bands.append(band)
    if any(a & b != a for a,b in zip(mask,out)): raise AssertionError('required output bit removed')
    delta = expected_tstates(out,fast_mask_dispatch=True)-expected_tstates(mask,fast_mask_dispatch=True)
    if delta > 0: raise AssertionError('slower output map')
    return bytes(out), bands, delta


def transform(source):
    # Full format roundtrip also validates variable lengths and cache maps.
    unpack(source)
    r = Reader(source); _, _, count, _, _ = read_header(r,magic=b'FAP1')
    out, rows = bytearray(source[:r.pos]), []
    for index in range(count):
        for _ in range(6): out += take_tick(r)
        header = r.take(7); _, masks, coded, literals = struct.unpack('<BHHH',header)
        out += header+r.take(3+192+masks)
        position = r.pos
        original = r.take(80); replacement, bands, delta = optimize(original)
        out += replacement+r.take(coded+literals)
        rows.append(dict(index=index,map_offset=position,changed_bands=bands,delta_tstates=delta,
            old_tstates=expected_tstates(original,fast_mask_dispatch=True),
            new_tstates=expected_tstates(replacement,fast_mask_dispatch=True)))
    r.end(); unpack(bytes(out))
    # Prove unchanged bytes outside output maps (including all AY records).
    restored = bytearray(out)
    for row in rows:
        p = row['map_offset']; restored[p:p+80] = source[p:p+80]
    if restored != source: raise AssertionError('non-map data changed')
    return bytes(out), rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','report'): p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); source = args.source.read_bytes()
    result, rows = transform(source)
    report = dict(scope=__doc__,complete=True,input_sha256=sha(source),output_sha256=sha(result),
        raw_bytes=len(result),frames=len(rows),frames_changed=sum(bool(r['changed_bands']) for r in rows),
        bands_changed=sum(len(r['changed_bands']) for r in rows),
        old_output_tstates=sum(r['old_tstates'] for r in rows),new_output_tstates=sum(r['new_tstates'] for r in rows),
        delta_output_tstates=sum(r['delta_tstates'] for r in rows),
        timing_basis='Instruction-count formula of fast_mask_dispatch; transformed stream CPU not measured here.',
        instruction_bytes_changed=False,unchanged_non_map_bytes=True,required_cells_preserved=True,
        zx0_bytes_measured=False,release=False,frames_detail=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(result)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frames_detail'}),flush=True)


if __name__ == '__main__': main()
