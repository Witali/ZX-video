"""Find globally constant attribute cells before considering fewer screen writes.

Read-only profile, no player or encoding change. The compact frame is 3072
bitmap bytes followed by 768 Spectrum attributes. Both native screen banks
would need explicit initialization for any nonzero constants skipped later.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840 or not len(states):
        raise ValueError('expected nonempty 3840-byte compact frames')
    attrs = states[:,3072:]
    constant = np.all(attrs == attrs[0],axis=0)
    runs = []
    for i in range(768):
        same = bool(constant[i])
        if runs and runs[-1]['constant'] == same: runs[-1]['length'] += 1
        else: runs.append(dict(first=i,length=1,constant=same))
    rows = [dict(index=i,changed_from_previous=int(np.count_nonzero(attrs[i] != attrs[i-1])) if i else 768,
        changed_from_same_screen=int(np.count_nonzero(attrs[i] != attrs[i-2])) if i > 1 else 768)
        for i in range(len(states))]
    result = dict(scope=__doc__,complete=True,release=False,player_changed=False,player_delta_tstates=0,
        frames=len(states),states_sha256=sha(states.tobytes()),
        attribute_value_counts=dict(sorted(Counter(int(v) for v in attrs.ravel()).items())),
        globally_constant_cells=int(np.count_nonzero(constant)),
        constant_cell_value_counts=dict(sorted(Counter(int(v) for v in attrs[0,constant]).items())),
        constant_top_two_rows=bool(np.all(constant[:64])),
        constant_bottom_two_rows=bool(np.all(constant[-64:])),runs=runs,frames_detail=rows)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'frames_detail'},indent=2))


if __name__ == '__main__': main()
