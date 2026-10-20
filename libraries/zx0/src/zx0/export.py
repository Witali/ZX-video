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
    'slice_finished': 'Verify the exact output end, then return on the caller stack.',
    'slice_sync_target': 'Patch high/low output comparisons while the decoder is suspended.',
    'DecompressZX0': 'Fast ZX0 v2 bit/gamma decoder with shared literal and match boundaries.',
    'TailRefill': 'Exhausted repeated-match gamma reservoir: refill A from (HL), advance HL, then call the aligned reader only if the stop bit is clear. BC keeps the partial length; DE stays the output cursor.',
    'dzx0_turbo': 'ZX0 v2 turbo decoder; HL=input, DE=output, AF holds the bit reservoir.',
    'dzx0_standard': 'ZX0 v2 compact decoder; HL=input, DE=output; uses the caller stack.',
    'dzx0_mega': 'One-shot bit-phase-expanded ZX0 v2; HL=input, DE=output; AF/BC/HL/DE clobbered. Resident source/history required; writable offset, caller stack.',
    'dzx0m_literals0': 'Refill the bit reservoir and select phase-specific literal Elias paths; BC carries the exact word count.',
    'dzx0m_last_offset': 'Patched negative previous offset; forward LDIR/LDI preserves overlapping history, then restores the source pointer.',
    'dzx0m_new_offset0': 'Decode the inverted offset MSB and test the format EOF before fetching its LSB.',
    'input_check': 'Wait before reading an unavailable page; the bit carry stays live.',
    'literal_split': 'Split literals at input-page boundaries without repeating the output check.',
    'state': 'Mutable words/flags. Keep state and self-modifying operands in writable RAM.',
}


def export(directory, regions, labels, metadata, *, namespace='zx0'):
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
    lines = ['; Generated adapted ZX0 v2 decoder. See LICENSE; Einar Saukas, spke, uniabis.',
             '; Code and patched operands require writable RAM. Counts exclude IRQ/ULA/disk.',
             '; Preserve decoder registers in IRQ handlers, including AF/AF\' when used.',
             '; Coroutine targets are minimums; retain source and complete output history.',
             '; Configure input_pointer/block_end/slice_target before begin; private SP is saved.', '']
    if 'input_pointer' not in labels:
        lines = ['; Generated forward ZX0 v2 decoder. See LICENSE; Einar Saukas.',
                 '; ABI: HL=input, DE=output; AF/BC/DE/HL clobbered; uses caller stack. Resident source/history required.',
                 '; Standard can run in ROM; the other profiles patch offsets and require writable code.',
                 '; Counts exclude IRQ/ULA/disk. Preserve working registers in interrupt handlers.', '']
    if metadata.get('fast_jumps'):
        lines += ['; Optional unconditional JR -> JP: 12 -> 10 T per execution, +1 byte/site.',
                  '; Conditional branches, register/flag ownership and the caller ABI are unchanged.', '']
    if metadata.get('branch_tuned'):
        lines += ['; Optional measured conditional branches: JR 7/12 T versus JP 10 T.',
                  '; Conditions/flags are unchanged; some synthetic cases are slower.', '']
    if metadata.get('variant')=='maximum-branches':
        measured=metadata['qualified_corpus']
        if metadata['prefix_cap']==255:
            lines += ['; Cap255 extends the accepted cap228-fast layout; all61 E01 branch choices are inherited.',
                      '; Twelve word-count chains each add27 LDI instructions: +648 service bytes.',
                      '; Word entry BC>=256 leaves BC>=1 for LDIR; each extended entry saves135 T.',
                      '; Measured real CPU139552884 ->139546674 T; service7517 ->8165 bytes.',
                      '; Every call includes46-T setup, including20-T offset reset; external initialization0 T.',
                      '; The following regression counts compare cap255-fast with cap228-fast.', '']
        lines += [f'; Optional resident Maximum branch policy {metadata["maximum_branch_policy"]}: '
                  f'{metadata["conditional_branch_site_count"]} fixed JP cc -> JR cc sites, one byte smaller each.',
                  '; Before 10 T; after 7 T untaken / 12 T taken. Conditions and flags are unchanged.',
                  f'; Retained 473-case regressions: {measured["slower_cases"]} cases, '
                  f'{measured["slower_real_cases"]} real; maximum delta {measured["maximum_case_delta_tstates"]:+d} T.',
                  '; Policies describe the measured input corpus; arbitrary streams can exercise slower outcomes.',
                  '; Resident complete-input ABI only; no coroutine or guarded-input qualification.', '']
    if metadata.get('inline_tail_refill'):
        lines += ['; Optional Fast repeat-gamma tail refill: +3 bytes, save 18/5 T for stop bit 1/0.',
                  '; Exact input consumption, count, flags and copy continuation are unchanged.', '']
    if metadata.get('mega_tuned'):
        lines += ['; Optional resident Mega: remove four dead offset RL B instructions (-8 T/execution).',
                  '; Four reuse exits use JP 10 T versus JR 7/12 T; total code -4 bytes.',
                  '; Individual untaken exits cost +3 T; complete retained blocks improve. No coroutine ABI.', '']
    routines = dict(ROUTINES)
    if metadata.get('prefix_cap')==255:
        routines['dzx0_mega']='HL=input, DE=output. Initialize BC=FFFF, reset the embedded negative offset, set BC=0 and jump to phase0. All46 T are included in the benchmark.'
    if metadata.get('small_profile'):
        profile=metadata['small_profile']
        lines += ['; Fixed compact Standard-derived profile: '+profile+'. Full forward ZX0 v2 counts remain valid.',
                  '; All per-block initialization and exact EOF return are included in measured CPU.',
                  '; Complete service includes emitted code/embedded state and required caller stack.',
                  '; No tables, alignment padding, scratch, internal buffers or external target initializer.', '']
        if profile=='smc':
            lines += ['; SMC startup is43 T, including20 T to reset the negative offset on every call.',
                      '; Copy setup/restoration70 ->42 T; total delta=-28*matchCopies-newOffsetEntries.',
                      '; The embedded offset needs writable nonreentrant code; plain stack peak4 bytes including return.', '']
            routines['dzx0_standard']='HL=input, DE=output. Set BC=FFFF, reset the embedded offset, then BC=0 and A=80. All43 T of entry setup is inside the benchmark.'
            routines['dzx0s_copy']='BC=positive count. Save input HL, load the patched negative offset, add DE and copy forward with LDIR, then restore input. Stack peak4 including caller return.'
            routines['s01_offset']='Two-byte mutable negative offset embedded in LD HL,nn. Entry resets it; every valid new offset replaces it. Already counted in emitted code.'
        else:
            lines += ['; Gamma-only backward JR12 -> JP10, one extra code byte; copy-back JR is retained.',
                      '; Startup remains34 T; persistent offset stays on caller stack. ROM-compatible, stack peak6 bytes.', '']
            routines['dzx0_standard']='HL=input, DE=output. Initialize the persistent stack offset and bit reservoir in34 T, included in the measured call; code remains ROM-compatible.'
            routines['dzx0s_copy']='Swap saved source/offset through the caller stack, copy the positive BC count forward and restore source/offset. Six-byte peak includes the caller return.'
        routines['dzx0s_literals']='Decode the complete positive Elias literal count and copy exactly BC input bytes; retain bit reservoir A and the input cursor.'
        routines['dzx0s_new_offset']='Decode inverted offset MSB and exact EOF before reading the LSB. Incoming B is discarded by LD B,C; ADD A,A replaces dead RL B flags. Full word shifts remain in all count paths.'
        routines['dzx0s_elias']='Positive full16-bit interlaced Elias count; BC accumulates data, A carries bits and HL advances only on refill.'
        routines['dzx0s_elias_backtrack']='Append the current data bit with RL C/RL B, then return to control-bit parsing. The gamma-jp profile saves2 T on this backward branch.'
    if metadata.get('literal_prefix'):
        lines += ['; Optional literal prefix: BC>=2 takes LDI then LDIR, saving 5 T/run.',
                  '; The BC=1 entry skips LDI. Coroutine checks quota before either copy.',
                  '; Additional target synchronization: '+str(metadata['additional_sync_tstates'])+' T/request.', '']
        routines.update(CopyLiterals='Proven BC>=2 literal run; validate quota before the prefix copy.',
                        CopyLiteral='Single-byte literal entry skips the prefix LDI; share the final LDIR.',
                        slice_long_fast='Quota accepted for BC>=2: LDI uses scratch AF before restoring the reservoir.',
                        slice_fast='Restore the reservoir when suspended, then LDIR with nonzero remaining BC.')
        if metadata.get('one_shot'):
            routines.update(CopyLiterals='Proven BC>=2 resident literal run: one LDI then the shared LDIR.',
                            slice_long_fast='Copy the first literal: HL source, DE output, BC>=2; no quota wrapper.',
                            slice_fast='Shared resident literal LDIR with nonzero BC; no deferred AF restore.')
    if metadata.get('measured_frontier'):
        lines += [f'; Measured maximum-speed direction: prefix cap {metadata["prefix_cap"]}; '
                  + ('ordinary complete-input coroutine.' if metadata.get('coroutine_supported') else 'no coroutine ABI.'),
                  '; Gamma depth proves count >= K; inline LDI copies at most K-1 bytes, then positive LDIR.',
                  '; BC high-byte shifts are delayed until the eighth data bit; full word loops remain.',
                  '; Forward copies retain overlapping history. No tables, alignment, scratch or internal buffers.',
                  f'; Complete service reservation: {metadata["service_memory_bytes"]} bytes, cap {metadata["service_limit_bytes"]}.',
                  ('; Includes all core/wrapper/state bytes, required caller/private stacks and declared IRQ code/headroom.' if metadata.get('coroutine_supported') else
                   '; Includes code/embedded offset, caller return, live source PUSH and declared IRQ code/extra stack.'),
                  '; Input/output/history are separate. Count the actual caller IRQ implementation explicitly.',
                  '; Frontier is measured on the retained corpus; global optimality is not established.', '']
        if metadata.get('shared_prefixes'):
            lines += ['; Optional shared LDI chains end in cloned LDIR/command continuations.',
                      '; Move each existing 10-T tail JP to its entry; original small-copy tails stay in place.',
                      '; Direct literal4 entries and word-prefix joins each eliminate one 10-T JP.',
                      '; Cloned labels are private to their continuation; only the original offset word is mutable.', '']
        elif metadata['prefix_cap']>127:
            extra=metadata['prefix_cap']-127
            lines += [f'; Word counts >=256 copy {extra} initial bytes, then share the existing 127-LDI suffix.',
                      f'; Match setup runs once. The shared suffix retains BC>={256-extra} and a positive LDIR tail.', '']
    if metadata.get('variant')=='maximum-coroutine':
        lines += ['; Optional Spectrum Z80 profile REQUIRES undocumented CP IXH / CP IXL, 8 T each.',
                  '; IX holds the quota only while decoding: caller IX is saved on entry and restored at every return.',
                  '; Preserve live IX and AF/AF\' in IRQ. Other Z80 clones require their own opcode qualification.',
                  '; Phase checks precede command preparation; published output cursors match ordinary Fast.',
                  '; Complete resident input is required. Internal input/count preparation can suspend earlier.',
                  '; Final quotas use FFFF internally so raw EOF is consumed before finish; caller targets stay exact.', '']
    if metadata.get('variant')=='maximum-coroutine':
        routines.update(dzx0_mega='Initialize the shared negative offset and enter phase-specific decoding on the private stack.',
            slice_sync_target='Normalize final demand to FFFF in quota_target, preserving the real caller target; BC/HL/AF are scratch.',
            slice_resume='Save caller IX, install the normalized quota in IX, restore the private AF/BC/DE/HL frame and continuation.',
            slice_yield='Save DE output and AF/BC/DE/HL continuation on the private stack; restore caller IX and SP before returning.',
            slice_finished='Verify DE equals block_end after raw EOF, set finished, restore caller IX/SP and return.',
            begin='Save caller IX/SP, install IX quota and private finish return, initialize HL/DE and enter the phased core.')
        for site in metadata.get('quota_sites',[]):
            routines[site['name']+'_check']='Before '+site['command']+': AF reservoir is parked in AF\'; compare output DE with IX quota using CP IXH/IXL. No output precedes quota validation.'
    for name,info in metadata.get('prefixes',{}).items():
        routines[name]=(f'Gamma-proven {info["family"]} count >= {info["minimum_count"]}; '
                            f'copy {info["prefix_bytes"]} bytes with LDI, leave positive BC for LDIR. '
                            + ('HL is resident input.' if info['family']=='literals' else
                               'Save source HL on '+('private decoder' if metadata.get('coroutine_supported') else 'caller')+' stack; use patched negative offset for forward history.'))
    if metadata.get('measured_frontier'):
        for name in labels:
            if name.startswith('shared_zero_clone_'):
                routines[name]='Cloned copy continuation/header: same register/flag and memory-access order as the original; ends at an existing JP.'
            elif name.startswith('shared_zero_'):
                routines[name]='Shared descending LDI suffix: BC exceeds the selected prefix; fall through to cloned LDIR/continuation, preserving forward overlap.'
            elif name.startswith('max_gamma_'):
                routines[name]='Depth-specific Elias continuation; BC accumulates length, A holds bit reservoir, HL advances only on refill. RL B begins at data bit eight.'
            elif name.startswith('max_word_join_'):
                routines[name]=('Word-entry setup is complete; jump to the shared long LDI chain, removing the old intermediate suffix JP.' if metadata.get('shared_prefixes') else
                    'Word-count continuation: retain high-byte shifts and join the proven >=128 copy path; extra JP costs 10 T.')
            elif name.startswith('max_suffix_'):
                routines[name]=('Retained >=128 entry alias: source/offset setup is complete; enter the common shared LDI chain.' if metadata.get('shared_prefixes') else
                    f'Shared 127-LDI suffix; word-entry setup already saved source/loaded offset and copied {metadata["prefix_cap"]-127} bytes. BC>=128 on every entry; restore source only at the original match tail.')
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
                    description=routines[name]
                    if metadata.get('one_shot') and name=='DecompressZX0':
                        description='Resident Fast ZX0 v2; bit/gamma decoder, writable offset, no boundaries, IX preserved.'
                    lines.append(f'; {namespace}_{name}: {description}')
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
