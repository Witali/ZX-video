"""Optional measured branch layout, private to each independently shipped package."""
from ._z80 import MiniAssembler


class _RelativeOverflow(Exception):
    def __init__(self, site):
        self.site = site


def tune(builder, options, codec, *, compact=False):
    """Rebuild a private assembler until every selected short branch fits.

    Frequencies come from the complete frozen 2026-10-19 real corpus. Compact
    LZSA2 selects only Case11x: JP NC is 10 T, JR NC is 7/12 T, saving one
    byte and 3 T on fallthrough while costing 2 T when taken. The older
    branch_tuned policy additionally lengthens two other branches unchanged.
    The policy trades JR's 7/12 T for JP's constant 10 T, without changing branch
    conditions or flags. It is optional: individual artificial inputs can be
    slower. Per-call factories avoid changing any global assembler or builder.
    """
    excluded = set()
    while True:
        instances = []

        class TunedAssembler(MiniAssembler):
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
                    lengthen = not compact and relative and op == 0x30 and target in ('MatchLen', 'CopyMoreLiterals')
                else:
                    shorten = not relative and (
                        (op == 0xd2 and normalized in ('gamma_loop', 'LongerMatch', 'LongerOffets', 'LongerRun', 'LongerRepMatch'))
                        or (op == 0xda and target in ('UsualMatch', 'CopyMatch2', 'ShorterOffsets', 'CopyLiteral'))
                        or (op == 0xc2 and target == 'CopyLiterals'))
                    lengthen = False
                return site, shorten and site not in excluded, lengthen

            def abs16(self, opcode, target):
                site, shorten, _ = self.select(opcode if isinstance(opcode, int) else -1, target, False)
                if shorten:
                    self.shortened[len(self.code)+1] = site
                    self.changed.append(dict(address=self.pc, target=target, before='jp', after='jr'))
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
                            raise _RelativeOverflow(self.shortened[position])
                return super().resolve(external_labels)

        try:
            profile = builder(**options, branch_tuned=False, _assembler=TunedAssembler)
        except _RelativeOverflow as error:
            assert error.site not in excluded
            excluded.add(error.site)
            continue
        changes = [row for instance in instances for row in instance.changed]
        policy = dict(compact_branches=True) if compact else dict(branch_tuned=True)
        metadata = dict(profile[2], **policy, branch_changes=changes,
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
