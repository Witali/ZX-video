"""Three bounded F00 raw candidates; private composition of measured emitters.

The E02 clone and E03 pair retain their independently reviewed algorithms.
Their combination applies E03's AST transform to E02's source, in an isolated
namespace. No installed module or global builder is patched.
"""
import ast
from functools import lru_cache
from types import FunctionType

from lzsa import hybrid,wide
from next_e02_profiles import builder as e02_builder, transformed_source
from next_e03_profiles import Transform,Emitter,emit_shared,build as e03_build

KINDS=('hot_clone','hot_pair','combined')
EXPECTED_SERVICE=dict(hot_clone=9529,hot_pair=9515,combined=9545)
EXPECTED_REAL_TSTATES=dict(hot_clone=14913435,hot_pair=14918596,combined=14905725)


@lru_cache(None)
def combined_builder():
    module=ast.parse(transformed_source('hot-clone'))
    function=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='build')
    transformed=Transform('hot_pair').visit(function)
    tree=ast.fix_missing_locations(ast.Module(body=[transformed],type_ignores=[]))
    namespace=dict(vars(wide),MiniAssembler=Emitter,emit_shared=emit_shared)
    exec(compile(tree,'<next_f00 combined Wide>','exec'),namespace)
    result=FunctionType(hybrid.build.__code__,dict(hybrid.build.__globals__,_wide_build=namespace['build']),
        hybrid.build.__name__,hybrid.build.__defaults__,hybrid.build.__closure__)
    result.__kwdefaults__=dict(hybrid.build.__kwdefaults__)
    return result


def build(kind,*,core=0x8000):
    if kind not in KINDS:
        raise ValueError('Only the three bounded F00 candidates are available')
    if kind=='hot_pair':
        regions,labels,metadata=e03_build('hot_pair',core=core)
    else:
        builder=e02_builder('hot-clone') if kind=='hot_clone' else combined_builder()
        regions,labels,metadata=builder('fast',core=core,cold_match_extension=True)
    # Parent E02 metadata contains historical nominal/reference values.
    # Private qualification reports only actual emitted storage and stack.
    metadata={key:value for key,value in metadata.items()
        if not key.startswith(('reference_','classic_reference_','nominal_','e02_'))}
    code=sum(len(blob) for _,blob in regions)
    service=dict(code_tables_alignment_and_embedded_state_bytes=code,
        extra_variables=0,caller_stack_bytes=6,scratch_bytes=0,internal_buffer_bytes=0)
    metadata.update(test_only=True,variant='next-f00-'+kind,experiment='F00',design=kind,
        code_bytes=code,service_memory=service,service_memory_bytes=code+6,
        total_storage_bytes=code+6,caller_stack_bytes=6,decoder_stack_bytes=4,
        embedded_mutable_bytes=2,embedded_state_counted_once_in_code=True,
        candidate_promoted=False,irq_qualified=False,inplace_qualified=False,
        qualification_scope='private raw candidate; complete proof recorded externally')
    assert len(set(metadata['patched_addresses']))==2
    return regions,labels,metadata
