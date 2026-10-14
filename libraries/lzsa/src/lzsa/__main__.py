"""Command-line export of the improved raw LZSA2 coroutine."""
import argparse
from pathlib import Path
from . import compress, decompress
from .resumable import build
from .export import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    assembly = commands.add_parser('build')
    assembly.add_argument('--output', type=Path, required=True)
    assembly.add_argument('--namespace', default='lzsa2')
    assembly.add_argument('--streaming', action='store_true')
    assembly.add_argument('--direct-header', action='store_true')
    assembly.add_argument('--long-copy', action='store_true',
                          help='append 16-LDI long-copy kernels; increase --core-limit explicitly')
    assembly.add_argument('--near-literals', action='store_true',
                          help='place the ordinary long-copy literal helper near its JR caller')
    assembly.add_argument('--word-state-init', action='store_true',help='clear adjacent streaming flags with a word store')
    assembly.add_argument('--restore-compare', action='store_true',help='restore the compared target arithmetically')
    for name, default in (('core',0x8de0),('core-limit',0x8ef7),('prefix',0x7c00),
                          ('prefix-limit',0x7d50),('stack',0x7be0),('output-base',0xc000)):
        assembly.add_argument('--'+name, type=lambda value:int(value,0), default=default)
    encoder = commands.add_parser('compress')
    encoder.add_argument('input', type=Path)
    encoder.add_argument('output', type=Path)
    encoder.add_argument('--executable', default='lzsa')
    decoder = commands.add_parser('decompress')
    decoder.add_argument('input', type=Path)
    decoder.add_argument('output', type=Path)
    decoder.add_argument('--limit', type=int, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        regions, labels, metadata = build(core=args.core,core_limit=args.core_limit,
            prefix=args.prefix,prefix_limit=args.prefix_limit,stack=args.stack,
            output_base=args.output_base,streaming=args.streaming,direct_header=args.direct_header,
            long_copy=args.long_copy,near_literals=args.near_literals,word_state_init=args.word_state_init,
            restore_compare=args.restore_compare)
        export(args.output,regions,labels,metadata,namespace=args.namespace)
        print(args.output / 'decoder.asm')
    else:
        data = args.input.read_bytes()
        result = (compress(data,executable=args.executable) if args.command == 'compress'
                  else decompress(data,limit=args.limit))
        args.output.write_bytes(result)


if __name__ == '__main__':
    main()
