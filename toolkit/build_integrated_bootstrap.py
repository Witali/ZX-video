"""Rebuild exact three-volume payloads with the integrated slot bootstrap.

Cold boots and disk swaps use real opcodes with mocked ROM reads. They do
not prove disk latency, AY cadence, complete pixels or publication deadlines.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
import fap3_disk_z80 as disk
from integrated_bootstrap import Builder
from measure_volume_huffman import identify
from test_fap3_disk import DiskCPU,verify_swaps
from test_warm_continuation import player,until


def check_cold(image,m,banks):
    cpu = DiskCPU(player(image),image)
    # Deliberately dirty all RAM except the loaded PLAYER and ROM workspace.
    for bank in (0,1,2,3,4,6,7): cpu.banks[bank][:] = b'\xa7'*16384
    cpu.banks[5][:6912] = b'\xa7'*6912
    cpu.banks[5][0x2400:] = b'\xa7'*(16384-0x2400)
    until(cpu,disk.DRIVER)
    checked = []
    for s in m['sections']:
        lo = s['address'] & 16383; hi = lo+s['decoded_bytes']
        if s['bank'] == 5 and s['address'] == 0x6400:
            lo = 0x7600 & 16383 # packet window is documented disposable staging
        actual = bytes(cpu.banks[s['bank']][lo:hi]); expected = bytes(banks[s['bank']][lo:hi])
        if actual != expected:
            at = next(i for i,(a,b) in enumerate(zip(actual,expected)) if a != b)
            raise AssertionError(('cold RAM differs',m['part'],s['bank'],hex(lo+at),actual[at],expected[at]))
        checked.append(dict(bank=s['bank'],offset=lo,bytes=len(actual),sha256=sha(actual)))
    for source,target in ((0xa100,0x6000),(0xa200,0x6100)):
        if bytes(cpu.read8(target+i) for i in range(256)) != bytes(cpu.read8(source+i) for i in range(256)):
            raise AssertionError('startup overlay differs')
    if cpu.dos_reads != sum(s['sectors'] for s in m['sections']):
        raise AssertionError('unexpected bootstrap video preload')
    return dict(cold_sections=checked,mocked_boot_tstates=cpu.tstates,
                boot_sectors=cpu.dos_reads,dirty_ram_boot_exact=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('directory','raw-directory','states','zx0','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--bank2-zx0',action='store_true')
    p.add_argument('--audio-wait-prefetch',action='store_true')
    p.add_argument('--ready-packet-guard',action='store_true')
    p.add_argument('--fast-return-irq',action='store_true')
    args = p.parse_args()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    inputs = [disk_blocks(args.directory,part) for part in (1,2,3)]
    ends = [m['frame_end_exclusive'] for m,_,_ in inputs]
    if ends[-1] != len(states) or [m['frame_start'] for m,_,_ in inputs] != [0]+ends[:-1]:
        raise ValueError('incomplete input partition')
    keys = ('fast_disk','cached_seek','interleaved','deferred_limit','keepalive_fields','frame_service',
            'cold_bitmaps','inline_matches','startup_delta','fast_noop_scan','irq_safe_paging',
            'static_cache_borders','carry_huffman','register_fragments','cached_huffman_byte')
    options = {k:inputs[0][0][k] for k in keys}
    raws = [(args.raw_directory/f'volume-{i}.raw').read_bytes() for i in (1,2,3)]
    for (m,_,_),raw in zip(inputs,raws):
        if any(m[k] != options[k] for k in keys): raise ValueError('different baseline options')
        if sha(raw) != m['raw_sha256'] or sha(states.tobytes()) != m['states_sha256']:
            raise ValueError('wrong input hash')
    contract = dict(version='integrated-slot-1',ends=ends,options=options,
                    raw_sha256=list(map(sha,raws)),states_sha256=sha(states.tobytes()))
    if args.bank2_zx0:options['bank2_zx0']=True
    if args.audio_wait_prefetch:options['audio_wait_prefetch']=True
    if args.ready_packet_guard:options['ready_packet_guard']=True
    if args.fast_return_irq:options['fast_return_irq']=True
    fingerprint = b'FAP3ZXV1'+bytes.fromhex(sha(json.dumps(contract,sort_keys=True).encode()))[:6]
    args.output.mkdir(parents=True,exist_ok=True); args.report.parent.mkdir(parents=True,exist_ok=True)
    report = dict(complete=False,release=False,scope=__doc__,baseline_commit='4ccd740',
                  contract=contract,volumes=[])
    def save(): args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    records = [];save()
    for part,((old,stream,blocks),raw) in enumerate(zip(inputs,raws),1):
        print(f'Build integrated bootstrap: part {part}',flush=True)
        b = Builder(raw,states,args.zx0.resolve(),args.output/'zx0',**options)
        b.read_cache = [args.directory/'zx0']; b.ends = ends
        b.memo.update({sha(decoded):payload for payload,decoded in blocks})
        image,m = b.volume(old['frame_start'],old['frame_end_exclusive'],part)
        row = dict(part=part,baseline_trd_sha256=old['trd_sha256'],baseline_used_sectors=old['used_sectors'],
                   used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],fits=image is not None,
                   video_start_sector=m['video_start_sector'],video_sectors=m['video_sectors'],
                   sections=m['sections'],inline_huffman=m['inline_huffman_patches'])
        if args.bank2_zx0:row['bank2_zx0']=m['bank2_zx0']
        if args.audio_wait_prefetch:row['audio_wait_prefetch']=m['audio_wait_prefetch']
        if args.ready_packet_guard:row['ready_packet_guard']=m['ready_packet_guard']
        if args.fast_return_irq:row['fast_return_irq']=m['fast_return_irq']
        report['volumes'].append(row);save()
        if image is None:
            print(json.dumps({k:v for k,v in row.items() if k not in ('sections','inline_huffman')}),flush=True)
            continue
        image = identify(image,m,fingerprint); stem = f'ZX-video-huffman-preview_part{part:02}'
        (args.output/(stem+'.trd')).write_bytes(image)
        (args.output/(stem+'.json')).write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
        _,new_stream,_ = disk_blocks(args.output,part)
        if new_stream != stream or m['blocks'] != old['blocks']: raise AssertionError('compressed movie changed')
        row.update(check_cold(image,m,b.expected_banks),trd_sha256=sha(image),stream_sha256=sha(stream),
                   compressed_stream_exact=True,independently_bootable=m['independently_bootable'])
        records.append(dict(part=part,file=stem+'.trd',metadata=stem+'.json',sha256=sha(image),
                            frame_start=m['frame_start'],frame_end_exclusive=m['frame_end_exclusive']))
        save(); print(json.dumps({k:v for k,v in row.items() if k not in ('sections','inline_huffman','cold_sections')}),flush=True)
    if len(records) == 3:
        (args.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        verify_swaps(args.output,args.output/'swaps.json')
        report.update(complete=True,mocked_rom_swaps=json.loads((args.output/'swaps.json').read_text()))
    report['source_sha256'] = {name:sha(Path(__file__).with_name(name).read_bytes()) for name in
        ('build_integrated_bootstrap.py','integrated_bootstrap.py','build_fap3_trd.py','fap3_disk_z80.py')}
    if args.bank2_zx0:
        report['source_sha256'].update({name:sha(Path(__file__).with_name(name).read_bytes()) for name in
            ('bank2_zx0.py','bank_local_zx0.py')})
    if args.audio_wait_prefetch:report['source_sha256']['audio_wait_prefetch.py']=sha(Path(__file__).with_name('audio_wait_prefetch.py').read_bytes())
    if args.ready_packet_guard:report['source_sha256']['ready_packet_guard.py']=sha(Path(__file__).with_name('ready_packet_guard.py').read_bytes())
    if args.fast_return_irq:report['source_sha256']['fast_return_irq.py']=sha(Path(__file__).with_name('fast_return_irq.py').read_bytes())
    save()


if __name__ == '__main__': main()
