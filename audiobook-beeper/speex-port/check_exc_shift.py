"""Execute the signed24 shift block across all low words and every sign/top byte."""
import argparse
import json
from check_primitives import machine,symbols,timing
from verify import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',default='pure-r19')
    a=p.parse_args();folder=ROOT/'build/speex-port'/a.variant;m=machine(folder);s=symbols(folder)
    m.set_breakpoint(s['_exc_shift_end'])
    # Every discarded-bit pattern and word boundary for the largest magnitudes,
    # plus every high byte with boundaries around 128/256 and signed16 clipping.
    pairs=[(top,word) for top in (0,1,0x7f,0x80,0xfe,0xff) for word in range(65536)]
    pairs += [(top,word) for top in range(256) for word in (0,1,63,64,65,127,128,129,255,256,32767,32768,65534,65535)]
    for top,word in pairs:
        m.pc=s['_exc_shift_start'];m.hl=0xa500|top;m.de=word;m.ticks_to_stop=1000
        while m.pc!=s['_exc_shift_end']:assert not(m.run()&m._TICKS_LIMIT_HIT)
        x=(top<<16)|word
        if top&128:x-=1<<24
        assert (m.hl<<16|m.de)==(x>>7)&0xffffffff,(top,word,m.hl,m.de)
        assert 1000-m.ticks_to_stop==52
    m.pc=s['_exc_shift_start'];m.hl=0x80;m.de=0xffff;audited=0;instructions=0
    while m.pc!=s['_exc_shift_end']:
        want=timing(m);before=m.frame_tick;m.ticks_to_stop=1;m.run()
        got=(m.frame_tick-before)%100000;assert got==want
        audited+=got;instructions+=1
    assert audited==52
    r=dict(exact_signed24_cases=len(pairs),block_tstates=52,previous_block_tstates=184,
           delta_tstates=-132,audited_instructions=instructions,all_instruction_counts_match=True,
           all_high_bytes_and_discarded_low_bit_patterns_covered=True)
    (folder/'shift-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(r)


if __name__=='__main__':main()
