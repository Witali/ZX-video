"""Package the standalone compact packet-PDM assembler player into a TRD."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import wave

import numpy as np

from feedback_player import loading_screen
from ima_beam import encode
from ima_codec import decode, decoder_table, require_unclipped
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files
from probe_feedback_packets import integral_table
from verify_pcm import save

HERE = Path(__file__).resolve().parent
HOLDS = [36,28,28,31,27,23,23,16,31,23,27,28,33,30,35,49]


def layout():
    words, successors, _ = integral_table(64, 2, holds=HOLDS)
    first_patterns = sorted(set(map(int, (words >> 8).ravel())))
    second_patterns = sorted(set(map(int, (words & 255).ravel())))
    first = {p: 0x8400 + i*40 for i,p in enumerate(first_patterns)}
    second_base = 0x8400 + len(first)*40
    second = {p: second_base+i*72 for i,p in enumerate(second_patterns)}
    pointers = (second_base+len(second)*72+255)&~255
    reserve = pointers+1024-0x8000
    assert reserve < 16384
    # B is the high byte of OUT (C),D/0. Exclude the contended 40..7F range.
    ids = dict(zip(second_patterns, list(range(64))+list(range(128,256))))
    assert len(ids)==len(second)
    sections = [dict(bank=b,address=0xc000,bytes=16384,sectors=64) for b in (0,4,6,1,3)]
    sections += [dict(bank=7,address=0xdb00,bytes=9472,sectors=37),
                 dict(bank=2,address=0xc000+reserve,bytes=16384-reserve,sectors=(16384-reserve)//256)]
    return words,successors,first,second,ids,pointers,reserve,sections


def build_disk(packed, work):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    words,successors,first,second,ids,pointers,reserve,sections=layout()
    assert len(packed)==sum(s['bytes'] for s in sections)
    guard=require_unclipped(packed)
    pcm,indices=decode(packed)
    assert (pcm[-1],indices[-1])==(0,0), 'loop must return to the initial IMA state'
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
                   basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
                   basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(23296),start=0x8000)])
    pos=track*16+sector
    decoder_sector=pos;pos+=23
    packet_sector=pos;pos+=32
    for s in sections:s['sector']=pos;pos+=s['sectors']
    constants=dict(first_base=0x8400,second_high=pointers,pcm_low=pointers+512,
                   resident_reserve=reserve,decoder_disk=decoder_sector//16*256+decoder_sector%16,
                   packet_disk=packet_sector//16*256+packet_sector%16)
    for i in range(256):
        constants[f'first_address_{i}']=first.get(i,-1)
        constants[f'second_address_{i}']=second.get(i,-1)
    for i,s in enumerate(sections):
        constants.update({f'disk_{i}':s['sector']//16*256+s['sector']%16,
                          f'address_{i}':s['address'],f'sectors_{i}':s['sectors']})
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in constants.items()))
    second_ptr=[0]*256
    for p,address in second.items():second_ptr[ids[p]]=address
    for name,data in [('second-high',bytes(a>>8 for a in second_ptr)),
                      ('second-low',bytes(a&255 for a in second_ptr)),
                      ('pcm-low',bytes((x&4)<<5 for x in range(256))),
                      ('pcm-high',bytes(0x60+(x>>3) for x in range(256))),
                      ('screen',loading_screen(len(packed)*2,'IMA / PACKET PDM'))]:
        (work/(name+'.bin')).write_bytes(data)
    table=bytearray()
    for value in range(64):
        for state in range(32):
            word=int(words[value,state])
            table+=struct.pack('<HBB',first[word>>8],int(successors[value,state])*4,ids[word&255])
    decoder=decoder_table(0x4000,False)
    (work/'decoder-table.bin').write_bytes(decoder);(work/'packet-table.bin').write_bytes(table)
    (work/'player.asm').write_bytes((HERE/'packet-player.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],
                       cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    blob=(work/'player.bin').read_bytes();assert len(blob)==23296
    files=[boot,TrdFile('PLAYER','C',blob,start=0x8000),TrdFile('DECODER','C',decoder,start=0x4000),
           TrdFile('PACKETS','C',bytes(table),start=0x6000)]
    offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+s['bytes']],start=s['address']))
        offset+=s['bytes']
    disk,directory,capacity=place_files(files,'IMAPACK')
    meta=dict(origin=0x8000,player_labels=labels,sections=sections,directory=directory,capacity=capacity,
              first_addresses=list(first.values()),second_addresses=list(second.values()),
              first_patterns=len(first),second_patterns=len(second),resident_reserve=reserve,
              pcm_samples=len(packed)*2,packed_bytes=len(packed),table_base=0x4000,packet_base=0x6000,
              source_sample_rate_hz=8000,cpu_clock_hz=3546900,ordinary_holds_tstates=HOLDS,
              ordinary_tstates=sum(HOLDS),page_extra_tstates=18,bank_extra_tstates=131,
              baseline_feedback_tstates=433.25,ordinary_delta_tstates=sum(HOLDS)-433.25,
              repeat=True,initial_predictor=0,initial_index=0,initial_feedback=16,paging_base=24,
              record_stop_addresses=[a+2 for a in first.values()],
              loop_terminal_predictor=int(pcm[-1]),loop_terminal_index=int(indices[-1]),
              saturation_guard=guard,packed_sha256=hashlib.sha256(packed).hexdigest(),
              binary_sha256=hashlib.sha256(blob).hexdigest(),
              mutable_addresses=[labels['bank_jump']+1,labels['bank_jump']+2],
              loading_message=dict(text='Loading audio data',attribute_address=0xd800,attribute_bytes=96),
              memory=dict(total_ram_bytes=131072,adpcm_bytes=len(packed),shadow_screen_bytes=6912,
                          bank5_tables_and_workspace_bytes=16384,bank2_resident_bytes=reserve,
                          pcm_buffer_bytes=0,pdm_buffer_bytes=0),
              assembly=dict(instruction_bytes_emitted_by_python=False,assembler='pyz80 1.3.0'))
    assert len(packed)+6912+16384+reserve==131072
    return disk,meta


def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    n=sum(s['bytes'] for s in layout()[-1])*2
    with wave.open(str(HERE/'experiments/ima-feedback64/source-preview.wav'),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,8000)
        pcm=np.frombuffer(w.readframes(n),'u1').copy()
    pcm[-288:-128]=np.rint(128+(pcm[-288:-128].astype(float)-128)*np.linspace(1,0,160)).astype('u1')
    pcm[-128:]=128
    packed=encode(pcm)
    disk,meta=build_disk(packed,out/'assembly')
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())
    (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    save(out/'player.json',meta)
    print(json.dumps({k:v for k,v in meta.items() if k not in ('player_labels','directory','first_addresses','second_addresses')}),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    prepare(p.parse_args().output)
