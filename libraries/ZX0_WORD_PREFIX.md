# ZX0 shared word-copy prefix within 10,000 service bytes

Completed 2026-10-20 after the independently committed initial maximum-speed
frontier `6759dedf`. The cap127 decoder left enough service memory to test
longer gamma-proven word copies. This bounded extension retains that complete
evidence and adds two measured profiles. Current `zx0.maximum.build()` and
CLI `--variant maximum` default to cap228; caps31/63/127/227 remain selectable.
No old public profile changes.

## Measured frontier and complete memory

The library service count includes all emitted code/embedded variables and
four maximum stack bytes, including the caller return. Extra state, tables,
alignment, scratch, private stack and internal buffers are zero. Input/output/
history are explicitly separate, as authorized. Both new profiles preserve
the resident Fast ABI, writable offset and complete resident source/history
requirements described in [the initial audit](ZX0_MAXIMUM.md).

| Prefix cap | Code | Library service | With minimal IRQ | With diagnostic full-AF IRQ | Real CPU T |
| --- | ---: | ---: | ---: | ---: | ---: |
| 127 | 7,522 | 7,526 | 7,531 | 7,545 | 140,193,198 |
| 227 | 9,962 | 9,966 | 9,971 | 9,985 | 140,170,198 |
| 228 (current default) | 9,986 | 9,990 | 9,995 | 10,009 (diagnostic only) | 140,169,968 |
| 229 (size-only rejection) | 10,010 | 10,014 | 10,019 | 10,033 | Not executed |
| 255 (size-only rejection) | 10,634 | 10,638 | 10,643 | 10,657 | Not executed |

Cap228 is a valid library option under the hard10,000-byte service limit.
Its actually replayed minimal register-preserving IM1 handler is EI;RETI:
three instruction bytes plus two hardware-pushed stack bytes, for9,995total.
The diagnostic handler saves/touches AF/AF' before restoring them; its13code
bytes and six extra stack bytes give10,009with cap228. That larger diagnostic
application footprint exceeds10,000and is reported explicitly. Choose cap227
to fit that handler at9,985bytes. A caller doing useful IRQ work must count
its actual code, state and stack; `irq_code_bytes`/`irq_stack_bytes` enforce
the chosen reservation, so cap228 with13/6 is rejected by the public API/CLI.
The decoder does not require either example IRQ implementation.

Example exports, with the caller providing the corresponding handler:

```powershell
python -m zx0 build --variant maximum --irq-code-bytes 3 --irq-stack-bytes 2 --output build/zx0-maximum
python -m zx0 build --variant maximum --prefix-cap 227 --irq-code-bytes 13 --irq-stack-bytes 6 --output build/zx0-maximum-full-af
```

This is the largest tested fitting prefix in this fixed suffix-sharing
layout. It is not a proof of the fastest possible decoder under the limit.
The next cap229already exceeds the library cap at10,014bytes; each extra
prefix byte costs24code bytes across the twelve phase/family clones.
Cap255 is also rejected by exact assembled size even before IRQ accounting;
do not infer that every other algorithm or branch layout has been searched.

## Transformation, counts and comparison

The existing cap127 path copies127bytes inline after gamma proves BC>=128.
At the deeper word exit, gamma proves BC>=256. Instead of duplicating a full
large-copy body per phase, the new entry saves source/loads the offset once,
copies100or101bytes with LDI, then jumps after the existing prologue into its
shared127-LDI suffix. The suffix begins with BC>=156or155 respectively and
leaves at least29or28bytes for positive-count LDIR. It retains forward overlap
semantics and the original source POP. Gamma's full RL B word shifts remain.
No runtime selector or new state is introduced.

Original word join and new shared-prefix join both use one10-T JP. Every
additional LDI replaces a repeating21-T LDIR iteration with16T. Thus each
word entry saves exactly500T at cap227 or505T at cap228 versus cap127. The
141entries across the417-case corpus give70,500 /71,205T;46real entries give
23,000 /23,230T. The56-case high-word supplement has45entries, saving22,500 /
22,725T. Every case matches both this independent count and the complete
instruction formula from the original audit. Dynamic observers count a shared
literal suffix once while still asserting its residual BC bound at the join.

The complete real corpus at cap228 is140,169,968T:

- Versus cap127140,193,198T: new23,230T,0.016570% gain for2,464extra code bytes.
- Versus tunedMega670B/145,701,295T: new combined5,531,327T,3.796347% gain.
- Versus original unmodifiedMega673B/146,422,274T:6,252,306T total difference.
- Versus originalFast207B/156,012,520T:10.154667% total difference, including
  the pre-existing Mega advantage. That old benefit is not a new optimization.

All417-case CPU at cap227/228 is145,283,522 /145,282,817T versus cap127
145,354,022T and tunedMega151,153,149T. High-word totals are17,161,212 /
17,160,987T versus cap12717,183,712T. No complete case slows versus cap127,
tunedMega or originalFast. Individual changed conditional exits still cost
3T more when untaken, as already documented. There is no coroutine ABI or
slice comparison. Counts exclude IRQservice/ULA/WAIT/ROM/paging/physical disk;
payload and required input-sector differences are zero. Larger code can affect
application allocation; no player/movie delivery is qualified.

## Verification and reproduction

Each new cap passes all417original cases and56high-word cases, including
32767/32768/49151-byte reused/new-offset matches. Per case: plain protected
replay, full-AF diagnostic IRQ, minimal IRQ and relocated replay. Including
shared baselines:946candidate comparisons and4,257complete native runs.
Plain/full-AF/minimal maximum stack is4/10/6bytes. Both handlers actually
interrupt long blocks; all output/history/input/EOF/register checks pass.

Wide high-word code is at0800h and relocated0703h, input0400h, output3000h,
callerSP2ff0h. Cap228 code ends2f02h; the guarded caller/IRQ stack starts2fb0h.
Every live region is checked disjoint before execution. The earlier0903h
relocation used by smaller profiles would overlap this guarded stack at the
new size, so it is not used for the wide supplement. No overlapping run was
accepted as evidence. Main-corpus origins remain8000h/9103h.

All31library tests pass. All31frozen default profiles and six pinned resources
remain byte-exact. All five frontier API/CLI/ORG-DB exports pass in an isolated
installed wheel, with no test/toolkit/numpy imports. Public byte/label layouts
match the independent prototype at four origins. Generated comments describe
the shared suffix, BC bounds, one-time match setup, word arithmetic and stack.

With native dependencies on PYTHONPATH and writable TMP/TEMP:

```powershell
python libraries/tests/measure_mega_prefix.py --public --caps 227 228 --minimal-irq --output libraries/evidence/ten_percent_maximum_word_prefix.json
python libraries/tests/measure_mega_prefix.py --public --caps 227 228 --minimal-irq --high-word --output libraries/evidence/ten_percent_maximum_word_prefix_high_word.json
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/maximum-word-prefix-final-wheels libraries/zx0
python -m pip install --no-index --no-deps --target .tmp/maximum-word-prefix-final-installed .tmp/maximum-word-prefix-final-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_install.py .tmp/maximum-word-prefix-final-installed zx0 .tmp/maximum-word-prefix-final-smoke
python libraries/tests/verify_maximum_word_prefix.py --output libraries/evidence/ten_percent_maximum_word_prefix_verification.json
```

Save command output to`.tmp/maximum-word-prefix-{native,high-word,unit,wheel,
install,smoke}.log` in the corresponding order. Authentication includes exact
assembled sizes of227/228/229/255, source/input/wheel hashes and archived logs.

- [Complete original-corpus comparisons](evidence/ten_percent_maximum_word_prefix.json).
- [Complete high-word supplement](evidence/ten_percent_maximum_word_prefix_high_word.json).
- [Source, wheel, memory and log authentication](evidence/ten_percent_maximum_word_prefix_verification.json).

Accept both optional measured points and retain cap228 as maximum-direction
default. The new word-prefix gain is small; the broader per-library/coroutine
goal remains active, and global optimality is not established.
