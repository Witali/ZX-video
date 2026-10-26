"""Build an AY-only, fully cached, interactive Spectrum128 music disk."""
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
from zx_text import menu_stream

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'audiobook-ay'))
from player import TrdFile, boot_basic, calculate_file_start, place_files, spectrum_bitmap_offset

BANKS = (0, 4, 6, 1, 3, 7)
CPU_HZ = 3546900
FIELD_T = 70908
CONTROL_HZ = CPU_HZ/FIELD_T
ROLE_NAMES = ('lead', 'piano_accompaniment', 'bass', 'inner_voice')
AY_LEVELS = (0., .009994659, .014450294, .02105745, .03070115, .04554818,
             .06449989, .1073625, .1265888, .2049897, .2922103, .3728389,
             .4925307, .6353246, .8055848, 1.)
TRIANGLE_MAX_CENTS = 18
# The mask describes these slots, not numerical register order. Prepare the
# oscillators/envelope before enabling a channel's new volume or ENV bit.
REGISTER_ORDER = (0,1,2,3,4,5,6,7,11,12,13,8,9,10)
# Silence first, clear the envelope counter before restoring a nonzero period,
# and park unused generators cheaply. Zero envelope periods accumulate a
# counter backlog in Fuse's AY renderer before a later nonzero period write.
MUTE_WRITES = ((8,0),(9,0),(10,0),(13,0),(7,63),(6,31),(11,255),(12,255),
               (0,0),(1,0),(2,0),(3,0),(4,0),(5,0))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def triangle_period(pitch):
    """A full up/down envelope is 64 internal steps at chip_clock/8."""
    frequency = 440*2**((pitch-69)/12)
    period = max(1, round((CPU_HZ/2)/(512*frequency)))
    cents = 1200*math.log2((CPU_HZ/2)/(512*period)/frequency)
    return period, cents


def pack_frames(frames):
    """Duration U8 + changed-register mask LE16 + ascending changed values.

    Mask slots follow REGISTER_ORDER; R13 is an explicit envelope restart.
    FF for R13 is a host sentinel only. It is never written to the chip.
    Long holds split at 255 fields. A zero duration is the single-byte EOF.
    """
    runs = []
    for row in frames:
        if runs and row[13]==255 and runs[-1][1][:13]==row[:13] and runs[-1][0]<255:
            runs[-1][0] += 1
        else:
            runs.append([1, row])
    data = bytearray()
    previous = None
    writes = 0
    for duration,row in runs:
        mask = sum(1<<slot for slot,reg in enumerate(REGISTER_ORDER)
                   if (row[reg]!=255 if reg==13 else previous is None or row[reg]!=previous[reg]))
        values = bytes(row[reg] for slot,reg in enumerate(REGISTER_ORDER) if mask&(1<<slot))
        data.extend(bytes([duration])+struct.pack('<H',mask)+values)
        writes += len(values)
        previous = row
    data.append(0)
    return bytes(data), len(runs), writes


def control_frames(score, *, triangle=True, click_safe=True):
    voices, duration = timeline(score)
    ticks = math.ceil(duration*CONTROL_HZ)
    gains = json.loads((HERE/'balance.json').read_text())['balance']['role_gain']
    states = [[(0,0.,0,-1) for _ in range(4)] for _ in range(ticks)]
    errors = []
    legato_links = 0
    maximum_extension = 0.
    for role,notes in enumerate(voices):
        for note_id,(start,length,pitch,instrument,gain) in enumerate(notes):
            if not 1<=pitch<=127 or length<=0:
                raise ValueError('Invalid note')
            previous = notes[note_id-1] if note_id else None
            following = notes[note_id+1] if note_id+1<len(notes) else None
            gap_limit = .065 if role==2 else .012
            link_before = bool(click_safe and instrument and previous and previous[3]
                               and -.000001<=start-previous[0]-previous[1]<=gap_limit)
            link_after = bool(click_safe and instrument and following and following[3]
                              and -.000001<=following[0]-start-length<=gap_limit)
            # Preserve note-on positions. Short string/cello articulation gaps
            # receive a release bridge instead of a repeated hard gate/retrigger.
            sound_end = following[0] if link_after else start+length
            if link_after:
                legato_links += 1
                maximum_extension = max(maximum_extension,sound_end-start-length)
            first = round(start*CONTROL_HZ)
            stop = min(ticks,round(sound_end*CONTROL_HZ))
            score_stop = min(ticks,round((start+length)*CONTROL_HZ))
            errors.extend((first/CONTROL_HZ-start,score_stop/CONTROL_HZ-start-length))
            for tick in range(first,stop):
                age = max(0.,tick/CONTROL_HZ-start)
                tail = max(0.,start+length-tick/CONTROL_HZ)
                if instrument==0:
                    if click_safe:
                        points = ((0.,1.),(.04,.74),(.1,.55),(.2,.4),(.4,.28),(.7,.18),(1.2,.1))
                        amplitude = points[-1][1]
                        for (left,a),(right,b) in zip(points,points[1:]):
                            if age<right:
                                amplitude = a+(b-a)*(age-left)/(right-left)
                                break
                        amplitude *= min(1.,(age+.004)/.035)
                    else:
                        amplitude = next(level for when,level in
                            ((1.2,.1),(.7,.18),(.4,.28),(.2,.4),(.1,.55),(.04,.74),(0.,1.)) if age>=when)
                else:
                    amplitude = 1. if link_before else min(1.,max(.08,age/.08))
                release = 1. if link_after else min(1.,tail/(.08 if click_safe else .06))
                amplitude *= release*gain*gains[ROLE_NAMES[role]]
                states[tick][role] = (pitch,amplitude,instrument,note_id)
    frames = []
    previous_bass = -1
    triangle_fields = 0
    pitch_errors = []
    envelope_starts = 0
    last_envelope_period = 65535
    triangle_was_active = False
    phase_preserved_note_changes = 0
    for state in states:
        row = bytearray(14)
        row[7] = 0x38
        row[13] = 255
        if click_safe:
            row[6] = 31  # Noise is disabled; do not run an unused zero-period RNG.
            row[11:13] = struct.pack('<H',last_envelope_period)
        for channel,role in enumerate((0,1,2)):
            pitch,amp,instrument,note_id = state[role]
            period = max(1,min(4095,round((CPU_HZ/2)/(16*440*2**((pitch-69)/12))))) if pitch else 1
            row[channel*2:channel*2+2] = struct.pack('<H',period)
            row[8+channel] = min(range(16),key=lambda n:abs(AY_LEVELS[n]-amp*.62))
        pitch,amp,instrument,note_id = state[2]
        if triangle and pitch:
            env,cents = triangle_period(pitch)
            if abs(cents)<=TRIANGLE_MAX_CENTS:
                # An internal 110.8-kHz tone gate halves the envelope's audio
                # amplitude after low-pass filtering. CPU writes stay at 50 Hz.
                # This is AY channel C, not the ULA speaker/PWM output.
                row[4:6] = b'\x01\x00'
                row[10] = 16
                row[11:13] = struct.pack('<H',env)
                restart = not triangle_was_active if click_safe else note_id!=previous_bass
                if restart:
                    row[13] = 14  # Rising/falling repeat, initial level zero.
                    envelope_starts += 1
                elif click_safe and note_id!=previous_bass:
                    phase_preserved_note_changes += 1
                last_envelope_period = env
                triangle_fields += 1
                pitch_errors.append(cents)
                previous_bass = note_id
            else:
                previous_bass = -1
        else:
            previous_bass = -1
        triangle_was_active = bool(row[10]&16)
        frames.append(bytes(row))
    data, records, writes = pack_frames(frames)
    return data, dict(ticks=ticks,score_seconds=duration,playback_seconds=ticks/CONTROL_HZ,
        records=records,register_writes=writes,packed_bytes=len(data),source_notes=[len(v) for v in voices],
        max_note_boundary_error_seconds=max(map(abs,errors)),packed_sha256=sha(data),
        frames_sha256=sha(b''.join(frames)),triangle_fields=triangle_fields,envelope_restarts=envelope_starts,
        click_safe=click_safe,legato_links=legato_links,max_release_extension_seconds=maximum_extension,
        phase_preserved_bass_note_changes=phase_preserved_note_changes,
        max_triangle_pitch_error_cents=max(map(abs,pitch_errors),default=0),
        retained_roles=['lead','piano_accompaniment','bass'],omitted_role='inner_voice')



def build(output):
    output = Path(output).resolve()
    work = output/'assembly'
    work.mkdir(parents=True,exist_ok=True)
    songs = []
    cache = bytearray()
    for name in ('lumiere','alicia'):
        source = (HERE/'scores'/f'{name}.json').read_bytes()
        data,meta = control_frames(json.loads(source))
        offset = len(cache)
        songs.append(dict(meta,song=name,score_sha256=sha(source),offset=offset,
            start_bank_index=offset//16384,start_address=0xC000+offset%16384))
        cache.extend(data)
        (output/f'{name}.rows').write_bytes(data)
    if len(cache)>len(BANKS)*16384:
        raise ValueError('Both cached songs exceed available RAM')
    files = [TrdFile('boot','B',boot_basic(),autostart_line=10),
             TrdFile('PLAYER','C',bytes(16384),start=0x8000)]
    config = ['song_table:']
    for song in songs:
        config.extend((f'        DEFB {song["start_bank_index"]}',f'        DEFW {song["start_address"]}'))
    config.append('cache_extents:')
    sections = []
    for index,offset in enumerate(range(0,len(cache),16384)):
        payload = bytes(cache[offset:offset+16384])
        track,sector = calculate_file_start(files)
        count = (len(payload)+255)//256
        bank = BANKS[index]
        config.append(f'        DEFB {bank},{sector},{track},{count}')
        sections.append(dict(bank=bank,sector=track*16+sector,sectors=count,bytes=len(payload)))
        files.append(TrdFile(f'CACHE{index}','C',payload,start=0xC000))
    config.append('        DEFB 255')
    config += ['menu_text:','        DEFB '+','.join(str(value) for value in menu_stream())]
    config += ['mute_values:','        DEFB '+','.join(str(value) for pair in MUTE_WRITES for value in pair)]
    (work/'variants.inc').write_text('\n'.join(config)+'\n',encoding='ascii',newline='\n')
    source = (HERE/'player.asm').read_bytes().replace(b'\r\n',b'\n')
    (work/'player.asm').write_bytes(source)
    run = subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin',
        '--lstfile=player.lst','-s','.*','player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    labels = next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    blob = (work/'player.bin').read_bytes()
    assert len(blob)==16384
    files[1] = TrdFile('PLAYER','C',blob,start=0x8000)
    disk,directory,capacity = place_files(files,'AYMUSIC')
    (output/'ZX-Music-Menu.trd').write_bytes(disk)
    meta = dict(schema=3,independently_bootable=True,target='Spectrum128 + Beta Disk; AY only',
        songs=songs,cache_sections=sections,cache_bytes=len(cache),player_labels=labels,
        directory=directory,capacity=capacity,trd_sha256=sha(disk),player_sha256=sha(blob),
        assembly_sha256=sha(source),control_hz=CONTROL_HZ,cpu_hz=CPU_HZ,frame_tstates=FIELD_T,
        tools=dict(pyz80=importlib.metadata.version('pyz80'),pillow=importlib.metadata.version('Pillow')),
        producer_sha256={name:sha((HERE/name).read_bytes()) for name in ('build.py','arrangement.py','balance.json','zx_text.py')},
        beeper_audio=False,simultaneously_cached_songs=True,font='Stock Spectrum48 ROM via RST10; CHARS=3C00; stream2',
        record_format='duration U8; changed-register slot mask LE16; register_order values; zero-duration EOF',
        register_order=list(REGISTER_ORDER),mute_writes=[list(pair) for pair in MUTE_WRITES],
        memory=dict(fixed_player_bank=2,display_basic_trdos_bank=5,available_song_banks=list(BANKS),
                    max_cache_bytes=98304,stack_top=0xBD00),
        timing_scope='CPU components exclude ULA, HALT, IRQ entry and TR-DOS; see verified timing report.')
    (output/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(trd_sha256=meta['trd_sha256'],cache_bytes=len(cache),
        capacity=capacity,songs=[{k:s[k] for k in ('song','packed_bytes','records','register_writes','triangle_fields')} for s in songs]),indent=2))
    return disk,meta


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-click-fix')
    build(parser.parse_args().output)
