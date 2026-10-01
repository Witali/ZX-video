"""Resident unsigned PCM8 -> first-order PDM directly in Z80 registers.

No prepared PDM payload and no PDM RAM buffer. Output has a three-bit
pipeline delay; bits 5..7 of port FE are unused by the Spectrum 128 ULA.
"""
from __future__ import annotations
import hashlib
from pdm_player import MiniAssembler,TrdFile,basic_line,place_files,calculate_file_start,spectrum_bitmap_offset
from pdm_player import ORIGIN,CPU_CLOCK,BANKS,BANK_BYTES

OVERSAMPLE=10


def screen(count,oversample):
    from PIL import Image,ImageDraw,ImageFont
    im=Image.new('1',(256,192)); draw=ImageDraw.Draw(im); font=ImageFont.load_default(size=13)
    rows=((25,'BEEPER / LIVE PDM'),(54,'8-BIT PCM IN MEMORY'),(83,'Z80 CONVERTS WHILE PLAYING'),
          (112,f'{oversample} PULSES PER SAMPLE'),(141,f'{count} PCM BYTES'),(168,'LOOP / RESET TO STOP'))
    for y,text in rows:
        box=draw.textbbox((0,0),text,font=font)
        draw.text(((256-(box[2]-box[0]))//2,y),text,font=font,fill=1)
    data=bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x,y)): data[spectrum_bitmap_offset(x//8,y)]|=128>>(x&7)
    return bytes(data)+bytes([0x47])*768


def player(sections,quarter_nops=0,steady=True,canonical_paging=True):
    a=MiniAssembler(ORIGIN); outs=[]
    oversample=OVERSAMPLE if steady else 13
    def pad():
        if steady: a.emit(0x18,0) # JR next: 12 T; no registers or flags changed.
    def word(op,value): a.emit(op); a.word(value)
    def page(bank):
        word(0x01,0x7ffd); a.emit(0x3e,0x10|bank,0xed,0x79)
    def pulse(label):
        # ADD A,D 4; RR E 8; RES 3,E 8; OUT(C),E 12 = 32 T.
        # E[7:5] delays carry three slots; E[3:0] remains zero.
        a.emit(0x82,0xcb,0x1b,0xcb,0x9b)
        a.label(label); outs.append(label); a.emit(0xed,0x59)
    a.label('start'); a.emit(0xf3); word(0x31,0xb800)
    a.emit(0xfd,0x21); a.word(0x5c3a); a.emit(0xed,0x56,0xaf,0xd3,0xfe)
    word(0x21,0x9000); word(0x11,0x4000); word(0x01,6912); a.emit(0xed,0xb0,0xfb)
    for s in sections:
        page(s['bank']); word(0x11,(s['sector']//16)*256+s['sector']%16)
        a.abs16((0xed,0x53),'disk_position'); word(0x21,s['address'])
        a.emit(0x06,s['sectors']); a.abs16(0xcd,'read_n')
    a.emit(0xf3)
    for register in (8,9,10):
        word(0x01,0xfffd); a.emit(0x3e,register,0xed,0x79)
        word(0x01,0xbffd); a.emit(0xaf,0xed,0x79)
    page(sections[0]['bank']); a.emit(0xfb,0x76,0xf3)
    a.label('ready')
    if canonical_paging:
        a.emit(0xd9); word(0x01,0x7ffd); a.emit(0xd9) # BC' is the complete paging address.
    word(0x01,0x10fe); word(0x21,sections[0]['address'])
    a.emit(0x3e,128,0x1e,0) # A modulo error, E three-bit output pipeline.
    a.label('playback')
    for i,s in enumerate(sections):
        a.label(f'loop_{i}'); a.emit(0x56) # LD D,(HL), next unsigned PCM value.
        for sample in range(4):
            for bit in range(oversample):
                pulse(f'out_{i}_{sample}_{bit}')
                if sample==0 and bit==1: a.emit(*([0x00]*quarter_nops))
                if sample==3 and bit==0:
                    # The last sample is already in D; move its page/bank
                    # while the remaining pulses still use that D.
                    a.emit(0x2c); a.abs16(0xca,f'page_tail_{i}') # INC L 4 + JP Z 10.
                elif bit<oversample-1: pad()
            if sample<3: a.emit(0x2c,0x56) # INC L 4 + LD D,(HL) 7.
        a.abs16(0xc3,f'loop_{i}')
        a.label(f'page_tail_{i}')
        pulse(f'out_{i}_page_1'); a.emit(0x24); a.abs16(0xca,f'bank_tail_{i}') # INC H 4 + JP Z 10.
        for bit in range(2,oversample):
            pulse(f'out_{i}_page_{bit}')
            if bit<oversample-1: pad()
        a.abs16(0xc3,f'loop_{i}')
        a.label(f'bank_tail_{i}')
        next_section=sections[(i+1)%len(sections)]
        for bit in range(2,oversample):
            pulse(f'out_{i}_bank_{bit}')
            if bit==2:
                if canonical_paging:
                    # Preserve PCM, accumulator and pipeline in the other set.
                    # EXX 4 + LD E,n 7 + OUT(C),E 12 + EXX 4 = 27 T.
                    # The former 26-T alias can address 1FFD on other models.
                    a.emit(0xd9,0x1e,0x10|next_section['bank'])
                    a.label(f'page_{i}'); a.emit(0xed,0x59,0xd9)
                else:
                    # Historical reproduction only; unsafe on extended decoders.
                    a.emit(0x08,0x3e,0x10|next_section['bank'])
                    a.label(f'page_{i}'); a.emit(0xd3,0xfd,0x08)
            if bit==3: word(0x21,next_section['address']) # 10 T, in a separate slot.
            if 3<bit<oversample-1: pad()
        a.abs16(0xc3,f'loop_{(i+1)%len(sections)}')
    a.label('read_n')
    a.emit(0xc5,0xe5); a.abs16((0xed,0x5b),'disk_position'); word(0x01,0x0105)
    a.label('disk_call'); word(0xcd,0x3d13)
    a.emit(0xe1,0xc1,0x24); a.abs16((0xed,0x5b),'disk_position')
    a.emit(0x1c,0xcb,0x63); a.rel8(0x28,'sector_ok'); a.emit(0x1e,0,0x14)
    a.label('sector_ok'); a.abs16((0xed,0x53),'disk_position'); a.rel8(0x10,'read_n'); a.emit(0xc9)
    a.label('disk_position'); a.word(0)
    code=a.resolve()
    if len(code)>4096: raise ValueError('PCM player overlaps screen staging')
    return code+bytes(4096-len(code))+screen(sum(s['bytes'] for s in sections),oversample),a.labels,outs,len(code)


def build_disk(pcm,quarter_nops=0,steady=True,canonical_paging=True):
    if not pcm or len(pcm)%256 or len(pcm)>98304: raise ValueError('need 1..384 PCM sectors')
    if quarter_nops not in range(9): raise ValueError('quarter_nops must be 0..8')
    if steady and quarter_nops: raise ValueError('clock trim is only available for the fast experiment')
    oversample=OVERSAMPLE if steady else 13
    sections=[]
    for i in range(0,len(pcm),BANK_BYTES):
        size=min(BANK_BYTES,len(pcm)-i)
        sections.append(dict(bank=BANKS[i//BANK_BYTES],sector=0,sectors=size//256,bytes=size,address=65536-size))
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    draft,_,_,_=player(sections,quarter_nops,steady,canonical_paging)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',draft,start=ORIGIN)])
    position=track*16+sector
    for s in sections: s['sector']=position; position+=s['sectors']
    code,labels,outs,code_bytes=player(sections,quarter_nops,steady,canonical_paging)
    files=[boot,TrdFile('PLAYER','C',code,start=ORIGIN)]
    for i,s in enumerate(sections):
        files.append(TrdFile(f'PCM{i}','C',pcm[i*BANK_BYTES:i*BANK_BYTES+s['bytes']],start=s['address']))
    disk,directory,capacity=place_files(files,'LIVEPDM')
    ordinary,page_extra,bank_extra=(441,2,12) if steady else (432+quarter_nops,14,36)
    bank_extra+=int(canonical_paging)
    cycles=len(pcm)*ordinary+page_extra*(len(pcm)//256)+bank_extra*len(sections)
    return disk,dict(origin=ORIGIN,format='unsigned PCM8; no PDM bytes on disk',source_sample_rate_hz=8000,
        pcm_samples=len(pcm),pcm_sha256=hashlib.sha256(pcm).hexdigest(),oversample=oversample,
        bits_per_cycle=len(pcm)*oversample,quarter_nops=quarter_nops,steady=steady,repeat=True,
        canonical_paging=canonical_paging,paging_value_register='e' if canonical_paging else 'a',
        sections=sections,player_labels=labels,output_labels=outs,code_bytes=code_bytes,directory=directory,capacity=capacity,
        cpu_clock_hz=CPU_CLOCK,deterministic_cycle_tstates=cycles,
        nominal_pcm_rate_hz=len(pcm)*CPU_CLOCK/cycles,nominal_pdm_rate_hz=len(pcm)*oversample*CPU_CLOCK/cycles,
        timing=dict(conversion_kernel_tstates=32,ordinary_four_sample_tstates=4*ordinary,
            additional_page_tstates=page_extra,additional_bank_tstates=bank_extra,maximum_native_hold_tstates=max(58+int(canonical_paging),32+4*quarter_nops),
            paging_work_tstates=26+int(canonical_paging),paging_work_delta_tstates=int(canonical_paging),
            baseline_precomputed_kernel_tstates=30,kernel_delta_tstates=2,baseline_precomputed_slot_tstates=46,
            ordinary_average_slot_tstates=ordinary/oversample,excludes='ULA, ROM and disk; measured separately'),
        modulator=dict(order=1,accumulator_bits=8,initial_accumulator=128,initial_pipeline=0,pipeline_delay_bits=3,
            recurrence='sum=error+PCM; carry=sum>>8; error=sum&255; E=((E>>1)|(carry<<7))&0xF7; output=(E>>4)&1'),
        memory=dict(bank_2='8000..8FFF code, 9000..AAFF screen staging, B800 stack',bank_5='screen/BASIC/TR-DOS',
            payload_banks=[s['bank'] for s in sections],pcm_bytes=len(pcm),pdm_buffer_bytes=0,pdm_lookup_table_bytes=0,
            runtime_disk_reads=0),paging_port='7FFD via BC\'' if canonical_paging else '10FD..17FD alias (legacy only)')
