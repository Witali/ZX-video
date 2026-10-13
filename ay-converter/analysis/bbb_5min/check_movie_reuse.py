"""Authenticate reuse of a complete movie Fuse run after a producer rebuild."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('verified',type=Path);parser.add_argument('rebuilt',type=Path);args=parser.parse_args()
    first=args.verified;current=args.rebuilt
    timing=json.loads((first/'timing.json').read_bytes())
    conversion=json.loads((current/'conversion.json').read_bytes())
    audio=json.loads((current/'audio-quality.json').read_bytes())
    assert timing['complete'] and timing['all_nominal_deadlines_met'] and conversion['complete']
    assert conversion['audio_wire']=='AYH2' and audio['chip_fit']['register_bytes_per_state']==14
    assert conversion['frames']==5 and conversion['ay_ticks']==25
    proofs=[];saved=first/'producer-rebuild';saved.mkdir(exist_ok=True)
    for volume in conversion['volumes']:
        name=volume['file'];data=(current/name).read_bytes()
        assert data==(first/name).read_bytes()
        measured=next(d for d in timing['disks'] if d['file']==name)
        assert measured['full_fuse_screens_exact'] and measured['disk_timing']['actual_ay_50hz']
        assert measured['disk_timing']['nominal_deadlines_met'] and not measured['disk_timing']['missed_nominal_frames']
        folder=current/'work'/Path(name).stem
        cpu=json.loads((folder/'cpu.json').read_bytes())
        assert cpu['complete'] and cpu['all_native_screens_exact']
        shutil.copyfile(folder/'cpu.json',saved/f'{Path(name).stem}-cpu.json')
        proofs.append(dict(file=name,sha256=hashlib.sha256(data).hexdigest(),identical_disk=True,
            current_native_complete=True,reused_complete_cold_fuse=True))
    for name in ('conversion.json','audio-quality.json','timing.json'):
        shutil.copyfile(current/name,saved/name)
    result=dict(complete=True,scope='Exact disk identity authenticates the earlier complete cold Fuse run; no new waveform or disk proof is inferred from metadata alone.',
        frames=5,ay_ticks=25,hardware_envelope=True,disks=proofs)
    (first/'verified-producer-rebuild.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__=='__main__':main()
