"""Resident IMA4 -> PCM16 -> PCM8 -> live PDM, interleaved on the Z80."""
from __future__ import annotations
import hashlib
from pcm_player import TrdFile,basic_line,place_files,calculate_file_start,spectrum_bitmap_offset
from pdm_player import ORIGIN,CPU_CLOCK,BANKS,BANK_BYTES
from ima_codec import decoder_table,require_unclipped


def screen(samples):
    from PIL import Image,ImageDraw,ImageFont
    im=Image.new('1',(256,192)); draw=ImageDraw.Draw(im); font=ImageFont.load_default(size=13)
    for y,text in ((25,'IMA ADPCM / LIVE PDM'),(54,'4-BIT AUDIO IN MEMORY'),(83,'DECODE AND PLAY ON Z80'),
                   (112,'8000 Hz / MONO SOURCE'),(141,f'{samples} SAMPLES'),(168,'LOOP / RESET TO STOP')):
        box=draw.textbbox((0,0),text,font=font)
        draw.text(((256-(box[2]-box[0]))//2,y),text,font=font,fill=1)
    data=bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x,y)): data[spectrum_bitmap_offset(x//8,y)]|=128>>(x&7)
    return bytes(data)+bytes([0x47])*768


def program(sections,initial_predictor=0,initial_index=0,assembly_dir=None,uniform=False):
    """Assemble authoritative ASM externally, then read its unchanged binary.

    Python emits only constants/table/screen data. It does not emit or patch
    any Z80 instruction, including disk sector addresses and predictor seed.
    """
    import ast,subprocess,sys,tempfile
    from pathlib import Path
    if not -32768<=initial_predictor<=32767 or not 0<=initial_index<=88:
        raise ValueError('invalid IMA initial state')
    if [s['bank'] for s in sections]!=[0,4,6,1,3,7,2,5]:
        raise ValueError('ASM requires the documented eight-bank layout')
    def assemble(work):
        work.mkdir(parents=True,exist_ok=True)
        source=Path(__file__).with_name('ima-uniform-player.asm' if uniform else 'ima-player.asm').read_text()
        (work/'ima-player.asm').write_text(source,encoding='utf-8',newline='\n')
        config=[f'initial_predictor: EQU {initial_predictor}',f'initial_index: EQU {initial_index}']
        for i,s in enumerate(sections):
            config.extend([f'disk_{i}: EQU {(s["sector"]//16)*256+s["sector"]%16}',
                           f'address_{i}: EQU {s["address"]}',f'sectors_{i}: EQU {s["sectors"]}'])
        (work/'config.inc').write_text('\n'.join(config)+'\n',encoding='ascii')
        table=decoder_table(0x8600,sign_tags=not uniform)
        (work/'decoder-table.bin').write_bytes(table)
        (work/'screen.bin').write_bytes(screen(2*sum(s['bytes'] for s in sections)))
        command=[sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','ima-player.asm']
        result=subprocess.run(command,cwd=work,capture_output=True,text=True)
        (work/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode: raise RuntimeError('ASM failed: '+result.stdout+result.stderr)
        symbols=next(ast.literal_eval(line) for line in result.stdout.splitlines() if line.startswith('{'))
        blob=(work/'player.bin').read_bytes()
        if len(blob)!=14336 or symbols['tables']!=0x8600 or symbols['screen_data']!=0x9d00:
            raise AssertionError('assembled memory layout changed')
        meta=dict(code_bytes=symbols['code_end']-ORIGIN,code_reserve=1536,resident_reserve=7424,
            table_base=symbols['tables'],table_bytes=len(table),player_labels=symbols,
            output_labels=[k for k in symbols if '_out' in k],
            sample_labels=[k for k in symbols if k.endswith('_clipped')],
            mutable_addresses=[symbols['bank_candidate'],symbols['disk_position'],symbols['disk_position']+1],
            assembly=dict(assembler='pyz80 1.3.0',command=command[1:],
                source_sha256_lf=hashlib.sha256(source.replace('\r\n','\n').encode()).hexdigest(),
                binary_sha256=hashlib.sha256(blob).hexdigest(),binary_bytes=len(blob),
                instruction_bytes_emitted_by_python=False))
        return blob,meta
    if assembly_dir is not None: return assemble(Path(assembly_dir).resolve())
    with tempfile.TemporaryDirectory(prefix='ima-assembly-') as directory:
        return assemble(Path(directory))


def layout():
    # ASM asserts this layout; all 128 KiB include screen, ROM workspace and stack.
    reserve=7424
    sections=[]
    for bank in (*BANKS,2,5):
        size=8192 if bank==5 else BANK_BYTES-reserve if bank==2 else BANK_BYTES
        sections.append(dict(bank=bank,bytes=size,sectors=size//256,address=65536-size,sector=0))
    return sections,reserve


def build_disk(packed,initial_predictor=0,initial_index=0,assembly_dir=None,uniform=False):
    sections,reserve=layout()
    if len(packed)!=sum(s['bytes'] for s in sections): raise ValueError('IMA payload must fill available sectors')
    guard=require_unclipped(packed,initial_predictor,initial_index) if uniform else None
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    draft=bytes(reserve+6912)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',draft,start=ORIGIN)])
    position=track*16+sector
    for s in sections: s['sector']=position; position+=s['sectors']
    blob,meta=program(sections,initial_predictor,initial_index,assembly_dir,uniform=uniform)
    files=[boot,TrdFile('PLAYER','C',blob,start=ORIGIN)]; offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+s['bytes']],start=s['address'])); offset+=s['bytes']
    disk,directory,capacity=place_files(files,'IMAPDM')
    # recorder's first output label and safe stop offset; not the PCM player's verifier.
    meta['player_labels']['out_0_0_0']=meta['player_labels']['high_out0']
    meta.update(origin=ORIGIN,sections=sections,directory=directory,capacity=capacity,
        format='IMA ADPCM4, low nibble first, reference shift/add rounding (IMA-WAV); headerless resident stream',
        initial_predictor=initial_predictor,initial_index=initial_index,packed_bytes=len(packed),pcm_samples=2*len(packed),
        source_sample_rate_hz=8000,predictor_bits=16,pdm_input_bits=8,repeat=True,steady=True,
        paging_value_register='a',canonical_paging=True,stack_top=0x6000,
        pdm_kernel_tstates=32,pdm_isolated_tstates=40,pdm_isolation_delta_tstates=8,
        ordinary_low_tstates=439,ordinary_high_tstates=437,maximum_native_hold_tstates=79,
        memory=dict(total_ram_bytes=131072,adpcm_bytes=len(packed),resident_code_and_tables=reserve,
                    screen_bytes=6912,workspace_stack_bytes=1280,pcm_buffer_bytes=0,pdm_buffer_bytes=0),
        pcm_clock_nominal_hz=CPU_CLOCK/438,packed_sha256=hashlib.sha256(packed).hexdigest())
    if uniform:
        meta.update(uniform_timing=True,saturation_guard=guard,ordinary_low_tstates=438,
                    ordinary_high_tstates=438,maximum_native_hold_tstates=77)
    return disk,meta
