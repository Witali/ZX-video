"""Optional non-wrapping ZX0-v2 coroutine prototypes; compressed bytes unchanged.

The Fast emitter adapts spke/uniabis' upstream dzx0_fast.asm. Its original
notice remains in asm/dzx0_fast.asm. This is an altered version:
add token-boundary suspension, remove the persistent IX continuation, and
merge literal copies. No upstream file or retained player default is changed.
Output must not wrap at FFFF. Defaults retain the current C000..FDFF slot.
"""
from pathlib import Path

from ._z80 import MiniAssembler
from ._z80 import sha
from . import codec as zx0_codec

PREFIX, PREFIX_LIMIT = 0x7c00, 0x7d50
CORE, CORE_LIMIT = 0x8df2, 0x8f09
STACK = 0x7be0
UPSTREAM = Path(__file__).parent/'asm/dzx0_fast.asm'


def build(variant='fast',*,core=CORE,core_limit=CORE_LIMIT,
          prefix=PREFIX,prefix_limit=PREFIX_LIMIT,stack=STACK,output_base=0xc000,branch_tuned=False,_assembler=None):
    """Return (address/bytes regions, labels, metadata) for a private coroutine.

    Set input_pointer, block_end and slice_target before begin. Resume through
    slice_until with monotonic targets; a token may overshoot the target.
    Code/state must be writable. AF/BC/DE/HL and AF' are clobbered; the caller's
    SP is restored on return. Interrupt handlers must preserve live registers
    and fit below the private stack. Output history and source stay available.
    branch_tuned optionally selects measured JR/JP forms in Fast. Branch
    conditions stay exact; metadata reports fallbacks and synthetic slowdowns.
    """
    if branch_tuned:
        if variant!='fast':raise ValueError('branch tuning requires the Fast decoder')
        from ._branch_tuning import tune
        return tune(build,dict(variant=variant,core=core,core_limit=core_limit,
            prefix=prefix,prefix_limit=prefix_limit,stack=stack,output_base=output_base),'zx0')
    if variant not in ('fast','turbo_tuned'): raise ValueError('unknown decoder')
    if not (0<=core<core_limit<=65536 and 0<=prefix<prefix_limit<=65536):
        raise ValueError('invalid code reservations')
    if not (core_limit<=prefix or prefix_limit<=core):raise ValueError('code reservations overlap')
    if not 0<stack<=65535 or not 0<=output_base<65535:raise ValueError('invalid stack/output address')
    assembler=_assembler or MiniAssembler
    cold, hot = assembler(prefix), assembler(core)
    sites = ('match','match3','slice') if variant == 'fast' else ('match','slice')
    patches = []

    cold.label('slice_until')
    cold.abs16(0xcd,'slice_sync_target')
    cold.abs16(0x2a,'slice_output'); cold.abs16((0xed,0x5b),'slice_target')
    cold.emit(0xb7,0xed,0x52,0xd0)
    cold.label('slice_resume')
    cold.abs16((0xed,0x73),'slice_caller_sp'); cold.abs16((0xed,0x7b),'slice_decoder_sp')
    cold.emit(0xe1,0xd1,0xc1,0xf1,0xc9)
    cold.label('slice_begin')
    cold.abs16(0xcd,'slice_sync_target'); cold.abs16((0xed,0x73),'slice_caller_sp')
    # Save the caller stack; the decoder keeps its continuation and live
    # registers on a separate stack so callers can reuse registers at yields.
    cold.emit(0x31); cold.word(stack)
    cold.abs16(0x21,'slice_finished'); cold.emit(0xe5)
    cold.abs16(0x2a,'input_pointer'); cold.emit(0x11); cold.word(output_base)
    cold.abs16(0xc3,'DecompressZX0' if variant=='fast' else 'dzx0_turbo')
    cold.label('slice_finished')
    cold.abs16(0x2a,'block_end'); cold.emit(0xb7,0xed,0x52); cold.abs16(0xc2,'fatal')
    cold.abs16((0xed,0x53),'slice_output'); cold.abs16((0xed,0x7b),'slice_caller_sp'); cold.emit(0xc9)
    cold.label('slice_yield')
    cold.abs16((0xed,0x53),'slice_output'); cold.emit(0xf5,0xc5,0xd5,0xe5)
    cold.abs16((0xed,0x73),'slice_decoder_sp'); cold.abs16((0xed,0x7b),'slice_caller_sp'); cold.emit(0xc9)
    cold.label('slice_sync_target'); cold.abs16(0x2a,'slice_target'); cold.emit(0x7c)
    for site in sites: cold.abs16(0x32,site+'_high_operand')
    cold.emit(0x7d)
    for site in sites: cold.abs16(0x32,site+'_low_operand')
    cold.emit(0xc9)
    cold.label('fatal'); cold.emit(0x76)
    cold.label('state')
    for name in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp',
                 'block_length','block_end','input_pointer'):
        cold.label(name); cold.word(0)
    cold.label('block_stored'); cold.emit(0)
    cold.label('end'); cold.labels['begin'] = cold.labels['slice_begin']

    def boundary(a, site):
        a.label(site+'_check'); a.emit(0x08,0x7a)
        a.label(site+'_compare_high'); a.emit(0xfe,0)
        a.abs16(0xda,site+'_fast')  # Frequent taken JP is 10 T vs JR's 12.
        a.rel8(0x20,site+'_slow')
        a.emit(0x7b); a.label(site+'_compare_low'); a.emit(0xfe,0)
        a.abs16(0xda,site+'_fast')
        a.label(site+'_slow'); a.emit(0x08)
        a.abs16(0xcd,'slice_yield'); a.abs16(0xc3,site+'_check')
        a.label(site+'_fast'); a.emit(0x08)
        for part in ('high','low'):
            name=site+'_'+part+'_operand'; a.labels[name]=a.labels[site+'_compare_'+part]+1
            patches.append(name)

    if variant=='turbo_tuned':
        def copy(a, site): boundary(a,site); a.emit(0xed,0xb0)
        zx0_codec.emit_decoder(hot,'turbo',copy_hook='slice_check',
            inline_match=lambda a:copy(a,'match'), inline_literal=lambda a:copy(a,'slice'))
        offset = 'dzx0t_last_offset'
    else:
        emit_fast(hot,boundary)
        offset = 'PrevOffset'
    labels = cold.labels | hot.labels
    labels['last_offset_operand'] = labels[offset]+1
    # Existing producer uses only the block/stream/coroutine state labels.
    regions=[(prefix,cold.resolve(labels)),(core,hot.resolve(labels))]
    if cold.pc>prefix_limit or hot.pc>core_limit:
        raise ValueError(('decoder does not fit retired regions',hex(cold.pc),hex(hot.pc)))
    patched=[labels[n] for n in patches]+[labels[offset]+1,labels[offset]+2]
    report=dict(variant=variant,prefix_end=cold.pc,core_end=hot.pc,
        code_and_state_bytes=sum(len(data) for _,data in regions),
        prefix_bytes=cold.pc-prefix,core_bytes=hot.pc-core,
        extra_stream_bytes=0,extra_buffer_bytes=0,private_stack_unchanged=True,
        only_nonwrapping_inplace_blocks=True,max_decoded_bytes=min(15872,65535-output_base),
        output_base=output_base,private_stack=stack,
        source_commit='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
        upstream_sha256=sha(UPSTREAM.read_bytes()),patched_addresses=patched,
        regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in regions])
    return regions,labels,report


def emit_fast(a,boundary):
    """Assemble the pinned upstream code with explicitly marked adaptations."""
    simple={'inc bc':(0x03,), 'inc c':(0x0c,), 'inc hl':(0x23,),
        'push hl':(0xe5,), 'pop hl':(0xe1,), 'add hl,de':(0x19,),
        'ldir':(0xed,0xb0), 'ldi':(0xed,0xa0), 'add a,a':(0x87,),
        'ld c,(hl)':(0x4e,), 'ld a,(hl)':(0x7e,), 'ld b,c':(0x41,),
        'rr c':(0xcb,0x19), 'rl c':(0xcb,0x11), 'rl b':(0xcb,0x10),
        'rla':(0x17,), 'ret z':(0xc8,), 'ret c':(0xd8,)}
    last_label = None
    for original in UPSTREAM.read_text().splitlines():
        line=' '.join(original.split(';')[0].strip().lower().split()).replace(', ',',')
        if not line:continue
        # Preserve upstream label spelling for readable metadata.
        names={name.lower():name for name in ('DecompressZX0','CopyMatch1','CopyMatch2','CopyMatch3',
            'PrevOffset','AfterMatch1','AfterMatch3','ShorterOffsets','LongerOffets','ProcessOffset',
            'UsualMatch','LongerMatch','RunOfLiterals','LongerRun','CopyLiteral','CopyLiterals',
            'RepMatch','LongerRepMatch','ReloadReadGamma','ReadGammaAligned','ReadingLongGamma')}
        if line.endswith(':'):
            last_label=names[line[:-1]]; a.label(last_label)
            if last_label in ('CopyMatch1','CopyMatch3','CopyLiteral'):
                boundary(a,dict(CopyMatch1='match',CopyMatch3='match3',CopyLiteral='slice')[last_label])
            continue
        if line.startswith('ld ix,'):continue  # Caller can own IX between resumptions.
        if line=='push ix':
            a.abs16(0xcd,'ReloadReadGamma'); a.abs16(0xc3,'CopyMatch1');continue
        if line=='ldi' and last_label=='CopyLiterals':continue # One shared literal-boundary check.
        if line in simple:a.emit(*simple[line]);continue
        op,args=line.split(' ',1)
        if op in ('jr','jp','call'):
            condition,target=args.split(',',1) if ',' in args else ('',args)
            if target=='$-4':
                label='gamma_loop_'+str(a.pc); a.labels[label]=a.pc-4
            else:label=names[target]
            # Added checks put some former JR targets outside relative range.
            # Absolute branches also avoid 12-T taken JR in this short-run path.
            opcode={'':0xc3,'nc':0xd2,'c':0xda,'nz':0xc2,'z':0xca}[condition]
            if op=='call':opcode={'':0xcd,'nc':0xd4,'z':0xcc}[condition]
            a.abs16(opcode,label);continue
        if op=='ld':
            dst,src=args.split(',')
            if dst=='(prevoffset+1)':
                a.abs16((0xed,0x43),'PrevOffset+1');continue
            if src=='(prevoffset+1)':a.abs16(0x2a,'PrevOffset+1');continue
            value=int(src[1:],16) if src.startswith('$') else int(src)
            a.emit({'bc':0x01,'hl':0x21,'b':0x06,'a':0x3e,'c':0x0e}[dst])
            if dst in ('bc','hl'):a.word(value)
            else:a.emit(value)
            continue
        raise ValueError(('unsupported fast instruction',line))
    a.labels['PrevOffset+1']=a.labels['PrevOffset']+1
