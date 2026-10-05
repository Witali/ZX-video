"""Prepare an independent later part with the running public conversion's settings.

Only host scheduling differs. Adoption requires unchanged source, tools,
producer hashes and complete stage checks; the final disk is still verified
by the public series converter. Uses installed native Fuse (independent stdout).
"""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from convert_audio import convert, pcm_wav
from convert_ima3_audio import stage, digest
from ima4_series import plan_parts
from verify_pcm import save

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('number', type=int)
p.add_argument('--base', type=Path, required=True)
p.add_argument('--ffmpeg', required=True)
p.add_argument('--fuse', type=Path, required=True)
a = p.parse_args()
base = a.base.resolve()
workspace = Path.cwd().resolve()
assert base.is_relative_to(workspace/'build')
identity = json.loads((base/'run.json').read_bytes())
track = json.loads((base/'track.json').read_bytes())
producer = Path('audiobook-beeper')
assert identity['codec']=='ima4' and identity['dynamics']=='gentle'
assert all(digest(producer/name)==value for name,value in identity['producers'].items())
assert digest(base/'track.f32')==track['sha256']
assert digest(Path(a.ffmpeg))==identity['ffmpeg_sha256'] and digest(a.fuse)==identity['fuse_sha256']
part = plan_parts(track['samples'])[a.number-1]
values = np.memmap(base/'track.f32', dtype='<f4', mode='r')
samples = values[part['start']:part['stop']].astype(float)*track['gain']
del values
fade = min(80,len(samples)//2)
samples[:fade] *= np.linspace(0,1,fade)
samples[-fade:] *= np.linspace(1,0,fade)
pcm = np.full(part['samples'],128,dtype='u1')
pcm[:len(samples)] = np.clip(np.rint(samples*128+128),0,255).astype('u1')
input_path = base/'work'/f'input-{a.number:05d}.wav'
pcm_wav(input_path,pcm)
out = base.with_name(base.name+'-precompute')/f'part-{a.number:05d}'
options = SimpleNamespace(input=input_path,output=out,ffmpeg=a.ffmpeg,fuse=a.fuse,codec='ima4',
    disk_mode=None,prepared_pcm=True,duration=None,dynamics=identity['dynamics'],
    quality=identity['quality'],target_snr=identity['target_snr'],attempts=identity['attempts'],
    iterations=identity['iterations'],refine_clock=identity['refine_clock'],
    no_recording=identity['no_recording'],resume=False)
result = stage(out,lambda _:convert(options))
assert all(digest(producer/name)==value for name,value in identity['producers'].items())
assert json.loads((base/'run.json').read_bytes())==identity
target = base/'work'/out.name
assert out.is_relative_to(workspace/'build') and target.is_relative_to(base/'work')
adopted = False
if not target.exists():
    try:
        out.rename(target)
        adopted = True
    except FileExistsError:
        pass  # The serial driver won; retain this independently completed result.
save(base/f'precompute-{a.number:05d}.json',dict(part=a.number,plan=part,
    source_sha256=digest(input_path),run_identity_sha256=digest(base/'run.json'),adopted=adopted,
    output=str(target if adopted else out),same_public_converter=True,
    helper_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
    quality_gate_passed=result['quality_gate_passed']))
print(json.dumps(dict(precomputed_part=a.number,adopted=adopted)),flush=True)
