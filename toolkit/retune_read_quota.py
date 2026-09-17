"""Retune the existing read-debt immediate, preserving every stream byte."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from validate_streaming_player import extract_file, parse_dir


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--quota',type=int,choices=(3,4,5,6,8),required=True);args=p.parse_args()
    meta=json.loads((args.build/'build_metadata.json').read_text())
    if not meta.get('read_reserve') or not meta.get('uncontended'):
        raise ValueError('requires relocated read-debt player')
    old=(args.build/'PLAYER.C.bin').read_bytes();new=bytearray(old)
    offset=meta['player_labels']['prefetch_loop']-meta['relocation']['runtime_address']+16
    expected=b'\x2a'+struct.pack('<H',meta['player_labels']['read_debt'])+b'\x11'+struct.pack('<H',meta['prefetch_quota'])+b'\x19'
    if old[offset:offset+7]!=expected:raise ValueError('unexpected scheduler instructions')
    struct.pack_into('<H',new,offset+4,args.quota)
    changed=[i for i,(a,b) in enumerate(zip(old,new)) if a!=b]
    if any(i not in (offset+4,offset+5) for i in changed):raise ValueError('unexpected player change')
    args.output.mkdir(parents=True,exist_ok=True)
    for volume in meta['volumes']:
        image=bytearray((args.build/volume['trd_name']).read_bytes())
        entry=next(e for e in parse_dir(image) if e[0]=='PLAYER')
        assert extract_file(image,entry)==old
        location=(entry[3]*16+entry[4])*256
        image[location:location+len(old)]=new
        assert extract_file(image,entry)==new
        (args.output/volume['trd_name']).write_bytes(image)
    meta['read_quota_experiment']=dict(previous_quota=meta['prefetch_quota'],quota=args.quota,
        changed_player_offsets=changed,previous_player_sha256=hashlib.sha256(old).hexdigest(),
        player_sha256=hashlib.sha256(new).hexdigest(),video_bytes_unchanged=True,
        nominal_tstates=dict(previous_unsaturated=115,current_unsaturated=115,
            previous_saturated=114,current_saturated=114,delta=0),
        instruction_timings=[16,10,11,10,11,4,15,10,12,16],
        saturated_branch='JR C not taken: 7 instead of 12; EX DE,HL: +4',
        scope='read-debt addition only; ROM, IRQ, contention, physical disk and branch frequencies excluded')
    meta['prefetch_quota']=args.quota
    (args.output/'PLAYER.C.bin').write_bytes(new)
    (args.output/'build_metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta['read_quota_experiment'],indent=2))


if __name__=='__main__':main()
