"""Independent instruction-table fixture, including prefixes, repeat and idle HALT."""
from collections import Counter
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

ap=argparse.ArgumentParser()
ap.add_argument('--core', required=True)
ap.add_argument('--system', required=True)
ap.add_argument('--out', type=Path, required=True)
args=ap.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
header=bytearray(27)
struct.pack_into('<H',header,23,0xfffc)
header[25]=1
ram=bytearray(49152)
struct.pack_into('<H',ram,0xfffc-0x4000,0x9000)
code=bytes.fromhex('f3 21 00 40 06 02 7e 23 10 fc 11 00 b0 01 03 00 ed b0 dd 21 00 c0 dd 34 00 dd 00 cb 07 3e 00 20 00')
timings=[4,10,7,7,6,13,7,6,8,10,10,21,21,16,14,23,8,8,7,7]
# Four separately entered 256-iteration loops; cross active display time.
for _ in range(4):
    code+=bytes.fromhex('06 00 7e 10 fd')
    timings += [7] + [7,13]*255 + [7,8]
code+=b'\x76'
timings+=[4]
ram[0x5000:0x5000+len(code)]=code
expected=Counter(timings)
results=[]
for label,address in [('contended',0x4000),('uncontended',0xa000)]:
    ram[0x5002:0x5004]=struct.pack('<H',address)
    snapshot=args.out/(label+'.sna')
    snapshot.write_bytes(header+ram)
    out=args.out/label
    subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),
        '--core',args.core,'--system',args.system,'--disk',str(snapshot),
        '--out',str(out),'--model','Spectrum 48K','--frames','5','--window','5'],check=True)
    data=json.loads((out/'raw.json').read_text())
    row=data['windows'][0]
    got=row['groups']['ram']
    assert got['instructions']==len(timings), (got,len(timings))
    assert got['base_t']==sum(timings), (got,sum(timings))
    assert got['histogram']=={str(t):n for t,n in expected.items()},got['histogram']
    assert got['halts']==1 and got['idle_m1']>0
    assert got['repeated_block_continuations']==2
    assert row['unattributed_t']==0,row
    assert (got['elapsed_t']>got['base_t']) == (label=='contended')
    results.append(dict(model=data['machine'],data_address=address,instructions=got['instructions'],
        base_t=got['base_t'],elapsed_t=got['elapsed_t'],idle_t=got['idle_t'],
        histogram=got['histogram'],passed=True))
(args.out/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS',results,flush=True)
