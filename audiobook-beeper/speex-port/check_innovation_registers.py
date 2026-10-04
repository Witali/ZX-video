"""Verify innovation table bytes, guarded writes, register contract and exact builder costs."""
import argparse
import json
import struct
from check_primitives import machine,symbols,call,timing
from make_decoder import array
from verify import ROOT


def energies():
    def q(a,b,k):return a*(b>>k)+((a*(b&((1<<k)-1)))>>k)
    return [q(a,q(28406,g,15),14) for g in array('ol_gain_table') for a in (11546,17224)]


def checked_machine(folder):
    m=machine(folder);s=symbols(folder)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    m.unmark_addrs(0x7c00,132*3,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('builder write',hex(address),value))
    m.set_write_callback(bad)
    m.ix=0x1234;m.iy=0x5678
    return m,s


def sweep(folder):
    m,s=checked_machine(folder);costs=[]
    for energy in energies():
        m.memory[0x7b00:0x7b04]=struct.pack('<i',energy)
        costs.append(call(m,s['_build_innovation'],hl=0x7c00,de=0x7b00))
        assert (m.sp,m.ix,m.iy)==(0xbffe,0x1234,0x5678)
        for i in range(132):
            value=int.from_bytes(m.memory[0x7c00+3*i:0x7c03+3*i],'little',signed=True)
            assert value==((i-65)*energy)//4096,(energy,i,value)
    return costs


def audit_builder(folder):
    m,s=checked_machine(folder)
    m.memory[0x7b00:0x7b04]=struct.pack('<i',energies()[-1])
    m.hl=0x7c00;m.de=0x7b00;m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f'
    m.pc=s['_build_innovation'];total=0;instructions=0;loop=[];done=None
    while m.pc!=0x7f00:
        if m.pc==s.get('_innov_register_loop'):loop.append(total)
        if m.pc==s.get('_innov_register_done'):done=total
        expected=timing(m);before=m.frame_tick;m.ticks_to_stop=1;m.run()
        got=(m.frame_tick-before)%100000;assert got==expected
        total+=got;instructions+=1
    r=dict(tstates=total,instructions=instructions,every_instruction_matches_timing_table=True)
    if loop:
        assert len(loop)==132 and all(b-a==137 for a,b in zip(loop,loop[1:]))
        assert done-loop[-1]==132
        r.update(ordinary_loop_tstates=137,last_loop_tstates=132,iterations=132)
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',default='pure-r20');p.add_argument('--previous',default='pure-r19')
    a=p.parse_args();out=ROOT/'build/speex-port';folder=out/a.variant
    old=sweep(out/a.previous);new=sweep(folder)
    assert len(old)==64 and all(b-a==-28189 for a,b in zip(old,new))
    r=dict(energies=64,exact_entries_per_variant=64*132,previous_tstates=old,selected_tstates=new,
           saving_per_table=28189,previous_audit=audit_builder(out/a.previous),selected_audit=audit_builder(folder),
           sp_ix_iy_preserved=True,all_writes_inside_exact_state_stack_and_table_ranges=True)
    (folder/'innovation-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print({k:v for k,v in r.items() if not k.endswith('_tstates')},flush=True)


if __name__=='__main__':main()
