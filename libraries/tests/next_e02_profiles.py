"""Three test-only LL3 continuation constructions; public sources stay intact.

Narrow, count-checked source substitutions keep the qualified Wide emitter's
token/copy/offset machinery. The generated source identity is saved by the
screening report. No transformed builder is imported by either library.
"""
from functools import lru_cache
from pathlib import Path
import sys
from types import FunctionType

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'libraries/lzsa/src'),str(ROOT)]
from lzsa import hybrid,wide

KINDS=('direct-hl','hot-clone','shared-tail')


def replace_once(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)


@lru_cache(None)
def transformed_source(kind):
    if kind not in KINDS:raise ValueError('unknown bounded E02 construction')
    source=Path(wide.__file__).read_text(encoding='utf-8')
    if kind=='direct-hl':
        # Dispatch lends HL' to the handler entry. Each LL3 prefix occupies
        # EXX;JP helper (four bytes), followed by an EXX continuation. All
        # original INC HLs preserve flags and safely cross a page boundary.
        source=replace_once(source,"jp(0xcd, 'LongLiterals')","jp(0xc3, 'LongLiterals');emit(0xd9)")
        begin=source.index("    a.label('LongLiterals')")
        end=source.index('    handlers = ',begin)
        helper=source[begin:end]
        assert helper.count('emit(0xc9)')==3
        helper=helper.replace('emit(0xc9)','emit(0xd9,0x23,0x23,0x23,0x23,0xe9)')
        source=source[:begin]+helper+source[end:]
    elif kind=='hot-clone':
        # Token248 is the one LL3 entry leading to hottest body_224_1.
        # Its nibble form falls directly into the existing body; byte/word
        # escapes call the untouched ManyLiterals helper and rejoin locally.
        source=replace_once(source,'def literal_prefix(literal, cls):','def literal_prefix(literal, cls, token=None):')
        source=replace_once(source,'literal_prefix(literal,cls)','literal_prefix(literal,cls,value)')
        source=replace_once(source,'literal_prefix(literal, cls)','literal_prefix(literal, cls, value)')
        source=replace_once(source,'literal_prefix((token>>3)&3, token>>5);token_body(token)',
            'literal_prefix((token>>3)&3, token>>5, token);token_body(token)')
        source=replace_once(source,"            jp(0xcd, 'LongLiterals')",'''            if token==248:
                a.label('E02CloneStart')
                nibble('E02CloneNibble')
                emit(0x3c);jr(0x28,'E02CloneCold');emit(0xd6,238,0x4f)
                ldi();ldi();ldir()
                a.label('E02CloneContinue')
            else:jp(0xcd, 'LongLiterals')''')
        source=replace_once(source,'                    emitted.append(dict(literals=list(members)',
            '''                    if token==224 and 3 in members:
                        a.label('E02CloneCold')
                        jp(0xcd,'ManyLiterals');jp(0xc3,'E02CloneContinue')
                    emitted.append(dict(literals=list(members)''')
    else:
        # Keep the hot nibble copy's fall-through LDIR/RET. Byte and word
        # paths each replace their three-byte LDIR/RET by a two-byte JR.
        source=replace_once(source,'    ldi();ldi();ldir();emit(0xc9)',
            "    ldi();ldi();a.label('E02SharedLiteralTail');ldir();emit(0xc9)")
        source=replace_once(source,"    a.label('long8_complete');ldir();emit(0xc9)",
            "    a.label('long8_complete');jr(0x18,'E02SharedLiteralTail')")
        source=replace_once(source,"    a.label('long16_complete');ldir();emit(0xc9)",
            "    a.label('long16_complete');jr(0x18,'E02SharedLiteralTail')")
    return source


@lru_cache(None)
def builder(kind):
    namespace={'__name__':'lzsa._next_e02_'+kind.replace('-','_'),'__package__':'lzsa'}
    exec(compile(transformed_source(kind),'<next_e02_'+kind+'>','exec'),namespace)
    # Copy the Hybrid builder's globals rather than mutating its module.
    fn=FunctionType(hybrid.build.__code__,dict(hybrid.build.__globals__,_wide_build=namespace['build']),
        hybrid.build.__name__,hybrid.build.__defaults__,hybrid.build.__closure__)
    fn.__kwdefaults__=dict(hybrid.build.__kwdefaults__)
    return fn


def build(kind,*,core=0x8000):
    regions,labels,metadata=builder(kind)('fast',core=core,cold_match_extension=True)
    metadata=dict(metadata,test_only=True,e02_construction=kind,
        variant='next-e02-'+kind,
        e02_baseline_nominal_aligned_service_bytes=metadata['nominal_aligned_service_bytes'],
        nominal_aligned_service_bytes=metadata['service_memory_bytes']-metadata['alignment_padding'])
    return regions,labels,metadata


def extra_word_cases():
    """Force the cloned token248's legal one/two-byte word literals in both phases."""
    for phase in ('cached','refill'):
        for n in (1,2):
            # One A literal and distance-one match initialize retained offset.
            # The byte-offset seed leaves the reservoir empty; the nibble
            # seed leaves a cached F consumed by the following LL3 word form.
            prefix=bytes.fromhex('0841fff8ef' if phase=='cached' else '4841fff8ffef')
            suffix=bytes.fromhex('e7f0e8' if phase=='cached' else 'e7e8')
            yield f'clone-word-{n}-{phase}',prefix+n.to_bytes(2,'little')+b'A'*n+suffix,b'A'*(n+5),phase
