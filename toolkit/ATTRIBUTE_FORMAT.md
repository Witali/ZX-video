# Attribute storage and the FLASH contract

Updated 2026-09-28. Hardware bytes use INK bits 0..2, PAPER bits 3..5,
shared BRIGHT bit 6 and FLASH bit 7. Video keeps **all seven colour bits**
and requires **FLASH=0**. The FAP3 encoder rejects FLASH rather than silently
changing an input frame. Quantization already produces non-FLASH colours.

The compact state retains 768 byte-aligned attributes (576 in the active
picture). This is a RAM layout, not a fixed 768-byte cost for every frame
on disk. Ordinary packets predict each attribute from the same position
in frame n-1, transmit sparse change masks and Huffman-code nonzero XOR
corrections. The outer packet stream is then compressed with ZX0. Unchanged
attributes have no correction symbols; the mask still has some overhead.

For many changes, packet flag bit 6 selects 768 absolute attribute bytes
in the literal region. The generic encoder currently chooses this at 128
changes or for its bounded-packet escape. These bytes are still subject to
outer ZX0. Packet flag bit 6 is unrelated to hardware attribute BRIGHT.

Native output uses two lists of changed eight-cell groups to cover n-2,
because screens alternate. It skips constant border attributes and chooses
a full active-attribute copy when that is cheaper than sparse groups.

## Current edited-movie measurements

[Audit](attribute_format_audit.json): 4221 compact frames and the current
volume-1 Huffman-training FAP3 stream, including its entire source timeline.

- FLASH occurrences: **0**; BRIGHT occurrences: **2351219**.
- **32135** attribute changes after the initial frame.
- **99.0085%** of full-screen attribute positions stay unchanged between
  successive frames; **98.6780%** in the active picture alone.
- **1763** frames have no attribute changes; **41** use raw attributes.

These are exact source-state/packet-flag counts. The audit does not re-decode
the whole stream, isolate final attribute-compressed bytes or measure speed.
Prior full round-trip evidence remains separate. This change adds a host
validation check only: **0 Z80 T-states**, unchanged valid stream bytes.

## Further packing experiment

Packing seven-bit absolute attributes would reduce a 768-byte raw array to
672 bytes, or 576 active bytes to 504 bytes, before compression. That is an
upper-level layout comparison, not a predicted disk saving. Huffman already
uses variable code lengths and ZX0 can exploit the constant high bit.
Measure seven-bit packing only on raw-attribute packets in bounded windows,
including unpacking, native writes and sectors, before adopting it. Do not
remove BRIGHT or replace the existing delta path with unconditional arrays.

```powershell
python -m unittest toolkit.test_generic_converter
python toolkit/audit_attributes.py `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --raw .worktree/volume-huffman/.tmp/probe/volume-1.raw `
  --output toolkit/attribute_format_audit.json
```
