"""Fuse pinned chips microsteps into straight-line instruction slices.

Adapted locally from z80-tester d45d8889 (see vendor provenance).
No external project checkout is required.

No second instruction implementation: every operation and transition comes
from the verified, unmodified vendor header. Only dispatch/bus plumbing changes.
"""
import argparse
import hashlib
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = (Path(__file__).resolve().parents[1] / 'vendor/z80_tester/z80.h').read_text(encoding='utf-8')
assert hashlib.sha256(source.encode()).hexdigest() == '6ca70ffd91b1bdbaf00f7a41e7092b326145fd1c95dcdd7bb01183370de734f3'
macros = source.split('// pin helper macros\n', 1)[1].split('uint64_t z80_tick(', 1)[0]
decoder = source.split('switch (cpu->step) {\n        // <% decoder\n', 1)[1].split('        default: _Z80_UNREACHABLE;', 1)[0]
cases = list(re.finditer(r'^\s*case\s+(\w+):', decoder, re.M))
assert len(cases) == 1709
defines = dict(re.findall(r'^#define (Z80_\w+) (\d+)$', source, re.M))
case_names = {case[1] for case in cases}
repeat_steps = {'1515': 'LDIR', '1528': 'CPIR', '1541': 'INIR', '1554': 'OTIR',
                '1567': 'LDDR', '1580': 'CPDR', '1593': 'INDR', '1606': 'OTDR'}
seen_repeats = set()

out = ['/* ALTERED GENERATED SOURCE: derived from pinned floooh/chips z80.h by\n * z80-tester generate_fast_decoder.py; flat RAM reads use codec_flat_read.\n * Copyright (c) 2021 Andre Weissflog; zlib/libpng license, see LICENSE.\n * This is not an unmodified upstream header. */', macros, r'''
#undef _mread
#undef _mwrite
#undef _ioread
#undef _iowrite
#undef _wait
#undef _fetch
#define _mread(ab) do { _sax(ab,Z80_MREQ|Z80_RD); Z80_SET_DATA(pins,codec_flat_read(b,Z80_GET_ADDR(pins))); } while(0)
#define _mwrite(ab,d) do { _sadx(ab,d,Z80_MREQ|Z80_WR); ++b->writes; BOARD_MEMORY_WRITE(b,Z80_GET_ADDR(pins),Z80_GET_DATA(pins)); } while(0)
#define _ioread(ab) do { _sax(ab,Z80_IORQ|Z80_RD); Z80_SET_DATA(pins,BOARD_INPUT(b,pins)); } while(0)
#define _iowrite(ab,d) do { _sadx(ab,d,Z80_IORQ|Z80_WR); board_emit(b,b->ticks+elapsed,Z80_GET_ADDR(pins),Z80_GET_DATA(pins)); } while(0)
#define _wait() ((void)0)

/* Run through one fetch boundary without dispatching every individual T.
 * The caller reserves 32 T and excludes pending/active interrupt sequences.
 * Exact partial runs and asynchronous INT/NMI retain the original tick path. */
static uint32_t board_fast_slice(board *b) {
    z80_t *cpu = &b->cpu;
    uint64_t pins = b->pins;
    uint32_t elapsed = 0;
fast_dispatch:
    switch (cpu->step) {''']
for case in cases:
    name = case[1]
    out.append(f'        case {name}: goto fast_{name};')
out += ['        default: _Z80_UNREACHABLE;', '    }']

def transition(match):
    target = match[1]
    if re.fullmatch(r'[0-9+ ]+', target):
        target = str(sum(map(int, target.split('+'))))
    if target not in case_names and target in defines:
        target = defines[target]
    if re.fullmatch(r'\w+', target):
        return f'goto fast_{target}'
    return f'{{ cpu->step={target}; goto fast_dispatch; }}'

for i, case in enumerate(cases):
    name = case[1]
    body = decoder[case.end():cases[i+1].start() if i+1 < len(cases) else len(decoder)]
    if name in repeat_steps:
        assert f'// {repeat_steps[name]} (8)' in body
        rewind = 'cpu->wz=--cpu->pc;--cpu->pc;'
        assert body.count(rewind) == 1
        io = 'true' if repeat_steps[name] in ('INIR', 'OTIR', 'INDR', 'OTDR') else 'false'
        body = body.replace(rewind, rewind + f'board_repeat_flags(cpu,{io});')
        seen_repeats.add(name)
    # Numeric transitions include conditional paths such as _goto(544+5).
    # The four computed transitions dispatch once at an opcode/prefix boundary.
    body = re.sub(r'_goto\(([^;]+)\)', transition, body)
    body = body.replace('_fetch();', f'pins=_z80_fetch(cpu,pins); goto finish_{name};')
    body = body.replace('goto step_to;', f'goto finish_{name};')
    if name in ('55', '63'):
        helper = '_z80_scf(cpu)' if name == '55' else '_z80_ccf(cpu)'
        body = body.replace(helper+';', '{ const uint8_t xy=((b->q^cpu->f)|cpu->a)&(Z80_YF|Z80_XF); '+helper+'; cpu->f=(cpu->f&~(Z80_YF|Z80_XF))|xy; }')
    if name == '1392':
        body = body.replace('_iowrite(cpu->bc,0)', '_iowrite(cpu->bc,b->model ? 255 : 0)')
    out.append(f'fast_{name}:\n    ++elapsed; pins &= ~(Z80_CTRL_PIN_MASK|Z80_RETI);\n    {body.strip()}')
    if f'finish_{name}' in body:
        out.append(f'finish_{name}:\n    board_finish_slice(b,pins,elapsed,{name}); return elapsed;')
out += ['}', '\n']
assert seen_repeats == set(repeat_steps)
for name in re.findall(r'^#define\s+(\w+)', macros, re.M):
    out.append(f'#undef {name}')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text('\n'.join(out)+'\n', encoding='utf-8', newline='\n')
