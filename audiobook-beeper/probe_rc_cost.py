"""Measure a direct fixed-point feedback term; not a complete player port."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from z80 import Z80Machine

HERE=Path(__file__).resolve().parent


def main():
    work=HERE.parent/'.tmp/rc-feedback-cost'
    work.mkdir(parents=True,exist_ok=True)
    source=(HERE/'rc-feedback-cost.asm').read_text()
    (work/'probe.asm').write_text(source,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=probe.bin',
                           '--lstfile=probe.lst','-s','.*','probe.asm'],cwd=work,
                          capture_output=True,text=True,check=True)
    labels=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
    blob=(work/'probe.bin').read_bytes()
    cases=0
    values=sorted(set(range(-10000,10001,500))|{-9999,-1,1,9999})
    for error in values:
        for older in values:
            machine=Z80Machine()
            machine.set_memory_block(0x8000,blob)
            machine.pc=labels['start'];machine.hl=error&65535;machine.de=older&65535
            machine.set_breakpoint(labels['done']);machine.ticks_to_stop=1000
            while machine.pc!=labels['done']:
                if machine.run()&machine._TICKS_LIMIT_HIT:raise AssertionError('incomplete term')
            if (machine.hl!=((error+(error-older)//2)&65535) or machine.de!=(error&65535)
                    or 1000-machine.ticks_to_stop!=62):
                raise AssertionError('fixed-point value or T-state mismatch')
            cases+=1
    report=dict(date='2026-10-02',scope='one register-only fixed-point term, not a complete RC/PDM port',
                cases=cases,tstates=62,baseline_extrapolation_tstates=0,delta_tstates=62,
                formula='e+floor((e-older)/2)',
                code_bytes_excluding_final_nop=len(blob)-1,
                instruction_tstates=[4,4,4,15,8,8,11,4,4],
                binary_sha256=hashlib.sha256(blob).hexdigest(),
                source_sha256_lf=hashlib.sha256(source.encode()).hexdigest(),
                additional_cpu_fraction_at_47702_626_pdm_hz=62*47702.626/3546900,
                excluded=['RC-state update','bit decision and OUT','IMA decoder','register spills',
                          'table or alternate implementation','ULA and bank boundaries'],
                decision='Direct arithmetic is too expensive for the current live schedule; '
                         'a future Z80 port needs a different representation or lookup tables. '
                         '62 T is a measured implementation cost, not a lower bound on all implementations.')
    (HERE/'rc-pdm-preview/z80-cost.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))


if __name__=='__main__':main()
