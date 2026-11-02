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
from player import TrdFile, basic_line, calculate_file_start, place_files, spectrum_bitmap_offset
from demo_assets import assets, footer, DISK_NAME
from zx0.small import build as zx0_small

BANKS = (0, 4, 6, 1, 3, 7)
CPU_HZ = 3546900
FIELD_T = 70908
CONTROL_HZ = CPU_HZ/FIELD_T
ROLE_NAMES = ('lead', 'piano_accompaniment', 'bass', 'inner_voice')
AY_LEVELS = (0., .009994659, .014450294, .02105745, .03070115, .04554818,
             .06449989, .1073625, .1265888, .2049897, .2922103, .3728389,
             .4925307, .6353246, .8055848, 1.)
TRIANGLE_MAX_CENTS = 18
REPEAT_GAP_FIELDS = 2
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


def percussion_beats(score):
    """Absolute quarter-note positions, respecting each bar's tempo and meter."""
    cursor = 0.
    for name in score['playlist']:
        pattern = score['patterns'][name]
        if isinstance(pattern, dict):
            tempo = pattern['tempo_bpm']
            bars = [bar.get('beats', pattern['beats_per_bar']) for bar in pattern['bars']]
        else:
            tempo = score['tempo_bpm']
            bars = [score['beats_per_bar']]*len(pattern)
        for beats in bars:
            for beat in range(math.ceil(beats)):
                yield cursor+beat*60/tempo,beat
            cursor += beats*60/tempo


def add_percussion(frames, states, score):
    """Use only literal piano rests: never replace a pitched note or share ENV.

    All three AY voices are occupied. A short noise pulse on B occupies the
    closest silent field at a quarter-note position, or the preceding field.
    No melody onset moves. The one-field pulse is intentional percussion,
    not an attempt to use AY's shared envelope for a fourth musical voice.
    """
    hits = []
    for seconds,beat in percussion_beats(score):
        nominal = round(seconds*CONTROL_HZ)
        tick = next((t for t in (nominal,nominal-1)
                     if 0<=t<len(frames) and not states[t][1][0]
                     and any(states[n][1][0] for n in (t-1,t+1) if 0<=n<len(states))),None)
        if tick is None:
            continue
        row = bytearray(frames[tick])
        assert row[9]==0
        snare = bool(beat%2)
        row[6] = 12 if snare else 4
        row[7] = (row[7]|2)&~16  # B: tone off, noise on; A/C mixer bits unchanged.
        row[9] = 7 if snare else 5
        frames[tick] = bytes(row)
        hits.append(dict(tick=tick,beat_seconds=seconds,beat_in_bar=beat,
                         kind='brush' if snare else 'hat',advance_seconds=seconds-tick/CONTROL_HZ))
    return hits


def control_frames(score, *, triangle=True, click_safe=True, articulation=True, percussion=True):
    voices, duration = timeline(score)
    ticks = math.ceil(duration*CONTROL_HZ)
    gains = json.loads((HERE/'balance.json').read_text())['balance']['role_gain']
    states = [[(0,0.,0,-1) for _ in range(4)] for _ in range(ticks)]
    errors = []
    legato_links = 0
    maximum_extension = 0.
    articulation = bool(articulation and click_safe)
    percussion = bool(percussion and click_safe)
    repeats = []
    for role,notes in enumerate(voices):
        for note_id,(start,length,pitch,instrument,gain) in enumerate(notes):
            if not 1<=pitch<=127 or length<=0:
                raise ValueError('Invalid note')
            previous = notes[note_id-1] if note_id else None
            following = notes[note_id+1] if note_id+1<len(notes) else None
            first = round(start*CONTROL_HZ)
            score_stop = min(ticks,round((start+length)*CONTROL_HZ))
            # Explicit ties have already become one note in timeline(). Only
            # separate lead events at the same pitch need a new articulation.
            repeat_before = bool(articulation and role==0 and previous and previous[2]==pitch
                and 0<=first-round((previous[0]+previous[1])*CONTROL_HZ)<REPEAT_GAP_FIELDS)
            repeat_after = bool(articulation and role==0 and following and following[2]==pitch
                and 0<=round(following[0]*CONTROL_HZ)-score_stop<REPEAT_GAP_FIELDS)
            gap_limit = .065 if role==2 else .012
            link_before = bool(click_safe and instrument and previous and previous[3]
                               and not repeat_before
                               and -.000001<=start-previous[0]-previous[1]<=gap_limit)
            link_after = bool(click_safe and instrument and following and following[3]
                              and not repeat_after
                              and -.000001<=following[0]-start-length<=gap_limit)
            # Preserve note-on positions. Short string/cello articulation gaps
            # receive a release bridge instead of a repeated hard gate/retrigger.
            sound_end = following[0] if link_after else start+length
            if link_after:
                legato_links += 1
                maximum_extension = max(maximum_extension,sound_end-start-length)
            stop = min(ticks,round(sound_end*CONTROL_HZ))
            release_end = start+length
            if repeat_after:
                next_first = round(following[0]*CONTROL_HZ)
                gap = min(REPEAT_GAP_FIELDS,max(0,next_first-first-1))
                stop = min(stop,next_first-gap)
                release_end = stop/CONTROL_HZ
                repeats.append(dict(role=ROLE_NAMES[role],pitch=pitch,next_tick=next_first,
                                    mute_from_tick=stop,gap_fields=next_first-stop))
            errors.extend((first/CONTROL_HZ-start,score_stop/CONTROL_HZ-start-length))
            for tick in range(first,stop):
                age = max(0.,tick/CONTROL_HZ-start)
                tail = max(0.,release_end-tick/CONTROL_HZ)
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
    noise_hits = add_percussion(frames,states,score) if percussion else []
    data, records, writes = pack_frames(frames)
    return data, dict(ticks=ticks,score_seconds=duration,playback_seconds=ticks/CONTROL_HZ,
        records=records,register_writes=writes,packed_bytes=len(data),source_notes=[len(v) for v in voices],
        max_note_boundary_error_seconds=max(map(abs,errors)),packed_sha256=sha(data),
        note_boundary_error_scope='Rounded score grid; repeated-note release gates intentionally end earlier',
        frames_sha256=sha(b''.join(frames)),triangle_fields=triangle_fields,envelope_restarts=envelope_starts,
        click_safe=click_safe,legato_links=legato_links,max_release_extension_seconds=maximum_extension,
        phase_preserved_bass_note_changes=phase_preserved_note_changes,
        repeated_note_articulation=repeats,repeat_gap_fields=REPEAT_GAP_FIELDS,
        percussion_hits=noise_hits,noise_fields=len(noise_hits),
        percussion_channel='B; piano rests only' if percussion else None,
        max_percussion_advance_seconds=max((h['advance_seconds'] for h in noise_hits),default=0),
        max_triangle_pitch_error_cents=max(map(abs,pitch_errors),default=0),
        retained_roles=['lead','piano_accompaniment','bass'],omitted_role='inner_voice')



def soft_edges(data):
    """Gentle fixed-volume edges without changing AY's shared bass oscillator.

    Every original active field remains active (minimum nonzero level one).
    Periods, mixer, noise, R13 restarts and all hardware-ENV values are exact.
    In particular, ENV is the bass waveform and cannot be gain-scaled by R10.
    Retain the full source timeline, including its original trailing silence.
    """
    from verify import unpack
    original = unpack(data)
    last = max(i for i,row in enumerate(original) if any(row[8:11]))
    result, changed, envelope_preserved = [], 0, 0
    for tick,source in enumerate(original):
        row = bytearray(source)
        gain = min(1., .08+.92*tick/8, .08+.92*max(0,last-tick)/40)
        for reg in (8,9,10):
            value = row[reg]
            if value&16:
                envelope_preserved += 1
            elif value and gain<1:
                row[reg] = min(range(1,value+1),key=lambda n:abs(AY_LEVELS[n]-AY_LEVELS[value]*gain))
                changed += row[reg]!=value
        assert bool(any(row[8:11]))==bool(any(source[8:11]))
        assert row[:8]==source[:8] and row[11:]==source[11:]
        result.append(bytes(row))
    packed,records,writes=pack_frames(result)
    return packed,dict(attack_fields=8,release_fields=40,changed_fixed_volume_fields=changed,
        hardware_envelope_fields_preserved=envelope_preserved,all_active_fields_preserved=True,
        all_oscillator_and_restart_values_preserved=True,source_packed_bytes=len(data),
        packed_bytes=len(packed),packed_records=records,ay_register_writes=writes,
        frames_sha256=sha(b''.join(result)))


def build(output):
    output = Path(output).resolve()
    work = output/'assembly'
    work.mkdir(parents=True,exist_ok=True)
    songs, raw = [], []
    for name in ('lumiere','alicia'):
        source = (HERE/'scores'/f'{name}.json').read_bytes()
        data,meta = control_frames(json.loads(source))
        (output/f'{name}.original.rows').write_bytes(data)
        data,fades=soft_edges(data)
        meta.update(source_frames_sha256=meta['frames_sha256'],source_packed_sha256=meta['packed_sha256'],
                    source_records=meta['records'],source_register_writes=meta['register_writes'],
                    frames_sha256=fades['frames_sha256'],packed_sha256=sha(data),packed_bytes=len(data),
                    records=fades['packed_records'],register_writes=fades['ay_register_writes'],soft_edges=fades)
        raw.append(data)
        songs.append(dict(meta,song=name,score_sha256=sha(source)))
        (output/f'{name}.rows').write_bytes(data)
    packed_songs,dictionary,depth,pictures,banks = assets(raw)
    from verify import unpack
    pauses = []
    for song,packed,data in zip(songs,packed_songs,raw):
        song.update(packed)
        frames = unpack(data)
        last = max(i for i,row in enumerate(frames) if any(row[8:11]))
        trailing = len(frames)-last-1
        pauses.append(max(0,150-trailing))
        song.update(trailing_silent_fields=trailing,additional_pause_fields=pauses[-1])
    # The sector-API first stage preserves the splash while loading PLAYER.
    # A second BASIC LOAD would clear SCREEN$ inside the TR-DOS interpreter.
    boot = b''.join((basic_line(10,b'\xfd \xb0 "24575"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "LOADER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "24576"')))
    files = [TrdFile('boot','B',boot,autostart_line=10),
             TrdFile('LOADER','C',bytes(7168),start=0x6000),
             TrdFile('PLAYER','C',bytes(16384),start=0x8000)]
    track,sector=calculate_file_start(files[:2])
    (work/'loader-position.inc').write_text(f'        LD DE,{track*256+sector}\n',encoding='ascii')
    (work/'loader.asm').write_bytes((HERE/'loader.asm').read_bytes())
    loader_run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=loader.bin','loader.asm'],
                              cwd=work,capture_output=True,text=True)
    if loader_run.returncode:
        raise RuntimeError(loader_run.stdout+loader_run.stderr)
    loader_blob=(work/'loader.bin').read_bytes()
    assert len(loader_blob)==256
    files[1]=TrdFile('LOADER','C',loader_blob+(HERE/'artwork/city.scr').read_bytes(),start=0x6000)
    config = [f'PICTURE_COUNT: EQU {len(pictures)}','song_table:']
    for song in songs:
        config += [f'        DEFB {song["start_bank_index"]}',f'        DEFW {song["start_address"]}']
    config += ['song_pauses:','        DEFB '+','.join(map(str,pauses)),'cache_extents:']
    sections = []
    for bank,payload in zip(BANKS,banks):
        track,sector = calculate_file_start(files)
        count = (len(payload)+255)//256
        config.append(f'        DEFB {bank},{sector},{track},{count}')
        sections.append(dict(bank=bank,sector=track*16+sector,sectors=count,bytes=len(payload)))
        files.append(TrdFile(f'CACHE{bank}','C',bytes(payload),start=0xC000))
    config += ['        DEFB 255','menu_text:',
        '        DEFB '+','.join(str(value) for value in menu_stream()),'mute_values:',
        '        DEFB '+','.join(str(value) for pair in MUTE_WRITES for value in pair),
        'grammar_dictionary:','        DEFB '+','.join(map(str,dictionary)),'picture_table:']
    for picture in pictures:
        config += [f'        DEFB {picture["bank"]}',f'        DEFW {picture["address"]}',
                   f'        DEFB {picture["border"]},{picture["accent"]}']
    config += ['column_table:','        DEFW '+','.join(str(0xA000+x*180) for x in range(32))]
    (work/'variants.inc').write_text('\n'.join(config)+'\n',encoding='ascii',newline='\n')
    regions,decoder_labels,decoder = zx0_small('smc',core=0x8D00,core_limit=0x8E00)
    (work/'zx0.inc').write_text('        DEFB '+','.join(map(str,regions[0][1]))+'\n',encoding='ascii')
    (work/'footer.inc').write_text('        DEFB '+','.join(map(str,footer()))+'\n',encoding='ascii')
    for name in ('player.asm','demo-core.asm','demo-graphics.asm'):
        (work/name).write_bytes((HERE/name).read_bytes().replace(b'\r\n',b'\n'))
    run = subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin',
        '--lstfile=player.lst','-s','.*','player.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    labels = next(ast.literal_eval(line) for line in run.stdout.splitlines() if line.startswith('{'))
    blob = (work/'player.bin').read_bytes()
    assert len(blob)==16384
    files[2] = TrdFile('PLAYER','C',blob,start=0x8000)
    disk,directory,capacity = place_files(files,'EXP33DEMO')
    (output/DISK_NAME).write_bytes(disk)
    meta = dict(schema=4,disk_name=DISK_NAME,title='Expedition 33 Demo',independently_bootable=True,
        target='Spectrum128 + Beta Disk; AY only',songs=songs,cache_sections=sections,
        cache_bytes=sum(map(len,banks)),player_labels=labels,directory=directory,capacity=capacity,
        trd_sha256=sha(disk),player_sha256=sha(blob),control_hz=CONTROL_HZ,cpu_hz=CPU_HZ,frame_tstates=FIELD_T,
        tools=dict(pyz80=importlib.metadata.version('pyz80')),
        producer_sha256={name:sha((HERE/name).read_bytes()) for name in
            ('build.py','arrangement.py','balance.json','zx_text.py','music_codec.py','demo_assets.py',
             'player.asm','demo-core.asm','demo-graphics.asm','loader.asm')},
        beeper_audio=False,simultaneously_cached_songs=True,autoplay_song='lumiere',
        autoplay_on_first_ula_field=True,menu_hidden_until_keypress=True,slideshow_default=True,
        pictures=pictures,graphics_decoder=decoder,music_codec=dict(format='bounded-byte-pair-grammar-v1',
            raw_bytes=sum(map(len,raw)),compressed_bytes=sum(s['compressed_bytes'] for s in songs),
            dictionary_bytes=len(dictionary),max_depth=depth,dictionary_sha256=sha(dictionary),
            byte_exact_roundtrip=True),playlist=dict(loop=True,nominal_silence_fields=150,
            source_silence_retained=True,additional_pause_fields=pauses),
        font='Stock Spectrum48 ROM menu; shared Cinzel image footer',
        register_order=list(REGISTER_ORDER),mute_writes=[list(pair) for pair in MUTE_WRITES],
        memory=dict(fixed_player_bank=2,display_basic_trdos_bank=5,menu_bank=7,menu_bytes=6912,
            available_cache_banks=[0,4,6,1,3],max_cache_bytes=81920,incoming_picture=[0xA000,0xB680],
            grammar_stack=[0xB700,0xB718],stack_top=0xBD00),
        timing_scope='Plain CPU excludes ULA contention, HALT, IRQ entry and TR-DOS; full Fuse proof is separate.')
    (output/'build.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(trd_sha256=meta['trd_sha256'],cache_bytes=meta['cache_bytes'],pictures=len(pictures))))
    return meta


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/expedition-33-demo')
    build(parser.parse_args().output)
