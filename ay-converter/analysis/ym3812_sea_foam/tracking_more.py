"""Confidence/group ablations after the first trajectory trials fail admission."""
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracking_trials as trials
import grouped_ym3812 as grouped

PROFILES = [('gate20', dict(strength=.004, inactive=True, gate=.02)),
            ('gate20levels', dict(strength=.004, inactive=True, gate=.02, refit_levels=True, envelopes=True)),
            ('group04', dict(strength=.004, inactive=True, gate=.01, refit_levels=True, envelopes=True)),
            ('group01', dict(strength=.001, inactive=True, gate=.004, refit_levels=True))]

if __name__ == '__main__':
    group = '--groups' in sys.argv
    if group:
        sys.argv.remove('--groups')
        trials.coherent.SourceLattice = grouped.GroupedLattice
        trials.opl.smooth_vgm = grouped.export
    trials.PROFILES = [p for p in PROFILES if p[0].startswith('group') == group]
    trials.main()
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    report = json.loads((output / 'report.json').read_bytes())
    report['grouped_export'] = group
    for p in (Path(__file__), trials.CORE / 'grouped_ym3812.py'):
        report['producer_sources_sha256_lf'][str(p.relative_to(trials.CORE)).replace('\\', '/')] = trials.opl.sha(p.read_bytes().replace(b'\r\n', b'\n'))
    trials.save(output / 'report.json', report)
