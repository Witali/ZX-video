"""Resident ZX0 v2 speed/space frontier with a hard 10,000-byte service cap.

The name identifies the maximum-speed direction of the measured experiment,
not a proof of global optimality. No coroutine, paging or quota is provided.
"""
from pathlib import Path
import re

from ._z80 import MiniAssembler, sha


FAMILIES = ('length', 'literals', 'reuse')
PHASES = (1, 3, 5, 7)


def _after(phase):
    return phase-2 if phase > 1 else 7


def build(*, core=0x8000, core_limit=None, prefix_cap=228, shared_prefixes=False,
          irq_code_bytes=0, irq_stack_bytes=0, service_limit=10000,
          _quota_hook=None, _external_labels=None):
    """Return absolute regions, labels and complete service-memory metadata.

    Call dzx0_mega with HL=complete resident input, DE=nonwrapping output and
    caller SP. AF/BC/DE/HL are clobbered; IX and alternate registers survive.
    Code contains a writable offset operand and is not reentrant. Retain all
    source/history and validate sizes/layout externally. IRQ must preserve live
    registers; include its code and additional stack in the explicit arguments.
    Input/output/history are separate from service RAM. The four-byte decoder
    stack includes the caller return and one live saved source word. There are
    no tables, alignment, extra variables, scratch areas or internal buffers.

    Gamma depth proves count >= K. Copy min(prefix_cap, K-1) bytes with LDI,
    leaving a positive LDIR remainder. This retains forward overlapping-copy
    semantics and avoids a zero-count 65,536-byte LDIR. B stays zero until the
    eighth length data bit; deeper loops retain the required word shifts.
    At cap227/228, word counts >=256 copy 100/101 extra bytes before sharing
    the existing 127-LDI suffix. Source is pushed and offset loaded once.
    shared_prefixes optionally merges all phase/family LDI suffixes, ending
    each chain in a cloned original continuation. The existing tail JP moves
    to the entry; literal4 and large word entries save another 10 T. Original
    small-copy paths stay in place. This layout supports resident calls only.
    """
    if type(shared_prefixes) is not bool:
        raise ValueError('shared-prefixes must be boolean')
    if shared_prefixes and _quota_hook is not None:
        raise ValueError('shared prefixes support resident raw code only')
    if type(prefix_cap) is not int or prefix_cap not in (31, 63, 127, 227, 228):
        raise ValueError('prefix-cap must be one of the measured 31, 63, 127, 227, 228 profiles')
    if (type(core) is not int or (core_limit is not None and type(core_limit) is not int)
            or not 0 <= core < (65536 if core_limit is None else core_limit) <= 65536):
        raise ValueError('invalid code reservation')
    if type(service_limit) is not int or not 0 < service_limit <= 10000:
        raise ValueError('service-limit must be 1..10000 bytes')
    if any(type(value) is not int or value < 0 for value in (irq_code_bytes, irq_stack_bytes)):
        raise ValueError('IRQ service reservations must be nonnegative integer bytes')
    source = Path(__file__).with_name('asm') / 'dzx0_mega.asm'
    original = [' '.join(line.split(';')[0].strip().split()).replace(', ', ',')
                for line in source.read_text().splitlines()]
    original = [line for line in original if line]
    lines = []; prefixes = {}; dead_stages = []; word_joins = []; shared_literals = {}

    def copy(family, phase, lower):
        label = f'max_copy_{family}_{phase}_{lower}'
        prefix = min(prefix_cap, lower-1)
        prefixes[label] = dict(family=family, phase=phase, minimum_count=lower,
                              prefix_bytes=prefix,
                              extra_offset_load_tstates=6 if family == 'reuse' and phase == 7 else 0)
        result = [label+':']
        if family != 'literals':
            result += ['push hl', 'ld hl,(dzx0m_last_offset+1)', 'add hl,de']
        if lower == 128 and prefix_cap > 127:
            result += [f'max_suffix_{family}_{phase}_128:']
        return result + ['ldi']*prefix + [f'jp tail_{family}_{phase}']

    def stage(family, phase, level):
        name = f'max_gamma_{family}_{phase}_{level}'
        result = [name+':', 'add a,a', 'rl c']
        if level >= 8:
            result += ['rl b']
        else:
            dead_stages.append(name)
        if phase == 1:
            result += ['ld a,(hl)', 'inc hl']
        result += ['add a,a']
        q = _after(phase)
        result += [f'jp nc,max_gamma_{family}_{q}_{min(8,level+1)}']
        if level == 8:
            join = f'max_word_join_{family}_{phase}'
            word_joins.append(join)
            if prefix_cap > 127:
                # At this depth BC>=256. Reuse the existing 127-LDI suffix
                # after its match setup, adding only the extra prefix bytes.
                # Save source and load offset exactly once. One JP connects
                # the two prefixes, as in the smaller word-loop join.
                entry=f'max_copy_{family}_{q}_256'
                prefixes[entry]=dict(family=family,phase=q,minimum_count=256,
                    prefix_bytes=prefix_cap,
                    extra_offset_load_tstates=6 if family=='reuse' and q==7 else 0)
                result += [entry+':']
                if family != 'literals':
                    result += ['push hl','ld hl,(dzx0m_last_offset+1)','add hl,de']
                result += ['ldi']*(prefix_cap-127) + [join+':',f'jp max_suffix_{family}_{q}_128']
                if family == 'literals':
                    shared_literals[join]=f'max_copy_{family}_{q}_128'
            else:
                result += [join+':', f'jp max_copy_{family}_{q}_128']
        else:
            result += copy(family, q, 1 << level)
        return result

    counts = {family: 0 for family in FAMILIES}
    active = None; copy_context = None; last_label = None
    for line in original:
        if line.endswith(':'):
            label = line[:-1]; last_label = label
            match = re.fullmatch(r'dzx0m_elias_(length|literals|reuse)([1357])', label)
            if match:
                active = (match[1], int(match[2])); dead_stages.append(label)
            match = re.fullmatch(r'dzx0m_(length|literals|reuse)([1357])', label)
            if match:
                copy_context = (match[1], int(match[2]))
            lines.append(line)
            if _quota_hook is not None and re.fullmatch(r'dzx0m_literals[0246]',label):
                lines.append('@quota '+label)
            continue
        # The ordinary coroutine checks output before preparing a command,
        # never within a proven LDI prefix. New-offset EOF is tested first;
        # literal/reuse gamma preparation can be suspended before reading its
        # count because complete input is resident and only DE is published.
        if _quota_hook is not None:
            if line=='ret z':
                lines += [line,'@quota '+last_label];continue
            if line=='inc c' and re.fullmatch(r'dzx0m_literals[1357]',last_label):
                lines.append('@quota reuse_after_'+last_label)
        # Offset B is overwritten by LD B,C. In first long-count stages B is
        # zero and no bit can reach it yet. Later word loops keep RL B.
        if line == 'rl b' and (active or last_label.startswith('dzx0m_elias_offset')):
            continue
        match = re.fullmatch(r'jp nc,dzx0m_elias_(length|literals|reuse)([1357])', line)
        if active and match:
            family, phase = active; q = _after(phase)
            assert (family, q) == (match[1], int(match[2]))
            lines += [f'jp nc,max_gamma_{family}_{q}_4'] + copy(family, q, 8)
            active = None; continue
        match = re.fullmatch(r'jp c,dzx0m_(length|literals|reuse)([1357])', line)
        if match:
            family, phase = match[1], int(match[2])
            if counts[family] % 3 == 2:
                line = f'jp c,max_copy_{family}_{phase}_4'
            counts[family] += 1
        if line == 'ldir':
            assert copy_context is not None
            lines.append(f'tail_{copy_context[0]}_{copy_context[1]}:')
        # Expanded paths exceed relative reach. Count the changed conditional
        # exit's +3/-2 T explicitly, including its slower individual outcome.
        if line.startswith('jr '):
            line = 'jp ' + line[3:]
        lines.append(line)
    assert all(value == 12 for value in counts.values())
    for family in FAMILIES:
        for phase in PHASES:
            lines += copy(family, phase, 4)
        for level in range(4, 9):
            for phase in PHASES:
                lines += stage(family, phase, level)

    # Assemble locally from the packaged pinned resource. The package never
    # imports the experiment harness or movie/toolkit modules.
    shared_audit = None
    if shared_prefixes:
        from ._shared_prefixes import transform
        lines, shared_audit = transform(lines, prefix_cap=prefix_cap, prefixes=prefixes,
            removed_word_shift_stages=dead_stages, word_copy_joins=word_joins,
            _quota_hook=_quota_hook)
    a = MiniAssembler(core)
    simple = {'push hl': (0xe5,), 'pop hl': (0xe1,), 'inc bc': (0x03,),
              'inc c': (0x0c,), 'inc hl': (0x23,), 'ldir': (0xed, 0xb0),
              'ldi': (0xed, 0xa0), 'add a,a': (0x87,), 'add hl,de': (0x19,),
              'ld b,c': (0x41,), 'ld c,(hl)': (0x4e,), 'ld a,(hl)': (0x7e,),
              'rr b': (0xcb, 0x18), 'rr c': (0xcb, 0x19), 'rl b': (0xcb, 0x10),
              'rl c': (0xcb, 0x11), 'ret z': (0xc8,)}
    aliases = {}
    for line in lines:
        if line.startswith('@quota '):
            _quota_hook(a,line.split(' ',1)[1]);continue
        if line.endswith(':'):
            a.label(line[:-1]); continue
        if line in simple:
            a.emit(*simple[line]); continue
        op, args = line.split(' ', 1)
        if op == 'jp':
            test, target = args.split(',', 1) if ',' in args else ('', args)
            a.abs16({'': 0xc3, 'c': 0xda, 'nc': 0xd2}[test], target)
        elif op == 'ld':
            dest, value = args.split(',')
            if dest.startswith('(') or value.startswith('('):
                expr = (dest if dest.startswith('(') else value)[1:-1]
                name, offset = expr.split('+'); aliases[expr] = (name, int(offset))
                a.abs16((0xed, 0x43) if dest.startswith('(') else 0x2a, expr)
            else:
                value = int(value[1:], 16) if value.startswith('$') else int(value)
                a.emit({'bc': 0x01, 'hl': 0x21, 'c': 0x0e}[dest])
                (a.word if dest in ('bc', 'hl') else a.emit)(value)
        else:
            raise ValueError(f'unsupported pinned Mega instruction: {line}')
    for name, (label, offset) in aliases.items():
        a.labels[name] = a.labels[label] + offset
    code_bytes = a.pc-core
    if a.pc > (65536 if core_limit is None else core_limit):
        raise ValueError('maximum ZX0 exceeds core-limit')
    service = dict(code_and_embedded_variables=code_bytes, extra_variables=0,
                   tables=0, alignment=0, scratch=0, internal_buffers=0,
                   decoder_stack_including_call_return=4,
                   caller_irq_code=irq_code_bytes, caller_irq_extra_stack=irq_stack_bytes)
    service_bytes = sum(service.values())
    if service_bytes > service_limit:
        raise ValueError(f'total service memory {service_bytes} exceeds {service_limit} bytes')
    blob = a.resolve(_external_labels)
    metadata = dict(
        entry='dzx0_mega', variant='maximum-block', one_shot=True,
        code_bytes=code_bytes, core_end=a.pc, state_bytes=0, private_stack_bytes=0,
        workspace_bytes=code_bytes+4, service_memory=service,
        service_memory_bytes=service_bytes, service_limit_bytes=service_limit,
        input_output_history_counted_separately=True, max_decoder_stack_bytes=4,
        stack_count_includes_caller_return=True, embedded_offset_variable_bytes=2,
        patched_addresses=[a.labels['dzx0m_last_offset+1']+i for i in (0, 1)],
        source_commit='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
        source_sha256=sha(source.read_bytes()), code_sha256=sha(blob), prefix_cap=prefix_cap,
        prefixes=prefixes, removed_word_shift_stages=dead_stages,
        word_copy_joins=word_joins, shared_literal_suffixes=shared_literals,
        coroutine_supported=False,
        measured_frontier=True, globally_optimal=False)
    if shared_prefixes:
        metadata.update(shared_prefixes=True, shared_prefix_audit=shared_audit,
            prefixes=dict(prefixes, **shared_audit['clone_prefixes']),
            removed_word_shift_stages=dead_stages+shared_audit['clone_removed_word_shift_stages'],
            word_copy_joins=[], shared_literal_suffixes={},
            shared_timing_formula=shared_audit['expected_delta_tstates'])
    return [(core, blob)], a.labels, metadata
