"""E01 test-only contraction of the three frozen E00 branch selections.

Recompile the current source in a private namespace with a per-call emitter;
never patch the installed package or a global assembler. An independent
binary/label relocation oracle checks the emitter at each measured origin.
The policy data is experiment evidence, not a runtime package dependency.
"""
import ast
from bisect import bisect_left
from functools import lru_cache
import gzip
import inspect
import json
from pathlib import Path

from measure_long_copy import ROOT, sha
from profile_branch_mix import instructions
from zx0 import maximum
from zx0._z80 import MiniAssembler


POLICIES = ('all_profitable_reachable', 'no_individual_real_block_regression',
            'no_individual_corpus_case_regression')
REPORT_PATH = ROOT/'libraries/evidence/next_e00_zx0_profile.json.gz'


@lru_cache(maxsize=6)
def selection(cap, policy):
    report = json.loads(gzip.decompress(REPORT_PATH.read_bytes()))
    assert report['complete'] and not report['candidate_decoder_implemented']
    if cap not in (127, 228) or policy not in POLICIES:
        raise ValueError('E01 supports the three frozen policies and shared caps127/228 only')
    return next(row for row in report['profiles'][str(cap)]['e01_predicted_sets']
                if row['name'] == policy)


def oracle(baseline, selected_offsets):
    """Independently relocate the original instruction bytes and every label.

    These resident profiles contain no embedded table/data beyond the offset
    operand. Internal absolute addresses occur in JP/CALL, LD HL,(nn) and
    LD (nn),BC; scalar LD immediate counts/negative offsets remain unchanged.
    """
    (origin, blob), = baseline[0]
    points = sorted(origin+offset for offset in selected_offsets)
    point_set = set(points)

    def remap(address):
        return address-bisect_left(points, address)

    output = bytearray()
    for at, original in instructions(blob, origin):
        code = bytearray(original)
        if at in point_set:
            assert code[0] in (0xc2, 0xca, 0xd2, 0xda)
            target = int.from_bytes(code[1:], 'little')
            span = remap(target)-remap(at)-2
            assert -128 <= span <= 127
            output.extend(({0xc2:0x20, 0xca:0x28, 0xd2:0x30, 0xda:0x38}[code[0]], span & 255))
            continue
        absolute = (len(code) == 3 and
                    (code[0] & 0xc7 in (0xc2, 0xc4) or code[0] in (0xc3, 0xcd, 0x2a)))
        offset = 1 if absolute else 2 if len(code) == 4 and code[:2] == b'\xed\x43' else None
        if offset is not None:
            target = int.from_bytes(code[offset:offset+2], 'little')
            assert origin <= target < origin+len(blob), ('unexpected external absolute reference', at, target)
            code[offset:offset+2] = remap(target).to_bytes(2, 'little')
        output.extend(code)
    assert len(output) == len(blob)-len(points)
    return [(origin, bytes(output))], {name:remap(at) for name,at in baseline[1].items()}


def build(*, core=0x8000, prefix_cap=228, policy=POLICIES[0]):
    selected = selection(prefix_cap, policy)
    offsets = {row['source_offset'] for row in selected['branches']}
    instances = []

    class ContractedAssembler(MiniAssembler):
        def __init__(self, origin):
            super().__init__(origin)
            self.changes = []
            instances.append(self)

        def abs16(self, opcode, target):
            old_offset = self.pc-self.origin+len(self.changes)
            if old_offset in offsets:
                assert opcode in (0xc2, 0xca, 0xd2, 0xda)
                self.changes.append(dict(baseline_offset=old_offset,
                    address=self.pc, opcode=opcode, target=target))
                super().rel8({0xc2:0x20, 0xca:0x28, 0xd2:0x30, 0xda:0x38}[opcode], target)
            else:
                super().abs16(opcode, target)

    namespace = dict(vars(maximum), MiniAssembler=ContractedAssembler)
    source = inspect.getsource(maximum.build)
    exec(compile(ast.parse(source), '<private E01 shared Maximum emitter>', 'exec'), namespace)
    candidate = namespace['build'](core=core, prefix_cap=prefix_cap, shared_prefixes=True)
    assert len(instances) == 1
    changes = instances[0].changes
    assert {row['baseline_offset'] for row in changes} == offsets
    baseline = maximum.build(core=core, prefix_cap=prefix_cap, shared_prefixes=True)
    assert candidate[:2] == oracle(baseline, offsets), 'independent binary/label oracle differs'
    assert candidate[2]['service_memory_bytes'] == baseline[2]['service_memory_bytes']-len(offsets)
    for row in changes:
        row['target_address'] = candidate[1][row['target']]
        row['final_displacement'] = row['target_address']-row['address']-2
        assert -128 <= row['final_displacement'] <= 127
    metadata = dict(candidate[2], test_only=True, measured_frontier=False,
        next_branch_policy=policy,
        next_branch_changes=changes, independent_binary_and_label_oracle_exact=True,
        branch_delta_formula='2*taken - 3*not_taken',
        baseline_service_bytes=baseline[2]['service_memory_bytes'],
        e00_report_sha256=sha(REPORT_PATH.read_bytes()))
    return candidate[0], candidate[1], metadata
