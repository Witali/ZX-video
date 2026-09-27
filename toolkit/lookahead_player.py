"""Install the two-byte Huffman cache and its bounded packet input contract.

FAP3 still stores no guards. The parser writes its existing zero guard and
reserves one further readable byte within the same packet window. That
second byte may contain any value; it is never part of a decoded symbol.
Payload capacity falls by one byte, with no extra disk byte, copy or T-state.
Oversized optional configurations are rejected before an image is built.
"""
from build_fap3_trd import sha
from bulk_frame_stream import read_packet, WINDOW
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
import bulk_frame_z80 as packet
import cached_huffman_lookahead as cache


def packet_contract(read8, instructions, labels):
    rows = [r for r in instructions if labels['read_packet'] <= r['address'] < labels['end']
            and r['instruction'] == 'LD DE,valid length range']
    if len(rows) != 1: raise ValueError('expected one packet capacity check')
    at = rows[0]['address']
    old, new = WINDOW-1, WINDOW-2
    before = bytes([0x11, *((old-294+1).to_bytes(2, 'little'))])
    after = bytes([0x11, *((new-294+1).to_bytes(2, 'little'))])
    if rows[0]['tstates'] != 10 or bytes(read8(at+i) for i in range(3)) != before:
        raise ValueError('FAP3 length range differs')
    return dict(address=at, before_hex=before.hex(), code_hex=after.hex(),
        minimum_payload_bytes=294, previous_maximum_payload_bytes=old, maximum_payload_bytes=new,
        packet_window_bytes=WINDOW, readable_guard_bytes=2, initialized_guard_bytes=1,
        second_guard_value='arbitrary; read-only and within the packet window',
        baseline_tstates=10, tstates=10, delta_tstates=0,
        extra_stream_bytes=0, extra_copies=0, extra_allocated_ram_bytes=0)


def audit_packets(raw, metadata):
    if sha(raw) != metadata['raw_sha256']: raise ValueError('wrong Huffman source')
    reader = Reader(raw)
    _, _, count, _, _ = read_header(reader, magic=b'FAP3')
    sizes = []
    for index in range(count):
        _, detail = read_packet(reader, stored_guards=False)
        if metadata['frame_start'] <= index < metadata['frame_end_exclusive']:
            size = len(detail['payload'])
            if size > WINDOW-2: raise ValueError(('two-byte cache requires a smaller packet or the old decoder', index, size, WINDOW-2))
            sizes.append(size)
    reader.end()
    if len(sizes) != metadata['frames']: raise ValueError('packet coverage differs')
    return dict(checked_packets=len(sizes), maximum_payload_bytes=max(sizes),
                source_sha256=sha(raw), all_fit=True)


def install(read8, put, metadata, h, raw):
    """Before inline-Huffman copying; update its source listing and labels."""
    inputs = audit_packets(raw, metadata)
    _, _, labels, rows = packet.build(metadata['decoder_labels'], metadata['queue_labels'],
        h.frame.w, h.frame.draw, metadata['compiled_masks']['labels'], h.audio,
        stored_guards=False, separate_prepare='idle', page_entry=0x9780)
    if labels != metadata['packet_labels']: raise ValueError('packet labels differ')
    contract = packet_contract(read8, rows, labels)
    report = cache.build(read8, h.frame.instructions.values(), h.frame.recon, frame=True)
    for region in report['regions']:
        put(region['address'], bytes.fromhex(region['code_hex']))
    put(contract['address'], bytes.fromhex(contract['code_hex']))
    h.frame.recon.update(report['labels'])
    h.frame.instructions = {r['address']: r for r in report['listing']}
    return dict(enabled=True, implementation=report, packet_contract=contract, input_audit=inputs,
                parser_tstate_delta=0, stream_delta_bytes=0)
