"""Check exact separated payloads, all cold-installed bytes and Z80 priming.

Boot and priming execute real opcodes with mocked ROM reads and no scheduled
interrupts. This checks first-frame/checkpoint/queue integration, not cadence.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha,display_screen
from bulk_frame_stream import read_packet
import disk_progress_z80 as progress
import fap3_disk_z80 as disk
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until
from uncontended_frame import FRAME
from zx0_codec import decompress

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','raw-directory','states','report','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); built=json.loads(a.report.read_bytes())
    if not built['complete']:raise ValueError('partial resident build')
    for n,digest in built['source_sha256_lf'].items():
        if sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n'))!=digest:raise ValueError(('build source differs',n))
    with np.load(a.states,allow_pickle=False) as source:states=source['states']
    results=[]
    for part in (1,2,3):
        m,stream,blocks=disk_blocks(a.directory,part)
        image=(a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        if sha(image)!=m['trd_sha256'] or m['used_sectors']>2544 or not m['independently_bootable']:
            raise ValueError('disk identity/capacity differs')
        raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
        if sha(raw)!=m['raw_sha256'] or sha(states.tobytes())!=m['states_sha256']:
            raise ValueError('raw/states source differs')
        r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3')
        video=Reader(b''.join(chunk for _,chunk in blocks));ticks=[];initial=bytearray(11)
        for i in range(count):
            _,old=read_packet(r,stored_guards=False)
            if i<m['frame_start']:
                for tick in old['ticks']:
                    for reg,value in zip(tick[1::2],tick[2::2],strict=True):initial[reg]=value
            if m['frame_start']<=i<m['frame_end_exclusive']:
                prefix=b''.join(old['ticks']);body=video.take(video.u16())
                expected=bytearray(old['payload'])
                if i in m['forced_native_map_frames']:
                    # Preserve the existing independent-volume cold-bitmap
                    # policy: render both native screens fully at this start.
                    at=old['coded_offset']-80
                    expected[at:at+80]=b'\xff'*80
                if prefix+body!=expected:raise AssertionError('video-only packet changed a video field')
                ticks.extend(old['ticks'])
        r.end();video.end()
        c=DiskCPU(player(image),image)
        for bank in (0,1,2,3,4,6,7):c.banks[bank][:]=b'\xa7'*16384
        c.banks[5][:6912]=b'\xa7'*6912
        c.banks[5][0x2400:]=b'\xa7'*(16384-0x2400)
        until(c,disk.DRIVER)
        checked=0
        for s in m['sections']:
            begin=s['sector']*256+s['source_offset']
            decoded=decompress(image[begin:begin+s['compressed_bytes']],limit=s['decoded_bytes'])
            if s.get('startup_delta'):
                from probe_startup_tables import undifference
                decoded=undifference(decoded)
            if sha(decoded)!=s['sha256']:raise AssertionError('decoded startup section differs')
            lo=s['address']&16383
            skip=max(0,0x7600-s['address']) if s['bank']==5 and s['address']==0x6400 else 0
            if bytes(c.banks[s['bank']][lo+skip:lo+len(decoded)])!=decoded[skip:]:
                raise AssertionError(('cold RAM differs',part,s['bank'],s['address']))
            checked+=len(decoded)-skip
        resident=m['resident_audio'];compiled=resident['compiled'];labels=compiled['labels']
        expected_bank=bytes.fromhex(compiled['image_hex'])
        if bytes(c.banks[4][:len(expected_bank)])!=expected_bank:raise AssertionError('cold audio bank differs')
        before=c.tstates;until(c,m['clock_labels']['start'])
        def byte(address):return c.read8(address)
        def word(address):return byte(address)|(byte(address+1)<<8)
        q=m['queue_labels'];ay=m['audio_labels']
        occupancy=(byte(ay['audio_write_index'])-byte(ay['audio_read_index']))&31
        if not 24<=occupancy<=31 or byte(ay['audio_enabled']) or word(ay['audio_ticks_played']):
            raise AssertionError(('incorrect prepared AY queue',part,occupancy))
        if bytes(c.ay[:11])!=initial:raise AssertionError('initial AY state differs before start')
        for i,tick in enumerate(ticks[:occupancy]):
            if bytes(c.read8(0xa000+32*i+j) for j in range(len(tick)))!=tick:
                raise AssertionError(('prefilled AY record differs',part,i))
        for i,v in enumerate(expected_bank):
            if labels['state']-0xc000<=i<labels['state_end']-0xc000:continue
            if c.banks[4][i]!=v:raise AssertionError(('resident bank overwritten by video',part,i))
        if byte(q['count'])>3 or max(byte(q['read_slot']),byte(q['write_slot']))>2:
            raise AssertionError('fourth video slot remains reachable')
        expected=progress.reference_screen(display_screen(states[m['frame_start']].tobytes(),black_borders=True),0,m['frames'])
        if bytes(c.banks[7][:6912])!=expected:raise AssertionError(('first complete native screen differs',part))
        if bytes(c.read8(FRAME+i) for i in range(3840))!=states[m['frame_start']+1].tobytes():
            raise AssertionError(('second compact frame differs',part))
        results.append(dict(part=part,installed_bytes_checked=checked,exact_all_video_packets=True,
            prepared_audio_records=occupancy,audio_initial_state_exact=True,audio_bank_immutable_exact=True,
            first_native_screen_exact=True,second_compact_frame_exact=True,
            priming_cpu_tstates=c.tstates-before,read_slot=byte(q['read_slot']),write_slot=byte(q['write_slot']),
            slot_count=byte(q['count']),mocked_boot_and_priming_sectors=c.dos_reads))
        print(json.dumps(results[-1]),flush=True)
    report=dict(complete=True,release=False,scope=__doc__,volumes=results,
        build_sha256=sha(a.report.read_bytes()),source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
