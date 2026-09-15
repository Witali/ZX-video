"""Compare both upstream ZX0 decoders on the exact blocks in a v8 build.

DEFLATE sizes are offline comparisons only; no Z80 DEFLATE timing is claimed.
Instruction timing scope is decoder entry through RET, excluding caller setup,
contention, interrupts, disk and paging. Inputs are build compression-cache files.
"""
import argparse
import hashlib
import json
from pathlib import Path

from build_zxv_trd import MiniAssembler
from validate_fast_sparse import CPU
from zx0_codec import emit_decoder


def benchmark(build: Path) -> dict:
    metadata = json.loads((build/'build_metadata.json').read_text())
    blocks = [block for volume in metadata['volumes'] for block in volume['blocks']]
    report = dict(scope=__doc__, blocks=len(blocks),
                  zx0_block_bytes=sum(b['compressed_bytes']+4 for b in blocks),
                  deflate_block_bytes=sum(min(b['deflate_bytes'],b['decoded_bytes'])+4 for b in blocks),
                  decoders={})
    for variant in ('standard', 'turbo'):
        assembler = MiniAssembler(0x6000)
        emit_decoder(assembler, variant)
        player = assembler.resolve()
        counts = []
        for block in blocks:
            if block['stored']:
                continue  # The player uses LDIR, not ZX0, for stored blocks.
            stem = build/'compression_cache'/block['sha256']
            payload = stem.with_suffix('.zx0').read_bytes()
            expected = stem.with_suffix('.raw').read_bytes()
            assert hashlib.sha256(expected).hexdigest() == block['sha256']
            assert len(payload) == block['compressed_bytes']
            cpu = CPU(player, b'')
            cpu.set_hl(0xA000); cpu.set_de(0x8000); cpu.push(0x5F00)
            for offset, value in enumerate(payload):
                cpu.write8(0xA000+offset, value)
            while cpu.pc != 0x5F00:
                if cpu.steps >= 1_000_000:
                    raise RuntimeError('decoder instruction limit exceeded')
                cpu.step()
            assert cpu.de() == 0x8000+len(expected)
            assert bytes(cpu.banks[2][:len(expected)]) == expected
            counts.append(cpu.tstates)
        report['decoders'][variant] = dict(bytes=len(player), tstates=counts,
            mean=sum(counts)/len(counts) if counts else 0, maximum=max(counts,default=0))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    report = benchmark(args.build)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({**report, 'decoders': {name: {key: value for key, value in data.items()
        if key != 'tstates'} for name, data in report['decoders'].items()}},indent=2))


if __name__ == '__main__': main()
