"""Optional resident shared Maximum with fixed measured branch layouts.

Each selected JP cc becomes JR cc: one less service byte, -3 T when untaken,
+2 T when taken. Policies describe selection on the retained corpus, not a
promise for arbitrary streams. All original format/IRQ/caller contracts apply;
there is no quota, coroutine or partial-input mode. Defaults in maximum.build
remain unchanged. Installed code never imports tests, AST or evidence files.
"""
from ._z80 import MiniAssembler, sha
from .maximum import build as _maximum


# Frozen (uncontracted byte offset, opcode, symbolic target) triples. Checking
# all three rejects generator drift instead of silently tuning another site.
_SITES = {
    228: (
        (100, 0xda, 'dzx0m_new_offset0'),
        (137, 0xda, 'dzx0m_new_offset0'),
        (279, 0xda, 'dzx0m_new_offset2'),
        (316, 0xda, 'dzx0m_new_offset2'),
        (458, 0xda, 'dzx0m_new_offset4'),
        (495, 0xda, 'dzx0m_new_offset4'),
        (766, 0xd2, 'max_gamma_length_7_5'),
        (781, 0xd2, 'max_gamma_length_1_5'),
        (796, 0xd2, 'max_gamma_length_3_5'),
        (811, 0xd2, 'max_gamma_length_5_5'),
        (828, 0xd2, 'max_gamma_length_7_6'),
        (843, 0xd2, 'max_gamma_length_1_6'),
        (858, 0xd2, 'max_gamma_length_3_6'),
        (873, 0xd2, 'max_gamma_length_5_6'),
        (890, 0xd2, 'max_gamma_length_7_7'),
        (905, 0xd2, 'max_gamma_length_1_7'),
        (920, 0xd2, 'max_gamma_length_3_7'),
        (935, 0xd2, 'max_gamma_length_5_7'),
        (952, 0xd2, 'max_gamma_length_7_8'),
        (967, 0xd2, 'max_gamma_length_1_8'),
        (982, 0xd2, 'max_gamma_length_3_8'),
        (997, 0xd2, 'max_gamma_length_5_8'),
        (1016, 0xd2, 'max_gamma_length_7_8'),
        (1033, 0xd2, 'max_gamma_length_1_8'),
        (1050, 0xd2, 'max_gamma_length_3_8'),
        (1067, 0xd2, 'max_gamma_length_5_8'),
        (1084, 0xd2, 'max_gamma_literals_7_5'),
        (1126, 0xd2, 'max_gamma_literals_7_6'),
        (1136, 0xd2, 'max_gamma_literals_1_6'),
        (1146, 0xd2, 'max_gamma_literals_3_6'),
        (1156, 0xd2, 'max_gamma_literals_5_6'),
        (1168, 0xd2, 'max_gamma_literals_7_7'),
        (1178, 0xd2, 'max_gamma_literals_1_7'),
        (1188, 0xd2, 'max_gamma_literals_3_7'),
        (1198, 0xd2, 'max_gamma_literals_5_7'),
        (1210, 0xd2, 'max_gamma_literals_7_8'),
        (1220, 0xd2, 'max_gamma_literals_1_8'),
        (1230, 0xd2, 'max_gamma_literals_3_8'),
        (1240, 0xd2, 'max_gamma_literals_5_8'),
        (1254, 0xd2, 'max_gamma_literals_7_8'),
        (1266, 0xd2, 'max_gamma_literals_1_8'),
        (1278, 0xd2, 'max_gamma_literals_3_8'),
        (1290, 0xd2, 'max_gamma_literals_5_8'),
        (1334, 0xd2, 'max_gamma_reuse_7_5'),
        (1349, 0xd2, 'max_gamma_reuse_1_5'),
        (1364, 0xd2, 'max_gamma_reuse_3_5'),
        (1379, 0xd2, 'max_gamma_reuse_5_5'),
        (1396, 0xd2, 'max_gamma_reuse_7_6'),
        (1411, 0xd2, 'max_gamma_reuse_1_6'),
        (1426, 0xd2, 'max_gamma_reuse_3_6'),
        (1441, 0xd2, 'max_gamma_reuse_5_6'),
        (1458, 0xd2, 'max_gamma_reuse_7_7'),
        (1473, 0xd2, 'max_gamma_reuse_1_7'),
        (1488, 0xd2, 'max_gamma_reuse_3_7'),
        (1503, 0xd2, 'max_gamma_reuse_5_7'),
        (1520, 0xd2, 'max_gamma_reuse_7_8'),
        (1535, 0xd2, 'max_gamma_reuse_1_8'),
        (1550, 0xd2, 'max_gamma_reuse_3_8'),
        (1565, 0xd2, 'max_gamma_reuse_5_8'),
        (1601, 0xd2, 'max_gamma_reuse_1_8'),
        (1618, 0xd2, 'max_gamma_reuse_3_8'),
    ),
    127: (
        (100, 0xda, 'dzx0m_new_offset0'),
        (137, 0xda, 'dzx0m_new_offset0'),
        (279, 0xda, 'dzx0m_new_offset2'),
        (316, 0xda, 'dzx0m_new_offset2'),
        (458, 0xda, 'dzx0m_new_offset4'),
        (495, 0xda, 'dzx0m_new_offset4'),
        (766, 0xd2, 'max_gamma_length_7_5'),
        (781, 0xd2, 'max_gamma_length_1_5'),
        (796, 0xd2, 'max_gamma_length_3_5'),
        (811, 0xd2, 'max_gamma_length_5_5'),
        (828, 0xd2, 'max_gamma_length_7_6'),
        (843, 0xd2, 'max_gamma_length_1_6'),
        (858, 0xd2, 'max_gamma_length_3_6'),
        (873, 0xd2, 'max_gamma_length_5_6'),
        (890, 0xd2, 'max_gamma_length_7_7'),
        (905, 0xd2, 'max_gamma_length_1_7'),
        (920, 0xd2, 'max_gamma_length_3_7'),
        (935, 0xd2, 'max_gamma_length_5_7'),
        (952, 0xd2, 'max_gamma_length_7_8'),
        (967, 0xd2, 'max_gamma_length_1_8'),
        (982, 0xd2, 'max_gamma_length_3_8'),
        (997, 0xd2, 'max_gamma_length_5_8'),
        (1016, 0xd2, 'max_gamma_length_7_8'),
        (1028, 0xd2, 'max_gamma_length_1_8'),
        (1040, 0xd2, 'max_gamma_length_3_8'),
        (1052, 0xd2, 'max_gamma_length_5_8'),
        (1064, 0xd2, 'max_gamma_literals_7_5'),
        (1106, 0xd2, 'max_gamma_literals_7_6'),
        (1116, 0xd2, 'max_gamma_literals_1_6'),
        (1126, 0xd2, 'max_gamma_literals_3_6'),
        (1136, 0xd2, 'max_gamma_literals_5_6'),
        (1148, 0xd2, 'max_gamma_literals_7_7'),
        (1158, 0xd2, 'max_gamma_literals_1_7'),
        (1168, 0xd2, 'max_gamma_literals_3_7'),
        (1178, 0xd2, 'max_gamma_literals_5_7'),
        (1190, 0xd2, 'max_gamma_literals_7_8'),
        (1200, 0xd2, 'max_gamma_literals_1_8'),
        (1210, 0xd2, 'max_gamma_literals_3_8'),
        (1220, 0xd2, 'max_gamma_literals_5_8'),
        (1234, 0xd2, 'max_gamma_literals_7_8'),
        (1246, 0xd2, 'max_gamma_literals_1_8'),
        (1258, 0xd2, 'max_gamma_literals_3_8'),
        (1270, 0xd2, 'max_gamma_literals_5_8'),
        (1314, 0xd2, 'max_gamma_reuse_7_5'),
        (1329, 0xd2, 'max_gamma_reuse_1_5'),
        (1344, 0xd2, 'max_gamma_reuse_3_5'),
        (1359, 0xd2, 'max_gamma_reuse_5_5'),
        (1376, 0xd2, 'max_gamma_reuse_7_6'),
        (1391, 0xd2, 'max_gamma_reuse_1_6'),
        (1406, 0xd2, 'max_gamma_reuse_3_6'),
        (1421, 0xd2, 'max_gamma_reuse_5_6'),
        (1438, 0xd2, 'max_gamma_reuse_7_7'),
        (1453, 0xd2, 'max_gamma_reuse_1_7'),
        (1468, 0xd2, 'max_gamma_reuse_3_7'),
        (1483, 0xd2, 'max_gamma_reuse_5_7'),
        (1500, 0xd2, 'max_gamma_reuse_7_8'),
        (1515, 0xd2, 'max_gamma_reuse_1_8'),
        (1530, 0xd2, 'max_gamma_reuse_3_8'),
        (1545, 0xd2, 'max_gamma_reuse_5_8'),
        (1576, 0xd2, 'max_gamma_reuse_1_8'),
        (1588, 0xd2, 'max_gamma_reuse_3_8'),
    ),
}

_POLICY_INDICES = {
    'fast': (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60),
    'real': (1, 3, 5, 19, 25, 38, 39, 40, 41, 42, 58, 59, 60),
    'corpus': (38, 42, 58),
}

_QUALIFIED = {
    (255, 'fast'): {'native_profile': '255-fast', 'canonical_code_sha256': '6f59e27d67ac567fc2a6b30c76f8520403c3fd00e3e415d396023d8a99394553', 'real_baseline_tstates': 139552884, 'real_tstates': 139546674, 'intrinsic_service_bytes': 8165, 'slower_real_cases': 0, 'slower_cases': 0, 'maximum_case_delta_tstates': 0},
    (228, 'fast'): {'native_profile': '228-all_profitable_reachable', 'canonical_code_sha256': '5a12b921418813e7d40afe2791a28c77f49ad333146ef88a47a3d433323087f4', 'real_baseline_tstates': 139892818, 'real_tstates': 139552884, 'intrinsic_service_bytes': 7517, 'slower_real_cases': 0, 'slower_cases': 103, 'maximum_case_delta_tstates': 38},
    (228, 'real'): {'native_profile': '228-no_individual_real_block_regression', 'canonical_code_sha256': '4be4133cd55ce55cfb64b1901713c95a706ea98bf7d543022e8a7d9151785dc0', 'real_baseline_tstates': 139892818, 'real_tstates': 139677954, 'intrinsic_service_bytes': 7565, 'slower_real_cases': 0, 'slower_cases': 38, 'maximum_case_delta_tstates': 11},
    (228, 'corpus'): {'native_profile': '228-no_individual_corpus_case_regression', 'canonical_code_sha256': '95516988e99c38fe794427bb835d32dce70c38e71bf73a731a06959770566e62', 'real_baseline_tstates': 139892818, 'real_tstates': 139891848, 'intrinsic_service_bytes': 7575, 'slower_real_cases': 0, 'slower_cases': 0, 'maximum_case_delta_tstates': 0},
    (127, 'fast'): {'native_profile': '127-all_profitable_reachable', 'canonical_code_sha256': '2681d22aa441705ae404425d822e33c1c5673babf46a459e6a26cf36f8a5d1ff', 'real_baseline_tstates': 139916508, 'real_tstates': 139576574, 'intrinsic_service_bytes': 5053, 'slower_real_cases': 0, 'slower_cases': 103, 'maximum_case_delta_tstates': 38},
    (127, 'real'): {'native_profile': '127-no_individual_real_block_regression', 'canonical_code_sha256': 'b5c31155abbe1a2d6a216ff776cb3cc6824d56885e54357e7da521474e87b87c', 'real_baseline_tstates': 139916508, 'real_tstates': 139701644, 'intrinsic_service_bytes': 5101, 'slower_real_cases': 0, 'slower_cases': 38, 'maximum_case_delta_tstates': 11},
    (127, 'corpus'): {'native_profile': '127-no_individual_corpus_case_regression', 'canonical_code_sha256': '36c418ae39152534676e77027931ebea05a96ff177462197d4d73f95d90d4b4a', 'real_baseline_tstates': 139916508, 'real_tstates': 139915538, 'intrinsic_service_bytes': 5111, 'slower_real_cases': 0, 'slower_cases': 0, 'maximum_case_delta_tstates': 0},
}


class _ContractedAssembler(MiniAssembler):
    def __init__(self, origin, sites):
        super().__init__(origin)
        self.sites = {offset: (opcode, target) for offset, opcode, target in sites}
        self.changes = []

    def abs16(self, opcode, target):
        # Every earlier contraction removed exactly one byte. Reconstruct the
        # uncontracted offset; counts/scalar operands never participate.
        offset = self.pc-self.origin+len(self.changes)
        if offset not in self.sites:
            return super().abs16(opcode, target)
        if self.sites[offset] != (opcode, target):
            raise ValueError('qualified Maximum branch site changed')
        self.changes.append(dict(baseline_offset=offset, address=self.pc,
                                 opcode=opcode, target=target))
        super().rel8({0xc2: 0x20, 0xca: 0x28, 0xd2: 0x30, 0xda: 0x38}[opcode], target)


def build(*, core=0x8000, core_limit=None, prefix_cap=228, policy='fast',
          irq_code_bytes=0, irq_stack_bytes=0, service_limit=10000,
          _quota_hook=None):
    """Return raw regions, labels and complete service-memory metadata.

    HL=input, DE=output; AF/BC/DE/HL clobbered, IX/alternate pairs preserved.
    Retain full resident input/output/history and writable offset code. The
    four-byte stack reservation includes caller return and live source word.
    IRQ preserves live registers; add actual IRQ code/extra stack explicitly.

    At caps127/228, fast contracts61 sites, real13, corpus3. Each improves
    measured real CPU and reduces service versus its uncontracted same-cap
    shared layout. fast/real retain non-real-case regressions;
    corpus had no regression among the retained 417+56 cases. Policy names
    describe this finite measured selection and establish no global optimum.
    Cap255/fast extends each of twelve proven word-count chains by27 LDI
    instructions: +648 service bytes, -135 T per word entry versus cap228/fast.
    Its46-T per-block setup includes the20-T offset reset in measured CPU.
    """
    if type(prefix_cap) is not int or prefix_cap not in (127, 228, 255):
        raise ValueError('maximum branches requires qualified prefix-cap 127, 228 or 255')
    if type(policy) is not str or policy not in _POLICY_INDICES:
        raise ValueError('maximum branch policy must be fast, real or corpus')
    if _quota_hook is not None:
        raise ValueError('maximum branches supports resident raw decoding only')
    if prefix_cap == 255 and policy != 'fast':
        raise ValueError('prefix-cap255 supports only the qualified fast policy')
    site_cap = 228 if prefix_cap == 255 else prefix_cap
    sites = tuple(_SITES[site_cap][index] for index in _POLICY_INDICES[policy])
    instances = []

    def assembler(origin):
        result = _ContractedAssembler(origin, sites)
        instances.append(result)
        return result

    regions, labels, original = _maximum(core=core, core_limit=core_limit,
        prefix_cap=prefix_cap, shared_prefixes=True, irq_code_bytes=irq_code_bytes,
        irq_stack_bytes=irq_stack_bytes, service_limit=service_limit, _assembler=assembler,
        **(dict(_allow_prefix255=True) if prefix_cap == 255 else {}))
    emitter, = instances
    if {row['baseline_offset'] for row in emitter.changes} != {row[0] for row in sites}:
        raise ValueError('qualified Maximum branch selection was not fully emitted')
    for row in emitter.changes:
        row['target_address'] = labels[row['target']]
        row['final_displacement'] = row['target_address']-row['address']-2
        if not -128 <= row['final_displacement'] <= 127:
            raise ValueError('qualified Maximum branch is outside JR range')
    frozen = _QUALIFIED[prefix_cap, policy]
    intrinsic = original['service_memory_bytes']-irq_code_bytes-irq_stack_bytes
    if (intrinsic != frozen['intrinsic_service_bytes'] or
            original['code_bytes']+4 != intrinsic or original['workspace_bytes'] != intrinsic):
        raise ValueError('qualified Maximum branch code/service size changed')
    # Canonicalize emitted absolute operands to the measured 8000h origin.
    # This catches equal-size generator drift outside selected branches too;
    # scalar counts and negative offsets are not address fixups and stay exact.
    canonical = bytearray(regions[0][1])
    for position, target in emitter.abs_fixups:
        value = labels[target]-core+0x8000
        canonical[position:position+2] = value.to_bytes(2, 'little')
    if sha(canonical) != frozen['canonical_code_sha256']:
        raise ValueError('qualified Maximum branch instructions changed')
    qualified = dict(_QUALIFIED[prefix_cap, policy], cases=473, real_cases=364,
                     main_cases=417, high_word_cases=56,
                     cpu_totals_exclude_irq_execution=True,
                     fixed_decoder_revision='9c28b01f',
                     comparison='same-cap shared Maximum before these contractions')
    metadata = dict(original, variant='maximum-branches', maximum_branch_policy=policy,
        conditional_branch_site_count=len(emitter.changes),
        conditional_branch_sites=emitter.changes,
        conditional_branch_tstates=dict(before=10, after_not_taken=7, after_taken=12),
        branch_delta_formula='2*taken - 3*not_taken',
        baseline_service_memory_bytes=original['service_memory_bytes']+len(emitter.changes),
        service_delta_bytes=-len(emitter.changes), qualified_corpus=qualified,
        coroutine_supported=False)
    if prefix_cap == 255:
        # The measured E04 baseline is actual cap228-fast, not an inferred
        # uncontracted cap255 binary. Branch timing remains historical lineage.
        qualified.update(fixed_decoder_revision='9fbd9ce7',
            comparison='accepted shared cap228-fast before the cap255 extension',
            native_proof='next_e04_full.json.gz',
            native_proof_sha256='7c0b3565b19e4da0c0de0e13f96fc9ea2a1eea0a96cf05e4edc34568f4bae009')
        metadata.update(baseline_service_memory_bytes=7517+irq_code_bytes+irq_stack_bytes,
            service_delta_bytes=648, prefix_extension_delta_formula='-135*word_prefix_entries',
            startup_tstates=46, offset_reset_tstates=20,
            target_initializer_required=False,
            benchmark_call_scope='entry including offset reset through exact EOF and RET',
            branch_delta_scope='inherited E01 substitutions; not the E04 incremental CPU delta',
            conditional_branch_lineage=dict(prefix_cap=228, policy='fast',
                native_profile=_QUALIFIED[228, 'fast']['native_profile'],
                native_proof='next_e01_zx0_branches.json.gz',
                site_count=61, branch_delta_formula='2*taken - 3*not_taken',
                real_delta_tstates=-339934, service_delta_bytes=-61,
                historical_slower_cases=103, historical_maximum_delta_tstates=38))
    return regions, labels, metadata
