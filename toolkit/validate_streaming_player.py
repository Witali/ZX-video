#!/usr/bin/env python3
"""Instruction-level validator for the generated streaming ZXV player.

This is a deliberately small Z80 interpreter supporting only the instructions
emitted by build_streaming_trd.py. It models the Spectrum 128 bank map and mocks
the stable TR-DOS call at 3D13h/function 05 by copying sectors from the TRD image.
"""
from __future__ import annotations
import argparse
import struct
from pathlib import Path

LOAD=0x6000
SECTOR=256
SPT=16
ROM48_BANK7=0x17

class CPU:
    def __init__(self, player: bytes, trd: bytes):
        self.banks=[bytearray(0x4000) for _ in range(8)]
        self.rom=bytearray(0x4000)
        self.trd=trd
        self.banks[5][LOAD-0x4000:LOAD-0x4000+len(player)]=player
        self.a=self.b=self.c=self.d=self.e=self.h=self.l=0
        self.sp=0x5FF0; self.pc=LOAD
        self.z=False; self.carry=False
        self.port_7ffd=0
        self.halts=0; self.steps=0; self.dos_reads=0; self.bytes_read=0
        self.screen_page_toggles=0
        self.min_sp=self.sp

    def map(self, addr:int):
        addr &= 0xffff
        if addr < 0x4000: return self.rom, addr
        if addr < 0x8000: return self.banks[5], addr-0x4000
        if addr < 0xC000: return self.banks[2], addr-0x8000
        return self.banks[self.port_7ffd & 7], addr-0xC000
    def read8(self,addr):
        m,o=self.map(addr); return m[o]
    def write8(self,addr,v):
        m,o=self.map(addr); m[o]=v&255
    def fetch8(self):
        v=self.read8(self.pc); self.pc=(self.pc+1)&0xffff; return v
    def fetch16(self):
        lo=self.fetch8(); return lo | self.fetch8()<<8
    def hl(self): return self.l | self.h<<8
    def de(self): return self.e | self.d<<8
    def bc(self): return self.c | self.b<<8
    def set_hl(self,v): self.h=(v>>8)&255; self.l=v&255
    def set_de(self,v): self.d=(v>>8)&255; self.e=v&255
    def set_bc(self,v): self.b=(v>>8)&255; self.c=v&255
    def push(self,v):
        self.sp=(self.sp-2)&0xffff; self.min_sp=min(self.min_sp,self.sp)
        self.write8(self.sp,v&255); self.write8(self.sp+1,(v>>8)&255)
    def pop(self):
        v=self.read8(self.sp)|self.read8(self.sp+1)<<8; self.sp=(self.sp+2)&0xffff; return v
    def rel(self):
        v=self.fetch8(); return v-256 if v&128 else v
    def cp(self,v):
        r=(self.a-v)&0x1ff; self.z=(r&255)==0; self.carry=self.a < v
    def mock_trdos(self):
        if self.c != 5: raise RuntimeError(f"unsupported TR-DOS function {self.c}")
        if not self.port_7ffd & 0x10:
            raise RuntimeError(
                f"TR-DOS dispatcher called with 128K ROM selected "
                f"(7FFD={self.port_7ffd:02X}h); bit 4 must select the 48K ROM"
            )
        count=self.b or 256
        logical=self.d*SPT+self.e
        src=logical*SECTOR
        length=count*SECTOR
        if src+length>len(self.trd): raise RuntimeError("disk read outside image")
        dest=self.hl()
        for i,v in enumerate(self.trd[src:src+length]): self.write8(dest+i,v)
        self.dos_reads += 1; self.bytes_read += length
        # Deliberately clobber registers to make accidental dependencies visible.
        self.a=0xA5; self.b=self.c=self.d=self.e=self.h=self.l=0

    def step(self):
        pc0=self.pc; op=self.fetch8(); self.steps+=1
        if op in (0x00,0xF3,0xFB): return
        if op==0x31: self.sp=self.fetch16(); return
        if op==0xAF: self.a=0; self.z=True; self.carry=False; return
        if op==0xD3: self.fetch8(); return
        if op==0x3E: self.a=self.fetch8(); return
        if op==0x01: self.set_bc(self.fetch16()); return
        if op==0x11: self.set_de(self.fetch16()); return
        if op==0x21: self.set_hl(self.fetch16()); return
        if op==0x06: self.b=self.fetch8(); return
        if op==0x0E: self.c=self.fetch8(); return
        if op==0x16: self.d=self.fetch8(); return
        if op==0x1E: self.e=self.fetch8(); return
        if op==0x32: self.write8(self.fetch16(),self.a); return
        if op==0x3A: self.a=self.read8(self.fetch16()); return
        if op==0x22:
            addr=self.fetch16(); v=self.hl(); self.write8(addr,v); self.write8(addr+1,v>>8); return
        if op==0x2A:
            addr=self.fetch16(); self.set_hl(self.read8(addr)|self.read8(addr+1)<<8); return
        if op==0xED:
            q=self.fetch8()
            if q==0x79:
                if self.bc()==0x7FFD:
                    if (self.port_7ffd ^ self.a) & 0x08:
                        self.screen_page_toggles += 1
                    self.port_7ffd=self.a
                return
            if q==0x5B:
                addr=self.fetch16(); self.set_de(self.read8(addr)|self.read8(addr+1)<<8); return
            if q==0xB0:
                n=self.bc(); hl=self.hl(); de=self.de()
                for _ in range(n): self.write8(de,self.read8(hl)); hl=(hl+1)&0xffff; de=(de+1)&0xffff
                self.set_hl(hl); self.set_de(de); self.set_bc(0); return
            raise RuntimeError(f"unsupported ED {q:02X} at {pc0:04X}")
        if op==0xCD:
            target=self.fetch16()
            if target==0x3D13: self.mock_trdos(); return
            self.push(self.pc); self.pc=target; return
        if op==0xC3: self.pc=self.fetch16(); return
        if op in (0xC2,0xCA,0xD2,0xDA):
            target=self.fetch16(); take=(op==0xC2 and not self.z) or (op==0xCA and self.z) or (op==0xD2 and not self.carry) or (op==0xDA and self.carry)
            if take:self.pc=target
            return
        if op==0xC9: self.pc=self.pop(); return
        if op==0xC8:
            if self.z:self.pc=self.pop()
            return
        if op==0xC0:
            if not self.z:self.pc=self.pop()
            return
        if op==0x76: self.halts+=1; return
        if op==0xEE: self.a ^= self.fetch8(); self.z=self.a==0; self.carry=False; return
        if op==0xF6: self.a |= self.fetch8(); self.z=self.a==0; self.carry=False; return
        if op==0xFE: self.cp(self.fetch8()); return
        if op==0xB8: self.cp(self.b); return
        if op==0xB7: self.z=self.a==0; self.carry=False; return
        if op==0xB1: self.a|=self.c; self.z=self.a==0; self.carry=False; return
        if op==0x78: self.a=self.b; return
        if op==0x47: self.b=self.a; return
        if op==0x57: self.d=self.a; return
        if op==0x5F: self.e=self.a; return
        if op==0x67: self.h=self.a; return
        if op==0x7E: self.a=self.read8(self.hl()); return
        if op==0x46: self.b=self.read8(self.hl()); return
        if op==0x4E: self.c=self.read8(self.hl()); return
        if op==0x56: self.d=self.read8(self.hl()); return
        if op==0x5E: self.e=self.read8(self.hl()); return
        if op==0x77: self.write8(self.hl(),self.a); return
        if op==0x12: self.write8(self.de(),self.a); return
        if op==0x23: self.set_hl(self.hl()+1); return
        if op==0x24: self.h=(self.h+1)&255; return
        if op==0x14: self.d=(self.d+1)&255; return
        if op==0x3C: self.a=(self.a+1)&255; self.z=self.a==0; return
        if op==0x3D: self.a=(self.a-1)&255; self.z=self.a==0; return
        if op==0x87:
            t=self.a*2; self.a=t&255; self.carry=t>255; self.z=self.a==0; return
        if op==0x82:
            t=self.a+self.d; self.a=t&255; self.carry=t>255; self.z=self.a==0; return
        if op==0x09: self.set_hl(self.hl()+self.bc()); return
        if op==0x19: self.set_hl(self.hl()+self.de()); return
        if op==0xEB:
            v=self.hl(); self.set_hl(self.de()); self.set_de(v); return
        if op==0x0B: self.set_bc(self.bc()-1); return
        if op==0xF5: self.push(self.a<<8); return
        if op==0xF1: self.a=(self.pop()>>8)&255; return
        if op==0xC5: self.push(self.bc()); return
        if op==0xC1: self.set_bc(self.pop()); return
        if op==0xD5: self.push(self.de()); return
        if op==0xD1: self.set_de(self.pop()); return
        if op==0xE5: self.push(self.hl()); return
        if op==0xE1: self.set_hl(self.pop()); return
        if op==0xCB:
            q=self.fetch8()
            if q==0x39:
                self.carry=bool(self.c&1); self.c>>=1; self.z=self.c==0; return
            raise RuntimeError(f"unsupported CB {q:02X} at {pc0:04X}")
        if op in (0x18,0x20,0x28,0x30,0x38,0x10):
            d=self.rel()
            if op==0x10:
                self.b=(self.b-1)&255; take=self.b!=0
            else:
                take=(op==0x18) or (op==0x20 and not self.z) or (op==0x28 and self.z) or (op==0x30 and not self.carry) or (op==0x38 and self.carry)
            if take:self.pc=(self.pc+d)&0xffff
            return
        raise RuntimeError(f"unsupported opcode {op:02X} at {pc0:04X}")


def parse_dir(trd:bytes):
    out=[]
    for i in range(128):
        e=trd[i*16:(i+1)*16]
        if not e or e[0]==0:break
        out.append((e[:8].decode('ascii').rstrip(),chr(e[8]),e[13],e[15],e[14],struct.unpack_from('<H',e,11)[0]))
    return out


def extract_file(trd:bytes, entry):
    name,typ,sectors,track,sector,length=entry
    off=(track*SPT+sector)*SECTOR
    return trd[off:off+length]


def full_loop_halts(video:bytes):
    if video[:4] != b"ZXVS": raise RuntimeError("bad VIDEO magic")
    initial=video[6]
    count=video[8]
    offset=SECTOR + 2*6912
    holds=[]
    for _ in range(count):
        sec=video[offset]
        holds.append(video[offset+1])
        offset += sec*SECTOR
    return initial*2 + sum(h*2 for h in holds), holds


def main():
    import json
    ap=argparse.ArgumentParser()
    ap.add_argument('trd',type=Path)
    ap.add_argument('--halts',type=int)
    ap.add_argument('--metadata',type=Path)
    ap.add_argument('--expect-no-screen-swaps',action='store_true')
    args=ap.parse_args(); trd=args.trd.read_bytes()
    directory=parse_dir(trd)
    p=next(x for x in directory if x[0]=='PLAYER')
    v=next(x for x in directory if x[0]=='VIDEO')
    player=extract_file(trd,p)
    video=extract_file(trd,v)
    loop_halts, holds=full_loop_halts(video)
    target=args.halts or loop_halts
    main_loop=None
    expect_no_screen_swaps=args.expect_no_screen_swaps
    if args.metadata and args.metadata.exists():
        meta=json.loads(args.metadata.read_text())
        main_loop=meta['player_labels']['main_loop']
        expect_no_screen_swaps = expect_no_screen_swaps or not meta.get('screen_swapping', True)
    cpu=CPU(player,trd)
    max_steps=40_000_000
    code_end=LOAD+len(player)
    reached=False
    while cpu.steps<max_steps:
        cpu.step()
        if not LOAD <= cpu.pc < code_end:
            raise RuntimeError(f"PC escaped player: {cpu.pc:04X}, code end {code_end:04X}")
        if cpu.sp < 0x5D00 or cpu.sp >= 0x6000:
            raise RuntimeError(f"bad SP {cpu.sp:04X}")
        if cpu.halts >= target:
            if main_loop is None:
                reached=True; break
            if cpu.pc == main_loop:
                reached=True; break
    if not reached: raise RuntimeError('validator step limit')
    print(f"validated {cpu.halts} fields, {cpu.steps} instructions")
    print(f"TR-DOS reads: {cpu.dos_reads}, bytes: {cpu.bytes_read}")
    print(f"screen flag/port: {cpu.port_7ffd:02X}h")
    print(f"visible-screen page toggles: {cpu.screen_page_toggles}")
    print(f"minimum SP: {cpu.min_sp:04X}h")
    if expect_no_screen_swaps and cpu.screen_page_toggles:
        raise RuntimeError(
            f'expected fixed screen but observed {cpu.screen_page_toggles} page toggles'
        )
    if args.halts is None and main_loop is not None:
        initial_a=video[SECTOR:SECTOR+6912]
        initial_b=video[SECTOR+6912:SECTOR+2*6912]
        bank5=bytes(cpu.banks[5][:6912])
        bank7=bytes(cpu.banks[7][:6912])
        if bank5 != initial_a: raise RuntimeError('bank 5 does not return to initial phase A')
        if bank7 != initial_b: raise RuntimeError('bank 7 does not return to initial phase B')
        if cpu.port_7ffd != ROM48_BANK7:
            raise RuntimeError(f'loop did not end on phase A with 48K ROM selected: {cpu.port_7ffd:02X}')
        print(f"full circular loop verified: {loop_halts} fields, {len(holds)} packets")
        print("bank 5/7 screens returned exactly to the initial pair")

if __name__=='__main__': main()
