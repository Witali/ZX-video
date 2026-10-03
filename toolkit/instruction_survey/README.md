# Measured Z80 instruction timing on eight TR-DOS disks

Measured on 2026-10-03 in response to the request for an empirical average
on typical Spectrum disk software. The selected windows execute **79,425,697
instructions/iterations in 698,325,097 nominal CPU T-states: 8.792181 T per
instruction**. The equal-program arithmetic mean is 8.742091 T. The five
games alone have an instruction-weighted mean of 8.870355 T.

This is a small, deliberately varied convenience sample, not a population
estimate for all Spectrum software. Each selected interval is 1,500 emulated
frames, approximately 30.72 seconds. Total selected emulated time is 245.76 s.
The longer cold runs, including discovery of startup screens, are separate
from these selected intervals. There is no complete-game or hardware claim.

## Results

The machine is **Pentagon 128K + Beta Disk**, 3,500,000 Hz, 71,680 T/frame.
Its lack of ULA contention makes nominal and active elapsed instruction
timings equal. These are not measurements of the contention overhead on an
original Sinclair 128K. That overhead depends on addresses and display phase.

| Program | Observed activity | Instructions/iterations | Mean T | HALT idle share of elapsed time |
|---|---|---:|---:|---:|
| Dizzy | First forest screen, movement/jump input | 10,888,517 | 9.872005 | 0.00% |
| Elite | Space flight after launch, no steering | 10,761,198 | 9.477785 | 5.12% |
| Exolon | First screen after restart, scripted keys | 14,049,267 | 7.653069 | 0.00% |
| R-Type | First level, movement and firing | 11,625,404 | 7.791451 | 15.73% |
| Renegade 128 | First fight, enemies active, no player input | 8,177,318 | 10.362469 | 21.16% |
| Aeon | Running visual demo effects | 10,821,794 | 8.017449 | 19.28% |
| 63 BIT | Trackmo credits/menu; not the whole demo | 1,579,682 | 7.432900 | 89.05% |
| Beta Commander 5.02+ | Idle directory display and key polling | 11,522,517 | 9.329602 | 0.00% |

The minimum and maximum observed nominal dispatch costs are **4 and 23 T**.
The most common costs are 4 T (24.457%), 7 T (22.354%), 10 T (10.130%),
11 T (10.026%), 12 T (8.239%), and 13 T (6.739%). The complete histogram is
in [summary.json](evidence/summary.json).

At 3.5 MHz, 8.792181 T corresponds to 2.512 microseconds per active
instruction, or about 398,000 instructions/s while executing. This is an
aggregate estimate; exact code-path timings are still required for deadlines.

## What is counted

- Count a completed dispatch in Fuse's Z80 interpreter, including opcode
  prefixes. Conditional instructions are charged for their actual branch.
- Count each iteration of repeating block instructions such as LDIR/CPIR
  separately, matching their 21/16-T timing-table entries. This is the
  convention used for the main result, not an assertion that the entire
  block copy takes 21 T. Subtracting the 993,436 repeated continuations from
  the denominator gives **8.903544 T** when each whole block operation is
  counted once. Block operations crossing a sample boundary have the usual
  boundary attribution ambiguity; the primary per-iteration result does not.
- Count the first HALT as a 4-T instruction. Exclude subsequent halted M1
  cycles from both the instruction count and active CPU time. Save them
  separately: 40,411,804 idle M1 cycles / 161,647,216 T in the selected data.
- Count instructions executed in RAM, Spectrum ROM and TR-DOS ROM in
  separate buckets, including ordinary instructions in interrupt handlers.
  Hardware interrupt entry time is outside an opcode and is not charged to
  the neighboring instruction. The selected clock remainder is 187,688 T.
- Record existing ULA memory and I/O delays at their original application
  points without removing them from emulation. Subtract them only when
  calculating the nominal cost. All selected Pentagon delays are zero.

All selected time reconciles as
`698325097 active + 161647216 HALT idle + 187688 outside instructions = 860160001 T`.
If all elapsed time, including idle and interrupt entry, is divided by the
same executed-instruction count, the result becomes **10.829744 T**. That is
a throughput measure, not the intrinsic average instruction cost. Counting
each idle HALT M1 cycle as another command would instead bias the result
toward 4 T, especially for 63 BIT.

## Startup and disk code

The first 500 frames are retained as a cold-start window. They can include
loading, decompression, crack intros and menus; they are **not** labeled as
pure loading time. TR-DOS values below come only from executed ROM opcodes
over the complete run through the selected window's end.

| Program | Cold first 500 frames, mean T | TR-DOS ROM instructions in whole run | TR-DOS ROM mean T |
|---|---:|---:|---:|
| Dizzy | 8.530586 | 4,934,486 | 8.484088 |
| Elite | 8.766219 | 4,313,649 | 8.465334 |
| Exolon | 8.676098 | 4,414,178 | 8.566957 |
| R-Type | 8.987756 | 6,729,774 | 8.385074 |
| Renegade 128 | 9.133969 | 4,701,002 | 9.340427 |
| Aeon | 8.598638 | 6,215,273 | 8.243556 |
| 63 BIT | 8.277175 | 4,205,758 | 8.562282 |
| Beta Commander | 8.684888 | 3,785,179 | 8.582487 |

Disk waiting is represented by whatever polling or HALT the program actually
executes. Do not add the physical sector latency to a single Z80 instruction.
This emulator result is not a measurement of a real drive's latency.

## Validation and evidence

[validate.py](validate.py) independently constructs a program with known
timing-table counts: 2,073 instructions/iterations and 20,705 nominal T.
It checks taken/untaken loop branches, LDIR's two repeated iterations and
one final iteration, indexed memory, a redundant DD prefix, CB rotation,
conditional JR and the distinction between initial HALT and idle cycles.
On the 48K model, contended reads give 21,440 active elapsed T (+735);
the same program with uncontended data gives exactly 20,705 T. Both
histograms and zero outside-instruction remainders pass. These two tests
deliberately use 48K snapshots; snapshot machine selection is reported as
48K rather than pretending a requested Pentagon option overrides it.

- [Validation results](evidence/validation.json)
- [All final counters and derived statistics](evidence/summary.json)
- [Source, build and ROM provenance](evidence/provenance.json)
- The eight `*-raw.json.gz` files preserve all 500-frame windows from cold
  start, group counters, histograms, key schedules, and screenshot hashes.
- [Sample screenshots](evidence/screens.png), visually inspected at all
  three selected endpoints. Rows follow the results table; columns are the
  first, second and third 500-frame endpoints within each selected interval.

Exploratory runs identified menus and controls before selecting active
intervals. In particular, R-Type needs six redefined keys including Detach.
F Commander 5.5 was downloaded but returned to the Spectrum menu; renaming
its first BASIC entry to `boot` in an ignored local copy did not fix it.
It is excluded, and Beta Commander 5.02+ is used instead. Initial validation
requested two models with the same 48K snapshot, which correctly loaded as
48K in both cases; final validation explicitly compares two memory regions
on 48K. No failed pilot is included as successful gameplay evidence.

## Reproduction

Uses the [Fuse libretro source](https://github.com/libretro/fuse-libretro/tree/e997e2bc32c888348f862f69f2c53babfedf7791)
at commit `e997e2bc32c888348f862f69f2c53babfedf7791` (Fuse 1.6.0 core),
GCC 13.3.0 on Ubuntu 24.04/WSL and Python 3.12.3. The original downloaded
tree was compared against the commit archive: all 871 source files match.
[prepare.py](prepare.py) verifies the pinned archive hash before building.
Use a fresh ignored work directory and existing legitimate Pentagon/TR-DOS
ROMs. No new ROM download is required.

From Ubuntu/WSL, with the repository as the current directory:

```sh
python3 toolkit/instruction_survey/prepare.py --work .tmp/instruction-survey-repro --roms tools/fuse-1.9.0-sdl/roms
python3 toolkit/instruction_survey/fetch.py .tmp/instruction-survey-repro/disks
python3 toolkit/instruction_survey/validate.py --core .tmp/instruction-survey-repro/fuse-libretro-master/fuse_libretro.so --system .tmp/instruction-survey-repro/system --out .tmp/instruction-survey-repro/validation
python3 toolkit/instruction_survey/survey.py --work .tmp/instruction-survey-repro
```

[cases.json](cases.json) fixes every input and sample interval. The manifest
in the results records exact [Virtual TR-DOS](https://trd.speccy.cz/)
download URLs, archive hashes, member names and disk hashes. Disk images,
ROMs, emulator binaries and temporary files are kept outside Git; the
repository contains scripts and compact measurement evidence. This is a
profiling study, not a change to the ZX-video player or a release image.
The instruction-table reference is the
[Zilog Z80 CPU User Manual](https://www.zilog.com/docs/z80/um0080.pdf).
