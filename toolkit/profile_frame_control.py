"""Profile measured foreground categories and unchanged-tile runs.

Run statistics identify optimization candidates; they are not cycle-saving
estimates. A no-op tile has vector zero and both bitmap masks zero. Runs
stop at each 16-tile stripe, where the cache and row traversal still matter.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from frame_output_pipeline import frames
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cpu','cells','output'): p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args(); cpu = json.loads(args.cpu.read_text(encoding='utf-8'))
    source = args.cells.read_bytes(); _,_,packets = frames(source)
    if not cpu['complete'] or len(cpu['frames']) != len(packets): raise ValueError('full matching frame reports required')
    instructions = {row['address']:row for row in cpu['instruction_listing']}
    stages = Counter()
    for row in cpu['instruction_histogram']:
        instruction = instructions.get(row['address'])
        key = (instruction['phase']+'/'+instruction.get('stage','unknown')) if instruction else 'ZX0_or_AY'
        stages[key] += row['tstates']*row['count']
    if sum(stages.values()) != cpu['summary']['total_tstates']: raise AssertionError('profile sum differs')
    counts, runs, rows = Counter(),Counter(),[]
    for index, (group,_) in enumerate(packets):
        vectors, masks = group[3:5]
        unchanged = [v == 0 and masks[i*2:i*2+2] == b'\0\0' for i,v in enumerate(vectors)]
        local = Counter()
        for first in range(0,192,16):
            run = 0
            for flag in unchanged[first:first+16]+[False]:
                if flag: run += 1
                elif run: local[run] += 1; run = 0
        counts.update(vectors); runs.update(local)
        rows.append(dict(index=index,unchanged_tiles=sum(unchanged),run_histogram=dict(sorted(local.items()))))
    report = dict(scope=__doc__,complete=True,cpu_report=args.cpu.name,cells_sha256=sha(source),
        frames=len(packets),measured_tstates=dict(stages.most_common()),vector_histogram=dict(sorted(counts.items())),
        unchanged_tiles=sum(r['unchanged_tiles'] for r in rows),total_tiles=192*len(rows),
        unchanged_run_histogram=dict(sorted(runs.items())),player_changed=False,delta_tstates=0,frames_detail=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frames_detail'}),flush=True)


if __name__ == '__main__': main()
