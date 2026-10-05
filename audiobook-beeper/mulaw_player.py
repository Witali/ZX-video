"""Build a compact G.711 mu-law / exact PCM16 first-order PDM player."""
import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
from g711_codec import decode_table
from feedback_player import loading_screen
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files, spectrum_bitmap_offset

HERE = Path(__file__).resolve().parent
CPU = 3546900
RESERVE = 2048
REGIONS = [(b, 0xc000, 16384) for b in (0, 4, 6, 1, 3)] + [
    (7, 0xdb00, 9472), (2, 0xc800, 14336), (5, 0xc000, 7168), (5, 0xe000, 8192)]
CAPACITY = sum(size for _, _, size in REGIONS)
HOLDS = [53, 53, 53, 53, 56, 55, 55, 54]


def layout(payload):
    if not payload or len(payload) % 256 or len(payload) > CAPACITY:
        raise ValueError('mu-law payload must be nonempty, sector aligned and fit resident RAM')
    sections = []
    left = len(payload)
    for bank, address, size in REGIONS:
        count = min(left, size)
        if count:
            sections.append(dict(bank=bank, address=address, bytes=count, sectors=count//256,
                                 end_high=((address+count) >> 8) & 255))
        left -= count
    return sections


def intervals(meta):
    result = np.tile(HOLDS, meta['pcm_samples']).astype(np.int64)
    end = 0
    for section in meta['sections']:
        for n in range(256, section['bytes']+1, 256):
            # Prefetch advances the source one sample ahead of the output.
            result[(end+n-2)*8+4] += 116 if n == section['bytes'] else 35
        end += section['bytes']
    return result


def screen(count):
    from PIL import Image, ImageDraw, ImageFont
    data = bytearray(loading_screen(count, 'MU-LAW / LIVE PDM'))
    tile = Image.new('1', (256, 24)); draw = ImageDraw.Draw(tile)
    font = ImageFont.load_default(size=13); text = '8-BIT G.711 IN MEMORY'
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((256-box[2]+box[0])//2, 6), text, font=font, fill=1)
    for y in range(24):
        for col in range(32):
            data[spectrum_bitmap_offset(col, y+48)] = sum(128 >> b for b in range(8) if tile.getpixel((col*8+b, y)))
    return bytes(data)


def build_disk(payload, work):
    work = Path(work).resolve(); work.mkdir(parents=True, exist_ok=True)
    sections = layout(payload)
    basic = b''.join([basic_line(10, b'\xfd \xb0 "32767"'),
        basic_line(20, b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30, b'\xf9 \xc0 \xb0 "32768"')])
    boot = TrdFile('boot', 'B', basic, autostart_line=10)
    track, sector = calculate_file_start([boot, TrdFile('PLAYER', 'C', bytes(RESERVE+6912), start=0x8000)])
    pos = track*16+sector
    for s in sections:
        s['sector'] = pos; pos += s['sectors']
    reads = sum(s['sectors'] for s in sections)
    steps = np.diff(np.r_[0, (np.arange(1,33)*reads+31)//32])
    # Short clips still have 32 real progress steps; minimum one second.
    if np.any(steps <= 0):
        raise ValueError('mu-law demo needs at least 8192 samples for loading progress')
    config = dict(first_address=sections[0]['address'], first_end_high=sections[0]['end_high'], progress_first=int(steps[0]))
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in config.items()))
    (work/'loads.inc').write_text(''.join(f'        LOAD_AUDIO {s["bank"]},{s["sector"]//16*256+s["sector"]%16},{s["address"]},{s["sectors"]}\n' for s in sections))
    tails = []
    for i in range(len(sections)):
        j=(i+1)%len(sections); s=sections[j]
        tails.append(f'        BANK_TAIL {i},{s["bank"]},{s["address"]},{j},{s["end_high"]}\n')
    (work/'tails.inc').write_text(''.join(tails))
    levels = decode_table('mulaw').astype(np.int32)+32768
    (work/'levels.bin').write_bytes((levels&255).astype('u1').tobytes()+(levels>>8).astype('u1').tobytes())
    (work/'screen.bin').write_bytes(screen(len(payload)))
    (work/'progress-steps.bin').write_bytes(bytes(steps[1:].astype('u1'))+b'\xff')
    (work/'player.asm').write_bytes((HERE/'mulaw-player.asm').read_bytes())
    run = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=player.bin', '--lstfile=player.lst', '-s', '.*', 'player.asm'], cwd=work, capture_output=True, text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    labels = next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    blob = (work/'player.bin').read_bytes()
    assert len(blob) == RESERVE+6912
    files = [boot, TrdFile('PLAYER','C',blob,start=0x8000)]
    offset = 0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'ULAW{i}', 'C', payload[offset:offset+s['bytes']], start=s['address']))
        offset += s['bytes']
    disk, directory, capacity = place_files(files, 'MULAW')
    meta = dict(codec='mulaw', source_sample_rate_hz=8000, cpu_clock_hz=CPU,
        pcm_samples=len(payload), outputs_per_cycle=len(payload)*8, oversample=8,
        sections=sections, player_labels=labels, paging_base=24,
        record_stop_addresses=[labels['out_0']+2], repeat=True,
        directory=directory, capacity=capacity, resident_reserve=RESERVE,
        ordinary_tstates=sum(HOLDS), ordinary_delta_vs_ima3_tstates=sum(HOLDS)-427.375,
        page_extra_tstates=35, bank_extra_tstates=116,
        modulator=dict(order=1, accumulator_bits=16, decoded_level_bits=16, lookup_bytes=512),
        playback_preload_sector_reads=reads, loading_progress_steps=32,
        memory=dict(total_ram_bytes=131072, maximum_audio_bytes=CAPACITY,
                    audio_bytes=len(payload), unused_audio_bytes=CAPACITY-len(payload),
                    shadow_screen_bytes=6912, trdos_workspace_and_load_stack_bytes=1024,
                    resident_code_table_and_play_stack_bytes=RESERVE,
                    pcm_audio_buffer_bytes=0, pdm_buffer_bytes=0, staged_sample_bytes=2),
        payload_sha256=hashlib.sha256(payload).hexdigest(), binary_sha256=hashlib.sha256(blob).hexdigest())
    meta['deterministic_cycle_tstates'] = int(intervals(meta).sum())
    return disk, meta
