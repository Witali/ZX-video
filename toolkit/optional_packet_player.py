"""Separate optional packet consumer; retain the original required queue loop.

Duplicate the small consumer code in unused bank 7. Both entries share
queue state and copying bridges, with no dynamic routing or extra data
buffer. Dispatch between them occurs once per parser transfer, not once
per sector or demand iteration. Historical global-gate code is preserved
in resumable_packet_player.py for reproducibility.
"""
from pathlib import Path
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha, padded, sectors
from inplace_keepalive_player import Builder as PreviousBuilder
from pipelined_frame_z80 import helpers, READY
from bulk_frame_z80 import LENGTH
from zx0_codec import decompress
import resumable_packet_player as previous

CODE, LIMIT = previous.CODE, previous.LIMIT


def build(read8, instructions, q, z, sites):
    a = MiniAssembler(CODE); rows = []; e,n = helpers(a,rows,'resumable_packet')
    def load(label): n('LD A,('+str(label)+')',0x3a,label,13)
    def store(label): n('LD ('+str(label)+'),A',0x32,label,13)
    def jump(op,label): n('JP '+str(label),op,label,10)
    def call(label): n('CALL '+str(label),0xcd,label,17)
    def ret(): e('RET',[0xc9],10)
    a.label('required'); e('XOR A',[0xaf],4); store('optional_mode'); jump(0xc3,'dispatch')
    a.label('optional'); e('LD A,1',[0x3e,1],7); store('optional_mode')
    a.label('dispatch'); load('stage'); e('OR A',[0xb7],4); jump(0xca,'packet_start')
    e('CP 1',[0xfe,1],7); jump(0xca,'resume_length'); jump(0xc3,'resume_body')
    a.label('packet_start'); e('LD A,1',[0x3e,1],7); store('stage')
    n('LD DE,length',0x11,LENGTH,10); n('LD BC,2',0x01,2,10)
    call('take_dispatch'); jump(0xda,'paused'); jump(0xc3,sites['validate_length'])
    a.label('resume_length'); call('resume_dispatch'); jump(0xda,'paused'); jump(0xc3,sites['validate_length'])
    a.label('begin_body'); e('LD A,2',[0x3e,2],7); store('stage')
    n('LD DE,packet',0x11,sites['input'],10); n('LD BC,(length)',(0xed,0x4b),LENGTH,20)
    call('take_dispatch'); jump(0xda,'paused'); jump(0xc3,sites['body_done'])
    a.label('resume_body'); call('resume_dispatch'); jump(0xda,'paused'); jump(0xc3,sites['body_done'])
    a.label('complete'); n('LD (literal_length),HL',0x22,sites['literal_length'],16)
    a.label('packet_ready'); e('XOR A',[0xaf],4); store('stage'); store('optional_mode')
    e('LD A,1',[0x3e,1],7); ret()
    a.label('paused'); e('XOR A',[0xaf],4); ret()
    for name,required,optional in (('take_dispatch',q['take'],'optional_take'),
                                   ('resume_dispatch',q['take_next'],'gate')):
        a.label(name); load('optional_mode'); e('OR A',[0xb7],4); jump(0xca,required); jump(0xc3,optional)

    # Clone actual resident/in-place opcodes, including the three-slot
    # cursor helper, while retaining every absolute data/bridge operand.
    original = {r['address']:r for r in instructions if q['take'] <= r['address'] < q['fatal']}
    pcs = sorted(original)
    if not pcs or pcs[0] != q['take']: raise ValueError('missing consumer instruction listing')
    copied = []; a.label('optional_take')
    for pc,end in zip(pcs,pcs[1:]+[q['fatal']]):
        row = original[pc]; blob = bytes(read8(i) for i in range(pc,end))
        if pc == q['take_next']:
            a.label('gate'); load(READY); e('OR A',[0xb7],4); jump(0xc2,f'original_{pc}')
            e('SCF',[0x37],4); ret()
        a.label(f'original_{pc}')
        if blob[0] in (0xc3,0xca,0xc2,0xda,0xd2,0xcd):
            if len(blob) != 3: raise ValueError('invalid consumer branch length')
            target = int.from_bytes(blob[1:],'little')
            if q['take'] <= target < q['fatal']:
                destination = 'gate' if target == q['take_next'] else f'original_{target}'
                n(row['instruction'],blob[0],destination,row['tstates'])
            elif target == q['demand']:
                if blob[0] != 0xca: raise ValueError('unexpected demand branch')
                n('JP Z,available optional output',0xca,'partial',10)
            else: e(row['instruction'],blob,row['tstates'])
        else:
            if blob[0] in (0x18,0x20,0x28,0x30,0x38,0x10):
                raise ValueError('unhandled relative consumer branch')
            e(row['instruction'],blob,row['tstates'])
        copied.append(dict(original_address=pc,address=a.labels[f'original_{pc}'],
                           previous_hex=blob.hex(),tstates=row['tstates']))
    a.label('partial')
    n('LD HL,(slice_output)',0x2a,z['slice_output'],16); n('LD DE,C000',0x11,0xc000,10)
    e('OR A',[0xb7],4); e('SBC HL,DE',[0xed,0x52],15)
    n('LD DE,(position)',(0xed,0x5b),q['position'],20)
    e('OR A',[0xb7],4); e('SBC HL,DE',[0xed,0x52],15)
    e('LD A,H',[0x7c],4); e('OR L',[0xb5],4); jump(0xc2,f'original_{q["take_available"]}')
    call(q['step']); e('OR A',[0xb7],4); jump(0xca,q['fatal']); jump(0xc3,'gate')
    a.label('stage'); a.emit(0); a.label('optional_mode'); a.emit(0); a.label('end')
    if a.pc > LIMIT: raise ValueError('optional consumer exceeds bank 7')
    return a.resolve(),dict(a.labels),rows,copied


def install(read8, put, m):
    q = m['queue_labels']; original_listing = list(m['slot_queue_instruction_listing'])
    original_consumer = bytes(read8(i) for i in range(q['take'],q['fatal']))
    previous.install(read8,put,m)
    old = m['resumable_packet']; old_patches = old['patches']
    # Restore both global queue patches before cloning. Keep all original
    # mandatory instruction bytes and their timing rows exactly.
    restored = old_patches[3:5]
    for patch in restored: put(patch['address'],bytes.fromhex(patch['before_hex']))
    if bytes(read8(i) for i in range(q['take'],q['fatal'])) != original_consumer:
        raise ValueError('required consumer was not restored')
    code,labels,rows,copied = build(read8,original_listing,q,m['decoder_labels'],old['sites'])
    if any(read8(i) for i in range(old['labels']['end'],CODE+len(code))):
        raise ValueError('optional extension space occupied')
    put(CODE,code)
    patches = []
    for index,label in ((0,'required'),(1,'begin_body'),(2,'complete'),(5,'optional')):
        patch = old_patches[index]; at = patch['address']; op = 0xcd if index == 5 else 0xc3
        after = bytes([op])+labels[label].to_bytes(2,'little')+(b'\x00\x00' if index == 5 else b'')
        if bytes(read8(at+i) for i in range(len(after))) != bytes.fromhex(patch['code_hex']):
            raise ValueError('unexpected parser redirect')
        put(at,after); patches.append(dict(patch,code_hex=after.hex()))
    replaced = [(r['address'],r['address']+len(bytes.fromhex(r['code_hex']))) for r in patches]
    kept = [r for r in original_listing if not any(lo <= r['address'] < hi for lo,hi in replaced)]
    for patch in patches:
        at = patch['address']; size = len(bytes.fromhex(patch['code_hex']))
        rows.append(dict(address=at,instruction='CALL optional packet' if size == 5 else 'JP resumable parser',
                         tstates=17 if size == 5 else 10,phase='resumable_packet'))
        if size == 5:
            rows.extend(dict(address=at+i,instruction='NOP',tstates=4,phase='resumable_packet') for i in (3,4))
    m['slot_queue_instruction_listing'] = kept+rows
    m['resumable_packet'] = dict(old,labels=labels,listing=rows,patches=patches,
        regions=[dict(address=CODE,code_hex=code.hex())],helper_bytes=len(code),extra_stack_bytes=0,
        mandatory_gate_tstates=13,mandatory_gate_delta_tstates=0,
        optional_continue_gate_tstates=40,optional_continue_gate_delta_tstates=27,
        mandatory_demand_gate_extra_tstates=0,
        transfer_dispatch_tstates=dict(required=27,optional=37),
        original_required_consumer_sha256=sha(original_consumer),copied_instructions=copied,
        optional_consumer=True,dynamic_routing=False,shared_queue_state=True,
        previous_global_gate_helper_bytes=old['helper_bytes'])
    m['packet_labels'] = dict(m['packet_labels'],read_packet=labels['packet_start'],packet_ready=labels['packet_ready'])


class Builder(PreviousBuilder):
    def compress(self,data):
        # Host-only cache reuse. Every hit is keyed by uncompressed SHA and
        # round-tripped before use; encoded/runtime policy is unchanged.
        digest = sha(data)
        if digest not in self.memo:
            for directory in getattr(self,'read_cache',[]):
                path = Path(directory)/(digest+'.zx0')
                if not path.exists(): continue
                blob = path.read_bytes()
                if decompress(blob,limit=len(data)) != data: raise ValueError('invalid ZX0 cache hit')
                self.memo[digest] = blob; break
        return super().compress(data)

    def ram(self,start,end,next_sector,remaining):
        sections,m = super().ram(start,end,next_sector,remaining); banks = self.expected_banks
        def bank_at(at): return 5 if at < 0x8000 else 2 if at < 0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at,data):
            if (at&16383)+len(data) > 16384: raise ValueError('cross-bank optional consumer')
            banks[bank_at(at)][at&16383:(at&16383)+len(data)] = data
        install(read8,put,m); result = []
        for section in sections:
            at = section['address']&16383
            length = m['resumable_packet']['labels']['end']-section['address'] if section['bank'] == 7 else section['decoded_bytes']
            raw = bytes(banks[section['bank']][at:at+length])
            if sha(raw) == section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            if len(padded(coded)) > (6912 if section['buffer'] == 0x4000 else 4608):
                raise ValueError('optional bootstrap staging overflow')
            result.append(dict(section,data=padded(coded),decoded_bytes=length,
                               compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m
