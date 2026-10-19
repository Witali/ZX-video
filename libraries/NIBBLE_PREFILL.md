# Optional LZSA2 pre-normalized nibble cache

Measured 2026-10-19 against `674a1fc8`, with the unchanged real raw-v2
blocks authenticated by `tests/measure_long_copy.py`. The active approximately
10% goal still uses `f5a0362c`; this smaller intermediate gain does not complete
that goal. ZX0 and existing defaults are unchanged.

`lzsa.block.build(nibble_prefill=True)` and
`lzsa.resumable.build(nibble_prefill=True)` pre-normalize the spare low nibble
in AF'. The CLI equivalent is `--nibble-prefill`. Small remains independent.
The option combines with the existing Fast branch/copy/streaming policies.

The old refill reads a byte, clears carry with `OR A`, saves it in AF', reads
the same byte again and rotates its high nibble into place. Every nibble then
passes through `OR F0h`. The new refill uses `OR F0h` for the cached byte and
branches past the final OR when returning the cached low nibble. Carry still
means refill when set and cache available when clear. The main AF carry from
SCF or offset dispatch still marks a consumed cache; IRQ and suspension must
preserve the complete AF' as before. No source byte is modified.

| Path, excluding the optional entry SCF | Before | After | Difference |
| --- | ---: | ---: | ---: |
| Refill | 62 T | 65 T | +3 T |
| Cached low nibble | 23 T | 16 T | -7 T |
| Complete pair | 85 T | 81 T | -4 T |

The refill sum is `EX AF,AF'` 4 + untaken `JR NC` 7 + `LD A,(HL)` 7 +
`OR A` 4 / `OR F0h` 7 + `EX AF,AF'` 4 + `LD A,(HL)` 7 + `INC HL` 6 +
four `RRCA` 16 + final `OR F0h` 7. The cached path is exchange 4 + taken
branch 12 + old final OR 7 / no OR 0. Entry SCF costs another 4 T on literal
and match-length paths in both versions. Four duplicated refill sites each
grow by one byte. The declared timing source remains Zilog UM0080; native
execution verifies both phases for every byte at all four sites, including
the resulting documented and undocumented OR flags.

| Complete 21-real-block profile | Before | After | Saved | Code bytes |
| --- | ---: | ---: | ---: | ---: |
| Fast resident + fast_jumps + branch_tuned | 17,714,484 T | 17,635,500 T | 78,984 T / 0.445872% | 220 -> 224 |
| Same ordinary coroutine, 256-byte demands | 19,356,394 T | 19,277,410 T | 78,984 T / 0.408051% | 387 -> 391 |
| Resident with long_copy + near_literals | 17,689,106 T | 17,610,122 T | 78,984 T / 0.446512% | 303 -> 307 |
| Same coroutine + restore_compare | 19,324,686 T | 19,245,702 T | 78,984 T / 0.408721% | 468 -> 472 |

All real blocks improve. A block ending after an unmatched refill can be
slower: literal-1, literal-2 and the two directed single-nibble EOF forms each
cost 3 T more. Across each ordinary coroutine profile, 17 slices are slower,
maximum +3 T. The option stays explicit; aggregate savings are not a promise
of faster execution for every valid input or slice.

The [complete native report](evidence/ten_percent_nibble_prefill.json) covers
eight configurations, each with 95 existing real/directed/random blocks and
`EF 41 F0 E8 -> 41` / `E7 F0 E8 -> empty`: 776 complete baseline/candidate
comparisons, each also passing relocation to 9103h and IRQ replay. Every byte
value passes both nibble phases at all four sites. EOF consumes exactly the
payload; no synthetic trailing word is read. Legal short word escapes,
distance-1/2 overlap, preserved alternate pairs, IX and caller SP remain checked.

Both guarded input modes pass 63 complete cases at six placements, including
all 21 real blocks and 18 legal short word escapes. CALL-mode total producer
and decoder CPU improves 29,563,863 -> 29,484,761 T; direct mode improves
27,347,392 -> 27,268,290 T. Each saves 79,102 T. Producers, input waits, output
slices and 772 once-only sectors remain exact. There are 32 slower slices per
mode out of 2,670, maximum +3 T; no real block slows overall. Core code grows
four bytes; cold wrapper/state extents, stack, compressed data and rounded
code-region sector counts stay unchanged. The two single-nibble EOF forms
also pass both guarded modes independently at every placement.

Both guarded modes additionally pass all 65 cases at six placements with
long_copy, word_state_init, restore_compare, fast_jumps and branch_tuned
enabled together. Baseline/candidate input waits agree, and every 253-byte
placement also passes IRQ replay. The saved combination report retains the
per-placement slower cases instead of treating aggregate savings as universal.

The [verification summary](evidence/nibble_prefill_verification.json) binds
the reports to source hashes and historical guarded-input hashes. It preserves
29 passing library unit tests, all 31 frozen default byte/address profiles,
six upstream resources and generated assembly/CLI checks. No wheel reinstall,
external compressor rerun, physical disk, ROM, ULA or movie publication timing
is claimed. The producer comparison measures deterministic player CPU only.

Reproduction uses the existing `z80==1.2.0` dependency and package/test/toolkit
source paths, with TMP/TEMP inside the worktree:

```powershell
python -m unittest discover -s libraries/tests -v *> .tmp/nibble-library-tests.log
python libraries/tests/measure_nibble_prefill.py --output libraries/evidence/ten_percent_nibble_prefill.json
python -c "import gzip,pathlib; p=pathlib.Path('.tmp'); f=pathlib.Path('toolkit/row_lzsa_evidence'); [(p/n).write_bytes(gzip.decompress((f/(n+'.gz')).read_bytes())) for n in ('video.stream','video.raw')]"
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --branch-tuned --nibble-prefill --output libraries/evidence/nibble_prefill_streaming_call.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --branch-tuned --nibble-prefill --direct-header --output libraries/evidence/nibble_prefill_streaming_direct.json
python libraries/tests/measure_nibble_stream_combinations.py --output .tmp/nibble-stream-combinations.json
python libraries/tests/summarize_nibble_prefill.py --directory .tmp --output libraries/evidence/nibble_prefill_verification.json
```

Full guarded JSON and successful unit logs are stored as indexed gzip
archives under `evidence/nibble_prefill/`; the summary consumes freshly
reproduced uncompressed files.
