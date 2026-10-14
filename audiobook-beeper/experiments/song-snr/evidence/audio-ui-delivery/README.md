# Automatic generation of the initial UI control

The public C program produced the entire song image `55216119...` in
60.620961 seconds. `generated/generation.json` authenticates the command,
timings and unchanged source, cover, compressed audio and decoder tables.
Only the PLAYER file differs from the previously delivered `ccab8724...`.
The host score remains20.250315887 dB. `builder-tests.log` records four
successful option-validation/default-compatibility tests.

This is an immutable initial control, not the updated delivered disk. Full
installed-Fuse audio passes on both Pentagon profiles, but the frame-clock
loading-dot animation fails: actual ROM FRAMES barely advances during disk
reads. The named delivered TRD therefore remainsccab until a sector-count
loading fix passes. See the [actual phase control](../audio-ui-emulator/README.md).

The converter archived the exact9cc verification source used at generation.
Subsequentf6 changes only improve the optional capture harness; it was not
executed inside this conversion. The separate player proof preserves both
versions and verifies the native/cold functions remain identical. Original
Python/C encoder bytes are preserved.

To repeat the initial generation, use its committed source revision and a
fresh destination:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery/generate.py `
  --output .tmp/reproduce-initial-ui
```

The generator refuses to overwrite existing evidence and verifies that only
the16-KiB PLAYER file changes. Later UI builds must be saved separately.
Program generation is not a substitute for full actual emulator verification.
