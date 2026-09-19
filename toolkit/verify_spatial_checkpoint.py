"""Compare a resumed partial Z80 checkpoint against an uninterrupted prefix."""
import argparse
import json
from pathlib import Path

from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resumed', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    resumed = json.loads(args.resumed.read_text(encoding='utf-8'))
    reference = json.loads(args.reference.read_text(encoding='utf-8'))
    count, groups = len(resumed['frames']), len(resumed['groups'])
    for key in ('input_sha256', 'states_sha256', 'code_hex', 'labels', 'instruction_listing', 'tables'):
        if resumed[key] != reference[key]:
            raise AssertionError('different '+key)
    if (count > len(reference['frames']) or resumed['frames'] != reference['frames'][:count]
            or resumed['groups'] != reference['groups'][:groups]
            or sum(row['total_tstates'] for row in resumed['frames']) != sum(row['tstates']*row['count'] for row in resumed['instruction_histogram'])):
        raise AssertionError('resumed timings/coverage differ')
    report = dict(scope=__doc__, complete=True, frames=count, groups=groups,
        input_sha256=resumed['input_sha256'], states_sha256=resumed['states_sha256'],
        resumed_report_sha256=sha(args.resumed.read_bytes()), reference_report_sha256=sha(args.reference.read_bytes()),
        exact_frame_rows_and_group_coverage=True, histogram_total_matches_frames=True,
        total_tstates=sum(row['total_tstates'] for row in resumed['frames']),
        note='Resumed frame output is checked by the benchmark against full reference states; this checks the saved timing rows.')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
