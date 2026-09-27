"""Complete only the cases missing when disk 3 was still being built.

The preceding test process exited on FileNotFoundError, after disks 1/2
and the baseline for disk 3 completed. Preserve those measured cases.
"""
import argparse
import json
from pathlib import Path
from build_fap3_trd import sha
from test_resumable_packet import run

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','baseline','previous','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args(); data = a.previous.read_bytes(); report = json.loads(data)
    if report['complete'] or not report.get('failure','').startswith('FileNotFoundError('):
        raise ValueError('expected the preserved missing-build attempt')
    report['resumed_from_sha256'] = sha(data); report['previous_failure'] = report.pop('failure')
    report['resume_scope'] = __doc__
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for row in report['volumes']:
            part = row['part']; count = len(row['baseline']['frames'])
            for name,forced,stress,n in (('required',False,False,count),('resumed',True,False,count),('irq',True,True,8)):
                if name in row: continue
                row[name] = run(a.directory,part,count=n,forced=forced,stress=stress); save()
                print(json.dumps(dict(part=part,case=name,tstates=row[name]['tstates'],
                                      paused=row[name]['paused'],irq_calls=row[name]['irq_calls'])),flush=True)
            if 'split_length' not in row:
                row['split_length'] = run(a.directory,part,count=1,forced=True,stress=True,split_length=True); save()
            row['required_delta_tstates'] = row['required']['tstates']-row['baseline']['tstates']
            row['resumed_delta_tstates'] = row['resumed']['tstates']-row['baseline']['tstates']
        report.update(complete=True,source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('test_resumable_packet.py','resumable_packet_player.py','resume_resumable_packet_tests.py')})
    except Exception as exc: report['failure'] = repr(exc); raise
    finally: save()


if __name__ == '__main__': main()
