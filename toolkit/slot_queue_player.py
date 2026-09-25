"""Install the experimental queue into a current independently booted player.

Returns debugger patches plus fresh measurement labels. Images/packets are
unchanged. Bootstrap's old ring preload is discarded and measured playback
rereads the full video stream. This is an integration fixture, not a release
builder, capacity check or bootstrap optimization.
"""
from copy import deepcopy
from build_fap3_trd import player_harness,sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
import bank_local_zx0 as local
import direct_slot_input_z80 as producer
import slot_queue_z80 as queue
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
import bulk_frame_z80 as packet


def build(metadata,raw,*,uncontended=False):
    m=deepcopy(metadata)
    if not m.get('irq_safe_paging') or not m.get('independently_bootable'):
        raise ValueError('queue requires IRQ-safe paging and an independent volume')
    if sha(raw)!=m['raw_sha256']:raise ValueError('wrong volume Huffman stream')
    r=Reader(raw);_,_,count,mapping,tables=read_header(r,magic=b'FAP3')
    ay=bytearray(11)
    for _ in range(m['frame_start']):
        _,detail=read_packet(r,stored_guards=False)
        for tick in detail['ticks']:
            for i in range(tick[0]):ay[tick[1+2*i]]=tick[2+2*i]
    options={key:m[key] for key in ('inline_matches','fast_noop_scan','irq_safe_paging',
        'static_cache_borders','carry_huffman','register_fragments')}
    h=player_harness(bytes(4),tables,mapping,m['frames'],**options)
    zcode,z=local.build(dynamic_input=True)
    dcode,d,drows=disk.build_disk(m['video_start_sector'],m['video_sectors'],
        fast_disk=True,cached_seek=True,interleaved=True)
    scode,seek,srows=disk.build_cached_seek(d)
    pcode,p,prows=producer.build(z,d)
    regions,q,qrows=queue.build(z,p,len(m['blocks']))
    vregions,vl,vrows=video.build_video(h.frame.draw,z,h.audio,irq_safe_paging=True)
    regions += [(a,b) for a,b in vregions if a==video.VIDEO]
    code,bridge,pl,rows=packet.build(z,q,h.frame.w,h.frame.draw,h.frame.metadata_labels,h.audio,
        stored_guards=False,separate_prepare='idle',page_entry=video.PAGE)
    regions += [(packet.CODE,code),(packet.BRIDGE,bridge)]
    ccode,c,crows=video.build_clock(pl,h.audio,h.frames,zx0=z,progress_entry=h.progress['tick'],
        packet_ahead='idle',disk_idle_entry=q['step'])
    if c['end']>disk.DRIVER:raise ValueError('clock overlaps driver')
    drivercode,driver=disk.build_driver(h,c,bytes(ay),has_next=m['frame_end_exclusive']<count,
        prefill_entry=q['prefill'])
    regions += [(local.CODE,zcode),(producer.CODE,pcode),(disk.DISK,dcode),
        (disk.CACHED_SEEK,scode),(video.CODE,ccode),(disk.DRIVER,drivercode)]
    # Original packet/bridge bytes are known; only patch their differences.
    # Other regions are installed in full, including all mutable state.
    sparse=[]
    for base,blob in regions:
        for i,value in enumerate(blob):
            address=base+i
            if base in (packet.CODE,packet.BRIDGE,video.VIDEO) and h.cpu.read8(address)==value:continue
            sparse.append((address,value))
    if uncontended:
        from uncontended_frame import patches as frame_patches,CHECKPOINT_COPIES
        # Read the final packet/clock/queue image, not the original reader.
        image={a+i:v for a,blob in regions for i,v in enumerate(blob)}
        def read8(address):return image.get(address,h.cpu.read8(address))
        current_rows={pc:row for pc,row in h.frame.instructions.items()}
        current_rows.update({row['address']:row for row in rows})
        extra,audit=frame_patches(read8,current_rows.values())
        sparse=sorted(dict(sparse+extra).items())
        m.update(uncontended_frame=audit,fixture_checkpoint_copies=CHECKPOINT_COPIES)
    lab=dict(m['player_labels']);lab.update(driver)
    for name in ('disk_full_call','disk_return','fast_read_enter','fast_disk_return','fast_read_retry','disk_finish'):
        lab[name]=d[name]
    lab.update({name:seek[name] for name in ('seek_side_enter','seek_side_return','seek_enter','seek_return')})
    lab['zx0_fatal']=z['fatal']
    lab['publish_out']=vl['publish_out']
    m.update(player_labels=lab,disk_labels=d,decoder_labels=z,seek_labels=seek,deferred_labels={},
        packet_labels=pl,clock_labels=c,queue_labels=q,producer_labels=p,
        native_ready_pcs=[row['address']+3 for row in crows if row['instruction'] in ('CALL native zero','CALL draw_compact')],
        runtime_video_preload_sectors=0,slot_queue_fixture=True,release=False,
        slot_queue_patches=sparse,slot_queue_patch_sha256=sha(bytes(v for _,v in sparse)),
        slot_queue_regions=[dict(address=a,bytes=len(b),sha256=sha(b)) for a,b in regions],
        slot_queue_instruction_listing=qrows+prows+drows+srows+crows+vrows)
    return sparse,m
