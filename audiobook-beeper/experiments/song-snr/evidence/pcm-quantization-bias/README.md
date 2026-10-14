# Optional centered predictor lookup in the player

2026-10-14. `pcm_quantization_bias=512` changes the256-byte PCM-high table to
`packet_pages[min(63,(IXH+2)//4)]`. It exactly implements
`min(63,(predictor+32768+512)//1024)` over every signedPCM16 input. The host
addition uses integers, so the last two high bytes saturate instead of wrapping.
The zero bucket spans[-512,511]. Other bias values or incompatible model
families fail before output creation.

Absent or integer0 bias keeps old disk and complete metadata unchanged. The
metadata oracle is the actual builder/layout/assembler at commit7938cbe6,
saved under `prior-producer`; an older song metadata file is unsuitable because
it predates the already accepted worker relocation. The old complete TRD is
also independently authenticated. The verifier derives centered bins from
full signedPCM16 and checks all256 selector bytes after cold loading.

Four tests pass. A4096-sample transient/tone control runs completely before
and after on all four native profiles, checking every bit, predictor/index,
guard, loading and interval. The option changes exactly126 LUT data bytes and
no instructions. Ordinary instruction counts stay423 T on128/Scorpion and
449 T onPentagon512/1024. Page extra14 T and bank extra243/267 T stay identical;
all deterministic deltas are0 T.

The short native proof separates CPU timing from actual ULA waits and TR-DOS
latency. The changed lookup can select different contended addresses on128
orScorpion. No new actual Fuse clock, audio-quality or hardware claim follows
from these tests. New source/profile quality must use its own complete trace.

```powershell
python audiobook-beeper/test_pcm_quantization_bias.py --evidence NEW_EMPTY_FOLDER -v
```

`report.json` authenticates producers and records the exhaustive mapping,
before/after native reports, malformed-input checks and old compatibility.
The two saved images remain research fixtures. This optional functionality
does not promote the matched centered corpus candidate or replace main.
