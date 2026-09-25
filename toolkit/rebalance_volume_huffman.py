"""Bounded partition search using already validated per-volume Huffman raws.

Each raw remains a valid whole movie; moving a boundary changes no pixels.
Build real standalone volume layouts, but do not publish mixed-series TRDs.
This is a storage-only search; neither frame cadence nor disk swaps pass here.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('probe','directory','states','zx0','output','report'): p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--first-radius',type=int,default=16)
    p.add_argument('--second-radius',type=int,default=8)
    p.add_argument('--start-ends',help='Three comma-separated endpoints to search around instead of the original probe')
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--fast-noop-scan',action='store_true')
    p.add_argument('--irq-safe-paging',action='store_true')
    p.add_argument('--inline-matches',action='store_true')
    p.add_argument('--deferred-limit',type=int,default=0)
    p.add_argument('--keepalive-fields',type=int,default=0)
    p.add_argument('--frame-service',action='store_true')
    args = p.parse_args(); probe = json.loads(args.probe.read_text())
    if not probe['complete'] or len(probe['ends']) != 3: raise ValueError('requires completed three-volume probe')
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    if sha(states.tobytes()) != probe['states_sha256']: raise ValueError('states differ')
    if min(args.first_radius,args.second_radius) < 0: raise ValueError('negative radius')
    args.output.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    center=[int(s) for s in args.start_ends.split(',')] if args.start_ends else probe['ends']
    if len(center)!=3 or center!=sorted(set(center)) or center[0]<=0 or center[-1]!=len(states):
        raise ValueError('partition must cover the complete movie')
    options=dict(fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True,startup_delta=True,
        fast_noop_scan=args.fast_noop_scan,irq_safe_paging=args.irq_safe_paging,inline_matches=args.inline_matches,
        deferred_limit=args.deferred_limit,keepalive_fields=args.keepalive_fields,frame_service=args.frame_service)
    builders = []
    for i in range(1,4):
        variant = next(v for v in probe['variants'] if v['name'] == f'volume-{i}')
        raw = (args.directory/variant['raw_file']).read_bytes()
        if sha(raw) != variant['raw_sha256']: raise ValueError('raw differs')
        b = ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',**options)
        b.read_cache = [args.directory/'zx0']+args.read_cache; builders.append(b)
    report = dict(complete=False,release=False,scope=__doc__,probe_raw_sha256=probe['raw_sha256'],
        states_sha256=probe['states_sha256'],original_ends=probe['ends'],search_center=center,options=options,first_radius=args.first_radius,
        second_radius=args.second_radius,attempts=[],partitions=[],all_fit=False,
        timing_verified=False,physical_drive_verified=False)
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n')
    save(); memo = {}
    def measure(part,start,end,ends):
        key = (part,start,end)
        if key not in memo:
            b = builders[part-1]; b.ends = ends
            _,m = b.volume(start,end,part)
            row = {k:m[k] for k in ('part','frame_start','frame_end_exclusive','used_sectors',
                'free_sectors','video_bytes','layout_padding_sectors','independently_bootable')}
            report['attempts'].append(row);memo[key] = row;save();print(json.dumps(row),flush=True)
        return memo[key]
    a,b,last = center; fits = []
    # Exhaustive first-boundary window, then try each fitting endpoint in
    # descending order. Stop at the first actual fitting complete partition.
    for first in range(max(1,a-2),min(b,a+args.first_radius+1)):
        row = measure(1,0,first,[first,b,last])
        if row['free_sectors'] >= 0: fits.append(first)
    for first in reversed(fits):
        for second in range(max(first+1,b-2),min(last,b+args.second_radius+1)):
            ends = [first,second,last]
            two = measure(2,first,second,ends)
            if two['free_sectors'] < 0: continue
            three = measure(3,second,last,ends)
            one = memo[1,0,first]
            candidate = dict(ends=ends,used_sectors=[r['used_sectors'] for r in (one,two,three)],
                all_fit=three['free_sectors'] >= 0)
            report['partitions'].append(candidate);save()
            if candidate['all_fit']:
                report.update(all_fit=True,selected=candidate,complete=True);save();return
    report['complete'] = True;save()


if __name__ == '__main__': main()
