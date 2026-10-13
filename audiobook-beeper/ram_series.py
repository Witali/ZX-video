"""Adaptive sequential volumes; the legacy volume formats remain reproducible."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from audio_cover import prepare
from ima3_series import disk_address,CONTROLLER_SECTOR,CONTROLLER_SECTORS,HEADER_SECTOR
from pcm_player import TrdFile,basic_line,place_files
from ram_cache import IMA3_BYTES,IMA4_BYTES,copy_worker
from verify_pcm import save

FIRST=56                       # boot1,controller10,header2,cover27,after directory
OVERHEAD=97+60                  # per-part tables keep every recording's hot rows


def capacity_samples(codec):return IMA4_BYTES*2 if codec=='ima4' else IMA3_BYTES//3*8


def section_sizes(samples,codec):
    alignment=512 if codec=='ima4' else 8
    if samples%alignment or not 8192<=samples<=capacity_samples(codec):
        raise ValueError('adaptive part length is outside aligned resident RAM')
    remaining=samples//2 if codec=='ima4' else samples//8*3
    result=[]
    for limit in ((16384,)*5+(7936,) if codec=='ima4' else (16383,)*5+(7935,)):
        size=min(limit,remaining)
        if size:result.append((size+255)//256)
        remaining-=size
    assert remaining==0
    return result


def plan_parts(samples,*,codec='ima4',part_samples=None):
    maximum=part_samples or capacity_samples(codec);section_sizes(maximum,codec)
    if samples<=0:raise ValueError('empty audio')
    parts=[];start=0;position=FIRST;alignment=512 if codec=='ima4' else 8
    while start<samples:
        room=2560-position-OVERHEAD
        if room<16:
            position=FIRST;continue
        # IMA3 bank-local rounding needs up to six extra sectors. Validate the
        # exact layout instead of accepting a byte-only packing estimate.
        count=min(maximum,room*(512 if codec=='ima4' else 256*8//3))//alignment*alignment
        while count>=8192 and OVERHEAD+sum(section_sizes(count,codec))>2560-position:count-=alignment
        if count<8192:position=FIRST;continue
        stop=min(samples,start+count-128)
        prepared=max(8192,(stop-start+128+alignment-1)//alignment*alignment)
        sectors=OVERHEAD+sum(section_sizes(prepared,codec))
        parts.append(dict(start=start,stop=stop,samples=prepared,sectors=sectors,file_count=3+len(section_sizes(prepared,codec))))
        position+=sectors;start=stop
    return parts


def plan_volumes(parts,*,single=False):
    volumes=[];current=[];position=FIRST;files=4
    for index,part in enumerate(parts):
        count=part.get('file_count',9)
        if position+part['sectors']>2560 or files+count>128 or len(current)==32:
            if not current:raise ValueError('part does not fit a volume')
            volumes.append(current)
            if single:return volumes
            current=[];position=FIRST;files=4
        current.append(index);position+=part['sectors'];files+=count
    if current:volumes.append(current)
    if len(volumes)>9999:raise ValueError('more than9999 volumes requested')
    return volumes


def assemble(work,series,volume,header):
    work.mkdir(parents=True,exist_ok=True);copy_worker(work)
    (work/'identity.bin').write_bytes(header[:24])
    (work/'header-seed.bin').write_bytes(header)
    (work/'chain-config.inc').write_text(f'initial_volume: EQU {volume}\nheader_disk: EQU {disk_address(27)}\ncover_disk: EQU {disk_address(29)}\n')
    (work/'ram-chain.asm').write_bytes(Path(__file__).with_name('ram-chain.asm').read_bytes())
    r=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=chain.bin','--lstfile=chain.lst','-s','.*','ram-chain.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    labels=next(ast.literal_eval(x) for x in r.stdout.splitlines() if x.startswith('{'))
    raw=(work/'chain.bin').read_bytes();assert len(raw)==2560 and labels['resume_entry']==0x400b
    return raw,labels


def build_volume(selected,work,series,volume,total_volumes,*,codec='ima4',cover=None):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    screen=prepare(cover) if not isinstance(cover,bytes) else cover
    header=bytearray(512);header[:24]=(b'IMA4VOL1' if codec=='ima4' else b'IMA3VOL1')+series
    struct.pack_into('<HHB',header,24,volume,total_volumes,len(selected))
    prompt=f'INSERT DISK {volume+1:04d}'.encode()+b'\0';header[128:128+len(prompt)]=prompt
    plans=[];position=FIRST
    for slot,path in enumerate(selected):
        path=Path(path);old=json.loads((path/'player.json').read_bytes())
        lower=position+97;upper=lower+28;end=upper+32;sectors=[]
        for count in section_sizes(old['pcm_samples'],codec):sectors.append(end);end+=count
        struct.pack_into('<H',header,32+slot*2,disk_address(position))
        struct.pack_into('<H',header,192+slot*2,end)
        plans.append((path,old,position,lower,upper,sectors,end));position=end
    struct.pack_into('<H',header,320,position)
    controller,labels=assemble(work/'controller',series,volume,bytes(header))
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "CHAIN" \xaf'),basic_line(30,b'\xf9 \xc0 \xb0 "16384"')])
    files=[TrdFile('boot','B',basic,autostart_line=10),TrdFile('CHAIN','C',controller,start=0x4000),
           TrdFile('HEADER','C',bytes(header),start=0x4a00),TrdFile('COVER','C',screen,start=0xc000)]
    if codec=='ima4':
        from direct_player import build_disk
    else:
        from ima3_direct_player import build_disk,pack3
    records=[]
    for slot,(path,old,start,lower,upper,sectors,end) in enumerate(plans):
        packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
        folder=work/f'part-{slot+1:02d}'
        chain=dict(controller_disk=disk_address(17),controller_sectors=10,controller_blob=controller,
                   volume=volume,next_slot=slot+1,future_sector=end,end_sector=position)
        model=dict(old['model'],extended_ram=True)
        _,meta=build_disk(packed,folder/'assembly',model,old['hot_indices'],old['loop_idle_pairs'],old['loop_idle_pad_tstates'],
                          chain=chain,storage=dict(lower=lower,upper=upper,audio=sectors),cover=screen)
        files.extend([TrdFile(f'P{slot:02d}','C',(folder/'assembly/player.bin').read_bytes(),start=0x8000),
            TrdFile(f'L{slot:02d}','C',(folder/'assembly/bank5-lower.bin').read_bytes(),start=0x4000),
            TrdFile(f'U{slot:02d}','C',(folder/'assembly/bank5-upper.bin').read_bytes(),start=0x6000)])
        resident=packed if codec=='ima4' else pack3(packed);offset=0
        for i,s in enumerate(meta['sections']):
            count=s.get('audio_bytes',s['bytes'])
            files.append(TrdFile(f'A{slot:02d}{i}','C',bytes(s['bytes']-count)+resident[offset:offset+count],start=s['address']));offset+=count
        meta.update(player_sector=start,selected_source=str(path.resolve()),controller_labels=labels,one_pass=True,repeat=False)
        save(folder/'player.json',meta)
        records.append(dict(slot=slot+1,metadata=str((folder/'player.json').resolve()),selected=str(path.resolve()),player_sector=start,samples=old['pcm_samples']))
    assert position<=2560 and len(files)<=128
    disk,directory,capacity=place_files(files,f'RAM{volume:04d}')
    meta=dict(codec=codec,extended_ram=True,volume=volume,total_volumes=total_volumes,parts=records,
              controller_labels=labels,controller_disk_sector=17,header_disk_sector=27,cover_disk_sector=29,
              directory=directory,capacity=capacity,used_sectors=position,free_sectors=2560-position,
              independently_bootable=True,trd_sha256=hashlib.sha256(disk).hexdigest(),series_id=series.hex())
    save(work/'volume.json',meta)
    return disk,meta
