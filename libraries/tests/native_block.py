"""Protected one-shot native replay; plain CPU T-states, separate IM1 probes."""
from z80 import Z80Machine


def execute(profile,payload,expected,*,interrupts=False,source=0x2000,output=0xc000,
            caller_stack=0xbff0,alternate_af=0,watch=None):
    regions,labels,metadata=profile
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    stack,stop=caller_stack,0x100
    assert source+len(payload)<=min(at for at,_ in regions)
    assert output+len(expected)<=65535
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
    # A relocated caller stack permits long high-word gamma cases. Validate
    # every live allocation so a larger output cannot overwrite code, source,
    # caller/IRQ stack or the harness's return and interrupt entry sequences.
    allocations=[(at,at+len(data),'code') for at,data in regions]
    allocations += [(source,source+len(payload),'input'),
                    (stack-64,stack,'caller/IRQ stack'),(0x38,0x38+len(irq),'IRQ'),
                    (0x200,0x207,'IRQ bootstrap'),(stop,stop+1,'return breakpoint')]
    if expected:allocations.append((output,output+len(expected),'output/history'))
    for index,(lo,hi,name) in enumerate(allocations):
        assert 0<=lo<hi<=65536,('invalid allocation',name,lo,hi)
        for other_lo,other_hi,other_name in allocations[index+1:]:
            assert hi<=other_lo or other_hi<=lo,('overlapping allocations',name,other_name)
    for at,data in regions:m.set_memory_block(at,data)
    m.set_memory_block(source,payload)
    m.set_memory_block(stack-2,stop.to_bytes(2,'little'))
    entry=labels[metadata['entry']]
    m.pc,m.sp,m.hl,m.de=entry,stack-2,source,output
    m.alt_af=alternate_af
    preserved=dict(ix=0x1357,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1)
    for name,value in preserved.items():setattr(m,name,value)
    m.set_memory_block(0x38,irq)
    if interrupts:
        m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'))
        m.pc=0x200
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,data in regions:m.unmark_addrs(at,len(data),m.READ_MARK)
    for at,n in ((stack-64,64),(0x38,len(irq)),(0x200,7)):
        m.unmark_addrs(at,n,m.READ_MARK)
    for at in metadata.get('patched_addresses',[]):m.unmark_addr(at,m.WRITE_MARK)
    if watch:
        assert all(any(lo<=at<lo+len(blob) for lo,blob in regions) for at in watch)
        for at in watch:m.mark_addr(at,m.READ_MARK)
    high=output;cursor=source;lowest=stack-2
    def read(at):
        nonlocal cursor
        if watch and at in watch:
            watch[at](m)
            return m.memory[at]
        if source<=at<source+len(payload):
            assert at in (cursor,cursor-1),('nonsequential source',hex(at),hex(cursor),hex(m.pc))
            if at==cursor:cursor+=1
            assert m.memory[at]==payload[at-source]
        else:assert output<=at<high,('read outside source/history',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high,lowest
        if output<=at<output+len(expected):
            assert at==high and value==expected[at-output],('output differs',hex(at),hex(m.pc))
            high+=1
        else:
            assert stack-64<=at<stack,('write outside stack/output',hex(at),hex(m.pc))
            lowest=min(lowest,at)
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write)
    m.set_breakpoint(stop);budget=20_000_000;m.ticks_to_stop=budget;irqs=0;skipped=0
    while m.pc!=stop:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT
        if interrupts and m.pc!=stop and event&m._END_OF_FRAME:
            if not m.iff1 or m.int_disabled:skipped+=1;continue
            m.on_handle_active_int();assert m.pc==0x38;irqs+=1
    assert high==output+len(expected) and cursor==source+len(payload)
    assert m.hl==cursor and m.de==high and m.sp==stack
    assert all(getattr(m,name)==value for name,value in preserved.items())
    return dict(tstates=budget-m.ticks_to_stop,exact=True,injected_interrupts=irqs,
                unavailable_interrupt_events=skipped,stack_bytes=stack-lowest)
