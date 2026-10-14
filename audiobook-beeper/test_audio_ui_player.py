"""Exact-cycle bank progress and cold-loading proofs for the optional UI.

The short live proofs execute the actual assembled previous/new handlers,
including both last-bit variants on all four RAM profiles. Complete song
execution and real ULA/floppy timing are separately verified in Fuse.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from build_stream_trd import build, sections
from ram_machine import MemoryMachine
from verify_stream_trd import cold_load


HERE=Path(__file__).resolve().parent
REPO=HERE.parent
SNAPSHOT=HERE/'experiments/song-snr/evidence/achieved-disk/generated'
PROFILES=('128','scorpion','pentagon512','pentagon1024')
EXPORT=None
PROOF={}


def word(machine,address,value):
    machine.write(address,value&255);machine.write(address+1,value>>8)


def copy_machine(cold,labels):
    result=MemoryMachine(cold.kind,b'',labels)
    result.banks=[bytearray(bank) for bank in cold.banks]
    result.rom[:]=cold.rom
    result.low=24;result.high=result.eff=0;result.selected=0
    return result


def run_until(machine,pc,target,*,budget=1000000):
    machine.m.pc=pc;machine.m.set_breakpoint(target)
    machine.m.ticks_to_stop=budget
    while machine.m.pc!=target:
        event=machine.m.run()
        if event&machine.m._TICKS_LIMIT_HIT:
            raise AssertionError(('timeout',hex(machine.m.pc),hex(target)))
    return budget-machine.m.ticks_to_stop


class AudioUiPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch=REPO/'.tmp/audio-ui-player-tests';scratch.mkdir(parents=True,exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(dir=scratch)
        cls.root=Path(cls.temporary.name)
        cls.before=json.loads((SNAPSHOT/'player.json').read_bytes())
        cls.old_disk=(SNAPSHOT/'audio.trd').read_bytes()
        cls.packed=gzip.decompress((SNAPSHOT/'soundtrack.ima.gz').read_bytes())
        cls.cover=(SNAPSHOT/'cover.scr').read_bytes()
        cls.disk,cls.meta=build(cls.packed,cls.root/'assembly',cls.cover,
                              dict(cls.before['model'],audio_progress_ui=True))
        cls.cold={};cls.loading={}
        for profile in PROFILES:
            cls.cold[profile],cls.loading[profile]=cold_load(cls.disk,cls.meta,profile)
        PROOF['trd_sha256']=hashlib.sha256(cls.disk).hexdigest()
        PROOF['baseline_trd_sha256']=hashlib.sha256(cls.old_disk).hexdigest()

    @classmethod
    def tearDownClass(cls):
        if EXPORT:
            import shutil
            shutil.copytree(cls.root/'assembly',EXPORT/'assembly',dirs_exist_ok=True)
            (EXPORT/'audio.trd').write_bytes(cls.disk)
            (EXPORT/'player.json').write_text(json.dumps(cls.meta,indent=2)+'\n',encoding='utf-8')
        cls.temporary.cleanup()

    def test_default_and_false_disk_and_metadata_exact(self):
        for flag in (None,False):
            model=dict(self.before['model'])
            if flag is not None:model['audio_progress_ui']=flag
            disk,meta=build(self.packed,self.root/('default-'+str(flag)),self.cover,model)
            self.assertEqual(disk,self.old_disk);self.assertEqual(meta,self.before)
        PROOF['default_identity']=dict(disk_exact=True,metadata_exact=True,
            absent_and_false=True,baseline_commit='5b7b8931',
            authenticated_baseline_sha256='ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074')

    def test_all_four_cold_loads_and_whole_source_records(self):
        labels=self.meta['player_labels'];reports={}
        for profile in PROFILES:
            machine=self.cold[profile];records=[];offset=0
            for index,part in enumerate(self.loading[profile]['loaded_sections']):
                at=labels['stream_play_records']+index*10
                flags=machine.read(at);paging=machine.read(at+1)
                expected_paging=24|(part['bank']&7)|((part['bank']&24)<<3)|(part['bank']&32)
                if profile=='scorpion':expected_paging=24|(part['bank']&7)
                self.assertEqual(flags,0);self.assertEqual(paging,expected_paging)
                self.assertEqual(machine.word(at+2),part['address']|paging)
                columns=32*offset//len(self.packed)
                expected=([labels['stream_play_dummy']]*2 if columns==0 else
                          [0xDAC0+max(0,columns-2),0xDAC0+columns-1])
                self.assertEqual([machine.word(at+4),machine.word(at+6)],expected)
                self.assertEqual(machine.word(at+8),0)
                records.append(dict(offset_bytes=offset,filled_columns=columns,
                                    paging=paging,attributes=expected))
                offset+=part['bytes']
            sentinel=labels['stream_play_records']+len(records)*10
            self.assertEqual(machine.word(sentinel),0x0040)
            self.assertEqual(machine.word(labels['stream_play_next_record']),labels['stream_play_records']+10)
            self.assertEqual(machine.read(0x5B78),0)
            self.assertEqual(machine.read(labels['stream_play_bar']),32*offset//len(self.packed))
            self.assertEqual(bytes(machine.banks[7][0x1AC0:0x1AE0]),bytes([4])*32)
            for bit in (0,1):
                target=machine.word(labels[f'stream_bank_dispatch_{bit}']+1)
                self.assertEqual(target,labels[f'stream_play_tail_{bit}' if profile.startswith('pentagon') else f'stream_legacy_handoff_{bit}'])
            reports[profile]=dict(loading=self.loading[profile],records=records,
                                  sentinel_af=64,initial_cursor_record=1,initial_green_columns=0)
        PROOF['cold_profiles']=reports

    def tail(self,profile,bit,enabled):
        if enabled:cold=self.cold[profile];meta=self.meta
        else:cold,_=cold_load(self.old_disk,self.before,profile);meta=self.before
        machine=copy_machine(cold,meta['player_labels']);m=machine.m;labels=meta['player_labels']
        # Enter immediately after SECOND's penultimate OUT: its remaining
        # EXX/INC E/JP Z, INC D/JP Z, handoff and release are all executed.
        second=labels[f'second_address_{bit}']
        sequence=bytes(machine.read(second+i) for i in range(64))
        offset=sequence.rfind(b'\xd9\x1c\xca')
        self.assertGreaterEqual(offset,0)
        for name,value in dict(af=0x3030,bc=0x00FE,de=0x1030,hl=0x0040,
                               ix=0x9ABC,iy=0xDEF0,alt_af=0x0081,
                               alt_bc=0x1234,alt_de=0xFFFF,
                               alt_hl=meta['decoder_rows'][9],sp=0x7777).items():setattr(m,name,value)
        before=[bytes(bank) for bank in machine.banks];events=[];budget=1000000
        original_output=machine.output
        def output(port,value):
            events.append(dict(port=port,value=value,tstate=budget-m.ticks_to_stop))
            original_output(port,value)
        m.set_output_callback(output)
        elapsed=run_until(machine,second+offset,0x40,budget=budget)
        beeper=[event for event in events if event['port']&255==254]
        self.assertEqual(len(beeper),1);self.assertEqual(beeper[0]['value'],bit*16)
        self.assertEqual(m.a,0x30);self.assertEqual(m.c,254)
        self.assertEqual(m.de,0x1030);self.assertEqual(m.ix,0x9ABC);self.assertEqual(m.iy,0xDEF0)
        self.assertEqual(m.hl,0x40);self.assertEqual(m.alt_hl,meta['decoder_rows'][9])
        self.assertEqual(m.alt_de,0xC000);self.assertEqual(m.alt_af&1,1)
        self.assertEqual(machine.selected,4)
        allowed=set()
        for label,size in (('stream_tail_hl',2),('stream_next_record',2),('stream_paging',1)):
            allowed.update(range(labels[label]-0x8000,labels[label]-0x8000+size))
        if enabled:allowed.update(range(labels['stream_play_next_record']-0x8000,labels['stream_play_next_record']-0x8000+2))
        for page,bank in enumerate(machine.banks):
            modified={i for i,(a,b) in enumerate(zip(bank,before[page])) if a!=b}
            self.assertTrue(modified <= (allowed if page==2 else {0x1AC0} if page==7 and enabled and profile.startswith('pentagon') else set()),(profile,bit,enabled,page,modified))
        if enabled and profile.startswith('pentagon'):
            self.assertEqual(machine.banks[7][0x1AC0],0x24)
            self.assertEqual([event['value'] for event in events if event['port']==0x7FFD],[31,28])
            self.assertEqual(machine.word(labels['stream_play_next_record']),labels['stream_play_records']+20)
        return dict(profile=profile,bit=bit,elapsed_to_next_dispatch_tstates=elapsed,
                    pulse=beeper[0],paging_events=events[:-1],registers_and_memory_guards=True)

    def test_both_literal_tails_all_profiles_exact_cycles_and_guards(self):
        reports=[]
        for profile in PROFILES:
            for bit in (0,1):
                before=self.tail(profile,bit,False);after=self.tail(profile,bit,True)
                self.assertEqual(after['elapsed_to_next_dispatch_tstates'],before['elapsed_to_next_dispatch_tstates'])
                self.assertEqual(after['pulse']['tstate'],before['pulse']['tstate'])
                self.assertEqual(after['pulse']['value'],before['pulse']['value'])
                self.assertEqual(after['elapsed_to_next_dispatch_tstates'],305 if profile=='scorpion' else 281)
                reports.append(dict(before=before,after=after,tstate_delta=0))
        PROOF['short_native_bank_handoffs']=reports

    def test_global_fraction_and_legacy_refill_origins(self):
        labels=self.meta['player_labels'];machine=copy_machine(self.cold['pentagon1024'],labels)
        word(machine,labels['stream_play_fraction'],0);machine.write(labels['stream_play_bar'],0)
        for sector in range(1,self.meta['audio_sectors']+1):
            machine.call('stream_play_advance_global')
            self.assertEqual(machine.read(labels['stream_play_bar']),32*sector//self.meta['audio_sectors'])
            self.assertEqual(machine.word(labels['stream_play_fraction']),32*sector%self.meta['audio_sectors'])
        self.assertEqual(machine.read(labels['stream_play_bar']),32)
        for profile in PROFILES:
            machine=copy_machine(self.cold[profile],labels)
            machine.write(labels['stream_play_batch_bar'],17)
            machine.call('stream_play_begin_batch')
            self.assertEqual(bytes(machine.banks[7][0x1AC0:0x1AE0]),bytes([0x24])*17+bytes([4])*15)
            self.assertEqual(machine.read(0x5B78),17);self.assertFalse(machine.m.iff1)
        PROOF['global_progress']=dict(every_sector_integer_fraction_verified=self.meta['audio_sectors'],
            completion_columns=32,refill_origin_redraw_columns=17,refill_profiles=list(PROFILES))

    def test_sentinel_restores_literal_resume_and_saved_ima_row(self):
        labels=self.meta['player_labels'];reports=[]
        for bit in (0,1):
            machine=copy_machine(self.cold['pentagon1024'],labels)
            sentinel=labels['stream_play_records']+(labels['record_slots']-1)*10
            word(machine,sentinel,64);word(machine,labels['stream_play_next_record'],sentinel)
            machine.m.hl=0x5432;machine.m.alt_af=0x30A5
            run_until(machine,labels[f'stream_play_tail_{bit}'],labels['stream_exhausted'])
            self.assertEqual(machine.word(labels['stream_tail_hl']),0x5432)
            self.assertEqual(machine.word(labels['stream_reload_end']+1),labels[f'stream_play_tail_{bit}'])
            self.assertEqual(machine.m.alt_af,0x30A5)
            self.assertEqual(machine.word(labels['stream_play_next_record']),sentinel)
            reports.append(dict(bit=bit,saved_ima_row=0x5432,literal_resume=labels[f'stream_play_tail_{bit}'],prefetched_nibble_preserved=True))
        PROOF['refill_sentinel']=reports

    def test_maximum_2392_sector_layout_and_cold_load(self):
        packed=bytes(2392*256)
        disk,meta=build(packed,self.root/'maximum',bytes(6912),dict(self.before['model'],audio_progress_ui=True))
        machine,report=cold_load(disk,meta,'pentagon1024');labels=meta['player_labels']
        self.assertEqual(report['remaining_sectors'],0)
        self.assertEqual(sum(part['bytes'] for part in report['loaded_sections']),len(packed))
        self.assertEqual(labels['record_slots'],39)
        self.assertEqual(labels['stream_play_records_end']-labels['stream_play_records'],390)
        self.assertLessEqual(labels['startup_end'],0x8340);self.assertLess(labels['stream_worker_end'],0xBFFF)
        self.assertLessEqual(labels['audio_ui_end'],labels['worker_origin'])
        PROOF['maximum_capacity']=dict(packed_bytes=len(packed),audio_sectors=2392,
            record_slots=39,command_bytes=390,startup_end=labels['startup_end'],
            worker_end=labels['stream_worker_end'],ui_resident_end=labels['audio_ui_end'],
            cold_loading_complete=report,default_bank_allocation_unchanged=True,
            scope='Complete cold load, not full maximum-length audio execution')

    def test_final_full_green_and_centered_caption_all_profiles(self):
        labels=self.meta['player_labels'];reports=[]
        for profile in PROFILES:
            machine=copy_machine(self.cold[profile],labels)
            for code in range(32,127):
                machine.rom[0x3C00+code*8:0x3C00+code*8+8]=bytes((code*17+row*29)&255 for row in range(8))
            before_audio=bytes(machine.banks[7][0x1B00:]);outputs=[];original=machine.output
            def output(port,value):outputs.append((port,value));original(port,value)
            machine.m.set_output_callback(output)
            run_until(machine,labels['stream_finish'],labels['stream_finished'])
            self.assertEqual(bytes(machine.banks[7][0x1AC0:0x1AE0]),bytes([0x24])*32)
            self.assertEqual(bytes(machine.banks[7][0x1B00:]),before_audio)
            for column,char in enumerate('END OF AUDIO'):
                for row in range(8):self.assertEqual(machine.banks[7][0x108A+column+row*256],(ord(char)*17+row*29)&255)
            self.assertEqual([value for port,value in outputs if port&255==254],[0])
            reports.append(dict(profile=profile,final_columns=32,caption='END OF AUDIO',caption_column=10,
                                audio_bank7_guard=True,only_teardown_mute=True))
        PROOF['completion']=reports


def main():
    global EXPORT
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args,remaining=parser.parse_known_args()
    if args.output:EXPORT=args.output.resolve();EXPORT.mkdir(parents=True,exist_ok=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AudioUiPlayerTests))
    if EXPORT:
        producers=('stream-player.asm','stream-worker.asm','stream-progress.asm','stream-playback-progress.asm',
                   'stream-audio-ui.asm','stream-audio-ui-helper.asm','build_stream_trd.py','direct_player.py','verify_stream_trd.py','test_audio_ui_player.py')
        PROOF['producer_sha256']={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in producers}
        PROOF.update(complete=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
            scope='Native CPU/functional/guard proof. No ULA contention or real floppy/Fuse claim. Full own-clock song evidence is separate.')
        (EXPORT/'report.json').write_text(json.dumps(PROOF,indent=2)+'\n',encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
