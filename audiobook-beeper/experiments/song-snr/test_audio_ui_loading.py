"""Actual Z80 loading UI geometry, frame cadence and protected-bank checks.

These are standalone routine proofs with a deterministic synthetic ROM font
and explicit ROM FRAMES values. They do not run the disk or claim actual
floppy/IRQ cadence. Integration/native/full Fuse audio checks remain separate.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ram_machine import MemoryMachine


REPO=Path(__file__).resolve().parents[3]
MODULE=REPO/'audiobook-beeper/stream-audio-ui.asm'
HELPER=REPO/'audiobook-beeper/stream-audio-ui-helper.asm'
PROFILES=('128','scorpion','pentagon512','pentagon1024')


def assemble_ui(work,origin=0x808A,helper_origin=0xB940):
    """Link the relocation-flexible module to the unchanged cache_restore ABI."""
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    cache=(REPO/'audiobook-beeper/ram-cache.asm').read_text()
    restore=cache[cache.index('cache_restore:\n'):cache.index('; Test two physical page selectors')]
    (work/'stream-audio-ui.asm').write_bytes(MODULE.read_bytes())
    (work/'stream-audio-ui-helper.asm').write_bytes(HELPER.read_bytes())
    text=(f'ORG {origin}\ncache_bar: EQU 0x5B78\ncache_mode: EQU 0x5B72\n'
          'INCLUDE "stream-audio-ui.asm"\nASSERT audio_ui_startup_end < 0x8340\n'
          f'DS {helper_origin} - $\nINCLUDE "stream-audio-ui-helper.asm"\n'
          'ASSERT audio_ui_end < 0xBA00\nDS 0xBB00 - $\n'+restore)
    (work/'test.asm').write_text(text,encoding='utf-8',newline='\n')
    result=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=ui.bin','--lstfile=ui.lst','-s','.*','test.asm'],cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
    if result.returncode:raise AssertionError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(x) for x in result.stdout.splitlines() if x.startswith('{'))
    (work/'labels.json').write_text(json.dumps(labels,indent=2)+'\n',encoding='utf-8',newline='\n')
    return (work/'ui.bin').read_bytes(),labels


def glyph(character):
    return bytes((ord(character)*17+row*29)&255 for row in range(8))


class UIHarness:
    def __init__(self,profile,blob,labels,origin=0x808A):
        self.machine=MemoryMachine(profile,b'',labels);self.labels=labels
        self.machine.banks[2][origin-0x8000:origin-0x8000+len(blob)]=blob
        self.machine.write(0x5B72,{'128':0,'scorpion':1,'pentagon512':2,'pentagon1024':3}[profile])
        for code in range(32,127):self.machine.rom[0x3C00+code*8:0x3C00+code*8+8]=glyph(chr(code))
        self.outputs=[];old=self.machine.output
        def output(port,value):
            self.outputs.append((port,value));old(port,value)
        self.machine.m.set_output_callback(output)
        self.preserved=dict(ix=0x1234,iy=0x5C3A,alt_af=0x5566,alt_bc=0x1122,alt_de=0x3344,alt_hl=0x7788)
        for key,value in self.preserved.items():setattr(self.machine.m,key,value)
        self.initial=[bytes(bank) for bank in self.machine.banks]

    def frames(self,value):
        self.machine.write(0x5C78,value&255);self.machine.write(0x5C79,(value>>8)&255)

    def call(self,label,**registers):
        self.machine.call(label,**registers)
        assert all(getattr(self.machine.m,key)==value for key,value in self.preserved.items())
        assert not any((port&255)==0xFE for port,value in self.outputs),'UI must not write the beeper port'
        self.guards()

    def guards(self):
        for page,bank in enumerate(self.machine.banks):
            before=self.initial[page]
            if page==2:
                begin=self.labels['audio_ui_data_start']-0x8000;end=self.labels['audio_ui_data_end']-0x8000
                assert bytes(bank[:begin])==before[:begin] and bytes(bank[end:])==before[end:]
            elif page==5:
                allowed=set(range(0x1FC0,0x2000))|{0x1B78,0x1C78,0x1C79}
                assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(bank,before)))
            elif page==7:
                allowed={0x108B+row*256+column for row in range(8) for column in range(10)}
                allowed|=set(range(0x1A8B,0x1A95))|set(range(0x1AC0,0x1AE0))
                assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(bank,before)))
                assert bytes(bank[0x1B00:])==before[0x1B00:],'bank7 audio payload was overwritten'
            else:assert bytes(bank)==before

    def expect_label(self,text,attribute):
        bank=self.machine.banks[7]
        assert len(text)==10
        for column,char in enumerate(text):
            for row,value in enumerate(glyph(char)):assert bank[0x108B+row*256+column]==value
        assert bytes(bank[0x1A8B:0x1A95])==bytes([attribute])*10

    def expect_bar(self,count,filled,empty):
        assert bytes(self.machine.banks[7][0x1AC0:0x1AE0])==bytes([filled])*count+bytes([empty])*(32-count)


class AudioUILoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch=REPO/'.tmp/audio-ui-tests';cls.scratch.mkdir(parents=True,exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(dir=cls.scratch);cls.work=Path(cls.temporary.name)
        assert cls.work.resolve().parent==cls.scratch.resolve()
        cls.blob,cls.labels=assemble_ui(cls.work/'startup')
        cls.relocated,cls.relocated_labels=assemble_ui(cls.work/'relocated',0x8100,0xB800)

    @classmethod
    def tearDownClass(cls):
        assert Path(cls.temporary.name).resolve().parent==cls.scratch.resolve()
        cls.temporary.cleanup()

    def harness(self,profile='pentagon1024'):
        return UIHarness(profile,self.blob,self.labels)

    def test_relocatable_split_and_maximum_record_padding(self):
        self.assertEqual(self.labels['audio_ui_startup_end']-0x808A,153)
        self.assertEqual(self.labels['audio_ui_end']-0xB940,185)
        self.assertEqual(self.relocated_labels['audio_ui_startup_end']-0x8100,153)
        self.assertEqual(self.relocated_labels['audio_ui_end']-0xB800,185)
        self.assertLessEqual(self.labels['audio_ui_startup_end']+514,0x8340)
        self.assertLess(self.labels['audio_ui_end'],0xBA00)
        self.assertEqual(self.labels['audio_ui_data_end']-self.labels['audio_ui_data_start'],4)
        for profile in PROFILES:
            h=UIHarness(profile,self.relocated,self.relocated_labels,0x8100);h.frames(123)
            h.call('audio_ui_begin_loading');h.expect_label('LOADING.  ',7);h.expect_bar(0,0x3F,7)

    def test_initial_loading_all_four_profiles(self):
        for profile in PROFILES:
            h=self.harness(profile)
            if profile=='scorpion':h.machine.output(0x1FFD,16);h.machine.output(0x7FFD,31)
            elif profile=='pentagon512':h.machine.output(0x7FFD,0xDF)
            elif profile=='pentagon1024':h.machine.output(0x7FFD,0xFF)
            else:h.machine.output(0x7FFD,31)
            self.assertEqual(h.machine.selected,{'128':7,'scorpion':15,'pentagon512':31,'pentagon1024':63}[profile])
            h.frames(100);h.call('audio_ui_begin_loading')
            h.expect_label('LOADING.  ',7);h.expect_bar(0,0x3F,7)
            self.assertEqual(h.machine.word(self.labels['audio_ui_frame']),100)
            self.assertEqual(h.machine.read(self.labels['audio_ui_dots']),1)
            self.assertEqual(h.machine.read(self.labels['audio_ui_loading']),1)
            self.assertEqual(h.machine.selected,0);self.assertFalse(h.machine.locked)
            self.assertTrue(h.machine.m.iff1)

    def test_frame_deadline_cycle_and_no_early_paging(self):
        h=self.harness();h.frames(100);h.call('audio_ui_begin_loading');before=len(h.outputs)
        h.frames(124);h.call('audio_ui_sector_tick');h.expect_label('LOADING.  ',7)
        self.assertEqual(len(h.outputs),before);self.assertEqual(h.machine.word(self.labels['audio_ui_frame']),100);self.assertTrue(h.machine.m.iff1)
        for frame,text,dots in [(125,'LOADING.. ',2),(150,'LOADING...',3),(175,'LOADING.  ',1)]:
            h.frames(frame);h.call('audio_ui_sector_tick');h.expect_label(text,7)
            self.assertEqual(h.machine.read(self.labels['audio_ui_dots']),dots)
            self.assertEqual(h.machine.selected,0)

    def test_frame_wrap_and_delayed_read_does_not_burst(self):
        h=self.harness();h.frames(65530);h.call('audio_ui_begin_loading')
        h.frames(19);h.call('audio_ui_sector_tick');h.expect_label('LOADING.. ',7)
        h.frames(1000);h.call('audio_ui_sector_tick');h.expect_label('LOADING...',7)
        before=len(h.outputs);h.frames(1024);h.call('audio_ui_sector_tick')
        self.assertEqual(len(h.outputs),before);h.expect_label('LOADING...',7)
        h.frames(1025);h.call('audio_ui_sector_tick');h.expect_label('LOADING.  ',7)

    def test_gray_loading_bar_exact_cells(self):
        for profile in PROFILES:
            h=self.harness(profile);h.frames(0);h.call('audio_ui_begin_loading')
            for cells in (0,1,17,32):
                h.machine.write(0x5B78,cells);h.call('audio_ui_draw_loading_bar')
                h.expect_bar(cells,0x3F,7);h.expect_label('LOADING.  ',7)
                self.assertEqual(h.machine.selected,0)

    def test_playing_green_reset_di_and_no_later_tick(self):
        for profile in PROFILES:
            h=self.harness(profile);h.frames(0);h.call('audio_ui_begin_loading');h.machine.write(0x5B78,32)
            h.call('audio_ui_begin_playback');h.expect_label('PLAYING   ',4);h.expect_bar(0,0x24,4)
            self.assertEqual(h.machine.read(0x5B78),0);self.assertEqual(h.machine.read(self.labels['audio_ui_loading']),0)
            self.assertFalse(h.machine.m.iff1);self.assertEqual(h.machine.selected,0)
            before=len(h.outputs);h.frames(500);h.call('audio_ui_sector_tick')
            self.assertEqual(len(h.outputs),before);h.expect_label('PLAYING   ',4);self.assertFalse(h.machine.m.iff1)

    def test_paused_global_green_redraw_does_not_reset_fill(self):
        for profile in PROFILES:
            h=self.harness(profile);h.frames(0);h.call('audio_ui_begin_loading');h.call('audio_ui_begin_playback')
            for cells in (0,1,17,32):
                h.machine.write(0x5B78,cells);h.call('audio_ui_redraw_playback_bar')
                h.expect_bar(cells,0x24,4);h.expect_label('PLAYING   ',4)
                self.assertEqual(h.machine.read(0x5B78),cells)
                self.assertEqual(h.machine.selected,0);self.assertFalse(h.machine.m.iff1)

    def test_end_clear_preserves_final_progress_and_disables_animation(self):
        for profile in PROFILES:
            h=self.harness(profile);h.frames(0);h.call('audio_ui_begin_loading');h.call('audio_ui_begin_playback')
            h.machine.write(0x5B78,32);h.call('audio_ui_redraw_playback_bar')
            h.call('audio_ui_clear_label');h.expect_label('          ',4);h.expect_bar(32,0x24,4)
            self.assertEqual(h.machine.read(0x5B78),32)
            self.assertEqual(h.machine.read(self.labels['audio_ui_loading']),0)
            self.assertEqual(h.machine.selected,0);self.assertFalse(h.machine.m.iff1)

    def test_print_returns_at_terminator(self):
        h=self.harness();h.machine.output(0x7FFD,31)
        h.call('audio_ui_print',hl=self.labels['audio_ui_loading_three'],de=0xD08B)
        self.assertEqual(h.machine.m.de,0xD095)
        self.assertEqual(h.machine.m.hl,self.labels['audio_ui_loading_three']+10)
        self.assertFalse(h.machine.m.halted)


if __name__=='__main__':unittest.main()
