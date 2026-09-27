"""Compare actual cold-loaded Turbo/Fast queue control and patched operands.

The ten queue paths exclude callee bodies, ROM, IRQ and ULA. Full decoder
counts and actual playback are separate measurements; never sum nested costs.
"""
import argparse
import json
from pathlib import Path

from build_fap3_trd import sha
from measure_inplace_streaming_queue import run
from test_fap3_disk import DiskCPU
from test_warm_continuation import player, until
import fap3_disk_z80 as disk

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline', 'fast', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    report = dict(complete=False, release=False, scope=__doc__, variants={})
    cases = ('full', 'eof_idle', 'begin', 'header_wait', 'prefix_ready', 'decode_more',
             'decode_eof', 'take_ready', 'take_partial', 'take_need_decode')
    loaded = {}
    for name, folder in (('baseline', args.baseline), ('fast', args.fast)):
        stem = folder/'ZX-video-huffman-preview_part01'
        image, metadata = stem.with_suffix('.trd').read_bytes(), stem.with_suffix('.json').read_bytes()
        m = json.loads(metadata)
        if sha(image) != m['trd_sha256']: raise ValueError('image identity differs')
        c = DiskCPU(player(image), image); until(c, disk.DRIVER); loaded[name] = c
        rows = [run(image, m, case) for case in cases]
        report['variants'][name] = dict(trd_sha256=sha(image), metadata_sha256=sha(metadata), cases=rows)
        if name == 'fast':
            checked = []
            for patch in m['fast_zx0']['external_operands']:
                at = patch['operand_address']
                before = loaded['baseline'].read8(at)+256*loaded['baseline'].read8(at+1)
                after = c.read8(at)+256*c.read8(at+1)
                if (before, after) != (patch['old'], patch['new']):
                    raise ValueError(('cold-loaded reference differs', hex(at)))
                checked.append(dict(address=at, before=before, after=after, delta_tstates=0))
            report['cold_references'] = checked
    report['deltas'] = []
    for before, after in zip(report['variants']['baseline']['cases'], report['variants']['fast']['cases'], strict=True):
        for key in ('case', 'tstates', 'excluded_calls', 'phase', 'count', 'position'):
            if before[key] != after[key]: raise ValueError(('queue behavior changed', before['case'], key))
        report['deltas'].append(dict(case=after['case'], baseline_tstates=before['tstates'],
            fast_tstates=after['tstates'], delta_tstates=after['tstates']-before['tstates']))
    report['complete'] = True
    report['source_sha256_lf'] = {n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
        ('measure_fast_zx0_queue.py', 'measure_inplace_streaming_queue.py', 'validate_fast_sparse.py', 'test_fap3_disk.py')}
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report['deltas']), flush=True)


if __name__ == '__main__': main()
