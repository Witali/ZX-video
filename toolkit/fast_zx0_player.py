"""Install adapted Fast into the complete-input, periodic-drive player.

The compressed stream and queue scheduling are unchanged. Patch only known
instruction operands; verify the retained producer against a fresh assembly.
"""
from copy import deepcopy

from build_fap3_trd import sha, padded, sectors
from inplace_keepalive_player import Builder as PreviousBuilder
import bank2_zx0
import faster_zx0
import inplace_slot_input_z80 as producer


def install(read8, put, m):
    if (not m.get('inplace_keepalive', {}).get('enabled')
            or not m['resident_audio']['foreground_audio'] or m.get('streaming_input')
            or m.get('fast_zx0')):
        raise ValueError('requires the unmodified complete-input keepalive player')
    placement=m['bank2_zx0'];origin,limit=placement['new_origin'],placement['new_end']
    old_regions, old, _ = bank2_zx0.build(origin=origin,limit=limit)
    if old != m['decoder_labels']:
        raise ValueError('unsupported decoder layout')
    for at, data in old_regions:
        expected = data.replace(b'\x11\x00\xe0', b'\x11\x00\xc0')
        if bytes(read8(at+i) for i in range(len(data))) != expected:
            raise ValueError(('retained decoder differs', hex(at)))
    regions, z, layout = faster_zx0.build('fast',core=origin,core_limit=limit)
    prefix_end = old_regions[0][0]+len(old_regions[0][1])
    if any(read8(at) for at in range(prefix_end, layout['prefix_end'])):
        raise ValueError('Fast helper region is occupied')
    if read8(limit) != 0xc9:
        raise ValueError('preserved frame return differs')
    names = ('begin', 'slice_until', 'fatal', 'slice_output', 'slice_target',
             'slice_caller_sp', 'slice_decoder_sp', 'block_length', 'block_end',
             'block_stored', 'input_pointer')
    remap = {old[k]: z[k] for k in names}
    external = []
    rows = {r['address']: r for r in m['slot_queue_instruction_listing']}
    for pc, row in sorted(rows.items()):
        if any(at <= pc < at+len(data) for at, data in old_regions):
            continue
        op, name, offset = read8(pc), row['instruction'], None
        if name.startswith('LD '):
            if op in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2a, 0x32, 0x3a): offset = 1
            if op in (0xdd, 0xfd) and read8(pc+1) in (0x21, 0x22, 0x2a): offset = 2
            if op == 0xed and read8(pc+1) in (0x43, 0x4b, 0x53, 0x5b, 0x63, 0x6b, 0x73, 0x7b): offset = 2
        if name.startswith(('CALL ', 'JP ')) and op in (
                0xc3, 0xc2, 0xca, 0xd2, 0xda, 0xe2, 0xea, 0xf2, 0xfa,
                0xcd, 0xc4, 0xcc, 0xd4, 0xdc, 0xe4, 0xec, 0xf4, 0xfc): offset = 1
        if offset is None: continue
        before = read8(pc+offset)+256*read8(pc+offset+1)
        if any(at <= before < at+len(data) for at, data in old_regions) and before not in remap:
            raise ValueError(('unrecognized decoder reference', hex(pc), hex(before)))
        after = remap.get(before, before)
        if before == after: continue
        put(pc+offset, after.to_bytes(2, 'little'))
        external.append(dict(address=pc, operand_address=pc+offset, instruction=name,
            old=before, new=after, previous_tstates=row['tstates'], tstates=row['tstates'], delta_tstates=0))
    if not any(v['old'] == old['begin'] for v in external):
        raise ValueError('decoder entry not remapped')
    # Independently assembled producer must match every patched instruction.
    pregions, p, prows = producer.build(z, m['disk_labels'], elapsed_fields=m['player_labels']['elapsed_fields'])
    if p != m['producer_labels']: raise ValueError('producer state moved')
    for at, data in pregions:
        if bytes(read8(at+i) for i in range(len(data))) != data:
            raise ValueError(('producer references incomplete', hex(at)))
    for at, data in old_regions: put(at, bytes(len(data)))
    for at, data in regions: put(at, data)
    # The cold bootstrap restores the low queue bridge from this overlay.
    put(0xa200, bytes(read8(at) for at in range(0x6100, 0x6200)))
    m['pre_fast_bank2_zx0'] = deepcopy(m['bank2_zx0'])
    m['bank2_zx0'] = dict(layout, enabled=True, kind='adapted-fast', code_bytes=layout['code_and_state_bytes'])
    m['decoder_labels'] = z
    m['decoder_end'] = layout['core_end']
    m['player_labels']['zx0_fatal'] = z['fatal']
    m['inplace_video']['producer_listing'] = prows
    m['inplace_video']['regions'] = [dict(address=at, code_hex=data.hex()) for at, data in pregions]
    m['fast_zx0'] = dict(enabled=True, layout=layout, external_operands=external,
        previous_decoder_labels=old, regions=layout['regions'],
        previous_decoder_bytes=314, decoder_bytes=layout['code_and_state_bytes'],
        extra_stream_bytes=0, extra_buffer_bytes=0, queue_schedule_unchanged=True,
        producer_reassembled_exact=True, cold_bridge_overlay_updated=True,
        cpu_reference='faster_zx0_cpu.json', timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


class Builder(PreviousBuilder):
    def ram(self, start, end, next_sector, remaining):
        sections, m = super().ram(start, end, next_sector, remaining)
        banks = self.expected_banks
        def bank_at(at): return 5 if at < 0x8000 else 2 if at < 0xc000 else 7
        def read8(at): return banks[bank_at(at)][at & 16383]
        def put(at, data):
            if (at & 16383)+len(data) > 16384: raise ValueError('cross-bank Fast patch')
            banks[bank_at(at)][at & 16383:(at & 16383)+len(data)] = data
        install(read8, put, m)
        result = []
        for section in sections:
            at = section['address'] & 16383
            raw = bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw) == section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            result.append(dict(section, data=padded(coded), compressed_bytes=len(coded), sectors=sectors(coded), sha256=sha(raw)))
        return result, m
