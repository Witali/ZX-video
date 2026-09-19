"""FSA1/FSA2: six unchanged AY records before each one-frame FSC1/FSC2 group.

The common ZX0 stream shares one decompression history for audio and video.
Header matches FSC1 except magic. AY records keep the existing IRQ queue
format: count u8 followed by count register/value pairs. This PC framing
experiment does not prove Z80 parsing, queue deadlines or disk delivery.
"""
import argparse
import json
from pathlib import Path
import struct

import ay_interrupt
import cell_output_stream
from probe_fast_fragments import SIZES
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header, read_group
from build_long_video_trd import AyFrame


def take_tick(reader):
    count = reader.take(1)[0]
    if count > 11:
        raise ValueError('invalid AY register count')
    pairs = reader.take(count*2)
    registers = list(pairs[::2])
    if any(r > 10 for r in registers) or registers != sorted(set(registers)):
        raise ValueError('invalid AY registers')
    return bytes([count])+pairs


def pack(cells, audio):
    extended = cells[:4] == b'FSC2'
    if extended:
        from raw_attribute_stream import packets
        _, _, _, parsed = packets(cells)
        groups = [dict(frames=g[0], coded_bytes=len(g[6])+len(g[7])) for g, _ in parsed]
    else:
        _, _, groups = cell_output_stream.unpack(cells)
    r, ticks = Reader(cells), Reader(audio)
    _, _, count, _, _ = read_header(r, magic=b'FSC2' if extended else b'FSC1')
    out = bytearray((b'FSA2' if extended else b'FSA1')+cells[4:r.pos])
    for group in groups:
        if group['frames'] != 1:
            raise ValueError('FSA1 requires one-frame groups')
        for _ in range(6):
            out += take_tick(ticks)
        start = r.pos
        header = r.take(11)
        _, vl, ml, _, _ = struct.unpack('<HHHBI', header)
        r.take(vl+ml+80+group['coded_bytes'])
        out += cells[start:r.pos]
    r.end(); ticks.end()
    return bytes(out)


def unpack(source):
    r = Reader(source)
    extended = source[:4] == b'FSA2'
    _, _, count, _, _ = read_header(r, magic=b'FSA2' if extended else b'FSA1')
    cells, audio, sizes = bytearray((b'FSC2' if extended else b'FSC1')+source[4:r.pos]), bytearray(), []
    for index in range(count):
        start_audio = len(audio)
        for _ in range(6):
            audio += take_tick(r)
        sizes.append(len(audio)-start_audio)
        start = r.pos
        if extended:
            from raw_attribute_stream import read_packet
            read_packet(r, count-index)
            cells += source[start:r.pos]
            continue
        header = r.take(11)
        n, vl, ml, _, bits = struct.unpack('<HHHBI', header)
        if n != 1:
            raise ValueError('FSA1 requires one-frame groups')
        metadata = r.take(vl+ml)
        r.take(80)
        encoded = r.take((bits+7)//8)
        check = Reader(header+metadata+encoded)
        group = read_group(check, count-index, fast_fragments=True)
        check.end()
        r.take(sum(SIZES.get(v, 0) for v in group[3]))
        cells += source[start:r.pos]
    r.end()
    if extended:
        from raw_attribute_stream import packets
        packets(bytes(cells))
    else:
        cell_output_stream.unpack(bytes(cells))
    return bytes(cells), bytes(audio), sizes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cells', type=Path, required=True)
    p.add_argument('--audio', type=Path, required=True)
    p.add_argument('--raw-ay', type=Path, required=True)
    p.add_argument('--timeline-report', type=Path, default=Path(__file__).with_name('no_credits_timeline.json'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--baseline-commit', default='6103e11')
    args = p.parse_args()
    cells, audio, raw = (f.read_bytes() for f in (args.cells, args.audio, args.raw_ay))
    timeline = json.loads(args.timeline_report.read_text(encoding='utf-8'))
    if (not timeline['complete'] or sha(audio) != timeline['ay_pairs_sha256']
            or sha(raw) != timeline['ay_sha256']):
        raise ValueError('different soundtrack')
    data = pack(cells, audio)
    restored_cells, restored_audio, sizes = unpack(data)
    if restored_cells != cells or restored_audio != audio or len(raw) != len(sizes)*54:
        raise AssertionError('A/V byte roundtrip or rate differs')
    registers, ticks = bytearray(11), Reader(restored_audio)
    for start in range(0, len(raw), 9):
        record = take_tick(ticks)
        for i in range(1, len(record), 2):
            registers[record[i]] = record[i+1]
        if registers != ay_interrupt.registers(AyFrame.deserialize(raw[start:start+9])):
            raise AssertionError('50 Hz AY replay differs')
    ticks.end()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    report = dict(scope=__doc__, complete=True, baseline_commit=args.baseline_commit,
        cells_sha256=sha(cells), audio_pairs_sha256=sha(audio), raw_ay_sha256=sha(raw),
        stream_sha256=sha(data), raw_bytes=len(data), frames=len(sizes), ay_ticks=len(sizes)*6,
        audio_bytes=len(audio), max_audio_bytes_per_frame=max(sizes),
        exact_fsc_roundtrip=True, exact_audio_roundtrip=True, all_ay_registers_verified=True,
        no_additional_pixel_changes=True, same_50hz_ay=True,
        player_changed=False, integrated_player_delta_tstates=0,
        frame_pacing_verified=False, disk_delivery_verified=False)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
