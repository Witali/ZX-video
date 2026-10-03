"""Instrument the pinned Fuse libretro tree without changing Z80 timing.

One dispatch includes prefixes; each repeated block iteration is a dispatch.
The initial HALT is an instruction; subsequent halted M1 cycles are idle.
"""
from pathlib import Path
import argparse
import re


COUNTERS = r'''
#include <stdint.h>
#include <string.h>
uint64_t retro_survey_contention;
/* count, base T, elapsed T, idle M1 count, idle T, initial HALTs */
static uint64_t survey[3][6], survey_hist[3][256];
static uint64_t survey_block_repeats[3];
static uint32_t survey_start;
static uint64_t survey_contention_start;
static unsigned survey_group, survey_idle, survey_pc, survey_block;
void retro_survey_reset(void) {
  memset(survey, 0, sizeof(survey));
  memset(survey_hist, 0, sizeof(survey_hist));
  memset(survey_block_repeats, 0, sizeof(survey_block_repeats));
}
void retro_survey_blocks(uint64_t *out) { memcpy(out, survey_block_repeats, sizeof(survey_block_repeats)); }
void retro_survey_read(uint64_t *out) {
  memcpy(out, survey, sizeof(survey));
  memcpy(out + 18, survey_hist, sizeof(survey_hist));
}
static void survey_begin(void) {
  survey_start = tstates;
  survey_contention_start = retro_survey_contention;
  survey_idle = z80.halted;
  survey_group = PC >= 0x4000 ? 0 : beta_active ? 2 : 1;
  survey_pc = PC;
  survey_block = readbyte_internal(PC) == 0xed &&
    ((readbyte_internal((PC+1)&65535) & 0xf4) == 0xb0);
}
static void survey_end(void) {
  uint32_t elapsed = tstates - survey_start;
  uint32_t base = elapsed - (retro_survey_contention - survey_contention_start);
  uint64_t *s = survey[survey_group];
  if(survey_idle) { s[3]++; s[4] += elapsed; return; }
  s[0]++; s[1] += base; s[2] += elapsed;
  if(survey_block && PC == survey_pc) survey_block_repeats[survey_group]++;
  if(z80.halted) s[5]++;
  survey_hist[survey_group][base < 255 ? base : 255]++;
}
'''


def patch(root: Path):
    ops = root / 'fuse/z80/z80_ops.c'
    s = ops.read_text()
    if 'survey_begin' in s:
        raise ValueError('Source is already instrumented')
    needle = '#include "z80_macros.h"'
    assert s.count(needle) == 1
    s = s.replace(needle, needle + '\n' + COUNTERS)
    s = s.replace('  opcode_delay:\n', '  opcode_delay:\n    survey_begin();\n')
    needle = '#include "z80/opcodes_base.c"\n    }'
    assert s.count(needle) == 1
    s = s.replace(needle, needle + '\n    survey_end();')
    ops.write_text(s)
    # Count every existing ULA delay at its original evaluation point.
    for rel in ['fuse/z80/z80_macros.h', 'fuse/memory_pages.c',
                'fuse/peripherals/ula.c']:
        path = root / rel
        s = path.read_text()
        s = '#include <stdint.h>\nextern uint64_t retro_survey_contention;\n' + s
        s, n = re.subn(r'tstates \+= (ula_contention(?:_no_mreq)?\[ tstates \]);',
                      r'tstates += (retro_survey_contention += \1, \1);', s)
        assert n > 0, rel
        path.write_text(s)
    path = root / 'fuse/spectrum.c'
    s = path.read_text()
    s += '''
#include <stdint.h>
uint64_t retro_survey_clock(void) {
  return (uint64_t)frames_since_reset * machine_current->timings.tstates_per_frame + tstates;
}
unsigned retro_survey_frame_length(void) {
  return machine_current->timings.tstates_per_frame;
}
const char *retro_survey_machine(void) { return machine_current->id; }
'''
    path.write_text(s)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    patch(ap.parse_args().source)
