"""Rank lossless ZX0 candidates by observed reserve pressure.

Weights are an offline heuristic, not physical T-states or a scheduling proof.
The whole-video capacity, raw bytes, frame cadence and AY remain fixed.
"""
import argparse
import json
from pathlib import Path

from benchmark_adaptive_zx0 import choose_cpu
from build_fap3_trd import sha
from probe_adaptive_block_codecs import geometry

ROOT = Path(__file__).parent
OUTPUT = ROOT/'pressure_zx0_tokens.json'


def choose(volume, pressure, strength, margin_sectors=4):
    rows = volume['blocks']; blocks = pressure['block_pressure']
    if len(rows) != len(blocks): raise ValueError('different block partition')
    fractions = []
    for row, b in zip(rows, blocks, strict=True):
        if row['decoded_bytes'] != b['raw_bytes']: raise ValueError('different raw block length')
        fractions.append((256*b['bytes_requested_without_completed_slot']+b['raw_bytes']-1)//b['raw_bytes'])
    # A producer may work up to two whole blocks ahead in the three-slot ring.
    # Decay future pressure; do not assume savings in a full ring are useful.
    pressure_q8 = [max([fractions[i]]+[fractions[i+d]//(2**d)
        for d in (1, 2) if i+d < len(rows)]) for i in range(len(rows))]
    weights = [256+strength*n for n in pressure_q8]
    price = volume['disk_charge_tstates_per_byte']
    options = [[dict(name=name, bytes=o['bytes'],
        tstates=weights[i]*(o['decoder_tstates']+price*o['bytes']))
        for name, o in row['variants'].items() if o['executed'] and 'reuses' not in o]
        for i, row in enumerate(rows)]
    capacity = volume['capacity_bytes']-256*margin_sectors
    picked = choose_cpu(options, capacity)
    names = picked.pop('selected_codecs'); score = picked.pop('decoder_tstates')
    ticks = sum(row['variants'][name]['decoder_tstates'] for row, name in zip(rows, names, strict=True))
    old = sum(row['variants']['min0']['decoder_tstates'] for row in rows)
    return dict(picked, names=names, decoder_tstates=ticks, delta_decoder_tstates=ticks-old,
        delta_bytes=picked['stream_bytes']-volume['baseline_bytes'],
        disk_charge_tstates_per_byte=price, bootstrap_margin_sectors=margin_sectors,
        capacity_bytes=capacity, pressure_strength=strength, pressure_q8=pressure_q8,
        weight_q8=weights, weighted_objective_score=score,
        geometry=geometry(picked['stream_bytes'], volume['video_start_sector']))


def generate():
    paths = [ROOT/n for n in ('fast_zx0_tokens_probe.json', 'fast_reservoir_profile.json', 'fast_token_player_build.json')]
    probe, profile, previous = [json.loads(p.read_bytes()) for p in paths]
    if not all(r['complete'] for r in (probe, profile, previous)): raise ValueError('incomplete source')
    rows = []
    for volume, pressure in zip(probe['volumes'], profile['volumes'], strict=True):
        if volume['part'] != pressure['part']: raise ValueError('different volumes')
        choices = {f'weight{strength}': choose(volume, pressure, strength) for strength in (0, 4, 16)}
        old = previous['volumes'][volume['part']-1]['fast_token_selection']
        if any(choices['weight0'][k] != old[k] for k in ('names', 'stream_bytes', 'decoder_tstates')):
            raise ValueError('zero-weight control differs from the previous experiment')
        rows.append(dict(part=volume['part'], selections=choices))
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='2881667',
        weights_are_estimates=True, player_instruction_delta_tstates=0, volumes=rows,
        references={p.name: sha(p.read_bytes()) for p in paths},
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n'))
            for n in ('pressure_zx0_tokens.py', 'benchmark_adaptive_zx0.py', 'probe_adaptive_block_codecs.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    args = p.parse_args(); result = json.loads(json.dumps(generate()))
    if args.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved choices differ')
    for v in result['volumes']:
        print(json.dumps(dict(part=v['part'], choices={n:{k:r[k] for k in
            ('stream_bytes', 'selected_counts', 'decoder_tstates', 'delta_decoder_tstates', 'delta_bytes')}
            for n, r in v['selections'].items()})), flush=True)


if __name__ == '__main__': main()
