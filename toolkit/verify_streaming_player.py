"""Check cold-installed streaming code, old streams, capacity and source hashes."""
import argparse
import json
from pathlib import Path
from benchmark_bank_local_zx0 import disk_blocks,sha
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until
import fap3_disk_z80 as disk
import streaming_zx0_layout as decoder
import streaming_slot_input as producer
import streaming_slot_queue as queue


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True,type=Path)
    p.add_argument('--report',default=Path('toolkit/streaming_player_build.json'),type=Path)
    a=p.parse_args();report=json.loads(a.report.read_bytes());root=Path(__file__).parent
    if not report['complete'] or len(report['volumes'])!=3:raise ValueError('incomplete build')
    for name,digest in report['source_sha256'].items():
        if sha((root/name).read_bytes())!=digest:raise ValueError(('changed build source',name))
    reference=json.loads((root/'hl_mask_reader_summary.json').read_bytes())
    for part in (1,2,3):
        m,stream,blocks=disk_blocks(a.directory,part);built=report['volumes'][part-1]
        if (not m['streaming_input']['enabled'] or not m['independently_bootable'] or
            not m['integrated_slot_queue'] or m['slot_queue_fixture'] or m['used_sectors']>2544 or
            m['trd_sha256']!=built['trd_sha256'] or sha(stream)!=reference['volumes'][part-1]['hl']['stream_sha256']):
            raise ValueError('wrong stream/build/independent disk')
        regions,z,layout=decoder.build();pregions,pl,pr=producer.build(z,m['disk_labels'],layout['helper_end'])
        qregions,ql,qr=queue.build(z,pl,len(blocks),demand_decode=True)
        if z!=m['decoder_labels'] or pl!=m['producer_labels'] or ql!=m['queue_labels']:raise ValueError('labels differ')
        expected=[dict(address=at,bytes=len(data),code_hex=data.hex(),sha256=sha(data)) for at,data in regions+pregions+qregions]
        if expected!=m['streaming_input']['regions'] or layout!=m['streaming_input']['layout']:
            raise ValueError('regenerated streaming bytes differ')
        image=(a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        c=DiskCPU(player(image),image);until(c,disk.DRIVER)
        for region in expected:
            blob=bytes.fromhex(region['code_hex']);at=region['address']
            if bytes(c.read8(at+i) for i in range(len(blob)))!=blob:raise ValueError(('cold code differs',hex(at)))
        for change in m['streaming_input']['external_operands']:
            at=change['operand_address']
            if c.read8(at)+256*c.read8(at+1)!=change['new']:raise ValueError('retained caller differs')
        # Ensure the previously accepted AY helper/IM2 fix and inline masks
        # survived, including the one-byte retired-body boundary.
        for key,address_key,hex_key in (('audio_wait_prefetch','origin','code_hex'),
                                       ('audio_wait_prefetch','hook_address','hook_hex'),
                                       ('fast_return_irq','hook_address','hook_hex')):
            change=m[key];at=change[address_key];blob=bytes.fromhex(change[hex_key])
            if bytes(c.read8(at+i) for i in range(len(blob)))!=blob:raise ValueError(('previous optimization changed',key))
        if c.read8(decoder.LIMIT)!=0xc9 or c.dos_reads!=sum(s['sectors'] for s in m['sections']):
            raise ValueError('retained RET or bootstrap read count differs')
        print(f'part {part}: stream exact, {m["used_sectors"]}/2544 sectors, {sum(len(bytes.fromhex(r["code_hex"])) for r in expected)} streaming bytes cold-verified',flush=True)


if __name__=='__main__':main()
