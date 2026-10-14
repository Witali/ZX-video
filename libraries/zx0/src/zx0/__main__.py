"""Command-line assembly export and verified upstream compression."""
import argparse
from pathlib import Path
from . import compress, decompress
from ._z80 import MiniAssembler
from .codec import emit_decoder
from .resumable import build
from .export import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    assembly = commands.add_parser('build', help='Export an improved Z80 decoder include')
    assembly.add_argument('--variant', choices=('fast','turbo_tuned','standard','turbo','mega','fast-block'), default='fast')
    assembly.add_argument('--output', type=Path, required=True)
    assembly.add_argument('--namespace', default='zx0')
    for name, default in (('core',0x8df2),('core-limit',0x8f09),('prefix',0x7c00),
                          ('prefix-limit',0x7d50),('stack',0x7be0),('output-base',0xc000)):
        assembly.add_argument('--'+name, type=lambda value:int(value,0), default=default)
    encoder = commands.add_parser('compress')
    encoder.add_argument('input', type=Path)
    encoder.add_argument('output', type=Path)
    encoder.add_argument('--executable', default='zx0')
    encoder.add_argument('--minimum-match', type=int, default=0)
    decoder = commands.add_parser('decompress')
    decoder.add_argument('input', type=Path)
    decoder.add_argument('output', type=Path)
    decoder.add_argument('--limit', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        if args.variant=='fast-block':
            from .block import build as block_build
            regions,labels,metadata=block_build(core=args.core,core_limit=args.core_limit)
        elif args.variant in ('standard','turbo','mega'):
            a = MiniAssembler(args.core)
            entry=emit_decoder(a, args.variant)
            if a.pc > args.core_limit:
                parser.error('decoder exceeds core-limit')
            regions, labels, metadata = [(a.origin,a.resolve())], a.labels, dict(variant=args.variant)
            if args.variant=='mega':
                metadata.update(entry=entry,code_bytes=673,one_shot=True,
                    source_commit='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
                    patched_addresses=[a.labels['dzx0m_last_offset+1']+i for i in (0,1)])
        else:
            regions, labels, metadata = build(args.variant,core=args.core,core_limit=args.core_limit,
                prefix=args.prefix,prefix_limit=args.prefix_limit,stack=args.stack,output_base=args.output_base)
        export(args.output,regions,labels,metadata,namespace=args.namespace)
        print(args.output / 'decoder.asm')
    else:
        data = args.input.read_bytes()
        result = (compress(data,executable=args.executable,minimum_match=args.minimum_match)
                  if args.command == 'compress' else decompress(data,limit=args.limit))
        args.output.write_bytes(result)


if __name__ == '__main__':
    main()
