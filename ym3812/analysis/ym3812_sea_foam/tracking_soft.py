"""Reduce measured low-frequency modulation side effects with softer FM groups."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracking_local as local
import tracking_trials as trials
import grouped_ym3812 as grouped


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mod-tl', type=int, choices=(48, 52), required=True)
    args, other = parser.parse_known_args()
    sys.argv = [sys.argv[0], *other]
    trials.opl.PATCHES[7]['mod_tl'] = args.mod_tl
    trials.opl.PATCHES[21]['mod_tl'] = args.mod_tl
    trials.opl.dictionary.cache_clear()
    trials.coherent.SourceLattice = local.LocalizedLattice
    trials.opl.smooth_vgm = grouped.export
    trials.PROFILES = [(f'soft{args.mod_tl}', dict(strength=.004, inactive=True, gate=.01, refit_levels=True, envelopes=True))]
    trials.main()
    output = Path(sys.argv[sys.argv.index('--output') + 1]); report = json.loads((output / 'report.json').read_bytes())
    report['grouped_export'] = True; report['modulator_tl'] = args.mod_tl
    for p in (Path(__file__), HERE / 'tracking_local.py', trials.CORE / 'grouped_ym3812.py'):
        report['producer_sources_sha256_lf'][str(p.relative_to(trials.CORE)).replace('\\', '/')] = trials.opl.sha(p.read_bytes().replace(b'\r\n', b'\n'))
    trials.save(output / 'report.json', report)
