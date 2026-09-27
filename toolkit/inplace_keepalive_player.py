"""Maintain the current drive cylinder while large decoded slots are full.

The separate pre-read recovery remains available. This periodic hook issues
no READ, does not advance stream cursors, and preserves both register sets.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha, padded, sectors
from inplace_slot_player import Builder as PreviousBuilder
from pipelined_frame_z80 import helpers
from fap3_disk_z80 import DISK_STACK, TRDOS_503_SHA256

CODE, LIMIT = 0x7e70, 0x7f00


def build(d, elapsed, last, *, threshold=64):
    if not 1 <= threshold <= 100: raise ValueError('unsupported keepalive threshold')
    a = MiniAssembler(CODE); rows = []; e, n = helpers(a, rows, 'inplace_keepalive')
    def load(label): n('LD A,('+str(label)+')', 0x3a, label, 13)
    def wl(label): n('LD HL,('+str(label)+')', 0x2a, label, 16)
    def ws(label): n('LD ('+str(label)+'),HL', 0x22, label, 16)
    def jump(op, label): n('JP '+str(label), op, label, 10)
    a.label('check')
    for name, op in (('AF',0xf5), ('BC',0xc5), ('DE',0xd5), ('HL',0xe5)): e('PUSH '+name, [op], 11)
    wl(d['remaining']); e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4); jump(0xca, 'done')
    load(d['cached_track']); e('CP FEh', [0xfe, 254], 7); jump(0xd2, 'done')
    wl(elapsed); n('LD DE,(last service)', (0xed,0x5b), last, 20)
    e('OR A', [0xb7], 4); e('SBC HL,DE', [0xed,0x52], 15)
    e('LD A,H', [0x7c], 4); e('OR A', [0xb7], 4); jump(0xc2, 'due')
    e('LD A,L', [0x7d], 4); e('CP threshold', [0xfe,threshold], 7); jump(0xda, 'done')
    a.label('due'); n('CALL keepalive', 0xcd, 'keepalive', 17)
    a.label('done')
    for name, op in (('HL',0xe1), ('DE',0xd1), ('BC',0xc1), ('AF',0xf1)): e('POP '+name, [op], 10)
    e('RET', [0xc9], 10)
    a.label('keepalive')
    n('LD (saved_sp),SP', (0xed,0x73), d['saved_sp'], 20); n('LD SP,disk stack', 0x31, DISK_STACK, 10)
    e('PUSH IX', [0xdd,0xe5], 15); e('PUSH IY', [0xfd,0xe5], 15)
    e("EX AF,AF'", [0x08], 4); e('PUSH AF', [0xf5], 11); e("EX AF,AF'", [0x08], 4)
    e('EXX', [0xd9], 4)
    for name, op in (('BC',0xc5), ('DE',0xd5), ('HL',0xe5)): e('PUSH '+name, [op], 11)
    e('EXX', [0xd9], 4)
    n('LD HL,slow IRQ', 0x21, 0xbd00, 10); ws(0xbdbe)
    e('LD B,0', [0x06,0], 7)
    n('LD HL,keepalive return', 0x21, 'keepalive_return', 10); e('PUSH HL', [0xe5], 11)
    n('LD HL,SEEK 5.03', 0x21, 0x3e44, 10); e('PUSH HL', [0xe5], 11)
    e('LD A,BEh', [0x3e,0xbe], 7); e('LD I,A', [0xed,0x47], 9); e('IM 2', [0xed,0x5e], 8)
    load(d['cached_track']); e('SRL A', [0xcb,0x3f], 8); e('EI', [0xfb], 4)
    a.label('keepalive_enter'); jump(0xc3, 0x3d2f)
    a.label('keepalive_return'); e('EI', [0xfb], 4)
    n('LD HL,fast IRQ', 0x21, 0xbd80, 10); ws(0xbdbe)
    wl(elapsed); ws(last); jump(0xc3, d['disk_restore'])
    a.label('end')
    if a.pc > LIMIT: raise ValueError('keepalive exceeds retired producer space')
    return a.resolve(), dict(a.labels), rows


def install(read8, put, m):
    if not m.get('inplace_video') or m['required_trdos_sha256']!=TRDOS_503_SHA256:
        raise ValueError('requires the measured in-place TR-DOS 5.03 player')
    p, audio = m['producer_labels'], m['resident_audio']
    code, labels, rows = build(m['disk_labels'], m['player_labels']['elapsed_fields'], p['last_read_field'])
    if p['end']>CODE or any(read8(CODE+i) for i in range(len(code))):
        raise ValueError('keepalive space is not free')
    # Service in both foreground frame work and queue waits. A busy run of
    # ready frames need not call queue.step often enough to keep the drive on.
    hook = audio['hooks']['end']
    service = audio['service_labels']['service']
    before = b'\xcd'+service.to_bytes(2, 'little')
    sites = [audio['hooks'][name] for name in ('queue_service','drain_service','frame_service','prepare_service','draw_service')]
    if (any(bytes(read8(at+i) for i in range(3))!=before for at in sites)
            or hook+6>0xdc00 or any(read8(hook+i) for i in range(6))):
        raise ValueError('unexpected audio-service hook layout')
    wrapper = b'\xcd'+service.to_bytes(2, 'little')+b'\xc3'+labels['check'].to_bytes(2, 'little')
    after = b'\xcd'+hook.to_bytes(2, 'little')
    put(CODE, code); put(hook, wrapper)
    for at in sites: put(at, after)
    extra = [dict(address=hook,instruction='CALL audio service',tstates=17,phase='inplace_keepalive_hook'),
             dict(address=hook+3,instruction='JP periodic drive service',tstates=10,phase='inplace_keepalive_hook')]
    m['slot_queue_instruction_listing'] = [dict(r,instruction='CALL audio and periodic drive service')
        if r['address'] in sites else r for r in m['slot_queue_instruction_listing']]+rows+extra
    # Reuse the existing read-only keepalive trace events; no debugger patch.
    m['deferred_labels'] = dict(m.get('deferred_labels',{}),
        keepalive_enter=labels['keepalive_enter'],keepalive_return=labels['keepalive_return'])
    m['inplace_keepalive'] = dict(enabled=True, threshold_fields=64, labels=labels,
        wrapper=hook, hook_addresses=sites, previous_hex=before.hex(), hook_hex=after.hex(),
        regions=[dict(address=CODE,code_hex=code.hex()),dict(address=hook,code_hex=wrapper.hex())],
        listing=rows+extra, helper_bytes=len(code), wrapper_bytes=6, extra_state_bytes=0,
        shares_last_service_counter=p['last_read_field'], no_sector_reads=True,
        current_cached_cylinder=True, previous_call_tstates=17, call_tstates=17,
        additional_wrapper_tstates=27, preserves_both_register_sets=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


class Builder(PreviousBuilder):
    def ram(self, start, end, next_sector, remaining):
        sections, m = super().ram(start, end, next_sector, remaining); banks = self.expected_banks
        def bank_at(at): return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at, data):
            if (at&16383)+len(data)>16384: raise ValueError('cross-bank keepalive patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(data)] = data
        install(read8, put, m); result = []
        for section in sections:
            at = section['address']&16383
            raw = bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result, m
