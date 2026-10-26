"""Build the independently bootable Lumiere/Alicia menu disk, without downloads."""
import argparse
import ast
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

from arrangement import timeline

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'audiobook-ay'))
from player import TrdFile, boot_basic, calculate_file_start, place_files, spectrum_bitmap_offset

BANKS = (0, 4, 6, 1, 3, 7)
WAVE_PAGE = 0xAB
SAMPLE_T = 242
CPU_HZ = 3546900
# The score clock follows real 128K ULA fields, not a rounded wall-clock 50.
FIELD_T = 70908
CONTROL_HZ = CPU_HZ/FIELD_T
ROLE_NAMES = ('lead', 'piano_accompaniment', 'bass', 'inner_voice')
AY_LEVELS = (0., .009994659, .014450294, .02105745, .03070115, .04554818,
             .06449989, .1073625, .1265888, .2049897, .2922103, .3728389,
             .4925307, .6353246, .8055848, 1.)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def control_frames(score, mode):
    """Quantize absolute note/envelope times once; retain all playlist entries.

    Four fixed musical roles avoid voice stealing. AY mode uses lead, piano
    and bass. Hybrid uses piano/bass/inner on AY and the lead on beeper DDS.
    Each RLE record is 16 bytes: duration LE16, DDS step LE16, wave-page, AY0..10.
    A zero duration is EOF. Records divide 16 KiB exactly, with no split reads.
    """
    if mode not in ('hybrid', 'ay'):
        raise ValueError('mode must be hybrid or ay')
    voices, duration = timeline(score)
    ticks = math.ceil(duration*CONTROL_HZ)
    gains = json.loads((HERE/'balance.json').read_text())['balance']['role_gain']
    states = [[(0, 0.) for _ in range(4)] for _ in range(ticks)]
    quantization_errors = []
    for role, notes in enumerate(voices):
        for start, length, pitch, instrument, gain in notes:
            if not 1 <= pitch <= 127 or length <= 0:
                raise ValueError('Invalid note')
            first = round(start*CONTROL_HZ)
            stop = min(ticks, round((start+length)*CONTROL_HZ))
            quantization_errors.extend((first/CONTROL_HZ-start, stop/CONTROL_HZ-start-length))
            for tick in range(first, stop):
                age = max(0., tick/CONTROL_HZ-start)
                tail = max(0., start+length-tick/CONTROL_HZ)
                if instrument == 0:
                    amplitude = next(level for when, level in
                                     ((1.2, .1), (.7, .18), (.4, .28), (.2, .4),
                                      (.1, .55), (.04, .74), (0., 1.)) if age >= when)
                else:
                    amplitude = 1. if age >= .065 else (.55 if age >= .025 else .18)
                amplitude *= min(1., tail/.045)*gain*gains[ROLE_NAMES[role]]
                states[tick][role] = (pitch, amplitude)
    frames = []
    for state in states:
        ay = bytearray(11)
        ay[7] = 0x38
        for channel, role in enumerate((1, 2, 3) if mode == 'hybrid' else (0, 1, 2)):
            pitch, amp = state[role]
            period = min(4095, max(1, round(CPU_HZ/2/(16*440*2**((pitch-69)/12))))) if pitch else 1
            ay[channel*2:channel*2+2] = struct.pack('<H', period)
            ay[8+channel] = min(range(16), key=lambda n: abs(AY_LEVELS[n]-amp*.62))
        pitch, amp = state[0]
        step = round(440*2**((pitch-69)/12)*65536/(CPU_HZ/SAMPLE_T)) if pitch and mode == 'hybrid' else 0
        volume = max(0, min(15, round(amp*15))) if mode == 'hybrid' else 0
        frames.append(struct.pack('<HB', step, WAVE_PAGE+volume)+ay)
    packed = bytearray()
    runs = []
    for row in frames:
        if runs and runs[-1][1] == row and runs[-1][0] < 65535:
            runs[-1][0] += 1
        else:
            runs.append([1, row])
    for count, row in runs:
        packed.extend(struct.pack('<H', count)+row)
    packed.extend(bytes(16))
    if len(packed) > len(BANKS)*16384:
        raise ValueError('Song exceeds resident RAM capacity')
    return bytes(packed), dict(ticks=ticks, score_seconds=duration,
        playback_seconds=ticks/CONTROL_HZ, records=len(runs), packed_bytes=len(packed),
        source_notes=[len(v) for v in voices], mode=mode,
        max_note_boundary_error_seconds=max(map(abs, quantization_errors)),
        packed_sha256=sha(packed), frames_sha256=sha(b''.join(frames)))


def screen():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('1', (256, 192))
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=12)
    def label(x, y, text, size=None):
        draw.text((x, y), text, font=ImageFont.load_default(size=size) if size else font, fill=1)
    label(22, 10, 'SPECTRUM MUSIC', 18)
    label(25, 35, 'CLAIR OBSCUR: EXPEDITION 33')
    draw.rectangle((16, 62, 239, 90), outline=1)
    draw.rectangle((16, 94, 239, 122), outline=1)
    label(30, 70, '1   LUMIERE', 16)
    label(30, 102, '2   ALICIA', 16)
    label(18, 135, 'M: AY + PWM')
    label(153, 135, 'M: AY')
    label(16, 153, 'READY')
    label(80, 153, 'LOADING')
    label(160, 153, 'PLAYING')
    label(15, 172, '1/2  6/7+ENTER  SPACE: STOP')
    bitmap = bytearray(6144)
    for y in range(192):
        for x in range(256):
            if im.getpixel((x, y)):
                bitmap[spectrum_bitmap_offset(x//8, y)] |= 128 >> (x & 7)
    return bytes(bitmap)+bytes([0x47])*768


def waves():
    # A band-limited single sinusoid avoids importing large sample banks.
    # Same signed phase for all levels; changing volume never resets DDS.
    return bytes(max(0, min(15, round(8+7*volume/15*math.sin(2*math.pi*i/256))))
                 for volume in range(16) for i in range(256))


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output/'assembly'
    work.mkdir(exist_ok=True)
    variants = []
    for song in ('lumiere', 'alicia'):
        score_data = (HERE/'scores'/f'{song}.json').read_bytes()
        score = json.loads(score_data)
        for mode in ('hybrid', 'ay'):
            data, meta = control_frames(score, mode)
            variants.append((data, dict(meta, song=song, score_sha256=sha(score_data))))
    files = [TrdFile('boot', 'B', boot_basic(), autostart_line=10),
             TrdFile('PLAYER', 'C', bytes(16384), start=0x8000)]
    table = ['variant_table: DEFW variant_0,variant_1,variant_2,variant_3']
    for index, (data, meta) in enumerate(variants):
        table.append(f'variant_{index}:')
        sections = []
        for part, offset in enumerate(range(0, len(data), 16384)):
            payload = data[offset:offset+16384]
            track, sector = calculate_file_start(files)
            sectors = (len(payload)+255)//256
            bank = BANKS[part]
            table.append(f'        DEFB {bank},{sector},{track},{sectors}')
            sections.append(dict(bank=bank, sector=track*16+sector, sectors=sectors, bytes=len(payload)))
            files.append(TrdFile(f'S{index}B{part}', 'C', payload, start=0xC000))
        table.append('        DEFB 255')
        meta['sections'] = sections
        (output/f'{meta["song"]}-{meta["mode"]}.rows').write_bytes(data)
    (work/'variants.inc').write_text('\n'.join(table)+'\n', encoding='ascii', newline='\n')
    (work/'screen.bin').write_bytes(screen())
    (work/'waves.bin').write_bytes(waves())
    source = (HERE/'player.asm').read_bytes().replace(b'\r\n', b'\n')
    (work/'player.asm').write_bytes(source)
    run = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=player.bin',
                          '--lstfile=player.lst', '-s', '.*', 'player.asm'],
                         cwd=work, capture_output=True, text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr, encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    labels = next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    blob = (work/'player.bin').read_bytes()
    assert len(blob) == 16384
    files[1] = TrdFile('PLAYER', 'C', blob, start=0x8000)
    disk, directory, capacity = place_files(files, 'ZXMUSIC')
    (output/'ZX-Music-Menu.trd').write_bytes(disk)
    meta = dict(schema=1, independently_bootable=True, target='Spectrum 128 + Beta Disk',
        variants=[v for _, v in variants], player_labels=labels, directory=directory, capacity=capacity,
        trd_sha256=sha(disk), player_sha256=sha(blob), assembly_sha256=sha(source),
        control_hz=CONTROL_HZ, cpu_hz=CPU_HZ, frame_tstates=FIELD_T,
        tools=dict(pyz80=importlib.metadata.version('pyz80'), pillow=importlib.metadata.version('Pillow')),
        producer_sha256={name:sha((HERE/name).read_bytes()) for name in
                         ('build.py', 'arrangement.py', 'balance.json')},
        pwm_ordinary_tstates=SAMPLE_T, pwm_nominal_carrier_hz=CPU_HZ/SAMPLE_T,
        memory=dict(fixed_code_screen_waves_stack_im2_bank=2, display_basic_trdos_bank=5,
                    available_song_banks=list(BANKS), max_resident_song_bytes=98304),
        timing_scope='Ordinary CPU counts exclude ULA waits, field work, IRQ and disk latency. See verification report.')
    (output/'build.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(trd_sha256=sha(disk), capacity=capacity,
                         variants=[{k:v[k] for k in ('song','mode','records','packed_bytes','playback_seconds')} for _,v in variants]), indent=2))
    return disk, meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/music-menu')
    args = parser.parse_args()
    build(args.output)
