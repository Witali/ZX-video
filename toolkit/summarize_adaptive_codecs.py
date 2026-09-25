"""Check saved adaptive-codec evidence and print a compact, reproducible summary."""
import json
from pathlib import Path

import bank_local_zx0
from benchmark_adaptive_zx0 import choose_cpu, stream_capacity
from probe_adaptive_block_codecs import CODECS, geometry, sha, summarize_volume


def summarize(directory):
    storage_path = directory/'adaptive_block_codecs_storage.json'
    cpu_path = directory/'adaptive_zx0_cpu.json'
    storage = json.loads(storage_path.read_bytes())
    cpu = json.loads(cpu_path.read_bytes())
    if not storage['complete'] or not cpu['complete']:
        raise ValueError('partial experiment')
    if cpu['storage_report_sha256'] != sha(storage_path.read_bytes()):
        raise ValueError('storage evidence hash changed')
    if cpu['decoder_code_sha256'] != sha(bank_local_zx0.build(dynamic_input=True)[0]):
        raise ValueError('measured decoder differs from current code')
    for filename, expected in (
            ('probe_adaptive_block_codecs.py', storage['provenance']['probe_sha256']),
            ('benchmark_adaptive_zx0.py', cpu['probe_sha256'])):
        if sha((directory/filename).read_bytes()) != expected:
            raise ValueError(f'{filename} differs from measured version')
    if len(storage['volumes']) != 3 or len(cpu['volumes']) != 3:
        raise ValueError('three volumes required')
    totals = dict(blocks=0, pc_verified_variants=0, executed_cpu_variants=0,
                  baseline_cpu=dict(decoder_tstates=0, producer_tstates=0, total_cpu_tstates=0),
                  candidates={name: 0 for name in CODECS}, selections={}, volumes=[])
    for source, measured in zip(storage['volumes'], cpu['volumes']):
        if not source['complete'] or not measured['complete']:
            raise ValueError('incomplete volume')
        for name in ('part', 'trd_sha256', 'stream_sha256', 'blocks_expected'):
            if source[name] != measured[name]:
                raise ValueError('CPU/storage volume mismatch')
        count = source['blocks_expected']
        if len(source['blocks']) != count or len(measured['blocks']) != count:
            raise ValueError('incomplete block coverage')
        old = source['summary']
        summarize_volume(source)
        if source['summary'] != old:
            raise ValueError('storage summary does not reproduce')
        options = []
        for index, (raw, block) in enumerate(zip(source['blocks'], measured['blocks'])):
            if raw['index'] != index or block['index'] != index or raw['decoded_sha256'] != block['decoded_sha256']:
                raise ValueError('block identity mismatch')
            group = []
            for name, result in block['variants'].items():
                if not result['executed']:
                    continue
                packed = raw['candidates'][name]
                if result['payload_sha256'] != packed['sha256'] or result['bytes'] != packed['bytes']+4:
                    raise ValueError('CPU payload mismatch')
                group.append(dict(name=name, bytes=result['bytes'], tstates=result['tstates']))
            if not any(row['name'] == 'zx0' for row in group):
                raise ValueError('baseline CPU not measured')
            options.append(group)
            totals['executed_cpu_variants'] += len(group)
        original = old['candidates']['zx0']
        base = measured['producer_checks']['baseline']
        for key in totals['baseline_cpu']:
            totals['baseline_cpu'][key] += base[key]
        volume = dict(part=source['part'], blocks=count,
                      budget_bytes=measured['budget_above_baseline_bytes'], selections={})
        base_ticks = sum(block['variants']['zx0']['tstates'] for block in measured['blocks'])
        if base_ticks != measured['baseline_decoder_tstates'] or base_ticks != base['decoder_tstates']:
            raise ValueError('baseline decoder total differs')
        for name, result in measured['selections'].items():
            used = original['fixed_bootstrap_used_sectors'] if name == 'no_extra_sectors' else 2544
            limit = stream_capacity(source['video_start_sector'], used)
            optimal = choose_cpu(options, limit)
            if any(result[key] != value for key, value in optimal.items()):
                raise ValueError('CPU selection is not reproducible')
            geom = geometry(result['stream_bytes'], source['video_start_sector'])
            if any(result[key] != value for key, value in geom.items()):
                raise ValueError('selected geometry differs')
            actual = measured['producer_checks'][name]
            if 'reuses' in actual:
                actual = measured['producer_checks'][actual['reuses']]
            if (actual['decoder_tstates'] != result['decoder_tstates']
                    or actual['sector_reads'] != geom['logical_video_sectors']
                    or not actual['sectors_exact_once_in_original_order']
                    or actual['stream_bytes'] != result['stream_bytes']):
                raise ValueError('producer/selection mismatch')
            volume['selections'][name] = dict(
                blocks_changed=sum(value != 'zx0' for value in result['selected_codecs']),
                bytes=result['stream_bytes'], delta_bytes=result['delta_bytes'],
                decoder_tstates=actual['decoder_tstates'], delta_decoder_tstates=result['delta_decoder_tstates'],
                producer_tstates=actual['producer_tstates'], delta_producer_tstates=actual['producer_tstates']-base['producer_tstates'],
                total_cpu_tstates=actual['total_cpu_tstates'], delta_total_cpu_tstates=actual['total_cpu_tstates']-base['total_cpu_tstates'],
                sector_reads=actual['sector_reads'], delta_sector_reads=actual['sector_reads']-base['sector_reads'],
                fixed_bootstrap_used_sectors=geom['fixed_bootstrap_used_sectors'])
        totals['volumes'].append(volume)
        totals['blocks'] += count
        totals['pc_verified_variants'] += sum(len(row['candidates']) for row in source['blocks'])
        for name in CODECS:
            totals['candidates'][name] += old['candidates'][name]['stream_bytes']
        for name, row in old['size_selections'].items():
            entry = totals['selections'].setdefault(name, dict(bytes=0, fixed_bootstrap_used_sectors=0))
            entry['bytes'] += row['stream_bytes']
            entry['fixed_bootstrap_used_sectors'] += row['fixed_bootstrap_used_sectors']
    totals['cpu_selections'] = {
        name: {key: sum(volume['selections'][name][key] for volume in totals['volumes'])
               for key in totals['volumes'][0]['selections'][name]}
        for name in totals['volumes'][0]['selections']}
    return dict(complete=True, release=False, storage_report_sha256=sha(storage_path.read_bytes()),
                cpu_report_sha256=sha(cpu_path.read_bytes()), **totals)


if __name__ == '__main__':
    print(json.dumps(summarize(Path(__file__).parent), indent=2))
