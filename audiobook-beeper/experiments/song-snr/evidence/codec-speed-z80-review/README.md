# Live Z80 decoder review

This review separates faster host decoding from the unchanged Spectrum
player. It hashes the actual player/generator sources and counts the IMA
transition core from the [Zilog instruction tables](https://www.zilog.com/docs/z80/um0080.pdf).
The six instructions take **49 T**, or **57 T** with their two surrounding
register exchanges. Thirty-two bounded native fragment cases confirm both
counts and the resulting predictor, row pointer and stack pointer.

No live instruction changes: **0 T delta**. The Pentagon player retains its
449-T ordinary sample, 14-T page extension and 243-T bank extension. The
49/57-T figures exclude audio output, source-nibble extraction, PDM dispatch,
bank handling and clone contention; they are not a whole-sample budget.

Aligning all 89 decoder rows to 256-byte pages could remove the 4-T `OR L`,
but changes transition allocation from 5,696 to 22,784 bytes: **17,088 extra
fixed bytes**. That counted alternative exceeds current fixed RAM and has
no integrated timing or paging proof. Moving the predictor from IX to HL
also conflicts with the existing row/dispatch register allocation; a faster
isolated ADD cannot establish a complete player saving.

The existing uniform 16×28-T component reads resident PCM8. Its static
two-bank version already uses 31,986 fixed bytes before a general loader/UI;
it omits live IMA decoding. Its 448-T result does not show that the compressed
player can use the same schedule. No new TRD, full-player execution, physical
hardware result or decoder improvement on the Spectrum is claimed here.

Reproduce the bounded review with `review.py` using the project's existing
Python/z80 runtime. The current host acceleration remains byte-exact and is
measured separately under `table-pdm-decode-speed-final`.

The initial instruction-extraction harness failure and its producer are
retained. Extraction was corrected before the 32 native cases ran.
