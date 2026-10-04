"""Additional final checks: LPC equivalence, random mode-3 packets and controls."""
import argparse
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import random
import struct
from check_primitives import machine,symbols,call,audit
from save_evidence import copy
from check_streams import control_cases
from verify import native,ROOT


def lpc_checks(out):
    folders=[out/v for v in ('pure-r3','pure-r4')]
    machines=[machine(p) for p in folders];maps=[symbols(p) for p in folders]
    rng=random.Random(711)
    cases=[[0]*10,[25736]*10,[16,25720]*5,list(range(16,160+16,16))]
    cases += [sorted(rng.sample(range(16,25721),10)) for _ in range(1000)]
    cases += [[rng.randrange(25737) for _ in range(10)] for _ in range(100)]
    for values in cases:
        outputs=[]
        for m,s in zip(machines,maps):
            m.memory[s['interp']:s['interp']+20]=struct.pack('<10h',*values)
            call(m,s['_zx_speex_lpc'],budget=1000000)
            outputs.append(bytes(m.memory[s['next_lpc']:s['next_lpc']+20]))
        assert outputs[0]==outputs[1],('LPC',values,outputs)
    return dict(cases=len(cases),all_ten_coefficients_exact=True,
                comparison='Verified round03 polynomial implementation versus compact round04')


def random_packets(out):
    rng=random.Random(711);ref=C.CDLL(str(out/'host/reference.dll'));oracle=C.CDLL(str(out/'host/decoder.dll'))
    ref.reference_reset();oracle.zx_speex_reset();packed=bytearray();pcm=bytearray()
    for frame in range(512):
        packet=bytearray(rng.randrange(256) for _ in range(20));packet[0]=(packet[0]&7)|0x18
        src=(C.c_char*20).from_buffer_copy(packet);a=(C.c_short*160)();b=(C.c_short*160)()
        assert ref.reference_decode(src,a)==0 and oracle.zx_speex_decode(src,b)==0
        assert bytes(a)==bytes(b),('upstream versus host oracle',frame)
        packed.extend(packet);pcm.extend(bytes(a))
    target=out/'checks/random-packets';target.mkdir(exist_ok=True)
    (target/'input.spxraw').write_bytes(packed);(target/'reference.pcm16').write_bytes(pcm)
    report=native(target,'pure-r4',out/'pure-r4');report.pop('out_intervals_histogram',None)
    report.update(payload_sha256=hashlib.sha256(packed).hexdigest(),reference_pcm16_sha256=hashlib.sha256(pcm).hexdigest())
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/speex-port');a=p.parse_args()
    out=a.output.resolve()
    report=dict(lpc=lpc_checks(out),random_packets=random_packets(out),controls=control_cases(out/'pure-r4'))
    silent=out/'checks/silence'
    report['cached_silence_instruction_audit']=audit(out/'pure-r4',(silent/'input.spxraw').read_bytes(),(silent/'reference.pcm16').read_bytes(),frames=2)
    target=ROOT/'audiobook-beeper/speex-port/rounds/05';target.mkdir(exist_ok=True)
    (target/'checks.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    copy(out/'pure-r4'/'report.json',target/'speech-report.json')
    copy(out/'pure-r4'/'out-times.u64.gz',target/'speech-out-times.u64.gz')
    for name in ('input.spxraw','reference.pcm16'):
        (target/('random-'+name+'.gz')).write_bytes(gzip.compress((out/'checks/random-packets'/name).read_bytes(),mtime=0))
    print('Final LPC, random-packet and control checks passed.',report['lpc'])


if __name__=='__main__':main()
