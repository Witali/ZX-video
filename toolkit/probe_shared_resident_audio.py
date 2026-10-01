"""Measure one exact AYH1 model per volume against duplicated AYB1 trees.

Host sizing only. No bank-spanning native reader or timing claim.
"""
import argparse
import json
from pathlib import Path

import ay_huffman_stream as wire
import banked_resident_audio as banked
import resident_audio_z80 as resident
from build_fap3_trd import sha
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();rows=[]
    for path in a.input:
        raw=path.read_bytes();initial,records=banked.decode(raw)
        data,_=wire.encode(records,initial)
        assert wire.decode(data)==(initial,records)
        _,_,trees,payload=resident.tables(data)
        roots,nodes=resident.tree_bytes(trees,0x1000)
        old=[]
        for part in banked.segments(raw):
            _,_,t,bits=resident.tables(part);r,n=resident.tree_bytes(t,0x1000)
            old.append(dict(tree_bytes=len(r+n),payload_bytes=len(bits)))
        rows.append(dict(input=path.name,input_sha256=sha(raw),ticks=len(records),records_exact=True,
            previous_wire_bytes=len(raw),wire_bytes=len(data),tree_bytes=len(roots+nodes),
            payload_bytes=len(payload),payload_above_16k=max(0,len(payload)-16384),old_segments=old,
            previous_tree_payload_bytes=sum(v['tree_bytes']+v['payload_bytes'] for v in old),
            tree_payload_bytes=len(roots+nodes+payload),
            native_code_reserved_bytes=512,estimated_fixed_requirement=512+len(roots+nodes)))
    result=dict(complete=True,release=False,scope=__doc__,parts=rows,
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    write_json(a.output,result);print(json.dumps(result))


if __name__=='__main__':main()
