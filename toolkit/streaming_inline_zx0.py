"""Inline-literal version of the input-page-suspending ZX0 prototype.

Keep the existing generator unchanged. Its assembler records source INC HL
sites; a checked relocation inserts page guards and the inline literal test.
Absolute and relative operands are re-resolved, never scanned as raw bytes.
The ordinary literal path has no CALL/RET. 7800 is only the CPU-test layout;
production installation must use the separately checked split placement.
"""
from build_zxv_trd import MiniAssembler
import incremental_zx0
from streaming_local_zx0 import CODE,INPUT,OUTPUT,STACK_BOTTOM,STACK_TOP


class SourceAssembler(MiniAssembler):
    def __init__(self,origin):
        super().__init__(origin);self.input_increments=[]

    def emit(self,*values):
        if values==(0x23,) and 'dzx0_turbo' in self.labels:
            self.input_increments.append(self.pc)
        super().emit(*values)


def assemble():
    old=SourceAssembler(CODE)
    incremental_zx0.emit_decoder(old,output_base=OUTPUT,input_base=INPUT,
        stack_top=STACK_TOP,wrap_output=True,token_boundaries=True,
        inline_matches=True,input_pointer_label='input_pointer',inline_literals=True)
    if len(old.input_increments)!=6:raise ValueError('upstream input sites changed')
    if any(old.code[pc-CODE-1] not in (0x7e,0x4e) for pc in old.input_increments):
        raise ValueError('input increment no longer follows a source read')
    fast=old.labels['slice_copy_fast']-CODE
    if old.code[fast:fast+3]!=bytes.fromhex('08 ed b0'):raise ValueError('literal copier changed')
    a=MiniAssembler(CODE);locations={}
    for index,byte in enumerate(old.code):
        locations[index]=len(a.code)
        if index==fast:
            # AF' already holds the ZX0 bit accumulator after the output
            # checkpoint. Retain it there until the original EX AF / LDIR.
            a.emit(0x7d,0x81,0x78,0xce,0,0xb7)
            a.abs16(0xc2,'literal_split')
        if CODE+index in old.input_increments:
            a.emit(0x2c);a.abs16(0xcc,'input_next_page')
        else:a.emit(byte)
    locations[len(old.code)]=len(a.code)
    a.labels.update({name:CODE+locations[pc-CODE] for name,pc in old.labels.items()})
    for pos,name in old.abs_fixups:
        if locations[pos+1]!=locations[pos]+1:raise ValueError('split absolute operand')
        a.abs_fixups.append((locations[pos],name))
    a.rel_fixups.extend((locations[pos],name) for pos,name in old.rel_fixups)
    a.labels['literal_done']=CODE+locations[fast+3]
    a.labels['core_finished']=a.labels.pop('slice_finished')
    a.label('slice_finished');a.emit(0x3e,1);a.abs16(0x32,'finished');a.abs16(0xc3,'core_finished')
    a.label('begin');a.emit(0xaf);a.abs16(0x32,'input_needed');a.abs16(0x32,'finished')
    a.abs16(0xc3,'slice_begin')
    a.label('resume');a.abs16(0x3a,'input_needed');a.emit(0xb7);a.abs16(0xca,'slice_until')
    a.emit(0xaf);a.abs16(0x32,'input_needed');a.abs16(0xcd,'slice_sync_target');a.abs16(0xc3,'slice_resume')

    a.label('input_next_page');a.emit(0xf5,0x24,0xf1)
    a.label('input_check');a.emit(0xf5)
    a.abs16(0x3a,'all_loaded');a.emit(0xb7);a.rel8(0x20,'input_ready')
    a.abs16(0x3a,'input_high');a.emit(0xbc);a.rel8(0x20,'input_ready')
    a.emit(0x3e,1);a.abs16(0x32,'input_needed');a.emit(0xf1)
    a.abs16(0xcd,'slice_yield');a.abs16(0xc3,'input_check')
    a.label('input_ready');a.emit(0xf1,0xc9)

    a.label('literal_split');a.emit(0x08)
    # The output checkpoint was passed. Copy the entire literal token, as
    # the old inline decoder did, but suspend at each unavailable input page.
    a.emit(0xf5,0x7d,0x81,0x4f,0x78,0xce,0,0x3d,0x47)
    a.abs16((0xed,0x43),'literal_tail');a.emit(0x01);a.word(256)
    a.emit(0x7d,0xb7);a.rel8(0x28,'literal_prefix');a.emit(0x06,0,0xed,0x44,0x4f)
    a.label('literal_prefix');a.emit(0xf1,0xed,0xb0)
    a.abs16(0xcd,'input_check');a.abs16((0xed,0x4b),'literal_tail')
    a.emit(0xf5,0x78,0xb1);a.rel8(0x28,'literal_finished')
    # Re-test the tail's input page without repeating the output checkpoint.
    a.emit(0xf1,0x08);a.abs16(0xc3,'slice_copy_fast')
    a.label('literal_finished');a.emit(0xf1);a.abs16(0xc3,'literal_done')
    a.label('fatal');a.emit(0x76)
    a.label('state');incremental_zx0.emit_variables(a)
    for name in ('block_length','block_end','input_pointer','literal_tail'):
        a.label(name);a.word(0)
    for name in ('block_stored','input_high','all_loaded','input_needed','finished'):
        a.label(name);a.emit(0)
    a.label('end')
    if a.pc>STACK_BOTTOM:raise ValueError('standalone inline prototype overlaps its stack')
    return a


def build():
    a=assemble();return a.resolve(),dict(a.labels)
