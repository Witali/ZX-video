"""Two fixed compact resident ZX0 v2 decoders derived from Standard.

The SMC profile moves the previous offset from the stack into two writable
instruction bytes. Gamma-JP retains Standard's ROM-compatible stack layout
and replaces only the gamma loop's unconditional jump. No quota, partial
input, paging or external target initializer is required or exposed.

Original algorithm: Einar Saukas and Urusergi, pinned ZX0 revision
ecde3a2ae05061fe06469ed46df81a33b7de7d86; see the package BSD-3-Clause LICENSE.
"""
from ._z80 import MiniAssembler, sha


_PROFILES = {
    "smc": (74, 4, 43, 189794309),
    "gamma-jp": (69, 6, 34, 199881370),
}


def build(profile="smc", *, core=0x8000, core_limit=0x8400):
    """Return fixed raw regions, labels and actual target service inventory.

    Call dzx0_standard with HL=complete input, DE=nonwrapping output and a
    valid caller stack. AF/BC/DE/HL may change; IX/IY and every alternate
    pair, including AF', survive. Keep the complete source and output/history
    resident. The valid forward ZX0 v2 format, including full word lengths,
    is unchanged; exact EOF returns before fetching a nonexistent offset LSB.

    SMC reserves four caller-stack bytes including the return word. Its
    embedded two-byte offset is writable/nonreentrant and reset on EVERY
    entry, inside the measured 43 T startup. Gamma-JP reserves six caller-stack
    bytes, needs no writable code, and includes Standard's 34 T startup. Add
    actual IRQ code and hardware/handler stack headroom separately; preserve
    live working registers across IRQ. Input/output/history are excluded
    from service inventory. No target preparation occurs outside this call.
    """
    if not isinstance(profile, str) or profile not in _PROFILES:
        raise ValueError("unknown Small profile; use smc or gamma-jp")
    if (type(core) is not int or type(core_limit) is not int or
            not 0 <= core < core_limit <= 65536):
        raise ValueError("invalid Small code reservation")
    code_bytes, stack_bytes, startup_tstates, real_tstates = _PROFILES[profile]
    smc = profile == "smc"
    a = MiniAssembler(core)

    def emit(*values): a.emit(*values)
    def call(opcode, target): a.abs16(opcode, target)
    def jump(opcode, target): a.rel8(opcode, target)

    a.label("dzx0_standard")
    emit(0x01, 0xff, 0xff)
    if smc:
        # BC=-1 initializes both offset bytes even after a dirty prior call.
        # This store costs 20 T versus the old PUSH's 11 T: complete startup
        # is 43 T, including INC BC and LD A,80h, versus Standard's 34 T.
        call((0xed, 0x43), "s01_offset")
    else:
        emit(0xc5)
    emit(0x03, 0x3e, 0x80)

    a.label("dzx0s_literals")
    call(0xcd, "dzx0s_elias")
    emit(0xed, 0xb0, 0x87)
    jump(0x38, "dzx0s_new_offset")
    call(0xcd, "dzx0s_elias")

    a.label("dzx0s_copy")
    if smc:
        # Save input HL before loading the retained negative offset. The
        # offset no longer occupies a persistent stack word. Excluding the
        # identical LDIR, this costs 42 T versus 70 T with two EX(SP),HLs.
        emit(0xe5)
        a.labels["s01_offset"] = a.pc+1
        emit(0x21, 0xff, 0xff, 0x19, 0xed, 0xb0, 0xe1)
    else:
        emit(0xe3, 0xe5, 0x19, 0xed, 0xb0, 0xe1, 0xe3)
    emit(0x87)
    jump(0x30, "dzx0s_literals")

    a.label("dzx0s_new_offset")
    if not smc:
        emit(0xc1)
    # Omitting POP BC changes only incoming B during offset gamma. C is
    # replaced by FEh, RL B cannot affect C, and the next ADD A,A replaces
    # its flags before use. LD B,C then discards that temporary high byte.
    # EOF may return earlier with clobbered BC, as the original ABI permits.
    emit(0x0e, 0xfe)
    call(0xcd, "dzx0s_elias_loop")
    emit(0x0c, 0xc8, 0x41, 0x4e, 0x23, 0xcb, 0x18, 0xcb, 0x19)
    if smc:
        call((0xed, 0x43), "s01_offset")
    else:
        emit(0xc5)
    emit(0x01, 1, 0)
    call(0xd4, "dzx0s_elias_backtrack")
    emit(0x03)
    jump(0x18, "dzx0s_copy")

    # The shared interlaced Elias reader retains both rotations for full
    # 16-bit literal/match lengths. Only gamma-JP changes the final loop
    # branch: JP 10 T replaces unconditional JR 12 T, one extra code byte.
    a.label("dzx0s_elias")
    emit(0x0c)
    a.label("dzx0s_elias_loop")
    emit(0x87)
    jump(0x20, "dzx0s_elias_skip")
    emit(0x7e, 0x23, 0x17)
    a.label("dzx0s_elias_skip")
    emit(0xd8)
    a.label("dzx0s_elias_backtrack")
    emit(0x87, 0xcb, 0x11, 0xcb, 0x10)
    if profile == "gamma-jp":
        a.abs16(0xc3, "dzx0s_elias_loop")
    else:
        jump(0x18, "dzx0s_elias_loop")

    if a.pc > core_limit:
        raise ValueError("Small ZX0 exceeds core-limit")
    blob = a.resolve()
    if len(blob) != code_bytes:
        raise ValueError("Small fixed code size changed")
    patches = [a.labels["s01_offset"], a.labels["s01_offset"]+1] if smc else []
    service = dict(code_tables_alignment_and_embedded_state_bytes=len(blob),
        caller_stack_bytes=stack_bytes, external_state_bytes=0,
        scratch_bytes=0, internal_buffer_bytes=0)
    return [(core, blob)], a.labels, dict(entry="dzx0_standard",
        variant="small-"+profile+"-block", small_profile=profile,
        one_shot=True, raw_only=True, coroutine_supported=False,
        code_bytes=len(blob), code_sha256=sha(blob), core_end=a.pc,
        service_memory=service, service_memory_bytes=sum(service.values()),
        total_storage_bytes=sum(service.values()), storage_budget_bytes=10000,
        caller_stack_bytes=stack_bytes, decoder_stack_bytes=stack_bytes-2,
        stack_count_includes_caller_return=True, private_stack_bytes=0,
        state_bytes=0, embedded_mutable_bytes=len(patches),
        embedded_state_counted_once_in_code=True, patched_addresses=patches,
        rom_compatible=not smc, requires_writable_code=smc, nonreentrant=smc,
        startup_tstates=startup_tstates, offset_reset_tstates=20 if smc else 0,
        target_initializer_required=False, runtime_generated_table_bytes=0,
        benchmark_call_scope="complete start entry, all per-call setup, exact EOF and RET",
        external_buffers="complete compressed input and complete output/history; counted separately",
        irq_headroom="add actual IRQ code and hardware/handler stack beyond the declared caller stack",
        preserved_registers=["IX", "IY", "AF'", "BC'", "DE'", "HL'"],
        clobbered_registers=["AF", "BC", "DE", "HL"],
        reference_real_tstates=real_tstates,
        reference_real_tstates_scope="frozen 364 real raw blocks; complete entry setup through EOF; no IRQ/ULA/disk",
        source_commit="ecde3a2ae05061fe06469ed46df81a33b7de7d86",
        timing_source="https://www.zilog.com/docs/z80/um0080.pdf")
