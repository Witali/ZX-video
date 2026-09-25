"""Inline cached short Huffman paths into sparse bitmap patches in bank 6.

The shared long fallback stays in fixed RAM. Only short lookup, local patch
control and long-return stubs are copied into unused table-tail RAM. Input
bytes, Huffman tables, the original fixed code and its state ABI stay put;
one three-byte JP redirects nonempty temporal patches into this experiment.
"""
from collections import Counter
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from prefix_huffman_z80 import prepare

ORIGIN,LIMIT=0xec00,0xf000


def build(read8,instructions,labels,table_bytes,*,origin=ORIGIN):
    if origin<0xc000+table_bytes or origin>=LIMIT:
        raise ValueError('Huffman tail has no room for inline patch code')
    start,end=labels['patches_nonzero'],labels['attributes']+1
    short_start,short_end=labels['bitmap'],labels['long']
    if (read8(start)!=0x2a or read8(end-1)!=0xc9 or
        read8(short_end-1)!=0xc9 or 'cache_short_refresh' not in labels):
        raise ValueError('requires sparse patches and cached carry-Huffman')
    rows={r['address']:r for r in instructions}
    def segment(lo,hi):
        pcs=sorted(pc for pc in rows if lo<=pc<hi)
        if not pcs or pcs[0]!=lo:raise ValueError('incomplete instruction listing')
        return [(rows[pc],bytes(read8(i) for i in range(pc,nxt)))
                for pc,nxt in zip(pcs,pcs[1:]+[hi])]
    main,short=segment(start,end),segment(short_start,short_end)
    a=MiniAssembler(origin);listing=[];entries=[];stubs=[];calls=[]
    def emit(row,blob):
        listing.append(dict(row,address=a.pc,phase='reconstruct'));a.emit(*blob)
    def branch(row,opcode,target,ticks,relative=False):
        listing.append(dict(row,address=a.pc,tstates=ticks,phase='reconstruct'))
        (a.rel8 if relative else a.abs16)(opcode,target)
    for row,blob in main:
        pc=row['address'];a.label(f'patch_{pc}')
        if row['instruction']=='CALL bitmap':
            if blob!=bytes([0xcd,short_start&255,short_start>>8]):raise ValueError('wrong bitmap call')
            calls.append(pc);entries.append(a.pc)
            for inner,data in short:
                ip=inner['address'];a.label(f'short_{pc}_{ip}')
                if ip==short_end-1:continue  # Fall through to EXX/store.
                if data[0] in (0x18,0x20,0x28,0x30,0x38):
                    target=ip+2+int.from_bytes(data[1:],'little',signed=True)
                    if data[0]==0x28 and target==short_end:
                        branch(dict(inner,instruction='JP Z,long stub'),0xca,f'long_{pc}',10)
                    else:
                        if not short_start<=target<short_end:raise ValueError('external short branch')
                        branch(inner,data[0],f'short_{pc}_{target}',inner['tstates'],True)
                else:emit(inner,data)
        elif blob[0] in (0xc3,0xc2,0xca,0xd2,0xda):
            target=int.from_bytes(blob[1:],'little')
            if not start<=target<end:raise ValueError('external patch jump')
            branch(row,blob[0],f'patch_{target}',row['tstates'])
        else:emit(row,blob)
    if len(calls)!=16:raise ValueError('expected sixteen unrolled sparse correction sites')
    for pc in calls:
        a.label(f'long_{pc}');stubs.append(a.pc)
        # Prefix decoder updates IX/C/B and returns A exactly as before.
        a.labels['shared_long']=short_end
        branch(dict(instruction='CALL shared long',stage='inline_huffman'),0xcd,'shared_long',17)
        branch(dict(instruction='JP patch continuation',stage='inline_huffman'),0xc3,f'patch_{pc+3}',10)
    code=a.resolve()
    if a.pc>LIMIT:raise ValueError(('inline patches overlap shift pages',len(code),LIMIT-origin))
    redirect=bytes([0xc3,origin&255,origin>>8])
    return code,dict(origin=origin,end=a.pc,code_bytes=len(code),code_sha256=sha(code),
        code_hex=code.hex(),redirect_address=start,redirect_bytes=redirect.hex(),
        table_body_bytes=table_bytes,free_bytes_before_shift=LIMIT-a.pc,
        symbol_entries=entries,long_stubs=stubs,original_call_sites=calls,
        symbol_exits=[a.labels[f'patch_{pc+3}'] for pc in calls],
        entry_delta_tstates=10,short_delta_tstates=-24,long_delta_tstates=8,
        extra_stack_bytes=0,extra_stream_bytes=0,listing=listing,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def install_stage(h,tables,mapping):
    """Install after optional address relocation; retain bank-7 metadata code."""
    c=h.cpu;c.guarding=False
    if c.port_7ffd&7!=6:raise ValueError('bank 6 must be mapped')
    table_bytes=prepare(tables,mapping,carry_huffman=True)['body_bytes']
    code,report=build(c.read8,h.instructions.values(),h.recon,table_bytes)
    for i,v in enumerate(code):c.write8(ORIGIN+i,v)
    at=report['redirect_address']
    for i,v in enumerate(bytes.fromhex(report['redirect_bytes'])):c.write8(at+i,v)
    fixed=dict(h.instructions)
    fixed[at]=dict(address=at,instruction='JP inline patches',tstates=10,phase='reconstruct',stage='patch')
    banked={r['address']:r for r in report['listing']}
    entries=set(report['symbol_entries']);stubs=set(report['long_stubs']);counts=Counter()
    class BankedInstructions(dict):
        def __getitem__(self,pc):
            if c.port_7ffd&7==6:
                if pc==at:counts['entries']+=1
                if pc in banked:
                    if pc in entries:counts['symbols']+=1
                    if pc in stubs:counts['long']+=1
                    return banked[pc]
            return super().__getitem__(pc)
    h.instructions=BankedInstructions(fixed)
    h.inline_counts=counts
    return report


def delta(counts):
    return 10*counts['entries']-24*(counts['symbols']-counts['long'])+8*counts['long']
