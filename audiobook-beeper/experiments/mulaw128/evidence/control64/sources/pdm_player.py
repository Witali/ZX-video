"""Resident 1-bit beeper player: selectable 52 or 46 deterministic T/bit."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'toolkit'))
from build_zxv_trd import MiniAssembler, TrdFile, basic_line, spectrum_bitmap_offset
from build_streaming_trd import place_files, calculate_file_start

ORIGIN = 0x8000
CPU_CLOCK = 3546900
BIT_TSTATES = 52
BANKS = (0, 4, 6, 1, 3, 7)
BANK_BYTES = 16384


def screen(byte_count,bit_tstates=BIT_TSTATES,repeat=False):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('1',(256,192)); draw = ImageDraw.Draw(im); font = ImageFont.load_default(size=13)
    for y,text in ((24,'BEEPER AUDIOBOOK'),(53,'O. HENRY / PDM TEST'),(84,'1 BIT / PORT FE'),
                   (111,f'{round(CPU_CLOCK/bit_tstates/1000)} kHz CPU / ULA MEASURED'),(139,f'{byte_count//1024} KiB / RESIDENT AUDIO'),
                   (168,'LOOP / RESET TO STOP' if repeat else 'RESET TO REPLAY')):
        box=draw.textbbox((0,0),text,font=font)
        draw.text(((256-(box[2]-box[0]))//2,y),text,font=font,fill=1)
    data=bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x,y)): data[spectrum_bitmap_offset(x//8,y)] |= 128>>(x&7)
    return bytes(data)+bytes([0x47])*768


def player(sections,bit_tstates=BIT_TSTATES,repeat=False):
    a=MiniAssembler(ORIGIN)
    output_labels=[]
    def ld16(op,value): a.emit(op); a.word(value)
    def page(bank):
        ld16(0x01,0x7ffd); a.emit(0x3e,0x10|bank,0xed,0x79)
    def pad(t):
        # Harmless instructions after AND/OR, which always clear carry.
        # RET C is deliberately never taken; tests check stack and all byte values.
        choices={4:(0x00,),5:(0xd8,),7:(0x3e,0),12:(0x18,0)}
        plan={0:[]}
        for n in range(1,t+1):
            for cost in choices:
                if n-cost in plan:
                    plan[n]=plan[n-cost]+[cost]; break
        if t not in plan: raise ValueError(f'cannot pad {t} T')
        for cost in plan[t]: a.emit(*choices[cost])
    def bit(name):
        # RLC D 8; SBC A,A 4; AND 16 7; OUT (FE),A 11 = 30 T.
        a.emit(0xcb,0x02,0x9f,0xe6,0x10)
        a.label(name); output_labels.append(name); a.emit(0xd3,0xfe)
    a.label('start')
    a.emit(0xf3); ld16(0x31,0xb800); a.emit(0xfd,0x21); a.word(0x5c3a); a.emit(0xed,0x56)
    a.emit(0xaf,0xd3,0xfe)
    ld16(0x21,0x9000); ld16(0x11,0x4000); ld16(0x01,6912); a.emit(0xed,0xb0,0xfb)
    for s in sections:
        page(s['bank']); ld16(0x11,(s['sector']//16)*256+s['sector']%16)
        a.abs16((0xed,0x53),'disk_position')
        ld16(0x21,s['address']); a.emit(0x06,s['sectors']); a.abs16(0xcd,'read_n')
    a.emit(0xf3)
    # AY remains silent throughout the beeper experiment, including dirty starts.
    for register in (8,9,10):
        ld16(0x01,0xfffd); a.emit(0x3e,register,0xed,0x79)
        ld16(0x01,0xbffd); a.emit(0xaf,0xed,0x79)
    page(sections[0]['bank'])
    # Start after a normal ROM interrupt; mask interrupts throughout PDM output.
    a.emit(0xfb,0x76,0xf3)
    a.label('ready')
    ld16(0x01,0x7ffd); ld16(0x21,sections[0]['address']); a.emit(0x56)
    a.label('playback')
    for i,s in enumerate(sections):
        a.label(f'loop_{i}')
        if bit_tstates==46:
            # 30-T bit kernel + 16-T housekeeping, including all bank edges.
            bit(f'out_{i}_1'); a.emit(0x23); pad(10) # INC HL 6 + padding 10.
            bit(f'out_{i}_2'); a.emit(0x7c,0xb5); pad(4); a.emit(0x08) # 4+4+4+4.
            bit(f'out_{i}_3'); a.emit(0x08)
            # Restore AF 4 + JR Z taken 12, or 4+7+untaken RET C 5.
            a.rel8(0x28,f'boundary_{i}'); pad(5)
            bit(f'out_{i}_4'); pad(16)
            bit(f'out_{i}_5'); pad(16)
            bit(f'out_{i}_6'); a.emit(0x5e); pad(9)
            bit(f'out_{i}_7'); pad(16)
            bit(f'out_{i}_8'); a.emit(0x53); a.rel8(0x18,f'loop_{i}') # 4+12.
            a.label(f'boundary_{i}')
            bit(f'out_{i}_tail4')
            if i+1<len(sections) or repeat:
                next_section=sections[(i+1)%len(sections)]
                a.emit(0x1e,0x10|next_section['bank']); pad(9)
                bit(f'out_{i}_tail5'); a.label(f'page_{i}'); a.emit(0xed,0x59); pad(4)
                bit(f'out_{i}_tail6'); ld16(0x21,next_section['address']-1); a.emit(0x23) # 10+6.
                bit(f'out_{i}_tail7'); a.emit(0x5e); pad(9)
                bit(f'out_{i}_tail8'); a.emit(0x53)
                if i+1<len(sections):
                    a.rel8(0x18,f'loop_{i+1}')
                else:
                    # Cross the whole code block: 4+4+10 = 18 T, so the
                    # final slot is 48 T (+2), with no loader or mute gap.
                    pad(4); a.abs16(0xc3,'loop_0')
            else:
                pad(16); bit(f'out_{i}_tail5'); pad(16); bit(f'out_{i}_tail6'); pad(16)
                bit(f'out_{i}_tail7'); pad(16); bit(f'out_{i}_tail8'); pad(31); a.emit(0xaf)
                a.label('mute'); a.emit(0xd3,0xfe) # Final hold 31+4+11 = 46 T.
                a.label('finished'); a.emit(0x76); a.rel8(0x18,'finished')
            continue
        for j in range(1,3): bit(f'out_{i}_{j}'); pad(22)
        bit(f'out_{i}_3')
        # Pointer/test preparation 6+4+4, NOP 4, EX AF,AF' 4 = 22 T.
        # Preserve Z while the bit-4 kernel uses carry and clears the flags.
        a.emit(0x23,0x7c,0xb5); pad(4); a.emit(0x08)
        bit(f'out_{i}_4'); a.emit(0x08)
        a.abs16(0xca,f'boundary_{i}'); pad(8) # Restore 4 + JP 10 + NOPs 8.
        bit(f'out_{i}_5'); pad(22)
        bit(f'out_{i}_6'); a.emit(0x5e); pad(15)
        bit(f'out_{i}_7'); pad(22)
        bit(f'out_{i}_8'); a.emit(0x53); pad(8); a.abs16(0xc3,f'loop_{i}')
        a.label(f'boundary_{i}'); pad(8)
        bit(f'out_{i}_tail5')
        if i+1<len(sections) or repeat:
            next_section=sections[(i+1)%len(sections)]
            a.emit(0x1e,0x10|next_section['bank']); pad(15)
            bit(f'out_{i}_tail6'); a.label(f'page_{i}'); a.emit(0xed,0x59); pad(10)
            bit(f'out_{i}_tail7'); ld16(0x21,next_section['address']); a.emit(0x5e); pad(5)
            bit(f'out_{i}_tail8'); a.emit(0x53); pad(8); a.abs16(0xc3,f'loop_{(i+1)%len(sections)}')
        else:
            pad(22); bit(f'out_{i}_tail6'); pad(22); bit(f'out_{i}_tail7'); pad(22); bit(f'out_{i}_tail8')
            pad(37); a.emit(0xaf) # 37+4+11 = one final 52-T hold.
            a.label('mute'); a.emit(0xd3,0xfe)
            a.label('finished'); a.emit(0x76); a.rel8(0x18,'finished')
    a.label('read_n')
    a.emit(0xc5,0xe5); a.abs16((0xed,0x5b),'disk_position'); ld16(0x01,0x0105)
    a.label('disk_call'); ld16(0xcd,0x3d13)
    a.emit(0xe1,0xc1,0x24); a.abs16((0xed,0x5b),'disk_position')
    a.emit(0x1c,0xcb,0x63); a.rel8(0x28,'sector_ok'); a.emit(0x1e,0,0x14)
    a.label('sector_ok'); a.abs16((0xed,0x53),'disk_position'); a.rel8(0x10,'read_n'); a.emit(0xc9)
    a.label('disk_position'); a.word(0)
    code=a.resolve()
    if len(code)>4096: raise ValueError('player overlaps screen staging buffer')
    return code+bytes(4096-len(code))+screen(sum(s['bytes'] for s in sections),bit_tstates,repeat),a.labels,output_labels


def build_disk(packed,bit_tstates=BIT_TSTATES,repeat=False):
    if bit_tstates not in (52,46): raise ValueError('supported PDM output periods are 52 and 46 T')
    if not packed or len(packed)%256 or len(packed)>len(BANKS)*BANK_BYTES:
        raise ValueError('PDM must contain 1..384 complete 256-byte sectors')
    sections=[]
    for i in range(0,len(packed),BANK_BYTES):
        size=min(BANK_BYTES,len(packed)-i)
        sections.append(dict(bank=BANKS[i//BANK_BYTES],sector=0,sectors=size//256,
                             bytes=size,address=0x10000-size))
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    draft,_,_=player(sections,bit_tstates,repeat)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',draft,start=ORIGIN)])
    position=track*16+sector
    for s in sections: s['sector']=position; position+=s['sectors']
    code,labels,outputs=player(sections,bit_tstates,repeat)
    files=[boot,TrdFile('PLAYER','C',code,start=ORIGIN)]
    for i,s in enumerate(sections):
        files.append(TrdFile(f'PDM{i}','C',packed[i*BANK_BYTES:i*BANK_BYTES+s['bytes']],start=s['address']))
    disk,directory,capacity=place_files(files,'PDMBOOK')
    return disk,dict(origin=ORIGIN,bits=len(packed)*8,packed_bytes=len(packed),sections=sections,
        player_labels=labels,output_labels=outputs,directory=directory,capacity=capacity,
        packed_sha256=hashlib.sha256(packed).hexdigest(),cpu_clock_hz=CPU_CLOCK,
        deterministic_bit_tstates=bit_tstates,deterministic_byte_tstates=bit_tstates*8,
        nominal_bit_rate_hz=CPU_CLOCK/bit_tstates,nominal_duration_seconds=len(packed)*8*bit_tstates/CPU_CLOCK,
        paging_value_register='e',repeat=repeat,
        timing=dict(output_kernel=30,padding_and_housekeeping=bit_tstates-30,
                    boundary_test_with_af_preservation=32 if bit_tstates==52 else 34,
                    page_output=12,final_hold=None if repeat else bit_tstates,
                    repeat_hold=(48 if bit_tstates==46 else 52) if repeat else None,
                    irq_during_playback=False,
                    excludes='ULA memory and I/O contention; measured separately in Fuse'),
        memory=dict(bank_2='8000..8FFF code, 9000..AAFF screen staging, B800 stack',
                    bank_5='screen, BASIC and TR-DOS workspace',payload_banks=list(BANKS),
                    maximum_payload_bytes=98304,runtime_disk_reads=0))
