"""Protected same-quota replay with exact EOF status and both stack peaks."""
from z80 import Z80Machine


def execute(profile,payload,expected,*,targets=None,interrupts=False,source=0x2000,
            caller_stack=0xbff0,watch=None,force_irq=False,irq_clobber_ix=False):
    regions,z,meta=profile;m=Z80Machine();m.memory[:]=b'\xa5'*65536
    output,private,stop=meta['output_base'],meta['private_stack'],0x100
    for top in (caller_stack,private):
        assert output+len(expected)<=top-128 or output>=top
        assert source+len(payload)<=top-128 or source>=top
    for at,blob in regions:
        assert source+len(payload)<=at or source>=at+len(blob)
        assert output+len(expected)<=at or output>=at+len(blob)
        m.set_memory_block(at,blob)
    def word(at,n):m.set_memory_block(at,n.to_bytes(2,'little'))
    m.set_memory_block(source,payload);word(z['input_pointer'],source)
    word(z['block_end'],output+len(expected));word(z['block_length'],len(expected))
    irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed4d')
    if irq_clobber_ix:irq=bytes.fromhex('f5 08 f5 dde5 dd21efbe dde1 3e55eeaa f1 08 f1 fb ed4d')
    m.set_memory_block(0x38,irq)
    m.mark_addrs(0,65536,m.READ_MARK|m.WRITE_MARK)
    for at,blob in regions:m.unmark_addrs(at,len(blob),m.READ_MARK)
    for at,n in ((caller_stack-128,128),(private-128,128),(0x38,len(irq)),(0x200,7)):
        m.unmark_addrs(at,n,m.READ_MARK)
    m.unmark_addrs(z['state'],z['end']-z['state'],m.WRITE_MARK)
    for at in meta['patched_addresses']:m.unmark_addr(at,m.WRITE_MARK)
    if watch:
        for at in watch:m.mark_addr(at,m.READ_MARK)
    high=output;cursor=source;lowest_caller=caller_stack;lowest_private=private
    def read(at):
        nonlocal cursor
        if watch and at in watch:watch[at](m);return m.memory[at]
        if output<=at<high:return m.memory[at]
        if source<=at<source+len(payload):
            assert at in (cursor,cursor-1),('source order',hex(at),hex(cursor),hex(m.pc))
            cursor=max(cursor,at+1);assert m.memory[at]==payload[at-source]
        else:assert output<=at<high,('read outside initialized memory',hex(at),hex(m.pc))
        return m.memory[at]
    def write(at,value):
        nonlocal high,lowest_caller,lowest_private
        if output<=at<output+len(expected):
            assert at==high and value==expected[at-output],('wrong output',hex(at),hex(m.pc))
            assert not cursor<=at<source+len(payload),('overwritten unread input',hex(at),hex(cursor))
            high+=1
        elif caller_stack-128<=at<caller_stack:lowest_caller=min(lowest_caller,at)
        elif private-128<=at<private:lowest_private=min(lowest_private,at)
        else:raise AssertionError(('write outside permitted memory',hex(at),hex(m.pc)))
        m.memory[at]=value
    m.set_read_callback(read);m.set_write_callback(write)
    m.set_breakpoint(stop);m.set_breakpoint(z['fatal']);m.set_breakpoint(z['slice_finished'])
    if targets is None:targets=list(range(256,len(expected),256))+[len(expected)]
    costs=[];cursors=[];finished_states=[];input_cursors=[];irqs=0;forced_irqs=0;periodic_irqs=0;finished=False;forced_hits=set()
    for index,target in enumerate(targets):
        preserved={name:0x1357+index for name in ('ix','iy','alt_bc','alt_de','alt_hl')}
        for name,value in preserved.items():setattr(m,name,value)
        word(z['slice_target'],output+target);word(caller_stack-2,stop)
        entry=z['begin' if index==0 else 'slice_until'];m.pc,m.sp=entry,caller_stack-2
        force=set()
        if force_irq:
            force={entry,z['slice_sync_target'],z['slice_yield'],z['slice_finished']}
            force.update(z[site['name']+'_check']+2 for site in meta.get('quota_sites',[]))
            for at in force:m.set_breakpoint(at)
        if interrupts or force_irq:m.set_memory_block(0x200,bytes.fromhex('ed56fb00c3')+entry.to_bytes(2,'little'));m.pc=0x200
        m.ticks_to_stop=20_000_000
        while m.pc!=stop:
            event=m.run();assert not event&m._TICKS_LIMIT_HIT and m.pc!=z['fatal']
            if m.pc==z['slice_finished']:
                finished=True;m.clear_breakpoint(z['slice_finished'])
            forced=m.pc in force
            if forced:
                force.remove(m.pc);forced_hits.add(m.pc);m.clear_breakpoint(m.pc)
            if (forced or (interrupts and m.pc!=stop and event&m._END_OF_FRAME)) and m.iff1 and not m.int_disabled:
                m.on_handle_active_int();assert m.pc==0x38;irqs+=1
                if forced:forced_irqs+=1
                else:periodic_irqs+=1
        assert m.sp==caller_stack and high>=output+target
        assert all(getattr(m,name)==value for name,value in preserved.items()),('caller pair changed',preserved)
        assert int.from_bytes(m.memory[z['input_pointer']:z['input_pointer']+2],'little')==source
        if 'finished' in z:assert bool(m.memory[z['finished']])==finished
        costs.append(20_000_000-m.ticks_to_stop);cursors.append(high-output);finished_states.append(finished);input_cursors.append(cursor-source)
        for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):setattr(m,name,0x9797)
    assert finished and cursor==source+len(payload) and high==output+len(expected)
    return dict(tstates=sum(costs),slices=costs,output_cursors=cursors,finished_states=finished_states,input_cursors=input_cursors,
        exact=True,injected_interrupts=irqs,forced_interrupts=forced_irqs,periodic_interrupts=periodic_irqs,forced_irq_addresses=sorted(forced_hits),irq_stub_bytes=len(irq),
        caller_stack_bytes=caller_stack-lowest_caller,private_stack_bytes=private-lowest_private)
