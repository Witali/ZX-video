"""Authenticate actual complete execution before scoring clock controls."""
import argparse
import json
from pathlib import Path
import shutil

from measure_prototype import measure
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('--stage',default='clock-compensation')
    p.add_argument('--source',action='append');p.add_argument('--scratch',required=True,type=Path)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    a=p.parse_args();root=a.evidence.resolve();stage=root/a.stage;a.scratch.mkdir(parents=True,exist_ok=True)
    names=a.source or ['silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam']
    rows=[]
    for name in names:
        dest=stage/name;host=json.loads((dest/'host.json').read_bytes())
        execution=json.loads((dest/'verification/execution.json').read_bytes())
        assert execution['complete'] and execution['packed_sha256']==host['packed_sha256']
        actual=[]
        for profile in ('pentagon512','pentagon1024') if name=='sea_foam' else ('pentagon512',):
            after=measure(dest,profile,a.ffmpeg,a.scratch)
            predicted=host['fixed_clock'];assert abs(after['fixed_clock']['error_rms']-predicted['error_rms'])<1e-10
            score=after['fixed_clock']['snr_db'];before=host['baseline_fixed_clock']['snr_db']
            actual.append(dict(profile=profile,after=after,host_prediction_reproduced=True,
                               change_db=None if score is None else score-before))
        rows.append(dict(source=name,actual=actual,baseline=host['baseline_fixed_clock'],
                         baseline_complete_actual_trace_available=name in ('speech','entertainer','sea_foam'),
                         strict20_db_passed=all(r['after']['fixed_clock']['snr_db'] is not None and
                                              r['after']['fixed_clock']['snr_db']>=20 for r in actual),
                         artifact_acceptance_separate=True))
        print(json.dumps(dict(source=name,actual_fixed_clock=actual[0]['after']['fixed_clock'],
                              gain_db=actual[0]['change_db'])),flush=True)
        save(stage/'actual-quality-partial.json',dict(complete=False,rows=rows))
    save(stage/'actual-quality.json',dict(complete=True,rows=rows,full_execution_required=True,
         reference='Original8-kHz source, unfitted, unchanged filter and fixed100-ms edges',
         release_accepted=False,physical_hardware_tested=False,
         main_checkout_unchanged=True,artifact_acceptance_required=True))


if __name__=='__main__':main()
