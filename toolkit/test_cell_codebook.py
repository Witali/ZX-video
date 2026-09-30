"""Boundary/coverage checks for the experimental exact CB41 host representation."""
import argparse,json
from pathlib import Path
import numpy as np
from build_five_level_test_trd import save
from probe_cell_codebook import changes,encode,decode_check


def put(state,cell,key):
    y,x=divmod(cell,32)
    for row,value in enumerate(key):state[((y+3)*4+row)*32+x]=value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('probe','metadata','states','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();probe=json.loads(a.probe.read_bytes());meta=json.loads(a.metadata.read_bytes())['row_dictionary']
    book=[bytes(row) for row in probe['dictionary_row_keys']];words=meta['words']
    with np.load(a.states,allow_pickle=False) as f:base=f['states'][probe['start']].copy()
    fallback=next(bytes([i,j,i,j]) for i in range(len(words)) for j in range(len(words))
        if bytes([i,j,i,j]) not in book and i!=j)
    outcomes=[]
    def check(name,updates=None,attrs=False,unchanged=False):
        states=np.stack([base.copy() for _ in range(3)])
        if updates:
            for cell,key in enumerate(updates):
                prior=bytes([0])*4 if key!=bytes([0])*4 else bytes([1])*4
                put(states[0],cell,prior);put(states[1],cell,prior);put(states[2],cell,key)
        if attrs:states[2,3072+96:3072+672]^=64  # BRIGHT must survive independently of bitmap data.
        rows=changes(states,2,1)
        if unchanged:assert not rows[0]['changed']
        for label,entries in (('dictionary',book),('literal_control',[])):
            data,_,details=encode(rows,entries,words)
            decode_check(data,states,2,1,words,meta)
            outcomes.append(dict(case=name,variant=label,**details[0]))
            assert details[0]['packet_bytes']<=3096
        return details[0]
    check('unchanged',unchanged=True)
    check('attributes_only',attrs=True,unchanged=True)
    check('every_dictionary_index',book)
    check('all_active_cells_literal_and_attributes',[fallback]*576,attrs=True)
    for count in (1,7,8,9,15,16,17):
        check('mode_mask_boundary_'+str(count),[book[i] if i%2 else fallback for i in range(count)])
    assert next(r for r in outcomes if r['case']=='every_dictionary_index' and r['variant']=='dictionary')['book_cells']==256
    assert next(r for r in outcomes if r['case']=='all_active_cells_literal_and_attributes' and r['variant']=='dictionary')['literal_cells']==576
    result=dict(complete=True,release=False,scope=__doc__,cases=len(outcomes),rows=outcomes,
        every_dictionary_index_used=True,all_active_cells_literal_and_attributes=True,
        maximum_packet_bytes=max(r['packet_bytes'] for r in outcomes),full_host_screens_exact=True)
    save(a.output,result);print(json.dumps({k:v for k,v in result.items() if k not in ('scope','rows')}))


if __name__=='__main__':main()
