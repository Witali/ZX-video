# Uniform table-output evidence audit

Completed2026-10-20 without re-encoding or rendering audio. The report
authenticates every file in the native residentPCM8 component, isolated static
bank bridge, retained failed bank attempt, both complete host render sets and
the first failed audit attempt. It verifies the entire canonical9-source corpus
and all1195520 decoded samples against the frozen C words/states and table.

The first host render incorrectly treated native Pentagon ticks as3546900-Hz
Spectrum-reference ticks. Its source rate was7917.1875Hz despite an8k label.
That attempt remains indexed; its scores are invalid for the canonical8k gate.
The corrected render converts clocks using referenceTicksPerSample=CPU/8000
and referenceTicksPerPulse=CPU/128000. C, model, compressed inputs, decoded
predictors, words and successor states remain unchanged.

The first audit rejected a bank README added after the bank manifest. That
bookkeeping failure is preserved separately. The final audit requires complete
artifact coverage as well as hashes, so a new unindexed document cannot pass.

Native table records are independently composed into packet words and compared
against the host model for all384 reachable level/state cells. All1536 native
PCM8/state cases and262128 trajectory outputs are checked from retained bytes;
native times have exactly28T differences. The bank bridge is an isolated static
I/O mechanism with its own preconditions. None of these records proves an
integrated compressed player, full banked playback, boot or quality acceptance.
