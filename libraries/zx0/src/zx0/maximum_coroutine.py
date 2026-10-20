"""Phase-specific complete-input ZX0 maximum coroutine, same output quotas."""
from ._z80 import MiniAssembler,sha
from .maximum import build as raw_build


def build(*,core=0x8000,core_limit=None,prefix=0x7000,prefix_limit=0x7400,
          stack=0x6fe0,output_base=0xc000,prefix_cap=127,
          irq_code_bytes=0,irq_stack_bytes=0,service_limit=10000,_quota_mode='index'):
    """Generate an ordinary complete-input coroutine with token-sized yields.

    Configure input_pointer, block_end and slice_target, then CALL begin and
    slice_until with monotonic nonwrapping quotas. Every return publishes the
    same output cursor as ordinary Fast; source/count preparation may suspend
    earlier internally. Retain complete input/output/history. Code/state are
    writable and non-reentrant; caller SP and IX/IY/alternate BC/DE/HL survive.
    AF/AF'/BC/DE/HL can be clobbered between returns, including by the caller.
    IRQ preserves all live pairs, including AF' and IX holding the quota.

    This optional profile requires the Spectrum Z80's undocumented CP IXH and
    CP IXL forms (8 T each). Save caller IX per entry, install the normalized
    quota in IX, then restore it before every return. The private continuation
    contains the live AF reservoir/count/pointers; quota IX is rebuilt on each
    resume. Other Z80 clones need their own opcode qualification. Private
    diagnostic modes retain the measured, rejected earlier quota strategies.
    """
    quota_mode=_quota_mode
    if quota_mode not in ('alternate','patched','index'):raise ValueError('unknown quota mode')
    if type(prefix_cap) is not int or prefix_cap not in (31,63,127):raise ValueError('coroutine prefix cap must be 31, 63 or 127')
    if any(type(n) is not int for n in (prefix,prefix_limit,stack,output_base)) or not (0<=prefix<prefix_limit<=65536 and 0<stack<=65535 and 0<=output_base<65535):raise ValueError('invalid wrapper/stack/output reservation')
    if any(type(n) is not int or n<0 for n in (irq_code_bytes,irq_stack_bytes)):raise ValueError('IRQ reservations must be nonnegative integer bytes')
    if type(service_limit) is not int or not 0<service_limit<=10000:raise ValueError('service limit must be 1..10000 bytes')
    c=MiniAssembler(prefix);sites=[];patches=[];added_ranges=[]
    def store(name):c.abs16((0xed,0x53),name)
    def quota_enter():
        if quota_mode=='alternate':
            c.emit(0xd9);store('saved_alternate_de');c.abs16((0xed,0x5b),'quota_target');c.emit(0xd9)
        elif quota_mode=='index':
            c.abs16((0xdd,0x22),'saved_alternate_de');c.abs16((0xdd,0x2a),'quota_target')
    def quota_leave():
        if quota_mode=='alternate':c.emit(0xd9);c.abs16((0xed,0x5b),'saved_alternate_de');c.emit(0xd9)
        elif quota_mode=='index':c.abs16((0xdd,0x2a),'saved_alternate_de')
    # Caller-side demand synchronization never borrows IX. A repeated target
    # returns here before changing any preserved caller register or private SP.
    c.label('slice_until');c.abs16(0xcd,'slice_sync_target')
    c.abs16(0x2a,'slice_output');c.abs16((0xed,0x5b),'slice_target');c.emit(0xb7,0xed,0x52,0xd0)
    c.label('slice_resume');quota_enter()
    c.abs16((0xed,0x73),'slice_caller_sp');c.abs16((0xed,0x7b),'slice_decoder_sp');c.emit(0xe1,0xd1,0xc1,0xf1,0xc9)
    # Start on the private stack with a finish return. Save caller IX once per
    # entry; suspended AF/BC/DE/HL and the return PC encode every pending phase.
    c.label('begin');c.labels['slice_begin']=c.pc;c.abs16(0xcd,'slice_sync_target');quota_enter()
    c.abs16((0xed,0x73),'slice_caller_sp');c.emit(0xaf);c.abs16(0x32,'finished')
    c.emit(0x31);c.word(stack);c.abs16(0x21,'slice_finished');c.emit(0xe5)
    c.abs16(0x2a,'input_pointer');c.emit(0x11);c.word(output_base);c.abs16(0xc3,'dzx0_mega')
    # EOF alone reaches finish. Private depth is 12 at a yield: finish return
    # 2 + yield CALL return 2 + four saved pairs 8. Match copies need only 4.
    c.label('slice_finished');c.abs16(0x2a,'block_end');c.emit(0xb7,0xed,0x52);c.abs16(0xc2,'fatal')
    c.emit(0x3e,1);c.abs16(0x32,'finished');store('slice_output');quota_leave()
    c.abs16((0xed,0x7b),'slice_caller_sp');c.emit(0xc9)
    c.label('slice_yield');store('slice_output');c.emit(0xf5,0xc5,0xd5,0xe5)
    c.abs16((0xed,0x73),'slice_decoder_sp');quota_leave();c.abs16((0xed,0x7b),'slice_caller_sp');c.emit(0xc9)
    c.label('slice_sync_target')
    # Final demand must continue through raw EOF even after reaching the last
    # output byte. Reverse subtraction uses only equality; caller BC is dead.
    c.abs16(0x2a,'block_end');c.abs16((0xed,0x4b),'slice_target');c.emit(0xb7,0xed,0x42)
    c.rel8(0x20,'sync_ready');c.emit(0x01,0xff,0xff);c.label('sync_ready')
    if quota_mode in ('alternate','index'):c.abs16((0xed,0x43),'quota_target')
    else:
        # Fill these stores after collecting the phase-specific operand labels.
        c.emit(0x78)
        for index in range(12):c.abs16(0x32,f'quota_{index}_high_operand')
        c.emit(0x79)
        for index in range(12):c.abs16(0x32,f'quota_{index}_low_operand')
    c.emit(0xc9);c.label('fatal');c.emit(0x76);c.label('state')
    for name in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp','block_length','block_end','input_pointer','quota_target','saved_alternate_de'):
        c.label(name);c.word(0)
    c.label('block_stored');c.emit(0);c.label('finished');c.emit(0);c.label('end')
    c.labels['saved_quota_register']=c.labels['saved_alternate_de']
    def boundary(a,site):
        index=len(sites);name=f'quota_{index}';sites.append(dict(name=name,command=site))
        a.label(name+'_check');a.emit(0x08,0x7a)
        if quota_mode=='alternate':a.emit(0xd9,0xba,0xd9)
        elif quota_mode=='index':a.emit(0xdd,0xbc)
        else:a.labels[name+'_high_operand']=a.pc+1;a.emit(0xfe,0);patches.append(name+'_high_operand')
        a.abs16(0xda,name+'_fast');a.rel8(0x20,name+'_slow');a.emit(0x7b)
        if quota_mode=='alternate':a.emit(0xd9,0xbb,0xd9)
        elif quota_mode=='index':a.emit(0xdd,0xbd)
        else:a.labels[name+'_low_operand']=a.pc+1;a.emit(0xfe,0);patches.append(name+'_low_operand')
        a.abs16(0xda,name+'_fast');a.label(name+'_slow');a.emit(0x08)
        a.abs16(0xcd,'slice_yield');a.abs16(0xc3,name+'_check');a.label(name+'_fast');a.emit(0x08)
        added_ranges.append((a.labels[name+'_check'],a.pc))
    raw=raw_build(core=core,core_limit=core_limit,prefix_cap=prefix_cap,_quota_hook=boundary,_external_labels=c.labels)
    assert len(sites)==12
    labels=c.labels|raw[1];regions=[(prefix,c.resolve(labels)),*raw[0]]
    if c.pc>prefix_limit:raise ValueError('maximum coroutine wrapper exceeds prefix limit')
    if not (raw[2]['core_end']<=prefix or prefix_limit<=core):raise ValueError('code reservations overlap')
    if stack<12+irq_stack_bytes or any(stack>at and stack-12-irq_stack_bytes<at+len(blob) for at,blob in regions):raise ValueError('private stack overlaps generated code/state or wraps')
    code=sum(len(blob) for _,blob in regions)
    service=dict(code_and_embedded_state=code,extra_variables=0,tables=0,alignment=0,scratch=0,internal_buffers=0,
        caller_stack_including_call_return=4,private_stack=12,caller_irq_code=irq_code_bytes,
        caller_irq_headroom=irq_stack_bytes,private_irq_headroom=irq_stack_bytes)
    total=sum(service.values())
    if total>service_limit:raise ValueError(f'total service memory {total} exceeds {service_limit} bytes')
    metadata=dict(raw[2],entry='begin',variant='maximum-coroutine',one_shot=False,coroutine_supported=True,quota_mode=quota_mode,
        output_base=output_base,private_stack=stack,prefix_end=c.pc,code_bytes=code,code_and_state_bytes=code,
        state_bytes=labels['end']-labels['state'],max_decoder_stack_bytes=12,private_stack_bytes=12,caller_stack_bytes=4,
        service_memory=service,service_memory_bytes=total,workspace_bytes=code+16,
        service_limit_bytes=service_limit,quota_sites=sites,quota_check_before_gamma=True,
        same_fast_output_cursors=True,source_preparation_can_suspend_earlier=True,
        requires_undocumented_ix_halves=quota_mode=='index',quota_register='IX' if quota_mode=='index' else 'alternate DE' if quota_mode=='alternate' else 'patched operands',
        added_instruction_ranges=[(prefix,c.labels['state']),*added_ranges],
        patched_addresses=raw[2]['patched_addresses']+[labels[name] for name in patches],
        regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions])
    return regions,labels,metadata
