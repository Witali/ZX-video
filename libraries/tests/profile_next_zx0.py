"""E00: authenticate and profile unchanged resident shared Maximum layouts.

No candidate decoder is emitted. E01 JPcc-to-JRcc sets are predictions from
exact branch outcomes: each selected branch saves one service byte and costs
-3 T when not taken, +2 T when taken. Final spans include every selected
one-byte contraction. Native correctness/IRQ/relocation proof is reused only
after authenticating its complete regions, inputs and independent label map.
"""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import date
import gzip
import json
from pathlib import Path
import subprocess

from measure_long_copy import ROOT, sha
from measure_bit_phases import samples
from measure_mega_prefix import high_word_samples
from native_block import execute
from profile_branch_mix import condition, instructions
from shared_zero_prefix_profile import build as independent
from zx0.maximum import build


FIXED_DECODER_BASELINE = '9c28b01f'
SOURCE_SNAPSHOT = 'a8632dac962106f2690f939607d425b6580e3417'
EXPECTED_REAL = {127: 139916508, 228: 139892818}
CONDITIONS = ('nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm')


def region_rows(profile):
    return [dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in profile[0]]


def load_proof(name):
    path = ROOT/'libraries/evidence'/name
    raw = path.read_bytes()
    decoded = gzip.decompress(raw)
    result = json.loads(decoded)
    assert result['complete']
    frozen = ROOT/'libraries/tests/shared_zero_prefix_profile.py'
    assert sha(frozen.read_bytes().replace(b'\r\n', b'\n')) == result['source_sha256_lf'][
        'libraries/tests/shared_zero_prefix_profile.py']
    return result, dict(path=str(path.relative_to(ROOT)).replace('\\', '/'),
                        sha256=sha(raw), decoded_sha256=sha(decoded),
                        executed_independent_generator_source_exact=True)


def branch_sites(profile):
    labels = profile[1]
    by_address = defaultdict(list)
    for name, at in labels.items():
        if '+' not in name:
            by_address[at].append(name)
    label_addresses = sorted(by_address)
    result = {}
    refills = {}
    for origin, blob in profile[0]:
        for at, code in instructions(blob, origin):
            context = label_addresses[bisect_left(label_addresses, at+1)-1]
            if code[0] == 0x7e:
                refills[at] = dict(address=at, source_offset=at-origin,
                                   context_labels=by_address[context])
            if code[0] & 0xc7 != 0xc2:
                continue
            target = int.from_bytes(code[1:], 'little')
            index = (code[0] >> 3) & 7
            result[at] = dict(address=at, source_offset=at-origin,
                condition=CONDITIONS[index], condition_index=index,
                target=target, target_offset=target-origin,
                target_labels=by_address[target], context_labels=by_address[context],
                context_offset=at-context, jr_form_exists=index < 4)
    return result, refills


def displacement(site, selected):
    """Exact final JR displacement after the selected one-byte contractions."""
    points = sorted(selected)
    source = site['address']-bisect_left(points, site['address'])
    target = site['target']-bisect_left(points, site['target'])
    return target-(source+2)


def select_sets(sites, blocks):
    # A contraction can bring another formerly distant branch into reach.
    # Start from valid single contractions and close only over eligible sites.
    def closure(eligible):
        selected = set()
        while True:
            additions = {at for at in eligible-selected
                         if -128 <= displacement(sites[at], selected | {at}) <= 127}
            if not additions:
                return selected
            selected.update(additions)

    profitable = {at for at, site in sites.items()
                  if site['jr_form_exists'] and site['real_delta_tstates'] < 0}
    real_safe = {at for at in profitable if all(
        block['branch_counts'].get(str(at), [0, 0])[1]*2
        -block['branch_counts'].get(str(at), [0, 0])[0]*3 <= 0
        for block in blocks if block['case'].startswith('real-'))}
    all_safe = {at for at in real_safe if all(
        block['branch_counts'].get(str(at), [0, 0])[1]*2
        -block['branch_counts'].get(str(at), [0, 0])[0]*3 <= 0
        for block in blocks)}
    result = []
    for name, eligible in (('all_profitable_reachable', profitable),
                           ('no_individual_real_block_regression', real_safe),
                           ('no_individual_corpus_case_regression', all_safe)):
        chosen = closure(eligible)
        rows = []
        for block in blocks:
            delta = sum(2*block['branch_counts'].get(str(at), [0, 0])[1]
                        -3*block['branch_counts'].get(str(at), [0, 0])[0] for at in chosen)
            rows.append(dict(case=block['case'], predicted_delta_tstates=delta,
                             baseline_tstates=block['tstates']))
        real = [row for row in rows if row['case'].startswith('real-')]
        result.append(dict(name=name, predicted_only=True,
            hypothesis='one fewer code/service byte per branch and net real CPU gain',
            rejection_condition='any final JR outside -128..127; native delta differs from '
                '2*taken-3*not_taken; correctness/IRQ/relocation fails; or total service/real CPU does not decrease',
            source_offsets=[sites[at]['source_offset'] for at in sorted(chosen)],
            branches=[dict(address=at, source_offset=sites[at]['source_offset'],
                           condition=sites[at]['condition'], target_labels=sites[at]['target_labels'],
                           final_displacement=displacement(sites[at], chosen)) for at in sorted(chosen)],
            service_delta_bytes=-len(chosen),
            real_delta_tstates=sum(row['predicted_delta_tstates'] for row in real),
            all_delta_tstates=sum(row['predicted_delta_tstates'] for row in rows),
            slower_real_cases=[row for row in real if row['predicted_delta_tstates'] > 0],
            slower_cases=[row for row in rows if row['predicted_delta_tstates'] > 0],
            maximum_case_delta_tstates=max(row['predicted_delta_tstates'] for row in rows),
            case_deltas=rows))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path)
    parser.add_argument('--caps', type=int, nargs='+', default=[228, 127])
    args = parser.parse_args()
    assert args.caps and all(cap in EXPECTED_REAL for cap in args.caps)
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    fixed_revision = subprocess.run(['git', 'rev-parse', FIXED_DECODER_BASELINE],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    # The proof remains reusable after its focused commit: later HEADs are
    # permitted only with the pinned baseline in history and exact native
    # region/label/input authentication below.
    subprocess.run(['git', 'merge-base', '--is-ancestor', SOURCE_SNAPSHOT, revision],
                   cwd=ROOT, check=True, capture_output=True)
    main_proof, main_hash = load_proof('shared_zero_prefix_native.json.gz')
    high_proof, high_hash = load_proof('shared_zero_prefix_high_word.json.gz')
    cases = [(name, payload, raw, False) for name, payload, raw in samples()]
    cases += [(name, payload, raw, True) for name, payload, raw in high_word_samples()]
    assert len(cases) == 473 and sum(name.startswith('real-') for name, *_ in cases) == 364
    report = dict(date=date.today().isoformat(), stage='E00', complete=False,
        baseline_revision=fixed_revision, fixed_decoder_baseline_revision=fixed_revision,
        source_snapshot_revision=SOURCE_SNAPSHOT, profiling_revision=revision,
        release=False, resident_only=True,
        candidate_decoder_implemented=False, evidence=[main_hash, high_hash],
        input_output_history_counted_separately=True,
        timing=dict(table='libraries/Z80_TIMINGS.md', jp_cc_tstates=10,
                    jr_cc_not_taken_tstates=7, jr_cc_taken_tstates=12,
                    delta_formula='2*taken - 3*not_taken', break_even_taken_fraction=0.6),
        reused_proof_scope='complete identical emitted regions and inputs; all-case IRQ/relocation, '
            'registers, protected source/stack/output and exact EOF from authenticated saved proof',
        new_replay_scope='unchanged normal origins, protected native output/input/register/stack checks; '
            'new branch, gamma/prefix and reservoir-refill observers; no repeated IRQ/relocation benchmark',
        source_binding='historical executed independent generator source matches its saved hash; '
            'current public normal/relocated bytes and independent full labels match; '
            'current public source hashes are recorded separately, not rebound as historical source',
        search_limit='three selection strategies for each of two existing caps; no branch inversion, '
            'zero-hit contraction or global layout search; no candidate implementation or qualification',
        profiles={})
    for cap in args.caps:
        normal = build(core=0x8000, prefix_cap=cap, shared_prefixes=True)
        high = build(core=0x0800, prefix_cap=cap, shared_prefixes=True)
        saved = {}
        for proof, current, origin, moved in ((main_proof, normal, 0x8000, 0x9103),
                                             (high_proof, high, 0x0800, 0x0703)):
            old = proof['profiles'][str(cap)]
            assert region_rows(current) == old['regions']
            assert region_rows(build(core=moved, prefix_cap=cap, shared_prefixes=True)) == old['relocated_regions']
            assert current[:2] == independent(origin=origin, prefix_cap=cap)[:2]
            assert current[2]['shared_prefix_audit'] == old['audit']
            assert all(current[2]['service_memory'][key] == value
                       for key, value in old['service_memory'].items())
            assert current[2]['service_memory_bytes'] == old['summary']['service_bytes']
            saved.update({row['case']: row for row in old['blocks']})
        sites, refills = branch_sites(normal)
        offset = 0x8000
        all_branch = Counter()
        real_branch = Counter()
        refill_counts = Counter()
        gamma_counts = Counter()
        prefix_counts = Counter()
        blocks = []
        for case_index, (name, payload, raw, high_word) in enumerate(cases):
            profile = high if high_word else normal
            shift = 0x0800-0x8000 if high_word else 0
            previous = saved[name]
            assert previous['input_sha256'] == sha(payload) and previous['output_sha256'] == sha(raw)
            assert previous['input_bytes'] == len(payload) and previous['output_history_bytes'] == len(raw)
            callbacks = defaultdict(list)
            branches = Counter()
            refilled = Counter()
            gamma = Counter()
            prefixes = Counter()
            def add(at, callback):
                callbacks[at].append(callback)
            for at, site in sites.items():
                def observe(machine, address=at, test=site['condition_index']):
                    branches[address, bool(condition(machine.f, test))] += 1
                add(at+shift, observe)
            for at in refills:
                def observe(machine, address=at):
                    refilled[address, machine.a, machine.f & 1] += 1
                add(at+shift, observe)
            for label, at in profile[1].items():
                if re_gamma(label):
                    def observe(machine, entry=label):
                        gamma[entry, machine.bc] += 1
                    add(at, observe)
            aliases = profile[2]['shared_prefix_audit']['literal_direct_aliases']
            for label, info in profile[2]['prefixes'].items():
                if label in aliases:
                    continue  # Shared3 also receives larger-copy fallthroughs.
                def observe(machine, entry=label, details=info):
                    assert machine.bc >= details['minimum_count']
                    assert machine.bc > details['prefix_bytes']
                    prefixes[entry, machine.bc] += 1
                add(profile[1][label], observe)
            def dispatch(items):
                def callback(machine):
                    for item in items:
                        item(machine)
                return callback
            watch = {at: dispatch(items) for at, items in callbacks.items()}
            options = dict(source=0x0400, output=0x3000, caller_stack=0x2ff0) if high_word else {}
            result = execute(profile, payload, raw, watch=watch, **options)
            assert result['tstates'] == previous['candidate_tstates'], (cap, name, result, previous)
            assert result['stack_bytes'] <= 4
            literal_targets = {normal[1][label] for label in aliases}
            direct_literal4 = sum(branches[at, True] for at, site in sites.items()
                                  if site['target'] in literal_targets)
            assert direct_literal4 == previous['baseline_literal4_entries']
            all_branch.update(branches)
            if name.startswith('real-'):
                real_branch.update(branches)
            for key, count in refilled.items():
                refill_counts[key+(name.startswith('real-'),)] += count
            for key, count in gamma.items():
                gamma_counts[key+(name.startswith('real-'),)] += count
            for key, count in prefixes.items():
                prefix_counts[key+(name.startswith('real-'),)] += count
            blocks.append(dict(case=name, input_sha256=sha(payload), output_sha256=sha(raw),
                input_bytes=len(payload), output_history_bytes=len(raw), tstates=result['tstates'],
                stack_bytes=result['stack_bytes'], high_word=high_word,
                branch_counts={str(at): [branches[at, False], branches[at, True]]
                               for at in sites if branches[at, False]+branches[at, True]},
                reservoir_refills=sum(refilled.values()), gamma_stage_entries=sum(gamma.values()),
                direct_prefix_entries_excluding_literal4=sum(prefixes.values()),
                confirmed_literal4_direct_entries=direct_literal4,
                reused_saved_literal4_entries=previous['baseline_literal4_entries'],
                reused_saved_word_entries=previous['baseline_word_joins']))
            if case_index % 50 == 0:
                print(f'cap{cap}: {case_index+1}/{len(cases)} {name}', flush=True)
        assert sum(row['tstates'] for row in blocks if row['case'].startswith('real-')) == EXPECTED_REAL[cap]
        for at, site in sites.items():
            no, yes = all_branch[at, False], all_branch[at, True]
            real_no, real_yes = real_branch[at, False], real_branch[at, True]
            site.update(not_taken=no, taken=yes, real_not_taken=real_no, real_taken=real_yes,
                real_taken_fraction=real_yes/(real_no+real_yes) if real_no+real_yes else None,
                real_delta_tstates=2*real_yes-3*real_no, all_delta_tstates=2*yes-3*no,
                real_saved_tstates_per_removed_service_byte=3*real_no-2*real_yes,
                single_replacement_displacement=displacement(site, {at}),
                single_replacement_relative_fits=-128 <= displacement(site, {at}) <= 127)
        selections = select_sets(sites, blocks)
        real_word = sum(count for (label, bc, real), count in prefix_counts.items()
                        if real and normal[2]['prefixes'][label]['minimum_count'] == 256)
        # Cap127's >=256 stage jumps into its >=128 prefix, so its historical
        # observer was deliberately empty. The cap228 word-entry count is direct.
        if cap == 228:
            assert real_word == 46
        profile_report = dict(builder='zx0.maximum.build', builder_arguments=dict(prefix_cap=cap, shared_prefixes=True),
            regions=region_rows(normal), high_word_regions=region_rows(high),
            labels_sha256=sha(json.dumps(normal[1], sort_keys=True).encode()),
            independent_frozen_regions_and_labels_exact=True,
            service_memory=normal[2]['service_memory'], service_memory_bytes=normal[2]['service_memory_bytes'],
            service_with_diagnostic_irq_bytes=normal[2]['service_memory_bytes']+13+6,
            real_cpu_tstates=EXPECTED_REAL[cap], cases=len(blocks), real_cases=364,
            real_word_prefix_entries_direct=real_word if cap == 228 else None,
            confirmed_real_literal4_direct_entries=sum(row['confirmed_literal4_direct_entries']
                for row in blocks if row['case'].startswith('real-')),
            reservoir_refill_scope='LD A,(HL) reservoir loads only; no separate nibble cache in this ZX0 decoder',
            prefix_histogram_scope='BC at each direct prefix entry, before setup/copy; '
                'length-family counts retain the existing later INC C/LDI convention; '
                'literal4 aliases counted only through incoming taken branches, excluding suffix fallthroughs',
            branches=sorted(sites.values(), key=lambda row: row['real_delta_tstates']),
            reservoir_refills=[dict(refills[at], incoming_a=a, incoming_carry=carry, real=real, entries=count)
                for (at, a, carry, real), count in sorted(refill_counts.items())],
            gamma_stage_histogram=[dict(label=label, bc=bc, real=real, entries=count)
                for (label, bc, real), count in sorted(gamma_counts.items())],
            prefix_length_histogram=[dict(label=label, bc=bc, real=real, entries=count,
                prefix=normal[2]['prefixes'][label])
                for (label, bc, real), count in sorted(prefix_counts.items())],
            e01_predicted_sets=selections, blocks=blocks)
        report['profiles'][str(cap)] = profile_report
        print(cap, json.dumps(dict(real_tstates=EXPECTED_REAL[cap], service=normal[2]['service_memory_bytes'],
            alternatives=[dict(name=row['name'], branches=len(row['branches']),
                               real_delta=row['real_delta_tstates'], service_delta=row['service_delta_bytes'])
                          for row in selections])), flush=True)
    paths = [Path(__file__), Path(__file__).with_name('native_block.py'),
             Path(__file__).with_name('profile_branch_mix.py'),
             Path(__file__).with_name('shared_zero_prefix_profile.py'),
             ROOT/'libraries/zx0/src/zx0/maximum.py', ROOT/'libraries/zx0/src/zx0/_shared_prefixes.py',
             ROOT/'libraries/zx0/src/zx0/asm/dzx0_mega.asm', ROOT/'libraries/Z80_TIMINGS.md']
    report['source_sha256_lf'] = {str(path.relative_to(ROOT)).replace('\\', '/'):
                                sha(path.read_bytes().replace(b'\r\n', b'\n')) for path in paths}
    report['complete'] = True
    raw_report = (json.dumps(report, indent=2)+'\n').encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(raw_report, mtime=0) if args.output.suffix == '.gz' else raw_report)
    if args.summary_output:
        summary = {key: value for key, value in report.items() if key != 'profiles'}
        summary['full_report'] = dict(path=str(args.output.relative_to(ROOT)
            if args.output.is_absolute() else args.output).replace('\\', '/'),
            sha256=sha(args.output.read_bytes()), decoded_sha256=sha(raw_report))
        summary['profiles'] = {}
        for cap, profile in report['profiles'].items():
            summary['profiles'][cap] = {key: profile[key] for key in (
                'builder', 'builder_arguments', 'regions', 'high_word_regions', 'labels_sha256',
                'independent_frozen_regions_and_labels_exact', 'service_memory', 'service_memory_bytes',
                'service_with_diagnostic_irq_bytes', 'real_cpu_tstates', 'cases', 'real_cases',
                'real_word_prefix_entries_direct', 'confirmed_real_literal4_direct_entries')}
            summary['profiles'][cap]['e01_predicted_sets'] = [
                {key: value for key, value in candidate.items()
                 if key not in ('case_deltas', 'slower_cases', 'slower_real_cases', 'branches')}
                | dict(slower_cases=len(candidate['slower_cases']),
                       slower_real_cases=len(candidate['slower_real_cases']))
                for candidate in profile['e01_predicted_sets']]
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8', newline='\n')


def re_gamma(label):
    # Include cloned next-command gamma headers as separate executable sites.
    return 'max_gamma_' in label or 'dzx0m_elias_' in label


if __name__ == '__main__':
    main()
