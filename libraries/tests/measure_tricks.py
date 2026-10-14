"""Native precondition/counterexample checks for the sequential Z80 trick audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
for package in ('zx0','lzsa'):
    sys.path.insert(0,str(ROOT/'libraries'/package/'src'))
from z80 import Z80Machine


def run(code,registers,*,memory=(),prepare=None,stop=None):
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    m.set_memory_block(0x200,bytes.fromhex(code));m.pc=0x200;m.sp=0xbff0
    for name,value in registers.items():setattr(m,name,value)
    for address,data in memory:m.set_memory_block(address,data)
    if prepare:prepare(m)
    if stop is None:stop=0x200+len(bytes.fromhex(code))
    m.set_breakpoint(stop);m.ticks_to_stop=100000
    while m.pc!=stop:assert not m.run()&m._TICKS_LIMIT_HIT
    return m,100000-m.ticks_to_stop


def transfers():
    checks=0;directions=[]
    moves={('bc','de'):'50 59',('bc','hl'):'60 69',('de','bc'):'42 4b',
           ('de','hl'):'62 6b',('hl','bc'):'44 4d',('hl','de'):'54 5d'}
    push={'bc':'c5','de':'d5','hl':'e5'};pop={'bc':'c1','de':'d1','hl':'e1'}
    increment={'bc':'03','de':'13','hl':'23'}
    for (source,destination),move in moves.items():
        free=next(pair for pair in push if pair not in (source,destination));variants={}
        for value in (0,1,0xff,0x100,0x1234,0xffff):
            for flags in range(256):
                registers=dict(hl=0x369a,bc=0x1357,de=0x2468,af=0x7300|flags)
                registers[source]=value;registers[destination]=value^0xffff
                for name,middle,placement in (
                        ('adjacent','','pop'),('independent_increment',increment[free],'pop'),
                        ('independent_call','cd 00 03','pop'),
                        ('source_modified_destination_dead',increment[source],'push')):
                    old_code=' '.join((push[source],middle,pop[destination]))
                    new_code=' '.join((move,middle) if placement=='push' else (middle,move))
                    memory=((0x300,bytes.fromhex(increment[free]+' c9')),)
                    old,ot=run(old_code,registers,memory=memory);new,nt=run(new_code,registers,memory=memory)
                    assert tuple(getattr(old,k) for k in ('hl','bc','de','af','sp'))==tuple(
                        getattr(new,k) for k in ('hl','bc','de','af','sp'))
                    assert old.__getattribute__(destination)==value and ot-nt==13;checks+=1
                    variants[name]=dict(placement=placement,before_tstates=ot,after_tstates=nt,delta=-13)
        directions.append(dict(source=source,destination=destination,stack_code=push[source]+' '+pop[destination],
            register_code=move,checks=6144,interleavings=variants))
    # Actual decoder save: BC remains a live count while HL becomes history.
    old,_=run('e5 21 ff ff 19 ed a0 e1',dict(hl=0x4000,bc=8,de=0x9000),
        memory=((0x8fff,b'Z'),))
    wrong,_=run('44 4d 21 ff ff 19 ed a0 60 69',dict(hl=0x4000,bc=8,de=0x9000),
        memory=((0x8fff,b'Z'),))
    assert old.hl==0x4000 and old.bc==7 and (wrong.hl,wrong.bc)!=(old.hl,old.bc)
    # Real bounded ZX0 copier: old BC is popped into HL after BC has become
    # the prefix count and HL was used as available-space scratch. Neither
    # endpoint can hold a two-LD transfer without losing a live value.
    registers=dict(bc=8,hl=0x4000,de=0x9000)
    original,_=run('c5 21 03 00 44 4d e1',registers)
    at_push,_=run('60 69 21 03 00 44 4d',registers)
    at_pop,_=run('21 03 00 44 4d 60 69',registers)
    assert original.hl==8 and original.bc==3 and at_push.hl==at_pop.hl==3
    return dict(item='02',baseline_revision='d0f04472',complete=True,decision='already present / no eligible pair transfer',
        primitive_checks=checks,transfer_tstates=dict(before=21,after=8,delta=-13),
        directions=directions,source_and_destination_live_counterexample=dict(
            correct_hl=original.hl,correct_bc=original.bc,at_push_hl=at_push.hl,at_pop_hl=at_pop.hl),
        save_counterexample=dict(input=0x4000,count=8,correct_hl=old.hl,correct_bc=old.bc,
            invalid_replacement_hl=wrong.hl,invalid_replacement_bc=wrong.bc),decoder_changes=0)


def bit_masks():
    checks=0;differences=0
    for low in range(256):
        for flags in (0,1,0x45,0xff):
            registers=dict(hl=0x4000|low,af=0x7300|flags)
            old,ot=run('7d e6 fe 6f',registers);new,nt=run('cb 85',registers)
            assert old.hl==new.hl==(0x4000|(low&254)) and (ot,nt)==(15,8)
            differences+=old.af!=new.af;checks+=1
    # RES cannot supply the cleared carry or updated parity of AND. LZSA2
    # explicitly consumes P/Z after AND 24 and Z after AND 7.
    old,_=run('7d e6 fe 6f',dict(hl=0x4001,af=0x7301))
    new,_=run('cb 85',dict(hl=0x4001,af=0x7301))
    assert old.f&1==0 and new.f&1==1 and old.a!=new.a
    return dict(item='03',baseline_revision='ec68b9d6',complete=True,
        decision='inapplicable: no equivalent single-bit mask with dead A/flags',
        primitive_checks=checks,af_differences=differences,
        mask_tstates=dict(before=15,after=8,delta=-7),
        live_af_counterexample=dict(before_af=old.af,after_af=new.af,equal_hl=old.hl),decoder_changes=0)


def pointer_increments():
    checks=crossings=flag_changes=0
    for high in (0x20,0x40,0xff):
        for low in range(256):
            for flags in (0,1,0xff):
                registers=dict(hl=high*256+low,af=0x7300|flags)
                old,ot=run('23',registers);new,nt=run('2c',registers)
                assert (ot,nt)==(6,4) and old.f==flags and new.f&1==flags&1
                crossings+=old.hl!=new.hl;flag_changes+=old.f!=new.f;checks+=1
                if low!=255:assert old.hl==new.hl
    guarded=[]
    for value in (0x40fe,0x40ff,0xffff):
        # Same INC L / CALL Z convention as ZX0's page-aware generator. This
        # minimal handler advances H and preserves the live carry/INC flags;
        # a real input-frontier check/refill has additional costs.
        m,t=run('2c cc 00 03',dict(hl=value,af=0x7301),memory=((0x300,bytes.fromhex('f5 24 f1 c9')),))
        assert m.hl==(value+1)&65535 and m.f&1
        assert t==(56 if value&255==255 else 14)
        guarded.append(dict(input=value,output=m.hl,tstates=t))
    return dict(item='04',baseline_revision='1f362d16',complete=True,
        decision='already present with page handling; reject unguarded decoder increments',
        primitive_checks=checks,pointer_mismatches=crossings,flag_changes=flag_changes,
        tstates=dict(inc_hl=6,inc_l=4,delta=-2),minimal_guarded=guarded,decoder_changes=0)


def jump_tables():
    from lzsa.resumable import build
    regions,z,_=build();checks=0;rows={}
    # A is already a table index in the 22-T primitive. A real token dispatch
    # additionally reads/masks A and must retain the live input pointer HL.
    for token in range(256):
        index=token&24;destination=0x7000+index
        m,t=run('6f 26 60 66 e9',dict(af=index<<8,hl=0x4000),
            memory=((0x6000+index,b'\x70'),),stop=destination)
        assert m.pc==destination and t==22 and m.hl!=0x4000
        new,nt=run('e5 7e e6 18 6f 26 60 66 e9',dict(hl=0x4000,af=0x73ff,bc=0x1234,de=0x9000),
            memory=((0x4000,bytes([token])),(0x6000+index,b'\x70'),(destination,b'\xe1')),
            stop=destination+1)
        m=Z80Machine()
        for at,blob in regions:m.set_memory_block(at,blob)
        m.memory[0x4000]=token;m.hl=0x4000;m.af=0x73ff;m.bc=0x1234;m.de=0x9000
        m.pc=z['Token'];stop=z['NoLiterals'] if index==0 else z['MoreLiterals'] if index==24 else z['Token']+6
        m.set_breakpoint(stop);m.ticks_to_stop=10000
        while m.pc!=stop:assert not m.run()&m._TICKS_LIMIT_HIT
        ot=10000-m.ticks_to_stop
        assert (m.hl,m.af,m.bc,m.de)==(new.hl,new.af,new.bc,new.de)
        assert nt==57 and ot=={0:31,8:24,16:24,24:36}[index]
        rows[index]=dict(index=index,baseline_tstates=ot,candidate_tstates=nt,delta_tstates=nt-ot)
        checks+=1
    return dict(item='05',baseline_revision='0d7caa52',complete=True,
        decision='rejected: saved-HL jump table slows every literal dispatch class',
        tokens_checked=checks,primitive_tstates=22,live_hl_dispatch=list(rows.values()),
        table_bytes=25,table_page_alignment=256,handler_low_bytes=[0,8,16,24],
        production_layout_allocated=False,decoder_changes=0)


def aligned_addresses():
    valid=[];invalid=[]
    for index in (0,1,0x3fff,0x7fff):
        old,ot=run('19',dict(hl=index,de=0x8000));new,nt=run('cb fc',dict(hl=index,de=0x8000))
        assert old.hl==new.hl==index+0x8000 and (ot,nt)==(11,8)
        valid.append(dict(index=index,address=new.hl))
    for offset,output in ((0xffff,0xc001),(0xfff0,0xc210),(0xffff,0xa001)):
        old,_=run('19',dict(hl=offset,de=output));new,_=run('cb fc',dict(hl=offset,de=output))
        assert old.hl!=new.hl
        invalid.append(dict(offset=offset,output=output,correct_address=old.hl,invalid_mask_address=new.hl))
    return dict(item='06',baseline_revision='ac346c70',complete=True,
        decision='optional aligned ZX0 bank table; reject history address masking',
        index_mapping=valid,history_counterexamples=invalid,primitive_tstates=dict(add=11,set=8,delta=-3),
        applied_lookup_tstates=dict(before=108,after=87,delta=-21),
        full_decoder_evidence='ring_table_native.json')


def stack_copies():
    def bulk(source,end):
        # Seven words: AF plus both BC/DE/HL banks. Store in reverse word
        # order so a nonoverlapping 14-byte copy preserves byte order.
        return ('31 '+source.to_bytes(2,'little').hex(' ')+' f1 c1 d1 e1 d9 c1 d1 e1 31 '
            +end.to_bytes(2,'little').hex(' ')+' e5 d5 c5 d9 e5 d5 c5 f5')
    raw=bytes(range(1,15));registers=dict(hl=0x4000,de=0x9000,bc=14,af=0x7301,alt_hl=0x1234)
    old,ot=run('ed b0',registers,memory=((0x4000,raw),))
    new,nt=run(bulk(0x4000,0x900e),registers,memory=((0x4000,raw),))
    assert bytes(old.memory[0x9000:0x900e])==bytes(new.memory[0x9000:0x900e])==raw
    assert (ot,nt)==(289,175) and old.sp!=new.sp and old.alt_hl!=new.alt_hl and old.a!=new.a
    overlap=[]
    for distance in (1,2):
        seed=b'ZQ'[:distance];source=0x9000-distance
        registers=dict(hl=source,de=0x9000,bc=14,af=0x7301,alt_hl=0x1234)
        old,_=run('ed b0',registers,memory=((source,seed),))
        new,_=run(bulk(source,0x900e),registers,memory=((source,seed),))
        correct=bytes(old.memory[0x9000:0x900e]);wrong=bytes(new.memory[0x9000:0x900e])
        assert correct!=wrong
        overlap.append(dict(distance=distance,correct=correct.hex(),invalid_prefetch=wrong.hex()))
    return dict(item='07',baseline_revision='94092f04',complete=True,
        decision='rejected for current live-register/private-stack/overlap ABI',
        primitive_bytes=14,primitive_tstates=dict(before=289,after=175,delta=-114),
        private_sp_restore_tstates=40,restore_is_excluded_from_primitive=True,
        live_register_changes=dict(sp=new.sp,alternate_hl=new.alt_hl,accumulator=new.a),
        overlap_counterexamples=overlap,decoder_changes=0)


def constant_code():
    from zx0 import Token,encode as zx_encode
    from lzsa import encode as lz_encode
    raw=bytes(range(128))
    # Fixed output known at code-generation time; PUSH emits words backwards.
    code='31 80 90 '+ ' '.join('21 '+raw[i:i+2].hex(' ')+' e5' for i in range(126,-1,-2))
    m,t=run(code,dict(hl=0x4000,de=0x9000,bc=len(raw),af=0x7301))
    assert bytes(m.memory[0x9000:0x9080])==raw and t==1354
    zx=zx_encode(raw,[Token(0,len(raw))]);lz=lz_encode(raw,[])
    return dict(item='08',baseline_revision='7d83ca1e',complete=True,
        decision='inapplicable to generic literals; compiled constants enlarge/change transport',
        fixed_data_bytes=len(raw),compiled_body_bytes=256,compiled_with_sp_entry_bytes=len(bytes.fromhex(code)),
        compiled_tstates=t,ldir_only_tstates=21*len(raw)-5,sp_save_restore_excluded_tstates=40,
        word_primitive_tstates=dict(load_immediate=10,push=11,total=21),
        formats=[dict(format=name,payload_bytes=len(blob),payload_sectors=(len(blob)+255)//256)
            for name,blob in (('zx0',zx),('lzsa2',lz))],
        compiled_sectors=(len(bytes.fromhex(code))+255)//256,exact_fixed_output=True,decoder_changes=0)


def carry_masks():
    masks=propagation=0
    for value in range(256):
        for carry in (0,1):
            m,t=run('9f',dict(af=(value<<8)|0x54|carry))
            assert m.a==(255 if carry else 0) and m.f&1==carry and t==4;masks+=1
            # A is dead here, just as in a frontier high-byte calculation.
            # The mask is correct, but direct carry propagation is cheaper.
            old,ot=run('7c ce 00',dict(hl=value<<8,af=0x7354|carry))
            new,nt=run('9f e6 01 84',dict(hl=value<<8,af=0x7354|carry))
            assert old.af==new.af and (ot,nt)==(11,15);propagation+=1
    m,_=run('9f',dict(af=0x7300))
    assert m.a==0
    return dict(item='09',baseline_revision='3e41889d',complete=True,
        decision='inapplicable: no carry-to-mask branch; existing ADC/rotate paths cheaper',
        mask_checks=masks,carry_propagation_checks=propagation,mask_tstates=4,
        high_byte_tstates=dict(direct_adc=11,via_mask=15,delta=4),
        live_accumulator_counterexample=dict(before=0x73,after=m.a),decoder_changes=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--item',required=True,choices=('02','03','04','05','06','07','08','09'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report={'02':transfers,'03':bit_masks,'04':pointer_increments,'05':jump_tables,
        '06':aligned_addresses,'07':stack_copies,'08':constant_code,'09':carry_masks}[args.item]()
    report.update(release=False,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='Native instruction/precondition checks; no new decoder or playback performance claim.',
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            ROOT/'libraries/zx0/src/zx0/banked.py',ROOT/'libraries/zx0/src/zx0/incremental.py',
            ROOT/'libraries/zx0/src/zx0/resumable.py',ROOT/'libraries/lzsa/src/lzsa/resumable.py')})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('item','complete','decision')}))


if __name__=='__main__':main()
