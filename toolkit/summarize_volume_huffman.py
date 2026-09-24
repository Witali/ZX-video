"""Summarize exact publication recovery, distinct from IRQ field counters."""
import argparse
import json
from pathlib import Path


def actual_runs(phases):
    runs = [];first = None
    for index, phase in enumerate(phases):
        if abs(phase) > 64 and first is None: first = index
        if abs(phase) <= 64 and first is not None:
            runs.append(dict(start=first,end=index-1,recovered_at=index));first = None
    if first is not None: runs.append(dict(start=first,end=len(phases)-1,recovered_at=None))
    return runs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('summary','evidence','output'): p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args();summary = json.loads(args.summary.read_text())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if not summary['complete']: raise ValueError('incomplete run')
    rows = []
    for volume in summary['variants'][0]['volumes']:
        data = json.loads((args.evidence/volume['full_report']).read_text())
        if not data['complete'] or data['trd_sha256'] != volume['trd_sha256']: raise ValueError('evidence differs')
        runs = actual_runs(data['actual_phase_tstates'])
        row = dict(part=volume['part'],frames=data['frames'],actual_fps=volume['timing']['actual_fps'],
            nominal_missed=volume['timing']['missed_nominal_frames'],
            actual_phase_missed=sum(abs(p)>64 for p in data['actual_phase_tstates']),
            actual_out_deviation_runs=runs,
            actual_recovered_runs=sum(r['recovered_at'] is not None for r in runs),
            actual_unrecovered_runs=sum(r['recovered_at'] is None for r in runs),
            irq_counter_recovered_runs=volume['timing']['recovered_late_runs'],
            maximum_deviation_seconds=max(map(abs,data['actual_phase_tstates']))/3546900,
            ay_missing_fields=data['ay_record_field_gaps'],audio_underruns=data['audio_underruns'])
        rows.append(row)
    report = dict(complete=True,release=False,scope=__doc__,nominal_tolerance_tstates=64,
        nominal_interval_tstates=425448,volume_start_is_local_schedule_origin=True,volumes=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__ == '__main__': main()
