"""Export generated absolute Z80 regions as a standalone assembly include."""
import json
from pathlib import Path
from ._z80 import sha


ROUTINES = {
    'begin': 'Start a new block after configuring input_pointer, block_end and slice_target.',
    'slice_begin': 'Switch to the private stack and start decoding the current block.',
    'slice_until': 'Resume until the output target; token boundaries can overshoot it.',
    'slice_resume': 'Restore the suspended decoder stack and live working registers.',
    'slice_yield': 'Save the continuation and restore the caller stack before returning.',
    'finish': 'Verify exact output end, set finished and restore the caller stack.',
    'sync': 'Patch output comparison operands; final targets still require reading raw EOD.',
    'start': 'Initialize the AF\' nibble reservoir and enter the raw LZSA2 decoder.',
    'ReadToken': 'Check output demand at a token boundary, allowing bounded overshoot.',
    'Token': 'S/P flag dispatch for literal classes; AF\' retains a cached low nibble.',
    'CopyMatch': 'A=length low byte, B=high; build BC, save input HL and copy forward from the patched negative offset, preserving overlap.',
    'ExtendedCode': 'Shared Small length helper: C=base; consume nibble/extra/word fields, including legal short word escapes.',
    'ExtraByte': 'Shared Small byte extension; carry+Z is EOF. Drop only the helper return and return to the caller before any word/nibble read.',
    'WordLength': 'Read the exact little-endian length into A/B; the encoding implies no lower bound beyond the valid format count.',
    'ReadNibble': 'Small cache in AF\': S=0 refills, S=1 returns cached low nibble. IRQ must preserve the complete alternate AF.',
    'guard_header': 'Require a 32-byte token prefix; direct mode uses dead AF for a 46-T ready path.',
    'guard_literals': 'Require the literal extent plus seven-byte lookahead before LDIR.',
    'input_wait': 'Set input_needed and yield; supplied pages and shared tails belong to the caller.',
    'LongLiterals8Jump': 'Nearby JR target for byte-form literals; word forms retain the original 7-T untaken JR.',
    'LongLiterals8': 'A=18..255 literal bytes, B=token; prepare BC and retain the token in A.',
    'LongLiteralsBC': 'BC=18..255, HL=readable literals, DE=output; 16 forward LDIs then nonzero LDIR. AF\' is preserved.',
    'LongMatch8': 'A=24..255 match bytes, B=0; prepare BC for the long match kernel.',
    'LongMatchBC': 'BC=24..255, HL=input, DE=output; save HL, load shared negative offset, copy forward for distance-1 overlap.',
    'state': 'Mutable words/flags. Keep state and self-modifying operands in writable RAM.',
}


def export(directory, regions, labels, metadata, *, namespace='lzsa2'):
    """Write decoder.asm, metadata.json, license and one binary per region.

    The include uses ORG/DB and namespaced EQU labels, so it needs no Python
    at application build time. Assemble at the recorded addresses; regenerate
    when relocating. It contains bytes of the adapted decoder, not upstream
    assembly accidentally bypassing the coroutine/streaming improvements.
    """
    if not namespace.isidentifier() or not namespace.isascii():
        raise ValueError('namespace must be an ASCII identifier')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lines = ['; Generated adapted raw LZSA2 decoder. See LICENSE; Emmanuel Marty, spke, uniabis.',
             '; Code and patched operands require writable RAM. Counts exclude IRQ/ULA/disk.',
             '; Preserve decoder registers in IRQ handlers, including AF/AF\' when used.',
             '; Coroutine targets are minimums; retain source and complete output history.',
             '; Configure input_pointer/block_end/slice_target before begin; private SP is saved.', '']
    routines=dict(ROUTINES)
    if metadata.get('one_shot'):
        lines=['; Generated resident raw LZSA2 block decoder; see LICENSE; Emmanuel Marty, spke, uniabis.',
               '; ABI: HL=input, DE=output; AF/AF\'/BC/DE/HL clobbered; uses caller stack.',
               '; Complete valid block/history and nonwrapping output required; no quotas/paging/yields.',
               '; Offset operand needs writable non-reentrant code; IRQ preserves all live registers, including AF\'.',
               '; Exact EOD returns before dummy word reads. Counts exclude IRQ/ULA/disk.', '']
        routines['ReadToken']='Enter the next resident token directly; AF\' nibble survives, no quota/frontier check.'
    if metadata.get('fast_jumps'):
        lines += ['; Optional core unconditional JR -> JP: 12 -> 10 T per execution, +1 byte/site.',
                  '; Conditional branches and cold input-wait retries keep their original encoding.',
                  '; Register/flag ownership and the caller ABI are unchanged.', '']
    if metadata.get('branch_tuned'):
        lines += ['; Optional measured conditional branches: JR 7/12 T versus JP 10 T.',
                  '; Conditions/flags are unchanged; some synthetic cases are slower.', '']
    if metadata.get('compact_sync'):
        lines += ['; Optional compact sync: BC is scratch before the saved decoder frame is restored.',
                  '; Patch quotas from BC; ordinary input also returns the original target in DE.',
                  f'; Compared with the selected prior wrapper: {metadata["compact_sync_code_delta"]} bytes, '
                  f'{metadata["begin_delta_tstates"]} T/begin, {metadata["resume_delta_tstates"]} T/resume.', '']
    if metadata.get('nibble_prefill'):
        lines += ['; Optional pre-normalized AF\' low-nibble cache: refill 62 -> 65 T, cached 23 -> 16 T.',
                  '; Carry phase is unchanged. Unpaired refill +3 T; complete pair -4 T, +4 code bytes.', '']

    if metadata.get('full_token_dispatch'):
        lines += ['; Wide raw profile: 256 token handlers; 512-byte low/high target table.',
                  '; EXX lends HL\' for lookup; every handler restores main registers before data access.',
                  '; IRQ must preserve both main and alternate register sets while dispatch is live.',
                  '; Raw entry/EOF retain caller HL\'; six stack bytes include the caller return word.',
                  '; Code + tables + alignment + six stack bytes stay within 10000 bytes.',
                  '; Compressed source and complete output/history are separate caller buffers.',
                  '; Add actual hardware-return/IRQ-handler stack headroom separately.',
                  '; Fixed one/two literal LDIs may wrap BC before a new-offset parser replaces B/C.',
                  '; Repeat-offset tokens retain B=0; short escaped word lengths use bounded LDIR.', '']
        routines.update({
            'dispatch_low':'256 immutable low bytes of token targets; indexed by the complete token.',
            'dispatch_high':'256 immutable high bytes, exactly one page above dispatch_low.',
            'start':'Save caller HL\' once, initialize B=0 and the AF\' nibble phase, enter token lookup.',
            'ReadToken':'58-T token lookup/restoration; main HL=input remains intact while HL\' is scratch.',
            'MatchUseC':'BC=count, HL=input, DE=output; save input HL and copy from patched offset with forward overlap.',
            'LongerMatch':'Parse nibble/byte/word length, returning at exact EOF before dummy word reads.',
            'LongLiterals':'Parse LL=3 literal length; keep legal one/two-byte word escapes on LDIR.',
            'done':'Restore caller HL\' and return with exact input/output cursors and caller SP.',
        })
    for name, address in sorted(labels.items()):
        if name.isidentifier():
            lines.append(f'{namespace}_{name} equ ${address:04x}')
    for index, (address, blob) in enumerate(regions):
        lines += ['', f'org ${address:04x}', f'; Region {index}: {len(blob)} bytes.']
        points = {address, address + len(blob)}
        for name, target in labels.items():
            if name in routines and address <= target < address + len(blob):
                points.add(target)
        ordered = sorted(points)
        for lo, hi in zip(ordered, ordered[1:]):
            for name, target in labels.items():
                if target == lo and name in routines:
                    lines.append(f'; {namespace}_{name}: {routines[name]}')
            for offset in range(lo - address, hi - address, 16):
                part = blob[offset:min(offset + 16, hi - address)]
                lines.append('db ' + ','.join(f'${value:02x}' for value in part))
        (directory / f'region-{index}-{address:04x}.bin').write_bytes(blob)
    (directory / 'decoder.asm').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    report = dict(metadata, labels=labels,
                  regions=[dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in regions])
    (directory / 'metadata.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (directory / 'LICENSE').write_bytes(Path(__file__).with_name('LICENSE').read_bytes())
    return report
