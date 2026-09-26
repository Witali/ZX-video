"""Preserve the live IM2 clock after successful direct TR-DOS 5.03 reads.

The pinned ROM direct entry preserves I/IM2 and the installed fast vector.
Full dispatcher calls and short-read fallback still restore all IRQ state.
No new code or variables: only the existing successful conditional JP changes.
"""
from fap3_disk_z80 import TRDOS_503_SHA256


def install(read8,put,m):
    if not m.get('fast_disk') or m.get('required_trdos_sha256')!=TRDOS_503_SHA256:
        raise ValueError('fast IRQ return requires the verified 5.03 direct reader')
    d=m['disk_labels'];rows=m['slot_queue_instruction_listing']
    sites=[r for r in rows if r['instruction']=='JP Z,disk_finish']
    if len(sites)!=1:raise ValueError('unexpected successful read branch')
    hook=sites[0]['address'];old=d['disk_finish']
    restore=bytes.fromhex('f33ebeed47ed5e2180bd22bebdfb')
    if bytes(read8(old+i) for i in range(len(restore)))!=restore:raise ValueError('IRQ restoration changed')
    original=bytes([0xca])+old.to_bytes(2,'little')
    if bytes(read8(hook+i) for i in range(3))!=original:raise ValueError('read branch differs')
    target=old+len(restore)
    if bytes(read8(target+i) for i in range(4))!=bytes([0xed,0x5b])+d['disk_position'].to_bytes(2,'little'):
        raise ValueError('unexpected cursor after restoration')
    replacement=bytes([0xca])+target.to_bytes(2,'little')
    put(hook,replacement);sites[0]['instruction']='JP Z,accepted_sector (preserve IM2)'
    return dict(enabled=True,hook_address=hook,previous_hook_hex=original.hex(),hook_hex=replacement.hex(),
        accepted_sector=target,restore_address=old,restoration_hex=restore.hex(),
        previous_success_to_cursor_tstates=115,success_to_cursor_tstates=57,delta_tstates=-58,
        restore_only_tstates=58,full_dispatch_delta_tstates=0,short_read_fallback_delta_tstates=0,
        code_growth_bytes=0,extra_ram_bytes=0,extra_stack_bytes=0,extra_stream_bytes=0,
        required_trdos_sha256=TRDOS_503_SHA256,
        invariants=['I=BEh','IM=2','JP at BDBD targets BD80','direct ROM return followed by EI'],
        timing_excludes=['ROM','IRQ','ULA','physical disk latency'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
