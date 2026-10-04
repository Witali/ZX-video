"""Host-only three-bit quarter-step delta with faster step adaptation.

This is a custom codec experiment, not standard WAV IMA3.
The current Z80 table ABI can express the recurrence without extra cycles.
"""
from pathlib import Path

source=Path('.tmp/probe-standard-ima3.py').read_text()
source=source.replace("m.INDEX=(-1,-1,-1,-1,1,4,2,8)", "m.INDEX=(-1,-1,-1,-1,2,4,6,8)")
source=source.replace(".tmp/voice-standard3-probe", ".tmp/voice-quarter6-probe")
source=source.replace('Host-only WAV-IMA3 recurrence control', 'Host-only quarter-step, step6 adaptation control')
exec(compile(source, __file__, 'exec'))
