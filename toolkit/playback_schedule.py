"""Ring producer, per-frame read quota and IM2 clock for ZX0 playback."""


def minimum_queue(demands, startup, capacity, quota):
    """Conservative sector schedule; frame zero has no producer phase."""
    queued=startup;unread=sum(demands)-startup;lowest=queued
    for index,need in enumerate(demands):
        queued-=need;lowest=min(lowest,queued)
        if index:
            produced=min(quota,capacity-queued,unread)
            queued+=produced;unread-=produced
    return lowest


def emit_producer(a, capacity, batch, *, keepalive_fields=0, cached_keepalive=False):
    def load(name): a.abs16(0x3A,name)
    def save(name): a.abs16(0x32,name)
    a.label('producer_one')
    a.emit(0x21); a.word(capacity)
    a.abs16((0xED,0x5B),'ring_count'); a.emit(0xB7,0xED,0x52)
    a.abs16(0xCA,'producer_idle')
    a.emit(0x06,batch,0x7C,0xB7); a.rel8(0x20,'batch_free_ready')
    a.emit(0x7D,0xB8); a.rel8(0x30,'batch_free_ready'); a.emit(0x47)
    a.label('batch_free_ready')
    a.abs16(0x2A,'disk_sectors_remaining'); a.emit(0x7C,0xB5)
    a.abs16(0xCA,'producer_idle')
    a.emit(0x7C,0xB7); a.rel8(0x20,'batch_disk_ready')
    a.emit(0x7D,0xB8); a.rel8(0x30,'batch_disk_ready'); a.emit(0x47)
    a.label('batch_disk_ready')
    load('ring_write_high'); a.emit(0xED,0x44,0xB8)
    a.rel8(0x30,'batch_bank_ready'); a.emit(0x47)
    a.label('batch_bank_ready')
    load('disk_sector'); a.emit(0x5F,0x3E,16,0x93,0xB8)
    a.rel8(0x30,'batch_track_ready'); a.emit(0x47)
    a.label('batch_track_ready')
    a.emit(0x78); save('read_count')
    load('ring_write_region'); a.abs16(0xCD,'page_queue_region')
    load('ring_write_high'); a.emit(0x67,0x2E,0)
    load('read_count'); a.emit(0x47); a.abs16(0xCD,'read_n')
    load('read_count'); a.emit(0x5F,0x16,0)
    a.abs16(0x2A,'ring_count'); a.emit(0x19); a.abs16(0x22,'ring_count')
    a.abs16(0x2A,'disk_sectors_remaining'); a.emit(0xB7,0xED,0x52)
    a.abs16(0x22,'disk_sectors_remaining')
    load('ring_write_high'); a.emit(0x83)
    a.rel8(0x20,'batch_store_high')
    load('ring_write_region'); a.emit(0x3C,0xFE,6)
    a.rel8(0x38,'batch_store_region'); a.emit(0x3E,1)
    a.label('batch_store_region'); save('ring_write_region')
    a.emit(0x3E,0xC0)
    a.label('batch_store_high'); save('ring_write_high')
    load('read_count'); a.emit(0xC9)
    a.label('producer_idle')
    if keepalive_fields: a.abs16(0xCD,'motor_keepalive')
    a.emit(0xAF,0xC9)
    if keepalive_fields:
        a.label('motor_keepalive')
        a.abs16(0x2A,'disk_sectors_remaining');a.emit(0x7C,0xB5,0xC8)
        a.abs16(0x2A,'elapsed_fields');a.abs16((0xED,0x5B),'last_disk_fields')
        a.emit(0xB7,0xED,0x52,0x11);a.word(keepalive_fields)
        a.emit(0xB7,0xED,0x52,0xD8)
        if cached_keepalive:
            a.abs16(0xC3,'keepalive_seek')
            return
        # Read into scratch while the ring is full. Preserve the next stream
        # sector and queue occupancy; it is consumed only by the real producer.
        load('disk_track');a.emit(0x57);load('disk_sector');a.emit(0x5F,0xD5)
        a.emit(0x21);a.word(0x7C00);a.emit(0x06,1);a.abs16(0xCD,'read_n')
        a.emit(0xD1,0x7A);save('disk_track');a.emit(0x7B);save('disk_sector')
        a.emit(0xC9)


def emit_clock(a, *, dos_irq=False, full_rom_clock=False, memory_clock=False):
    a.label('setup_clock')
    if memory_clock:
        a.emit(0x21);a.word(0);a.abs16(0x22,'elapsed_fields')
    elif dos_irq:a.emit(0xD9,0x21,0,0,0xD9)
    a.emit(0x21); a.word(0xBE00 if dos_irq else 0x7E00)
    a.emit(0x11); a.word(0xBE01 if dos_irq else 0x7E01)
    a.emit(0x01); a.word(256)
    a.emit(0x36,0xBD if dos_irq else 0x7F,0xED,0xB0)
    a.abs16(0x21,'clock_isr_template')
    a.emit(0x11); a.word(0xBD80 if memory_clock else 0xBDBD if dos_irq else 0x7F7F)
    a.emit(0x01); a.word(13 if memory_clock else 7 if dos_irq else 12)
    a.emit(0xED,0xB0)
    if full_rom_clock:
        a.abs16(0x21,'clock_slow_template');a.emit(0x11);a.word(0xBD00)
        a.emit(0x01);size_pos=len(a.code);a.word(0);a.emit(0xED,0xB0)
    if memory_clock:
        # The vector always executes JP nn. Only its operand changes, in one
        # atomic LD (nn),HL, so fast/ROM handlers can switch with IRQ enabled.
        a.emit(0x3E,0xC3,0x32);a.word(0xBDBD)
        select_rom_clock(a,False,True)
    a.emit(0x3E,0xBE if dos_irq else 0x7E,0xED,0x47,0xED,0x5E,0xC9)
    a.label('clock_isr_template')
    if dos_irq:
        if memory_clock:
            # INC HL leaves AF intact. An atomic LD reads the counter in the
            # foreground, so its entire scheduling loop can keep IRQ enabled.
            a.emit(0xE5);a.abs16(0x2A,'elapsed_fields')
            a.emit(0x23);a.abs16(0x22,'elapsed_fields');a.emit(0xE1)
        else:a.emit(0xD9,0x23,0xD9)
        a.emit(0xFB,0xC3);a.word(0x3D2F)
        if full_rom_clock:
            a.label('clock_slow_template')
            a.emit(0xF5,0xE5)
            if memory_clock:
                a.abs16(0x2A,'elapsed_fields');a.emit(0x23);a.abs16(0x22,'elapsed_fields')
            else:a.emit(0xD9,0x23,0xD9)
            a.emit(0x21);a.word(5)
            a.emit(0x39,0x7E,0xFE,0x1F);a.rel8(0x20,'clock_return_dos')
            a.emit(0x2B,0x7E,0xFE,0x54);a.rel8(0x38,'clock_return_dos')
            a.emit(0xFE,0x60);a.rel8(0x30,'clock_return_dos')
            a.emit(0xE1,0xF1,0xFB,0xED,0x4D)
            a.label('clock_return_dos');a.emit(0xE1,0xF1,0xFB,0xC3);a.word(0x3D2F)
            size=a.pc-a.labels['clock_slow_template']
            if size>(0x80 if memory_clock else 0xBD):raise ValueError('ROM clock handler overlaps fast ISR')
            a.code[size_pos:size_pos+2]=bytes([size,0])
        return
    a.emit(0xE5)
    a.abs16(0x2A,'elapsed_fields'); a.emit(0x23); a.abs16(0x22,'elapsed_fields')
    a.emit(0xE1,0xFB)
    a.emit(0xED,0x4D)
    assert a.pc-a.labels['clock_isr_template'] == 12


def select_rom_clock(a, slow, memory_clock=False):
    if memory_clock:
        a.emit(0x21);a.word(0xBD00 if slow else 0xBD80)
        a.emit(0x22);a.word(0xBDBE)
        return
    if slow:
        a.emit(0x3E,0xC3,0x32);a.word(0xBDBD)
        a.emit(0x21);a.word(0xBD00);a.emit(0x22);a.word(0xBDBE)
    else:
        a.emit(0x21);a.word(0x23D9);a.emit(0x22);a.word(0xBDBD)
        a.emit(0x3E,0xD9,0x32);a.word(0xBDBF)


def emit_wait(a, *, dos_irq=False, quota=0, lookahead=False, memory_clock=False):
    a.label('prefetch_loop')
    if quota:
        a.emit(0x3E,quota);a.abs16(0x32,'prefetch_remaining')
        a.label('prefetch_check')
    if memory_clock:a.emit(0xFB)
    elif dos_irq:
        a.emit(0xD9);a.abs16(0x22,'elapsed_fields');a.emit(0xD9)
    if not memory_clock:a.label('clock_check')
    # A late frame still runs its producer quota. The builder verifies that
    # this quota covers every block burst from the chosen startup backlog.
    # Without a quota, retain the earlier 64-sector low-water policy.
    loop='prefetch_check' if quota else 'prefetch_loop'
    if quota:
        a.abs16(0x3A,'prefetch_remaining');a.emit(0xB7);a.rel8(0x28,'check_deadline')
        a.abs16(0xCD,'producer_one');a.emit(0xB7);a.rel8(0x28,'quota_idle')
        a.abs16(0x3A,'prefetch_remaining');a.emit(0x3D);a.abs16(0x32,'prefetch_remaining')
        a.rel8(0x18,loop)
        a.label('quota_idle');a.emit(0xAF);a.abs16(0x32,'prefetch_remaining')
    else:
        a.abs16(0x2A,'ring_count'); a.emit(0x7C,0xB7)
        a.rel8(0x20,'check_deadline'); a.emit(0x7D,0xFE,64)
        a.rel8(0x30,'check_deadline')
        a.abs16(0xCD,'producer_one'); a.emit(0xB7)
        a.rel8(0x20,loop)
    a.label('check_deadline')
    if memory_clock:a.label('clock_check')
    a.abs16(0x2A,'elapsed_fields')
    a.abs16((0xED,0x5B),'next_frame_field')
    a.emit(0xB7,0xED,0x52,0xCB,0x7C)
    a.rel8(0x28,'frame_due')
    if lookahead:
        # Negative elapsed-deadline: leave a complete field for a bounded
        # quantum. Quota is already fulfilled before this optional work.
        a.emit(0x23,0x7C,0xB5);a.rel8(0x28,'ahead_wait_field')
        a.emit(0xFB);a.label('ahead_call');a.abs16(0xCD,'ahead_prefetch')
        a.label('ahead_return')
        if not memory_clock:a.emit(0xF3)
        a.emit(0xB7)
        a.abs16(0xC2,loop)
    a.abs16(0xCD,'producer_one')
    a.emit(0xB7); a.rel8(0x20,loop)
    if lookahead:a.label('ahead_wait_field')
    a.abs16(0xCD,'wait_field'); a.rel8(0x18,loop)
    a.label('frame_due')
    a.abs16(0x2A,'next_frame_field'); a.emit(0x11); a.word(6)
    a.emit(0x19); a.abs16(0x22,'next_frame_field')
