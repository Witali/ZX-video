"""Execute generated Z80 players; validate every frame/AY and count CPU T-states.

TR-DOS sector reads are mocked. Timings exclude ROM execution, ULA contention,
interrupt service, HALT waiting and physical disk latency; use Fuse for those.
Instruction timings: Zilog UM0080, https://www.zilog.com/docs/z80/um0080.pdf.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_streaming_player import CPU as MemoryCPU, extract_file, parse_dir


class CPU(MemoryCPU):
    registers = ("b", "c", "d", "e", "h", "l", None, "a")

    def __init__(self, player: bytes, trd: bytes):
        super().__init__(player, trd)
        self.min_sp = 0x10000  # Ignore the constructor's unused default stack.
        self.ix = 0
        self.tstates = 0
        self.ay_register = 0
        self.ay = bytearray(16)
        self.i = self.im = 0
        self.iff1 = False
        self.alt_a=0; self.alt_z=False; self.alt_carry=False
        self.alt_b=self.alt_c=self.alt_d=self.alt_e=self.alt_h=self.alt_l=0
        self.seek_calls=[]

    def reg(self, index):
        return self.read8(self.hl()) if index == 6 else getattr(self, self.registers[index])

    def put(self, index, value):
        if index == 6:
            self.write8(self.hl(), value)
        else:
            setattr(self, self.registers[index], value & 255)

    def pair(self, index):
        return (self.bc(), self.de(), self.hl(), self.sp)[index]

    def set_pair(self, index, value):
        if index == 3:
            self.sp = value & 65535
        else:
            (self.set_bc, self.set_de, self.set_hl)[index](value)

    def condition(self, index):
        if index > 3:
            raise RuntimeError("unimplemented condition")
        return (not self.z, self.z, not self.carry, self.carry)[index]

    def mock_trdos(self):
        self.write8(0x5CF5,self.d)
        super().mock_trdos()

    def step(self):
        before = self.pc
        try:
            cycles = self.instruction()
        except Exception as exc:
            raise RuntimeError(f"at {before:04X}: {exc}") from exc
        self.tstates += cycles
        self.steps += 1

    def instruction(self):
        op = self.fetch8()
        if op == 0xD9:
            for name in ('b','c','d','e','h','l'):
                value=getattr(self,name);setattr(self,name,getattr(self,'alt_'+name));setattr(self,'alt_'+name,value)
            return 4
        if op == 0x08:
            self.a,self.alt_a=self.alt_a,self.a
            self.z,self.alt_z=self.alt_z,self.z
            self.carry,self.alt_carry=self.alt_carry,self.carry
            return 4
        if op in (0, 0xF3, 0xFB):
            if op != 0: self.iff1 = op == 0xFB
            return 4
        if op == 0x76:
            self.halts += 1
            return 4
        if op == 0xDD:
            q = self.fetch8()
            if q == 0x21:
                self.ix = self.fetch16(); return 14
            if q == 0x23:
                self.ix = (self.ix + 1) & 65535; return 10
            if q == 0xE5:
                self.push(self.ix); return 15
            if q == 0xE1:
                self.ix = self.pop(); return 14
            if q & 0xC7 == 0x46:
                displacement = self.rel()
                self.put((q >> 3) & 7, self.read8(self.ix + displacement)); return 19
            raise RuntimeError(f"unsupported DD {q:02X}")
        if 0x40 <= op < 0x80:
            dest, source = (op >> 3) & 7, op & 7
            self.put(dest, self.reg(source))
            return 7 if 6 in (dest, source) else 4
        if op & 0xC7 == 0x06:
            register = (op >> 3) & 7
            self.put(register, self.fetch8())
            return 10 if register == 6 else 7
        if op & 0xCF == 0x01:
            self.set_pair(op >> 4, self.fetch16()); return 10
        if op & 0xCF in (0x03, 0x0B):
            index = op >> 4
            self.set_pair(index, self.pair(index) + (1 if op & 8 == 0 else -1))
            return 6
        if op & 0xCF == 0x09:
            value = self.hl() + self.pair(op >> 4)
            self.set_hl(value); self.carry = value > 65535; return 11
        if op & 0xC7 in (0x04, 0x05):
            register = (op >> 3) & 7
            value = (self.reg(register) + (1 if op & 1 == 0 else -1)) & 255
            self.put(register, value); self.z = value == 0
            return 11 if register == 6 else 4
        if op in (0x02, 0x12):
            self.write8(self.bc() if op == 2 else self.de(), self.a); return 7
        if op in (0x0A, 0x1A):
            self.a = self.read8(self.bc() if op == 10 else self.de()); return 7
        if op in (0x32, 0x3A):
            address = self.fetch16()
            if op == 0x32: self.write8(address, self.a)
            else: self.a = self.read8(address)
            return 13
        if op in (0x22, 0x2A):
            address = self.fetch16()
            if op == 0x22:
                self.write8(address, self.l); self.write8(address + 1, self.h)
            else:
                self.set_hl(self.read8(address) | self.read8(address + 1) << 8)
            return 16
        if 0x80 <= op < 0xC0 or op & 0xC7 == 0xC6:
            immediate = op >= 0xC0
            value = self.fetch8() if immediate else self.reg(op & 7)
            operation = (op >> 3) & 7
            if operation in (0, 1):
                result = self.a + value + (int(self.carry) if operation == 1 else 0)
                self.carry = result > 255
            elif operation in (2, 3, 7):
                result = self.a - value - (int(self.carry) if operation == 3 else 0)
                self.carry = result < 0
            else:
                result = (self.a & value, self.a ^ value, self.a | value)[operation - 4]
                self.carry = False
            self.z = result & 255 == 0
            if operation != 7: self.a = result & 255
            return 7 if immediate or op & 7 == 6 else 4
        if op == 0x0F:
            self.carry = bool(self.a & 1)
            self.a = (self.a >> 1) | ((self.a & 1) << 7); return 4
        if op == 0x2F:
            self.a ^= 255; return 4  # CPL preserves the modeled Z/C flags.
        if op == 0x17:
            carry = self.carry
            self.carry = bool(self.a & 128)
            self.a = ((self.a << 1) | int(carry)) & 255; return 4
        if op == 0x1F:
            carry = self.carry
            self.carry = bool(self.a & 1)
            self.a = (self.a >> 1) | (int(carry) << 7); return 4
        if op == 0xE3:
            old = self.hl()
            self.set_hl(self.read8(self.sp) | self.read8(self.sp+1) << 8)
            self.write8(self.sp,old); self.write8(self.sp+1,old >> 8); return 19
        if op == 0xEB:
            old = self.hl(); self.set_hl(self.de()); self.set_de(old); return 4
        if op in (0xC5, 0xD5, 0xE5, 0xF5, 0xC1, 0xD1, 0xE1, 0xF1):
            index = (op >> 4) & 3
            if op & 4:
                value = self.pair(index) if index < 3 else self.a << 8 | int(self.z) << 6 | int(self.carry)
                self.push(value); return 11
            value = self.pop()
            if index < 3: self.set_pair(index, value)
            else:
                self.a = value >> 8; self.z = bool(value & 64); self.carry = bool(value & 1)
            return 10
        if op in (0xC3, 0xC2, 0xCA, 0xD2, 0xDA):
            target = self.fetch16()
            if op == 0xC3 and target == 0x3D2F:
                entry=self.pop()
                if entry in (0x1FEB,0x1FF6,0x3E44):
                    # Direct 5.03 side/seek helpers. ROM and physical latency
                    # remain outside this CPU model; Fuse executes the ROM.
                    self.seek_calls.append((entry,self.a,self.b))
                    if entry in (0x1FEB,0x1FF6):
                        value=self.read8(0x5D16)
                        self.write8(0x5D16,value|0x3C if entry==0x1FEB else value&0x6F)
                    self.set_hl(0xA55A);self.set_bc(0xC33C);self.set_de(0xDEAD)
                    self.a=0x81;self.pc=self.pop()
                    return 10
                if entry not in (0x3F0E,0x3F17):
                    self.pc=entry
                    return 24  # JP plus ROM NOP/RET trampoline in IRQ tests.
                if entry==0x3F17:self.pop()  # retry counter saved before ROM core
                self.d=self.read8(0x5CF5);self.e=self.read8(0x5CFF)
                self.set_hl(self.read8(0x5D00) | self.read8(0x5D01)<<8)
                destination=self.hl()
                self.b=1;self.c=5;self.mock_trdos();self.set_hl(destination+256);self.pc=self.pop()
                return 10
            if op == 0xC3 or self.condition((op >> 3) & 7): self.pc = target
            return 10
        if op in (0xCD, 0xC4, 0xCC, 0xD4, 0xDC):
            target = self.fetch16()
            if op != 0xCD and not self.condition((op >> 3) & 7): return 10
            if target == 0x3D13: self.mock_trdos()
            else: self.push(self.pc); self.pc = target
            return 17
        if op in (0xC9, 0xC0, 0xC8, 0xD0, 0xD8):
            if op != 0xC9 and not self.condition((op >> 3) & 7): return 5
            self.pc = self.pop()
            return 10 if op == 0xC9 else 11
        if op in (0x18, 0x20, 0x28, 0x30, 0x38, 0x10):
            distance = self.rel()
            if op == 0x10:
                self.b = (self.b - 1) & 255; take = self.b != 0
            else:
                take = op == 0x18 or self.condition((op - 0x20) >> 3)
            if take: self.pc = (self.pc + distance) & 65535
            return (13 if take else 8) if op == 0x10 else (12 if take else 7)
        if op == 0xD3:
            self.fetch8(); return 11
        if op == 0xCB:
            q = self.fetch8(); register = q & 7; value = self.reg(register)
            if q & 0xF8 in (0x00, 0x08):
                if q & 8:
                    self.carry = bool(value & 1); value = (value >> 1) | ((value & 1) << 7)
                else:
                    self.carry = bool(value & 128); value = ((value << 1) | (value >> 7)) & 255
                self.put(register, value); self.z = value == 0
                return 15 if register == 6 else 8
            if q & 0xC0 == 0xC0:
                self.put(register, value | (1 << ((q >> 3) & 7)))
                return 15 if register == 6 else 8
            if q & 0xC0 == 0x40:
                self.z = value & (1 << ((q >> 3) & 7)) == 0
                return 12 if register == 6 else 8
            if q & 0xF8 == 0x38:
                self.carry = bool(value & 1); value >>= 1
                self.put(register, value); self.z = value == 0
                return 15 if register == 6 else 8
            if q & 0xF8 in (0x10,0x18):
                carry = self.carry
                if q & 8:
                    self.carry = bool(value & 1); value = (value >> 1) | (int(carry) << 7)
                else:
                    self.carry = bool(value & 128); value = ((value << 1) | int(carry)) & 255
                self.put(register,value); self.z = value == 0
                return 15 if register == 6 else 8
            raise RuntimeError(f"unsupported CB {q:02X}")
        if op == 0xED:
            q = self.fetch8()
            if q == 0x47:
                self.i = self.a; return 9
            if q == 0x5E:
                self.im = 2; return 8
            if q == 0x56:
                self.im = 1; return 8
            if q == 0x4D:
                self.pc = self.pop(); return 14
            if q == 0x79:
                port = self.bc()
                if port == 0x7FFD:
                    if (self.port_7ffd ^ self.a) & 8: self.screen_page_toggles += 1
                    self.port_7ffd = self.a
                elif port == 0xFFFD: self.ay_register = self.a & 15
                elif port == 0xBFFD: self.ay[self.ay_register] = self.a
                return 12
            if q & 0xCF in (0x43, 0x4B):
                index = (q >> 4) & 3; address = self.fetch16()
                if q & 8:
                    self.set_pair(index, self.read8(address) | self.read8(address + 1) << 8)
                else:
                    value = self.pair(index)
                    self.write8(address, value); self.write8(address + 1, value >> 8)
                return 20
            if q & 0xCF == 0x42:
                value = self.hl() - self.pair((q >> 4) & 3) - int(self.carry)
                self.set_hl(value); self.carry = value < 0; self.z = self.hl() == 0; return 15
            if q == 0x44:
                self.carry = self.a != 0; self.a = (-self.a) & 255; self.z = self.a == 0; return 8
            if q in (0xB0, 0xB8):
                count = self.bc() or 65536
                step = 1 if q == 0xB0 else -1
                source, dest = self.hl(), self.de()
                for _ in range(count):
                    self.write8(dest, self.read8(source))
                    source = (source + step) & 65535; dest = (dest + step) & 65535
                self.set_hl(source); self.set_de(dest); self.set_bc(0)
                return 21 * count - 5
            raise RuntimeError(f"unsupported ED {q:02X}")
        raise RuntimeError(f"unsupported opcode {op:02X}")


def validate_volume(path, labels, states, ay_states, *, max_steps=100_000_000, decode_fields=None,
                    interrupt_every: int | None = None, clock_checks=None, minimum_read_reserve=0, audio_frames=None):
    import build_long_video_trd as compact
    trd = path.read_bytes()
    player = extract_file(trd, next(e for e in parse_dir(trd) if e[0] == 'PLAYER'))
    cpu = CPU(player, trd)
    screens = [b"".join(compact.expand_compact_screen(state)) for state in states]
    decoded = 0
    delivery_start = None
    delivery_cycles = []
    background_cycles=[];background_start=None;frame_background=0;quantum_cycles=[]
    underflows = 0
    underflow_addresses = {labels[name] for name in ('wait_packet_fill','stream_byte_fill') if name in labels}
    next_interrupt = interrupt_every or 0
    interrupts = 0
    clock_index = 0
    reserve_checks=0;minimum_live_queue=None
    audio_index=0
    def audio_irq():
        nonlocal audio_index
        import ay_interrupt
        return_pc=cpu.pc;before=cpu.tstates
        cpu.push(return_pc);cpu.pc=0xBDBD;cpu.iff1=False
        while cpu.pc!=return_pc:cpu.step()
        assert bytes(cpu.ay[:11])==ay_interrupt.registers(audio_frames[audio_index]), f'50 Hz AY {audio_index}'
        audio_index+=1
        # The deterministic foreground model excludes IRQ execution, as before.
        cpu.tstates=before
    while cpu.steps < max_steps:
        if minimum_read_reserve and cpu.pc==labels['flip_screen']:
            unread=cpu.read8(labels['disk_sectors_remaining'])|cpu.read8(labels['disk_sectors_remaining']+1)<<8
            if unread:
                queued=cpu.read8(labels['ring_count'])|cpu.read8(labels['ring_count']+1)<<8
                assert queued>=minimum_read_reserve, f'queue reserve {queued} at frame {decoded}'
                reserve_checks+=1
                minimum_live_queue=queued if minimum_live_queue is None else min(minimum_live_queue,queued)
        if cpu.pc in underflow_addresses:
            underflows += 1
        if decode_fields is not None and cpu.pc == labels.get('frame_prepared'):
            cpu.write8(labels['field_counter'],decode_fields[decoded-1])
        if clock_checks is not None and cpu.pc == labels['clock_check']:
            value=clock_checks[clock_index];clock_index+=1
            if audio_frames is not None:
                current=cpu.read8(labels['elapsed_fields'])|cpu.read8(labels['elapsed_fields']+1)<<8
                for _ in range((value-current)&65535):audio_irq()
            cpu.write8(labels['elapsed_fields'],value)
            cpu.write8(labels['elapsed_fields']+1,value>>8)
            cpu.alt_h=value>>8;cpu.alt_l=value&255
        if cpu.pc == labels['fatal']:
            raise AssertionError(f"player entered fatal at frame {decoded}")
        if cpu.pc == labels['main_loop']:
            local = decoded
            newest_bank = 5 if local % 2 == 0 else 7
            other_bank = 7 if newest_bank == 5 else 5
            assert bytes(cpu.banks[newest_bank][:6912]) == screens[local], f"frame {local}, bank {newest_bank}"
            assert bytes(cpu.banks[other_bank][:6912]) == screens[max(0, local-1)], f"reference bank at {local}"
            if audio_frames is None:
                expected_ay = compact.AyFrame.deserialize(ay_states[local])
                expected_tones = compact.AyFrame(expected_ay.periods, expected_ay.volumes).serialize()
                assert bytes(cpu.ay[r] for r in (0,1,2,3,4,5,8,9,10)) == expected_tones, f"AY {local}"
                assert cpu.ay[7] == expected_ay.mixer, f"AY mixer {local}"
                assert cpu.ay[6] == expected_ay.noise_period, f"AY noise {local}"
            assert (7 if cpu.port_7ffd & 8 else 5) == newest_bank, f"visible bank {local}"
            decoded += 1
            if decoded>1:
                background_cycles.append(frame_background);frame_background=0
            if decoded == len(states): break
            delivery_start = cpu.tstates
        if cpu.pc == labels['prefetch_loop'] and delivery_start is not None:
            delivery_cycles.append(cpu.tstates - delivery_start)
            delivery_start = None
        if cpu.pc == labels.get('ahead_call'):background_start=cpu.tstates
        if cpu.pc == labels.get('ahead_return'):
            assert background_start is not None
            quantum=cpu.tstates-background_start
            frame_background+=quantum;quantum_cycles.append(quantum);background_start=None
        before_pc=cpu.pc
        cpu.step()
        if audio_frames is not None and before_pc==labels['audio_start']+7:
            audio_irq()  # First HALT starts the sound before the video clock reset.
        # Stress test only: inject between instructions while IM2 is enabled.
        # This is not a Spectrum IRQ timing model (HALT waiting is omitted).
        if interrupt_every and cpu.iff1 and cpu.im == 2 and cpu.tstates >= next_interrupt:
            cpu.push(cpu.pc); cpu.pc = cpu.read8((cpu.i << 8)|255) | cpu.read8((cpu.i << 8)+256) << 8
            cpu.iff1 = False; cpu.tstates += 19
            interrupts += 1; next_interrupt = cpu.tstates+interrupt_every
    else:
        raise AssertionError("instruction limit exceeded")
    assert underflows == 0, f"{underflows} ring underflows"
    if clock_checks is not None: assert clock_index==len(clock_checks)
    if audio_frames is not None:
        while audio_index<len(audio_frames):audio_irq()
        assert cpu.read8(labels['audio_underruns'])==cpu.read8(labels['audio_underruns']+1)==0
    return dict(frames=decoded, instructions=cpu.steps, cpu_tstates=cpu.tstates,
                delivery_tstates=delivery_cycles, dos_reads=cpu.dos_reads,
                background_preparation_tstates=background_cycles,
                background_quantum_count=len(quantum_cycles),
                background_quantum_max_tstates=max(quantum_cycles,default=0),
                disk_bytes=cpu.bytes_read, underflows=underflows, minimum_sp=cpu.min_sp,
                reserve_checks=reserve_checks,minimum_live_queue_before_flip=minimum_live_queue,
                injected_interrupts=interrupts,verified_audio_ticks=audio_index)


def _validate_job(job):
    return validate_volume(**job)


def main():
    import build_fast_sparse_trd as codec
    parser = argparse.ArgumentParser()
    parser.add_argument('build', type=Path)
    parser.add_argument('--source-build', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--ay-50hz',type=Path,help='raw states matching the v11 build')
    parser.add_argument('--fuse-timing', type=Path, help='Replay measured IRQ field counts, excluding IRQ execution from CPU totals')
    parser.add_argument('--jobs',type=int,choices=range(1,9),default=1,help='independent host processes for disk validation')
    args = parser.parse_args()
    meta = json.loads((args.build/'build_metadata.json').read_text())
    if meta.get('pacing') == 'deadline' and not args.fuse_timing:
        parser.error('deadline playback requires --fuse-timing to replay its measured clock')
    states, ay_states, _ = codec.decode_compact_build(args.source_build/'VIDEO_full.C.bin')
    results = []
    timing = json.loads(args.fuse_timing.read_text()) if args.fuse_timing else None
    audio_frames=None
    if meta.get('audio_irq'):
        import build_long_video_trd as compact
        if not args.ay_50hz:parser.error('v11 validation requires --ay-50hz')
        raw=args.ay_50hz.read_bytes()
        audio_frames=[compact.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
        assert len(audio_frames)==6*len(states)
    jobs=[]
    for index,volume in enumerate(meta['volumes']):
        if timing and timing[index].get('trd_sha256'):
            import hashlib
            if hashlib.sha256((args.build/volume['trd_name']).read_bytes()).hexdigest()!=timing[index]['trd_sha256']:
                raise ValueError('Fuse timing belongs to another disk image')
        start, end = volume['frame_start'], volume['frame_end']
        jobs.append(dict(path=args.build/volume['trd_name'],labels=meta['player_labels'],states=states[start:end],ay_states=ay_states[start:end],
                                 decode_fields=timing[index]['decode_fields'] if timing else None,
                                 clock_checks=timing[index].get('clock_checks') or None if timing else None,
                                 minimum_read_reserve=meta.get('read_reserve',0),
                                 audio_frames=audio_frames[start*6:end*6] if audio_frames is not None else None))
    from concurrent.futures import ProcessPoolExecutor
    from contextlib import nullcontext
    with ProcessPoolExecutor(max_workers=args.jobs) if args.jobs>1 else nullcontext() as pool:
        measured=pool.map(_validate_job,jobs) if pool else map(_validate_job,jobs)
        for volume,result in zip(meta['volumes'],measured):
            results.append(result)
            print(f"Verified frames {volume['frame_start']}..{volume['frame_end']-1}; {result['dos_reads']} sector reads",flush=True)
    cycles = [n for result in results for n in result['delivery_tstates']]
    report = dict(scope='player CPU only; excludes contention, ROM, IRQ, HALT waiting and disk latency',
                  timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
                  delivery_scope='main_loop through first prefetch_loop, excluding frame zero',
                  frames=sum(r['frames'] for r in results),
                  delivery_tstates_mean=sum(cycles)/len(cycles), delivery_tstates_max=max(cycles),
                  volumes=results)
    background=[n for result in results for n in result['background_preparation_tstates']]
    report['background_preparation_tstates_mean']=sum(background)/len(background)
    report['combined_preparation_tstates_mean']=(sum(cycles)+sum(background))/len(cycles)
    report['background_quantum_max_tstates']=max(r['background_quantum_max_tstates'] for r in results)
    if args.output: args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'volumes'}, indent=2))


if __name__ == '__main__': main()
