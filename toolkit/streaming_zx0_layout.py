"""Relocate the inline streaming decoder into verified current-player gaps."""
from build_fap3_trd import sha
import streaming_inline_zx0 as core

ORIGIN,LIMIT=0x8df2,0x8f09
HELPERS,HELPERS_LIMIT=0x7c31,0x7d50


def build():
    a=core.assemble();original=a.resolve();z=a.labels
    hot1=z['slice_sync_target']-z['slice_begin']
    hot2=z['slice_finished']-z['dzx0_turbo']
    sync=z['dzx0_turbo']-z['slice_sync_target']
    spans=[(core.CODE,z['slice_begin'],0x7c00),
        (z['slice_begin'],z['slice_sync_target'],ORIGIN),
        (z['dzx0_turbo'],z['slice_finished'],ORIGIN+hot1),
        (z['state'],z['end'],ORIGIN+hot1+hot2),
        (z['slice_sync_target'],z['dzx0_turbo'],HELPERS),
        (z['slice_finished'],z['state'],HELPERS+sync)]
    hot_end=ORIGIN+hot1+hot2+z['end']-z['state']
    helper_end=HELPERS+sync+z['state']-z['slice_finished']
    if hot_end>LIMIT or helper_end>HELPERS_LIMIT or z['slice_begin']-core.CODE!=35:
        raise ValueError('streaming decoder does not fit player reservations')
    def moved(pc):
        if pc==z['end']:return hot_end
        return next(target+pc-lo for lo,hi,target in spans if lo<=pc<hi)
    blob=bytearray(original);absolute=[];relative=[]
    for pos,name in a.abs_fixups:
        old=z[name];new=moved(old);blob[pos:pos+2]=new.to_bytes(2,'little')
        absolute.append(dict(operand=moved(core.CODE+pos),label=name,old=old,new=new))
    for pos,name in a.rel_fixups:
        delta=moved(z[name])-moved(core.CODE+pos+1)
        if not -128<=delta<=127:raise ValueError(('streaming relative relocation',name,delta))
        blob[pos]=delta&255
        relative.append(dict(operand=moved(core.CODE+pos),target=moved(z[name]),displacement=delta))
    regions=[(target,bytes(blob[lo-core.CODE:hi-core.CODE])) for lo,hi,target in spans]
    labels={name:moved(pc) for name,pc in z.items()}
    # Queue's public decoder entry must force resumption of input waits.
    labels['core_until']=labels['slice_until'];labels['slice_until']=labels['resume']
    report=dict(enabled=True,core_origin=ORIGIN,core_end=hot_end,core_limit=LIMIT,
        helper_origin=HELPERS,helper_end=helper_end,helper_limit=HELPERS_LIMIT,
        prefix_bytes=35,code_bytes=len(blob),state_bytes=z['end']-z['state'],
        standalone_sha256=sha(original),relocated_sha256=sha(blob),instruction_tstate_delta=0,
        absolute_operands=absolute,relative_branches=relative,
        regions=[dict(address=at,bytes=len(data),code_hex=data.hex(),sha256=sha(data)) for at,data in regions])
    return regions,labels,report
