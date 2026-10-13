"""Coherent physical-bank native Z80 harness for adaptive RAM verification."""
from z80 import Z80Machine

class MemoryMachine:
    def __init__(self,kind,code,labels,*,actual_pages=None):
        self.kind=kind
        self.count=actual_pages or {'128':8,'scorpion':16,'pentagon512':32,'pentagon1024':64}[kind]
        self.banks=[bytearray([i]*16384) for i in range(self.count)]
        self.rom=bytearray(16384);self.rom[0x3d13]=0xc9
        self.low=self.high=self.eff=0;self.locked=False;self.selected=0
        self.physical_reads=[];self.page_writes=[];self.labels=labels
        self.m=Z80Machine()
        self.banks[2][0x3800:0x3800+len(code)]=code
        self.m.set_read_callback(self.read)
        self.m.set_write_callback(self.write)
        self.m.mark_addrs(0,65536,self.m.READ_MARK|self.m.WRITE_MARK)
        self.m.set_output_callback(self.output)
        self.m.set_breakpoint(0x40);self.m.set_breakpoint(0x3d13)

    def where(self,address):
        if address<0x4000:return self.rom,address
        if address<0x8000:return self.banks[5],address-0x4000
        if address<0xc000:return self.banks[2],address-0x8000
        return self.banks[self.selected],address-0xc000

    def read(self,address):
        bank,offset=self.where(address);return bank[offset]

    def write(self,address,value):
        bank,offset=self.where(address)
        if bank is not self.rom:bank[offset]=value

    def output(self,port,value):
        if port==0xeff7:
            if self.kind=='pentagon1024' and not self.locked:self.eff=value
        elif port==0x1ffd and self.kind=='scorpion':
            if not self.locked:self.high=value
        elif port&0x8002==0:
            if not self.locked:
                self.low=value
                if self.kind!='pentagon1024' or self.eff&4:self.locked=bool(value&32)
        page=self.low&7
        if self.kind=='scorpion':page|=(self.high&16)>>1
        elif self.kind=='pentagon512':page|=(self.low&0xc0)>>3
        elif self.kind=='pentagon1024' and not self.eff&4:page|=(self.low&0xc0)>>3|self.low&32
        self.selected=page%self.count
        self.page_writes.append(self.selected)

    @staticmethod
    def sector(number):return bytes((number*17+i*13)%256 for i in range(256))

    def call(self,label,**registers):
        for name,value in registers.items():setattr(self.m,name,value)
        self.m.sp=0x5ffe;self.write(0x5ffe,0x40);self.write(0x5fff,0)
        self.m.pc=self.labels[label];self.m.ticks_to_stop=100_000_000
        while self.m.pc!=0x40:
            outcome=self.m.run()
            if self.m.pc==0x3d13:
                assert self.selected<8,'TR-DOS was called with extended RAM selected'
                number=(self.m.de>>8)*16+(self.m.de&255)
                self.physical_reads.append(number)
                for i,value in enumerate(self.sector(number)):self.write(self.m.hl+i,value)
                self.m.clear_breakpoint(0x3d13)
                self.m.ticks_to_stop=4
                self.m.run()
                self.m.set_breakpoint(0x3d13)
                self.m.ticks_to_stop=100_000_000
            elif outcome&self.m._TICKS_LIMIT_HIT:raise AssertionError('native cache timeout')

    def word(self,address):return self.read(address)|self.read(address+1)<<8

