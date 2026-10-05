"""Sequential IMA4 volumes, retaining each part's qualified decoder tables."""
import gzip
import hashlib
import json
from pathlib import Path
import struct

from direct_player import build_disk,MAX_PACKED_BYTES
from ima3_series import (assemble_controller,disk_address,CONTROLLER_SECTOR,
                         CONTROLLER_SECTORS,HEADER_SECTOR,plan_volumes as shared_volumes)
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files
from verify_pcm import save

MAGIC=b'IMA4VOL1'
FIRST_PLAYER_SECTOR=27
PART_OVERHEAD_SECTORS=91+28+32


def capacity_samples():return MAX_PACKED_BYTES*2


def section_sizes(samples):
    if samples%512 or not 8192<=samples<=capacity_samples():
        raise ValueError('IMA4 part must have 8192..186880 samples, aligned to 512')
    remaining=samples//2;result=[]
    for limit in (16384,)*5+(9472,2048):
        size=min(limit,remaining)
        if size:result.append(size//256)
        remaining-=size
    assert remaining==0
    return result


def plan_parts(samples,*,part_samples=None):
    """Fill the last usable sectors with a shorter part, preserving source order."""
    maximum=capacity_samples() if part_samples is None else part_samples
    section_sizes(maximum)
    if samples<=0:raise ValueError('empty audio')
    start=0;position=FIRST_PLAYER_SECTOR;parts=[]
    while start<samples:
        room=(2560-position-PART_OVERHEAD_SECTORS)*512
        if room<8192:
            position=FIRST_PLAYER_SECTOR
            continue
        count=min(maximum,room)
        stop=min(samples,start+count-128)
        prepared=max(8192,((stop-start+128+511)//512)*512)
        sectors=PART_OVERHEAD_SECTORS+prepared//512
        parts.append(dict(start=start,stop=stop,samples=prepared,sectors=sectors))
        position+=sectors;start=stop
    return parts


def plan_volumes(parts,*,single=False):
    return shared_volumes(parts,single=single,first_sector=FIRST_PLAYER_SECTOR)


def build_volume(selected,work,series,volume,total_volumes):
    """Only relocate disk sectors; keep all qualified live addresses and tables."""
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    controller,labels=assemble_controller(work/'controller',series,volume,magic=MAGIC)
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "CHAIN" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "16384"')])
    header=bytearray(512);header[:24]=MAGIC+series
    struct.pack_into('<HHB',header,24,volume,total_volumes,len(selected))
    prompt=f'INSERT DISK {volume+1:04d}'.encode()+b'\0'
    header[128:128+len(prompt)]=prompt
    files=[TrdFile('boot','B',basic,autostart_line=10),
           TrdFile('CHAIN','C',controller,start=0x4000),
           TrdFile('HEADER','C',bytes(header),start=0x4800)]
    track,sector=calculate_file_start(files);position=track*16+sector
    assert position==FIRST_PLAYER_SECTOR
    records=[]
    for slot,path in enumerate(selected):
        path=Path(path);old=json.loads((path/'player.json').read_bytes())
        packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
        lower=position+91;upper=lower+28;next_pos=upper+32;sectors=[]
        for count in section_sizes(old['pcm_samples']):
            sectors.append(next_pos);next_pos+=count
        chain=dict(controller_disk=disk_address(CONTROLLER_SECTOR),
                   controller_sectors=CONTROLLER_SECTORS,volume=volume,next_slot=slot+1)
        folder=work/f'part-{slot+1:02d}'
        _,meta=build_disk(packed,folder/'assembly',old['model'],old['hot_indices'],
            old['loop_idle_pairs'],old['loop_idle_pad_tstates'],chain=chain,
            storage=dict(lower=lower,upper=upper,audio=sectors))
        for key in ('first_addresses','second_addresses','decoder_rows','packet_pages'):
            assert meta[key]==old[key],key
        assert [{k:v for k,v in s.items() if k!='sector'} for s in meta['sections']]==[
            {k:v for k,v in s.items() if k!='sector'} for s in old['sections']]
        # Hot IMA rows are recording dependent. Sharing only the PDM portions
        # would corrupt cold rows, so preserve both complete bank-5 files.
        for name in ('bank5-lower.bin','bank5-upper.bin'):
            assert (folder/'assembly'/name).read_bytes()==(path/'assembly'/name).read_bytes(),name
        files.extend([TrdFile(f'P{slot:02d}','C',(folder/'assembly/player.bin').read_bytes(),start=0x8000),
            TrdFile(f'L{slot:02d}','C',(folder/'assembly/bank5-lower.bin').read_bytes(),start=0x4000),
            TrdFile(f'U{slot:02d}','C',(folder/'assembly/bank5-upper.bin').read_bytes(),start=0x6000)])
        offset=0
        for i,s in enumerate(meta['sections']):
            files.append(TrdFile(f'A{slot:02d}{i}','C',packed[offset:offset+s['bytes']],start=s['address']))
            offset+=s['bytes']
        struct.pack_into('<H',header,32+slot*2,disk_address(position))
        meta.update(player_sector=position,selected_source=str(path.resolve()),
                    controller_labels=labels,one_pass=True,repeat=False)
        save(folder/'player.json',meta)
        records.append(dict(slot=slot+1,metadata=str((folder/'player.json').resolve()),
            selected=str(path.resolve()),player_sector=position,samples=old['pcm_samples']))
        position=next_pos
    files[2]=TrdFile('HEADER','C',bytes(header),start=0x4800)
    assert position<=2560 and len(files)<=128
    disk,directory,capacity=place_files(files,f'IMA4{volume:04d}')
    meta=dict(codec='ima4',volume=volume,total_volumes=total_volumes,parts=records,
        controller_labels=labels,controller_disk_sector=CONTROLLER_SECTOR,
        header_disk_sector=HEADER_SECTOR,directory=directory,capacity=capacity,
        used_sectors=position,free_sectors=2560-position,independently_bootable=True,
        trd_sha256=hashlib.sha256(disk).hexdigest(),series_id=series.hex())
    save(work/'volume.json',meta)
    return disk,meta
