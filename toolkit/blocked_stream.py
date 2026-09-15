"""Independent ZX0 blocks containing complete, byte-contiguous v7 frames."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import subprocess
import zlib
from fractions import Fraction

import packed_stream
import zx0_codec

MAGIC = b'ZXFC'
VERSION = 8
RING_CAPACITY_SECTORS = 5*64
OUTPUT_BUFFER = 0x8000


@dataclass(frozen=True)
class Block:
    data: bytes
    decoded: bytes
    frames: int
    stored: bool
    deflate_bytes: int

    def serialize(self):
        return struct.pack('<HH', len(self.data) | (0x8000 if self.stored else 0), len(self.decoded)) + self.data


def compress_frames(frames: list[bytes], executable: Path, cache: Path) -> list[Block]:
    """Compressor work is offline. Cache entries are verified before reuse."""
    cache.mkdir(parents=True, exist_ok=True)
    groups = []
    pending = bytearray()
    count = 0
    for frame in frames:
        if len(frame) > 8192: raise ValueError('frame exceeds block buffer')
        if pending and len(pending)+len(frame) > 8192:
            groups.append((bytes(pending),count)); pending.clear(); count=0
        pending += frame; count += 1
    if pending: groups.append((bytes(pending),count))
    result=[]
    for index,(decoded,count) in enumerate(groups):
        digest=hashlib.sha256(decoded).hexdigest()
        raw=cache/f'{digest}.raw'; encoded=cache/f'{digest}.zx0'
        if not encoded.exists():
            raw.write_bytes(decoded)
            subprocess.run([str(executable.resolve()),'-f',str(raw.resolve()),str(encoded.resolve())],
                           check=True,capture_output=True)
        payload=encoded.read_bytes()
        if zx0_codec.decompress(payload) != decoded: raise ValueError('ZX0 verification failed')
        stored=len(payload)>=len(decoded)
        compressor=zlib.compressobj(9,zlib.DEFLATED,-15)
        deflated=compressor.compress(decoded)+compressor.flush()
        assert zlib.decompress(deflated,-15)==decoded
        result.append(Block(decoded if stored else payload,decoded,count,stored,len(deflated)))
        if index%20==0: print(f'compressed block {index+1}/{len(groups)}',flush=True)
    return result


def frame_demands(blocks: list[Block]) -> list[int]:
    return [length for block in blocks for length in (len(block.serialize()), *([0]*(block.frames-1)))]


def serialize_volume(blocks: list[Block], frame_rate: float, *, clocked: bool = False) -> bytes:
    data=b''.join(block.serialize() for block in blocks)
    header=bytearray(256)
    header[:4]=MAGIC; header[4]=VERSION
    struct.pack_into('<H',header,8,sum(block.frames for block in blocks))
    rate=Fraction(frame_rate).limit_denominator(1000)
    struct.pack_into('<HH',header,12,rate.numerator,rate.denominator)
    struct.pack_into('<H',header,16,(len(data)+255)//256)
    backlog = (min(RING_CAPACITY_SECTORS,(len(data)+255)//256) if clocked else
               packed_stream.minimum_startup_backlog(frame_demands(blocks),RING_CAPACITY_SECTORS))
    struct.pack_into('<H',header,18,backlog)
    struct.pack_into('<H',header,20,RING_CAPACITY_SECTORS)
    struct.pack_into('<I',header,22,len(data))
    return bytes(header)+data+bytes(-len(data)%256)


def emit_clock(a):
    """IM2 counts fields during CPU work; ROM/disk waits remain separate."""
    a.label('setup_clock')
    a.emit(0x21); a.word(0x7E00)
    a.emit(0x11); a.word(0x7E01)
    a.emit(0x01); a.word(256)
    a.emit(0x36,0x7F,0xED,0xB0)
    a.abs16(0x21,'clock_isr_template')
    a.emit(0x11); a.word(0x7F7F)
    a.emit(0x01); a.word(12)
    a.emit(0xED,0xB0,0x3E,0x7E,0xED,0x47,0xED,0x5E,0xC9)
    a.label('clock_isr_template')
    a.emit(0xF5); a.abs16(0x3A,'field_counter'); a.emit(0x3C)
    a.abs16(0x32,'field_counter'); a.emit(0xF1,0xFB)
    a.emit(0xED,0x4D)
    assert a.pc-a.labels['clock_isr_template'] == 12


def emit_hold_budget(a):
    a.abs16(0x3A,'field_counter')
    a.emit(0xFE,6); a.rel8(0x38,'hold_subtract_cpu')
    a.emit(0x3E,1); a.rel8(0x18,'hold_budget_ready')
    a.label('hold_subtract_cpu')
    a.emit(0x47,0x3E,6,0x90)
    a.label('hold_budget_ready')
    a.abs16(0x32,'hold_counter')


def emit_transport(a, *, input_limit=8192):
    packed_stream.emit_transport(a,blocked=True,input_limit=input_limit)
    a.label('wait_packet')
    a.abs16(0x2A,'block_frame_pointer')
    a.abs16((0xED,0x5B),'block_end')
    a.emit(0xB7,0xED,0x52,0xC0)  # RET NZ: another complete frame remains.
    a.abs16(0xCD,'load_block_header')
    a.abs16(0x2A,'block_length')
    a.emit(0x11); a.word(8193)
    a.emit(0xB7,0xED,0x52); a.abs16(0xD2,'fatal')
    a.abs16(0x2A,'block_length'); a.emit(0x7C,0xB7)
    a.rel8(0x20,'block_length_valid')
    a.emit(0x7D,0xFE,12); a.abs16(0xDA,'fatal')
    a.label('block_length_valid')
    a.abs16(0xCD,'load_block_body')
    a.abs16(0x2A,'block_length')
    # Output is 1..8192 bytes. The builder only emits whole nonempty frames.
    a.emit(0x11); a.word(OUTPUT_BUFFER)
    a.emit(0x19); a.abs16(0x22,'block_end')
    a.emit(0x21); a.word(packed_stream.FRAME_BUFFER)
    a.emit(0x11); a.word(OUTPUT_BUFFER)
    a.abs16(0x3A,'block_stored'); a.emit(0xB7)
    a.rel8(0x28,'block_unpack')
    a.abs16((0xED,0x4B),'block_length'); a.emit(0xED,0xB0)
    a.rel8(0x18,'block_unpacked')
    a.label('block_unpack')
    a.abs16(0xCD,'dzx0_turbo')
    a.label('block_unpacked')
    a.abs16(0x2A,'block_end'); a.emit(0xB7,0xED,0x52)
    a.abs16(0xC2,'fatal')
    a.emit(0x21); a.word(OUTPUT_BUFFER)
    a.abs16(0x22,'block_frame_pointer'); a.emit(0xC9)

    a.label('ring_packet')
    a.abs16(0x2A,'block_frame_pointer')
    a.emit(0x5E,0x23,0x56,0x23,0xE5,0x19)
    a.abs16(0x22,'block_frame_pointer')
    # Every frame must end inside this independently decoded block.
    a.abs16((0xED,0x5B),'block_end'); a.emit(0xB7,0xED,0x52)
    a.rel8(0x28,'block_frame_valid')
    a.abs16(0xD2,'fatal')
    a.label('block_frame_valid')
    a.emit(0xE1)
    a.abs16(0x11,'ay_state'); a.emit(0x01); a.word(9)
    a.emit(0xED,0xB0,0xE5,0xDD,0xE1)
    a.abs16(0xCD,'command_loop'); a.emit(0xC9)
    zx0_codec.emit_decoder(a,'turbo')


def emit_variables(a):
    for name,size in (('block_length',2),('block_stored',1),('block_frame_pointer',2),('block_end',2)):
        a.label(name); a.emit(*([0]*size))
    a.labels['block_length_high']=a.labels['block_length']+1
