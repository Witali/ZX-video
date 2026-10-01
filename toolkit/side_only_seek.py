"""Opt-in same-cylinder side selection for the pinned TR-DOS 5.03 reader."""
import fap3_disk_z80 as disk


def install(banks,m):
    if not m.get('seek_labels') or m.get('required_trdos_sha256')!=disk.TRDOS_503_SHA256:
        raise ValueError('side-only path requires the pinned cached TR-DOS reader')
    if not m.get('inplace_keepalive',{}).get('enabled'):
        raise ValueError('side-only path requires active head maintenance')
    old,_,_=disk.build_cached_seek(m['disk_labels'])
    code,labels,rows=disk.build_cached_seek(m['disk_labels'],side_only=True)
    at=disk.CACHED_SEEK&16383
    if bytes(banks[2][at:at+len(old)])!=old or any(banks[2][at+len(old):at+len(code)]):
        raise ValueError('cached seek bytes or spare space changed')
    banks[2][at:at+len(code)]=code
    m['seek_labels']=labels
    for name in ('seek_side_enter','seek_side_return','seek_enter','seek_return'):
        m['player_labels'][name]=labels[name]
    m['slot_queue_instruction_listing']=[r for r in m['slot_queue_instruction_listing']
        if not disk.CACHED_SEEK<=r['address']<0x9b00]+rows
    m['side_only_seek']=dict(enabled=True,labels=labels,listing=rows,code_hex=code.hex(),
        required_trdos_sha256=disk.TRDOS_503_SHA256,
        previous_code_bytes=len(old),code_bytes=len(code),extra_stack_bytes=2,
        settle_loop_tstates=717,minimum_side_settle_microseconds=200,
        maximum_supported_cpu_hz=3546900,
        unknown_and_idle_sentinels_use_full_seek=True,
        compressed_stream_changed=False,decoder_changed=False,
        timing_scope='RAM instructions only; ROM, physical disk, IRQ and contention measured separately')
