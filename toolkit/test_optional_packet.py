"""Check separate optional consumption against the saved identical baseline.

Reuse the already verified CPU execution fixture; keep its historical
source unchanged. Exercise every new opcode, shared queue ownership,
split length/EOF, clobbered registers and real AY IRQ preservation.
"""
import argparse
import json
from pathlib import Path
from build_fap3_trd import sha
from test_resumable_packet import run, fixture

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--reference',type=Path,default=ROOT/'resumable_packet_cpu.json')
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args(); reference = json.loads(a.reference.read_bytes())
    if not reference['complete'] or reference['parts'] != [1,2,3]: raise ValueError('incomplete CPU baseline')
    report = dict(complete=False,release=False,scope=__doc__,reference_sha256=sha(a.reference.read_bytes()),
                  parts=[1,2,3],volumes=[])
    names = ('test_optional_packet.py','optional_packet_player.py','test_resumable_packet.py','resumable_packet_player.py')
    report['source_sha256_lf'] = {n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names}
    if report['source_sha256_lf']['test_resumable_packet.py'] != reference['source_sha256_lf']['test_resumable_packet.py']:
        raise ValueError('baseline CPU fixture changed')
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for part in (1,2,3):
            before = reference['volumes'][part-1]; row = dict(part=part,baseline=before['baseline'])
            report['volumes'].append(row); count = len(before['baseline']['frames'])
            c,m,_,_ = fixture(a.directory,part); q=m['queue_labels']; optional=m['resumable_packet']
            actual = bytes(c.read8(i) for i in range(q['take'],q['fatal']))
            if sha(actual) != optional['original_required_consumer_sha256']:
                raise AssertionError('required consumer opcodes changed during boot')
            row['required_consumer_exact'] = True
            for name,forced,stress,n,split in (
                    ('required',False,False,count,False),('resumed',True,False,count,False),
                    ('irq',True,True,8,False),('split_length',True,True,1,True)):
                row[name] = run(a.directory,part,count=n,forced=forced,stress=stress,split_length=split); save()
                print(json.dumps(dict(part=part,case=name,tstates=row[name]['tstates'],
                    paused=row[name]['paused'],irq_calls=row[name]['irq_calls'])),flush=True)
            for name in ('required','resumed'):
                row[name+'_delta_tstates'] = row[name]['tstates']-row['baseline']['tstates']
                row[name+'_delta_from_global_gate_tstates'] = row[name]['tstates']-before[name]['tstates']
            if not row['resumed']['paused'] or not row['irq']['irq_calls'] or not row['split_length']['paused']:
                raise AssertionError('optional/IRQ boundary was not exercised')
            # Required calls never enter the duplicate consumer/gate/partial
            # path. Assert actual instruction counts, not only metadata flags.
            labels = optional['labels']
            if any(h['count'] for h in row['required']['instruction_histogram']
                   if labels['optional_take'] <= h['address'] < labels['stage']):
                raise AssertionError('required read executed optional checks')
            save()
        report['complete'] = True
    except Exception as exc: report['failure'] = repr(exc); raise
    finally: save()


if __name__ == '__main__': main()
