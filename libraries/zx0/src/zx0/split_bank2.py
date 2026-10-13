"""Move the ZX0 hot core into retired fixed Huffman-patch RAM, opcodes unchanged.

The 35-byte resumable entry remains in bank 5. All 279 remaining bytes,
including mutable state, move to bank 2. The old IRQ-safe private stack is
retained. This requires inline sparse patches in bank 6; default mode stays
unchanged when that dependency is unavailable.
"""
from . import bank_local as local
from ._z80 import sha

ORIGIN,LIMIT=0x8df2,0x8f09


def build(*,origin=ORIGIN,limit=LIMIT):
    a=local.assemble(dynamic_input=True,inline_literals=True)
    old=a.resolve();start,end=a.labels['slice_begin'],a.labels['end']
    split=start-local.CODE
    if split!=35 or end-start!=limit-origin or not 0x8000<=origin<limit<0x9000:
        raise ValueError('ZX0 or retired region size changed')
    def moved(address):return address+origin-start if start<=address<=end else address
    blob=bytearray(old);absolute=[];relative=[]
    for pos,label in a.abs_fixups:
        before=a.labels[label];after=moved(before)
        if before!=after:
            blob[pos:pos+2]=after.to_bytes(2,'little')
            absolute.append(dict(operand=moved(local.CODE+pos),label=label,old=before,new=after))
    for pos,label in a.rel_fixups:
        after=moved(a.labels[label])-moved(local.CODE+pos+1)
        before=int.from_bytes(old[pos:pos+1],'little',signed=True)
        if after!=before:raise ValueError('relative branch crosses split')
        relative.append(dict(operand=moved(local.CODE+pos),target=moved(a.labels[label]),displacement=after))
    regions=[(local.CODE,bytes(blob[:split])),(origin,bytes(blob[split:]))]
    labels={key:moved(value) for key,value in a.labels.items()}
    return regions,labels,dict(enabled=True,old_origin=start,old_end=end,new_origin=origin,new_end=limit,
        prefix_bytes=split,core_and_state_bytes=len(blob)-split,code_bytes=len(blob),
        old_code_sha256=sha(old),code_sha256=sha(blob),absolute_operands=absolute,relative_branches=relative,
        regions=[dict(address=address,code_hex=data.hex(),bytes=len(data),sha256=sha(data)) for address,data in regions],
        instruction_tstate_delta=0,extra_stream_bytes=0,extra_ram_bytes=0,private_stack_unchanged=True)
