"""Measure unchanged-tile run shapes and AY starvation in complete evidence.

Scanner cycle deltas are instruction-table predictions until paired Z80
execution verifies them. AY ticks plus empty-queue ISR visits distinguish
producer starvation from unobserved physical interrupt fields.

The proposed scanner combines vector and mask tests. Keep DEC HL after
the final OR: DEC L would overwrite Z before JP Z. INC L is safe before
that OR because mask pairs start at even addresses. Retain INC DE for
zero-copy vectors: the packet's vector array can cross a page boundary.
The archived fast_noop_probe.json used a single-page assumption; its
estimate is superseded by the implementation's measured report.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from build_fap3_trd import sha


def scanner_tstates(length, following, proposed=False):
    """Tile entry through jump to next tile/stripe, excluding destination.

    Counts use the existing instruction listing in causal_tile_z80.py.
    Proposed: initial mask pair INC/DEC L (-4 T), advancing INC DE then
    INC L/INC HL (-2 T/tile), combined check 41/51 T versus 57/21/67 T.
    ROM, disk, paging outside scanner, IRQ and ULA contention excluded.
    """
    if not 1 <= length <= 16 or following not in ('end', 'vector', 'patch'):
        raise ValueError('invalid run shape')
    if proposed:
        return 74*length+(212 if following == 'end' else 278)
    return 92*length+{'end':200,'vector':236,'patch':282}[following]


def frame_runs(vectors,masks,static_stripes=True):
    runs = []; patches = 0
    for first in range(0,192,16):
        if static_stripes and first in (0,176) and vectors[first] == 0: continue
        i = first
        while i < first+16:
            if vectors[i]: i += 1; continue
            if masks[2*i] or masks[2*i+1]: patches += 1;i += 1;continue
            begin = i
            while i < first+16 and not (vectors[i] or masks[2*i] or masks[2*i+1]): i += 1
            runs.append((i-begin,'end' if i == first+16 else 'vector' if vectors[i] else 'patch'))
    return runs,patches


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args();source = args.raw.read_bytes();r = Reader(source)
    _,_,count,_,_ = read_header(r,magic=b'FAP3');hist = Counter();patches = 0;frames = []
    for index in range(count):
        _,d = read_packet(r,stored_guards=False);at = sum(map(len,d['ticks']))+8
        v = d['payload'][at:at+192];m = restore(d['payload'][at+192:at+192+d['mask_bytes']],1,480,4)
        runs,n = frame_runs(v,m);hist.update(runs);patches += n
        delta = -6*n+sum(scanner_tstates(length,kind,True)-scanner_tstates(length,kind)
            for length,kind in runs)
        frames.append(dict(frame=index,delta_tstates=delta))
    r.end();ay = []
    for path in sorted(args.evidence.glob('fuse_part*.json')):
        data = json.loads(path.read_bytes())
        if not data['complete']: raise ValueError('partial Fuse evidence')
        ticks = data['audio_tick_tstates'];empty = data['audio_underrun_tstates']
        first,last = ticks[0]//70908,ticks[-1]//70908
        observed = {t//70908 for t in ticks+empty if first <= t//70908 <= last}
        missing = [field for field in range(first,last+1) if field not in observed]
        read_overlap = sum(any(rd['start_tstate'] <= f*70908 < rd['end_tstate'] for rd in data['reads']) for f in missing)
        ay.append(dict(part=data['part'],played_records=len(ticks),empty_queue_visits=len(empty),
            empty_queue_fields=len({t//70908 for t in empty if first <= t//70908 <= last}),
            ay_missing_fields=data['ay_record_field_gaps'],unobserved_physical_fields=len(missing),
            unobserved_fields_in_read_windows=read_overlap,
            note='Counts field occupancy, not exact IRQ entry time; seek timestamps are unavailable.'))
    report = dict(complete=True,release=False,scope=__doc__,raw_sha256=sha(source),frames=count,
        scanner_prediction_verified=False,estimated_delta_tstates=sum(f['delta_tstates'] for f in frames),
        player_modified=True,
        cycle_model=dict(unit='Z80 T-states',
            baseline_run=dict(end='92*k+200',vector='92*k+236',patch='92*k+282'),
            proposed_run=dict(end='74*k+212',vector='74*k+278',patch='74*k+278'),
            zero_vector_patch_overhead=dict(baseline=257,proposed=251,delta=-6,
                scope='Tile entry through tile_done; patch routine body excluded, CALL included.'),
            assumptions=['Vectors can cross pages; even mask pairs at A4C0..A63F.',
                'Static first/last stripes skipped by the existing marker; no encoded runs.',
                'Final OR followed by DEC HL, preserving Z for JP Z.',
                'CPU estimate only: excludes IRQ, ULA, ROM and physical disk latency.']),
        estimated_slower_frames=sum(f['delta_tstates']>0 for f in frames),zero_vector_patch_tiles=patches,
        runs=[dict(length=k,following=t,count=n) for (k,t),n in sorted(hist.items())],
        ay=ay,per_frame=frames)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','per_frame')}),flush=True)


if __name__ == '__main__': main()
