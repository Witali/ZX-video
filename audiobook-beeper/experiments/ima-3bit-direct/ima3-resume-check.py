import hashlib,json
from pathlib import Path
from convert_ima3_audio import stage
p=Path('.tmp/ima3-resume-corruption-fixture');p.mkdir(exist_ok=True)
(p/'report.json').write_text('{}')
(p/'stage-complete.json').write_text(json.dumps({'report.json':hashlib.sha256(b'original').hexdigest()}))
try:stage(p,lambda _: (_ for _ in ()).throw(AssertionError('must not execute')))
except ValueError as e:
    assert 'cached stage artifact changed' in str(e)
    r=dict(complete=True,modified_artifact_rejected=True,encoder_not_invoked=True,completed_stages_reused=3,resume_trace='.tmp/ima3-automatic-resume.txt')
    Path('.tmp/ima3-automatic-resume-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
else:raise AssertionError('modified cache accepted')
