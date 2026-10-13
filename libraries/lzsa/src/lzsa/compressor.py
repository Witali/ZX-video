"""Verified adapter to upstream raw LZSA2; size/cycle search is explicit."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from .codec import decompress


def compress(raw, *, executable='lzsa'):
    """Run standard raw v2 ratio compression and verify the entire block.

    CPU-aware distance selection and short-match fitting are separate passes
    because applications supply their own byte, CPU and input-layout budgets.
    """
    raw = bytes(raw)
    if not 1 <= len(raw) <= 65535:
        raise ValueError('LZSA2 block must contain 1..65535 bytes')
    program = shutil.which(str(executable))
    if program is None:
        raise FileNotFoundError(f'LZSA executable not found: {executable}')
    with tempfile.TemporaryDirectory(prefix='lzsa2-') as directory:
        source, output = Path(directory) / 'input.raw', Path(directory) / 'output.lzsa'
        source.write_bytes(raw)
        subprocess.run([program, '-r', '-f', '2', '--prefer-ratio', str(source), str(output)],
                       check=True, capture_output=True)
        payload = output.read_bytes()
    if decompress(payload, limit=len(raw)) != raw:
        raise ValueError('upstream LZSA2 output failed the independent round trip')
    return payload
