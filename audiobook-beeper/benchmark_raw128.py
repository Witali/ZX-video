"""Cold Fuse timing of 512 real TR-DOS sectors, with a reused 16-KiB buffer.

RAM cannot hold a program plus a separate 128-KiB destination. The benchmark
reads every byte from disk but reuses bank3 as the buffer. It does not imply
128 KiB of audio fits beside the player. Reading uses the same one-sector
ROM call, interrupt policy and track/sector cursor as the audio preloader.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from build_lpc_disk import assemble, disk_address
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files
from smoke_test_fuse import hidden_startupinfo
from verify_pcm import save


def benchmark(out, fuse):
    out.mkdir(parents=True,exist_ok=True)
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "BENCH" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    files=[TrdFile('boot','B',basic,autostart_line=10),TrdFile('BENCH','C',bytes(256),start=0x8000)]
    track,sector=calculate_file_start(files);first=track*16+sector
    asm=f'''        ORG 0x8000
start:  DI
        LD SP,0x6000
        LD IY,0x5C3A
        LD A,19
        LD BC,0x7FFD
        OUT (C),A
        LD DE,{disk_address(first)}
        LD HL,0xC000
        LD BC,512
read_begin:
loop:   PUSH BC
        PUSH DE
        PUSH HL
        LD BC,0x0105
        EI
disk_call:
        CALL 0x3D13
        DI
        POP HL
        POP DE
        POP BC
        INC H
        LD A,H
        OR A
        JR NZ,destination_ready
        LD H,0xC0
destination_ready:
        INC E
        BIT 4,E
        JR Z,sector_ready
        LD E,0
        INC D
sector_ready:
        DEC BC
        LD A,B
        OR C
        JR NZ,loop
read_end:
        JP read_end
        ASSERT $ <= 0x8100
        DS 0x8100-$
'''
    (out/'bench.asm').write_text(asm,encoding='utf-8',newline='\n')
    labels=assemble(out,'bench')
    files[1]=TrdFile('BENCH','C',(out/'bench.bin').read_bytes(),start=0x8000)
    for bank in range(8):
        payload=bytes((i*73+bank*19)&255 for i in range(16384))
        files.append(TrdFile('RAW'+str(bank),'C',payload,start=0xC000))
    disk,_,_=place_files(files,'RAW128');(out/'raw128.trd').write_bytes(disk)
    stamp='spectrum:frames*70908+ula:tstates'
    script=['base 10']
    for i,name in enumerate(('disk_call','read_end'),1):
        script += [f'breakpoint {labels[name]}',f'commands {i}', 'print '+stamp]
        if name=='disk_call':script += ['print z80:de','print z80:hl']
        script += ['exit 77' if name=='read_end' else 'continue','end']
    script='\n'.join(script);(out/'debugger.txt').write_text(script,encoding='utf-8')
    result=subprocess.run([str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command',script,str((out/'raw128.trd').resolve())],
        cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=120)
    (out/'trace.txt').write_bytes(result.stdout);(out/'stderr.txt').write_bytes(result.stderr)
    assert result.returncode==77,(result.returncode,result.stderr[:1000])
    numbers=[int(s,0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:\d+|0x[\da-fA-F]+)',s)]
    assert len(numbers)==512*3+1,len(numbers)
    for i in range(512):
        assert numbers[3*i+1]==disk_address(first+i)
        assert numbers[3*i+2]==0xC000+256*(i%64)
    elapsed=numbers[-1]-numbers[0]
    report=dict(complete=True,bytes_read=131072,sectors_verified=512,tstates=elapsed,
                seconds=elapsed/3546900,maximum_decode_seconds=2*elapsed/3546900,
                timing_scope=__doc__,physical_hardware_tested=False,
                trd_sha256=hashlib.sha256(disk).hexdigest(),fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest())
    save(out/'report.json',report);print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fuse',type=Path,required=True)
    a=p.parse_args();benchmark(a.output,a.fuse)
