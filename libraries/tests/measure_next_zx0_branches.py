"""E01: prove bounded branch contractions against immutable E00 observations.

Runs changed bytes, not just a branch model. Every case has protected disjoint
and actual minimum-safe overlap replays, each plain/IRQ/relocated. Independent
binary/label relocation and all 256 low-byte layouts precede qualification.
"""
import argparse
from datetime import date
import gzip
import json
from pathlib import Path
import subprocess

from measure_long_copy import ROOT, sha
from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from native_block import execute
from native_inplace_block import execute as inplace
from next_zx0_branches_profile import build, POLICIES, REPORT_PATH, selection


def regions(profile):
    return [dict(address=at, bytes=len(blob), sha256=sha(blob)) for at,blob in profile[0]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--policies', nargs='+', choices=POLICIES, default=POLICIES)
    parser.add_argument('--caps', nargs='+', type=int, choices=(127,228), default=(228,127))
    args = parser.parse_args()
    baseline = json.loads(gzip.decompress(REPORT_PATH.read_bytes()))
    cases = [(n,p,r,False) for n,p,r in samples()]
    cases += [(n,p,r,True) for n,p,r in high_word_samples()]
    assert len(cases) == 473
    result = dict(date=date.today().isoformat(), stage='E01', complete=False,
        release=False, public_decoder_changes=False, fixed_decoder_revision='9c28b01f',
        experiment_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        e00_report_sha256=sha(REPORT_PATH.read_bytes()), profiles={},
        tstate_delta_formula='2*taken - 3*not_taken; only selected JPcc->JRcc encodings differ',
        acceptance='strictly lower real CPU AND complete service memory, with every slower case explicit')

    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(gzip.compress((json.dumps(result,indent=2)+'\n').encode(),mtime=0))

    try:
        for cap in args.caps:
            frozen = baseline['profiles'][str(cap)]
            previous = {row['case']:row for row in frozen['blocks']}
            for policy in args.policies:
                picked = selection(cap,policy)
                offsets = {row['source_offset'] for row in picked['branches']}
                targets = {large:(build(core=0x0800 if large else 0x8000,prefix_cap=cap,policy=policy),
                                  build(core=0x0703 if large else 0x9103,prefix_cap=cap,policy=policy))
                           for large in (False,True)}
                normal = targets[False][0]
                key = f'{cap}-{policy}'
                report = dict(prefix_cap=cap,policy=policy,complete=False,
                    regions=regions(normal), relocated_regions=regions(targets[False][1]),
                    high_word_regions=regions(targets[True][0]),
                    high_word_relocated_regions=regions(targets[True][1]),
                    changes=normal[2]['next_branch_changes'],
                    baseline_service_bytes=frozen['service_memory_bytes'],
                    service_memory=normal[2]['service_memory'],
                    service_bytes=normal[2]['service_memory_bytes'],blocks=[],alignments=[])
                result['profiles'][key] = report
                for low in range(256):
                    layout = build(core=0x8000+low,prefix_cap=cap,policy=policy)
                    assert layout[2]['service_memory_bytes'] == report['service_bytes']
                    assert layout[2]['independent_binary_and_label_oracle_exact']
                    report['alignments'].append(dict(origin=0x8000+low,regions=regions(layout),
                        service_bytes=layout[2]['service_memory_bytes']))
                for index,(name,payload,raw,large) in enumerate(cases):
                    old = previous[name]
                    assert sha(payload) == old['input_sha256'] and sha(raw) == old['output_sha256']
                    delta = sum(2*old['branch_counts'].get(str(0x8000+offset),[0,0])[1]
                                -3*old['branch_counts'].get(str(0x8000+offset),[0,0])[0]
                                for offset in offsets)
                    profile,moved = targets[large]
                    ordinary_options = dict(source=0x0400,output=0x3000,caller_stack=0x2ff0) if large else {}
                    overlap_options = dict(output=0x3000,caller_stack=0x2ff0) if large else {}
                    plain = execute(profile,payload,raw,**ordinary_options)
                    irq = execute(profile,payload,raw,interrupts=True,**ordinary_options)
                    relocated = execute(moved,payload,raw,**ordinary_options)
                    overlapped = inplace(profile,payload,raw,codec='zx0',**overlap_options)
                    overlapped_irq = inplace(profile,payload,raw,codec='zx0',interrupts=True,**overlap_options)
                    overlapped_relocated = inplace(moved,payload,raw,codec='zx0',**overlap_options)
                    assert plain['tstates'] == old['tstates']+delta, (key,name,plain,old['tstates'],delta)
                    assert all(row['tstates'] == plain['tstates'] for row in (relocated,overlapped,overlapped_relocated))
                    assert irq['tstates'] == overlapped_irq['tstates']
                    assert all(row['host_read_order_exact'] for row in (overlapped,overlapped_irq,overlapped_relocated))
                    assert max(row['stack_bytes'] for row in (plain,relocated,overlapped,overlapped_relocated)) <= 4
                    assert max(irq['stack_bytes'],overlapped_irq['stack_bytes']) <= 10
                    report['blocks'].append(dict(case=name,real=name.startswith('real-'),high_word=large,
                        input_sha256=sha(payload),output_sha256=sha(raw),
                        input_bytes=len(payload),output_history_bytes=len(raw),
                        baseline_tstates=old['tstates'],candidate_tstates=plain['tstates'],delta_tstates=delta,
                        plain=plain,irq=irq,relocated=relocated,inplace=overlapped,
                        inplace_irq=overlapped_irq,inplace_relocated=overlapped_relocated))
                    if (index+1)%100 == 0:
                        print(key,f'{index+1}/{len(cases)}',flush=True)
                # Independently exercise the supported final output cursor FFFFh.
                name,payload,raw,_ = next(row for row in cases if 0<len(row[2])<=4096)
                end_probe = execute(normal,payload,raw,output=65535-len(raw))
                assert end_probe['exact']
                real = [row for row in report['blocks'] if row['real']]
                slower = [dict(case=row['case'],real=row['real'],high_word=row['high_word'],delta_tstates=row['delta_tstates'])
                          for row in report['blocks'] if row['delta_tstates']>0]
                report.update(complete=True,cases=len(cases),native_replays=6*len(cases),
                    real_baseline_tstates=sum(row['baseline_tstates'] for row in real),
                    real_candidate_tstates=sum(row['candidate_tstates'] for row in real),
                    real_delta_tstates=sum(row['delta_tstates'] for row in real),
                    service_delta_bytes=report['service_bytes']-report['baseline_service_bytes'],
                    slower_cases=slower,slower_real_cases=[row for row in slower if row['real']],
                    maximum_delta_tstates=max(row['delta_tstates'] for row in report['blocks']),
                    output_end_FFFF_probe=dict(case=name,result=end_probe),
                    independent_binary_and_label_oracle_exact=True)
                assert report['real_delta_tstates'] == picked['real_delta_tstates'] < 0
                assert report['service_delta_bytes'] == picked['service_delta_bytes'] < 0
                assert not report['slower_real_cases']
                save()
                print(json.dumps({k:report[k] for k in ('prefix_cap','policy','real_candidate_tstates','service_bytes','real_delta_tstates','service_delta_bytes')}),flush=True)
        sources = [Path(__file__),Path(__file__).with_name('next_zx0_branches_profile.py'),
                   Path(__file__).with_name('native_block.py'),Path(__file__).with_name('native_inplace_block.py'),
                   ROOT/'libraries/zx0/src/zx0/maximum.py',ROOT/'libraries/zx0/src/zx0/_shared_prefixes.py',
                   ROOT/'libraries/zx0/src/zx0/_z80.py',ROOT/'libraries/Z80_TIMINGS.md']
        result['source_sha256_lf'] = {str(path.relative_to(ROOT)).replace('\\','/'):
                                    sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in sources}
        result['complete'] = True
    except BaseException as error:
        result['failure'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
