"""Protected raw native replay with actual compressed-input/output overlap.

Unlike native_block.execute, this runner permits only the input and output
allocations to intersect. It checks each input read and output write against
the live unread input frontier, rather than treating distance-one history as
proof of compressed-input overlap. The host trace supplies the minimum safe
placement and an independent digest of the input cursor at every write.

Current raw decoders read history with LDI/LDIR; other marked data reads are
parser reads. A future decoder using another history-load instruction needs
an explicit classification extension before it can use this gate.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from z80 import Z80Machine


IRQ = bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')


def host_trace(codec, payload, expected, *, input_start=None):
    if codec == 'zx0':
        from zx0.inplace import trace
    elif codec == 'lzsa2':
        from lzsa.codec import trace
    else:
        raise ValueError('codec must be zx0 or lzsa2')
    decoded, proof = trace(payload, limit=len(expected), input_start=input_start,
                           bank_bytes=65536)
    assert decoded == expected, 'host output differs'
    return proof


def execute(profile, payload, expected, *, codec, source=None, output=0xc000,
            caller_stack=0xbff0, interrupts=False, alternate_af=0x9797,
            watch=None):
    """Replay a valid raw block at its host minimum unless source is explicit.

    An explicitly unsafe placement is intentionally not rejected by the host
    preflight: the live native write observer must catch its first unread-byte
    overwrite. Code, the two allowed self-modified offset bytes, caller stack,
    IRQ entry and return stub remain protected independently of I/O overlap.
    """
    payload, expected = bytes(payload), bytes(expected)
    proof = host_trace(codec, payload, expected)
    if source is None:
        source = output + proof['minimum_input_start']
    regions, labels, metadata = profile
    end, output_end = source + len(payload), output + len(expected)
    assert source >= output and 0 <= source < end <= 65536
    assert 0 <= output <= output_end <= 65535
    stack, stop = caller_stack, 0x100
    allocations = [(at, at+len(blob), 'code') for at, blob in regions]
    allocations += [(source, end, 'input'), (stack-64, stack, 'caller/IRQ stack'),
                    (0x38, 0x38+len(IRQ), 'IRQ'), (0x200, 0x207, 'IRQ bootstrap'),
                    (stop, stop+1, 'return breakpoint')]
    if expected:
        allocations.append((output, output_end, 'output/history'))
    for index, (lo, hi, name) in enumerate(allocations):
        assert 0 <= lo < hi <= 65536, ('invalid allocation', name, lo, hi)
        for other_lo, other_hi, other_name in allocations[index+1:]:
            if {name, other_name} == {'input', 'output/history'}:
                continue
            assert hi <= other_lo or other_hi <= lo, ('overlapping allocations', name, other_name)
    if source-output >= proof['minimum_input_start']:
        shared = host_trace(codec, payload, expected, input_start=source-output)
        assert shared['shared_memory_verified']

    m = Z80Machine()
    m.memory[:] = b'\xa5'*65536
    for at, blob in regions:
        m.set_memory_block(at, blob)
    patches = set(metadata.get('patched_addresses', []))
    assert all(any(lo <= at < lo+len(blob) for lo, blob in regions) for at in patches)
    # Force each call to initialize its own previous-offset operand.
    for at in patches:
        m.memory[at] = 0xa5
    protected_code = [(at, bytes(m.memory[at:at+len(blob)])) for at, blob in regions]
    m.set_memory_block(source, payload)
    m.set_memory_block(stack-2, stop.to_bytes(2, 'little'))
    m.set_memory_block(0x38, IRQ)
    entry = labels[metadata['entry']]
    bootstrap = bytes.fromhex('ed56fb00c3') + entry.to_bytes(2, 'little')
    m.set_memory_block(0x200, bootstrap)
    m.pc, m.sp, m.hl, m.de = entry, stack-2, source, output
    m.af, m.bc, m.iy, m.alt_af = 0x5a93, 0xb7d9, 0x57b9, alternate_af
    preserved = dict(ix=0x1357, iy=0x57b9, alt_bc=0x2468, alt_de=0x369a, alt_hl=0xace1)
    if codec == 'zx0':
        preserved['alt_af'] = alternate_af
    for name, value in preserved.items():
        setattr(m, name, value)
    if interrupts:
        m.pc = 0x200
    m.mark_addrs(0, 65536, m.READ_MARK | m.WRITE_MARK)
    for at, blob in regions:
        m.unmark_addrs(at, len(blob), m.READ_MARK)
    for at, length in ((0x38, len(IRQ)), (0x200, 7)):
        m.unmark_addrs(at, length, m.READ_MARK)
    for at in patches:
        m.unmark_addr(at, m.WRITE_MARK)
    if watch:
        assert all(any(lo <= at < lo+len(blob) for lo, blob in regions) for at in watch)
        for at in watch:
            m.mark_addr(at, m.READ_MARK)
    high, cursor, lowest = output, source, stack-2
    stack_written = {stack-2, stack-1}
    digest = hashlib.sha256()
    minimum = overlap_writes = history_reads = source_rereads = 0
    critical = None

    def read(at):
        nonlocal cursor, history_reads, source_rereads
        if watch and at in watch:
            watch[at](m)
            return m.memory[at]
        if stack-64 <= at < stack:
            assert at in stack_written, ('read uninitialized stack', hex(at), hex(m.pc))
            return m.memory[at]
        assert any(lo < m.pc <= lo+len(blob) for lo, blob in regions), (
            'I/O read outside decoder', hex(at), hex(m.pc))
        block = bytes(m.memory[m.pc-2:m.pc]) in (b'\xed\xa0', b'\xed\xb0')
        if at == cursor and cursor < end:
            assert m.memory[at] == payload[at-source], ('unread input changed', hex(at), hex(m.pc))
            cursor += 1
        elif block:
            assert output <= at < high, ('block read outside consumed source/history', hex(at), hex(m.pc))
            assert m.memory[at] == expected[at-output], ('history changed', hex(at), hex(m.pc))
            history_reads += 1
        else:
            assert source <= at < end and at == cursor-1, (
                'nonsequential parser read/EOF overread', hex(at), hex(cursor), hex(m.pc))
            assert m.memory[at] == payload[at-source], ('parser rereads overwritten input', hex(at), hex(m.pc))
            source_rereads += 1
        return m.memory[at]

    def write(at, value):
        nonlocal high, lowest, minimum, critical, overlap_writes
        if output <= at < output_end:
            assert at == high and value == expected[at-output], ('output differs', hex(at), hex(m.pc))
            assert not cursor <= at < end, ('output overwrites unread input', hex(at), hex(cursor), hex(m.pc))
            consumed = cursor-source
            if cursor < end and at-output+1-consumed > minimum:
                minimum = at-output+1-consumed
                critical = dict(output_offset=at-output, input_cursor=consumed)
            digest.update(consumed.to_bytes(4, 'little'))
            overlap_writes += int(source <= at < end)
            high += 1
        else:
            assert stack-64 <= at < stack, ('write outside stack/output', hex(at), hex(m.pc))
            stack_written.add(at)
            lowest = min(lowest, at)
        m.memory[at] = value

    m.set_read_callback(read)
    m.set_write_callback(write)
    m.set_breakpoint(stop)
    budget = 20_000_000
    m.ticks_to_stop = budget
    irqs = skipped = 0
    while m.pc != stop:
        event = m.run()
        assert not event & m._TICKS_LIMIT_HIT, 'native CPU budget exceeded'
        if interrupts and m.pc != stop and event & m._END_OF_FRAME:
            if not m.iff1 or m.int_disabled:
                skipped += 1
                continue
            m.on_handle_active_int()
            assert m.pc == 0x38
            irqs += 1
    assert high == output_end and cursor == end, ('incomplete output/input', high, cursor)
    assert m.hl == (cursor & 65535) and m.de == high and m.sp == stack, 'raw return cursors/stack differ'
    assert all(getattr(m, name) == value for name, value in preserved.items()), 'preserved registers changed'
    for at, blob in protected_code:
        assert all(m.memory[at+i] == value for i, value in enumerate(blob) if at+i not in patches), 'code changed'
    assert bytes(m.memory[0x38:0x38+len(IRQ)]) == IRQ
    assert bytes(m.memory[0x200:0x207]) == bootstrap
    native_digest = digest.hexdigest()
    exact_order = (minimum == proof['minimum_input_start'] and
                   native_digest == proof['write_input_cursors_sha256'])
    return dict(tstates=budget-m.ticks_to_stop, exact=True,
        injected_interrupts=irqs, unavailable_interrupt_events=skipped,
        stack_bytes=stack-lowest, source=source, output=output,
        input_bytes=len(payload), output_bytes=len(expected),
        input_start_relative_to_output=source-output,
        host_minimum_input_start=proof['minimum_input_start'],
        native_minimum_input_start=minimum, minimum_footprint=proof['minimum_footprint'],
        native_critical_write=critical, actual_overlap_bytes=overlap_writes,
        history_reads=history_reads, parser_rereads=source_rereads,
        write_input_cursors_sha256=native_digest, host_read_order_exact=exact_order,
        dirty_offset_startup_tested=True, code_protected=True, raw_abi_exact=True)


def source_hashes():
    """Normalized source identity survives Windows checkout line endings."""
    root = Path(__file__).resolve().parents[2]
    paths = (
        'libraries/tests/native_inplace_block.py',
        'libraries/tests/test_native_inplace_block.py',
        'libraries/tests/native_block.py',
        'libraries/tests/measure_bit_phases.py',
        'libraries/tests/measure_mega_prefix.py',
        'libraries/tests/measure_long_copy.py',
        'libraries/tests/measure_full_token_dispatch.py',
        'libraries/zx0/src/zx0/maximum.py',
        'libraries/zx0/src/zx0/_z80.py',
        'libraries/zx0/src/zx0/inplace.py',
        'libraries/zx0/src/zx0/codec.py',
        'libraries/lzsa/src/lzsa/hybrid.py',
        'libraries/lzsa/src/lzsa/wide.py',
        'libraries/lzsa/src/lzsa/_wide_kernels.py',
        'libraries/lzsa/src/lzsa/_z80.py',
        'libraries/lzsa/src/lzsa/codec.py',
    )
    return {path: hashlib.sha256((root/path).read_text(encoding='utf-8').encode()).hexdigest()
            for path in paths}


def authenticate_report(report, *, executed_sources):
    """Bind replayed inputs/regions/CPU to the already frozen disjoint proofs.

    This can also finalize a saved matrix after a reporting-only field rename;
    executed_sources then retains the original runner identity separately from
    the reporting source. No native result is synthesized or rerun here.
    """
    root = Path(__file__).resolve().parents[2]
    archives = (
        ('zx0-False', 'libraries/evidence/shared_zero_prefix_native.json.gz', '228'),
        ('zx0-True', 'libraries/evidence/shared_zero_prefix_high_word.json.gz', '228'),
        ('lzsa2-False', 'libraries/evidence/wide_hybrid/wide_hybrid_experiment_short.json.gz', 'budget-9500'),
    )
    provenance = []
    for key, path, selector in archives:
        packed = (root/path).read_bytes()
        decoded = gzip.decompress(packed)
        saved = json.loads(decoded)
        assert saved['complete'], ('incomplete archived baseline', path)
        old = saved['profiles'][selector]
        current = report['profiles'][key]
        if key.startswith('zx0'):
            rows = old['blocks']
            regions, moved = old['regions'], old['relocated_regions']
        else:
            rows = old['full_blocks'] + old['directed_blocks']
            regions, moved = old['layout']['regions'], old['relocated_layout']['regions']
        assert current[0]['regions'] == regions and current[1]['regions'] == moved, (
            'current/archive region mismatch', path)
        codec, large = key.split('-')
        actual = {r['case']:r for r in report['blocks']
                  if r['codec'] == codec and str(r['large_layout']) == large}
        assert set(actual) == {r['case'] for r in rows}, ('archive case set mismatch', path)
        for row in rows:
            new = actual[row['case']]
            assert new['payload_sha256'] == row.get('input_sha256', row.get('payload_sha256'))
            assert new['raw_sha256'] == row.get('output_sha256', row.get('raw_sha256'))
            assert new['plain']['tstates'] == row['candidate_tstates'], ('inplace CPU changed', codec, row['case'])
        provenance.append(dict(path=path, profile=selector,
            archive_sha256=hashlib.sha256(packed).hexdigest(),
            decoded_sha256=hashlib.sha256(decoded).hexdigest(),
            source_baseline=saved.get('source_baseline'),
            archived_source_sha256_lf=saved.get('source_sha256_lf', {}),
            archived_revalidated_source_sha256_lf=saved.get('revalidated_generator_source_sha256_lf', {}),
            input_hashes_exact_cases=len(rows), emitted_regions_exact=True,
            per_case_plain_cpu_equal_to_disjoint=True))
    for row in report['blocks']:
        for mode in ('plain', 'irq', 'relocated'):
            result = row[mode]
            if 'dirty_offset_initialized' in result:
                result['dirty_offset_startup_tested'] = result.pop('dirty_offset_initialized')
    final_sources = source_hashes()
    report['provenance'] = dict(
        executed_source_sha256_lf=executed_sources,
        reporting_source_sha256_lf=final_sources,
        post_replay_source_changes=[path for path in final_sources
                                    if executed_sources.get(path) != final_sources[path]],
        archived_baseline_reports=provenance,
        native_host_digest_scope='SHA256 of four-byte little-endian unique compressed-input cursor before every output write; exact for plain, IRQ, and relocated in every recorded case. Parser rereads do not advance the cursor; history reads are independent.',
        minimum_scope='Host and native minima exclude consumed input and buffered bits/nibbles; minimum safe placement is source=output+minimum. Empty output has no actual compressed-input/output overlap.',
        abi_scope='IX/IY/BC\'/DE\'/HL\' and caller SP survive; ZX0 also preserves AF\'. LZSA2 AF/AF\' are documented scratch.',
        dirty_offset_scope='Every permitted offset operand starts A5A5 before each call; exact output/EOF proves startup under dirty state, without requiring empty/no-match streams to modify it.')
    return report


def baseline(output_path):
    """Bounded E00 proof of existing fast raw profiles; no optimization sweep."""
    from measure_bit_phases import samples as zx_samples
    from measure_mega_prefix import high_word_samples
    from measure_long_copy import samples as lz_samples
    from measure_full_token_dispatch import directed_tokens
    from zx0.maximum import build as zx_build
    from lzsa.hybrid import build as lz_build
    executed_sources = source_hashes()
    profiles = {
        ('zx0', False): (zx_build(prefix_cap=228, shared_prefixes=True),
                        zx_build(core=0x9103, prefix_cap=228, shared_prefixes=True)),
        ('zx0', True): (zx_build(core=0x0800, prefix_cap=228, shared_prefixes=True),
                       zx_build(core=0x0703, prefix_cap=228, shared_prefixes=True)),
        ('lzsa2', False): (lz_build(profile='fast'), lz_build(profile='fast', core=0x9103)),
    }
    report = dict(date='2026-10-20', baseline_revision='9c28b01f', complete=False,
        release=False, optimization=False,
        contract='Actual minimum-safe compressed-input/output overlap; unread source protected at each write; exact EOF/raw ABI/code/dirty offset; separate IM1 and relocation replay.',
        profiles={f'{codec}-{large}': [dict(metadata=p[2], regions=[dict(address=a, bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for a,b in p[0]]) for p in pair] for (codec,large),pair in profiles.items()},
        blocks=[])
    output_path = Path(output_path)
    def save():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(output_path, 'wt', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, sort_keys=True)
            stream.write('\n')
    cases = [('zx0', False, row) for row in zx_samples()]
    cases += [('zx0', True, row) for row in high_word_samples()]
    cases += [('lzsa2', False, row) for row in lz_samples()]
    cases += [('lzsa2', False, row[:3]) for row in directed_tokens()]
    try:
        for index, (codec, large, (name, payload, raw)) in enumerate(cases):
            profile, moved = profiles[codec, large]
            options = dict(output=0x3000, caller_stack=0x2ff0) if large else {}
            plain = execute(profile, payload, raw, codec=codec, **options)
            irq = execute(profile, payload, raw, codec=codec, interrupts=True, **options)
            relocated = execute(moved, payload, raw, codec=codec, **options)
            assert plain['tstates'] == relocated['tstates'], (codec, name, 'relocation changed CPU')
            assert all(r['host_read_order_exact'] for r in (plain, irq, relocated)), (codec, name, 'native/host read order differs')
            assert plain['actual_overlap_bytes'] > 0 or not raw, (codec, name, 'no actual input overlap')
            report['blocks'].append(dict(codec=codec, case=name, large_layout=large,
                payload_sha256=hashlib.sha256(payload).hexdigest(), raw_sha256=hashlib.sha256(raw).hexdigest(),
                plain=plain, irq=irq, relocated=relocated))
            if (index+1) % 25 == 0:
                save()
                print(json.dumps(dict(completed=index+1, total=len(cases), codec=codec, case=name)), flush=True)
        report['complete'] = True
        report['summary'] = {}
        for codec in ('zx0', 'lzsa2'):
            rows = [r for r in report['blocks'] if r['codec'] == codec]
            real = [r for r in rows if r['case'].startswith('real-')]
            report['summary'][codec] = dict(cases=len(rows), real_blocks=len(real),
                real_tstates=sum(r['plain']['tstates'] for r in real),
                actual_overlap_cases=sum(r['plain']['actual_overlap_bytes']>0 for r in rows),
                maximum_plain_stack_bytes=max(r['plain']['stack_bytes'] for r in rows),
                maximum_irq_stack_bytes=max(r['irq']['stack_bytes'] for r in rows),
                injected_interrupts=sum(r['irq']['injected_interrupts'] for r in rows),
                host_read_order_exact=all(r['plain']['host_read_order_exact'] for r in rows))
        authenticate_report(report, executed_sources=executed_sources)
    except BaseException as error:
        report['failure'] = dict(case=name, codec=codec, error=repr(error))
        raise
    finally:
        save()
    print(json.dumps(report['summary']), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    baseline(parser.parse_args().output)
