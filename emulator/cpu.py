"""Reusable native CPU and Spectrum128 API for decoder experiments.

Build emulator/build_codec_cpu.ps1 first. The flat guarded runner is a pure
CPU benchmark; banked Spectrum runs use a native C bus and explicit frame IRQ.
Instruction-level ULA contention is deliberately unavailable until its CPU
phase/address annotations have been qualified. No Python byte callbacks run
inside either execution loop.
"""
import ctypes as C
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Registers(C.Structure):
    _fields_ = [(name,C.c_uint32) for name in
        'pc af bc de hl sp ix iy af2 bc2 de2 hl2 wz i r iff1 iff2 im halt q'.split()]


class Status(C.Structure):
    _fields_ = [(name,C.c_uint64) for name in
        'cpu_tstates wait_tstates error error_address error_value input_cursor output_cursor stack_bytes memory_writes'.split()]


class Guards(C.Structure):
    _fields_ = [(name,C.c_uint32) for name in
        'source input_bytes output output_bytes caller_stack'.split()] + [
        ('expected_output',C.POINTER(C.c_uint8))]


class SpectrumState(C.Structure):
    _fields_ = [(name,C.c_uint64) for name in
        'cpu_tstates ula_wait_tstates master_tstates frame_number memory_reads memory_writes ignored_rom_writes paging_writes ignored_paging_writes unmodeled_port_reads unmodeled_port_writes'.split()] + [
        (name,C.c_uint32) for name in
        'frame_tstate paging_latch paged_bank rom_bank screen_bank paging_locked contention_enabled int_active ula_last'.split()] + [
        ('irq_acknowledgements',C.c_uint64)]


def _as_dict(value):
    return {name:getattr(value,name) for name,_ in value._fields_}


def load_library(path=None):
    if path is None:
        path = os.environ.get('CODEC_EMULATOR_DLL',os.environ.get('CODEC_CPU_DLL',
            str(ROOT/'.tmp/codec-cpu/codec_cpu.dll')))
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Build emulator/build_codec_cpu.ps1 first, or set CODEC_EMULATOR_DLL: {path}')
    lib = C.CDLL(str(path))
    signatures = (
        ('codec_cpu_abi_version',C.c_uint32,()),
        ('spectrum128_abi_version',C.c_uint32,()),
        ('codec_cpu_create',C.c_void_p,()),
        ('codec_cpu_destroy',None,(C.c_void_p,)),
        ('codec_cpu_memory',C.POINTER(C.c_uint8),(C.c_void_p,)),
        ('codec_cpu_set_registers',C.c_uint32,(C.c_void_p,C.POINTER(Registers))),
        ('codec_cpu_get_registers',None,(C.c_void_p,C.POINTER(Registers))),
        ('codec_cpu_get_status',None,(C.c_void_p,C.POINTER(Status))),
        ('codec_cpu_disable_guards',None,(C.c_void_p,)),
        ('codec_cpu_set_guards',C.c_uint32,(C.c_void_p,C.POINTER(Guards),C.POINTER(C.c_uint8))),
        ('codec_cpu_set_bus',None,(C.c_void_p,C.c_void_p,C.c_void_p)),
        ('codec_cpu_run_to_pc',C.c_uint32,(C.c_void_p,C.c_uint32,C.c_uint64,C.c_uint32)),
        ('spectrum128_create',C.c_void_p,(C.c_int,)),
        ('spectrum128_destroy',None,(C.c_void_p,)),
        ('spectrum128_get_state',None,(C.c_void_p,C.POINTER(SpectrumState))),
        ('spectrum128_set_phase',C.c_int,(C.c_void_p,C.c_uint32)),
        ('spectrum128_mapping',C.c_uint32,(C.c_void_p,C.c_uint16)),
        ('spectrum128_peek',C.c_uint8,(C.c_void_p,C.c_uint16)),
        ('spectrum128_port_write',C.c_int,(C.c_void_p,C.c_uint16,C.c_uint8)),
        ('spectrum128_load_ram',C.c_int,(C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32)),
        ('spectrum128_load_rom',C.c_int,(C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32)))
    for name,result,args in signatures:
        function = getattr(lib,name)
        function.argtypes,function.restype = list(args),result
    if lib.codec_cpu_abi_version() != 2:
        raise RuntimeError('Unsupported native CPU ABI; rebuild the matching sources')
    if lib.spectrum128_abi_version() != 1:
        raise RuntimeError('Unsupported Spectrum128 bus ABI; rebuild the matching sources')
    return lib


class CPU:
    """An owned native CPU. Configure state before running to a stop PC."""
    def __init__(self,library=None):
        self.lib = library if library is not None else load_library()
        self.handle = self.lib.codec_cpu_create()
        if not self.handle:
            raise MemoryError('Cannot allocate native CPU')
        self._spectrum = None
        self._retained_guards = None

    def close(self):
        if self.handle:
            self.lib.codec_cpu_destroy(self.handle)
            self.handle = None
        self._spectrum = self._retained_guards = None

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close()

    @property
    def memory(self):
        if not self.handle:
            raise RuntimeError('CPU is closed')
        if self._spectrum is not None:
            raise RuntimeError('Use Spectrum128.read/load for the attached banked memory')
        pointer = self.lib.codec_cpu_memory(self.handle)
        return (C.c_uint8*65536).from_address(C.addressof(pointer.contents))

    def load(self,address,data):
        data = bytes(data)
        if not 0 <= address <= 65536-len(data):
            raise ValueError('Flat memory load crosses 64 KiB')
        self.memory[address:address+len(data)] = data

    def set_registers(self,**values):
        if values.get('halt',0):
            raise ValueError('HALT is a getter-only diagnostic; register setup starts at an instruction boundary')
        known = {name for name,_ in Registers._fields_}
        if not set(values) <= known:
            raise ValueError('Unknown CPU register')
        if any(type(v) is not int or not 0 <= v <= 65535 for v in values.values()):
            raise ValueError('CPU register values must be unsigned words')
        if not self.lib.codec_cpu_set_registers(self.handle,C.byref(Registers(**values))):
            raise ValueError(('Native register setup rejected',self.status()))

    def registers(self):
        value = Registers()
        self.lib.codec_cpu_get_registers(self.handle,C.byref(value))
        return _as_dict(value)

    def status(self):
        value = Status()
        self.lib.codec_cpu_get_status(self.handle,C.byref(value))
        return _as_dict(value)

    def run(self,stop=0x100,*,budget=20_000_000,fast=True):
        if not self.handle or not 0 <= stop <= 65535 or budget <= 0:
            raise ValueError('Invalid CPU handle, stop PC or budget')
        code = self.lib.codec_cpu_run_to_pc(self.handle,stop,budget,bool(fast))
        status = self.status()
        if code == 2:
            raise AssertionError(('native memory guard',status))
        if code == 1:
            raise TimeoutError(('native CPU budget exhausted',status))
        return status


class Spectrum128:
    """Native 128K bus; exact frame IRQ, currently uncontended CPU execution."""
    def __init__(self,*,library=None,contention=False):
        self.lib = library if library is not None else load_library()
        self.handle = self.lib.spectrum128_create(bool(contention))
        if not self.handle:
            raise MemoryError('Cannot allocate Spectrum128 bus')
        self._cpu = None

    def close(self):
        if self._cpu is not None and self._cpu.handle:
            self.lib.codec_cpu_set_bus(self._cpu.handle,None,None)
            self._cpu._spectrum = None
        self._cpu = None
        if self.handle:
            self.lib.spectrum128_destroy(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close()

    def state(self):
        result = SpectrumState()
        self.lib.spectrum128_get_state(self.handle,C.byref(result))
        return _as_dict(result)

    def attach(self,cpu):
        if self.state()['contention_enabled']:
            raise NotImplementedError('Instruction-level ULA phase/address hooks are not yet qualified; use contention=False')
        if self._cpu is not None or cpu._spectrum is not None or self.lib._name != cpu.lib._name:
            raise ValueError('Attach one CPU and bus from the same native build')
        self._cpu,cpu._spectrum = cpu,self
        self.lib.codec_cpu_set_bus(cpu.handle,C.cast(self.lib.spectrum128_cpu_bus,C.c_void_p),self.handle)

    def set_phase(self,tstate):
        if not 0 <= tstate < 70908 or not self.lib.spectrum128_set_phase(self.handle,tstate):
            raise ValueError('Spectrum frame phase must be 0..70907')

    def load_rom(self,bank,data,offset=0):
        data = bytes(data)
        if bank not in (0,1) or not 0 <= offset <= 16384-len(data):
            raise ValueError('ROM load must fit a physical 16 KiB page')
        buffer = C.create_string_buffer(data)
        if not self.lib.spectrum128_load_rom(self.handle,bank,offset,buffer,len(data)):
            raise ValueError('Native ROM load failed')

    def load(self,address,data):
        data = bytes(data)
        if not 0x4000 <= address <= 65536-len(data):
            raise ValueError('Logical RAM setup must stay within 4000h..FFFFh; use load_rom for ROM')
        while data:
            size = min(len(data),16384-(address&16383))
            bank = self.lib.spectrum128_mapping(self.handle,address)
            buffer = C.create_string_buffer(data[:size])
            if bank >= 8 or not self.lib.spectrum128_load_ram(self.handle,bank,address&16383,buffer,size):
                raise ValueError('Native banked RAM load failed')
            address,data = address+size,data[size:]

    def read(self,address,size):
        if not 0 <= size <= 65536 or not 0 <= address <= 65536-size:
            raise ValueError('Logical read crosses 64 KiB')
        return bytes(self.lib.spectrum128_peek(self.handle,address+i) for i in range(size))

    def out(self,port,value):
        if not 0 <= port <= 65535 or not 0 <= value <= 255:
            raise ValueError('Invalid port/value')
        return bool(self.lib.spectrum128_port_write(self.handle,port,value))


def execute_block(profile,payload,expected,*,library=None,source=0x2000,
                  output=0xc000,caller_stack=0xbff0,fast=True,dirty_offset=True):
    """Guarded flat CPU replay; I/O overlap/IRQ use the independent runners.

    All live allocations must be disjoint. Native guards enforce source order,
    exact output bytes, the stack window and the declared mutable operands.
    Final code and return cursors/registers are also checked in Python.
    """
    payload,expected = bytes(payload),bytes(expected)
    regions,labels,metadata = profile
    allocations = [(at,at+len(blob),'code') for at,blob in regions]
    allocations += [(source,source+len(payload),'input'),(caller_stack-64,caller_stack,'stack'),(0x100,0x101,'stop')]
    if expected:
        allocations.append((output,output+len(expected),'output'))
    for index,(lo,hi,name) in enumerate(allocations):
        if not 0 <= lo < hi <= 65536:
            raise ValueError(('Invalid allocation',name,lo,hi))
        for other_lo,other_hi,other in allocations[index+1:]:
            if not (hi <= other_lo or other_hi <= lo):
                raise ValueError(('Overlapping allocations',name,other))
    if output+len(expected)>65535:
        raise ValueError('Output cursor must not wrap')
    permissions = bytearray(65536)
    patches = set(metadata.get('patched_addresses',()))
    with CPU(library) as cpu:
        for at,blob in regions:
            cpu.load(at,blob)
            permissions[at:at+len(blob)] = b'\1'*len(blob)
        for at in patches:
            if not any(lo <= at < lo+len(blob) for lo,blob in regions):
                raise ValueError('Mutable operand is outside code')
            permissions[at] |= 2
            if dirty_offset:
                cpu.memory[at] = 0xa5
        initial_code = [(at,bytes(cpu.memory[at:at+len(blob)])) for at,blob in regions]
        permissions[caller_stack-64:caller_stack] = b'\1'*64
        permissions[0x100] = 1
        cpu.load(source,payload)
        cpu.load(caller_stack-2,(0x100).to_bytes(2,'little'))
        expected_buffer = (C.c_uint8*max(1,len(expected)))(*expected)
        guard = Guards(source,len(payload),output,len(expected),caller_stack,expected_buffer)
        permission_buffer = (C.c_uint8*65536).from_buffer(permissions)
        if not cpu.lib.codec_cpu_set_guards(cpu.handle,C.byref(guard),permission_buffer):
            raise ValueError('Native guard setup rejected')
        cpu.set_registers(pc=labels[metadata['entry']],sp=caller_stack-2,hl=source,de=output,
            af=0x5a93,bc=0xb7d9,ix=0x1357,iy=0x57b9,af2=0x9797,
            bc2=0x2468,de2=0x369a,hl2=0xace1)
        status = cpu.run(fast=fast)
        registers = cpu.registers()
        assert status['input_cursor'] == source+len(payload)
        assert status['output_cursor'] == output+len(expected)
        assert registers['hl'] == source+len(payload) and registers['de'] == output+len(expected)
        assert registers['sp'] == caller_stack
        for name,value in dict(ix=0x1357,iy=0x57b9,bc2=0x2468,de2=0x369a,hl2=0xace1).items():
            assert registers[name] == value,(name,registers[name])
        assert bytes(cpu.memory[output:output+len(expected)]) == expected
        for at,blob in initial_code:
            assert all(cpu.memory[at+i] == value for i,value in enumerate(blob) if at+i not in patches)
        return dict(tstates=status['cpu_tstates'],exact=True,stack_bytes=status['stack_bytes'],
            ula_wait_tstates=status['wait_tstates'],registers=registers,
            input_bytes=len(payload),output_history_bytes=len(expected),
            backend='z80-tester C flat guarded',interrupts=False,
            contention=False,compressed_overlap=False,dirty_offset_startup_tested=dirty_offset)
