"""Package an externally assembled, looping AY player for arbitrary audio."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unicodedata

from trd import boot_basic, TrdFile, calculate_file_start, place_files, spectrum_bitmap_offset

ORIGIN = 0x8000
BANKS = (0, 4, 6, 1, 3, 7)
TICKS_PER_BANK = 16384 // 11
BANK_BYTES = TICKS_PER_BANK * 11
MAX_TICKS = len(BANKS) * TICKS_PER_BANK


def screen(ticks, title, loop):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('1', (256, 192))
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=13)
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().strip().upper() or 'AUDIO PREVIEW'
    while draw.textbbox((0, 0), title, font=font)[2] > 240:
        title = title[:-1]
    for y, text in ((8, 'LOADING AUDIO DATA'), (28, 'AY MUSIC'), (55, title),
                    (86, f'{ticks / 50:g}-SECOND PREVIEW'), (115, 'THREE VOICES + NOISE'),
                    (137, '50 Hz / RESIDENT AUDIO'),
                    (166, 'LOOP / RESET TO STOP' if loop else 'RESET TO REPLAY')):
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((256-(box[2]-box[0]))//2, y), text, font=font, fill=1)
    data = bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x, y)):
                data[spectrum_bitmap_offset(x//8, y)] |= 128 >> (x & 7)
    return bytes(data) + bytes([0x47])*768


def build_disk(registers, *, title='AUDIO PREVIEW', loop=True, assembly_dir=None):
    if not registers or len(registers) % 11 or len(registers) > MAX_TICKS*11:
        raise ValueError(f'expected 1..{MAX_TICKS} whole AY ticks')
    for i in range(0, len(registers), 11):
        row = registers[i:i+11]
        if any(row[j] > 15 for j in (1, 3, 5, 8, 9, 10)) or row[6] > 31 or row[7] > 63:
            raise ValueError('invalid AY registers')
    ticks = len(registers)//11
    sections = [dict(bank=BANKS[i//BANK_BYTES], sector=0,
                     sectors=(len(registers[i:i+BANK_BYTES])+255)//256,
                     bytes=len(registers[i:i+BANK_BYTES]))
                for i in range(0, len(registers), BANK_BYTES)]
    boot = TrdFile('boot', 'B', boot_basic(), autostart_line=10)
    # The fixed 8000..AAFF loader image makes disk positions known pre-assembly.
    track, sector = calculate_file_start([boot, TrdFile('PLAYER', 'C', bytes(11008), start=ORIGIN)])
    position = track*16+sector
    for part in sections:
        part['sector'] = position
        position += part['sectors']

    def assemble(work):
        work.mkdir(parents=True, exist_ok=True)
        config = [f'total_ticks: EQU {ticks}', f'loop_playback: EQU {int(loop)}']
        for i in range(len(BANKS)):
            part = sections[i] if i < len(sections) else dict(sector=0, sectors=0)
            config += [f'disk_{i}: EQU {(part["sector"]//16)*256+part["sector"]%16}',
                       f'sectors_{i}: EQU {part["sectors"]}']
        (work/'config.inc').write_text('\n'.join(config)+'\n', encoding='ascii', newline='\n')
        source = Path(__file__).with_name('ay-player.asm').read_bytes().replace(b'\r\n', b'\n')
        (work/'ay-player.asm').write_bytes(source)
        (work/'screen.bin').write_bytes(screen(ticks, title, loop))
        command = [sys.executable, '-m', 'pyz80.pyz80', '--obj=player.bin',
                   '--lstfile=player.lst', '-s', '.*', 'ay-player.asm']
        run = subprocess.run(command, cwd=work, capture_output=True, text=True)
        (work/'assembler.log').write_text(run.stdout+run.stderr, encoding='utf-8', newline='\n')
        if run.returncode:
            raise RuntimeError(run.stdout+run.stderr)
        labels = next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
        blob = (work/'player.bin').read_bytes()
        assert len(blob) == 11008 and labels['screen_data'] == 0x9000
        return blob, labels, dict(assembler='pyz80', instruction_bytes_emitted_by_python=False,
                                 source_sha256_lf=hashlib.sha256(source).hexdigest(),
                                 binary_sha256=hashlib.sha256(blob).hexdigest())
    if assembly_dir is None:
        with tempfile.TemporaryDirectory(prefix='ay-assembly-') as temp:
            blob, labels, assembly = assemble(Path(temp))
    else:
        blob, labels, assembly = assemble(Path(assembly_dir).resolve())
    files = [boot, TrdFile('PLAYER', 'C', blob, start=ORIGIN)]
    for i, part in enumerate(sections):
        files.append(TrdFile(f'AUDIO{i}', 'C', registers[i*BANK_BYTES:(i+1)*BANK_BYTES], start=0xc000))
    disk, directory, capacity = place_files(files, 'AYMUSIC')
    return disk, dict(origin=ORIGIN, ticks=ticks, duration_seconds=ticks/50,
        loop_playback=loop, disk_filename='audio-preview.trd', player_labels=labels,
        sections=sections, directory=directory, capacity=capacity, assembly=assembly,
        loading_message='LOADING AUDIO DATA', loading_bitmap_rows=24,
        registers_sha256=hashlib.sha256(registers).hexdigest(),
        timing=dict(ordinary_field_work_tstates=974, ordinary_delta_tstates=0,
                    near_boundary_tstates=992, bank_change_tstates=1091,
                    exact_boundary_eof_tstates=1007, loop_restart_extra_tstates=105,
                    loop_first_field_tstates=1079, tick_start_to_tick_end_tstates=867,
                    irq_body_tstates=18, im2_ack_tstates=19, vector_jump_tstates=10,
                    nominal_field_tstates=70908,
                    excludes='ULA contention, HALT wait, boot ROM and physical disk latency'),
        memory=dict(bank_5='display, BASIC and TR-DOS workspace',
                    bank_2='8000..8FFF code; 9000..AAFF screen copy; stack below B800; BDBD vector; BE00..BF00 IM2',
                    data_banks=list(BANKS), capacity_register_bytes=MAX_TICKS*11,
                    unused_data_tail_bytes_per_bank=5, runtime_disk_reads=0))
