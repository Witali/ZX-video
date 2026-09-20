"""CPU verification of B2 queue consumption, with guarded banks and timing."""
from collections import Counter

from benchmark_compact_screen import NativeCPU,STACK,STOP
from benchmark_context_huffman import word
from frame_output_pipeline import display_screen
import cell_screen_z80 as old
import pipelined_frame_z80 as paging
import prepared_cells_z80 as machine
from validate_fast_sparse import CPU

ACTIVE=set(((y&0xc0)<<5)|((y&7)<<8)|((y&0x38)<<2)|x for y in range(24,168) for x in range(32))
ACTIVE.update(range(0x1860,0x1aa0))


class GuardCPU(NativeCPU):
    def read8(self,address):
        if self.guarding and address>=0xc000 and self.port_7ffd&7 in (3,4):
            key=(self.port_7ffd&7,address)
            if key not in self.queue_valid: raise AssertionError(f'queue overread {key}')
            value=super().read8(address); self.queue_reads.append(value)
            return value
        return super().read8(address)

    def write8(self,address,value):
        if self.guarding:
            bank=self.port_7ffd&7
            if 0x4000<=address<0x5b00 or bank==7 and 0xc000<=address<0xdb00:
                physical=5 if address<0x8000 else 7
                if physical!=self.target_bank or address&0x3fff not in ACTIVE:
                    raise AssertionError(f'visible screen or border write {address:04x}, bank {physical}')
            elif not (self.state[0]<=address<self.state[1] or STACK-96<=address<STACK
                    or machine.STAGE<=address<machine.STAGE+128
                    or machine.MASK<=address<machine.MASK+90
                    or address==paging.SHADOW or address in self.mutable_operands):
                raise AssertionError(f'write outside owned regions {address:04x}, bank {bank}')
        return CPU.write8(self,address,value)


class Harness:
    def __init__(self,*,baseline=False,start=0,unrolled_staging=False):
        self.baseline=baseline; self.cursor=start
        options=dict(fast_mask_dispatch=True,constant_attribute_borders=True,skip_black_borders=True,page_entry=machine.PAGE)
        self.code,self.labels,self.listing,self.regions=old.build(**options) if baseline else machine.build(unrolled_staging=unrolled_staging)
        regions,page_labels,listing=paging.build_video(dict(saved_page=0,screen_base=0),dict(history_page=0),dict(elapsed_fields=0))
        self.paging_regions=[(base,data) for base,data in regions if base!=paging.VIDEO]
        self.listing += [dict(r,stage='atomic_paging') for r in listing if paging.PAGE<=r['address']<paging.STATE]
        self.instructions={r['address']:r for r in self.listing}; self.histogram=Counter()
        self.cpu=GuardCPU(b'',b''); cpu=self.cpu
        cpu.state=self.labels['state'],self.labels['end']
        cpu.mutable_operands={self.labels[k] for k in ('copy_operand',) if k in self.labels}
        for bank in range(8): cpu.banks[bank][:]=b'\xa5'*16384
        for bank in (5,7): cpu.banks[bank][:6912]=bytes(6144)+bytes([1])*768
        cpu.port_7ffd=0x16
        for base,data in [(machine.CODE,self.code)]+self.regions+self.paging_regions:
            for i,v in enumerate(data): cpu.write8(base+i,v)
        self.screens={bank:bytes(cpu.banks[bank][:6912]) for bank in (5,7)}

    def run(self,state,mask,index,interrupt=None):
        cpu=self.cpu; cpu.guarding=False
        payload=machine.body(state,mask); target=7 if index%2==0 else 5
        page=0x16 if target==7 else 0x1e; cpu.port_7ffd=page; cpu.target_bank=target
        cpu.write8(paging.SHADOW,page)
        cpu.queue_valid={}; cpu.queue_reads=[]
        if self.baseline:
            for base,data in ((old.FRAME,state),(0xa400,mask)):
                for i,v in enumerate(data): cpu.write8(base+i,v)
            cpu.write8(self.labels['saved_page'],page); cpu.set_hl(0xa400)
        else:
            for i,v in enumerate(payload):
                pos=(self.cursor+i)%(2*machine.RING_BANK_BYTES)
                bank=3+pos//machine.RING_BANK_BYTES; addr=machine.RING_BEGIN+pos%machine.RING_BANK_BYTES
                cpu.banks[bank][addr&16383]=v; cpu.queue_valid[bank,addr]=v
            bank=3+self.cursor//machine.RING_BANK_BYTES
            word(cpu,self.labels['read_pointer'],machine.RING_BEGIN+self.cursor%machine.RING_BANK_BYTES)
            cpu.write8(self.labels['read_bank'],bank)
        cpu.a=0xc0 if target==7 else 0x40; cpu.pc=self.labels['draw']; cpu.sp=STACK
        cpu.push(STOP); cpu.guarding=True
        start=cpu.tstates; count=0; irq=0; stages=Counter(); pages=[]; windows=[]
        while cpu.pc!=STOP:
            pc=cpu.pc; before=cpu.tstates; old_page=cpu.port_7ffd
            if not self.baseline and pc==self.labels['window']:
                windows.append(dict(bytes=cpu.c,cursor=(cpu.read8(self.labels['read_bank'])-3)*machine.RING_BANK_BYTES
                    +word(cpu,self.labels['read_pointer'])-machine.RING_BEGIN))
            row=self.instructions[pc]; cpu.step(); t=cpu.tstates-before
            expected=row['tstates']
            if t not in (expected if isinstance(expected,list) else [expected]): raise AssertionError(('instruction timing',row,t))
            self.histogram[pc,t]+=1; stages[row['stage']]+=t
            if old_page!=cpu.port_7ffd: pages.append(cpu.port_7ffd)
            count+=1
            if count>100000: raise AssertionError('consumer failed to return')
            if interrupt and cpu.pc!=STOP: irq+=interrupt(cpu)
        cpu.guarding=False
        self.screens[target]=display_screen(state,black_borders=True)
        if any(bytes(cpu.banks[b][:6912])!=screen for b,screen in self.screens.items()):
            raise AssertionError(('native screen differs',index,target))
        if cpu.port_7ffd!=page or cpu.sp!=STACK or sum(stages.values())!=cpu.tstates-start-irq:
            raise AssertionError('paging/stack/timing differs')
        baseline=old.expected_tstates(mask,fast_mask_dispatch=True,constant_attribute_borders=True,skip_black_borders=True)+186
        if self.baseline:
            if sum(stages.values())!=baseline: raise AssertionError(('baseline formula',sum(stages.values()),baseline))
        else:
            if bytes(cpu.queue_reads)!=payload: raise AssertionError('queue cursor/order differs')
            self.cursor=(self.cursor+len(payload))%(2*machine.RING_BANK_BYTES)
            actual=(cpu.read8(self.labels['read_bank'])-3)*machine.RING_BANK_BYTES+word(cpu,self.labels['read_pointer'])-machine.RING_BEGIN
            if actual%(2*machine.RING_BANK_BYTES)!=self.cursor: raise AssertionError('queue end differs')
            for (bank,addr),v in cpu.queue_valid.items():
                if cpu.banks[bank][addr&16383]!=v: raise AssertionError('queue source mutated')
        return dict(index=index,target_bank=target,body_bytes=len(payload),tstates=sum(stages.values()),
            stages=dict(stages),baseline_tstates=baseline,delta_tstates=sum(stages.values())-baseline,
            page_writes=len(pages),windows=len(windows),irq_tstates=irq)
