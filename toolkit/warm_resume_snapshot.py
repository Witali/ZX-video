"""Transfer actual EOF RAM to the disk prompt for a resumed Fuse measurement.

The SZX layout follows libspectrum/szx.c (explicit Spectrum 128 model 2).
https://github.com/speccytools/libspectrum/blob/master/szx.c
All retained bytes in banks
5, 2, 6 come from a completed predecessor run, never from build checkpoints.
Other banks are deliberately poisoned: continuation must reload them before
use. CPU enters WAIT_NEXT, whose prologue resets SP/IY/IM; AY is restored by
the next volume. This tests sequential RAM reuse across emulator runs; it
does not measure physical disk swapping or preserve the controller state.
"""
import hashlib
import struct


def make_snapshot(ram, *, pc=0x6200):
    if len(ram)!=49152: raise ValueError('expected actual banks 5/2/6, 48 KiB')
    def chunk(tag,data): return tag+struct.pack('<I',len(data))+data
    regs=bytearray(37)
    struct.pack_into('<HHH',regs,18,0x5c3a,0x5ff0,pc)  # IY, SP, PC
    regs[24]=0xbd; regs[28]=1; regs[33]=48  # I, IM, interrupt window
    result=b'ZXST'+bytes([1,5,2,0])+chunk(b'Z80R',regs)
    result+=chunk(b'SPCR',struct.pack('<BBBBI',0,0x16,0,0,0))
    result+=chunk(b'B128',struct.pack('<IBBBBBB',1,4,0x1c,0,1,0,0))
    retained={5:ram[:16384],2:ram[16384:32768],6:ram[32768:]}
    for bank in range(8):
        result+=chunk(b'RAMP',struct.pack('<HB',0,bank)+retained.get(bank,b'\xa5'*16384))
    return result


def verify_retained(ram, metadata, states):
    from warm_startup import immutable_fixed
    if len(ram)!=49152: raise ValueError('incomplete RAM')
    fixed=ram[:32768]; tables=ram[32768:]
    invariant=hashlib.sha256(tables+immutable_fixed(fixed,metadata['warm_reset_ranges'])).hexdigest()
    if invariant!=metadata['warm_immutable_sha256']:
        raise AssertionError('runtime changed a retained immutable byte')
    expected=states[metadata['frame_end_exclusive']-1].tobytes()
    if fixed[0x2400:0x3300]!=expected:
        raise AssertionError('actual EOF compact predictor differs')
    return dict(immutable_ram_exact=True,compact_predictor_exact=True,
        immutable_sha256=invariant,compact_sha256=hashlib.sha256(expected).hexdigest(),
        ram_sha256=hashlib.sha256(ram).hexdigest())
