"""Reuse the guarded streaming ZX0 core with in-place C000 output.

These are decoder and sector-prefix components, not a complete player.
The existing streaming layout is retained, with one same-cost output operand
change. The prefix wrapper reads at most one sector and finalizes carry data
before reporting all input loaded. No complete compressed-block copy occurs.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers
from build_fap3_trd import sha
import inplace_slot_input_z80 as producer
import streaming_zx0_layout as streaming


def decoder():
    regions, labels, report = streaming.build(); sites=[]; result=[]
    for at, data in regions:
        changed=bytearray(data); start=0
        while (index:=data.find(b'\x11\x00\xe0',start))>=0:
            changed[index:index+3]=b'\x11\x00\xc0';sites.append(at+index);start=index+3
        result.append((at,bytes(changed)))
    if len(sites)!=1:raise ValueError('unexpected streaming output initialization')
    report['e000_relocated_sha256']=report.pop('relocated_sha256')
    return result, labels, dict(report, output_base=0xc000, maximum_decoded_bytes=15872,
        regions_sha256=sha(b''.join(at.to_bytes(2,'little')+len(data).to_bytes(2,'little')+data
            for at,data in sorted(result))),
        output_patch=dict(address=sites[0],previous_hex='1100e0',code_hex='1100c0',
            previous_tstates=10,tstates=10,delta_tstates=0),
        regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in result])


def input_prefix(z, d, *, elapsed_fields, origin,patch_guards=False):
    regions, p, rows = producer.build(z,d,elapsed_fields=elapsed_fields)
    a=MiniAssembler(origin);e,n=helpers(a,rows,'inplace_streaming_input')
    def load(label):n('LD A,('+str(label)+')',0x3a,label,13)
    def store(label):n('LD ('+str(label)+'),A',0x32,label,13)
    def jump(op,label):n('JP '+str(label),op,label,10)
    def call(label):n('CALL '+str(label),0xcd,label,17)
    a.label('prefix_step');call(p['step']);load(p['phase']);e('OR A',[0xb7],4);e('RET Z',[0xc8],[5,11])
    load(p['pages']);e('OR A',[0xb7],4);jump(0xc2,'frontier')
    load(p['phase']);e('CP 2',[0xfe,2],7);jump(0xca,'frontier')
    # No pages remain: this call can only save carry, never read again.
    call(p['step'])
    a.label('frontier');load(p['destination_high']);store(z['input_high'])
    if patch_guards:store(z['header_frontier']);store(z['literal_frontier'])
    load(p['phase']);e('CP 2',[0xfe,2],7);e('LD A,0',[0x3e,0],7);jump(0xc2,'flag')
    e('INC A',[0x3c],4)
    a.label('flag');store(z['all_loaded'])
    if patch_guards:
        e('OR A',[0xb7],4);e('LD A,PUSH AF',[0x3e,0xf5],7);jump(0xca,'set_guards')
        e('LD A,RET',[0x3e,0xc9],7);a.label('set_guards')
        store(z['guard_header']);store(z['guard_literals'])
        # OR's zero flag still describes all_loaded. Once complete, the
        # original jumps bypass the input guards with zero per-token cost.
        for key,active,complete,operands in (
                ('token',z['Token'],z['Token']+3,('token_high_target','token_low_target','token_end_target')),
                ('long8',z['guard_long8'],z['CopyMoreLiterals'],('long8_target',)),
                ('long16',z['guard_long16'],z['NextUseBC'],('long16_target',))):
            n('LD HL,guarded '+key,0x21,active,10);jump(0xca,'set_'+key)
            n('LD HL,complete '+key,0x21,complete,10);a.label('set_'+key)
            for operand in operands:n('LD ('+operand+'),HL',0x22,z[operand],16)
    e('LD A,1',[0x3e,1],7);e('RET',[0xc9],10)
    a.label('prefix_end')
    if a.pc>producer.CODE:raise ValueError('streaming prefix exceeds free decoder-helper tail')
    p=dict(p,legacy_step=p['step'],step=a.labels['prefix_step'],prefix_step=a.labels['prefix_step'],prefix_end=a.pc)
    return regions+[(origin,a.resolve())],p,rows
