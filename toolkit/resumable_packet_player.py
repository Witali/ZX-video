"""Yield optional video-packet acquisition after a screen publication.

The original queue owns pending byte count, destination and slot position.
Two parser state bytes distinguish length/body continuation and optional
mode. There is no private stack, copied packet or changed compressed data.
Mandatory reads retain the original demand-decode policy. Optional reads
consume available output or run one ordinary producer quantum at a time.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha, padded, sectors
from inplace_keepalive_player import Builder as PreviousBuilder
from pipelined_frame_z80 import helpers, READY
from bulk_frame_z80 import LENGTH

CODE, LIMIT = 0xf900, 0x10000


def build(q, z, sites, *, origin=CODE):
    a = MiniAssembler(origin); rows = []; e, n = helpers(a, rows, 'resumable_packet')
    def load(label): n('LD A,('+str(label)+')', 0x3a, label, 13)
    def store(label): n('LD ('+str(label)+'),A', 0x32, label, 13)
    def jump(op, label): n('JP '+str(label), op, label, 10)
    def call(label): n('CALL '+str(label), 0xcd, label, 17)
    def ret(): e('RET', [0xc9], 10)

    a.label('required'); e('XOR A', [0xaf], 4); store('optional_mode'); jump(0xc3, 'dispatch')
    a.label('optional'); e('LD A,1', [0x3e, 1], 7); store('optional_mode')
    a.label('dispatch'); load('stage'); e('OR A', [0xb7], 4); jump(0xca, 'packet_start')
    e('CP 1', [0xfe, 1], 7); jump(0xca, 'resume_length'); jump(0xc3, 'resume_body')
    a.label('packet_start')
    e('LD A,1', [0x3e, 1], 7); store('stage')
    n('LD DE,length', 0x11, LENGTH, 10); n('LD BC,2', 0x01, 2, 10)
    call(q['take']); jump(0xda, 'paused'); jump(0xc3, sites['validate_length'])
    a.label('resume_length'); call(q['take_next']); jump(0xda, 'paused')
    jump(0xc3, sites['validate_length'])
    a.label('begin_body'); e('LD A,2', [0x3e, 2], 7); store('stage')
    n('LD DE,packet', 0x11, sites['input'], 10)
    n('LD BC,(length)', (0xed, 0x4b), LENGTH, 20)
    call(q['take']); jump(0xda, 'paused'); jump(0xc3, sites['body_done'])
    a.label('resume_body'); call(q['take_next']); jump(0xda, 'paused')
    jump(0xc3, sites['body_done'])
    a.label('complete')
    n('LD (literal_length),HL', 0x22, sites['literal_length'], 16)
    a.label('packet_ready'); e('XOR A', [0xaf], 4); store('stage'); store('optional_mode')
    e('LD A,1', [0x3e, 1], 7); ret()
    a.label('paused'); e('XOR A', [0xaf], 4); ret()

    # The queue's original LD A,(count) is replaced by CALL gate. On yield,
    # discard only that CALL return: RET then returns from take/resume to
    # the parser above. Queue state has already been saved in its own RAM.
    a.label('gate'); load('optional_mode'); e('OR A', [0xb7], 4); jump(0xca, 'gate_continue')
    load(READY); e('OR A', [0xb7], 4); jump(0xc2, 'gate_continue')
    a.label('yield'); e('POP HL (gate return)', [0xe1], 10); e('SCF', [0x37], 4); ret()
    a.label('gate_continue'); load(q['count']); ret()

    a.label('demand_gate'); load('optional_mode'); e('OR A', [0xb7], 4); jump(0xca, q['demand'])
    # count == 0 and phase == 2: read_slot is the active producer slot.
    # Keep history until EOF publishes the completed descriptor, as before.
    n('LD HL,(slice_output)', 0x2a, z['slice_output'], 16)
    n('LD DE,C000', 0x11, 0xc000, 10); e('OR A', [0xb7], 4); e('SBC HL,DE', [0xed, 0x52], 15)
    n('LD DE,(position)', (0xed, 0x5b), q['position'], 20)
    e('OR A', [0xb7], 4); e('SBC HL,DE', [0xed, 0x52], 15)
    e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4); jump(0xc2, q['take_available'])
    call(q['step']); e('OR A', [0xb7], 4); jump(0xca, q['fatal']); jump(0xc3, q['take_next'])
    a.label('stage'); a.emit(0)
    a.label('optional_mode'); a.emit(0)
    a.label('end')
    if a.pc > LIMIT: raise ValueError('resumable packet helper exceeds bank 7')
    return a.resolve(), dict(a.labels), rows


def install(read8, put, m):
    if not (m.get('inplace_keepalive') and m['demand_decode'] and m['resident_audio']['foreground_audio']):
        raise ValueError('requires the retained in-place resident-AY player')
    q, z, p, clock = (m[k] for k in ('queue_labels', 'decoder_labels', 'packet_labels', 'clock_labels'))
    listing = m['slot_queue_instruction_listing']
    # Several historical installers append duplicate rows; use final entries.
    unique = {r['address']: r for r in listing}
    def one(name, lo, hi):
        found = [r for r in unique.values() if r['instruction'] == name and lo <= r['address'] < hi]
        if len(found) != 1: raise ValueError(('unexpected resumable patch site', name, len(found)))
        return found[0]['address']
    body = one('LD DE,packet', p['read_packet'], p['end'])
    done = one('CALL take packet', p['read_packet'], p['end']) + 3
    finish = one('LD (literal_length),HL', p['read_packet'], p['end'])
    optional = one('CALL read next packet', clock['prime'], clock['end'])
    demand = one('JP demand', q['take_next'], q['have_slot'])
    sites = dict(validate_length=p['read_packet']+9, input=read8(body+1)+256*read8(body+2),
                 body_done=done, literal_length=read8(finish+1)+256*read8(finish+2))
    code, labels, rows = build(q, z, sites)
    if any(read8(i) for i in range(CODE, CODE+len(code))):
        raise ValueError('resumable bank-7 space is occupied')
    patches = []
    def patch(at, before, after, new_rows):
        if len(before) != len(after) or bytes(read8(at+i) for i in range(len(before))) != before:
            raise ValueError(('unexpected resumable opcode', hex(at), before.hex()))
        put(at, after)
        patches.append(dict(address=at, before_hex=before.hex(), code_hex=after.hex(),
                            old_listing=[unique[k] for k in sorted(unique) if at <= k < at+len(before)]))
        for pc in list(unique):
            if at <= pc < at+len(before): del unique[pc]
        for offset, name, ticks in new_rows:
            unique[at+offset] = dict(address=at+offset, instruction=name, tstates=ticks, phase='resumable_packet')
    def target(op, address): return bytes([op])+address.to_bytes(2, 'little')
    patch(p['read_packet'], target(0x11, LENGTH), target(0xc3, labels['required']), [(0,'JP required packet',10)])
    patch(body, target(0x11, sites['input']), target(0xc3, labels['begin_body']), [(0,'JP begin body',10)])
    patch(finish, target(0x22, sites['literal_length']), target(0xc3, labels['complete']), [(0,'JP complete packet',10)])
    patch(q['take_next'], target(0x3a, q['count']), target(0xcd, labels['gate']), [(0,'CALL packet yield gate',17)])
    patch(demand, target(0xca, q['demand']), target(0xca, labels['demand_gate']), [(0,'JP Z,optional demand gate',10)])
    patch(optional, target(0xcd, p['read_packet'])+b'\x3e\x01', target(0xcd, labels['optional'])+b'\x00\x00',
          [(0,'CALL optional packet',17),(3,'NOP (retain completion result)',4),(4,'NOP',4)])
    put(CODE, code)
    m['slot_queue_instruction_listing'] = list(unique.values())+rows
    m['resumable_packet'] = dict(enabled=True, labels=labels, sites=sites, listing=rows, patches=patches,
        regions=[dict(address=CODE, code_hex=code.hex())], helper_bytes=len(code), state_bytes=2,
        extra_packet_bytes=0, extra_stack_bytes=2, private_stack=False,
        mandatory_gate_tstates=67, previous_gate_tstates=13, mandatory_gate_delta_tstates=54,
        optional_continue_gate_tstates=94, optional_continue_gate_delta_tstates=81,
        mandatory_demand_gate_extra_tstates=27, stream_unchanged=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    # Trace starts once per new packet, not again when a mandatory call
    # resumes a partially acquired packet. Original callers keep their ABI.
    m['packet_labels'] = dict(p, read_packet=labels['packet_start'], packet_ready=labels['packet_ready'])


class Builder(PreviousBuilder):
    def ram(self, start, end, next_sector, remaining):
        sections, m = super().ram(start, end, next_sector, remaining); banks = self.expected_banks
        def bank_at(at): return 5 if at < 0x8000 else 2 if at < 0xc000 else 7
        def read8(at): return banks[bank_at(at)][at & 16383]
        def put(at, data):
            if (at & 16383)+len(data) > 16384: raise ValueError('cross-bank packet helper')
            banks[bank_at(at)][at & 16383:(at & 16383)+len(data)] = data
        install(read8, put, m); result = []
        for section in sections:
            at = section['address'] & 16383
            # Extend the existing bank-7 section through the new helper.
            # Mask bodies E600..F8FF are still generated after cold loading.
            length = m['resumable_packet']['labels']['end']-section['address'] if section['bank'] == 7 else section['decoded_bytes']
            raw = bytes(banks[section['bank']][at:at+length])
            if sha(raw) == section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            if len(padded(coded)) > (6912 if section['buffer'] == 0x4000 else 4608):
                raise ValueError('resumable bootstrap staging overflow')
            result.append(dict(section, data=padded(coded), decoded_bytes=length,
                               compressed_bytes=len(coded), sectors=sectors(coded), sha256=sha(raw)))
        return result, m
