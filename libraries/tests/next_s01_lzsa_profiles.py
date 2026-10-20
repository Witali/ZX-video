"""Three bounded S01 Small candidates; no public decoder is modified.

The EOF layout temporarily holds ExtendedCode's return in dead BC. The
tagged layout shares nibble decoding with its length continuation, removing
one nested CALL/RET and two bytes of peak caller stack. Both retain the
per-block XOR/LD B/EX AF initialization and exact byte EOF.
"""
from functools import lru_cache
from pathlib import Path

from lzsa import compact


KINDS=('eof_stack','tagged','combined')
EXPECTED_CODE=dict(baseline=137,eof_stack=136,tagged=139,combined=138)
EXPECTED_STACK=dict(baseline=8,eof_stack=8,tagged=6,combined=6)


def once(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)


@lru_cache(None)
def transformed_source(kind):
    if kind not in KINDS:raise ValueError('unknown bounded S01 construction')
    source=Path(compact.__file__).read_text(encoding='utf-8')
    if kind in ('eof_stack','combined'):
        # Carry is already set. POP/PUSH preserve Z and restore the original
        # return on a word escape; the word reader overwrites B, and its
        # caller overwrites C. EOF discards only ExtendedCode's return.
        source=once(source,"jr(0x20,'WordLength');emit('POP BC',(0xc1,),10);ret()",
            "emit('POP BC',(0xc1,),10);ret(0xc8);emit('PUSH BC',(0xc5,),11)")
    if kind in ('tagged','combined'):
        # Case00x has B=FF. Case10x increments token80..BF before saving it
        # in C; common DEC restores80..BF exactly, including token80.
        # Length bases3/9 become2/8 and remain nonnegative. Their constants
        # compensate for DEC C. No extra tag state or initialization exists.
        source=once(source,"a.label('Case00x');emit('PUSH AF',(0xf5,),11);call(0xcd,'NibbleSkipC')",
            "a.label('Case00x');emit('PUSH AF',(0xf5,),11);emit('LD C,B',(0x48,),4);call(0xcd,'NibbleSkipC')")
        source=once(source,"a.label('Case10x');call(0xcd,'ReadNibble')",
            "a.label('Case10x');emit('INC A',(0x3c,),4);call(0xcd,'ReadNibble')")
        begin=source.index("    a.label('ExtendedCode');call(0xcd,'ReadNibble');")
        split=source.index("    a.label('ReadNibble');",begin)
        end=source.index('    if a.pc>core_limit:',split)
        extension=source[begin:split]
        extension=once(extension,"    a.label('ExtendedCode');call(0xcd,'ReadNibble');",'    ')
        extension=once(extension,"emit('SUB 241',(0xd6,241),7)","emit('SUB 240',(0xd6,240),7)")
        extension=once(extension,"emit('LD A,15',(0x3e,15),7)","emit('LD A,16',(0x3e,16),7)")
        reader=source[split:end]
        reader="    a.label('ExtendedCode')\n"+reader
        reader=once(reader,"ret(0xf8)","absolute(0xfa,'NibbleDone','JP M,NibbleDone',10)")
        assert reader.endswith('    ret()\n')
        reader=reader[:-len('    ret()\n')]+"    a.label('NibbleDone');emit('DEC C',(0x0d,),4);ret(0xf8)\n"
        source=source[:begin]+reader+extension+source[end:]
    return source


@lru_cache(None)
def builder(kind):
    namespace=dict(vars(compact))
    exec(compile(transformed_source(kind),'<next_s01_lzsa_'+kind+'>','exec'),namespace)
    return namespace['build']


def build(kind='baseline',*,core=0x8000):
    if kind!='baseline' and kind not in KINDS:raise ValueError('unknown S01 kind')
    regions,labels,metadata=(compact.build if kind=='baseline' else builder(kind))(core=core,core_limit=core+512)
    code=sum(len(blob) for _,blob in regions);stack=EXPECTED_STACK[kind]
    assert code==EXPECTED_CODE[kind],(kind,code)
    service=dict(code_tables_alignment_and_embedded_state_bytes=code,
        extra_variables=0,caller_stack_bytes=stack,scratch_bytes=0,internal_buffer_bytes=0)
    metadata=dict(metadata,test_only=kind!='baseline',variant='next-s01-lzsa-'+kind,
        service_memory=service,service_memory_bytes=code+stack,caller_stack_bytes=stack,
        decoder_stack_bytes=stack-2,embedded_mutable_bytes=2,
        embedded_state_counted_once_in_code=True,alignment_padding=0,
        external_initialization_tstates=0,per_block_setup_tstates=24,
        qualification_scope='private raw Small candidate; native evidence recorded separately')
    return regions,labels,metadata
