"""Apply stronger continuity only to source-weak suspect trajectory events."""
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracking_trials as trials
import grouped_ym3812 as grouped
import coherent_ym3812 as coherent


class LocalizedLattice(grouped.GroupedLattice):
    def __init__(self, *args):
        super().__init__(*args)
        with np.load(HERE / 'beep-evidence/diagnostic-arrays.npz') as saved:
            exposed = saved['exposed'].copy(); frequency = saved['frequency'].copy()
        original = self.original
        assert exposed.shape == (self.count, 9)
        pitch = 12 * np.log2(frequency)
        delta = np.diff(pitch, axis=0)
        bounce = (abs(delta[:-1]) >= 3) & (abs(delta[1:]) >= 3) & (abs(delta[:-1] + delta[1:]) < .5)
        middle = np.zeros_like(exposed); middle[1:-1] = bounce
        weak = (original['level'] >= 20) & (self.confidence[:, :, 0] < .65)
        self.suspect = exposed | (middle & weak)

    def fit(self, **options):
        # Preserve current source-supported pitches and long-window refinement.
        # Neighbor-pitch substitutions are confined to suspect source-weak
        # events; FM shape alternatives remain available for supported groups.
        original_path = coherent.path; channel = [0]
        def localized_path(emission, frequency, levels, confidence, strength):
            index = channel[0]; channel[0] += 1
            protected = ~self.suspect[:, index]
            emission[protected, 1:5] = 1e6
            emission[protected, -1] = 1e6
            return original_path(emission, frequency, levels, confidence, strength)
        coherent.path = localized_path
        try: result, info = super().fit(**options)
        finally: coherent.path = original_path
        info['suspect'] = self.suspect
        return result, info


if __name__ == '__main__':
    trials.coherent.SourceLattice = LocalizedLattice
    trials.opl.smooth_vgm = grouped.export
    trials.PROFILES = [('local04', dict(strength=.004, inactive=True, gate=.01, refit_levels=True, envelopes=True)),
                       ('local08', dict(strength=.008, inactive=True, gate=.02, refit_levels=True, envelopes=True)),
                       ('local02', dict(strength=.002, inactive=True, gate=.01, refit_levels=True))]
    trials.main()
    output = Path(sys.argv[sys.argv.index('--output') + 1]); report = json.loads((output / 'report.json').read_bytes())
    report['grouped_export'] = True
    for p in (Path(__file__), trials.CORE / 'grouped_ym3812.py'):
        report['producer_sources_sha256_lf'][str(p.relative_to(trials.CORE)).replace('\\', '/')] = trials.opl.sha(p.read_bytes().replace(b'\r\n', b'\n'))
    trials.save(output / 'report.json', report)
