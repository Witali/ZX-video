"""Bounded native CPU proof of the opt-in448-T Pentagon pacing mechanism.

This intentionally keeps the table weights/payload identical in before/after
controls. It is not a quality result or a proof of physical ULA/floppy timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from build_stream_trd import build
from direct_player import HOLDS, build_disk, canonical_pcm_model
from ram_machine import MemoryMachine
from verify_stream_trd import cold_load, native_check

HERE=Path(__file__).resolve().parent
REPO=HERE.parent
PROFILES=('128','scorpion','pentagon512','pentagon1024')
EXPORT=None
PROOF={}


def model(pace=None,*,ui=False):
    holds=HOLDS.copy();holds[7]+=26
    result=dict(holds=holds,beta=.5,extent=.5,pcm_origin=0)
    if pace is not None:result['pentagon_ordinary_tstates']=pace
    if ui:result['audio_progress_ui']=True
    return result


def clone(cold,labels):
    result=MemoryMachine(cold.kind,b'',labels)
    result.banks=[bytearray(bank) for bank in cold.banks]
    result.rom[:]=cold.rom
    result.low=24;result.high=result.eff=0;result.selected=0
    return result


def run_to(machine,pc,target,*,budget=100000):
    m=machine.m;m.pc=pc;m.set_breakpoint(target);m.ticks_to_stop=budget
    # The entry itself can equal the eventual next packet's dispatch address.
    if pc==target:
        m.clear_breakpoint(target);m.ticks_to_stop=1;m.run()
        spent=1-m.ticks_to_stop;m.ticks_to_stop=budget-spent;m.set_breakpoint(target)
    while m.pc!=target:
        event=m.run()
        if event&m._TICKS_LIMIT_HIT:
            raise AssertionError(('timeout',hex(m.pc),hex(target)))
    return budget-m.ticks_to_stop


def register_snapshot(m):
    return {name:getattr(m,name) for name in ('af','bc','de','hl','ix','iy','sp',
        'alt_af','alt_bc','alt_de','alt_hl')}


def prior_builder(folder):
    folder.mkdir()
    names=('build_stream_trd.py','direct_player.py','stream-player.asm',
           'stream-worker.asm','stream-progress.asm','ram-cache.asm',
           'stream-audio-ui.asm','stream-audio-ui-helper.asm','stream-playback-progress.asm')
    for name in names:
        data=subprocess.run(['git','show','5d10036c:audiobook-beeper/'+name],cwd=REPO,
                            capture_output=True,check=True).stdout
        (folder/name).write_bytes(data)
    namespaces=[]
    for name in ('direct_player.py','build_stream_trd.py'):
        namespace=dict(__file__=str(folder/name),__name__='_prior_pacing_'+name[:-3])
        exec(compile((folder/name).read_bytes(),str(folder/name),'exec'),namespace)
        namespaces.append(namespace)
    for name in ('layout','canonical_pcm_model','pcm_high_lookup','pcm_quantization_metadata',
                 'neutral_packet_metadata','idle_cycle_packet_metadata','idle_pair_packet_metadata',
                 'endpoint_idle_pair_metadata'):
        namespaces[1][name]=namespaces[0][name]
    return namespaces[1]['build']


class Pacing448Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch=REPO/'.tmp/pacing448-tests';scratch.mkdir(parents=True,exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(dir=scratch);cls.root=Path(cls.temporary.name)
        cls.packed=bytes([0x91])*256+bytes(256)
        cls.cover=bytes(6912)
        cls.disks={};cls.metas={};cls.cold={}
        for pace in (449,448):
            disk,meta=build(cls.packed,cls.root/str(pace),cls.cover,model(pace))
            cls.disks[pace]=disk;cls.metas[pace]=meta
            for profile in PROFILES:cls.cold[pace,profile]=cold_load(disk,meta,profile)[0]

    @classmethod
    def tearDownClass(cls):
        if EXPORT:
            for pace in (449,448):
                shutil.copytree(cls.root/str(pace),EXPORT/str(pace),dirs_exist_ok=True)
                (EXPORT/str(pace)/'audio.trd').write_bytes(cls.disks[pace])
            for name in ('prior-producer','native','maximum'):
                if (cls.root/name).exists():shutil.copytree(cls.root/name,EXPORT/name,dirs_exist_ok=True)
        cls.temporary.cleanup()

    def test_default_absent_explicit449_and_archived_disk_metadata_identity(self):
        prior=prior_builder(self.root/'prior-producer');reports=[]
        for ui in (False,True):
            config=model(ui=ui)
            original,old_meta=prior(self.packed,self.root/f'prior-{ui}',self.cover,config)
            for pace in (None,449):
                disk,meta=build(self.packed,self.root/f'default-{ui}-{pace}',self.cover,model(pace,ui=ui))
                self.assertEqual(disk,original);self.assertEqual(meta,old_meta)
                self.assertNotIn('pentagon_pacing',meta)
                self.assertNotIn('pentagon_ordinary_tstates',meta['model'])
                self.assertNotIn('pentagon_ordinary_tstates',meta['player_labels'])
            reports.append(dict(ui=ui,trd_sha256=hashlib.sha256(original).hexdigest(),
                exact_disk=True,exact_metadata=True,absent_and_explicit449=True))
        PROOF['defaults']=dict(prior_commit='5d10036c',cases=reports)

    def test_setting_types_legacy_rejection_and_fixed_six_byte_stub(self):
        invalid=(None,False,True,0,447,450,448.,'448',[448])
        for pace in invalid:
            config=model();config['pentagon_ordinary_tstates']=pace
            with self.subTest(pace=pace):
                with self.assertRaises(ValueError):canonical_pcm_model(config)
                with self.assertRaises(ValueError):build(self.packed,self.root/'invalid',self.cover,config)
        self.assertFalse((self.root/'invalid').exists())
        with self.assertRaises(ValueError):build_disk(self.packed,self.root/'legacy',model(448))
        self.assertFalse((self.root/'legacy').exists())
        old=(self.root/'449/player.bin').read_bytes();new=(self.root/'448/player.bin').read_bytes()
        labels=self.metas[448]['player_labels'];at=labels['hardware_delay']-0x8000
        self.assertEqual(old[at:at+6],bytes.fromhex('00000000FDE9'))
        self.assertEqual(new[at:at+6],bytes.fromhex('ED5F23FDE900'))
        self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a!=b],list(range(at,at+6)))
        self.assertEqual(self.metas[449]['first_addresses'],self.metas[448]['first_addresses'])
        self.assertEqual(self.metas[449]['second_addresses'],self.metas[448]['second_addresses'])
        self.assertEqual(self.metas[449]['memory'],self.metas[448]['memory'])
        PROOF['mechanism']=dict(old_stub_hex=old[at:at+6].hex(),new_stub_hex=new[at:at+6].hex(),
            only_changed_player_offsets=list(range(at,at+6)),lookup_and_worker_addresses_preserved=True,
            old_stub_tstates=16,new_stub_tstates=15,old_ordinary_tstates=449,new_ordinary_tstates=448,
            default_128_scorpion_tstates=423,clone_patch_jp_tstates=10,final_jp_iy_tstates=8,
            table_hold_sum=449,table_weights_held_fixed=True,malformed_options_rejected=True,
            legacy_builder_rejected_before_creation=True)

    def packet(self,pace,profile,first,second,phase,rvalue,iff2):
        meta=self.metas[pace];labels=meta['player_labels']
        machine=clone(self.cold[pace,profile],labels);m=machine.m
        registers=dict(af=0x0000,bc=0x00FE,de=0x1000+meta['feedback_states'].index(16)*6,
            hl=0xFFFF,ix=0x9000,iy=second,sp=0x7777,alt_af=phase,
            alt_bc=0x3456,alt_de=0xC000,alt_hl=meta['decoder_rows'][0])
        for name,value in registers.items():setattr(m,name,value)
        m.r=rvalue;m.iff1=False;m.iff2=iff2
        page=meta['packet_pages'][0x90//4]
        # Replace only the next dispatch pointer with the native harness stop.
        # This avoids an entry breakpoint when FIRST selects its own literal;
        # lookup SP, SECOND POP HL and every emitted instruction remain real.
        pointer=page+registers['de']%256;target=0x40
        machine.write(pointer,0x40);machine.write(pointer+1,0)
        banks_before=[bytes(bank) for bank in machine.banks]
        events=[];budget=100000
        def output(port,value):
            events.append((port,value,budget-m.ticks_to_stop))
            machine.output(port,value)
        m.set_output_callback(output)
        elapsed=run_to(machine,first,target,budget=budget)
        self.assertEqual([bytes(bank) for bank in machine.banks],banks_before)
        return dict(elapsed=elapsed,events=events,registers=register_snapshot(m),
                    iff1=m.iff1,iff2=m.iff2)

    def test_every_first_second_pattern_both_nibble_branches_register_liveness(self):
        meta=self.metas[449];coverage={}
        firsts=meta['first_addresses'];seconds=meta['second_addresses']
        # Cover every literal FIRST and SECOND body with both phase branches.
        pairs=[(first,seconds[i%len(seconds)]) for i,first in enumerate(firsts)]
        pairs.extend((firsts[i%len(firsts)],second) for i,second in enumerate(seconds))
        for profile in PROFILES:
            runs=0
            for i,(first,second) in enumerate(pairs):
                for phase in (0,1):
                    rvalue=(0,127,128,255)[i%4];iff2=bool((i//4)%2)
                    before=self.packet(449,profile,first,second,phase,rvalue,iff2)
                    after=self.packet(448,profile,first,second,phase,rvalue,iff2)
                    self.assertEqual(after['registers'],before['registers'],(profile,i,phase))
                    self.assertEqual(after['iff1'],before['iff1']);self.assertEqual(after['iff2'],before['iff2'])
                    self.assertEqual([e[:2] for e in after['events']],[e[:2] for e in before['events']])
                    delta=-1 if profile.startswith('pentagon') else 0
                    expected=[(p,v,t+(delta if j>=8 else 0)) for j,(p,v,t) in enumerate(before['events'])]
                    self.assertEqual(after['events'],expected,(profile,i,phase))
                    self.assertEqual(after['elapsed'],before['elapsed']+delta)
                    self.assertEqual(before['elapsed'],449 if profile.startswith('pentagon') else 423)
                    runs+=2
            coverage[profile]=dict(before_after_executions=runs,every_first=len(firsts),every_second=len(seconds),
                both_nibble_phase_branches=True,seed_R=[0,127,128,255],both_IFF2=True,
                complete_AF_AFprime_IX_IY_SP_registers_exact=True,
                changed_interval_slot=7 if profile.startswith('pentagon') else None,
                source_pulses_unchanged=True,ordinary_tstate_delta=-1 if profile.startswith('pentagon') else 0)
        PROOF['literal_paths']=coverage

    def test_page_and_bank_both_last_bits_ui_and_legacy_exact_guards(self):
        packed=bytes(1024*256);reports=[]
        for ui in (False,True):
            controls={}
            for pace in (449,448):
                disk,meta=build(packed,self.root/f'tail-{ui}-{pace}',self.cover,model(pace,ui=ui))
                for profile in PROFILES:controls[pace,profile]=(cold_load(disk,meta,profile)[0],meta)
            for profile in PROFILES:
                for bit in (0,1):
                    for bank_tail in (False,True):
                        result=[]
                        for pace in (449,448):
                            cold,meta=controls[pace,profile];labels=meta['player_labels']
                            machine=clone(cold,labels);m=machine.m
                            literal=next(i for i in range(256) if i%2==bit and labels[f'second_address_{i}']>=0)
                            second=labels[f'second_address_{literal}']
                            sequence=bytes(machine.read(second+i) for i in range(64))
                            offset=sequence.rfind(bytes.fromhex('D91CCA'));self.assertGreaterEqual(offset,0)
                            for name,value in dict(af=0x3030,bc=0x00FE,de=0x1030,hl=0x0040,
                                ix=0x9ABC,iy=0xDEF0,alt_af=0x0081,alt_bc=0x1234,
                                alt_de=0xFFFF if bank_tail else 0xC0FF,
                                alt_hl=meta['decoder_rows'][9],sp=0x7777).items():setattr(m,name,value)
                            before=[bytes(bank) for bank in machine.banks];events=[];budget=100000
                            def output(port,value):
                                events.append((port,value,budget-m.ticks_to_stop));machine.output(port,value)
                            m.set_output_callback(output)
                            elapsed=run_to(machine,second+offset,0x40,budget=budget)
                            pulses=[event for event in events if event[0]&255==254]
                            self.assertEqual(len(pulses),1);self.assertEqual(pulses[0][1],bit*16)
                            self.assertEqual(m.ix,0x9ABC);self.assertEqual(m.iy,0xDEF0)
                            self.assertEqual(m.alt_hl,meta['decoder_rows'][9]);self.assertEqual(m.alt_af&1,1)
                            # Bank tails may update only their documented descriptor/UI cursors.
                            allowed=set()
                            if bank_tail:
                                for label,size in (('stream_tail_hl',2),('stream_next_record',2),('stream_paging',1)):
                                    allowed.update(range(labels[label]-0x8000,labels[label]-0x8000+size))
                                if ui:allowed.update(range(labels['stream_play_next_record']-0x8000,labels['stream_play_next_record']-0x8000+2))
                            for page,bank in enumerate(machine.banks):
                                changed={i for i,(a,b) in enumerate(zip(before[page],bank)) if a!=b}
                                legal=(allowed if page==2 else {0x1AC0,0x1AC1} if page==7 and bank_tail and ui and profile.startswith('pentagon') else set())
                                self.assertTrue(changed<=legal,(profile,bit,bank_tail,ui,page,changed))
                            result.append(dict(elapsed=elapsed,events=events,registers=register_snapshot(m)))
                        self.assertEqual(result[0],result[1])
                        self.assertEqual(result[0]['elapsed'],(305 if profile=='scorpion' else 281) if bank_tail else 52)
                        reports.append(dict(profile=profile,last_bit=bit,ui=ui,bank_tail=bank_tail,
                            elapsed=result[0]['elapsed'],before_after_delta=0,all_registers_and_memory_guards=True))
        PROOF['directed_tails']=dict(cases=reports,both_literal_bits=True,ui_and_legacy=True)

    def test_short_complete_native_profiles_page_bank_and_payload_identity(self):
        packed=bytes([0x91])*16384+bytes(256)
        reports=[]
        for pace in (449,448):
            folder=self.root/'native'/str(pace)
            disk,meta=build(packed,folder,self.cover,model(pace))
            (folder/'audio.trd').write_bytes(disk)
            for profile in PROFILES:
                report=native_check(disk,meta,packed,profile,out=folder/(profile+'.json'))
                self.assertTrue(report['complete']);self.assertTrue(report['memory_guards_passed'])
                self.assertEqual(report['ordinary_tstates'],pace if profile.startswith('pentagon') else 423)
                self.assertTrue(report['pages']);self.assertEqual(report['reloads'],0)
                reports.append(dict(pace=pace,profile=profile,report=report))
        for profile in PROFILES:
            old=next(r['report'] for r in reports if r['pace']==449 and r['profile']==profile)
            new=next(r['report'] for r in reports if r['pace']==448 and r['profile']==profile)
            for key in ('bits_verified','predictor_index_samples','interval_extras','pages',
                        'bank_extra_tstates','explicit_reload_intervals'):
                self.assertEqual(new[key],old[key],(profile,key))
        PROOF['complete_short_native']=dict(runs=reports,source_bytes=len(packed),all_eight_complete=True,
            page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
            actual_Fuse_hardware_or_quality_claim=False)

    def test_ui_cold_maximum_and_all_profiles_dispatch(self):
        packed=bytes(2392*256);folder=self.root/'maximum'
        disk,meta=build(packed,folder,self.cover,model(448,ui=True))
        (folder/'audio.trd').write_bytes(disk)
        self.assertLess(meta['player_labels']['stream_worker_end'],0xBFFF)
        reports={}
        for profile in PROFILES:
            machine,report=cold_load(disk,meta,profile);labels=meta['player_labels']
            for bit in (0,1):
                target=machine.word(labels[f'stream_bank_dispatch_{bit}']+1)
                self.assertEqual(target,labels[f'stream_play_tail_{bit}' if profile.startswith('pentagon') else f'stream_legacy_handoff_{bit}'])
            patched=profile.startswith('pentagon')
            first=meta['first_addresses'][0]+39
            self.assertEqual(machine.read(first),0xC3 if patched else 0xFD)
            self.assertEqual(machine.word(first+1),labels['hardware_delay'] if patched else 0x00E9)
            reports[profile]=report
        self.assertEqual(reports['pentagon1024']['remaining_sectors'],0)
        PROOF['maximum_ui']=dict(source_bytes=len(packed),worker_end=meta['player_labels']['stream_worker_end'],
            profiles=reports,pentagon_live_progress_and_legacy_dispatch_preserved=True,
            physical_448_UI_cadence_seconds=meta['audio_progress_ui']['full_bank_update_seconds'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args,remaining=parser.parse_known_args()
    if args.output:EXPORT=args.output.resolve();EXPORT.mkdir(parents=True,exist_ok=True)
    program=unittest.main(argv=[__file__,*remaining],exit=False,verbosity=2)
    if EXPORT:
        PROOF.update(complete=program.result.wasSuccessful(),scope='Native instruction CPU only; no physical/Fuse/audio-quality claim')
        (EXPORT/'report.json').write_text(json.dumps(PROOF,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not program.result.wasSuccessful())
