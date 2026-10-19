"""Test-only Mega offset/register and reuse-tail candidates; no public profile."""
from pathlib import Path

from zx0._z80 import MiniAssembler, sha


def build(*, origin=0x8000, dead_offset_shifts=True, reuse_tail_jp=False,fast_jumps=True):
    """Assemble the pinned Mega resource with explicit local substitutions.

    The four offset-Elias RL B instructions are dead: their consumer writes
    B from C before reading B, and the intervening ADD A,A replaces flags.
    Length/literal/reuse RL B instructions remain necessary word-count code.
    A second independent candidate uses JP for four frequent reuse exits.
    Both variants retain the full resident caller-stack ABI, with no coroutine.
    """
    source = Path(__file__).resolve().parents[1]/'zx0/src/zx0/asm/dzx0_mega.asm'
    a = MiniAssembler(origin)
    simple = {'push hl':(0xe5,), 'pop hl':(0xe1,), 'inc bc':(0x03,),
        'inc c':(0x0c,), 'inc hl':(0x23,), 'ldir':(0xed,0xb0),
        'ldi':(0xed,0xa0), 'add a,a':(0x87,), 'add hl,de':(0x19,),
        'ld b,c':(0x41,), 'ld c,(hl)':(0x4e,), 'ld a,(hl)':(0x7e,),
        'rr b':(0xcb,0x18), 'rr c':(0xcb,0x19), 'rl b':(0xcb,0x10),
        'rl c':(0xcb,0x11), 'ret z':(0xc8,)}
    aliases = {}; last_label = None; removed = []; changed = []
    for original in source.read_text().splitlines():
        line = ' '.join(original.split(';')[0].strip().split()).replace(', ', ',')
        if not line:continue
        if line.endswith(':'):
            last_label = line[:-1]; a.label(last_label);continue
        if line == 'rl b' and dead_offset_shifts and last_label.startswith('dzx0m_elias_offset'):
            removed.append(last_label);continue
        if line in simple:a.emit(*simple[line]);continue
        op, args = line.split(' ',1)
        if op in ('jp','jr'):
            condition, target = args.split(',',1) if ',' in args else ('',args)
            if op == 'jr' and ((fast_jumps and not condition) or (reuse_tail_jp and condition=='nc' and target.startswith('dzx0m_literals'))):
                if condition:changed.append(dict(address=a.pc, target=target))
                op = 'jp'
            forms = {'jp':{'':0xc3,'nc':0xd2,'c':0xda}, 'jr':{'':0x18,'nc':0x30,'c':0x38}}
            (a.abs16 if op=='jp' else a.rel8)(forms[op][condition],target)
        elif op == 'ld':
            dest, value = args.split(',')
            if dest.startswith('('):
                expression=dest[1:-1]; label,offset=expression.split('+')
                aliases[expression]=(label,int(offset));a.abs16((0xed,0x43),expression)
            elif value.startswith('('):
                expression=value[1:-1];label,offset=expression.split('+')
                aliases[expression]=(label,int(offset));a.abs16(0x2a,expression)
            else:
                number=int(value[1:],16) if value.startswith('$') else int(value)
                a.emit({'bc':0x01,'hl':0x21,'c':0x0e}[dest])
                (a.word if dest in ('bc','hl') else a.emit)(number)
        else:raise ValueError(line)
    for alias,(label,offset) in aliases.items():a.labels[alias]=a.labels[label]+offset
    assert a.pc-origin == 673+fast_jumps-8*dead_offset_shifts+4*reuse_tail_jp
    assert len(removed) == 4*dead_offset_shifts and len(changed) == 4*reuse_tail_jp
    blob=a.resolve()
    return [(origin,blob)],a.labels,dict(entry='dzx0_mega',variant='mega-offset-test',
        one_shot=True, code_bytes=len(blob), patched_addresses=[a.labels['dzx0m_last_offset+1']+i for i in (0,1)],
        source_sha256=sha(source.read_bytes()), removed_offset_shifts=removed,
        reuse_exit_changes=changed, coroutine_supported=False, test_only=True)
