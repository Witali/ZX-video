"""Build one continuous IMA4 stream, directly resident in detected RAM banks."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

from audio_cover import prepare
from convert_audio import pcm_wav
from direct_player import layout,HOLDS
from ima_beam import encode
from ima_codec import decode,STEPS,INDEX,require_unclipped
from ima3_series import disk_address
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files
from probe_reconstruction_error import wav8
from verify_pcm import save

HERE=Path(__file__).resolve().parent
BASE_BANKS=(0,4,6,1,3,7)


def sections(byte_count,extra_pages):
    result=[];remaining=byte_count
    for page in BASE_BANKS+tuple(range(8,8+extra_pages)):
        size=min(9472 if page==7 else 16384,remaining)
        if not size:break
        assert size%256==0
        result.append(dict(bank=page,address=0x10000-size,bytes=size,sectors=size//256))
        remaining-=size
    return result,remaining


def build(packed,work,cover,model=None):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    model=dict(model or dict(holds=HOLDS,beta=.5,extent=1.),extended_ram=True)
    pcm,indices=decode(packed);assert len(packed)%256==0 and (pcm[-1],indices[-1])==(0,0)
    counts=np.bincount(np.r_[0,indices[:-1]],minlength=89)
    hot=sorted(range(89),key=lambda i:(-int(counts[i]),i))[:25]
    compact_loader=bool(model.pop('compact_stream_loader',False))
    if compact_loader:model['compact_stream_loader']=True
    resident_limit=16384 if compact_loader else 14848
    words,nxt,states,first,second,pointers,pages,rows,_,_,_=layout(packed[:256],model,hot,resident_limit=resident_limit)
    assert len(states)<=18
    # Source-independent table dictionaries may grow. Move only cold/refill
    # code after the aligned resident end; the live descriptor tail remains
    # at its original address. B800/BA00 leave enough room for this worker,
    # bounce and the maximum one-TRD descriptor count in the same16-KiB bank.
    resident_end=pointers+256+1024+1088
    if compact_loader:
        # The persistent map/probe routines and256-byte mutable bounce occupy
        # uncontended startup padding, not the hot dictionary. This leaves the
        # same cold/refill worker after a64-byte-aligned resident end. Assembly
        # separately checks both regions against FIRST and the final bank byte.
        worker_origin=(resident_end+63)&~63
        assert worker_origin<0xBFFF,'compact worker must start inside fixed bank2'
    else:
        # Preserve the established default alignment and every archived image.
        worker_origin=(resident_end+255)&~255
        assert worker_origin<=0xBA00,'loader plus wider tables must fit fixed bank2'
    memory=bytearray(65536)
    for value in range(64):
        for sid,state in enumerate(states):
            word=int(words[value,state]);at=pages[value]+sid*6
            memory[at:at+6]=struct.pack('<HHBB',first[word>>8],second[word&255],states.index(int(nxt[value,state]))*6,16)
    for index in range(89):
        step=STEPS[index]
        for code in range(16):
            delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            if code&8:delta=-delta
            at=rows[index]+code*4
            memory[at:at+4]=struct.pack('<HH',delta&65535,rows[max(0,min(88,index+INDEX[code&7]))])
    memory[pointers:pointers+256]=bytes(pages[i>>2]>>8 for i in range(256))
    all_sections,remaining=sections(len(packed),56);assert remaining==0
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    files=[TrdFile('boot','B',basic,autostart_line=10),TrdFile('PLAYER','C',bytes(16384),start=0x8000),
           TrdFile('LOWER','C',bytes(memory[0x4000:0x5c00]),start=0x4000),
           TrdFile('UPPER','C',bytes(memory[0x6000:0x8000]),start=0x6000),TrdFile('COVER','C',cover,start=0xc000)]
    positions=[];position=16
    for f in files:positions.append(position);position+=(len(f.data)+255)//256
    assert calculate_file_start(files)==(position//16,position%16)
    constants=dict(extended_ram=1,first_base=min(first.values()),first_size=42,first_patterns=len(first),
                   pcm_high=pointers,decoder_seed=rows[0],initial_feedback_offset=states.index(16)*6,
                   lower_disk=disk_address(positions[2]),upper_disk=disk_address(positions[3]),
                   cover_disk=disk_address(positions[4]),audio_sector=position,audio_sectors=len(packed)//256,
                   record_slots=len(all_sections)+1,worker_origin=worker_origin,
                   compact_stream_loader=int(compact_loader))
    for i in range(256):constants.update({f'first_address_{i}':first.get(i,-1),f'second_address_{i}':second.get(i,-1)})
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in constants.items()),encoding='utf-8',newline='\n')
    for name,data in [('pcm-high',memory[pointers:pointers+256]),('fixed-pages',memory[pointers+256:pointers+1280]),
                      ('decoder-extra',memory[pointers+1280:pointers+1280+1088])]:
        (work/(name+'.bin')).write_bytes(data)
    cache=(HERE/'ram-cache.asm').read_text(encoding='utf-8')
    (work/'stream-probe.asm').write_text(cache[:cache.index('; DE=TR-DOS track/sector.')],encoding='utf-8',newline='\n')
    for name in ('stream-player.asm','stream-worker.asm','stream-progress.asm'):(work/name).write_bytes((HERE/name).read_bytes())
    r=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','stream-player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    labels=next(ast.literal_eval(x) for x in r.stdout.splitlines() if x.startswith('{'))
    if not compact_loader:
        # Captured historical verification requires exact metadata as well as
        # byte-identical disks. Optional symbols do not enter default exports.
        for name in ('compact_stream_loader','startup_hot_end','stream_probe_start','stream_probe_end'):
            labels.pop(name,None)
    blob=(work/'player.bin').read_bytes();assert len(blob)==16384
    files[1]=TrdFile('PLAYER','C',blob,start=0x8000)
    # A TR-DOS directory sector count is one byte. Split file entries, but keep
    # physical data contiguous: the player sees one byte stream without gaps.
    for i,offset in enumerate(range(0,len(packed),255*256)):
        files.append(TrdFile(f'AUD{i:02d}','C',packed[offset:offset+255*256],start=0xc000))
    disk,directory,capacity=place_files(files,'SEAFRAM')
    compact_memory=(dict(compact_stream_loader=True,startup_end=labels['startup_end'],
                         probe_start=labels['stream_probe_start'],probe_end=labels['stream_probe_end'],
                         bounce_start=labels['stream_bounce'],bounce_bytes=256) if compact_loader else {})
    meta=dict(continuous_ram=True,origin=0x8000,player_labels=labels,model=model,first_code_bytes=42,
              first_addresses=list(first.values()),second_addresses=list(second.values()),decoder_rows=[rows[i] for i in range(89)],
              packet_pages=pages,feedback_states=states,hot_indices=hot,pcm_samples=len(pcm),packed_bytes=len(packed),
              audio_sector=position,audio_sectors=len(packed)//256,sections=all_sections,ordinary_tstates=423,
              ordinary_holds_tstates=HOLDS,page_extra_tstates=14,initial_predictor=0,initial_index=0,
              paging_base=24,source_sample_rate_hz=8000,directory=directory,capacity=capacity,
              binary_sha256=hashlib.sha256(blob).hexdigest(),packed_sha256=hashlib.sha256(packed).hexdigest(),
              trd_sha256=hashlib.sha256(disk).hexdigest(),independently_bootable=True,
              memory=dict(fixed_bank2=16384,resident_table_end=labels['resident_end'],worker_origin=worker_origin,
                          bank5_tables_and_workspace=16384,shadow_screen=6912,
                          base_audio_bytes=91392,extra_audio_bytes_per_page=16384,pcm_buffer_bytes=0,pdm_buffer_bytes=0,**compact_memory),
              saturation_guard=require_unclipped(packed))
    save(work/'player.json',meta)
    return disk,meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--cover',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=wav8(a.prepared);count=len(source)
    length=max(8192,(count+128+511)//512*512)
    pcm=np.full(length,128,'u1');pcm[:count]=source
    marker=out/'encoded.json'
    identity=dict(source_sha256=hashlib.sha256(a.prepared.read_bytes()).hexdigest(),samples=count,
                  prepared_samples=length,encoder='unchanged IMA beam32/block64',internal_fades=False,internal_guards=False)
    if marker.exists():
        assert json.loads(marker.read_bytes())==identity
        packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    else:
        packed=encode(pcm,width=32,block_samples=64)
        (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));save(marker,identity)
        pcm_wav(out/'source-preview.wav',pcm)
    disk,meta=build(packed,out/'assembly',prepare(a.cover))
    (out/'audio.trd').write_bytes(disk);save(out/'player.json',meta)
    print(json.dumps(dict(assembled=True,sha256=meta['trd_sha256'],audio_bytes=len(packed),worker_end=meta['player_labels']['stream_worker_end'])),flush=True)


if __name__=='__main__':main()
