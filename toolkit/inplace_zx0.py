"""Trace every ZX0 input read/output write and prove a forward overlap margin.

Reference algorithm copyright (c) 2021 Einar Saukas. All rights reserved.
See third_party/zx0/LICENSE for the BSD-3-Clause conditions and disclaimer.
This is a host model, not an installed player decoder or disk producer.
"""
import hashlib

BANK = 16384


class OverlapError(ValueError):
    pass


def trace(data, *, limit, input_start=None, bank_bytes=BANK):
    """Optionally replay in shared memory; buffered bits no longer need RAM.

    For each write w with unread input at cursor p, require w < start+p.
    The maximum w+1-p is the minimum safe input start relative to output.
    Literal reads happen before their writes, including in-place LDIR.
    """
    data = bytes(data)
    if not data or not 1 <= limit <= 65535: raise ValueError('invalid trace bounds')
    memory = None
    if input_start is not None:
        if input_start < 0 or input_start+len(data)>bank_bytes or limit>bank_bytes:
            raise ValueError('shared layout exceeds bank')
        memory = bytearray(b'\xa5'*bank_bytes)
        memory[input_start:input_start+len(data)] = data
    position = mask = value = last_byte = 0
    backtrack = False
    output = bytearray(); digest = hashlib.sha256()
    minimum = max_offset = literals = matches = 0
    critical = None; last_write_input = None

    def byte():
        nonlocal position, last_byte
        if position >= len(data): raise ValueError('truncated ZX0 input')
        last_byte = data[position] if memory is None else memory[input_start+position]
        if last_byte != data[position]: raise OverlapError('unread input was changed')
        position += 1
        return last_byte

    def bit():
        nonlocal mask, value, backtrack
        if backtrack:
            backtrack = False
            return last_byte & 1
        mask >>= 1
        if not mask: mask = 128; value = byte()
        return int(bool(value & mask))

    def gamma(inverted=0):
        result = 1
        while not bit():
            result = (result << 1) | (bit() ^ inverted)
            if result > 65535: raise ValueError('oversized gamma')
        return result

    def write(value, kind):
        nonlocal minimum, critical, last_write_input
        at = len(output)
        if at >= limit: raise ValueError('oversized ZX0 output')
        if position < len(data):
            required = at+1-position
            if required > minimum:
                minimum = required
                critical = dict(output_offset=at, input_cursor=position, kind=kind)
            if memory is not None and input_start+position<=at<input_start+len(data):
                raise OverlapError(f'write {at} overwrites unread byte {at-input_start}')
        if memory is not None: memory[at] = value
        output.append(value); last_write_input = position
        digest.update(position.to_bytes(4, 'little'))

    def copy(offset, length):
        nonlocal max_offset, matches
        if not 0 < offset <= len(output) or len(output)+length > limit:
            raise ValueError('invalid ZX0 match')
        max_offset = max(max_offset, offset); matches += 1
        for _ in range(length):
            source = len(output)-offset
            value = output[source] if memory is None else memory[source]
            if value != output[source]: raise OverlapError('live history was changed')
            write(value, 'match')

    offset = 1; mode = 'literal'
    while True:
        if mode == 'literal':
            length = gamma(); literals += 1
            if len(output)+length > limit: raise ValueError('oversized literal')
            for _ in range(length): write(byte(), 'literal')
            if not bit():
                copy(offset, gamma())
                if not bit(): continue
        offset = gamma(1)
        if offset == 256:
            if position != len(data): raise ValueError('trailing ZX0 input')
            return bytes(output), dict(decoded_bytes=len(output), input_bytes=position,
                minimum_input_start=minimum,
                minimum_footprint=max(len(output), minimum+len(data)), critical_write=critical,
                write_input_cursors_sha256=digest.hexdigest(), max_offset=max_offset,
                literal_runs=literals, match_runs=matches,
                input_bytes_after_last_write=len(data)-last_write_input,
                output_writes=len(output), shared_memory_verified=memory is not None)
        offset = offset*128-(byte() >> 1)
        backtrack = True
        copy(offset, gamma()+1)
        mode = 'offset' if bit() else 'literal'


def layout(payload_bytes, decoded_bytes, minimum_input_start, stream_offset, *, bank_bytes=BANK):
    """Place all whole sectors intersecting header/body at the top of a bank.

    Preserve the last shared sector in the existing 256-byte fixed carry
    buffer BEFORE decoding. No unread next-block byte is treated as scratch.
    Header acquisition/control and copying that carry are not measured here.
    """
    prefix = stream_offset % 256 + 4
    span = ((prefix+payload_bytes+255)//256)*256
    start = bank_bytes-span+prefix
    trailing = span-prefix-payload_bytes
    exact_start = bank_bytes-payload_bytes
    return dict(sector_span_bytes=span, prefix_bytes=prefix, trailing_bytes=trailing,
        input_start=start, slack_bytes=start-minimum_input_start,
        sector_aligned_fits=span<=bank_bytes and decoded_bytes<=bank_bytes and start>=minimum_input_start,
        exact_end_input_start=exact_start, exact_end_slack_bytes=exact_start-minimum_input_start,
        exact_end_fits=payload_bytes<=bank_bytes and decoded_bytes<=bank_bytes and exact_start>=minimum_input_start,
        shared_tail_must_be_saved=bool(trailing), carry_copy_bytes=256 if trailing else 0,
        output_end_wraps=decoded_bytes==bank_bytes)
