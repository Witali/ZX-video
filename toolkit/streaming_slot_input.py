"""Start the existing direct producer after its header, finish one sector/step.

The original sequential sector/carry implementation is retained. A wrapper
reports a decodable prefix and publishes its loaded frontier to ZX0. After
the final read it calls the original finalizer (no second read) so the shared
sector is saved before the decoder may finish and release the slot.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers
import direct_slot_input_z80 as original


def build(z,disk,origin):
    code,p,rows=original.build(dict(z,end=0x7c23),disk)
    # The caller separately verifies every split decoder region; the old
    # contiguous decoder-end check cannot describe its bank-2 core.
    a=MiniAssembler(origin);a.labels.update(p);e,n=helpers(a,rows,'direct_slot_input')
    def load(name):n('LD A,('+str(name)+')',0x3a,name,13)
    def store(name):n('LD ('+str(name)+'),A',0x32,name,13)
    def jump(op,name):n('JP '+str(name),op,name,10)
    def call(name):n('CALL '+str(name),0xcd,name,17)
    a.label('prefix_step');call(p['step']);load(p['phase']);e('OR A',[0xb7],4);e('RET Z',[0xc8],[5,11])
    # If the just-completed sector was the last one, finalize the carry now.
    # write_high >= target_high proves the second step cannot read a sector.
    load(p['target_high']);e('LD B,A',[0x47],4);load(disk['write_high'])
    e('CP B',[0xb8],4);jump(0xda,'frontier_ready')
    load(p['phase']);e('CP 2',[0xfe,2],7);jump(0xca,'frontier_ready');call(p['step'])
    a.label('frontier_ready');load(disk['write_high']);store(z['input_high'])
    load(p['phase']);e('CP 2',[0xfe,2],7);e('LD A,0',[0x3e,0],7)
    jump(0xc2,'frontier_flag');e('INC A',[0x3c],4)
    a.label('frontier_flag');store(z['all_loaded']);e('LD A,1',[0x3e,1],7);e('RET',[0xc9],10)
    a.label('prefix_end')
    if a.pc>original.CODE:raise ValueError('prefix wrapper overlaps direct producer')
    p.update(legacy_step=p['step'],step=a.labels['prefix_step'],prefix_step=a.labels['prefix_step'],prefix_end=a.pc)
    return [(original.CODE,code),(origin,a.resolve())],p,rows
