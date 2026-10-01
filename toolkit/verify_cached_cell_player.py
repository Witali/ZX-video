"""Run guarded native playback of an existing cell-player TRD without rebuilding."""
import argparse
import json
from pathlib import Path
import numpy as np

from build_cell_codebook_trd import verify
from build_fap3_trd import sha
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','trd','states','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.metadata.read_bytes());image=a.trd.read_bytes()
    assert sha(image)==m['trd_sha256']
    with np.load(a.states,allow_pickle=False) as saved:states=saved['states']
    assert sha(states.tobytes())==m['states_sha256']
    result=verify(image,m,states)
    result.update(trd_sha256=sha(image),metadata_sha256=sha(a.metadata.read_bytes()))
    write_json(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','histogram')}))


if __name__=='__main__':main()
