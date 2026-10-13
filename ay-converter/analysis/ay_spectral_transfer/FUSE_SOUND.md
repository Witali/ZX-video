# Fuse sound model and runtime readback probe

Verified2026-10-13 against installed Windows Fuse1.9.0 and the official
`fuse-1.9.0` release tag, commit
`b72c83e85786f5f84375d42c104952cc5453bbaa`. The installed executable reports
version1.9.0. [Machine-readable source/executable hashes](evidence/fuse-source.json).
This establishes matching release source/version, not identical binary build
provenance or physical-chip identity.

In `sound.c`, `AY_ENV_STEPS=16`; amplitude and envelope use the same16-entry
table. `sound_ay_init()` attributes it to Matthew Westcott's2001 measurements.
The chip clock is half the emulated CPU clock and envelope steps occur every
16 chip clocks times the envelope period. Register changes are timestamped,
not atomic. There is no separately selectable YM2149 model in this release.
`peripherals/sound/ay.c` explicitly describes AY-3-8912 behavior and masks R1
with0Fh on both reads and writes; writing1Fh therefore reads0Fh in Fuse.

The Fuse volume table is different from both vendored Ayumi curves. Mean
absolute level error over nonzero codes, normalized at maximum output, is
1.928268 dB for Ayumi AY versus3.328873 dB for Ayumi YM. This simple static
comparison does not prove waveform/perceptual fidelity: Fuse and Ayumi also
have different counters and filters. Default to the explicit AY target for
this Spectrum/Fuse experiment, and retain YM as a separately labeled trial.
Do not switch to YM merely because its name starts with Yamaha.

## Software detection on a Spectrum

Real-device tests demonstrate a useful readback behavior: select R1, write
1Fh, read0Fh on AY-3-8910/12 or1Fh on tested YM2149 parts. WritingFFh is not
equivalent: the tested genuine Yamaha parts also mask that value. Sources:
[the original hardware investigation](https://blog.tynemouthsoftware.co.uk/2023/01/testing-ay-3-8910-ym2149-sound-card-for-rc2014-and-minstrel-4D.html),
[official Fuse source](https://sourceforge.net/p/fuse-emulator/fuse/ci/b72c83e85786f5f84375d42c104952cc5453bbaa/tree/peripherals/sound/ay.c).
This is a behavior probe, not a guaranteed manufacturer/revision identifier
for every clone, FPGA or emulator. It cannot distinguish8910 from8912 by
this test alone. Explicit target selection remains necessary for ambiguous
hardware; switching between independently precomputed streams would require
both streams, not just detecting the chip at playback startup.

[psg_probe.asm](../../psg_probe.asm) is an optional standalone Z80 routine,
not installed in the current player. Call with interrupts disabled and audio
muted. It tests used-bit readback with00h/0Fh before1Fh, then restores the old
readable R1 value on every outcome. Return A=0 unknown/absent,1 AY-style,
2 YM-style. Clobbers F/BC/DE/HL and leaves the latch selecting R1.

An independent Z80 executes the actual assembled routine on30 bus fixtures:
AY, YM (includingFFh masking), absent, stuck and unknown buses, six initial
values each. All return codes, register restoration and stack checks pass.
Independent instruction-table sums including RET but excluding caller CALL:
265 T AY,279 T YM,226 T for the fixtures failing the first bus check. A CALL
adds17 T. Existing player hot-path instructions are unchanged: delta0 T.
No physical-device execution or new native release claim is made.

Reproduction from this worktree:

```powershell
git clone --depth 1 --branch fuse-1.9.0 https://git.code.sf.net/p/fuse-emulator/fuse .tmp/fuse-1.9.0-source
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies).Path
python ay-converter/analysis/ay_spectral_transfer/fuse_source.py --source .tmp/fuse-1.9.0-source --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --output .tmp/fuse-source-check.json
python -m unittest discover -s ay-converter -p test_psg_probe.py -v
```

Local test dependencies are pinned pyz801.3.0 and z801.2.0; NumPy uses the
bundled Python runtime. The initial HTTP archive download returned HTML and
was rejected as invalid; the official Git release clone supplies the source.
