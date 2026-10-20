"""Independent bounded Z80 timing review; does not edit or run a player."""
import hashlib
import json
from pathlib import Path
import struct

from z80 import Z80Machine

OUT = Path(__file__).resolve().parent
RESEARCH = OUT.parents[1]
AUDIO = RESEARCH.parents[1]


def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    source_paths = ('stream-player.asm', 'direct_player.py', 'ram_cache.py',
                    'ima_codec.py', 'experiments/song-snr/table_pdm_uniform16.py',
                    'experiments/song-snr/table_pdm_uniform16_paged.py')
    sources = {name: dict(bytes=(AUDIO/name).stat().st_size,
                         sha256=sha((AUDIO/name).read_bytes())) for name in source_paths}
    text = (AUDIO/'stream-player.asm').read_text(encoding='utf-8')
    first = text.split('FIRST: MACRO', 1)[1].split('ENDM', 1)[0]
    instructions = ('EXX', 'OR L', 'LD L,A', 'LD SP,HL', 'POP BC', 'POP HL', 'ADD IX,BC', 'EXX')
    lines = [line.strip() for line in first.splitlines()]
    cursor = 0
    for instruction in instructions:
        cursor = lines.index(instruction, cursor)+1
    # Official instruction-table counts, independent of host encoder timings.
    ledger = [dict(instruction=name, tstates=t) for name, t in (
        ('OR L', 4), ('LD L,A', 4), ('LD SP,HL', 6),
        ('POP BC', 10), ('POP HL', 10), ('ADD IX,BC', 15))]
    assert sum(r['tstates'] for r in ledger) == 49
    core = bytes.fromhex('b5 6f f9 c1 e1 dd 09')
    cases = []
    for exchanged in (False, True):
        blob = b'\xd9'+core+b'\xd9' if exchanged else core
        for code in range(16):
            row = 0xA580; delta = code*257-1900; successor = 0xA600+64*(code%4)
            predictor = 32768+code*719
            machine = Z80Machine(); machine.memory[0x8000:0x8000+len(blob)] = blob
            at = row+code*4
            machine.memory[at:at+4] = struct.pack('<HH', delta & 65535, successor)
            machine.a = code*4; machine.hl = 0x9876 if exchanged else row
            machine.alt_hl = row if exchanged else 0x9876
            machine.bc = 0x10FE; machine.alt_bc = 0x2345; machine.ix = predictor
            machine.de = 0xC123; machine.alt_de = 0xD456
            machine.sp = 0x5B00; machine.pc = 0x8000
            machine.iff1 = machine.iff2 = False
            stop = 0x8000+len(blob); machine.set_breakpoint(stop)
            machine.ticks_to_stop = 1000
            while machine.pc != stop:
                event = machine.run()
                assert not event & machine._TICKS_LIMIT_HIT
            actual = 1000-machine.ticks_to_stop
            assert actual == (57 if exchanged else 49)
            assert machine.ix == (predictor+delta) & 65535 and machine.sp == at+4
            if exchanged:
                assert machine.hl == 0x9876 and machine.bc == 0x10FE
                assert machine.alt_hl == successor and machine.alt_bc == delta & 65535
            else:
                assert machine.hl == successor and machine.bc == delta & 65535
            assert machine.de == 0xC123 and machine.alt_de == 0xD456
            cases.append(dict(code=code, surrounding_EXX=exchanged,
                              actual_tstates=actual, exact_register_result=True))
    paged_path = RESEARCH/'evidence/table-pdm-uniform16-paged-component/report.json'
    paged = json.loads(paged_path.read_bytes())
    report = dict(complete=True, date='2026-10-20', source_files=sources,
        timing_source=dict(title='Zilog Z80 CPU User Manual UM008011-0816',
            url='https://www.zilog.com/docs/z80/um0080.pdf',
            printed_pages=dict(LD_register=71, LD_SP_HL=112, POP=119, EXX=126, OR_register=160, ADD_IX=194)),
        live_decoder_core=dict(ledger=ledger, total_tstates=49,
            surrounding_EXX_count=2, with_register_exchange_tstates=57,
            excludes='Speaker OUT instructions, nibble fetch/extraction, PDM lookup/dispatch, page/bank/EOF handling and clone contention'),
        bounded_native_confirmation=dict(cases=cases, actual_machine_cases=len(cases),
            physical_scope='Uncontended native CPU instruction fragment only, no I/O or disk; not a fresh whole-player execution'),
        unchanged_player=dict(instruction_changes=0, core_Tstate_delta=0,
            ordinary_Pentagon_Tstates=449, page_extra_Tstates=14, bank_extra_Pentagon_Tstates=243,
            compressed_disk_format='Headerless low-nibble-first IMA4, preserved',
            decoded_precision='Full16-bit predictor before the existing PDM lookup'),
        rejected_layout_estimate=dict(status='Counted feasibility observation, not implemented',
            current_rows=89, codes_per_row=16, record_bytes=4,
            used_transition_bytes=89*16*4, page_aligned_allocation_bytes=89*256,
            extra_bytes=89*256-89*16*4, hypothetical_core_saving_Tstates=4,
            reason='Page-aligning every row can remove OR L, but costs17088 additional fixed bytes; this exceeds the current fixed-RAM budget and is not a paging-safe integrated solution'),
        existing_uniform_component=dict(report_sha256=sha(paged_path.read_bytes()),
            PCM_sample_Tstates=paged['ordinary_page_bank_source_period_tstates'],
            PDM_hold_Tstates=paged['all_actual_speaker_holds_tstates'],
            fixed_bytes=paged['fixed_allocation_bytes'], includes_live_IMA_decode=False,
            scope='ResidentPCM8 with one static two-bank handoff, not a complete compressed player'),
        decision='Accept host C decoder speed improvement separately. No live Z80 decoder acceleration is claimed or applied; register reassignment or row expansion requires a new integrated CPU/RAM/bank/EOF and exact-OUT-timing proof.',
        no_new_TRD_or_full_player_or_hardware_claim=True)
    save(OUT/'report.json', report)
    files = {p.relative_to(OUT).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
             for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json'}
    save(OUT/'manifest.json', dict(complete=True, artifact_files=files))
    print(json.dumps(dict(complete=True, core_Tstates=49, with_EXX_Tstates=57,
                         fragment_cases=len(cases), player_delta_Tstates=0)))


if __name__ == '__main__': main()
