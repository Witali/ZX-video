"""64-step, two-pixel-high progress for the CURRENT DISK, not the movie.

Entry tick is called once after publishing a video frame, with bank 7 paged.
Only a countdown runs on idle frames. A step writes one nibble-sized change
to both native screens. White-on-black attributes are set once. reset clears
only the progress rows/attributes and restores this volume's counters.
The volume builder must supply its own frame count and reload/reset this
module when changing disks. No AY tick or disk byte count is used.
"""
from build_zxv_trd import MiniAssembler

CODE = 0xdce0
PIXEL_ROWS = (0x50e0,0x51e0)
ATTRIBUTE_ROW = 0x5ae0
MAX_FRAMES = 64*255


def build(frames_on_disk):
    if not isinstance(frames_on_disk,int) or not 1 <= frames_on_disk <= MAX_FRAMES:
        raise ValueError('progress requires 1..16320 frames on this disk')
    deadlines = [(step*frames_on_disk+63)//64 for step in range(1,65)]
    intervals = [deadlines[0]]+[b-a for a,b in zip(deadlines,deadlines[1:])]
    a,listing = MiniAssembler(CODE),[]
    def emit(name,data,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase='progress')); a.emit(*data)
    def addr(name,opcode,value,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase='progress'))
        if isinstance(value,str): a.abs16(opcode,value)
        else: a.emit(opcode); a.word(value)
    a.label('tick')
    addr('LD A,(countdown)',0x3a,'countdown',13)
    emit('OR A',[0xb7],4); emit('RET Z (finished)',[0xc8],[5,11])
    emit('DEC A',[0x3d],4); addr('LD (countdown),A',0x32,'countdown',13)
    emit('RET NZ (no progress change)',[0xc0],[5,11])
    a.label('advance')
    addr('LD HL,(pixel_pointer)',0x2a,'pixel_pointer',16)
    addr('LD A,(bits)',0x3a,'bits',13)
    emit('LD (HL),A',[0x77],7); emit('INC H',[0x24],4); emit('LD (HL),A',[0x77],7)
    emit('SET 7,H',[0xcb,0xfc],8); emit('LD (HL),A',[0x77],7)
    emit('DEC H',[0x25],4); emit('LD (HL),A',[0x77],7)
    emit('RES 7,H',[0xcb,0xbc],8)
    emit('CP F0h',[0xfe,0xf0],7); addr('JP Z,half',0xca,'half',10)
    emit('INC L',[0x2c],4); emit('LD A,F0h',[0x3e,0xf0],7)
    addr('JP store',0xc3,'store',10)
    a.label('half'); emit('OR 0Fh',[0xf6,0x0f],7)
    a.label('store')
    addr('LD (bits),A',0x32,'bits',13); addr('LD (pixel_pointer),HL',0x22,'pixel_pointer',16)
    addr('LD A,(remaining)',0x3a,'remaining',13); emit('DEC A',[0x3d],4)
    addr('LD (remaining),A',0x32,'remaining',13); addr('JP Z,done',0xca,'done',10)
    addr('LD HL,(interval_pointer)',0x2a,'interval_pointer',16)
    emit('LD A,(HL)',[0x7e],7); emit('INC HL',[0x23],6)
    addr('LD (interval_pointer),HL',0x22,'interval_pointer',16)
    addr('LD (countdown),A',0x32,'countdown',13)
    emit('OR A',[0xb7],4); addr('JP Z,advance',0xca,'advance',10); emit('RET',[0xc9],10)
    a.label('done'); emit('XOR A',[0xaf],4); addr('LD (countdown),A',0x32,'countdown',13)
    emit('RET',[0xc9],10)
    a.label('reset')
    for base in (*PIXEL_ROWS,ATTRIBUTE_ROW,*(n+0x8000 for n in PIXEL_ROWS),ATTRIBUTE_ROW+0x8000):
        addr('LD HL,bar range',0x21,base,10); addr('LD DE,bar range+1',0x11,base+1,10)
        addr('LD BC,31',0x01,31,10)
        emit('LD (HL),initial',[0x36,0x47 if (base & 0x1f00) == 0x1a00 else 0],10)
        emit('LDIR',[0xed,0xb0],[16,21])
    addr('LD HL,initial_state',0x21,'initial_state',10)
    addr('LD DE,state',0x11,'state',10); addr('LD BC,7',0x01,7,10)
    emit('LDIR',[0xed,0xb0],[16,21]); emit('RET',[0xc9],10)
    a.label('state')
    a.label('countdown'); a.emit(0)
    a.label('remaining'); a.emit(0)
    a.label('pixel_pointer'); a.word(0)
    a.label('bits'); a.emit(0)
    a.label('interval_pointer'); a.word(0)
    a.label('state_end')
    a.label('initial_state'); a.emit(intervals[0],64); a.word(PIXEL_ROWS[0]); a.emit(0xf0)
    a.abs16((), 'intervals_next')
    a.label('intervals'); a.emit(intervals[0]); a.label('intervals_next'); a.emit(*intervals[1:])
    a.label('end')
    if a.pc > 0xde00: raise ValueError('disk progress overlaps frame clock')
    return a.resolve(),dict(a.labels),listing,deadlines


def reference_screen(screen, displayed_frames, frames_on_disk):
    """Display-only reference for the current volume, including both rows."""
    steps = min(64,displayed_frames*64//frames_on_disk)
    result = bytearray(screen)
    for column in range(32):
        filled = min(2,max(0,steps-2*column))
        for row in PIXEL_ROWS: result[row-0x4000+column] = (0,0xf0,0xff)[filled]
        result[ATTRIBUTE_ROW-0x4000+column] = 0x47
    return bytes(result)


def expected_tick_tstates(previous_steps, next_steps):
    """Instruction-table sum, excluding caller's 27-T paging-bridge addition."""
    if previous_steps == 64: return 28
    if previous_steps == next_steps: return 50
    ticks = 44  # Countdown reaches zero; neither conditional RET is taken.
    for step in range(previous_steps+1,next_steps+1):
        ticks += 174 if step % 2 else 188  # Update screens, pointer and remaining.
        if step == 64: ticks += 27  # Finish and return; no next interval read.
        else:
            ticks += 72  # Load next interval and branch if zero.
            if step == next_steps: ticks += 10  # RET when countdown is nonzero.
    return ticks
