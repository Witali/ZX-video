"""Guard an additional fixed-RAM candidate during complete native playback."""
import argparse
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from build_cell_codebook_trd import verify
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','trd','states','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--start',type=lambda n:int(n,0),default=0xb100)
    p.add_argument('--end',type=lambda n:int(n,0),default=0xb700)
    a=p.parse_args();m=json.loads(a.metadata.read_bytes());image=a.trd.read_bytes()
    if not 0x8000<=a.start<a.end<=0xc000:p.error('guard must be within fixed bank 2')
    assert sha(image)==m['trd_sha256']
    with np.load(a.states,allow_pickle=False) as saved:states=saved['states']
    assert sha(states.tobytes())==m['states_sha256']
    m['cell_codebook']['obsolete_fixed_ranges'].append(dict(start=a.start,end=a.end,reason='proposed fixed-RAM allocation'))
    result=verify(image,m,states)
    result.update(trd_sha256=sha(image),metadata_sha256=sha(a.metadata.read_bytes()),
        extra_guard=[a.start,a.end],scope=f'Unmodified existing TRD; extra native read/write/fetch guard for {a.start:04X}h..{a.end:04X}h')
    write_json(a.output,result)
    print(json.dumps(dict(complete=result['complete'],frames=result['frames_checked'],guards=result['retired_ranges_guarded'])))


if __name__=='__main__':main()
