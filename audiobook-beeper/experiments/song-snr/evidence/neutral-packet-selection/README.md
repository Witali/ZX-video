# Instruction-derived stable neutral packet

2026-10-14. The selector examines every65536 pulse word without opening audio.
Its ordinary Pentagon period is449 T at3584000 Hz. Only848 patterns with224
or225 high T are allowed, keeping mean duty within0.5 T of50% and excluding
constant0/1 exploits. Physical holds are converted to the established
3546900-Hz reference units before using the unchanged analytic filter.

The periodic state is solved as `(I-A)^-1 Bword`. Duration-weighted variance
of the16 filtered midpoint values ranks the permitted words. Complementary
words share an exact symmetric score; ascending word ID breaks that tie.
The fixed choice is0x56AD,225 high T and successor16. Its estimated steady
RMS is0.0019133345. This is an ordinary-packet analytic estimate; complete
rendering, page/bank holds and source-quality effects are separate checks.

`neutral_packet_model.py` copies and replaces only input bin32 across32
feedback states. Absent options return the original arrays. Strict validation
requires the centered64-bin zero-origin full-extent integral model and exact
449-T holds. Six tests pass, including independent sequential periodic filter
propagation, complete selection/complement symmetry, immutable input arrays,
default identity, malformed tables and forbidden DC/wrong-model cases.

All64-bin closure remains18 states. FIRST138/SECOND97 patterns need12004
unrolled bytes and15424 resident bytes; compact worker estimate endsBFBC at
maximum one-TRD capacity,67 bytes belowBFFF. These are layout estimates until
the independent builder/native proof executes the option. No live algorithm,
C encoder or original Python source is modified in this selector stage.

```powershell
python -m unittest discover -s audiobook-beeper -p test_neutral_packet_model.py -v
python audiobook-beeper/experiments/song-snr/evidence/neutral-packet-selection/select.py `
  --output NEW_EMPTY_FOLDER
```

The report records conditioning, residuals, all assumptions, top20, producer
hashes and unchanged original Python. `enumeration.json.gz` preserves every
word, including disallowed DC cases, and the entire848-word ranking. The
subsequent complete source control rejects this all-state override for real
quality regressions despite its lower silence noise. Preserve that result
separately; the analytic selector does not qualify an audio release.
