"""Native precondition/counterexample checks for the sequential Z80 trick audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
for package in ('zx0','lzsa'):
    sys.path.insert(0,str(ROOT/'libraries'/package/'src'))
from z80 import Z80Machine


def run(code,registers,*,memory=(),prepare=None):
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    m.set_memory_block(0x200,bytes.fromhex(code));m.pc=0x200;m.sp=0xbff0
    for name,value in registers.items():setattr(m,name,value)
    for address,data in memory:m.set_memory_block(address,data)
    if prepare:prepare(m)
    stop=0x200+len(bytes.fromhex(code));m.set_breakpoint(stop);m.ticks_to_stop=100000
    while m.pc!=stop:assert not m.run()&m._TICKS_LIMIT_HIT
    return m,100000-m.ticks_to_stop


def transfers():
    checks=0
    for value in (0,1,0xff,0x100,0x1234,0xffff):
        for flags in range(256):
            registers=dict(hl=value,bc=value^0xffff,af=0x7300|flags)
            old,ot=run('e5 c1',registers);new,nt=run('44 4d',registers)
            assert (old.hl,old.bc,old.af,old.sp)==(new.hl,new.bc,new.af,new.sp)
            assert old.bc==value and (ot,nt)==(21,8);checks+=1
    # Actual decoder save: BC remains a live count while HL becomes history.
    old,_=run('e5 21 ff ff 19 ed a0 e1',dict(hl=0x4000,bc=8,de=0x9000),
        memory=((0x8fff,b'Z'),))
    wrong,_=run('44 4d 21 ff ff 19 ed a0 60 69',dict(hl=0x4000,bc=8,de=0x9000),
        memory=((0x8fff,b'Z'),))
    assert old.hl==0x4000 and old.bc==7 and (wrong.hl,wrong.bc)!=(old.hl,old.bc)
    return dict(item='02',baseline_revision='542b2059',complete=True,decision='already present / no eligible pair transfer',
        primitive_checks=checks,transfer_tstates=dict(before=21,after=8,delta=-13),
        save_counterexample=dict(input=0x4000,count=8,correct_hl=old.hl,correct_bc=old.bc,
            invalid_replacement_hl=wrong.hl,invalid_replacement_bc=wrong.bc),decoder_changes=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--item',required=True,choices=('02',))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=transfers()
    report.update(release=False,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='Native instruction/precondition checks; no new decoder or playback performance claim.',
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            ROOT/'libraries/zx0/src/zx0/banked.py',ROOT/'libraries/zx0/src/zx0/incremental.py',
            ROOT/'libraries/zx0/src/zx0/resumable.py',ROOT/'libraries/lzsa/src/lzsa/resumable.py')})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
