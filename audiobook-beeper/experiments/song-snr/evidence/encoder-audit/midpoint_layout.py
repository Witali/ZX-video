"""Read-only exact source-independent memory feasibility; no new TRD proof."""
import gzip,json
from pathlib import Path
from direct_player import layout
from build_stream_trd import sections
from general import models
r=Path('audiobook-beeper/experiments/song-snr/evidence')
old=json.loads((r/'prototype/sea_foam/player.json').read_bytes());labels=old['player_labels']
packed=gzip.decompress((r/'general/inputs/sea_foam.ima.gz').read_bytes())
model=dict(dict(models())['duration_midpoint'],extended_ram=True)
words,nxt,states,first,second,pointers,pages,rows,*_=layout(packed[:256],model,old['hot_indices'],resident_limit=16384)
resident_end=pointers+256+1024+17*64
startup_end=labels['startup_end'];startup_bytes=min(first.values())-startup_end
probe_bytes=labels['stream_cold_start']-labels['cache_map']
bounce_bytes=labels['stream_worker_end']-labels['stream_bounce']
old_records=labels['stream_bounce']-labels['stream_records']
fixed_remaining=labels['stream_worker_end']-labels['cache_map']-probe_bytes-bounce_bytes-old_records
limits=[]
for audio_sectors in (old['audio_sectors'],2392):
 allocation,remaining=sections(audio_sectors*256,56);assert remaining==0
 record_slots=len(allocation)+1;records_bytes=record_slots*3+1
 worker_end=resident_end+fixed_remaining+records_bytes
 limits.append(dict(audio_sectors=audio_sectors,sections=len(allocation),record_slots=record_slots,record_bytes=records_bytes,worker_bytes=fixed_remaining+records_bytes,worker_end=worker_end,worker_end_hex=hex(worker_end),free_before_forced_final_byte=0xbfff-worker_end))
assert len(states)<=18
assert startup_bytes>=probe_bytes+bounce_bytes
assert all(row['worker_end']<=0xbfff for row in limits)
report=dict(date='2026-10-14',scope='Read-only arithmetic using complete universal table closure and existing assembled code sizes. No new assembly, native execution, Fuse or physical-hardware verification.',model=model,feedback_states=len(states),first_patterns=len(first),second_patterns=len(second),first_base=min(first.values()),table_pointers=pointers,resident_end=resident_end,resident_end_hex=hex(resident_end),old_startup_end=startup_end,startup_padding_bytes=startup_bytes,move_to_startup_probe_bytes=probe_bytes,move_to_startup_bounce_bytes=bounce_bytes,startup_remaining_bytes=startup_bytes-probe_bytes-bounce_bytes,remaining_fixed_worker_bytes=fixed_remaining,cases=limits,hot_path_tstate_delta=0,ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},requirements=['Keep all 311 bytes of map/restore/alias/detect in fixed-bank2 startup padding. They remain present for refills.','Keep the 256-byte bounce in separate startup padding after probe code; do not overlay live code or place it in bank5/TR-DOS workspace.','Place worker at exact 64-byte-aligned resident_end BC40, without 256-byte rounding.','Assert startup area end<=FIRSTbase, universal feedback states<=18 and worker_end<=BFFF at maximum 2392 audio sectors.','Teach guards/verifiers the relocated mutable bounce address, then perform whole coldload/native/Fuse verification on all claimed profiles/refills.','Preserve actual timing and independently bootable disks. This arithmetic is feasibility only.'])
print(json.dumps(report,indent=2))
Path('.tmp/audit/midpoint-layout.json').write_text(json.dumps(report,indent=2)+'\n')
