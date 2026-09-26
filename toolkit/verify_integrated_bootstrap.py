"""Verify real cold-installed bytes against the measured queue and CPU model."""
import argparse
import json
from pathlib import Path
import struct
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
import fap3_disk_z80 as disk
from slot_queue_player import build
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','baseline-directory','raw-directory'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--report',type=Path,default=Path('toolkit/integrated_bootstrap_build.json'))
    a=p.parse_args();report=json.loads(a.report.read_bytes())
    if not report['complete'] or len(report['volumes'])!=3:raise ValueError('incomplete build')
    for name,digest in report['source_sha256'].items():
        if sha(Path(__file__).with_name(name).read_bytes())!=digest:raise ValueError(('source changed',name))
    model=json.loads(Path(__file__).with_name('inline_huffman_patches_cpu.json').read_bytes())
    for part in (1,2,3):
        m,stream,_=disk_blocks(a.directory,part);old,old_stream,_=disk_blocks(a.baseline_directory,part)
        raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
        if (sha(raw)!=m['raw_sha256'] or stream!=old_stream or m['used_sectors']>2544 or
            m['trd_sha256']!=report['volumes'][part-1]['trd_sha256'] or
            not m['independently_bootable'] or not m['integrated_slot_queue']):raise ValueError('wrong volume')
        image=(a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        old_image=(a.baseline_directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        # The generalized hooks must preserve the legacy bootstrap byte for byte.
        old_boot,_=disk.build_bootstrap(old['sections'],old['video_start_sector'],old['video_sectors'],
            next_id=bytes.fromhex(old['disk_id_hex'])[:14]+struct.pack('<H',part+1),interleaved=True)
        if old_boot!=player(old_image):raise AssertionError('legacy bootstrap changed')
        c=DiskCPU(player(image),image);until(c,disk.DRIVER)
        patches,_=build(old,raw,uncontended=True,compiled_masks=True,inline_literals=True,demand_decode=True)
        if m.get('bank2_zx0',{}).get('enabled'):
            from bank2_zx0 import build as split_decoder
            regions,labels,relocation=split_decoder()
            if labels!=m['decoder_labels']:raise AssertionError('relocated labels differ')
            for key,value in relocation.items():
                if m['bank2_zx0'][key]!=value:raise AssertionError(('relocation differs',key))
            patches=dict(patches)
            for change in m['bank2_zx0']['external_operands']:
                if (change['new_operand']-change['old_operand']!=relocation['new_origin']-relocation['old_origin'] or
                    change['delta_tstates']!=0):raise AssertionError('invalid external relocation')
                for i,v in enumerate(change['new_operand'].to_bytes(2,'little')):
                    patches[change['operand_address']+i]=v
            for address,blob in regions+[(relocation['old_origin'],bytes(relocation['core_and_state_bytes']))]:
                patches.update({address+i:v for i,v in enumerate(blob)})
            patches=sorted(patches.items())
        if m.get('audio_wait_prefetch',{}).get('enabled'):
            from audio_wait_prefetch import build as audio_helper
            helper=m['audio_wait_prefetch'];blob,expected=audio_helper(m['queue_labels']['step'],
                int.from_bytes(bytes.fromhex(helper['previous_hook_hex'])[-2:],'little'))
            if any(helper[k]!=v for k,v in expected.items()):raise AssertionError('audio helper metadata differs')
            patches=dict(patches)
            for address,data in ((helper['origin'],blob),(helper['hook_address'],bytes.fromhex(helper['hook_hex']))):
                patches.update({address+i:v for i,v in enumerate(data)})
            patches=sorted(patches.items())
        if m.get('ready_packet_guard',{}).get('enabled'):
            from ready_packet_guard import build as packet_guard
            helper=m['ready_packet_guard'];blob,expected=packet_guard(m['queue_labels'],helper['audio_labels'],m['packet_labels']['read_packet'])
            if any(helper[k]!=v for k,v in expected.items()):raise AssertionError('packet guard metadata differs')
            patches=dict(patches)
            for address,data in ((helper['origin'],blob),(helper['hook_address'],bytes.fromhex(helper['hook_hex']))):
                patches.update({address+i:v for i,v in enumerate(data)})
            patches=sorted(patches.items())
        inline=model['volumes'][part-1]['inline_patches']
        if m.get('fast_return_irq',{}).get('enabled'):
            from fast_return_irq import install as fast_irq
            import copy
            helper=m['fast_return_irq'];patches=dict(patches)
            rows=copy.deepcopy(m['slot_queue_instruction_listing'])
            for r in rows:
                if r['address']==helper['hook_address']:r['instruction']='JP Z,disk_finish'
            def put(address,blob):patches.update({address+i:v for i,v in enumerate(blob)})
            expected=fast_irq(lambda address:patches.get(address,c.read8(address)),put,
                dict(m,slot_queue_instruction_listing=rows))
            if expected!=helper:raise AssertionError('fast IRQ metadata differs')
            patches=sorted(patches.items())
        retired=[(v['start'],v['end']) for v in m['retired_fixed_code']]
        retired.append((inline['redirect_address'],inline['redirect_address']+3))
        checked=0
        for address,value in patches:
            if any(lo<=address<hi for lo,hi in retired):continue
            # Runtime cursor changes with startup-sector placement.
            if m['disk_labels']['disk_position']<=address<m['disk_labels']['disk_position']+2:continue
            if c.read8(address)!=value:raise AssertionError(('installed fixture differs',part,hex(address)))
            checked+=1
        blob=bytes.fromhex(inline['code_hex']);offset=inline['origin']&16383
        if (bytes(c.banks[6][offset:offset+len(blob)])!=blob or
            bytes(c.read8(inline['redirect_address']+i) for i in range(3))!=bytes.fromhex(inline['redirect_bytes'])):
            raise AssertionError('installed Huffman differs from full-frame CPU model')
        if c.dos_reads!=sum(s['sectors'] for s in m['sections']):raise AssertionError('unexpected preload')
        print(f'Part {part}: exact stream, legacy bootstrap unchanged, {checked} fixture bytes and {len(blob)} inline bytes exact',flush=True)


if __name__=='__main__':main()
