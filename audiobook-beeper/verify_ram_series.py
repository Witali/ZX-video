"""Full adaptive loader/cache execution plus independent complete PDM proofs."""
import gzip
import hashlib
import json
from pathlib import Path

from ram_cache import PROFILES,playback_patch
from verify_ima3_series import native_part,fuse_volume,continuation_snapshot
from verify_pcm import save


def native_loader(disk,volume,profile):
    # Coherent physical banks exercise the actual controller/player assembly.
    # The ROM boundary supplies exact sectors; real ROM/latency is proved by
    # Fuse separately. Complete PDM is independently executed by native_part.
    from ram_machine import MemoryMachine
    labels=volume['controller_labels']
    m=MemoryMachine(profile,b'',labels)
    m.banks[5][:2560]=disk[17*256:27*256]
    m.m.pc=0x4000;m.m.sp=0x6000
    m.m.clear_breakpoint(0x40)
    metas=[json.loads(Path(x['metadata']).read_bytes()) for x in volume['parts']]
    ready={x['player_labels']['ready']-2 for x in metas}
    for at in ready:m.m.set_breakpoint(at)
    terminal=labels['swap_prompt'] if volume['volume']<volume['total_volumes'] else labels['finished']
    m.m.set_breakpoint(terminal);m.m.set_breakpoint(labels['wrong_disk_prompt'])
    total=0;seen=[];physical=[];bar=[];cover_before_audio=False;cache_counts=[]
    old_write=m.write
    def write(at,value):
        if at==0x5b78:bar.append(value)
        old_write(at,value)
    m.m.set_write_callback(write)
    m.m.set_breakpoint(labels['cover_visible'])
    while m.m.pc!=terminal:
        m.m.ticks_to_stop=100_000_000
        event=m.m.run();total+=1
        if total>10000:raise AssertionError('adaptive native loader did not finish')
        if m.m.pc==0x3d13:
            assert m.selected<8,'ROM called with extended RAM selected'
            sector=(m.m.de>>8)*16+(m.m.de&255)
            assert 0<=sector<volume['used_sectors'],('physical read outside data',sector,physical[-10:],hex(m.m.sp),hex(m.word(m.m.sp)),[m.read(0x5b70+i) for i in range(16)])
            physical.append(sector)
            for i,value in enumerate(disk[sector*256:(sector+1)*256]):m.write(m.m.hl+i,value)
            m.m.clear_breakpoint(0x3d13);m.m.ticks_to_stop=4;m.m.run();m.m.set_breakpoint(0x3d13)
        elif m.m.pc==labels['cover_visible']:
            assert m.banks[7][:6912]==disk[29*256:56*256]
            assert not seen
            cover_before_audio=True;m.m.clear_breakpoint(labels['cover_visible'])
        elif m.m.pc in ready:
            index=len(seen);meta=metas[index]
            assert index==len(seen)
            for section in meta['sections']:
                expected=disk[section['sector']*256:(section['sector']+section['sectors'])*256]
                assert m.banks[section['bank']][section['address']-0xc000:]==expected,('resident payload',index,section['bank'])
            expected=bytearray(disk[meta['player_sector']*256:(meta['player_sector']+64)*256])
            for address,patch in playback_patch(meta,profile):expected[address-0x8000:address-0x8000+3]=patch
            start=min(meta['first_addresses'])-0x8000
            assert m.banks[2][start:0x3800]==expected[start:0x3800],'code or timing patch differs'
            cover=disk[29*256:56*256]
            from pcm_player import spectrum_bitmap_offset
            for y in range(160):
                for x in range(32):
                    at=spectrum_bitmap_offset(x,y);assert m.banks[7][at]==cover[at]
            assert m.read(0x5b78)==32,'progress incomplete at audio start'
            assert m.banks[7][0x1ac0:0x1ae0]==bytes([0x24]*32)
            assert m.word(0x5b74)+m.word(0x5b76)<=volume['used_sectors']
            cache_counts.append(m.word(0x5b76));seen.append(index)
            # Full live CPU/PDM is tested separately; resume the actual silent
            # transition here, keeping all real loader/cache/screen RAM.
            m.m.pc=meta['player_labels']['chain_exit'];m.m.halted=False
        elif m.m.pc==labels['wrong_disk_prompt']:raise AssertionError('native accepted volume rejected')
        elif event&m.m._TICKS_LIMIT_HIT:raise AssertionError(('native loader timeout',hex(m.m.pc)))
    assert len(seen)==len(metas) and cover_before_audio and not m.locked
    return dict(complete=True,machine=profile,parts_loaded=len(seen),cover_before_audio=True,
                every_resident_byte_exact=True,every_code_and_pacing_byte_exact=True,cover_preserved=True,
                progress_complete_at_every_part=True,cache_sector_counts=cache_counts,
                physical_sector_calls=len(physical),physical_sectors=physical,
                paging_never_locked=True,scope='Complete loading/cache/controller transitions; ROM sector supply stubbed, active PDM separately proved')


def verify_series(out,fuse,ffmpeg):
    from concurrent.futures import ThreadPoolExecutor,as_completed
    volumes=json.loads((out/'volumes.json').read_bytes())
    root=out/'verification';root.mkdir(exist_ok=True)
    def prove(profile):
        runs=[];continuations=[];previous=None
        for volume in volumes:
            disk=(out/volume['file']).read_bytes()
            assert hashlib.sha256(disk).hexdigest()==volume['trd_sha256']
            folder=root/profile/f'volume-{volume["volume"]:04d}';folder.mkdir(parents=True,exist_ok=True)
            save(folder/'native-loader.json',native_loader(disk,volume,profile))
            for record in volume['parts']:
                meta=json.loads(Path(record['metadata']).read_bytes());meta['ram_profile']=profile
                packed=gzip.decompress((Path(record['selected'])/'soundtrack.ima.gz').read_bytes())
                save(folder/f'native-part-{record["slot"]:02d}.json',native_part(disk,meta,packed))
            cold,ram=fuse_volume(out/volume['file'],volume,folder/'cold',fuse,ffmpeg=ffmpeg,machine=profile)
            runs.append(cold)
            if previous is not None:
                snap=folder/'resume.szx';snap.write_bytes(continuation_snapshot(previous,previous_labels['key_accepted'],machine=profile))
                wrong,_=fuse_volume(out/previous_volume['file'],volume,folder/'wrong',fuse,ffmpeg=ffmpeg,snapshot=snap,expect_wrong=True,machine=profile)
                resumed,ram=fuse_volume(out/volume['file'],volume,folder/'resumed',fuse,ffmpeg=ffmpeg,snapshot=snap,machine=profile)
                resumed['wrong_disk_check']=wrong;continuations.append(resumed)
            previous=ram;previous_volume=volume;previous_labels=volume['controller_labels']
        return runs,continuations
    report=dict(complete=False,volumes=[],continuations=[],machines={})
    # Each emulator has private output/media and no saved settings. Within a
    # machine keep disk continuations sequential; different machines are independent.
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(prove,p):p for p in PROFILES}
        for future in as_completed(pending):
            profile=pending[future];runs,continued=future.result()
            report['machines'][profile]=runs;report['continuations'].extend(continued)
            if profile=='128':report['volumes']=runs
            print(json.dumps(dict(stage='machine-qualified',machine=profile)),flush=True)
            save(root/'report.json',report)
    report['complete']=True;save(root/'report.json',report)
    return report
