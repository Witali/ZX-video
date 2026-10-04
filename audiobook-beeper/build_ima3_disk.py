"""Bootable blockwise IMA3 preload followed by the unchanged direct PDM player."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import numpy as np

from build_lpc_disk import assemble, disk_address
from convert_audio import pcm_wav
from direct_player import build_disk, MEASURED_MODEL
from pcm_player import TrdFile, basic_line, calculate_file_start, place_files, spectrum_bitmap_offset
from verify_pcm import save

HERE = Path(__file__).resolve().parent


def compress(packed):
    """Losslessly transport the even-nibble IMA subset; reject other streams."""
    data = np.frombuffer(packed, 'u1')
    assert not np.any(data & 0x11), 'IMA3 transport requires even IMA nibbles'
    codes = np.column_stack(((data & 15) >> 1, data >> 5)).ravel()
    assert len(codes) % 8 == 0
    return np.packbits(((codes[:, None] >> np.array([2, 1, 0])) & 1).ravel()).tobytes()


def progress_screen():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('1', (256, 192)); draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=12)
    for y, label in ((12, '3-BIT IMA / PDM AUDIO'), (34, 'LOADING AUDIO DATA'),
                     (62, 'READ COMPRESSED AUDIO'), (106, 'EXPAND TO 4-BIT IMA'),
                     (151, 'PLAYBACK STARTS WHEN READY'), (174, 'SPECTRUM 128 / BEEPER')):
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(((256-box[2])//2, y), label, font=font, fill=1)
    data = bytearray(6912)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x, y)): data[spectrum_bitmap_offset(x//8, y)] |= 128 >> (x & 7)
    data[6144:] = bytes([0x47])*768
    for row in (10, 16): data[6144+row*32:6144+(row+1)*32] = bytes([0x49])*32
    return bytes(data)


def write_candidate(out, packed, source, hot=None, pairs=0, pad=0):
    out.mkdir(parents=True, exist_ok=True)
    _, meta = build_disk(packed, out/'assembly', MEASURED_MODEL, hot, pairs, pad)
    work = out/'assembly'
    compressed = compress(packed)
    chunks = []; payload = bytearray(); offset = 0
    for section in meta['sections']:
        for pos in range(0, section['bytes'], 8192):
            size = min(8192, section['bytes']-pos)
            block = compress(packed[offset:offset+size]); sectors = (len(block)+255)//256
            offset += size
            chunks.append(dict(bank=section['bank'], address=section['address']+pos,
                               bytes=size, input_bytes=len(block), sectors=sectors, groups=size//4,
                               output_end=offset, disk_offset=len(payload)//256,
                               unpack_target=offset*32//len(packed)))
            payload.extend(block + bytes(sectors*256-len(block)))
    assert offset == len(packed) and len(payload)//256 >= 32
    basic = b''.join([basic_line(10, b'\xfd \xb0 "32767"'),
        basic_line(20, b'\xf9 \xc0 \xb0 "15619":\xea:\xef "IMA3BOOT" \xaf'),
        basic_line(30, b'\xf9 \xc0 \xb0 "32768"')])
    files = [TrdFile('boot', 'B', basic, autostart_line=10),
             TrdFile('IMA3BOOT', 'C', bytes(0x2F00), start=0x8000),
             TrdFile('PLAYER', 'C', bytes(23296), start=0x8000),
             TrdFile('LOWER', 'C', (work/'bank5-lower.bin').read_bytes(), start=0x4000),
             TrdFile('UPPER', 'C', (work/'bank5-upper.bin').read_bytes(), start=0x6000)]
    # A TR-DOS directory entry has a16-bit length. Split the physical payload
    # into <=60-KiB files; the preloader reads their contiguous sector extent.
    for i, start in enumerate(range(0, len(payload), 60*1024)):
        files.append(TrdFile('IMA3DAT'+str(i), 'C', bytes(payload[start:start+60*1024]), start=0x6000))
    starts = []
    for i in range(len(files)):
        track, sector = calculate_file_start(files[:i]); starts.append(track*16+sector)
    replacement = dict(lpc_preloaded=1, screen_disk=disk_address(starts[2]+64),
                       lower_disk=disk_address(starts[3]), upper_disk=disk_address(starts[4]))
    lines = (work/'config.inc').read_text().splitlines()
    (work/'config.inc').write_text('\n'.join(
        f'{line.split(":")[0]}: EQU {replacement[line.split(":")[0]]}'
        if line.split(':')[0] in replacement else line for line in lines)+'\n')
    player_labels = assemble(work, 'player')
    config = dict(audio_disk=disk_address(starts[5]), player_disk=disk_address(starts[2]),
                  chunk_count=len(chunks), trampoline_size=0)
    def write_config():
        (work/'ima3-config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k, v in config.items()))
    write_config()
    shutil.copy2(HERE/'ima3-handoff.asm', work/'trampoline.asm'); trampoline_labels = assemble(work, 'trampoline')
    config['trampoline_size'] = (work/'trampoline.bin').stat().st_size; write_config()
    (work/'chunks.bin').write_bytes(b''.join(struct.pack('<BHBHB', c['bank'], c['address'],
        c['sectors'], c['groups'], c['unpack_target']) for c in chunks))
    sectors = len(payload)//256
    (work/'load-thresholds.bin').write_bytes(struct.pack('<32H', *((sectors*i+31)//32 for i in range(1, 33))))
    tables = bytes(((v>>4)&14)|((v<<3)&224) for v in range(256))
    tables += bytes(((v>>6)&2)|((v<<1)&224) for v in range(256))
    tables += bytes((v&14)|((v&1)<<7) for v in range(256))
    tables += bytes(((v>>2)&14)|((v<<5)&224) for v in range(256))
    (work/'lookup.bin').write_bytes(tables)
    (work/'progress-screen.bin').write_bytes(progress_screen())
    shutil.copy2(HERE/'ima3-preload.asm', work/'ima3-preload.asm'); labels = assemble(work, 'ima3-preload')
    preloader = (work/'ima3-preload.bin').read_bytes(); assert len(preloader) == 0x2F00
    player = (work/'player.bin').read_bytes(); assert len(player) == 23296
    files[1] = TrdFile('IMA3BOOT', 'C', preloader, start=0x8000)
    files[2] = TrdFile('PLAYER', 'C', player, start=0x8000)
    disk, directory, capacity = place_files(files, 'IMA3PDM')
    meta.update(player_labels=player_labels, directory=directory, capacity=capacity,
        binary_sha256=hashlib.sha256(player).hexdigest(), compensated_reference_rate_hz=8000,
        playback_preload_sector_reads=87, loading_display_sector_reads=27,
        preload=dict(format='IMA3 even-nibble subset', labels=labels, trampoline_labels=trampoline_labels,
            compressed_bytes=len(compressed), ima_bytes=len(packed), chunks=chunks,
            source_sector=starts[5], load_sectors=sectors, preloader_sector=starts[1],
            preloader_size=len(preloader), playback_instruction_delta_tstates=0,
            core_tstates_per_eight_samples=285, chunk_buffer_bytes=6144,
            memory=dict(input=[0x6000, 0x77FF], lookup=[0x9000, 0x93FF],
                        screen_data=[0x9400, 0xAEFF], code_end=labels['code_end'])))
    save(out/'player.json', meta); (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed, mtime=0))
    (out/'soundtrack.ima3.gz').write_bytes(gzip.compress(compressed, mtime=0))
    pcm_wav(out/'source-preview.wav', source)
    return disk, meta


def main():
    import wave
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path, help='prior IMA3 expansion archive')
    p.add_argument('--source-wav', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--fuse', type=Path, help='calibrate both playback loops on the actual disk')
    a = p.parse_args()
    if a.output.exists() and any(a.output.iterdir()): p.error('output must be empty')
    packed = gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes())
    with wave.open(str(a.source_wav), 'rb') as w:
        assert w.getsampwidth() == w.getnchannels() == 1 and w.getframerate() == 8000
        source = np.frombuffer(w.readframes(w.getnframes()), 'u1')
    assert len(source) == len(packed)*2
    if a.fuse:
        from convert_audio import calibrate
        selected, meta = calibrate(a.output/'calibration', packed, source, a.fuse, writer=write_candidate)
        for name in ('player.json', 'audiobook-preview.trd', 'soundtrack.ima.gz', 'soundtrack.ima3.gz',
                     'source-preview.wav', 'phase-probe.json'):
            shutil.copy2(selected/name, a.output/name)
        shutil.copytree(selected/'assembly', a.output/'assembly')
    else:
        _, meta = write_candidate(a.output, packed, source)
    print(json.dumps(dict(output=str(a.output), preload=meta['preload'], capacity=meta['capacity'])), flush=True)


if __name__ == '__main__': main()
