"""Authenticate saved residual diagnostics, inputs and reproducibility reports."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
manifest = json.loads((HERE/'artifact-hashes.json').read_text())
for group, root in (('artifacts', HERE), ('inputs', ROOT)):
    for relative, expected in manifest[group].items():
        path = root/relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (group, relative, actual, expected)
for row in json.loads((HERE/'controls.json').read_text()):
    folder = HERE/'controls'/row['variant']
    replay = json.loads((folder/'replay.json').read_text())
    assert replay['player_verified'] is False
    assert abs(replay['snr_db']-row['snr_db']) < 1e-10
    assert all(abs(replay['bands'][band]-score) < 1e-10 for band, score in row['bands'].items())
    assert len(gzip.decompress((folder/'soundtrack.ima.gz').read_bytes()))*2 == 32896
print(json.dumps(dict(artifacts=len(manifest['artifacts']), inputs=len(manifest['inputs']),
                      controls=7, hashes_exact=True, replay_scores_exact=True,
                      production_player_changed=False, listening_defect_resolved=False)))
