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
    assembly.add_argument('--profile',choices=('coroutine','fast-block','small-block','wide-block','wide-shared-block'),default='coroutine',
                          help='wide profiles need explicit larger --core/--core-limit reservations')
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
    assembly.add_argument('--fast-jumps', action='store_true',
                          help='use 10-T JP for core unconditional JR; one extra byte per site')
    assembly.add_argument('--branch-tuned', action='store_true',
                          help='select conditional JR/JP forms measured on the frozen real corpus')
    assembly.add_argument('--nibble-prefill', action='store_true',
                          help='pre-normalize low-nibble cache; +3 T refill, -7 T cached, +4 bytes')
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
        if args.profile!='coroutine':
            if args.streaming or args.direct_header or args.word_state_init or args.restore_compare:
                parser.error('resident-block profile has no streaming/state wrapper')
            from .block import build as block_build
            if args.profile=='small-block' and (args.long_copy or args.near_literals or args.fast_jumps or args.branch_tuned or args.nibble_prefill):
                parser.error('compact profile does not support fast copy/jump options')
            variant=args.profile.removesuffix('-block')
            if variant in ('wide','wide-shared') and (args.long_copy or args.near_literals or args.fast_jumps or args.branch_tuned or args.nibble_prefill):
                parser.error('wide profiles use their own copy/branch layout')
            regions,labels,metadata=block_build(variant,core=args.core,core_limit=args.core_limit,
                long_copy=args.long_copy,near_literals=args.near_literals,fast_jumps=args.fast_jumps,branch_tuned=args.branch_tuned,nibble_prefill=args.nibble_prefill)
        else:
            regions, labels, metadata = build(core=args.core,core_limit=args.core_limit,
                prefix=args.prefix,prefix_limit=args.prefix_limit,stack=args.stack,
                output_base=args.output_base,streaming=args.streaming,direct_header=args.direct_header,
                long_copy=args.long_copy,near_literals=args.near_literals,word_state_init=args.word_state_init,
                restore_compare=args.restore_compare,fast_jumps=args.fast_jumps,branch_tuned=args.branch_tuned,nibble_prefill=args.nibble_prefill)
        export(args.output,regions,labels,metadata,namespace=args.namespace)
        print(args.output / 'decoder.asm')
    else:
        data = args.input.read_bytes()
        result = (compress(data,executable=args.executable) if args.command == 'compress'
                  else decompress(data,limit=args.limit))
        args.output.write_bytes(result)


if __name__ == '__main__':
    main()
