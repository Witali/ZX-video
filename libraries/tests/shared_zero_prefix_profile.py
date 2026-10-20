"""Test-only Maximum suffix sharing with no added executed instructions.

Each former inline LDI prefix keeps its existing 10-T JP, moved from the
prefix's end to its beginning. The shared descending LDI chain falls into a
clone of the original LDIR continuation. A clone stops at an existing
unconditional JP; it never adds a return jump. Original small-copy tails stay
in place. Four literal >=4 entries can jump directly into their shared suffix,
and word prefixes above 127 lose their intermediate suffix JP: each saves 10 T.

This is a raw resident experiment. No coroutine/quota semantics are claimed.
The pure transform is intentionally separable from the AST capture/assembler
used by this test module; a public integration can call it before assembly.
"""
import ast
import inspect
import re

import zx0.maximum as maximum
from zx0._z80 import MiniAssembler, sha


FAMILIES = ('length', 'literals', 'reuse')
PHASES = (1, 3, 5, 7)


def _unconditional(line):
    return line.startswith('jp ') and ',' not in line


def transform(lines, *, prefix_cap, prefixes, removed_word_shift_stages=(),
              word_copy_joins=(), _quota_hook=None):
    """Return transformed normalized assembly lines and an explicit audit.

    Inputs are the resident Maximum generator's lines/metadata before assembly.
    Every label defined in a continuation clone is remapped, including embedded
    next-command copy entries. Offset-operand references remain external, so
    the decoder still owns exactly one mutable two-byte offset operand.
    """
    if _quota_hook is not None or any(line.startswith('@quota ') for line in lines):
        raise ValueError('zero-penalty shared prefixes support resident raw code only')
    if prefix_cap not in (31, 63, 127, 227, 228):
        raise ValueError('unsupported Maximum prefix cap')
    original = list(lines)
    starts = {line[:-1]: i for i, line in enumerate(original) if line.endswith(':')}
    if len(starts) != sum(line.endswith(':') for line in original):
        raise ValueError('duplicate source labels')
    aliases = {f'max_copy_literals_{phase}_4':
               f'shared_zero_literals_{phase}_3' for phase in PHASES}
    replacements = {}
    retained_joins = set()
    for entry, details in prefixes.items():
        start = starts[entry]
        end = next(i for i in range(start, len(original)) if _unconditional(original[i]))
        block = original[start:end+1]
        family, phase, count = details['family'], details['phase'], details['prefix_bytes']
        if family not in FAMILIES or phase not in PHASES:
            raise ValueError(f'unexpected prefix {entry}')
        expected = count-127 if details['minimum_count'] == 256 else count
        if block.count('ldi') != expected:
            raise ValueError(f'unexpected inline prefix body at {entry}')
        if entry in aliases:
            if block != [entry+':', 'ldi', 'ldi', 'ldi', f'jp tail_literals_{phase}']:
                raise ValueError(f'literal direct alias is not isolated: {entry}')
            replacements[start] = (end, [])
        else:
            # Retain match setup and every original audit label, including a
            # word-join label. Only its LDIs and terminal JP move to the chain.
            setup = [line for line in block[:-1] if line != 'ldi']
            retained_joins.update(line[:-1] for line in setup
                                  if line.endswith(':') and line[:-1] in word_copy_joins)
            replacements[start] = (end, setup + [f'jp shared_zero_{family}_{phase}_{count}'])
    rewritten = []
    i = 0
    while i < len(original):
        if i in replacements:
            end, block = replacements[i]
            rewritten.extend(block)
            i = end+1
        else:
            rewritten.append(original[i])
            i += 1
    positions = {line[:-1]: i for i, line in enumerate(rewritten) if line.endswith(':')}

    def through_jump(label):
        first = positions[label]
        last = next(j for j in range(first, len(rewritten)) if _unconditional(rewritten[j]))
        return rewritten[first:last+1]

    clone_audit = []
    clone_prefixes = {}
    clone_dead = []
    shared_entries = {}
    appended = []
    for family in FAMILIES:
        for phase in PHASES:
            tail = f'tail_{family}_{phase}'
            inversion = None
            if family == 'reuse' and phase != 7:
                # Reuse's ordinary fallthrough enters the long new-offset
                # parser. Invert its existing 10-T JP and instead fall into a
                # clone of the literal header, ending at that header's existing
                # prefix-entry JP. Both C outcomes retain precisely one JP.
                start = positions[tail]
                branch = f'jp nc,dzx0m_literals{phase-1}'
                end = rewritten.index(branch, start)
                first = rewritten[start:end+1]
                first[-1] = f'jp c,dzx0m_new_offset{phase-1}'
                second = through_jump(f'dzx0m_literals{phase-1}')
                segment = first+second
                inversion = dict(before=branch, after=first[-1])
                source_spans = [dict(start=tail, end=branch),
                                dict(start=f'dzx0m_literals{phase-1}', end=second[-1])]
            else:
                # Reuse7 already has an unconditional JP after its conditional
                # branch. Keep it: eliminating it would be a separate change.
                segment = through_jump(tail)
                source_spans = [dict(start=tail, end=segment[-1])]
            if not _unconditional(segment[-1]):
                raise ValueError(f'clone has no existing terminal JP: {family}/{phase}')
            mapping = {line[:-1]: f'shared_zero_clone_{family}_{phase}_{line[:-1]}'
                       for line in segment if line.endswith(':')}
            token = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
            cloned = [token.sub(lambda match: mapping.get(match[0], match[0]), line)
                      for line in segment]
            for old, new in mapping.items():
                if old in prefixes:
                    clone_prefixes[new] = dict(prefixes[old], cloned_from=old)
                if old in removed_word_shift_stages:
                    clone_dead.append(new)
            counts = sorted({value['prefix_bytes'] for value in prefixes.values()
                             if value['family'] == family and value['phase'] == phase}, reverse=True)
            for index, count in enumerate(counts):
                label = f'shared_zero_{family}_{phase}_{count}'
                appended.append(label+':')
                if family == 'literals' and count == 3:
                    appended.append(f'max_copy_literals_{phase}_4:')
                shared_entries[label] = dict(family=family, phase=phase, prefix_bytes=count)
                next_count = counts[index+1] if index+1 < len(counts) else 0
                appended.extend(['ldi']*(count-next_count))
            appended.extend(cloned)
            clone_audit.append(dict(family=family, phase=phase,
                                    source_spans=source_spans, label_map=mapping,
                                    entry=mapping[tail], terminal_jump=cloned[-1],
                                    conditional_inversion=inversion))
    audit = dict(
        strategy='shared descending LDI chains fall into remapped original continuations',
        continuation_clones=clone_audit, clone_prefixes=clone_prefixes,
        clone_removed_word_shift_stages=clone_dead, shared_suffix_entries=shared_entries,
        literal_direct_aliases=aliases,
        eliminated_word_join_labels=list(word_copy_joins) if prefix_cap > 127 else [],
        retained_word_join_labels=sorted(retained_joins),
        expected_delta_tstates='-10 * baseline literal_direct_aliases hits'
            ' - 10 * baseline eliminated_word_join_labels hits',
        eliminated_jump_tstates=10, added_runtime_jump_tstates=0,
        literal_alias_candidate_hits_include_larger_suffix_fallthroughs=True,
        coroutine_supported=False)
    return rewritten+appended, audit


def _capture(*, origin, prefix_cap):
    """Run the public source generator only, without modifying its module."""
    source = inspect.getsource(maximum.build)
    tree = ast.parse(source)
    function = tree.body[0]
    cut = next(i for i, statement in enumerate(function.body)
               if isinstance(statement, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'a'
                       for target in statement.targets)
               and isinstance(statement.value, ast.Call)
               and isinstance(statement.value.func, ast.Name)
               and statement.value.func.id == 'MiniAssembler')
    function.body = function.body[:cut]+[ast.Return(ast.Call(ast.Name('locals', ast.Load()), [], []))]
    ast.fix_missing_locations(tree)
    namespace = dict(vars(maximum))
    exec(compile(tree, '<resident Maximum generator capture>', 'exec'), namespace)
    captured = namespace['build'](core=origin, prefix_cap=prefix_cap)
    captured['generator_source_sha256'] = sha(source.encode())
    return captured


def build(*, origin=0x8000, prefix_cap=127, allow_oversize=False, _quota_hook=None):
    """Return an independent resident-only native-test profile.

    HL=input, DE=output; AF/BC/DE/HL clobbered, IX/alternates preserved. The
    caller return plus live match-source word require at most four stack bytes.
    Code includes the only mutable offset word; no other service RAM is added.
    """
    if _quota_hook is not None:
        raise ValueError('zero-penalty shared prefixes do not support quota hooks')
    captured = _capture(origin=origin, prefix_cap=prefix_cap)
    lines, audit = transform(captured['lines'], prefix_cap=prefix_cap,
                             prefixes=captured['prefixes'],
                             removed_word_shift_stages=captured['dead_stages'],
                             word_copy_joins=captured['word_joins'])
    a = MiniAssembler(origin)
    simple = {'push hl': (0xe5,), 'pop hl': (0xe1,), 'inc bc': (0x03,),
              'inc c': (0x0c,), 'inc hl': (0x23,), 'ldir': (0xed, 0xb0),
              'ldi': (0xed, 0xa0), 'add a,a': (0x87,), 'add hl,de': (0x19,),
              'ld b,c': (0x41,), 'ld c,(hl)': (0x4e,), 'ld a,(hl)': (0x7e,),
              'rr b': (0xcb, 0x18), 'rr c': (0xcb, 0x19), 'rl b': (0xcb, 0x10),
              'rl c': (0xcb, 0x11), 'ret z': (0xc8,)}
    aliases = {}
    for line in lines:
        if line.endswith(':'):
            a.label(line[:-1])
        elif line in simple:
            a.emit(*simple[line])
        else:
            op, args = line.split(' ', 1)
            if op == 'jp':
                test, target = args.split(',', 1) if ',' in args else ('', args)
                a.abs16({'': 0xc3, 'c': 0xda, 'nc': 0xd2}[test], target)
            elif op == 'ld':
                dest, value = args.split(',')
                if dest.startswith('(') or value.startswith('('):
                    expr = (dest if dest.startswith('(') else value)[1:-1]
                    name, offset = expr.split('+')
                    aliases[expr] = (name, int(offset))
                    a.abs16((0xed, 0x43) if dest.startswith('(') else 0x2a, expr)
                else:
                    value = int(value[1:], 16) if value.startswith('$') else int(value)
                    a.emit({'bc': 0x01, 'hl': 0x21, 'c': 0x0e}[dest])
                    (a.word if dest in ('bc', 'hl') else a.emit)(value)
            else:
                raise ValueError(f'unsupported pinned instruction: {line}')
    for name, (label, offset) in aliases.items():
        a.labels[name] = a.labels[label]+offset
    blob = a.resolve()
    service_bytes = len(blob)+4
    if a.pc > 65536:
        raise ValueError('shared suffix code crosses FFFFh')
    if not allow_oversize and service_bytes > 10000:
        raise ValueError(f'total service memory {service_bytes} exceeds 10000 bytes')
    prefixes = dict(captured['prefixes'])
    prefixes.update(audit['clone_prefixes'])
    service = dict(code_and_embedded_variables=len(blob), extra_variables=0,
                   tables=0, alignment=0, scratch=0, internal_buffers=0,
                   decoder_stack_including_call_return=4)
    metadata = dict(
        entry='dzx0_mega', variant='maximum-zero-penalty-shared-test', test_only=True,
        one_shot=True, code_bytes=len(blob), core_end=a.pc, state_bytes=0,
        private_stack_bytes=0, workspace_bytes=service_bytes,
        service_memory=service, service_memory_bytes=service_bytes,
        input_output_history_counted_separately=True, max_decoder_stack_bytes=4,
        stack_count_includes_caller_return=True, embedded_offset_variable_bytes=2,
        patched_addresses=[a.labels['dzx0m_last_offset+1']+i for i in (0, 1)],
        source_sha256=sha(captured['source'].read_bytes()),
        generator_source_sha256=captured['generator_source_sha256'],
        code_sha256=sha(blob), prefix_cap=prefix_cap, prefixes=prefixes,
        removed_word_shift_stages=captured['dead_stages']+audit['clone_removed_word_shift_stages'],
        word_copy_joins=captured['word_joins'], shared_literal_suffixes={},
        coroutine_supported=False, globally_optimal=False,
        shared_zero_audit=audit)
    return [(origin, blob)], a.labels, metadata
