"""Test-only branch-layout candidates derived from the complete real-input profile."""
from unittest.mock import patch

from lzsa import resumable as lzsa_coroutine
from lzsa.block import build as lblock
from zx0 import block as zx0_block
from zx0 import resumable as zx0_coroutine


class RelativeOverflow(Exception):
    def __init__(self, site):
        self.site = site


def build(codec, *, resident=True, core=0x8000, core_limit=None, **options):
    module = lzsa_coroutine if codec == 'lzsa2' else (zx0_block if resident else zx0_coroutine)
    core_limit = core+0x400 if core_limit is None else core_limit
    base = module.MiniAssembler
    excluded = set()
    while True:
        instances = []

        class TunedAssembler(base):
            def __init__(self, origin):
                super().__init__(origin)
                self.changed = []; self.site_counts = {}; self.shortened = {}
                instances.append(self)

            def select(self, op, target, relative):
                normalized = 'gamma_loop' if target.startswith('gamma_loop_') else target
                key = (op, normalized)
                occurrence = self.site_counts.get(key, 0)
                self.site_counts[key] = occurrence+1
                site = (op, normalized, occurrence)
                if codec == 'lzsa2':
                    shorten = not relative and op == 0xd2 and target == 'Case11x'
                    lengthen = relative and op == 0x30 and target in ('MatchLen', 'CopyMoreLiterals')
                else:
                    shorten = not relative and (
                        (op == 0xd2 and normalized in ('gamma_loop', 'LongerMatch', 'LongerOffets', 'LongerRun', 'LongerRepMatch'))
                        or (op == 0xda and target in ('UsualMatch', 'CopyMatch2', 'ShorterOffsets', 'CopyLiteral'))
                        or (op == 0xc2 and target == 'CopyLiterals'))
                    lengthen = False
                if site in excluded:
                    shorten = False
                return site, shorten, lengthen

            def abs16(self, opcode, target):
                site, shorten, _ = self.select(opcode if isinstance(opcode, int) else -1, target, False)
                if shorten:
                    at = self.pc
                    self.shortened[len(self.code)+1] = site
                    self.changed.append(dict(address=at, target=target, before='jp', after='jr'))
                    super().rel8({0xc2:0x20,0xca:0x28,0xd2:0x30,0xda:0x38}[opcode], target)
                else:
                    super().abs16(opcode, target)

            def rel8(self, opcode, target):
                _, _, lengthen = self.select(opcode, target, True)
                if lengthen:
                    self.changed.append(dict(address=self.pc, target=target, before='jr', after='jp'))
                    super().abs16({0x20:0xc2,0x28:0xca,0x30:0xd2,0x38:0xda}[opcode], target)
                else:
                    super().rel8(opcode, target)

            def resolve(self, external_labels=None):
                labels = self.labels | (external_labels or {})
                for position, target in self.rel_fixups:
                    if not -128 <= labels[target]-(self.origin+position+1) <= 127:
                        if position in self.shortened:
                            raise RelativeOverflow(self.shortened[position])
                return super().resolve(external_labels)

        try:
            with patch.object(module, 'MiniAssembler', TunedAssembler):
                if codec == 'lzsa2':
                    profile = (lblock(core=core, core_limit=core_limit, **options) if resident else
                               lzsa_coroutine.build(core=core, core_limit=core_limit, **options))
                else:
                    profile = (zx0_block.build(core=core, core_limit=core_limit, **options) if resident else
                               zx0_coroutine.build(core=core, core_limit=core_limit, **options))
        except RelativeOverflow as error:
            assert error.site not in excluded
            excluded.add(error.site)
            continue
        changes = [row for instance in instances for row in instance.changed]
        metadata = dict(profile[2], branch_tuned=True, branch_changes=changes,
                        relative_overflow_fallbacks=[list(site) for site in sorted(excluded)])
        if 'instruction_listing' in metadata:
            changed = {row['address']:row for row in changes}
            rows = []
            for original in metadata['instruction_listing']:
                row = dict(original)
                if row['address'] in changed:
                    item = changed[row['address']]
                    row.update(instruction=item['after'].upper()+' '+item['target'],
                               tstates=[7,12] if item['after']=='jr' else 10)
                rows.append(row)
            metadata['instruction_listing'] = rows
        return profile[0], profile[1], metadata
