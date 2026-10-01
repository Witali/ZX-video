"""Generic CB41/LZSA2 disk assembly using the verified native movie player."""
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

from build_fap3_trd import Builder as LegacyBuilder, player_harness, sha
from cell_codebook_player import Builder
from convert_video import write_json
from generic_cell_codebook import representation, row_partitions, row_sets
from inplace_zx0 import layout
from measure_cell_codebook_movie import audio_size
from probe_adaptive_block_codecs import ExternalCodec
from row_dictionary_video import reference_tables
import lzsa2_stream


# The passing 9885483 movie profile; automatically selected as a unit.
# This changes no native instruction or its absolute T-state count.
OPTIONS = dict(fast_disk=True, cached_seek=True, interleaved=True,
    deferred_limit=248, keepalive_fields=64, frame_service=True, cold_bitmaps=True,
    inline_matches=True, startup_delta=False, fast_noop_scan=True,
    irq_safe_paging=True, static_cache_borders=True, carry_huffman=True,
    register_fragments=True, cached_huffman_byte=True, bank2_zx0=True,
    fast_return_irq=True, hl_mask_reader=True, compact_cursor=True,
    cached_huffman_lookahead=True, audio_batch=31, foreground_audio=True)
WINDOW = 32
VIDEO_BUDGET = (2544-160)*256


def video_encoder(dynamic_rows=False,front_reuse=False):
    if front_reuse:
        from front_cell_reuse import representation as selected
    elif dynamic_rows:
        from dynamic_row_dictionary import representation as selected
    else:selected=representation
    return selected


def pack_blocks(raw, codec, cache):
    stream, blocks = bytearray(), []
    for lo in range(0, len(raw), 15872):
        data = raw[lo:lo+15872]
        payload = codec.encode_verified(data, None, cache)
        exact, proof = lzsa2_stream.trace(payload, limit=len(data))
        space = layout(len(payload), len(data), proof['minimum_input_start'], len(stream))
        if exact != data or not space['sector_aligned_fits']:
            raise ValueError('CB41 LZSA2 block exceeds safe native in-place capacity')
        lzsa2_stream.trace(payload, limit=len(data), input_start=space['input_start'])
        blocks.append(dict(raw_start=lo, raw_end=lo+len(data), decoded_bytes=len(data),
            compressed_bytes=len(payload), codec='lzsa2', sha256=sha(data),
            inplace_proof=proof, inplace_layout=space))
        stream += struct.pack('<HH', len(data), len(payload))+payload
    return bytes(stream), blocks


def plan_volumes(frames, audio, labels, codec, cache, max_frames, frame_fields=6, target_volumes=None,
                 volume_cuts=None, dynamic_rows=False, audio_banks=1,front_reuse=False):
    """Measure short windows once; choose cuts without building candidate sets.

    Exact row unions include both histories. Window byte costs select an
    initial size partition; exact resident AY sizes may split it further.
    Final TRD capacity is a separate gate, never inferred from this estimate.
    """
    sets = row_sets(frames)
    audio_options=dict(frame_fields=frame_fields)
    if audio_banks!=1:audio_options['audio_banks']=audio_banks
    dynamic_rows=dynamic_rows or front_reuse
    represent=video_encoder(dynamic_rows,front_reuse)
    if volume_cuts is not None:
        if target_volumes is not None:
            raise ValueError('explicit cuts and balanced target are mutually exclusive')
        ends = [0]+list(volume_cuts)
        if ends[-1] != len(frames) or any(not 0 < b-a <= max_frames for a,b in zip(ends,ends[1:])):
            raise ValueError('explicit cuts must cover every frame once, ending at EOF')
        parts, probes = [], []
        for lo, hi in zip(ends,ends[1:]):
            rows = len({0}.union(*sets[max(0,lo-2):hi]))
            if rows > 256 and not dynamic_rows: raise ValueError(f'explicit volume {lo}..{hi} needs {rows} rows')
            coded, report = audio_size(audio,lo,hi,labels,**audio_options)
            if not report['resident_fits']: raise ValueError('explicit volume exceeds resident audio bank')
            parts.append(dict(start=lo,end=hi,audio=coded,audio_report=report))
            probes.append(dict(start=lo,end=hi,rows=rows,**report))
        return parts, dict(method='explicit cuts after bounded timing diagnosis', boundaries=ends,
            audio_probes=probes, windows=[], candidate_disk_sets_built=0,
            final_disk_capacity_verified=False, minimum_volume_count_claimed=False, quality_reduced=False)
    row_parts = [dict(start=lo,end=min(len(frames),lo+max_frames),row_limit='dynamic')
                 for lo in range(0,len(frames),max_frames)] if dynamic_rows else row_partitions(sets,max_frames)
    all_costs = []
    windows, initial = [], []
    for part in row_parts:
        start, stop = part['start'], part['end']
        costs = []
        for lo in range(start, stop, WINDOW):
            hi = min(lo+WINDOW, stop)
            probe = represent(frames, lo, hi)
            stream, _ = pack_blocks(probe['raw'], codec, cache)
            # Charging every local header is intentionally conservative. The
            # final volume has only one book. This is not an optimal partition.
            costs.extend([len(stream)/(hi-lo)]*(hi-lo))
            windows.append(dict(start=lo, end=hi, raw_sha256=probe['raw_sha256'],
                bytes=len(stream), stream_sha256=sha(stream), host_screens_exact=True))
        lo, amount = start, 0
        for index, cost in enumerate(costs, start):
            if index > lo and amount+cost > VIDEO_BUDGET:
                initial.append((lo, index))
                lo, amount = index, 0
            amount += cost
        initial.append((lo, stop))
        all_costs.extend(costs)
    balance = None
    if target_volumes is not None:
        from balance_cb41_cadence import three_parts,balanced_parts
        if target_volumes==3 and not dynamic_rows:
            initial,balance=three_parts(sets,all_costs,max_frames)
        else:
            initial,balance=balanced_parts(all_costs,max_frames,target_volumes,
                sets=None if dynamic_rows else sets)
    parts, audio_probes = [], []

    def add(lo, hi):
        coded, report = audio_size(audio, lo, hi, labels, **audio_options)
        audio_probes.append(dict(start=lo, end=hi, **report))
        if not report['resident_fits']:
            if hi-lo == 1:
                raise ValueError(f'frame {lo}: AY data cannot fit the resident bank')
            mid = (lo+hi)//2
            add(lo, mid)
            add(mid, hi)
        else:
            parts.append(dict(start=lo, end=hi, audio=coded, audio_report=report))

    for lo, hi in initial:
        add(lo, hi)
    if len(parts) > 65534:
        raise ValueError('CB41 exceeds the disk-change volume ordinal limit')
    report = dict(method='32-frame exact local probes plus row/AY constraints',
        window_frames=WINDOW, estimated_video_budget_bytes=VIDEO_BUDGET,
        estimated_startup_reserve_sectors=160, windows=windows,
        row_partitions=row_parts, audio_probes=audio_probes,
        boundaries=[0]+[p['end'] for p in parts],
        candidate_disk_sets_built=0, final_disk_capacity_verified=False,
        minimum_volume_count_claimed=False, quality_reduced=False)
    if balance is not None: report['balanced_target'] = balance
    return parts, report


def build(frames, audio, raw, compact, args, executables, output, manifest):
    """Build once and verify at the requested level; retain failures in reports."""
    work = output/'work'
    frame_fields = getattr(args, 'frame_fields', 6)
    if len(audio) != len(frames)*frame_fields:
        raise ValueError('video and AY durations differ')
    cache = work/'lzsa'; cache.mkdir()
    codec = ExternalCodec('lzsa2', Path(executables['lzsa']), Path(executables['lzsa']),
                          'user-supplied executable; exact hash recorded')
    scaffold = LegacyBuilder(raw, compact, Path(executables['zx0']), work/'zx0')
    # Resolve the real audio ABI, rather than borrowing labels from a movie.
    labels = player_harness(bytes(4), scaffold.tables, scaffold.mapping, 1).audio
    front_reuse=getattr(args,'front_reuse',False)
    dynamic_rows=getattr(args,'dynamic_rows',False) or front_reuse
    audio_banks=getattr(args,'audio_banks',1)
    represent=video_encoder(dynamic_rows,front_reuse)
    parts, plan = plan_volumes(frames, audio, labels, codec, cache, args.max_frames_per_disk,
        frame_fields, getattr(args,'target_volumes',None), getattr(args,'volume_cuts',None),dynamic_rows,audio_banks,front_reuse)
    only = getattr(args,'only_volume',None)
    if only is not None and not 1 <= only <= len(parts): raise ValueError('invalid selected volume')
    write_json(output/'partition.json', plan)
    ends = [p['end'] for p in parts]
    identity_options=dict(options=OPTIONS, ends=ends, frame_fields=frame_fields)
    if dynamic_rows:identity_options['dynamic_rows']=True
    if front_reuse:identity_options['front_reuse']=True
    if audio_banks!=1:identity_options['audio_banks']=audio_banks
    identity = sha(frames.tobytes()+b''.join(f.serialize() for f in audio)
                   +json.dumps(identity_options, sort_keys=True).encode())
    fingerprint = (b'CB44GEN1' if front_reuse else b'CB42GEN1' if dynamic_rows else b'CB41GEN1')+bytes.fromhex(identity)[:6]
    records = []
    timing = dict(complete=False, release=False, all_nominal_deadlines_met=False,
        player_hot_path_changed=frame_fields!=6, player_hot_path_delta_tstates=0,
        unchanged_native_baseline='9885483', disks=[])
    if dynamic_rows:
        timing.update(player_hot_path_changed=True,player_hot_path_delta_tstates=None,
            ordinary_packet_delta_tstates=18,renderer_delta_tstates=0)
    if audio_banks==2:
        timing.update(player_hot_path_changed=True,player_hot_path_delta_tstates=None,
            audio_banks=[4,6],audio_refill_bridge_normal_delta_tstates=50)
    if front_reuse:timing.update(front_reuse=True,renderer_delta_tstates=None)
    write_json(output/'timing.json', timing)
    for number, part in enumerate(parts, 1):
        if only is not None and number != only: continue
        lo, hi = part['start'], part['end']
        print(f'CB41 disk {number}/{len(parts)}: frames {lo}..{hi-1}', flush=True)
        chosen = represent(frames, lo, hi)
        stem = f'{args.prefix}_part{number:02}'
        folder = work/stem; folder.mkdir()
        (folder/'codebook.raw').write_bytes(chosen['raw'])
        (folder/'audio.ayh1').write_bytes(part['audio'])
        write_json(folder/'rows.json', chosen['rows'])
        # The inherited metadata/reference API uses global frame indices.
        if dynamic_rows:
            states=frames
            builder_states=np.zeros((len(frames),3840),dtype=np.uint8)
            builder_states[:,3072:]=frames[:,3840:]
            write_json(folder/'dynamic-rows.json',dict(frames=chosen['details'],
                proof=chosen['dynamic_proof'],updates=chosen['row_updates'],
                unique_literal_rows=chosen['unique_literal_rows']))
        else:
            states = np.zeros((len(frames), 3840), dtype=np.uint8)
            states[chosen['first']:hi] = chosen['states']
            builder_states=states
        np.savez_compressed(folder/'states.npz', states=states)
        packed, blocks = pack_blocks(chosen['raw'], codec, cache)
        (folder/'codebook.stream').write_bytes(packed)
        with reference_tables(chosen['rows']):
            builder = Builder(raw, builder_states, Path(executables['zx0']), work/'zx0',
                row_dictionary=chosen['rows'], lzsa=Path(executables['lzsa']),
                series_fingerprint=fingerprint, cell_raw=chosen['raw'], cell_start=lo,
                frame_fields=frame_fields,reference_frames=frames if dynamic_rows else None, **OPTIONS)
            builder.ends = ends
            builder.inplace_streams[lo, hi] = packed, blocks
            builder.resident_streams[lo, hi] = b'', part['audio']
            image, metadata = builder.volume(lo, hi, number)
            write_json(output/(stem+'.json'), metadata)
            if image is None:
                raise ValueError(f'CB41 disk {number} needs {metadata["used_sectors"]} sectors; '
                    'maximum 2544. Local-window size estimate was insufficient. '
                    'Retry with a smaller --max-frames-per-disk; no image/frame/quality was truncated.')
            (output/(stem+'.trd')).write_bytes(image)
            record = dict(file=stem+'.trd', metadata=stem+'.json', frames=hi-lo,
                frame_start=lo, frame_end_exclusive=hi, used_sectors=metadata['used_sectors'],
                free_sectors=metadata['free_sectors'], sha256=sha(image),
                states=str((folder/'states.npz').relative_to(output)).replace('\\', '/'),
                host_screens_exact=True, row_entries=chosen['rows']['entries'])
            records.append(record)
            write_json(output/'volumes.json', records)
            checked = dict(file=record['file'], frames=hi-lo)
            if args.verify != 'none':
                from build_integrated_bootstrap import check_cold
                from build_cell_codebook_trd import verify
                checked['cold'] = check_cold(image, metadata, builder.expected_banks)
                # Full Fuse screen passes cover the complete real execution.
                # Keep instruction replay for CPU-only mode and short fixtures;
                # replaying long movies as well would duplicate that coverage.
                if args.verify == 'cpu' or hi-lo <= 64:
                    cpu = verify(image, metadata, states)
                    write_json(folder/'cpu.json', cpu)
                    checked.update(cpu_complete=cpu['complete'],
                        cpu_all_native_screens_exact=cpu['all_native_screens_exact'],
                        cpu_report=str((folder/'cpu.json').relative_to(output)).replace('\\', '/'))
                else:
                    checked['instruction_replay'] = 'Covered by unchanged-kernel fixtures; all movie screens checked in Fuse'
        if args.verify == 'fuse':
            common = ['--fuse', str(args.fuse.resolve()), '--trd', str(output/record['file']),
                '--metadata', str(output/record['metadata']), '--states', str(folder/'states.npz'),
                '--timeout', str(args.verification_timeout)]
            subprocess.run([sys.executable, str(Path(__file__).with_name('measure_fap3_fuse.py')),
                *common, '--raw', str(work/'stream.raw'), '--output', str(folder/'timing.json')], check=True)
            subprocess.run([sys.executable, str(Path(__file__).with_name('capture_cell_codebook_full.py')),
                *common, '--timing', str(folder/'timing.json'), '--work', str(folder/'captures'),
                '--output', str(folder/'screens.json')], check=True)
            from profile_fap3 import summarize_fuse
            measured = json.loads((folder/'timing.json').read_bytes())
            checked['disk_timing'] = summarize_fuse(measured)
            checked['full_fuse_screens_exact'] = json.loads((folder/'screens.json').read_bytes())['full_screens_exact']
        timing['disks'].append(checked)
        write_json(output/'timing.json', timing)
    if args.verify != 'none' and len(records) > 1:
        from test_fap3_disk import verify_swaps
        verify_swaps(output, output/'disk-swaps.json')
    plan['final_disk_capacity_verified'] = only is None
    plan['final_disk_sets_built'] = int(only is None)
    plan['verified_volume_indices'] = [only] if only is not None else list(range(1,len(parts)+1))
    write_json(output/'partition.json', plan)
    timing['complete'] = args.verify != 'none'
    timing['all_nominal_deadlines_met'] = args.verify == 'fuse' and all(
        d['disk_timing']['nominal_deadlines_met'] and d['full_fuse_screens_exact'] for d in timing['disks'])
    if args.verify == 'none':
        timing['reason'] = 'Native CPU and disk measurements skipped by --verify none'
    write_json(output/'timing.json', timing)
    manifest.update(volumes=records, frames=len(frames), ay_ticks=len(audio),
        duration_seconds=len(frames)*frame_fields/50, timing_verified=timing['all_nominal_deadlines_met'],
        stream_sha256=sha(raw), five_states_sha256=sha(frames.tobytes()),
        compression=codec.identity, native_options=OPTIONS,
        independently_bootable=True, brightness_levels=5,
        player_baseline='9885483', player_hot_path_changed=frame_fields!=6, player_hot_path_delta_tstates=0)
    if dynamic_rows:
        manifest.update(dynamic_row_dictionary=True,wire='CB42',player_hot_path_changed=True,
            player_hot_path_delta_tstates=None,
            cycle_note='Ordinary packet +18 T; renderer 0 T delta; row controls measured separately')
    if audio_banks==2:manifest.update(audio_banks=[4,6],audio_wire='AYB1',player_hot_path_changed=True,player_hot_path_delta_tstates=None)
    if front_reuse:manifest.update(front_reuse=True,wire='CB44',cycle_note='Counted CB44 mode reader and front copy; data-dependent timing')
    if only is not None:
        manifest.update(whole_movie=False, selected_volume=only, source_movie_frames=len(frames),
                        frames=sum(r['frames'] for r in records), ay_ticks=sum(r['frames'] for r in records)*frame_fields,
                        duration_seconds=sum(r['frames'] for r in records)*frame_fields/50)
    return records
