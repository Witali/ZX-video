# CPU execution and shared-event loop

Baseline: `aef79237` on 2026-11-04. This changes host execution overhead,
not the instruction decoder, guest instruction timing, contention model,
TRD layout, drive rotation, AY synthesis or emulator frequency.

## Final implementation

The old clock called the CPU, read its cycle counter, updated the absolute
clock and checked the event queue after every instruction/prefix step. The
new CPU loop runs the same interpreter and checks the next device deadline
locally. It calls the clock's dispatcher only when a device is due. A newly
scheduled I/O event immediately shortens that deadline. The existing paced
host budget remains unchanged; no instructions, M1 reads, refresh increments,
interrupt boundaries, disk waits or audio samples are skipped.

Ports still observe the beginning of their current CPU step, matching the
previous core rather than exposing partially accrued operand cycles. The
debugger retains the original step loop. Exceptions retain its last
instruction-start timestamp. Guest T-state counts and target RAM change by
**0 T / 0 bytes**. Both `process()` and state APIs retain their contracts.
[Reproducible guarded source patch](../../tools/patch-cpu-slices.mjs).

## Performance and limits

The four shared [workloads](../../tools/cpu-clock-workload.js) use the actual
Z80, banked RAM, bus and 50-Hz interrupt queue: arithmetic/flags, LDIR copying,
DD/CB memory operations, and DJNZ/CALL/RET flow. Each fresh trial warms up for
one emulated second, then times twenty. Setup, mapped-memory hashing and
identity checks are outside timing. Five before/after pairs alternate order.
They are CPU/clock workloads with no audio or graphics, not application FPS.

| Node 22.22.3 workload | Before | After | Time reduction |
| --- | ---: | ---: | ---: |
| Arithmetic/flags | 475.587 ms | 445.736 ms | 6.28% |
| LDIR copy | 180.675 ms | 155.149 ms | 14.13% |
| Indexed memory/CB | 262.829 ms | 235.819 ms | 10.28% |
| Branch/stack flow | 197.688 ms | 177.368 ms | 10.28% |

[Node samples](node-clock.json) and [built-in-browser samples](browser.json)
retain the alternating trials and exact CPU/RAM/interrupt identities. These
are observations on this host, with visible timing spread, not cross-device
or physical-board qualification.

The final built-in Chromium trial medians improve by **9.15% / 11.32% /
7.50% / 8.69%**, respectively (430.4 -> 391.0, 167.9 -> 148.9,
253.3 -> 234.3 and 166.9 -> 152.4 ms). Retain the individual pairs rather
than treating these medians as guaranteed gains on every run.

The same existing real-ROM/TRD/CPU/AY workload remains dominated by other
work: the 66.2-second music workload median is **3759.231 -> 3857.049 ms**
(2.60% slower); the 60-second video-disk workload is **3880.997 -> 3870.701 ms**
(0.27% faster). Treat these small, noisy complete-machine results as no
established overall application-speed gain. Every PCM packet, mapped 64 KiB,
CPU register, emulated clock, PSG and disk state matches exactly in all pairs.
[Music](machine.json), [video workload](movie.json). The video test is a
differential workload, not full-movie frame/deadline qualification.

## Correctness

[Instruction-boundary checks](boundaries.json) compare the previous core
against the new loop under regular/irregular callbacks, catch-up, frequency
changes, pause/resume and debug stepping. They compare complete M1/I/O/event
traces, memory, CPU and clocks, including IRQ/NMI, canceled/repeating tasks,
nested immediate tasks and I/O events earlier than the previous deadline.
A fractional event at 129998.00000000001 T guards the initial rounding issue.
CI additionally checks the new core against its retained single-step path.
Pinned Fuse instruction vectors and shared-clock checks remain independent.

## Rejected attempts

- A first version returned from the CPU to the clock at every device event.
  It improved isolated CPU tests but slowed the full AY workload by **15.80%**
  (3832.047 -> 4437.398 ms). Preserve [that run](rejected-always-machine.json)
  and [its browser trials](rejected-browser.json); it is not shipped.
- A guarded version fell back to stepping with dense repeat intervals. Its
  music median 4118.795 -> 4082.814 ms (0.87%) is inconclusive, and the normal
  browser player always has a dense AY sample clock. Reject that inert
  application optimization; [samples](rejected-guarded-machine.json).
- The final loop dispatches events without returning to the host clock on
  every event, eliminating that intermediate boundary overhead.
- Earlier one-shot probes of opcode-family functions, numeric flag stores,
  specialized LD handlers and common-opcode paths did not justify promotion;
  the original interpreter remains byte-identical. Initial VM probes were
  corrected to capture local CPU/memory references rather than measure VM
  global-proxy lookups. A mismatched comment anchor and the first fractional
  slice calculation failed locally; only corrected variants were timed.

## Reproduce

Save baseline `web/vendor/zx-dream.js` from `aef79237` byte-for-byte as
`.tmp/baseline-zx-dream.js`. Materialize the authenticated disks and use the
pinned ZX-Dream/Fuse sources documented in the vendor README.

```powershell
node web/tools/vendor-emulator.mjs C:/path/to/zx-dream 'C:/Program Files (x86)/Fuse/roms'
node web/tools/check-cpu-slices.mjs .tmp/boundaries.json .tmp/baseline-zx-dream.js
node web/tools/bench-cpu-clock.mjs .tmp/baseline-zx-dream.js web/vendor/zx-dream.js .tmp/cpu-clock.json
node web/tools/build.mjs .tmp/web-site
node web/tools/bench-cpu-machine.mjs .tmp/baseline-zx-dream.js web/vendor/zx-dream.js .tmp/web-site .tmp/music.json
node web/tools/bench-cpu-machine.mjs .tmp/baseline-zx-dream.js web/vendor/zx-dream.js .tmp/web-site .tmp/movie.json movie
```

For browser timing, copy the baseline/candidate cores as `baseline.js` and
`candidate.js` beside [cpu-benchmark.html](../../tools/cpu-benchmark.html) and
`cpu-clock-workload.js` in a locally served directory. Run **Run CPU benchmark**
in the built-in browser without concurrent heavy work. Development fixtures
remain outside the Pages artifact.
