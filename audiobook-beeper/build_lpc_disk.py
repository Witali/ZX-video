"""Package an independently bootable LPC-to-IMA preload disk; no IMA on disk."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from direct_player import build_disk, MEASURED_MODEL
from ima_codec import STEPS
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files, spectrum_bitmap_offset
from lpc_preload import unpack
from verify_pcm import save

HERE = Path(__file__).resolve().parent


def assemble(work, stem):
    run = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj='+stem+'.bin',
                          '--lstfile='+stem+'.lst', '-s', '.*', stem+'.asm'],
                         cwd=work, capture_output=True, text=True)
    (work/(stem+'.log')).write_text(run.stdout+run.stderr, encoding='utf-8')
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    return next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))


def progress_screen():
    from PIL import Image, ImageDraw, ImageFont
    im=Image.new('1',(256,192)); draw=ImageDraw.Draw(im); font=ImageFont.load_default(size=12)
    for y,label in ((12,'LPC -> IMA ADPCM'),(34,'PREPARING AUDIO'),(62,'READ LPC FROM DISK'),
                    (106,'CONVERT LPC TO IMA'),(151,'PLAYBACK STARTS WHEN READY'),(174,'SPECTRUM 128 / BEEPER')):
        box=draw.textbbox((0,0),label,font=font)
        draw.text(((256-box[2])//2,y),label,font=font,fill=1)
    data=bytearray(6912)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x,y)): data[spectrum_bitmap_offset(x//8,y)] |= 128>>(x&7)
    data[6144:]=bytes([0x47])*768
    for row in (10,16): data[6144+row*32:6144+(row+1)*32]=bytes([0x49])*32
    return bytes(data)


def disk_address(sector):
    return (sector//16)*256+sector%16


def build(source, out, pairs=0, pad=0, hot=None):
    out.mkdir(parents=True, exist_ok=True)
    packed=gzip.decompress((source/'soundtrack.ima.gz').read_bytes())
    lpc=(source/'soundtrack.lps').read_bytes();records,samples=unpack(lpc)
    assert len(packed)*2==samples and 32<len(lpc)<=32768
    _,meta=build_disk(packed,out/'assembly',MEASURED_MODEL,hot,pairs,pad)
    work=out/'assembly'
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "LPCBOOT" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    preloader_size=0x3700
    files=[boot,TrdFile('LPCBOOT','C',bytes(preloader_size),start=0x8000),
           TrdFile('PLAYER','C',bytes(23296),start=0x8000),
           TrdFile('LOWER','C',(work/'bank5-lower.bin').read_bytes(),start=0x4000),
           TrdFile('UPPER','C',(work/'bank5-upper.bin').read_bytes(),start=0x6000),
           TrdFile('LPCDATA','C',lpc,start=0xC000)]
    starts=[]
    for i in range(len(files)):
        tr,sec=calculate_file_start(files[:i]);starts.append(tr*16+sec)
    config=(work/'config.inc').read_text()
    for key,value in dict(lpc_preloaded=1,screen_disk=disk_address(starts[2]+64),
                           lower_disk=disk_address(starts[3]),upper_disk=disk_address(starts[4])).items():
        lines=config.splitlines()
        config='\n'.join(f'{key}: EQU {value}' if x.startswith(key+':') else x for x in lines)+'\n'
    (work/'config.inc').write_text(config,encoding='utf-8',newline='\n')
    player_labels=assemble(work,'player')
    config_values=dict(lpc_disk=disk_address(starts[5]),player_disk=disk_address(starts[2]),
        lpc_bytes=len(lpc),lpc_first_sectors=min(64,(len(lpc)+255)//256),
        lpc_second_sectors=max(0,(len(lpc)+255)//256-64),frame_count=len(records),
        last_frame_samples=(samples-128-1)%160+1,trampoline_size=0)
    def config_lpc():
        (work/'lpc-config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in config_values.items()),encoding='utf-8')
    config_lpc()
    shutil.copy2(HERE/'lpc-handoff.asm',work/'trampoline.asm')
    assemble(work,'trampoline')
    config_values['trampoline_size']=(work/'trampoline.bin').stat().st_size
    config_lpc()
    (work/'sections.bin').write_bytes(b''.join(struct.pack('<BH',s['bank'],s['address']) for s in meta['sections']))
    sectors=(len(lpc)+255)//256
    (work/'load-thresholds.bin').write_bytes(bytes((sectors*i+31)//32 for i in range(1,33)))
    (work/'unpack-thresholds.bin').write_bytes(b''.join(((len(packed)*i+31)//32).to_bytes(3,'little') for i in range(1,33)))
    (work/'ima-steps.bin').write_bytes(struct.pack('<89H',*STEPS))
    (work/'progress-screen.bin').write_bytes(progress_screen())
    shutil.copy2(HERE/'lpc-preload.asm',work/'lpc-preload.asm')
    preload_labels=assemble(work,'lpc-preload')
    preloader=(work/'lpc-preload.bin').read_bytes();assert len(preloader)==preloader_size
    player=(work/'player.bin').read_bytes();assert len(player)==23296
    files[1]=TrdFile('LPCBOOT','C',preloader,start=0x8000)
    files[2]=TrdFile('PLAYER','C',player,start=0x8000)
    disk,directory,capacity=place_files(files,'LPCIMA')
    meta.update(player_labels=player_labels,directory=directory,capacity=capacity,
        binary_sha256=hashlib.sha256(player).hexdigest(),playback_preload_sector_reads=87,
        compensated_reference_rate_hz=8000,
        lpc_preload=dict(labels=preload_labels,format='LPS1',lpc_bytes=len(lpc),ima_bytes=len(packed),
                        source_sector=starts[5],load_sectors=sectors,frames=len(records),samples=samples,
                        preloader_sector=starts[1],preloader_size=preloader_size,
                        playback_instruction_delta_tstates=0,
                        memory=dict(product_tables=[0x6000,0x77ff],temporary_input_banks=[3,7],
                                    final_input_tail=[0xa000,0xb7ff],decoder_end=preload_labels['code_end'])))
    save(out/'player.json',meta)
    (out/'audiobook-preview.trd').write_bytes(disk)
    for name in ('source-preview.wav','original-source-preview.wav','soundtrack.lps','soundtrack.ima.gz','lpc.json'):
        shutil.copy2(source/name,out/name)
    return meta


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--pairs',type=int,default=0)
    p.add_argument('--pad',type=int,default=0)
    a=p.parse_args();build(a.source,a.output,a.pairs,a.pad)
