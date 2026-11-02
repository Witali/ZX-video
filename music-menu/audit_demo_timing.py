"""Count changed demo paths against the old AY-menu CPU baseline.

Counts use libraries/Z80_TIMINGS.md and the independent native Z80. Ordinary
instruction T states include complete entry-through-RET, required setup and
state storage. External CALL17, ULA contention, IRQ19 and floppy time are
separate. Complete physical scheduling remains the full Fuse report's scope.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from build import ROOT,sha
from verify import Machine


def audit(output):
    meta=json.loads((output/'build.json').read_text())
    native=json.loads((output/'native-demo.json').read_text())
    labels=meta['player_labels']
    blob=(output/'assembly/player.bin').read_bytes()
    def fixture(root,pending=b'',dictionary=b''):
        m=Machine(blob,labels)
        m.cpu.set_memory_block(0xC000,root)
        m.word('record_pointer',0xC000)
        m.word('grammar_sp',0xB700+len(pending))
        m.cpu.set_memory_block(0xB700,pending)
        if dictionary:
            m.cpu.set_memory_block(labels['grammar_dictionary'],dictionary)
        t=m.call('read_byte')
        return t,m.cpu.a
    direct=fixture(bytes([42]))
    pending=fixture(b'',bytes([42,0]))
    escape=fixture(bytes([255,128]))
    pair=fixture(bytes([128]),dictionary=bytes([42,0,43,0]))
    assert direct==(252,42) and pending==(199,42) and escape==(362,128)
    assert pair==(489,42)
    from verify_demo import boot
    m=Machine(blob,labels)
    boot(m,(output/meta['disk_name']).read_bytes())
    def call_cost(name):
        m.cpu.sp=0xBCFE
        m.cpu.memory[0xBCFE:0xBD00]=b'\xff\x7f'
        return m.run_to(labels[name],[0x7FFF],3000000)
    foreground={}
    for kind,name in ((0,'reveal'),(1,'petal')):
        m.byte('tile_kind',kind)
        m.cpu.hl=0
        foreground['single_tile_'+name]=call_cost('draw_tile')
        m.cpu.hl=0
        foreground['sixteen_tile_'+name]=call_cost('tile_batch')
    foreground['footer_bitmap_copy']=call_cost('draw_footer')
    foreground['menu_snapshot_restore_with_ui']=call_cost('show_menu')
    old=json.loads((ROOT/'music-menu/reports/autoplay/native.json').read_text())
    baseline=[]
    for song in old['songs']:
        hist=song['audio_service_with_caller_tstates']
        baseline.append(dict(song=song['song'],subsequent_fields_audio_cpu_tstates=sum(int(k)*v for k,v in hist.items()),
            scope='Old foreground audio caller, excludes choose tick0, EOF, menu and IRQ37 per field.'))
    before=[1452,1616,3748]
    report=dict(trd_sha256=meta['trd_sha256'],timing_reference='libraries/Z80_TIMINGS.md',
        byte_provider=dict(old_uncompressed=75,root_literal=252,root_literal_delta=177,
            pending_literal=199,pending_literal_delta=124,escaped_root=362,escaped_root_delta=287,
            root_pair_leaf=489,root_pair_leaf_delta=414,additional_pair_expansion=193,
            max_dictionary_depth=meta['music_codec']['max_depth'],
            formula='Root pair path 296+193*d; pending path 199+193*d; d is number of expanded pairs.'),
        unchanged_mask_loop_old_record_cost=dict(zero_writes=before[0],one_write=before[1],fourteen_writes=before[2],
            formula='New record cost adds sum(provider_cost-75) for its 3+w decoded bytes; parser unchanged.'),
        mute=dict(before=1164,after=1153,delta=-11,reason='Remove border-reset XOR/OUT15, replace with NOP4; preserve picture BORDER.'),
        paging=dict(before_stream_tail=39,after_stream_tail=62,delta=23,reason='JP10 to shared page helper; latch store13.'),
        full_irq_body=dict(previous=18,new_min=min(map(int,native['irq_body_tstates'])),
            new_max=max(map(int,native['irq_body_tstates'])),
            max_delta=max(map(int,native['irq_body_tstates']))-18,
            hardware_im2_entry=19,field_budget=70908,
            scope='New body includes bank save/restore, register preservation, playlist clock and complete music service.'),
        foreground_paths=dict(previous=0,paths=foreground,
            scope='Entry through RET, required state writes included; sample tile0/16-cell batch. New graphics paths have no old implementation.'),
        baseline_audio=baseline,decoder_comparison=native['decoder_comparison'],
        qualifiers='Plain native CPU counts; actual ULA/contention/disk execution is in fuse-demo.json. Graphics one-shot decode may span fields while music remains in IRQ.')
    (output/'timing-demo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('decoder_comparison','baseline_audio')},indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/expedition-33-demo')
    audit(p.parse_args().output.resolve())
