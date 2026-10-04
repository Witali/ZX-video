import sys,json
from pathlib import Path
import ima_waveform_encoder as module
original=module.encode_waveform
def extended(*args,**kwargs):
    kwargs['block_size']=128
    return original(*args,**kwargs)
module.encode_waveform=extended
sys.argv=['ima_waveform_encoder.py','--input','.tmp/ima3-automatic-full/pilot','--output','.tmp/ima3-direct-lookahead128','--ima3','--width','256','--regularization','0.03','--ffmpeg','C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/bin/ffmpeg.exe']
module.main()
p=Path('.tmp/ima3-direct-lookahead128/report.json');r=json.loads(p.read_bytes());r['block_size']=128;r['scope']+=' Longer 128-sample beam horizon; host-only probe.';p.write_text(json.dumps(r,indent=2))
