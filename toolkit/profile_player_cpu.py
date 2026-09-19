"""Rank measured instructions and sub-stages in a complete player CPU report."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def profile(path):
    data = path.read_bytes(); report = json.loads(data)
    if not report['complete']: raise ValueError('complete CPU report required')
    instructions = {r['address']:r for r in report['instruction_listing']}
    phases,stages,totals,calls = Counter(),Counter(),Counter(),Counter()
    for row in report['instruction_histogram']:
        pc = row['address']; inst = instructions.get(pc,{})
        ticks = row['count']*row['tstates']
        phase = inst.get('phase','unlisted ZX0/AY')
        phases[phase] += ticks
        stages[phase+'/'+inst.get('stage',phase)] += ticks
        totals[pc] += ticks; calls[pc] += row['count']
    if sum(totals.values()) != report['summary']['total_tstates']:
        raise AssertionError('histogram does not match complete foreground')
    return dict(scope=__doc__,input=path.as_posix(),input_sha256=sha256(data).hexdigest(),
        complete=True,measured=True,total_tstates=sum(totals.values()),phases=dict(phases.most_common()),
        sub_stages=dict(stages.most_common()),hot_instructions=[dict(address=pc,tstates=ticks,
            executions=calls[pc],instruction=instructions.get(pc,{})) for pc,ticks in totals.most_common(50)])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cpu',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    args = p.parse_args(); result = profile(args.cpu)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['sub_stages'],indent=2))
    print(json.dumps(result['hot_instructions'][:15],indent=2))


if __name__ == '__main__': main()
