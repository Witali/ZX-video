"""Rebalance CB41 cuts using saved block costs and exact small-window probes.

Use row-set prefix counts to reject impossible cuts, apportion the existing
compressed blocks over their raw frame spans, then check one selected set
of cuts on local windows. No candidate whole movies or TRDs are compressed.
"""
import argparse
import bisect
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from build_five_level_test_trd import save
from lzsa2_oracle_host import Author
from prepare_cell_codebook_movie import file_sha, sha
from probe_cell_codebook import changes, encode, decode_check, compress
from row_dictionary_video import encode_states


def block_weights(volume):
    blocks = volume['blocks']
    starts = [b['raw_start'] for b in blocks]
    sums = np.r_[0, np.cumsum([4+b['compressed_bytes'] for b in blocks])]
    def cost(at):
        if at == volume['raw_bytes']:
            return float(sums[-1])
        i = bisect.bisect_right(starts, at)-1
        block = blocks[i]
        return float(sums[i]+(at-block['raw_start'])*(4+block['compressed_bytes'])/block['decoded_bytes'])
    at, weights = 2056, []
    for frame in volume['frames']:
        end = at+2+frame['packet_bytes']
        weights.append(cost(end)-cost(at))
        at = end
    assert at == volume['raw_bytes']
    assert abs(sum(weights)+cost(2056)-volume['compressed_bytes']) < 1e-6
    return weights, cost(2056)


def representation(frames, start, end):
    first = max(0, start-2)
    states, table = encode_states(frames[first:end])
    rows = changes(states, start-first, end-start)
    counts = Counter(row['patterns'][i] for row in rows for i in row['changed'])
    book = sorted(counts, key=lambda key: (-counts[key], key))[:256]
    assert len(book) == 256
    return dict(first=first, start=start, end=end, states=states, table=table, rows=rows, book=book)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'measurements', 'capacity', 'author', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    prepared = json.loads(a.prepared.read_bytes())
    measured = json.loads(a.measurements.read_bytes())
    capacity = json.loads(a.capacity.read_bytes())
    assert measured['preparation_sha256'] == file_sha(a.prepared) == capacity['preparation_sha256']
    assert capacity['measurements_sha256'] == file_sha(a.measurements)
    with np.load(a.prepared.parent/'words.npz', allow_pickle=False) as cache:
        words = cache['words']
    with np.load(a.measurements.parent/'five-states.npz', allow_pickle=False) as cache:
        frames = [s.tobytes() for s in cache['five_states']]
    assert len(words) == len(frames) == prepared['frames']
    weights, headers = [], []
    for volume in measured['volumes']:
        share, header = block_weights(volume)
        weights.extend(share)
        headers.append(header)
    cumulative = np.r_[0, np.cumsum(weights)]
    prefix = np.vstack([np.zeros(625,dtype=np.int32),
        np.cumsum(np.stack([np.bincount(w,minlength=625)>0 for w in words]),axis=0,dtype=np.int32)])
    old_cuts = [v['end'] for v in measured['volumes'][:-1]]
    overhead = [v['overhead_sectors'] for v in capacity['volumes']]
    candidates, tested = [], 0
    for left in range(max(16,(old_cuts[0]-256+15)//16*16), min(len(words),old_cuts[0]+256)+1,16):
        for right in range(max(left+16,(old_cuts[1]-256+15)//16*16), min(len(words),old_cuts[1]+256)+1,16):
            if right>=len(words):
                continue
            tested += 1
            bounds = [0,left,right,len(words)]
            counts = []
            for lo,hi in zip(bounds,bounds[1:]):
                used = prefix[hi]-prefix[max(0,lo-2)]
                used[0] = 1
                counts.append(int(np.count_nonzero(used)))
            if max(counts)>256:
                continue
            totals = [math.ceil((cumulative[hi]-cumulative[lo]+header)/256)+boot
                      for lo,hi,header,boot in zip(bounds,bounds[1:],headers,overhead)]
            candidates.append(dict(boundaries=bounds, rows=counts, estimated_used_sectors=totals,
                score=[max(totals), abs(left-old_cuts[0])+abs(right-old_cuts[1]), left, right]))
    if not candidates:
        raise ValueError('no row-valid partition in the bounded search')
    chosen = min(candidates,key=lambda row:row['score'])
    bounds = chosen['boundaries']
    old_bounds = [0]+old_cuts+[len(words)]
    old = [representation(frames,lo,hi) for lo,hi in zip(old_bounds,old_bounds[1:])]
    new = [representation(frames,lo,hi) for lo,hi in zip(bounds,bounds[1:])]
    for rep, volume in zip(old,measured['volumes']):
        raw,_,_ = encode(rep['rows'],rep['book'],rep['table']['words'])
        assert sha(raw) == volume['raw_sha256'], 'baseline representation no longer reproduces saved stream'
    windows = set()
    for before,after in zip(old_cuts,bounds[1:-1]):
        lo,hi = sorted((before,after))
        windows.add((max(0,lo-64),lo))
        windows.add((hi,min(len(words),hi+64)))
        if hi>lo:
            pieces = math.ceil((hi-lo)/64)
            edges = np.linspace(lo,hi,pieces+1,dtype=int)
            windows.update(zip(map(int,edges),map(int,edges[1:])))
    author, probes = Author(a.author), []
    for lo,hi in sorted(windows):
        item = dict(start=lo,end=hi,frames=hi-lo)
        for name,reps in (('previous',old),('candidate',new)):
            rep = next(r for r in reps if r['start']<=lo and hi<=r['end'])
            rows = rep['rows'][lo-rep['start']:hi-rep['start']]
            raw,_,_ = encode(rows,rep['book'],rep['table']['words'])
            _,checks = decode_check(raw,rep['states'],lo-rep['first'],hi-lo,rep['table']['words'],rep['table'])
            stream,blocks = compress(raw,author)
            target = a.output/f'{lo}-{hi}-{name}'
            target.with_suffix('.raw').write_bytes(raw)
            target.with_suffix('.stream').write_bytes(stream)
            item[name] = dict(raw_bytes=len(raw), compressed_bytes=len(stream),
                raw_sha256=sha(raw), stream_sha256=sha(stream),
                frames_screen_sha256=checks, blocks=blocks)
        assert item['previous']['frames_screen_sha256'] == item['candidate']['frames_screen_sha256']
        probes.append(item)
    report = dict(complete=True,release=False,scope=__doc__,baseline_commit='2a1686d',
        preparation_sha256=file_sha(a.prepared),measurements_sha256=file_sha(a.measurements),
        capacity_sha256=file_sha(a.capacity), boundaries=bounds, selected=chosen,
        row_boundary_candidates=tested,row_valid_candidates=len(candidates),
        estimates_are_not_capacity_proof=True, unchanged_native_instruction_delta_tstates=0,
        estimated_overhead_sectors=overhead, previous_boundaries=old_bounds,
        compressed_whole_movie_candidates=0, windows=probes,
        host_windows_exact=True, windows_frames=sum(p['frames'] for p in probes),
        previous_window_bytes=sum(p['previous']['compressed_bytes'] for p in probes),
        candidate_window_bytes=sum(p['candidate']['compressed_bytes'] for p in probes),
        estimate_method='Existing compressed-block byte cost apportioned over raw frame extents; old per-volume startup overhead. Does not model changed codebooks or all cross-boundary matches.',
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('plan_cell_codebook_volumes.py','probe_cell_codebook.py','row_dictionary_video.py')})
    save(a.output/'plan.json',report)
    print(json.dumps({k:report[k] for k in ('boundaries','selected','row_boundary_candidates','row_valid_candidates',
        'windows_frames','previous_window_bytes','candidate_window_bytes')}),flush=True)


if __name__ == '__main__':
    main()
