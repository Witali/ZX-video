"""Resident, cold-bootable AY50 preview player for Spectrum 128 + Beta Disk.

All disk reads finish before IM2 playback. R0..R10 are written each field.
No movie player is modified. See README.md for timing and memory contracts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'toolkit'))
from build_zxv_trd import MiniAssembler, TrdFile, basic_line, spectrum_bitmap_offset
from build_streaming_trd import place_files, calculate_file_start

ORIGIN = 0x8000
BANKS = (0, 4, 6, 1, 3)
TICKS_PER_BANK = 16384 // 11
BANK_BYTES = TICKS_PER_BANK * 11


def boot_basic():
    return b''.join([
        basic_line(10, b'\xfd \xb0 "32767"'),
        basic_line(20, b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30, b'\xf9 \xc0 \xb0 "32768"')])


def screen(ticks):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('1', (256, 192))
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=13)
    for y, text in [(28, 'AY AUDIOBOOK'), (55, 'O. HENRY / STORIES (1977)'),
                    (86, f'{ticks / 50:g}-SECOND PREVIEW'), (115, 'THREE VOICES + NOISE'),
                    (137, '50 Hz / RESIDENT AUDIO'), (166, 'RESET TO REPLAY')]:
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((256-(box[2]-box[0]))//2, y), text, font=font, fill=1)
    data = bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x, y)):
                data[spectrum_bitmap_offset(x // 8, y)] |= 128 >> (x & 7)
    return bytes(data) + bytes([0x47]) * 768


def player(ticks, sections):
    a = MiniAssembler(ORIGIN)
    def ld16(op, value):
        a.emit(op); a.word(value)
    def page(bank):
        a.emit(0x3e, 0x10 | bank); ld16(0x01, 0x7ffd); a.emit(0xed, 0x79)
    a.label('start')
    a.emit(0xf3); ld16(0x31, 0xb800)
    a.emit(0xfd, 0x21); a.word(0x5c3a); a.emit(0xed, 0x56)
    a.emit(0xaf, 0xd3, 0xfe)
    ld16(0x21, 0x9000); ld16(0x11, 0x4000); ld16(0x01, 6912); a.emit(0xed, 0xb0)
    a.emit(0xfb)
    for section in sections:
        page(section['bank'])
        ld16(0x11, (section['sector']//16)*256 + section['sector']%16)
        a.abs16((0xed, 0x53), 'disk_position')
        ld16(0x21, 0xc000); a.emit(0x06, section['sectors'])
        a.abs16(0xcd, 'read_n')
    a.emit(0xf3)
    # Initialise every AY register, independently of preceding programs/RAM.
    a.emit(0x16, 0, 0x1e, 0, 0x0e, 0xfd)
    a.label('clear_ay')
    a.emit(0x06, 0xff, 0xed, 0x51, 0x06, 0xbf, 0xed, 0x59, 0x14, 0x7a, 0xfe, 14)
    a.rel8(0x20, 'clear_ay')
    # 257-byte IM2 table; the IRQ changes no registers.
    ld16(0x21, 0xbe00); ld16(0x11, 0xbe01); ld16(0x01, 256)
    a.emit(0x36, 0xbd, 0xed, 0xb0, 0x3e, 0xc3, 0x32); a.word(0xbdbd)
    a.abs16(0x21, 'irq'); a.emit(0x22); a.word(0xbdbe)
    a.emit(0x3e, 0xbe, 0xed, 0x47, 0xed, 0x5e)
    page(BANKS[0])
    ld16(0x21, 0xc000)
    a.label('ready'); a.emit(0xfb)
    a.label('wait_field'); a.emit(0x76)
    a.label('field_start')
    a.abs16((0xed, 0x5b), 'remaining')
    a.emit(0x7a, 0xb3); a.abs16(0xca, 'finished')
    a.label('tick_start')
    a.emit(0x16, 0, 0x0e, 0xfd)
    a.label('write_register')
    # 78 T per continuing register, 73 T for the last register.
    a.emit(0x5e, 0x23, 0x06, 0xff, 0xed, 0x51, 0x06, 0xbf)
    a.label('ay_out'); a.emit(0xed, 0x59)
    a.emit(0x14, 0x7a, 0xfe, 11); a.rel8(0x20, 'write_register')
    a.label('tick_end')
    a.abs16((0xed, 0x5b), 'remaining'); a.emit(0x1b)
    a.abs16((0xed, 0x53), 'remaining')
    # A bank always ends on a whole eleven-register tick; no cross-bank read.
    a.emit(0x7c, 0xfe, 0xff); a.rel8(0x20, 'wait_field')
    a.emit(0x7d, 0xfe, 0xfb); a.rel8(0x20, 'wait_field')
    # Do not page past the bank table after the last tick at an exact boundary.
    a.emit(0x7a, 0xb3); a.rel8(0x28, 'wait_field')
    a.abs16(0x2a, 'bank_pointer'); a.emit(0x23); a.abs16(0x22, 'bank_pointer')
    a.emit(0x7e); ld16(0x01, 0x7ffd); a.emit(0xed, 0x79)
    ld16(0x21, 0xc000); a.rel8(0x18, 'wait_field')
    a.label('finished')
    a.emit(0x1e, 0, 0x0e, 0xfd)
    for reg in (8, 9, 10):
        a.emit(0x16, reg, 0x06, 0xff, 0xed, 0x51, 0x06, 0xbf, 0xed, 0x59)
    a.label('finished_wait'); a.emit(0x76); a.rel8(0x18, 'finished_wait')
    a.label('irq'); a.emit(0xfb, 0xed, 0x4d)
    # Same one-sector TR-DOS 3D13/05 bootstrap contract as fap3_disk_z80.
    a.label('read_n')
    a.emit(0xc5, 0xe5); a.abs16((0xed, 0x5b), 'disk_position')
    ld16(0x01, 0x0105)
    a.label('disk_call'); ld16(0xcd, 0x3d13)
    a.emit(0xe1, 0xc1, 0x24)
    a.abs16((0xed, 0x5b), 'disk_position')
    a.emit(0x1c, 0xcb, 0x63); a.rel8(0x28, 'sector_ok')
    a.emit(0x1e, 0, 0x14)
    a.label('sector_ok'); a.abs16((0xed, 0x53), 'disk_position')
    a.rel8(0x10, 'read_n'); a.emit(0xc9)
    a.label('remaining'); a.word(ticks)
    a.label('disk_position'); a.word(0)
    a.label('bank_pointer'); a.abs_fixups.append((len(a.code), 'bank_table')); a.word(0)
    a.label('bank_table'); a.emit(*(0x10 | b for b in BANKS))
    code = a.resolve()
    if len(code) > 4096:
        raise ValueError('code overlaps resident screen data')
    return code + bytes(4096-len(code)) + screen(ticks), dict(a.labels)


def build_disk(registers):
    if not registers or len(registers) % 11 or len(registers) > 5 * BANK_BYTES:
        raise ValueError('expected 1..7445 whole AY ticks')
    for i in range(0, len(registers), 11):
        row = registers[i:i+11]
        if any(row[j] > 15 for j in (1, 3, 5, 8, 9, 10)) or row[6] > 31 or row[7] > 63:
            raise ValueError('invalid AY registers')
    ticks = len(registers) // 11
    sections = [dict(bank=BANKS[i//BANK_BYTES], sector=0,
                     sectors=(len(registers[i:i+BANK_BYTES])+255)//256,
                     bytes=len(registers[i:i+BANK_BYTES]))
                for i in range(0, len(registers), BANK_BYTES)]
    boot = TrdFile('boot', 'B', boot_basic(), autostart_line=10)
    draft, _ = player(ticks, sections)
    track, sector = calculate_file_start([boot, TrdFile('PLAYER', 'C', draft, start=ORIGIN)])
    position = track * 16 + sector
    for s in sections:
        s['sector'] = position; position += s['sectors']
    code, labels = player(ticks, sections)
    files = [boot, TrdFile('PLAYER', 'C', code, start=ORIGIN)]
    for i, section in enumerate(sections):
        files.append(TrdFile(f'AUDIO{i}', 'C', registers[i*BANK_BYTES:(i+1)*BANK_BYTES], start=0xc000))
    disk, directory, capacity = place_files(files, 'AYBOOK')
    return disk, dict(origin=ORIGIN, ticks=ticks, duration_seconds=ticks/50,
        player_labels=labels, sections=sections, directory=directory, capacity=capacity,
        registers_sha256=hashlib.sha256(registers).hexdigest(),
        timing=dict(tick_start_to_tick_end_tstates=867, field_check_tstates=38,
                    irq_body_tstates=18, im2_ack_tstates=19,
                    register_loop_continue_tstates=78, register_loop_last_tstates=73,
                    nominal_field_tstates=70908,
                    excludes='ULA contention, HALT wait and boot-only TR-DOS/physical latency'),
        memory=dict(bank_5='screen, BASIC and TR-DOS workspace',
                    bank_2='8000 code; 9000..AAFF screen; B800 stack top; BDBD vector; BE00..BF00 IM2 table',
                    data_banks=list(BANKS), bank_7='spare; never required from a preceding disk',
                    runtime_disk_reads=0))
