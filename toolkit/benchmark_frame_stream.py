"""Verify FAP1..FAP5 movie packets in one Z80/RAM instance.

Z80 reads packet headers, AY records, metadata and values from the ZX0 ring,
prepares native screens, then publishes them. Host startup installs Huffman
tables and supplies an ideal raw compressed ring. By default six actual AY
interrupts are manually run after every frame: exact data, not cadence.
With --cadence, real ISR code runs every 70908 T and a Z80 deadline loop
waits before publication; --lookahead decodes during idle fields. External
entry CALLs, disk, ULA and volume changes remain excluded in both modes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np
import ay_interrupt
from frame_stream_harness import Harness
from frame_output_pipeline import frames,display_screen
from cell_screen_z80 import expected_tstates as output_tstates
from frame_packet_stream import unpack
from probe_sparse_motion_cache import unpack as unpack_cache
from cell_audio_stream import unpack as unpack_audio, take_tick
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha
from benchmark_context_huffman import word
from build_long_video_trd import expand_compact_screen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','storage-report','cache','baseline','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--cadence', action='store_true', help='Run real 70908-T IRQ deadlines; ideal producer, no ULA/disk')
    p.add_argument('--lookahead', action='store_true', help='Decode 256-byte quanta during idle fields')
    p.add_argument('--zero-copy', action='store_true', help='Consume bulk vectors and native map in place')
    p.add_argument('--skip-noop-runs', action='store_true', help='Skip consecutive unchanged tiles in each stripe')
    p.add_argument('--constant-attribute-borders',action='store_true',help='Initialize constant rows once; copy only 576 attributes')
    p.add_argument('--black-borders',action='store_true',help='Initialize black borders once; draw only the central 18 cell rows')
    p.add_argument('--progress-frames',type=int,help='Enable the bar with this CURRENT DISK frame count; implies black borders')
    p.add_argument('--preview',type=Path,help='Save the final visible native screen as a PNG')
    args = p.parse_args()
    if args.progress_frames is not None:
        if not 1 <= args.progress_frames <= 16320: p.error('--progress-frames must be 1..16320')
        if not args.zero_copy: p.error('--progress-frames requires --zero-copy')
        args.black_borders = True
    if args.black_borders: args.constant_attribute_borders = True
    if args.lookahead and not args.cadence: p.error('--lookahead requires --cadence')
    raw = args.raw.read_bytes()
    bulk = raw[:4] in (b'FAP2',b'FAP3',b'FAP4',b'FAP5')
    stored_guards = raw[:4] not in (b'FAP3',b'FAP4',b'FAP5')
    encoded_noop_runs = 'inplace' if raw[:4] == b'FAP5' else raw[:4] == b'FAP4'
    if args.zero_copy and not bulk: p.error('--zero-copy requires FAP2..FAP5')
    if bulk:
        from bulk_frame_stream import unpack as unpack_bulk,read_packet as read_bulk_packet
    storage = json.loads(args.storage_report.read_text(encoding='utf-8'))
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    with np.load(args.states, allow_pickle=False) as saved: states = saved['states']
    if args.constant_attribute_borders and (not np.all(states[:,3072:3168] == 1)
            or not np.all(states[:,3744:3840] == 1)):
        raise ValueError('constant attribute border optimization requires rows 0..2 and 21..23 to stay 1')
    source = raw
    if encoded_noop_runs:
        from vector_run_stream import transcode,encode_vectors
        source = transcode(raw,inverse=True)[0]
    cells = unpack_audio(unpack_cache(unpack(unpack_bulk(source) if bulk else source), 32, 4))[0]
    tables, mapping, packets = frames(cells)
    r = Reader(raw); _, _, count, _, _ = read_header(r, magic=raw[:4])
    if args.progress_frames is not None and (args.limit or count) > args.progress_frames:
        p.error('benchmark would cross the supplied disk boundary; set --limit to its frame count or less')
    if (not storage['complete'] or storage['input_sha256'] != sha(raw) or not baseline['complete']
            or baseline['states_sha256'] != sha(states.tobytes()) or len(states) != count
            or baseline['stream_sha256'] != sha(cells)):
        raise ValueError('inconsistent benchmark inputs')
    ring, ends, position = bytearray(), [0], 0
    for b in storage['blocks']:
        data = raw[position:position+b['decoded_bytes']]; position += len(data); ends.append(position)
        payload = (args.cache/(b['sha256']+'.zx0')).read_bytes()
        if sha(data) != b['sha256'] or len(payload) != b['zx0_bytes']: raise ValueError('wrong cached block')
        ring += struct.pack('<HH', len(data), len(payload))+payload
    if position != len(raw): raise ValueError('incomplete block coverage')
    h = Harness(bytes(ring), tables, mapping, count,bulk=bulk,zero_copy=args.zero_copy,
        skip_noop_runs=args.skip_noop_runs,stored_guards=stored_guards,
        constant_attribute_borders=args.constant_attribute_borders,skip_black_borders=args.black_borders,
        progress_frames=args.progress_frames,encoded_noop_runs=encoded_noop_runs)
    header_result = h.consume_header(raw[:r.pos]); h.histogram.clear()
    clock = None
    all_ticks = []
    if args.cadence:
        from frame_clock_harness import Clock
        ar = Reader(raw); read_header(ar,magic=raw[:4])
        for _ in range(count):
            if bulk:
                all_ticks.extend(read_bulk_packet(ar,stored_guards=stored_guards)[1]['ticks'])
            else:
                all_ticks.extend(take_tick(ar) for _ in range(6))
                _, ml, coded, lit = struct.unpack('<BHHH',ar.take(7))
                ar.take(3+192+ml+80+coded+lit)
        ar.end()
    report = dict(scope=__doc__, complete=False, baseline_commit='2f8535e' if encoded_noop_runs else '7608922' if h.progress else '8706cc0' if args.black_borders else '469402c' if args.constant_attribute_borders else '17f079c' if not stored_guards else
        ('8390053' if args.skip_noop_runs else 'a875d18') if bulk else '1963bab', frames_expected=count,
        raw_sha256=sha(raw), states_sha256=sha(states.tobytes()), frames=[], header_results=header_result,
        code_regions=[dict(base=base,code_hex=data.hex()) for base,data in h.regions],
        packet_labels=h.p, reader_labels=h.r, decoder_labels=h.z, audio_labels=h.audio,
        instruction_listing=list(h.instructions.values()), timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        release=False, disk_delivery_verified=False, cadence_verified=False, cadence_requested=args.cadence,
        lookahead=args.lookahead,bulk_packet=bulk,zero_copy=args.zero_copy,skip_noop_runs=args.skip_noop_runs,
        format=raw[:4].decode(),stored_guards=stored_guards,encoded_noop_runs=encoded_noop_runs,
        constant_attribute_borders=args.constant_attribute_borders,black_borders=args.black_borders,cold_init=h.frame.init_result,
        cold_init_code_hex=h.frame.init_code.hex(),progress_frames_on_disk=args.progress_frames,
        progress_labels=h.progress,progress_init=h.progress_init_result)
    for i, expected in enumerate(states[:args.limit or count]):
        if bulk:
            _, detail = read_bulk_packet(r,stored_guards=stored_guards)
            ticks,flags,ml,coded,lit = (detail[n] for n in ('ticks','flags','mask_bytes','coded_bytes','literal_bytes'))
            cache_map = detail['cache']
            value_base = 0xa6a0+detail['coded_offset']
        else:
            ticks = [take_tick(r) for _ in range(6)]
            flags, ml, coded, lit = struct.unpack('<BHHH', r.take(7))
            body = r.take(3+192+ml+80+coded+lit)
            cache_map,value_base = body[:3],0xa6a0
        try:
            if args.cadence and i:
                prepared = clock.play_one()
                published = dict(tstates=0,stages={},irq_tstates=0)
            else:
                prepared = h.prepare()
                if args.cadence:
                    clock = Clock(h,all_ticks,lookahead=args.lookahead)
                    published = clock.start()
                    report['clock'] = dict(code_hex=clock.code.hex(),labels=clock.labels,listing=clock.listing)
                else:
                    published = h.publish()
        except (AssertionError,RuntimeError) as exc:
            report['failure'] = dict(frame=i,error=str(exc),tstates=h.cpu.tstates,pc=h.cpu.pc,
                fields=word(h.cpu,h.audio['elapsed_fields']),played_ticks=clock.ticks if clock else None)
            if clock: report['publications'] = clock.publications
            args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            raise
        group, native = packets[i]; cpu = h.cpu
        current = bytes(cpu.read8(0x6400+j) for j in range(3840))
        if current != expected.tobytes(): raise AssertionError(('compact frame differs', i))
        target = 7 if i % 2 == 0 else 5
        h.expected_screens[target] = display_screen(current,black_borders=args.black_borders)
        if h.progress:
            from disk_progress_z80 import reference_screen
            h.expected_screens = {bank:reference_screen(screen,i+1,args.progress_frames)
                for bank,screen in h.expected_screens.items()}
        for bank, wanted in h.expected_screens.items():
            if bytes(cpu.banks[bank][:6912]) != wanted: raise AssertionError(('native screen differs', i, bank))
        consumed = ends[h.blocks-1]+word(cpu,h.r['position'])
        bits = (word(cpu,h.frame.recon['source'])-value_base)*8+(cpu.read8(h.frame.recon['bit_page']) & 7)
        if (consumed != r.pos or bits != group[2]
                or word(cpu,h.frame.recon['literal_source']) != value_base+coded+stored_guards+lit):
            raise AssertionError(('packet/bit/literal cursor differs', i))
        vector_base = word(cpu,h.frame.w['vector_pointer']) if args.zero_copy else 0xa400
        native_base = word(cpu,h.frame.w['native_pointer']) if args.zero_copy else 0x7300
        vectors = group[3]
        if encoded_noop_runs:
            # Validate the actual command choices, including unencoded short
            # runs; no implicit threshold is substituted by the benchmark.
            from vector_run_stream import decode_vectors
            offset = sum(map(len,ticks))+8
            vectors = detail['payload'][offset:offset+192]
            if decode_vectors(vectors,group[4],inplace=encoded_noop_runs == 'inplace')[0] != group[3]:
                raise AssertionError('vector commands changed predictions')
        checks = ((vector_base, vectors), (0xa4c0,group[4]+group[5]), (native_base,native),
            (0xba40,cache_map), (value_base,group[6]+(b'\0' if stored_guards else b'')+group[7]+b'\0'))
        if bulk: checks += ((0xa6a0,detail['payload']),)
        for first, wanted in checks:
            if bytes(cpu.read8(first+j) for j in range(len(wanted))) != wanted:
                raise AssertionError(('parsed input differs',i,first))
        if bytes(cpu.banks[5][0x1b00:0x2400]) != b'\xa5'*0x900: raise AssertionError('TR-DOS workspace changed')
        old_page = cpu.port_7ffd; cpu.port_7ffd = (old_page & ~7) | 6
        for first, wanted in h.frame.protected_regions:
            if bytes(cpu.read8(first+j) for j in range(len(wanted))) != wanted:
                raise AssertionError(('protected tables differ', i, first))
        cpu.port_7ffd = old_page
        stages = Counter(prepared['stages']); stages.update(published['stages'])
        if h.progress:
            from disk_progress_z80 import expected_tick_tstates
            old_steps,new_steps = i*64//args.progress_frames,(i+1)*64//args.progress_frames
            if stages['progress'] != expected_tick_tstates(old_steps,new_steps):
                raise AssertionError(('progress timing differs',i))
        old = baseline['frames'][i]['stages']
        for stage in ('metadata','reconstruct','output'):
            delta = 0
            if stage == 'reconstruct' and args.skip_noop_runs:
                from causal_tile_z80 import noop_run_delta_tstates
                delta = noop_run_delta_tstates(group[3],group[4])
            if stage == 'reconstruct' and encoded_noop_runs:
                from causal_tile_z80 import encoded_run_delta_tstates
                delta = encoded_run_delta_tstates(group[3],group[4],commands=vectors,
                    inplace=encoded_noop_runs == 'inplace',scan_uncoded=args.skip_noop_runs)
            if stage == 'output':
                delta = output_tstates(native,fast_mask_dispatch=True,
                    constant_attribute_borders=args.constant_attribute_borders,skip_black_borders=args.black_borders
                    )-output_tstates(native,fast_mask_dispatch=True)
            if stages[stage] != old[stage]+delta: raise AssertionError(('stage timing differs',i,stage))
        if stages['handoff'] != old['handoff']+10+6*bulk+12*args.zero_copy: raise AssertionError('wrapper timing differs')
        if stages['audio'] != 1705+42*sum(t[0] for t in ticks)+(42 if args.cadence and i == 0 else 0):
            raise AssertionError('AY enqueue timing differs')
        irq = (prepared['irq_tstates']+published['irq_tstates']) if args.cadence else h.drain_six(ticks)
        total = prepared['tstates']+published['tstates']
        report['frames'].append(dict(index=i,tstates=total,stages=dict(stages),irq_tstates=irq,
            reconstruction_delta_tstates=stages['reconstruct']-old['reconstruct'],
            idle_tstates=prepared.get('idle_tstates',0)+published.get('idle_tstates',0),
            consumed_raw_bytes=consumed,consumed_ring_bytes=cpu.consumed,
            baseline_video_tstates=baseline['frames'][i]['total_tstates'],
            added_input_audio_bridge_tstates=total-baseline['frames'][i]['total_tstates']))
        if i % 100 == 0:
            if clock: report['publications'] = clock.publications
            args.output.write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
            print(f'Integrated {raw[:4].decode()} Z80 checked frame {i+1}/{count}',flush=True)
    complete = len(report['frames']) == count
    if complete:
        r.end()
        if clock:
            histogram = h.histogram.copy()
            report['final_audio_drain'] = clock.drain()
            h.histogram = histogram
        if cpu.consumed != len(ring) or word(cpu,h.audio['audio_ticks_played']) != count*6:
            raise AssertionError('incomplete stream/AY consumption')
    total_stages = Counter()
    for row in report['frames']: total_stages.update(row['stages'])
    counts = [row['tstates'] for row in report['frames']]
    report['summary'] = dict(frames=len(counts),total_tstates=sum(counts),stages=dict(total_stages),
        mean_tstates=sum(counts)/len(counts),max_tstates=max(counts),worst_frame=counts.index(max(counts)),
        frames_above_425448=sum(t>425448 for t in counts),
        irq_tstates=sum(row['irq_tstates'] for row in report['frames']),
        unchanged_video_except_wrapper=not (args.skip_noop_runs or args.constant_attribute_borders),
        exact_pixels_and_ay=not args.black_borders,exact_active_pixels_and_ay=True,
        exact_compact_states=True,black_borders=args.black_borders,progress_frames_on_disk=args.progress_frames,
        constant_attribute_output_delta_tstates=-3240*len(counts)*args.constant_attribute_borders,
        reconstruction_delta_tstates=sum(row['reconstruction_delta_tstates'] for row in report['frames']),
        added_ret_tstates=10*len(counts),
        added_dynamic_source_tstates=6*len(counts)*bulk,
        added_dynamic_metadata_tstates=12*len(counts)*args.zero_copy)
    report['instruction_histogram'] = [dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())]
    if sum(r['tstates']*r['count'] for r in report['instruction_histogram']) != sum(counts):
        raise AssertionError('full instruction histogram differs')
    report['complete'] = complete
    if clock:
        report['publications'] = clock.publications
        late = [row['late_fields'] for row in clock.publications]
        report['summary'].update(late_frames=sum(bool(n) for n in late),max_late_fields=max(late),
            played_ay_ticks=clock.ticks,ideal_clock_irq_tstates=clock.irq_tstates,ideal_clock_idle_tstates=clock.idle_tstates)
        report['cadence_verified'] = complete and not any(late)
    if args.preview:
        from PIL import Image
        from build_long_video_trd import base
        native = bytes(cpu.banks[7 if cpu.port_7ffd & 8 else 5][:6912])
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(base.render_spectrum_screen(native[:6144],native[6144:])).resize((512,384),
            Image.Resampling.NEAREST).save(args.preview)
        report['preview'] = dict(path=args.preview.as_posix(),sha256=sha(args.preview.read_bytes()),
            source='actual Z80 visible-screen RAM',frame=len(report['frames'])-1)
    args.output.write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__': main()
