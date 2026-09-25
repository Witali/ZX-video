"""Compress a debugger fixture's byte patches to fit the Windows command line.

Temporary bank-7 E400..FFFF is used only before the experimental driver.
This installer is outside playback and is never added to release images.
"""
import struct
import subprocess
from build_zxv_trd import MiniAssembler
from benchmark_compact_screen import NativeCPU
from test_fap3_disk import install
import zx0_codec

ENTRY,PACKED,OUTPUT=0xe400,0xe600,0xf000


def build(patches,entry,zx0,directory,*,copies=()):
    runs=[]
    for address,value in sorted(patches):
        if runs and address==runs[-1][0]+len(runs[-1][1]):runs[-1][1].append(value)
        else:runs.append((address,bytearray([value])))
    data=b''.join(struct.pack('<HH',len(blob),base)+blob for base,blob in runs)+bytes(2)
    if len(data)>4096:raise ValueError('fixture patch table too large')
    directory.mkdir(parents=True,exist_ok=True)
    source=directory/'fixture-patches.bin';packed=directory/'fixture-patches.zx0'
    source.write_bytes(data)
    subprocess.run([str(zx0.resolve()),'-f',str(source.resolve()),str(packed.resolve())],check=True,capture_output=True)
    payload=packed.read_bytes()
    if PACKED+len(payload)>OUTPUT or zx0_codec.decompress(payload,limit=len(data))!=data:
        raise ValueError('fixture patch compression failed')
    a=MiniAssembler(ENTRY)
    a.emit(0xf3,0x31);a.word(0x9df0)
    a.emit(0x21);a.word(PACKED);a.emit(0x11);a.word(OUTPUT);a.abs16(0xcd,'dzx0_turbo')
    a.emit(0x21);a.word(OUTPUT)
    a.label('next');a.emit(0x4e,0x23,0x46,0x23,0x78,0xb1);a.abs16(0xca,'finished')
    a.emit(0x5e,0x23,0x56,0x23,0xed,0xb0);a.abs16(0xc3,'next')
    a.label('finished')
    for source,destination,count in copies:
        if not (0x6400<=source<source+count<=0x7800 and 0xa400<=destination<destination+count<=0xb700):
            raise ValueError('unexpected checkpoint copy range')
        a.emit(0x21);a.word(source);a.emit(0x11);a.word(destination)
        a.emit(0x01);a.word(count);a.emit(0xed,0xb0)
    a.emit(0xc3);a.word(entry)
    zx0_codec.emit_decoder(a,'turbo')
    code=a.resolve()
    if ENTRY+len(code)>PACKED:raise ValueError('patch loader overlaps packed data')
    for address,_ in patches:
        if address>=ENTRY:raise ValueError('patch target overlaps installer scratch')
    # Execute installer in the same Z80 CPU, checking every requested byte.
    c=NativeCPU(b'',b'');c.port_7ffd=0x17
    for bank in c.banks:bank[:]=bytes((i*37+i//256)%256 for i in range(16384))
    copy_expected=[bytes(c.read8(src+i) for i in range(n)) for src,_,n in copies]
    install(c,ENTRY,code);install(c,PACKED,payload);c.pc=ENTRY
    while c.pc!=entry:
        c.step()
        if c.steps>100000:raise AssertionError('patch installer did not terminate')
    if any(c.read8(a)!=v for a,v in patches):raise AssertionError('installed patch differs')
    if any(bytes(c.read8(dst+i) for i in range(n))!=blob for (_,dst,n),blob in zip(copies,copy_expected)):
        raise AssertionError('installed checkpoint copy differs')
    return [(ENTRY+i,v) for i,v in enumerate(code)]+[(PACKED+i,v) for i,v in enumerate(payload)],ENTRY,dict(
        installed_bytes=len(patches),compressed_bytes=len(payload),table_bytes=len(data),loader_bytes=len(code),
        cpu_verified=True,playback_code=False,checkpoint_copies=copies,
        checkpoint_copy_tstates=sum(25+21*n for _,_,n in copies))
