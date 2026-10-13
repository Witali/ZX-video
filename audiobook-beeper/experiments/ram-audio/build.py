"""Rebuild the selected90-second song with adaptive RAM and its actual title."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
BEEPER=HERE.parents[1]
sys.path[:0]=[str(BEEPER),str(BEEPER.parent/'toolkit')]
from audio_cover import prepare,render
from convert_audio import pcm_wav
from direct_player import build_disk,HOLDS
from ima_beam import encode
from probe_reconstruction_error import wav8
from ram_series import build_volume,plan_parts,plan_volumes
from verify_ram_series import verify_series
from verify_pcm import save


def build(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=wav8(args.prepared)
    assert len(source)==720000,'expected the previously selected90-second song'
    identity=dict(prepared_sha256=hashlib.sha256(args.prepared.read_bytes()).hexdigest(),
                  cover_sha256=hashlib.sha256(args.cover.read_bytes()).hexdigest(),
                  producers={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in BEEPER.iterdir() if p.suffix in ('.py','.asm')})
    if (out/'run.json').exists():assert json.loads((out/'run.json').read_bytes())==identity
    else:save(out/'run.json',identity)
    cover=prepare(args.cover);(out/'cover.scr').write_bytes(cover);render(cover).resize((768,576)).save(out/'cover.png')
    parts=plan_parts(len(source));assert plan_volumes(parts)==[list(range(len(parts)))]
    save(out/'parts.json',parts);selected=[]
    for i,part in enumerate(parts):
        path=out/'selected'/f'part-{i+1:02d}';path.mkdir(parents=True,exist_ok=True)
        if not (path/'player.json').exists():
            count=part['stop']-part['start'];pcm=np.full(part['samples'],128,'u1')
            pcm[:count]=source[part['start']:part['stop']]
            fade=min(160,count)
            pcm[count-fade:count]=np.rint(128+(pcm[count-fade:count].astype(float)-128)*np.linspace(1,0,fade)).astype('u1')
            print(json.dumps(dict(stage='encode',part=i+1,total=len(parts))),flush=True)
            packed=encode(pcm,width=32,block_samples=64)
            _,meta=build_disk(packed,path/'assembly',dict(holds=HOLDS,beta=.5,extent=1.))
            pcm_wav(path/'source-preview.wav',pcm)
            (path/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));save(path/'player.json',meta)
        selected.append(path)
    disk,meta=build_volume(selected,out/'volume',bytes.fromhex(identity['prepared_sha256'])[:16],1,1,cover=cover)
    (out/'audio.trd').write_bytes(disk);save(out/'volumes.json',[dict(file='audio.trd',**meta)])
    print(json.dumps(dict(stage='verify-all-four-machines',used_sectors=meta['used_sectors'])),flush=True)
    verified=verify_series(out,args.fuse,args.ffmpeg)
    save(out/'report.json',dict(complete=True,disk_count=1,source_seconds=90,full_selected_song_retained=parts[-1]['stop']==len(source),
        original_preparation_retained=True,legacy_pdm_model=dict(holds=HOLDS,beta=.5,extent=1.),
        trd_sha256=meta['trd_sha256'],verification=verified,preview_only=True,physical_hardware_tested=False))
    print(json.dumps(dict(stage='complete',sha256=meta['trd_sha256'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--cover',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));build(p.parse_args())
