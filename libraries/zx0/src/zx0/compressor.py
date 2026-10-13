"""Verified adapter to the upstream ZX0 v2 compressor executable."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from .codec import decompress
from .tokens import rewrite


def compress(raw, *, executable='zx0', minimum_match=0):
    """Compress with upstream, optionally replacing short matches by literals.

    This lossless host pass can trade bytes for fewer decoder operations;
    measure complete native CPU and delivery costs before selecting a stream.
    The executable must produce forward ZX0 v2 (no classic/backward flags).
    """
    raw = bytes(raw)
    if not 1 <= len(raw) <= 65535:
        raise ValueError('ZX0 block must contain 1..65535 bytes')
    if not isinstance(minimum_match, int) or minimum_match < 0:
        raise ValueError('minimum_match must be a nonnegative integer')
    program = shutil.which(str(executable))
    if program is None:
        raise FileNotFoundError(f'ZX0 executable not found: {executable}')
    with tempfile.TemporaryDirectory(prefix='zx0-') as directory:
        source, output = Path(directory) / 'input.raw', Path(directory) / 'output.zx0'
        source.write_bytes(raw)
        subprocess.run([program, '-f', str(source), str(output)], check=True, capture_output=True)
        payload = output.read_bytes()
    if decompress(payload, limit=len(raw)) != raw:
        raise ValueError('upstream ZX0 output failed the independent round trip')
    return rewrite(payload, minimum_match)
