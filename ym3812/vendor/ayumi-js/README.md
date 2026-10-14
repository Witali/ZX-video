# Vendored Ayumi JavaScript core

Unmodified `ayumi.js` and `LICENSE` from
[alexanderk23/ayumi-js](https://github.com/alexanderk23/ayumi-js), revision
`3a1fb9120cc2c5ef8f538af59b46701e4c2305bb`, retrieved 2026-10-01.
JavaScript port by Alexander Kovalenko of Peter Sovietov's
[Ayumi](https://github.com/true-grue/ayumi). MIT license, retained alongside
the source. No package installation, browser UI or network use at runtime.

The local wrapper selects the YM2149 DAC table, preserves generator phase,
and writes ordinary tone/noise/mixer/volume registers. This models the chip,
not a particular Spectrum's analogue output circuit or CPU bus timing.
