"""Complete native block replay with protected RAM and optional IM1 probes.

Counts deterministic Z80 instructions in flat memory. ROM, physical disk,
ULA contention and a publication scheduler require a separate application test.
"""
from z80 import Z80Machine

def put_word(machine, address, value):
    machine.set_memory_block(address, value.to_bytes(2, 'little'))

def execute(regions, labels, layout, payload, expected, interrupts=False, *, source=0x4000,
            caller_stack=0xbff0,slice_bytes=256):
    m = Z80Machine()
    m.memory[:] = b'\xa5'*65536
    for address,data in regions:
        assert source+len(payload)<=address or source>=address+len(data),('input overlaps code',hex(source),hex(address))
        m.set_memory_block(address,data)
    output,stack,stop = layout.get('output_base', 0xc000),caller_stack,0x100
    private_stack = layout.get('private_stack', 0x7be0)
    for top in (stack,private_stack):
        if not (output+len(expected)<=top-128 or output>=top):
            raise ValueError('output overlaps a native replay stack; choose caller_stack/private_stack')
    m.set_memory_block(source,payload)
    put_word(m,labels['input_pointer'],source)
    put_word(m,labels['block_end'],output+len(expected))
    put_word(m,labels['block_length'],len(expected))
    m.set_breakpoint(stop)
    # Register-preserving IM1 handler also alters AF' temporarily.
    irq = bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
    m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for address,data in regions:
        m.unmark_addrs(address,len(data),m.READ_MARK)
    for lo,hi in ((source,source+len(payload)),(stack-128,stack),
                  (private_stack-128,private_stack),(0x38,0x38+len(irq)),(0x200,0x207)):
        m.unmark_addrs(lo,hi-lo,m.READ_MARK)
    m.unmark_addrs(labels['state'],labels['end']-labels['state'],m.WRITE_MARK)
    for address in layout['patched_addresses']:
        m.unmark_addr(address,m.WRITE_MARK)
    high=output;private_low=private_stack;caller_low=stack-2
    def read(address):
        assert output<=address<high,('invalid read',hex(address),hex(m.pc))
        return m.memory[address]
    def write(address,value):
        nonlocal high,private_low,caller_low
        if output<=address<output+len(expected):
            assert address==high,('nonsequential output',hex(address))
            high+=1
        else:
            assert (stack-128<=address<stack or
                    private_stack-128<=address<private_stack),('invalid write',hex(address),hex(m.pc))
            if stack-128<=address<stack:caller_low=min(caller_low,address)
            if private_stack-128<=address<private_stack:private_low=min(private_low,address)
        m.memory[address]=value
    m.set_read_callback(read);m.set_write_callback(write)
    slices=[];output_cursors=[];irqs=0;unavailable_irqs=0
    targets=([len(expected)] if slice_bytes is None else list(range(slice_bytes,len(expected),slice_bytes))+[len(expected)])
    for index,target in enumerate(targets):
        put_word(m,labels['slice_target'],output+target)
        put_word(m,stack-2,stop)
        entry=labels['begin' if index==0 else 'slice_until']
        m.pc,m.sp=entry,stack-2
        if interrupts:
            m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'))
            m.pc=0x200
        budget=20_000_000;m.ticks_to_stop=budget
        while m.pc!=stop:
            event=m.run()
            assert not event&m._TICKS_LIMIT_HIT and m.pc!=labels['fatal']
            if interrupts and m.pc!=stop and event&m._END_OF_FRAME:
                # A frame event may fall between opcode prefix bytes or in
                # EI's one-instruction delay. The real CPU cannot accept an
                # interrupt there. Count skipped synthetic pulses explicitly.
                if not m.iff1 or m.int_disabled:
                    unavailable_irqs+=1
                    continue
                m.on_handle_active_int()
                assert m.pc==0x38
                irqs+=1
        assert m.sp==stack and high>=output+target
        slices.append(budget-m.ticks_to_stop)
        # Expose each published output frontier so candidate checks can prove
        # identical quota boundaries, beyond merely matching final output.
        output_cursors.append(high-output)
        # The caller may overwrite every working register between demands.
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):
            setattr(m,name,0x9797)
    assert bytes(m.memory[output:high])==expected and high==output+len(expected)
    return dict(tstates=sum(slices),slices=slices,output_cursors=output_cursors,publication_offsets=output_cursors,
                exact=True,injected_interrupts=irqs,
                private_stack_bytes=private_stack-private_low,caller_stack_bytes=stack-caller_low,
                unavailable_interrupt_events=unavailable_irqs)
