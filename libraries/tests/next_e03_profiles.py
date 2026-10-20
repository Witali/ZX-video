"""Three finite E03 screens; private emitters never patch public modules.

Full-table state threading is rejected by an optimistic static inventory.
The hot pair and shared-SMC designs compile the current raw Hybrid emitter
in an isolated namespace. Public packages, assemblers and defaults are intact.
"""
import ast
import inspect
from textwrap import dedent

from lzsa import hybrid, wide
from lzsa._z80 import MiniAssembler


READER = bytes.fromhex('37 08 30 09 7e b7 08 7e 23 0f 0f 0f 0f f6 f0')


class Emitter(MiniAssembler):
    def __init__(self, origin):
        super().__init__(origin)
        self.low_fixups = []

    def low8(self, label):
        self.low_fixups.append((len(self.code),label))
        self.emit(0)

    def resolve(self, external_labels=None):
        result = bytearray(super().resolve(external_labels))
        for offset,label in self.low_fixups:
            result[offset] = self.labels[label]&255
        return bytes(result)


def emit_shared(a):
    """CALL-site costs68/104T; one extra mutable low-byte, no extra RAM.

    Full/empty entry addresses differ by9, so at most9 padding bytes make
    their high bytes equal. The low operand is reset on every complete call.
    AF' carries only the cache byte here; flags no longer encode its phase.
    """
    a.label('e03_padding_begin')
    padding = 0
    while (a.pc+3)>>8 != (a.pc+12)>>8:
        a.emit(0)
        padding += 1
    a.label('e03_reader')
    a.abs16(0xc3,'e03_empty')
    a.labels['e03_state_operand'] = a.labels['e03_reader']+1
    a.label('e03_full')
    a.emit(0x3e);a.low8('e03_empty');a.abs16(0x32,'e03_state_operand')
    a.emit(8,0xf6,0xf0,0xc9)
    a.label('e03_empty')
    a.emit(0x3e);a.low8('e03_full');a.abs16(0x32,'e03_state_operand')
    a.emit(0x7e,8,0x7e,0x23,0x0f,0x0f,0x0f,0x0f,0xf6,0xf0,0xc9)
    a.label('e03_reader_end')
    assert a.labels['e03_reader_end']-a.labels['e03_reader']==28
    assert a.labels['e03_full']>>8 == a.labels['e03_empty']>>8
    return padding


HOT_BODY = '''
def token_body(token):
    if token != 167 or a.labels.get('body_167_0') != a.pc:
        return e03_original_token_body(token)
    a.label('e03_hot_first')
    emit(0x37,8);jr(0x30,'e03_hot_cached')
    emit(0x7e,0xb7,8,0x7e,0x23,0x0f,0x0f,0x0f,0x0f,0xf6,0xf0)
    emit(0x3d,0x87,0x47,0x4e,0x23)
    a.abs16((0xed,0x43),'offset');emit(0x06,0);jp(0xc3,'LongerMatch')
    a.label('e03_hot_cached')
    emit(0xf6,0xf0,0x3d,0x87,0x47,0x4e,0x23)
    a.abs16((0xed,0x43),'offset');emit(0x06,0)
    jp(0xc3,'e03_known_empty_LongMatchNibble')
'''


class Transform(ast.NodeTransformer):
    def __init__(self, design):
        self.design = design

    def visit_FunctionDef(self, node):
        if node.name == 'nibble':
            if self.design == 'shared_smc':
                return ast.parse(dedent('''
                    def nibble(label):
                        jp(0xcd,'e03_reader');a.label(label)
                ''')).body[0]
            # A direct entry after SCF/EX/JR is valid only for a proved empty
            # cache, retaining the original OR A/AF' carry protocol.
            for index,statement in enumerate(node.body):
                if (isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call)
                        and isinstance(statement.value.func,ast.Name) and statement.value.func.id=='emit'
                        and [getattr(arg,'value',None) for arg in statement.value.args]==[0x7e,0xb7,8,0x7e]):
                    node.body.insert(index,ast.parse("a.label('e03_known_empty_'+label)").body[0])
                    break
            else:
                raise AssertionError('reader source drift')
            return node
        if node.name == 'token_body' and self.design == 'hot_pair':
            node.name = 'e03_original_token_body'
            return [node,*ast.parse(dedent(HOT_BODY)).body]
        if node.name != 'build':
            return node
        node = self.generic_visit(node)
        if self.design == 'shared_smc':
            output = []
            for statement in node.body:
                if (isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call)
                        and isinstance(statement.value.func,ast.Name) and statement.value.func.id=='emit'
                        and [getattr(arg,'value',None) for arg in statement.value.args]==[0xd9,0xe5,0xd9,0x06,0,0x37,8]):
                    output.extend(ast.parse(dedent('''
                        emit(0xd9,0xe5,0xd9,0x06,0)
                        emit(0x3e);a.low8('e03_empty');jp(0x32,'e03_state_operand')
                    ''')).body)
                else:
                    if (isinstance(statement,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='handlers'
                                                              for target in statement.targets)):
                        output.append(ast.parse('_e03_padding=emit_shared(a)').body[0])
                    output.append(statement)
            node.body = output
        return node


def baseline(*, profile='fast', core=0x8000):
    return hybrid.build(profile=profile,core=core,cold_match_extension=True)


def inventory(profile):
    if isinstance(profile,str):
        profile = baseline(profile=profile)
    origin,blob = profile[0][0]
    labels = profile[1]
    sites = []
    cursor = labels['start']-origin
    while (cursor:=blob.find(READER,cursor)) >= 0:
        sites.append(origin+cursor)
        cursor += len(READER)
    return dict(reader_bytes=15,reader_sites=sites,count=len(sites),
        current_reader_bytes=15*len(sites),extra_full_word_table_bytes=512,
        maximum_reader_pair_saving_bytes=2*len(sites),startup_saving_bytes=2,
        optimistic_zero_extra_dispatch_service_delta=512-2*len(sites)-2,
        specified_second_lookup_bytes=11,
        specified_service_lower_bound_delta=512+11-2*len(sites)-2)


def build(design, *, core=0x8000, profile='fast'):
    if design not in ('hot_pair','shared_smc') or profile!='fast':
        raise ValueError('Only the two bounded fast-profile E03 emitters are implemented')
    tree = Transform(design).visit(ast.parse(inspect.getsource(wide.build)))
    ast.fix_missing_locations(tree)
    namespace = dict(vars(wide),MiniAssembler=Emitter,emit_shared=emit_shared)
    exec(compile(tree,'<private E03 '+design+'>','exec'),namespace)
    hybrid_namespace = dict(vars(hybrid),_wide_build=namespace['build'])
    exec(compile(ast.parse(inspect.getsource(hybrid.build)),'<private E03 Hybrid>','exec'),hybrid_namespace)
    regions,labels,metadata = hybrid_namespace['build'](profile=profile,core=core,cold_match_extension=True)
    metadata = {key:value for key,value in metadata.items()
                if not key.startswith(('reference_','classic_reference_','nominal_'))}
    code = sum(len(blob) for _,blob in regions)
    stack = 8 if design=='shared_smc' else 6
    patches = list(metadata['patched_addresses'])
    if design=='shared_smc':
        patches.append(labels['e03_state_operand'])
    service = dict(code_tables_alignment_and_embedded_state_bytes=code,
        extra_variables=0,caller_stack_bytes=stack,scratch_bytes=0,internal_buffer_bytes=0)
    metadata.update(test_only=True,experiment='E03',design=design,variant='next-e03-'+design,
        code_bytes=code,service_memory=service,service_memory_bytes=sum(service.values()),
        total_storage_bytes=sum(service.values()),caller_stack_bytes=stack,
        decoder_stack_bytes=stack-2,patched_addresses=patches,
        embedded_mutable_bytes=len(patches),embedded_state_counted_once_in_code=True,
        candidate_promoted=False,irq_qualified=False,inplace_qualified=False)
    return regions,labels,metadata


def micro(kind, *, core=0x8000):
    """Component tests of the three designs; no additional optimization option."""
    a = Emitter(core);a.label('entry')
    if kind=='baseline':
        a.emit(*READER,0xc9)
    elif kind=='known_empty':
        a.emit(*READER[4:],0xc9)
    elif kind=='shared_smc':
        a.abs16(0xcd,'e03_reader');a.emit(0xc9);emit_shared(a)
    else:
        raise ValueError(kind)
    return [(core,a.resolve())],a.labels,dict(entry='entry',
        patched_addresses=[a.labels['e03_state_operand']] if kind=='shared_smc' else [])
