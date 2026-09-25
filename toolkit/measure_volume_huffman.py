"""Build one coherent independently bootable set and cold-play every TRD.

Per-volume FAP3 sources have different hashes. Assign a common set identity
derived from all sources, states, boundaries and build options. Only the
16-byte reserved disk ID and the bootstrap's 16-byte next-ID constant change;
all executable instructions, sections and video data remain untouched.
Full Fuse timing remains separate from the isolated Huffman cost experiment.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

from build_fap3_trd import sha
import fap3_disk_z80 as disk
from profile_fap3 import summarize_fuse
from probe_startup_tables import undifference
from run_deferred_disk import ReadThroughBuilder
from test_fap3_disk import DiskCPU, verify_swaps
from test_warm_continuation import player, until
from zx0_codec import decompress


def identify(image, meta, fingerprint):
    if len(fingerprint) != 14: raise ValueError('expected 14-byte set identity')
    old = bytes.fromhex(meta['disk_id_hex']); part = meta['part']
    next_at = 17*256+meta['bootstrap_labels']['next_id']-0x6000
    if not 17*256 <= next_at <= 21*256-16: raise ValueError('next ID outside PLAYER')
    if image[15*256:15*256+16] != old or image[next_at:next_at+16] != old[:14]+struct.pack('<H',part+1):
        raise AssertionError('original identity constants differ')
    result = bytearray(image)
    result[15*256:15*256+16] = fingerprint+struct.pack('<H',part)
    result[next_at:next_at+16] = fingerprint+struct.pack('<H',part+1)
    if any(a != b for i,(a,b) in enumerate(zip(image,result))
            if not (15*256 <= i < 15*256+16 or next_at <= i < next_at+16)):
        raise AssertionError('identity update changed other disk bytes')
    image = bytes(result)
    meta.update(disk_id_hex=(fingerprint+struct.pack('<H',part)).hex(),trd_sha256=sha(image),
        entropy_set_identity=True,identity_instruction_delta_tstates=0)
    return image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('probe','partition','directory','states','zx0','fuse','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--fast-noop-scan',action='store_true',help='Compare combined scanner with the saved original layout')
    p.add_argument('--irq-safe-paging',action='store_true',help='Restart bank changes interrupted by publication; no DI')
    args = p.parse_args();probe = json.loads(args.probe.read_text());partition = json.loads(args.partition.read_text())
    if not probe['complete'] or not partition['complete'] or not partition['all_fit']:
        raise ValueError('requires completed fitting storage experiment')
    if partition['probe_raw_sha256'] != probe['raw_sha256']: raise ValueError('partition source differs')
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    if sha(states.tobytes()) != probe['states_sha256']: raise ValueError('states differ')
    ends = partition['selected']['ends']; sources = []
    if not ends or ends != sorted(set(ends)) or ends[0] <= 0 or ends[-1] != len(states):
        raise ValueError('partition must cover every frame exactly once')
    for i in range(1,len(ends)+1):
        v = next(v for v in probe['variants'] if v['name'] == f'volume-{i}')
        path = args.directory/v['raw_file'];raw = path.read_bytes()
        if sha(raw) != v['raw_sha256']: raise ValueError('candidate differs')
        sources.append((path,raw))
    options = dict(fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True,startup_delta=True)
    if args.fast_noop_scan: options['fast_noop_scan']=True
    if args.irq_safe_paging: options['irq_safe_paging']=True
    contract = dict(version='standalone-huffman-1',raw_sha256=[sha(raw) for _,raw in sources],
        states_sha256=probe['states_sha256'],ends=ends,options=options)
    contract_sha = sha(json.dumps(contract,sort_keys=True).encode())
    fingerprint = b'FAP3ZXV1'+bytes.fromhex(contract_sha)[:6]
    args.output.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    variant = dict(name='individual',complete=False,volumes=[])
    report = dict(complete=False,release=False,contract=contract,contract_sha256=contract_sha,
        storage_baseline_commit='53d7a1e',frames=len(states),ends=ends,
        full_pixel_comparison=False,pixel_samples_per_frame=80,physical_drive_verified=False,
        variants=[variant],all_independently_bootable=True)
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n')
    records = [];save()
    for part,(start,end) in enumerate(zip([0]+ends,ends),1):
        path,raw = sources[part-1]
        builder = ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',**options)
        builder.read_cache = [args.directory/'zx0']+args.read_cache;builder.ends = ends
        image,m = builder.volume(start,end,part)
        if image is None or not m['independently_bootable']: raise ValueError('volume not standalone or overfull')
        if not (args.fast_noop_scan or args.irq_safe_paging) and m['used_sectors'] != partition['selected']['used_sectors'][part-1]:
            raise AssertionError('partition size changed')
        image = identify(image,m,fingerprint);m['entropy_set_contract_sha256'] = contract_sha
        trd = args.output/f'ZX-video-huffman-preview_part{part:02}.trd';metadata = trd.with_suffix('.json')
        trd.write_bytes(image);metadata.write_text(json.dumps(m,indent=2)+'\n')
        records.append(dict(part=part,file=trd.name,metadata=metadata.name,frame_start=start,
            frame_end_exclusive=end,sha256=sha(image)))
        cpu = DiskCPU(player(image),image);until(cpu,disk.DRIVER)
        section = next(s for s in m['sections'] if s['bank'] == 6);at = section['sector']*256
        table = decompress(image[at:at+section['compressed_bytes']],limit=16384)
        if section.get('startup_delta'): table = undifference(table)
        if sha(table) != section['sha256'] or bytes(cpu.banks[6]) != table: raise AssertionError('cold table restoration differs')
        target = args.output/f'fuse_part{part:02}.json'
        print(f'Complete independent Fuse boot: part {part}, {end-start} frames',flush=True)
        subprocess.run([sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse',str(args.fuse.resolve()),'--trd',str(trd.resolve()),'--metadata',str(metadata.resolve()),
            '--raw',str(path.resolve()),'--states',str(args.states.resolve()),'--output',str(target.resolve()),
            '--timeout',str(args.timeout)],check=True)
        data = json.loads(target.read_text());timing = summarize_fuse(data)
        for key in ('missed_nominal_frame_indices','publication_intervals_tstates','late_runs'): timing.pop(key)
        pubs = data['publications']
        timing.update(actual_fps=(len(pubs)-1)*3546900/(pubs[-1]['tstate']-pubs[0]['tstate']),
            recovered_late_runs=sum(r['recovered_at'] is not None for r in data['late_runs']),
            unrecovered_late_runs=sum(r['recovered_at'] is None for r in data['late_runs']))
        row = dict(part=part,frames=end-start,used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],
            video_bytes=m['video_bytes'],trd_sha256=sha(image),independently_bootable=True,
            cold_table_all_bytes_exact=True,boot_mocked_tstates=cpu.tstates,
            fast_noop_scan=args.fast_noop_scan,
            irq_safe_paging=args.irq_safe_paging,
            read_attempts=data['read_attempts'],fast_read_retries=data['fast_read_retries'],
            full_report=target.name,timing=timing)
        variant['volumes'].append(row);save();print(json.dumps(row),flush=True)
    (args.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n')
    swaps = args.output/'swaps.json';verify_swaps(args.output,swaps)
    report['mocked_rom_swaps'] = json.loads(swaps.read_text())
    if sum(v['frames'] for v in variant['volumes']) != len(states): raise AssertionError('partial movie')
    variant['complete'] = True;report['complete'] = True;save()


if __name__ == '__main__': main()
