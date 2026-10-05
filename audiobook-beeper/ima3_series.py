"""RAM-sized IMA3 parts, packed into independently bootable TR-DOS volumes."""
import ast
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

from ima3_direct_player import build_disk, layout, pack3, MEASURED_MODEL
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files
from convert_audio import pcm_wav
from verify_pcm import save

HERE=Path(__file__).resolve().parent
MAGIC=b'IMA3VOL1'
CONTROLLER_SECTORS=8
CONTROLLER_SECTOR=17
HEADER_SECTOR=25
LOWER_SECTOR=27
UPPER_SECTOR=55
FIRST_PLAYER_SECTOR=87


def disk_address(sector):
    if not 0<=sector<2560:raise ValueError('TRD sector outside disk')
    return (sector//16)*256+sector%16


@lru_cache(maxsize=1)
def capacity_samples():
    reserve=layout(bytes(256),chained=True)[-1]
    return (5*16383+9471+(16384-reserve)//3*3)//3*8


def section_sizes(samples):
    if samples%8 or not 8<=samples<=capacity_samples():raise ValueError('invalid part length')
    remaining=samples//8*3;parts=[]
    for limit in (16383,)*5+(9471,(capacity_samples()//8*3-5*16383-9471)):
        size=min(limit,remaining)
        if size:parts.append((size+255)//256)
        remaining-=size
    assert remaining==0
    return parts


def plan_parts(samples,*,part_samples=None):
    maximum=part_samples or capacity_samples()
    if maximum>capacity_samples() or maximum<8192 or maximum%8:
        raise ValueError('part size must be a multiple of eight, 8192..RAM capacity')
    if samples<=0:raise ValueError('empty audio')
    parts=[]
    for start in range(0,samples,maximum-128):
        stop=min(samples,start+maximum-128)
        count=max(8192,(stop-start+128+7)//8*8)
        parts.append(dict(start=start,stop=stop,samples=count,sectors=91+sum(section_sizes(count))))
    return parts


def plan_volumes(parts,*,single=False):
    volumes=[];current=[];position=FIRST_PLAYER_SECTOR
    for index,part in enumerate(parts):
        if position+part['sectors']>2560 or len(current)==32:
            if not current:raise ValueError('a RAM part cannot fit a disk')
            volumes.append(current)
            if single:return volumes
            current=[];position=FIRST_PLAYER_SECTOR
        current.append(index);position+=part['sectors']
    if current:volumes.append(current)
    if len(volumes)>9999:raise ValueError('more than 9999 TRDs requested')
    return volumes


def assemble_controller(work,series,volume):
    work.mkdir(parents=True,exist_ok=True)
    (work/'identity.bin').write_bytes(MAGIC+series)
    (work/'chain-config.inc').write_text(
        f'initial_volume: EQU {volume}\nheader_disk: EQU {disk_address(HEADER_SECTOR)}\n',encoding='ascii')
    (work/'ima3-chain.asm').write_bytes((HERE/'ima3-chain.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=chain.bin','--lstfile=chain.lst','-s','.*','ima3-chain.asm'],
                       cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    blob=(work/'chain.bin').read_bytes()
    assert len(blob)==2048 and labels['resume_entry']==0x400b
    return blob,labels


def build_volume(selected,work,series,volume,total_volumes):
    """Repackage already qualified parts; retain pulse addresses and model."""
    work.mkdir(parents=True,exist_ok=True)
    controller,labels=assemble_controller(work/'controller',series,volume)
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
                   basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "CHAIN" \xaf'),
                   basic_line(30,b'\xf9 \xc0 \xb0 "16384"')])
    header=bytearray(512);header[:24]=MAGIC+series
    struct.pack_into('<HHB',header,24,volume,total_volumes,len(selected))
    prompt=f'INSERT DISK {volume+1:04d}'.encode('ascii')+b'\0'
    header[128:128+len(prompt)]=prompt
    files=[TrdFile('boot','B',basic,autostart_line=10),TrdFile('CHAIN','C',controller,start=0x4000),
           TrdFile('HEADER','C',bytes(512),start=0x4800),
           TrdFile('LOWER','C',bytes(7168),start=0x4000),TrdFile('UPPER','C',bytes(8192),start=0x6000)]
    assert calculate_file_start(files)==(FIRST_PLAYER_SECTOR//16,FIRST_PLAYER_SECTOR%16)
    records=[];position=FIRST_PLAYER_SECTOR;tables=None
    for slot,path in enumerate(selected):
        old=json.loads((path/'player.json').read_bytes())
        packed=gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
        expected=section_sizes(old['pcm_samples'])
        sectors=[];next_pos=position+91
        for count in expected:sectors.append(next_pos);next_pos+=count
        storage=dict(lower=LOWER_SECTOR,upper=UPPER_SECTOR,audio=sectors)
        chain=dict(controller_disk=disk_address(CONTROLLER_SECTOR),controller_sectors=CONTROLLER_SECTORS,
                   volume=volume,next_slot=slot+1)
        folder=work/f'part-{slot+1:02d}'
        _,meta=build_disk(packed,folder/'assembly',old['model'],idle_pairs=old['loop_idle_pairs'],
                          idle_pad=old['loop_idle_pad_tstates'],chain=chain,storage=storage)
        # Never change pulse/extraction addresses when repackaging a qualified
        # recording. The one-pass exit affects only the final silent guard.
        assert meta['first_addresses']==old['first_addresses'] and meta['phase_base']==old['phase_base']
        assert meta['resident_audio_bytes']==old['resident_audio_bytes']
        pair=((folder/'assembly/bank5-lower.bin').read_bytes(),(folder/'assembly/bank5-upper.bin').read_bytes())
        if tables is None:tables=pair
        assert pair==tables,'parts use incompatible PDM tables'
        player=(folder/'assembly/player.bin').read_bytes()
        files.append(TrdFile(f'P{slot:02d}','C',player,start=0x8000))
        resident=pack3(packed);offset=0
        for i,s in enumerate(meta['sections']):
            payload=bytes(s['bytes']-s['audio_bytes'])+resident[offset:offset+s['audio_bytes']]
            files.append(TrdFile(f'A{slot:02d}{i}','C',payload,start=s['address']));offset+=s['audio_bytes']
        struct.pack_into('<H',header,32+slot*2,disk_address(position))
        meta.update(player_sector=position,selected_source=str(path.resolve()),controller_labels=labels,
                    # Last complete-source sample precedes the exit by >=125 samples.
                    one_pass=True,repeat=False)
        save(folder/'player.json',meta)
        records.append(dict(slot=slot+1,metadata=str((folder/'player.json').resolve()),
                            selected=str(path.resolve()),player_sector=position,samples=old['pcm_samples']))
        position=next_pos
    files[2]=TrdFile('HEADER','C',bytes(header),start=0x4800)
    files[3]=TrdFile('LOWER','C',tables[0],start=0x4000)
    files[4]=TrdFile('UPPER','C',tables[1],start=0x6000)
    assert position<=2560 and len(files)<=128
    disk,directory,capacity=place_files(files,f'IMA3{volume:04d}')
    meta=dict(volume=volume,total_volumes=total_volumes,parts=records,controller_labels=labels,
              controller_disk_sector=CONTROLLER_SECTOR,header_disk_sector=HEADER_SECTOR,
              directory=directory,capacity=capacity,independently_bootable=True,
              trd_sha256=hashlib.sha256(disk).hexdigest(),series_id=series.hex())
    save(work/'volume.json',meta)
    return disk,meta


def convert_series(args):
    from convert_ima3_audio import convert,digest
    from verify_ima3_series import verify_series
    if args.prepared_pcm or args.reuse_pilot:
        raise ValueError('series mode accepts ordinary audio; --prepared-pcm/--reuse-pilot belong to the looping preview')
    out=args.output.resolve();manifest=out/'run.json'
    identity=dict(mode=args.disk_mode,input_sha256=digest(args.input),duration=args.duration,
                  quality=getattr(args,'quality','best'),
                  target_snr=args.target_snr,attempts=args.attempts,no_recording=args.no_recording,
                  ffmpeg_sha256=digest(Path(args.ffmpeg)),fuse_sha256=digest(args.fuse),
                  producers={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.py','.asm')})
    if out.exists() and any(out.iterdir()):
        if not args.resume or not manifest.is_file() or json.loads(manifest.read_bytes())!=identity:
            raise ValueError('output not empty or resume source/settings/producers changed')
    else:out.mkdir(parents=True,exist_ok=True);save(manifest,identity)
    source=out/'track.f32'
    source_marker=out/'track.json'
    if not source_marker.exists():
        command=[args.ffmpeg,'-v','error','-nostdin','-y','-i',str(args.input),'-map','0:a:0']
        if args.duration is not None:
            if not math.isfinite(args.duration) or args.duration<=0:raise ValueError('duration must be positive and finite')
            command+=['-t',str(args.duration)]
        subprocess.run(command+['-ac','1','-ar','8000','-f','f32le',str(source)],check=True)
        if not source.stat().st_size or source.stat().st_size%4:raise ValueError('no decoded audio')
        values=np.memmap(source,dtype='<f4',mode='r');peak=0.
        for i in range(0,len(values),1000000):
            block=values[i:i+1000000]
            if not np.all(np.isfinite(block)):raise ValueError('nonfinite audio')
            peak=max(peak,float(np.max(np.abs(block))))
        save(source_marker,dict(samples=len(values),gain=(109/128)/peak if peak else 1.,sha256=digest(source)))
        del values
    original=json.loads(source_marker.read_bytes())
    if digest(source)!=original['sha256']:raise ValueError('cached decoded source changed')
    parts=plan_parts(original['samples']);volumes=plan_volumes(parts,single=args.disk_mode=='single')
    included=[i for volume in volumes for i in volume]
    values=np.memmap(source,dtype='<f4',mode='r');work=out/'work';work.mkdir(exist_ok=True)
    selected=[];qualities=[]
    for i in included:
        part=parts[i];samples=values[part['start']:part['stop']].astype(float)*original['gain']
        fade=min(80,len(samples)//2)
        if fade:
            samples[:fade]*=np.linspace(0,1,fade);samples[-fade:]*=np.linspace(1,0,fade)
        pcm=np.full(part['samples'],128,dtype='u1')
        pcm[:len(samples)]=np.clip(np.rint(samples*128+128),0,255).astype('u1')
        path=work/f'input-{i+1:05d}.wav';pcm_wav(path,pcm)
        options=copy.copy(args);options.disk_mode=None;options.input=path;options.output=work/f'part-{i+1:05d}'
        options.prepared_pcm=True;options.duration=None
        print(json.dumps(dict(stage='convert-part',part=i+1,parts=len(included),**part)),flush=True)
        result=convert(options);selected.append(options.output);qualities.append(result['quality_gate_passed'])
    del values
    series=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).digest()[:16]
    disks=[]
    for number,indices in enumerate(volumes,1):
        disk,meta=build_volume([selected[i] for i in indices],work/f'volume-{number:04d}',series,number,len(volumes))
        name='audio.trd' if args.disk_mode=='single' else f'audio-{number:04d}.trd'
        (out/name).write_bytes(disk);disks.append(dict(file=name,**meta))
    save(out/'volumes.json',disks)
    verified=verify_series(out,args.fuse,args.ffmpeg)
    measured=[p for run in verified['volumes']+verified['continuations'] for p in run['parts']]
    passed=all(qualities) and all(p['source_silent'] or p['fixed_clock_snr_db'] is not None
                                and p['fixed_clock_snr_db']>=args.target_snr for p in measured)
    report=dict(complete=True,disk_mode=args.disk_mode,disks=[d['file'] for d in disks],
                part_count=len(included),source_samples=original['samples'],
                retained_source_samples=parts[included[-1]]['stop'],
                full_source_retained=parts[included[-1]]['stop']==original['samples'],
                parts=[parts[i] for i in included],fixed_gain=original['gain'],
                sample_rate_hz=8000,silence_guard_samples=128,edge_fade_samples=80,
                maximum_prepared_samples_per_part=capacity_samples(),
                quality_gate_passed=passed,preview_only=not passed,
                loading_between_parts=True,simultaneous_disk_and_audio=False,verification=verified,
                physical_hardware_tested=False)
    save(out/'report.json',report)
    print(json.dumps(dict(stage='complete',disk_mode=args.disk_mode,disks=report['disks'],
                          part_count=report['part_count'],retained_seconds=report['retained_source_samples']/8000,
                          full_source_retained=report['full_source_retained'],quality_gate_passed=passed)),flush=True)
    return report
