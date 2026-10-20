"""Spectrum128 bus primitives and bounded native CPU integration.

Build with emulator/build_codec_cpu.ps1 -ExtraSources emulator/src/spectrum128.c
before running. CODEC_EMULATOR_DLL selects another native artifact;
CODEC_CPU_DLL remains a compatibility alias.
Contention tests prove explicit bus phases, not an unannotated full instruction
run. The pin callback is qualified here only for no-contention CPU benchmarks.
"""
import ctypes as C
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
QWORD_FIELDS = ('cpu_tstates', 'ula_wait_tstates', 'master_tstates', 'frame_number',
    'memory_reads', 'memory_writes', 'ignored_rom_writes', 'paging_writes',
    'ignored_paging_writes', 'unmodeled_port_reads', 'unmodeled_port_writes')
WORD_FIELDS = ('frame_tstate', 'paging_latch', 'paged_bank', 'rom_bank', 'screen_bank',
    'paging_locked', 'contention_enabled', 'int_active', 'ula_last')


class State(C.Structure):
    _fields_ = [(key, C.c_uint64) for key in QWORD_FIELDS] + [(key, C.c_uint32) for key in WORD_FIELDS] + [
        ('irq_acknowledgements',C.c_uint64)]


class Registers(C.Structure):
    _fields_ = [(key, C.c_uint32) for key in ('pc', 'af', 'bc', 'de', 'hl', 'sp', 'ix',
        'iy', 'af2', 'bc2', 'de2', 'hl2', 'wz', 'i', 'r', 'iff1', 'iff2', 'im', 'halt', 'q')]


class Spectrum128Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('CODEC_EMULATOR_DLL',os.environ.get('CODEC_CPU_DLL',
            str(ROOT/'.tmp/codec-cpu/codec_cpu.dll'))))
        cls.lib = C.CDLL(str(path))
        cls.bind('abi_version',C.c_uint32)
        if cls.abi_version() != 1:
            raise RuntimeError('Rebuild the matching Spectrum bus ABI1')
        cls.bind('create', C.c_void_p, C.c_int)
        cls.bind('destroy', None, C.c_void_p)
        cls.bind('reset', None, C.c_void_p)
        cls.bind('get_state', None, C.c_void_p, C.POINTER(State))
        cls.bind('set_contention', None, C.c_void_p, C.c_int)
        cls.bind('set_phase', C.c_int, C.c_void_p, C.c_uint32)
        cls.bind('advance', None, C.c_void_p, C.c_uint32, C.c_uint32)
        cls.bind('int_active', C.c_int, C.c_void_p)
        for name in ('load_ram', 'load_rom', 'copy_ram'):
            cls.bind(name, C.c_int, C.c_void_p, C.c_uint32, C.c_uint32, C.c_void_p, C.c_uint32)
        cls.bind('mapping', C.c_uint32, C.c_void_p, C.c_uint16)
        cls.bind('peek', C.c_uint8, C.c_void_p, C.c_uint16)
        cls.bind('read', C.c_uint8, C.c_void_p, C.c_uint16)
        cls.bind('write', None, C.c_void_p, C.c_uint16, C.c_uint8)
        cls.bind('port_write', C.c_int, C.c_void_p, C.c_uint16, C.c_uint8)
        cls.bind('port_read', C.c_uint8, C.c_void_p, C.c_uint16)
        cls.bind('delay_at', C.c_uint32, C.c_void_p, C.c_uint16, C.c_uint64)
        cls.bind('delay', C.c_uint32, C.c_void_p, C.c_uint16)
        for name in ('mem_cycle', 'internal_cycles'):
            cls.bind(name, C.c_uint32, C.c_void_p, C.c_uint16, C.c_uint32)
        cls.bind('io_cycle', C.c_uint32, C.c_void_p, C.c_uint16)
        cls.bind('port_write_cycle', C.c_uint32, C.c_void_p, C.c_uint16, C.c_uint8)
        cls.lib.codec_cpu_create.restype = C.c_void_p
        cls.lib.codec_cpu_destroy.argtypes = [C.c_void_p]
        cls.lib.codec_cpu_set_bus.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
        cls.lib.codec_cpu_set_registers.argtypes = [C.c_void_p, C.POINTER(Registers)]
        cls.lib.codec_cpu_set_registers.restype = C.c_uint32
        cls.lib.codec_cpu_get_registers.argtypes = [C.c_void_p, C.POINTER(Registers)]
        cls.lib.codec_cpu_run_to_pc.argtypes = [C.c_void_p, C.c_uint32, C.c_uint64, C.c_uint32]
        cls.lib.codec_cpu_run_to_pc.restype = C.c_uint32

    @classmethod
    def bind(cls, name, result, *arguments):
        function = getattr(cls.lib, 'spectrum128_'+name)
        function.restype, function.argtypes = result, list(arguments)
        setattr(cls, name, staticmethod(function))

    def setUp(self):
        self.bus = self.create(1)
        self.assertTrue(self.bus)
        self.addCleanup(self.destroy, self.bus)

    def state(self):
        result = State()
        self.get_state(self.bus, C.byref(result))
        return result

    def load(self, name, bank, offset, data):
        blob = C.create_string_buffer(data)
        self.assertEqual(getattr(self, name)(self.bus, bank, offset, blob, len(data)), 1)

    def test_reset_map_and_all_physical_ram_banks(self):
        for bank in range(8):
            self.load('load_ram', bank, 0, bytes([bank])*16384)
        for bank in range(2):
            self.load('load_rom', bank, 0, bytes([0xa0+bank])*16384)
        self.assertEqual([self.mapping(self.bus, at) for at in (0,0x4000,0x8000,0xc000)], [8,5,2,0])
        for value in range(32):
            self.assertEqual(self.port_write(self.bus, 0x7ffd, value), 1)
            self.assertEqual(self.peek(self.bus, 0), 0xa0+((value>>4)&1))
            self.assertEqual(self.peek(self.bus, 0x4000), 5)
            self.assertEqual(self.peek(self.bus, 0x8000), 2)
            self.assertEqual(self.peek(self.bus, 0xffff), value&7)
            self.assertEqual(self.state().screen_bank, 7 if value&8 else 5)

    def test_aliases_share_physical_ram_and_rom_is_read_only(self):
        for bank, fixed in ((2,0x8000), (5,0x4000)):
            self.port_write(self.bus, 0x7ffd, bank)
            self.write(self.bus, fixed+21, 0x35)
            self.assertEqual(self.read(self.bus, 0xc015), 0x35)
            self.write(self.bus, 0xc016, 0x76)
            self.assertEqual(self.read(self.bus, fixed+22), 0x76)
        self.load('load_rom', 0, 0, b'\x91')
        self.write(self.bus, 0, 0)
        self.assertEqual(self.peek(self.bus, 0), 0x91)
        self.assertEqual(self.state().ignored_rom_writes, 1)

    def test_partial_7ffd_decode_exhaustive_and_even_ula_alias(self):
        # Every address bit other than A15/A1 is a don't-care, including A0.
        for port in range(65536):
            self.port_write(self.bus, 0x7ffd, 0)
            self.port_write(self.bus, port, 0x1f)
            self.assertEqual(self.state().paging_latch, 0x1f if port&0x8002 == 0 else 0, hex(port))
        self.port_write(self.bus, 0x0000, 0x1b)
        state = self.state()
        self.assertEqual((state.paged_bank, state.rom_bank, state.screen_bank, state.ula_last), (3,1,7,0x1b))

    def test_paging_lock_applies_its_own_value_and_survives_later_writes(self):
        self.port_write(self.bus, 0x7ffd, 0x3d)
        self.port_write(self.bus, 0x7ffd, 0)
        self.port_write(self.bus, 0, 0x12)
        state = self.state()
        self.assertEqual((state.paging_latch, state.paged_bank, state.rom_bank, state.screen_bank), (0x3d,5,1,7))
        self.assertEqual((state.paging_locked, state.ignored_paging_writes, state.ula_last), (1,2,0x12))
        self.write(self.bus, 0xc021, 0x69)
        self.reset(self.bus)
        self.assertEqual((self.state().paging_latch, self.state().paging_locked), (0,0))
        self.assertEqual(self.peek(self.bus, 0x4021), 0x69)

    def test_load_bounds_and_no_observer_or_time_side_effects(self):
        blob = C.create_string_buffer(b'\x17')
        for name, banks in (('load_ram',8), ('load_rom',2), ('copy_ram',8)):
            for bank, offset, size in ((banks,0,1), (0,16384,1), (0,0,16385), (0,0xffffffff,1)):
                self.assertEqual(getattr(self,name)(self.bus, bank, offset, blob, size), 0)
            self.assertEqual(getattr(self,name)(self.bus, 0, 16384, None, 0), 1)
        self.assertEqual(self.state().memory_reads, 0)
        self.assertEqual(self.state().cpu_tstates, 0)

    def test_frame_int_window_36t_and_separate_wait_clock(self):
        self.assertEqual(self.int_active(self.bus), 1)
        self.advance(self.bus, 35, 0)
        self.assertEqual(self.int_active(self.bus), 1)
        self.advance(self.bus, 1, 0)
        self.assertEqual(self.int_active(self.bus), 0)
        self.assertEqual(self.set_phase(self.bus, 70907), 1)
        self.advance(self.bus, 2, 3)
        state = self.state()
        self.assertEqual((state.cpu_tstates,state.ula_wait_tstates,state.master_tstates), (2,3,70912))
        self.assertEqual((state.frame_number,state.frame_tstate,state.int_active), (1,4,1))
        self.assertEqual(self.set_phase(self.bus, 70908), 0)
        self.assertEqual(self.state().master_tstates, 70912)

    def test_full_frame_contention_table_and_physical_bank_identity(self):
        # Independent frame/line mask, including both boundaries of every row.
        reference = bytearray(70908)
        pattern = bytes((6,5,4,3,2,1,0,0))*16
        for line in range(192):
            begin = 14361+228*line
            reference[begin:begin+128] = pattern
        for time, expected in enumerate(reference):
            self.assertEqual(self.delay_at(self.bus, 0x4000, time), expected, time)
        for bank in range(8):
            self.port_write(self.bus, 0x7ffd, bank)
            self.assertEqual(self.delay_at(self.bus,0xc000,14361), 6 if bank&1 else 0)
            self.assertEqual(self.delay_at(self.bus,0xc000,14361+70908), 6 if bank&1 else 0)
        self.assertEqual(self.delay_at(self.bus,0,14361), 0)
        self.assertEqual(self.delay_at(self.bus,0x8000,14361), 0)
        # Shadow-screen selection changes the display source, not CPU bank arbitration.
        self.port_write(self.bus,0x7ffd,8)
        self.assertEqual(self.delay_at(self.bus,0x4000,14361), 6)
        self.assertEqual(self.delay_at(self.bus,0xc000,14361), 0)

    def test_memory_and_internal_cycle_timing_golden_cases(self):
        for length in (3,4):
            self.set_phase(self.bus,14361)
            self.assertEqual(self.mem_cycle(self.bus,0x4000,length), 6)
            self.assertEqual((self.state().cpu_tstates,self.state().ula_wait_tstates), (length,6))
        self.set_phase(self.bus,14361)
        self.assertEqual(self.internal_cycles(self.bus,0x4000,4), 12)
        self.assertEqual((self.state().cpu_tstates,self.state().ula_wait_tstates,self.state().master_tstates), (4,12,14377))
        self.set_phase(self.bus,14360)
        self.assertEqual(self.mem_cycle(self.bus,0x4000,3), 0)
        self.assertEqual(self.state().master_tstates,14363)

    def test_io_cycle_four_port_classes_and_latch_update(self):
        # Golden waits at the first display contention T: N:4=0,
        # N:1,C:3=5, C:1,C:3=6, C:1,C:1,C:1,C:1=12.
        for port, wait in ((0x80ff,0), (0x80fe,5), (0x40fe,6), (0x40ff,12), (0x7ffd,12)):
            self.set_phase(self.bus,14361)
            self.assertEqual(self.io_cycle(self.bus,port), wait, hex(port))
            self.assertEqual((self.state().cpu_tstates,self.state().ula_wait_tstates), (4,wait))
        self.set_phase(self.bus,14361)
        self.assertEqual(self.port_write_cycle(self.bus,0x7ffd,5), 12)
        self.assertEqual(self.state().paged_bank,5)
        self.port_write(self.bus,0x7ffd,1)
        self.set_phase(self.bus,14361)
        self.assertEqual(self.io_cycle(self.bus,0xc0ff),12)
        self.port_write(self.bus,0x7ffd,2)
        self.set_phase(self.bus,14361)
        self.assertEqual(self.io_cycle(self.bus,0xc0ff),0)

    def test_no_contention_mode_and_unsupported_ports_are_explicit(self):
        self.set_contention(self.bus,0)
        self.set_phase(self.bus,14361)
        self.assertEqual(self.internal_cycles(self.bus,0x4000,4),0)
        self.assertEqual(self.io_cycle(self.bus,0x7ffd),0)
        self.assertEqual(self.state().cpu_tstates,8)
        self.assertEqual(self.state().ula_wait_tstates,0)
        self.assertEqual(self.port_read(self.bus,0x7ffd),255)
        self.assertEqual(self.state().unmodeled_port_reads,1)
        self.port_write(self.bus,0xfffd,3)
        self.assertEqual(self.state().unmodeled_port_writes,1)

    def cpu(self, program, *, phase=0):
        self.set_contention(self.bus,0)
        self.set_phase(self.bus,phase)
        self.load('load_ram',2,0,program)
        self.load('load_ram',2,0x3fee,b'\x00\x90')
        cpu = self.lib.codec_cpu_create()
        self.assertTrue(cpu)
        self.addCleanup(self.lib.codec_cpu_destroy,cpu)
        self.lib.codec_cpu_set_bus(cpu,C.cast(self.lib.spectrum128_cpu_bus,C.c_void_p),self.bus)
        registers = Registers(pc=0x8000,sp=0xbfee)
        self.assertEqual(self.lib.codec_cpu_set_registers(cpu,C.byref(registers)),1)
        return cpu

    def test_native_pin_bus_executes_paging_and_physical_alias_without_python_callbacks(self):
        program = bytes.fromhex('01fd7f 3e05 ed79 2100c0 365a 3a0040 c9')
        cpu = self.cpu(program,phase=14361)
        self.assertEqual(self.lib.codec_cpu_run_to_pc(cpu,0x9000,1000,1),0)
        registers = Registers()
        self.lib.codec_cpu_get_registers(cpu,C.byref(registers))
        self.assertEqual(registers.af>>8,0x5a)
        self.assertEqual(registers.sp,0xbff0)
        self.assertEqual(self.peek(self.bus,0x4000),0x5a)
        self.assertEqual((self.state().cpu_tstates,self.state().ula_wait_tstates), (72,0))
        self.assertEqual(self.state().master_tstates,14361+72)

    def test_native_int_accepts_after_ei_halt_but_expires_at_36t(self):
        # First run crosses the frame boundary; the second expires during EI's
        # one-instruction inhibition. An expired ULA pulse must not stay queued.
        program = bytes.fromhex('ed56 fb 76 00')
        cpu = self.cpu(program,phase=70908-12)
        self.assertEqual(self.lib.codec_cpu_run_to_pc(cpu,0x0038,100,0),0)
        registers = Registers()
        self.lib.codec_cpu_get_registers(cpu,C.byref(registers))
        self.assertEqual(registers.sp,0xbfec)
        self.assertEqual(self.state().cpu_tstates,29)
        self.assertEqual(self.state().frame_tstate,17)
        self.assertEqual(self.state().irq_acknowledgements,1)
        self.reset(self.bus)
        cpu = self.cpu(program,phase=24)
        self.assertEqual(self.lib.codec_cpu_run_to_pc(cpu,0x0038,100,0),1)
        self.lib.codec_cpu_get_registers(cpu,C.byref(registers))
        self.assertEqual(registers.sp,0xbfee)
        self.assertEqual(self.state().int_active,0)
        self.assertEqual(self.state().irq_acknowledgements,0)


if __name__ == '__main__':
    unittest.main()
