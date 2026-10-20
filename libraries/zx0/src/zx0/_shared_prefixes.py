"""Share resident Maximum LDI suffixes without adding executed instructions.

Move each existing prefix-tail JP to the prefix entry, and let the shared
LDI chain fall into a remapped clone of its original LDIR continuation.
Clones stop at existing unconditional JPs; original small-copy fallthroughs
remain in place. Direct literal >=4 entries and word prefixes above 127 each
remove one 10-T JP. The returned audit describes the clones, label remapping,
and exact dynamic delta against the same-cap unshared resident decoder.

Input lines are normalized instructions/labels from maximum.build before
assembly. This transform supports resident raw decoding only: quota markers
or a quota hook are rejected. It adds code only, with no variables, tables,
alignment, scratch storage, stack depth, or internal buffers.
"""
import re


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
