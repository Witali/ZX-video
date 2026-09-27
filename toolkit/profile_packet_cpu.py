"""Profile the retained player's complete cold-loaded packet reader.

Required reads start before prefill, with the field clock frozen, no injected
IRQs and mocked ROM services. Every packet byte must match and be written once.
This measures deterministic instruction costs for this demand-only workload;
it does not reproduce integrated read-ahead, disk latency or AY playback.
Metadata is included here AND in the separate frame fixture: never add it twice.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import test_resumable_packet as reader
from verify_streaming_zx0_input import validate_histogram

ROOT = Path(__file__).parent


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def profile(directory, part, count):
    original_fixture = reader.fixture
    hist, stages = Counter(), Counter()
    frame_stages, instructions, state = [], {}, {}
    previous = Counter()

    def fixture(directory, part):
        nonlocal previous
        c, m, packets, digest = original_fixture(directory, part)
        if m.get('resumable_packet'): raise ValueError('retained baseline required')
        state.update(metadata=m, trd_sha256=digest, packet_count=len(packets))
        rows = {r['address']: r for r in m['slot_queue_instruction_listing']}
        audio = {r['address']: r for r in m['resident_audio']['compiled']['listing']}
        z, q = m['decoder_labels'], m['queue_labels']['bridge']
        ranges = [(z['slice_until'], z['slice_until']+m['bank2_zx0']['prefix_bytes']),
                  (z['slice_begin'], z['state'])]
        code = bytes(c.read8(i) for i in range(65536))
        original_step = c.step

        def step():
            pc, before = c.pc, c.tstates
            bank = c.port_7ffd & 7 if pc >= 0xc000 else -1
            if bank == -1 and any(start <= pc < end for start, end in ranges):
                stage, row = 'zx0', None
            else:
                row = audio[pc] if bank == 4 else rows[pc]
                stage = 'resident_audio' if bank == 4 else row.get('phase', row.get('stage'))
                if stage == 'slot_bridge' and q['copy'] <= pc < q['restore']:
                    stage = 'packet_copy'
            original_step()
            ticks = c.tstates-before
            if row:
                allowed = row['tstates']
                if ticks not in (allowed if isinstance(allowed, list) else [allowed]):
                    raise AssertionError(('listing timing differs', bank, pc, ticks, row))
                instruction = row['instruction']
            else:
                # Validate the actual decoder opcode, not the overwritten old
                # frame listing at the same fixed-memory address.
                instruction = 'opcode '+code[pc:pc+2].hex()
            key = bank, pc, ticks
            instructions[key] = dict(bank=bank, address=pc, tstates=ticks,
                                     stage=stage, instruction=instruction)
            hist[key] += 1; stages[stage] += ticks
            if c.pc == reader.STOP:
                frame_stages.append(dict(stages-previous)); previous.update(stages-previous)
                if len(frame_stages) % 250 == 0:
                    print(f'part {part}: {len(frame_stages)} exact packet calls', flush=True)

        c.step = step
        state['code'] = code
        return c, m, packets, digest

    with patch.object(reader, 'fixture', fixture):
        result = reader.run(directory, part, count=count, forced=False, stress=False)
    if len(result['frames']) != len(frame_stages): raise AssertionError('missing packet calls')
    for frame, stage in zip(result['frames'], frame_stages, strict=True):
        if sum(stage.values()) != frame['tstates']: raise AssertionError('packet sum differs')
        frame['stages'] = stage
    rows = [instructions[k] | dict(count=n, total=k[2]*n) for k, n in sorted(hist.items())]
    zx0_rows = [dict(pc=r['address'], tstates=r['tstates'], count=r['count'])
                for r in rows if r['stage'] == 'zx0']
    if validate_histogram(state['code'], 0, zx0_rows) != stages['zx0']:
        raise AssertionError('ZX0 timing sum differs')
    if sum(r['total'] for r in rows) != result['tstates'] or sum(stages.values()) != result['tstates']:
        raise AssertionError('instruction sum differs')
    m = state['metadata']
    result.update(stages=dict(stages), instruction_histogram=rows,
        expected_packets=state['packet_count'], complete=len(frame_stages)==state['packet_count'],
        metadata_sha256=sha((directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()),
        video_sectors=m['video_sectors'], reads=sum(f['rom_reads'] for f in result['frames']))
    if result['complete'] and result['reads'] != m['video_sectors']:
        raise AssertionError('not all video sectors read')
    prior = json.loads((ROOT/'resumable_packet_cpu.json').read_bytes())['volumes'][part-1]['baseline']
    for actual, expected in zip(result['frames'], prior['frames']):
        for key in ('frame', 'bytes', 'tstates', 'rom_reads'):
            if actual[key] != expected[key]: raise AssertionError(('prior prefix differs', part, key))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path,
        default=ROOT.parent/'.worktree/streaming-zx0-player/.tmp/inplace-keepalive-player')
    p.add_argument('--output', type=Path, default=ROOT/'packet_cpu_profile.json')
    p.add_argument('--limit', type=int)
    a = p.parse_args()
    if a.output.exists(): p.error('output already exists')
    if a.limit is not None and a.limit < 1: p.error('positive limit required')
    result = dict(complete=False, release=False, scope=__doc__, baseline_commit='a84451d',
                  player_cpu_delta_tstates=0, stream_delta_bytes=0, volumes=[])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save(): a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        for part in (1, 2, 3):
            v = profile(a.directory, part, a.limit or 100000)
            result['volumes'].append(v); save()
            print(json.dumps(dict(part=part, frames=len(v['frames']), tstates=v['tstates'], stages=v['stages'])), flush=True)
        sources = {Path(m.__file__).resolve() for m in tuple(sys.modules.values())
                   if getattr(m, '__file__', None) and Path(m.__file__).suffix == '.py'
                   and Path(m.__file__).resolve().parent == ROOT.resolve()}
        result.update(complete=all(v['complete'] for v in result['volumes']),
            frames=sum(len(v['frames']) for v in result['volumes']),
            tstates=sum(v['tstates'] for v in result['volumes']),
            source_sha256_lf={p.name:sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in sorted(sources)},
            reference_sha256=sha((ROOT/'resumable_packet_cpu.json').read_bytes()))
    except Exception as exc:
        result['failure'] = repr(exc); save(); raise
    save()


if __name__ == '__main__': main()
