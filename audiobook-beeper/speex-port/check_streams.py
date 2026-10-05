"""Exercise official mode-3 encodings and reject unsupported input on the Z80."""
import argparse
import json
import math
from pathlib import Path
import random
import wave

from check_primitives import machine, symbols
from verify import host_fixture, native, ROOT


def control_cases(folder):
    s=symbols(folder)
    results=[]
    for count,first_byte,want in ((0,0,0),(1,0,1),(1,0x98,1),(4916,0,2),(65535,0,2)):
        m=machine(folder);m.clear_breakpoint(0x7f00)
        m.set_breakpoint(s['_complete'])
        m.memory[s['_packet_count']:s['_packet_count']+2]=count.to_bytes(2,'little')
        m.memory[0xc000:0xc014]=bytes([first_byte])+bytes(19)
        ports=[]
        m.set_output_callback(lambda port,value:ports.append((port,value)))
        m.pc=s['_entry'];m.ticks_to_stop=100000
        while m.pc!=s['_complete']:
            assert not(m.run()&m._TICKS_LIMIT_HIT),'control timeout'
        assert int.from_bytes(m.memory[s['_status']:s['_status']+2],'little')==want
        assert all(port==0x7ffd for port,value in ports),'invalid input produced PCM'
        if want==2:assert not ports,'oversized input paged RAM'
        results.append(dict(packet_count=count,first_byte=first_byte,status=want,pcm_outputs=0))
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/speex-port')
    p.add_argument('--variant',default='pure-r40')
    a=p.parse_args();out=a.output.resolve();n=3200;rng=random.Random(711)
    cases={
        'silence':bytes([128])*n,
        'impulses':bytes(255 if i%211==0 else 0 if i%337==0 else 128 for i in range(n)),
        'low-tone':bytes(round(128+110*math.sin(2*math.pi*125*i/8000)) for i in range(n)),
        'high-tone':bytes(round(128+110*math.sin(2*math.pi*3371*i/8000)) for i in range(n)),
        'noise':bytes(rng.randrange(256) for _ in range(n)),
        'level-jumps':bytes(([0,255,128,180,76][(i//160)%5]) for i in range(n)),
        'six-bank-capacity':bytes([128])*(4915*160),
    }
    results={}
    for name,pcm in cases.items():
        target=out/'checks'/name;target.mkdir(parents=True,exist_ok=True)
        wav=target/'source.wav'
        with wave.open(str(wav),'wb') as w:
            w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(pcm)
        host=host_fixture(target,wav,out/'host')
        z80=native(target,a.variant,out/a.variant)
        results[name]=dict(host=host,z80={k:v for k,v in z80.items() if k!='out_intervals_histogram'})
    results['control_cases']=control_cases(out/a.variant)
    (out/'stream-checks.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Seven complete streams and five control cases passed.',flush=True)


if __name__=='__main__':main()
