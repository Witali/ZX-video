"""Recheck every archived block, overlap witness and complete native CPU report."""
import argparse
import bisect
import gzip
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
from benchmark_inplace_zx0 import CODE
from disk_layout import required_sectors
from inplace_zx0 import trace, layout, OverlapError
from probe_inplace_zx0 import packet_ends
from zx0_codec import decompress, emit_decoder

ROOT = Path(__file__).parent
OUTPUT = ROOT/'inplace_zx0_summary.json'


def audit():
    probe_path, cpu_path = ROOT/'inplace_zx0_probe.json', ROOT/'inplace_zx0_cpu.json'
    probe, cpu = [json.loads(p.read_bytes()) for p in (probe_path, cpu_path)]
    if not probe['complete'] or not cpu['complete'] or cpu['probe_sha256']!=sha(probe_path.read_bytes()):
        raise ValueError('incomplete/different host or CPU evidence')
    for report in (probe, cpu):
        for name, digest in report['source_sha256_lf'].items():
            if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))!=digest:
                raise ValueError(('changed source', name))
    a = MiniAssembler(CODE); emit_decoder(a, 'turbo'); code = a.resolve()
    summaries = []; cpu_variants = {v['block_bytes']:v for v in cpu['variants']}
    for variant in probe['variants']:
        size = variant['block_bytes']; volumes = []
        if not variant['complete'] or len(variant['volumes'])!=3: raise ValueError('incomplete variant')
        for volume, source in zip(variant['volumes'], probe['sources'], strict=True):
            part = volume['part']; filename = f'block{size}-part{part:02}.stream.gz'
            descriptor = next(v for v in probe['archives'] if v['file']==filename)
            packed = (ROOT/'inplace_zx0_evidence'/filename).read_bytes(); stream = gzip.decompress(packed)
            if (sha(packed)!=descriptor['sha256'] or sha(stream)!=descriptor['decoded_sha256']
                    or len(packed)!=descriptor['packed_bytes'] or len(stream)!=descriptor['decoded_bytes']
                    or sha(stream)!=volume['stream_sha256'] or len(stream)!=volume['stream_bytes']):
                raise ValueError('stream archive changed')
            at = 0; decoded = bytearray(); native_rows = None
            if size in cpu_variants:
                core = cpu_variants[size]['volumes'][part-1]; native_rows = core['blocks']
                if not core['complete'] or len(native_rows)!=len(volume['blocks']):
                    raise ValueError('incomplete native volume')
            for index, block in enumerate(volume['blocks']):
                n, count = struct.unpack_from('<HH', stream, at)
                payload = stream[at+4:at+4+count]; raw = decompress(payload, limit=n)
                expected, detail = trace(payload, limit=n)
                if raw!=expected or detail!=block['trace']: raise ValueError('byte trace differs')
                placement = layout(count, n, detail['minimum_input_start'], at)
                if (placement!=block['layout'] or sha(raw)!=block['raw_sha256']
                        or sha(payload)!=block['payload_sha256'] or block['index']!=index
                        or block['raw_start']!=len(decoded) or block['raw_end']!=len(decoded)+n
                        or block['stream_offset']!=at or n!=min(size, source['raw_video_bytes']-len(decoded))):
                    raise ValueError('block descriptor differs')
                if placement['sector_aligned_fits']:
                    repeated, _ = trace(payload, limit=n, input_start=placement['input_start'])
                    if repeated!=raw or not block['shared_memory_replay_exact']:
                        raise ValueError('shared memory differs')
                else:
                    if block['shared_memory_replay_exact']: raise ValueError('unsafe replay marked exact')
                    if placement['sector_span_bytes']<=16384:
                        try: trace(payload, limit=n, input_start=placement['input_start'])
                        except OverlapError: pass
                        else: raise ValueError('unsafe boundary no longer rejects')
                if native_rows is not None:
                    native = native_rows[index]
                    if (not native['exact'] or native['index']!=index or native['delta_tstates']!=0
                            or native['tstates']!=native['disjoint_tstates'] or native['code_bytes']!=len(code)
                            or native['code_sha256']!=sha(code) or native['input_start']!=placement['input_start']
                            or native['output_writes']!=n or native['input_reads']!=count
                            or any(native[k]!=detail[k] for k in ('minimum_input_start', 'write_input_cursors_sha256'))):
                        raise ValueError('native access trace differs from proven host trace')
                decoded += raw; at += 4+count
            if (at!=len(stream) or sha(decoded)!=source['raw_video_sha256']
                    or len(decoded)!=source['raw_video_bytes']):
                raise ValueError('complete video differs')
            ends = packet_ends(decoded, source['frames']); starts = [0]+ends[:-1]
            coverage = [max(0, bisect.bisect_right(ends, min(len(decoded), (i+3)*size))
                -bisect.bisect_left(starts, i*size)) for i in range(max(1, len(volume['blocks'])-2))]
            derived = dict(unsafe_exact_end_blocks=sum(not b['layout']['exact_end_fits'] for b in volume['blocks']),
                minimum_sector_slack=min(b['layout']['slack_bytes'] for b in volume['blocks']),
                maximum_footprint=max(b['trace']['minimum_footprint'] for b in volume['blocks']),
                shared_tail_copy_bytes=sum(b['layout']['carry_copy_bytes'] for b in volume['blocks']),
                initial_prefill_complete_frames=bisect.bisect_right(ends, min(len(decoded), 3*size)),
                minimum_complete_frames_in_three_slots=min(coverage))
            if any(volume[k]!=v for k,v in derived.items()): raise ValueError('derived buffer totals differ')
            sectors = (len(stream)+255)//256
            physical = required_sectors(sectors, source['video_start_sector']%16)
            used = source['used_sectors']+physical-source['video_physical_sectors']
            bad = sum(not b['layout']['sector_aligned_fits'] for b in volume['blocks'])
            if (sectors!=volume['video_sectors'] or physical!=volume['video_physical_sectors']
                    or used!=volume['used_sectors_if_bootstrap_unchanged']
                    or bad!=volume['unsafe_sector_layout_blocks']):
                raise ValueError('storage or safety totals differ')
            cpu_cost = None
            if native_rows is not None:
                cpu_cost = sum(b['tstates'] for b in native_rows)
                if cpu_cost!=core['tstates'] or core['output_bytes']!=len(decoded):
                    raise ValueError('native totals differ')
            volumes.append(dict(part=part, blocks=len(volume['blocks']), frames=source['frames'],
                video_bytes=len(stream), video_sectors=sectors, unsafe_blocks=bad,
                unsafe_exact_end_blocks=volume['unsafe_exact_end_blocks'],
                minimum_sector_slack=volume['minimum_sector_slack'],
                max_minimum_footprint=volume['maximum_footprint'],
                used_sectors_if_bootstrap_unchanged=used, free_sectors_if_bootstrap_unchanged=2544-used,
                shared_tail_copy_bytes=volume['shared_tail_copy_bytes'],
                initial_prefill_complete_frames=volume['initial_prefill_complete_frames'],
                minimum_complete_frames_in_three_slots=volume['minimum_complete_frames_in_three_slots'],
                naked_turbo_cpu_tstates=cpu_cost))
        if (sum(v['video_bytes'] for v in volumes)!=variant['stream_bytes']
                or sum(v['video_sectors'] for v in volumes)!=variant['video_sectors']
                or all(v['unsafe_blocks']==0 for v in volumes)!=variant['all_sector_layouts_safe']):
            raise ValueError('variant totals differ')
        summary = dict(block_bytes=size, ready_bytes=3*size, stream_bytes=variant['stream_bytes'],
            stream_delta_bytes=variant['stream_bytes']-sum(s['video_bytes'] for s in probe['sources']),
            video_sectors=variant['video_sectors'], all_sector_layouts_safe=variant['all_sector_layouts_safe'],
            volumes=volumes, native_cpu_complete=size in cpu_variants)
        if size in cpu_variants:
            cost = sum(v['naked_turbo_cpu_tstates'] for v in volumes)
            if cost!=cpu_variants[size]['tstates']: raise ValueError('CPU variant total differs')
            summary['naked_turbo_cpu_tstates'] = cost
        summaries.append(summary)
    return dict(complete=True, release=False, scope=__doc__, variants=summaries,
        probe_sha256=sha(probe_path.read_bytes()), cpu_sha256=sha(cpu_path.read_bytes()),
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
        player_changed=False, cadence_verified=False, new_bootstrap_measured=False,
        coroutine_and_sector_producer_verified=False, physical_drive_verified=False,
        limitations='Native totals are uninterrupted turbo decoding only. Sector-aligned input assumes '
            'header acquisition and preservation of the shared final sector before decoding. '
            'Conditional capacity holds the old bootstrap/code size and stream start fixed.')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    a = p.parse_args(); result = audit()
    if a.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps([{k:v for k,v in r.items() if k!='volumes'} for r in result['variants']]), flush=True)


if __name__ == '__main__': main()
