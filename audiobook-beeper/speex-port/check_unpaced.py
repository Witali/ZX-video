"""Audit exact unpaced throughput, register-table construction and full random packets."""
import argparse
import json
import struct
import subprocess
import sys
from check_primitives import machine,symbols,timing,audit,primitives,call
from check_streams import control_cases
from verify import native,ROOT,HERE,image,sha


def preparation_audit(folder):
    """Step the entire builder with independent instruction timings and write guards."""
    m=machine(folder);s=symbols(folder)
    coefficients=[-32768,-32767,-8192,-257,-1,0,1,255,8192,32767]
    m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*coefficients)
    m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f'
    m.ix=0x1234;m.iy=0x5678;m.pc=s['_prepare_coefficients']
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(s['s__DATA'],s['l__DATA'],m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    m.unmark_addrs(0x7200,2560,m.WRITE_MARK)
    def forbidden(address,value):raise AssertionError(('builder write',address,value))
    m.set_write_callback(forbidden)
    total=0;count=0
    while m.pc!=0x7f00:
        expected=timing(m);before=m.frame_tick
        m.ticks_to_stop=1;m.run()
        actual=(m.frame_tick-before)%100000
        assert actual==expected,(hex(m.pc),actual,expected)
        total+=actual;count+=1
    assert (m.sp,m.ix,m.iy)==(0xbffe,0x1234,0x5678)
    for tap,coefficient in enumerate(coefficients):
        for part in range(4):
            for nibble in range(16):
                digit=nibble-16 if part==3 and nibble>=8 else nibble
                address=0x7200+256*tap+64*part+4*nibble
                assert int.from_bytes(m.memory[address:address+4],'little')==(coefficient*digit<<(4*part))&0xffffffff
    return dict(tstates=total,instructions=count,table_entries=640,
                caller_sp_ix_iy_preserved=True,every_instruction_matches_timing_table=True,
                writes_guarded=True)


def product_costs(folder):
    m=machine(folder);s=symbols(folder)
    values=[-32768,-32767,-8192,-257,-1,0,1,255,8192,32767]
    m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=struct.pack('<10h',*values)
    call(m,s['_prepare_coefficients'],budget=1000000)
    split_cost=set();product_cost=set()
    for x in values:
        split_cost.add(call(m,s['_split_nibbles'],hl=x&65535))
        for tap,coefficient in enumerate(values):
            product_cost.add(call(m,s['_coefficient_product'],a=0x72+tap))
            assert (m.hl<<16|m.de)==(x*coefficient)&0xffffffff
    return dict(exact_products=100,split_tstates=sorted(split_cost),product_tstates=sorted(product_cost))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',required=True);p.add_argument('--previous',required=True)
    p.add_argument('--check-default',action='store_true')
    a=p.parse_args();out=ROOT/'build/speex-port';folder=out/a.variant
    r=json.loads((folder/'report.json').read_text())
    baseline=json.loads((out/a.previous/'report.json').read_text())
    extra=dict(preparation=preparation_audit(folder),previous_preparation=preparation_audit(out/a.previous),
               products=product_costs(folder),previous_products=product_costs(out/a.previous),
               controls=control_cases(folder),general_primitives=primitives(folder))
    random=out/'checks/random-packets'
    extra['random_packets']=native(random,a.variant,folder)
    extra['random_packets'].pop('out_intervals_histogram',None)
    silence=out/'checks/silence'
    extra['cached_silence_audit']=audit(folder,(silence/'input.spxraw').read_bytes(),
                                       (silence/'reference.pcm16').read_bytes(),frames=2)
    extra['total_tstates']=r['total_tstates']
    extra['delta_tstates']=r['total_tstates']-baseline['total_tstates']
    extra['average_budget_tstates']=437.5
    extra['mean_budget_multiple']=r['mean_total_tstates_per_sample']/437.5
    extra['sustained_cpu_real_time']=r['total_tstates']<=r['samples']*437.5
    extra['uniform_sample_deadlines_required']=False
    extra['baseline']=a.previous
    mem=image(folder/'player.ihx');extra['binary_sha256']=sha(bytes(mem[k] for k in sorted(mem)))
    assert r['binary_sha256']==extra['binary_sha256']
    checks=json.loads((folder/'checks.json').read_text())
    streams=[r,*checks['fixtures'].values(),extra['random_packets']]
    assert all(x['complete'] and x['every_pcm8_exact'] and x['every_pcm16_exact']
               and x['binary_sha256']==extra['binary_sha256'] for x in streams)
    extra['exact_samples_verified']=sum(x['samples'] for x in streams)
    if a.check_default:
        fresh=out/'unpaced-default-rebuild'
        subprocess.run([sys.executable,str(HERE/'build.py'),'--skip-host','--output',str(fresh)],check=True)
        rebuilt=image(fresh/a.variant/'player.ihx')
        digest=sha(bytes(rebuilt[k] for k in sorted(rebuilt)))
        assert digest==extra['binary_sha256']
        extra['fresh_default_build_sha256']=digest
    (folder/'unpaced-checks.json').write_text(json.dumps(extra,indent=2)+'\n')
    print({k:v for k,v in extra.items() if k not in ('general_primitives','random_packets')},flush=True)


if __name__=='__main__':main()
