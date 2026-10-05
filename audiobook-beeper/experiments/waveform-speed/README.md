# Exact PC waveform-search acceleration

Requested 2026-10-04 after the normalized Entertainer conversion. The old
1024-wide /256-sample-horizon IMA3 pass took 2723.703 s for 186880 prepared
samples. It advances only 64 samples per horizon: approximately 746624
sample-search steps, each expanding up to 8192 candidates. Array allocation,
copying and sorting amplify that work. This change targets PC waveform
encoding, not the legacy IMA4 PCM search or Spectrum decoding.

## Changes

- Reuse the error scratch array and broadcast common parent responses.
- Keep parent backpointers, reconstructing only the winning path once per
  horizon instead of copying every complete path at every step.
- Propagate filter states only for retained candidates when history bins
  are disabled, the normal production setting.
- NumPy fallback: sort one integer state key, reduce equivalent states,
  partition the winners, then sort only the retained beam and boundary ties.
- Optional C backend: fuse elementwise error terms without intermediate
  arrays, hash-merge decoder states, and select a bounded max-heap. Preserve
  candidate-ID tie breaks and exactly the original floating-point order.
  NumPy still performs the final 16-term pairwise reduction. No fast-math or
  float32 arithmetic is used.

`waveform_kernel.py` contains the small C implementation so that the existing
producer-source hashes cover it. It builds with installed MSVC x64 or cc,
using private build directories and atomically publishing complete libraries
in the ignored cache. There is no download or mandatory new dependency.
Auto mode falls back to NumPy when no suitable compiler is available.
The first attempted MSVC command incorrectly escaped the batch path and
fell back safely with an exact stream; cmd-specific quoting fixed the build.

Beam widths, horizons, regularization, allowed codes, overlap and quality
gates are unchanged. Z80/player source, RAM format and release TRDs are
unchanged: IMA3 ordinary cost 427.375 T/sample, delta 0 T; +14/+140 T page/bank
extras remain unchanged. No native-player timing improvement is claimed.

## Reproduction

Use the project Python dependencies and put `audiobook-beeper` and `toolkit`
on PYTHONPATH. The saved pilot files reconstruct the exact old timing model;
the archived baseline is the unmodified pre-change encoder. The benchmark
sets one OpenBLAS thread for comparable small matrix operations.

```powershell
python audiobook-beeper/experiments/waveform-speed/test_search.py
python audiobook-beeper/experiments/waveform-speed/reproduce.py --output build/waveform-speed --full
```

The output directory must be new. Tests require the native backend so that
a missing compiler cannot silently substitute the fallback during testing.
They cover tied costs, duplicate keys/collisions, floating-point error terms,
IMA3/IMA4 alphabets, reordered codes, narrow beams, history bins, overlap,
partial horizons, and automatic fallback. Full reproduction checks the three
complete encoded streams against the saved normalized Entertainer attempts.
Because those bytes and the player are unchanged, their existing complete
native/Fuse timing and quality evidence remains applicable. This experiment
does not introduce a new disk or a new quality claim.

## Results

Three repeats time the same `encode_waveform` function on 2048 searched
samples, with width 1024, horizon 256, commit 64 and regularization 0.03.
The median comparison is directly like-for-like:

| Backend | Median seconds | Speedup | Encoded bytes |
| --- | ---: | ---: | --- |
| Archived baseline | 22.766993 | 1.000x | Reference |
| Optimized NumPy | 12.571314 | 1.811x | Exact match |
| Optional native kernel | 5.589146 | 4.073x | Exact match |

The full 186880-sample reference also matches **every byte of all three
archived attempts**, including the final silence guard:

| Width / horizon | New search seconds | Previous complete CLI seconds |
| --- | ---: | ---: |
| 256 /128 | 102.094716 | 259.859 |
| 512 /128 | 170.451387 | 526.813 |
| 1024 /256 | 652.329028 | 2723.703 |

The last column includes the old CLI's model preparation and waveform scoring;
the new column times search alone. Do not treat this table as an exact
end-to-end speedup. The three new searches total 924.875131 s (15 min 25 s).
The longest search is now 10 min 52 s. Full converter disk construction and
Fuse verification still add their own time and were not skipped or timed
again: their input streams, player sources and published disks are unchanged.
Existing IMA3 minimum SNR remains 19.031203 dB for the selected music preview.

All five search test methods pass (including ties/collisions and full-path
subcases), as do all nine existing converter tests. The CLI exposes its
documented backend choices. [Benchmark report](report.json), [full run log](full-run.log),
[native build identity](native-build.json), [initial line profile](initial-line-profile.json)
and [unchanged player identities](unchanged-player.json) are retained.
The bounded comparison is complete; adopt auto/native and retain the exact
NumPy fallback. No smaller beam or reduced-quality fast mode is introduced.

Verify the 28 archived artifacts, three matching streams, producer snapshots,
embedded C source and two unchanged release disks with:

```powershell
python audiobook-beeper/experiments/waveform-speed/archive.py
```

To archive a completed fresh reproduction, use `archive.py --archive
build/waveform-speed --write-manifest`; it refuses differing existing results.
