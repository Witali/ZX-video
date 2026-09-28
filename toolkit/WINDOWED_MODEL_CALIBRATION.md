# Calibrating the sliding-window cost model

Measured on 2026-09-28 using existing archived runs. **No new TRDs or Fuse
playbacks** are used by this experiment. It changes host-side estimates,
with **0 T runtime instruction delta** and no stream, pixel or AY change.
The original planner and its measured output remain reproducible.

## Corrected omissions

1. The real `read_packet` routine expands metadata before returning. The
   initial model charged that work at the later reconstruction stage.
   [`calibrated_windowed_model.py`](calibrated_windowed_model.py) moves it
   into the packet-read phase, counting it once. This corrects ownership of
   the available time, but by itself does **not** improve prediction error.
2. A 16-T LDI is not the elapsed cost of packet transport. Queue/paging
   work, loop control, ULA and IRQ also consume time. A least-squares fit
   from **2710 baseline transfers without empty-queue waits or disk service**
   gives **20.885080 T/byte + 3129.767723 T**. Mean absolute residual is
   **1848.42 T**. This is an elapsed-time fit, not a Z80 instruction count.
3. The old model omitted work before preparation and drawing. Baseline
   stage boundaries give means of **3901 T before prepare** (4215 samples)
   and **5618 T before draw** (1483 samples). Draw-entry samples are restricted
   to cases where foreground work already extends beyond the previous
   publication; background production or HALT cannot occupy that gap.

These entry costs mix control code, AY refill, periodic disk service and
IRQ. The trace does not distinguish them, so they are not labelled pure
CPU costs. Coefficients are fitted from the Fast baseline only. They are
then held fixed when comparing the four other archived token selections;
their publication times are not used to fit parameters.

## Prediction coverage

All 4221 frames of each existing set are compared. Error is recorded for
every consecutive window of at most 64 frames, with schedule and reservoir
state carried continuously. An absolute publication error is the difference
between the predicted and observed OUT time, relative to each disk's first
publication. The report also counts falsely predicted on-time frames and
false alarms. No window is restarted with an artificially full reservoir.

| Existing set | Actual late frames | Original prediction | Corrected prediction |
| --- | ---: | ---: | ---: |
| Fast baseline | 1239 | 653 | 903 |
| Unweighted token selection | 1149 | 641 | 835 |
| Pressure weight 4 | 1111 | 622 | 815 |
| Pressure weight 16 | 1105 | 622 | 819 |
| Window-selected set | 1186 | 595 | 825 |

The sum of absolute publication errors across the four held-out selections
falls **17273310436→11184085840 T**, approximately **35.25%**. Baseline error
falls **5551824937→3515488951 T**. These sums combine per-frame errors; they
are neither CPU savings nor reductions of movie duration.

The report retains all four incremental controls: original model,
metadata moved to read, measured transport, and measured entry costs.
Moving metadata alone slightly worsens aggregate error; it is retained
because it represents the real instruction order, not because it happens
to fit one trace. Adding measured transport and entry costs reduces error
on every held-out set, but **the model still substantially underestimates
lateness**.

## Decision and next work

Keep this as a separate calibrated model, not as a timing-qualified
automatic policy. The existing selected set and generic frontend defaults
are unchanged. Do not spend another complete playback on a newly selected
set based solely on these still-optimistic estimates.

The remaining model has no explicit charge for queue-step control and AY
service around background production. Its fixed 256-byte decoder slices
also differ from foreground demand sizes. Next, use bounded native queue
replay or local tracing to measure those costs, including bank changes,
input-sector operations and actual entering slot state. Preserve absolute
deadlines and separate native CPU from ROM/physical disk/IRQ/ULA time.
The larger prepared-command queue and generic-media integration remain
separate unfinished work.

## Reproduction and checks

```powershell
python -m unittest discover -s toolkit -p test_calibrated_windowed_model.py
python toolkit/calibrate_windowed_model.py
```

The second command reconstructs the calibration and compares it with the
saved report. `--write` regenerates the report deliberately. Archived
metadata and run JSON are checked against their manifests before use;
input/report/source hashes are recorded. Four regression tests check
compatibility with the original control, early metadata charging, absence
of double counting, carried window state and recovery to the original
deadline sequence.

[Calibration script](calibrate_windowed_model.py) ·
[Full measurements and per-window errors](windowed_model_calibration.json) ·
[Initial windowed experiment](WINDOWED_OPTIMIZATION.md)
