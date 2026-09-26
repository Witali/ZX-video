"""Build the measured slot player into independently bootable TRDs.

Experimental: preserves the exact movie packets and makes no deadline claim.
The legacy builder stays the default. No debugger writes or retained RAM are
needed. Empty slots are filled by the player's normal prefill before its clock.
"""
from build_fap3_trd import padded, player_harness, sectors, sha
from build_zxv_trd import MiniAssembler,TrdFile
import fap3_disk_z80 as disk
import inline_huffman_patches as inline
from prefix_huffman_z80 import prepare
from probe_startup_tables import undifference
from run_deferred_disk import ReadThroughBuilder
import slot_queue_player
from uncontended_frame import RANGES
from zx0_codec import decompress

INSTALL = 0xdb00


def installer():
    """Two startup-only overlays; 2*(30+21*256-5)+10 = 10812 T."""
    a = MiniAssembler(INSTALL)
    for source, target in ((0xa100, disk.DISK), (0xa200, 0x6100)):
        a.emit(0x21); a.word(source); a.emit(0x11); a.word(target)
        a.emit(0x01); a.word(256); a.emit(0xed, 0xb0)
    a.emit(0xc3); a.word(disk.DRIVER)
    if a.pc > 0xdc00: raise ValueError('overlay installer overlaps packet code')
    return a.resolve()


class Builder(ReadThroughBuilder):
    preload_sectors = 0

    def __init__(self, *args, bank2_zx0=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.bank2_zx0=bank2_zx0
        if (self.warm_continuation or not self.fast_disk or not self.cached_seek or
            not self.interleaved or not self.irq_safe_paging or not self.cached_huffman_byte):
            raise ValueError('integrated mode requires independent cached-Huffman/interleaved fast-disk options')

    def bootstrap(self, sections, video_sector, ns, next_id, start):
        return disk.build_bootstrap(sections, video_sector, ns, next_id=next_id,
            interleaved=True, preload_sectors=0, runtime_entry=INSTALL)

    def place_sections(self, sections, position):
        payload=bytearray()
        for s in sections:
            offset=len(payload)%256
            s.update(sector=position+len(payload)//256,source_offset=offset,
                     sectors=(offset+s['compressed_bytes']+255)//256)
            capacity=6912 if s['buffer']==0x4000 else 4608
            if s['sectors']*256>capacity:raise ValueError('pooled startup input exceeds staging')
            payload.extend(s['data'][:s['compressed_bytes']])
        # A boundary sector may be reread during bootstrap; runtime video
        # sectors remain read exactly once by the existing interleaved reader.
        return [TrdFile('INIT','C',padded(bytes(payload)))],position+sectors(payload)

    def ram(self, start, end, next_sector, remaining):
        old_sections, m = super().ram(start, end, next_sector, remaining)
        banks = [bytearray(16384) for _ in range(8)]
        for s in old_sections:
            raw = decompress(s['data'][:s['compressed_bytes']], limit=s['decoded_bytes'])
            if s.get('startup_delta'): raw = undifference(raw)
            if sha(raw) != s['sha256']: raise AssertionError('base RAM hash mismatch')
            at = s['address'] & 16383
            banks[s['bank']][at:at+len(raw)] = raw

        def bank_at(address): return 5 if address < 0x8000 else 2 if address < 0xc000 else 7
        def read8(address): return banks[bank_at(address)][address & 16383]
        def put(address, data, bank=None):
            target = banks[bank_at(address) if bank is None else bank]; at = address & 16383
            if at+len(data) > 16384: raise ValueError('cross-bank write')
            target[at:at+len(data)] = data

        _, blocks = self.stream(start, end)
        m.update(frame_start=start, frame_end_exclusive=end, frames=end-start,
            video_start_sector=next_sector, video_sectors=remaining, blocks=blocks,
            raw_sha256=sha(self.raw), independently_bootable=True,
            **{key:getattr(self,key) for key in ('inline_matches','fast_noop_scan','irq_safe_paging',
                'static_cache_borders','carry_huffman','register_fragments','cached_huffman_byte')})
        patches, m = slot_queue_player.build(m,self.raw,uncontended=True,compiled_masks=True,
            inline_literals=True,demand_decode=True)
        # Move initial data on the host, not at every Spectrum cold start.
        relocated = [(dest,bytes(read8(i) for i in range(lo,hi))) for lo,hi,dest in RANGES]
        for address,data in relocated: put(address,data)
        for address,value in patches: put(address,bytes([value]))

        h = player_harness(bytes(4),self.tables,self.mapping,end-start,
            **{key:getattr(self,key) for key in ('inline_matches','fast_noop_scan','irq_safe_paging',
                'static_cache_borders','carry_huffman','register_fragments','cached_huffman_byte')})
        table_bytes = prepare(self.tables,self.mapping,carry_huffman=True)['body_bytes']
        # An unrelated video's larger trees may require the shared routine.
        if 0xc000+table_bytes <= inline.ORIGIN:
            code, report = inline.build(read8,h.frame.instructions.values(),h.frame.recon,table_bytes)
            if any(banks[6][inline.ORIGIN & 16383:(inline.ORIGIN & 16383)+len(code)]):
                raise ValueError('inline code would overwrite a nonempty table tail')
            put(inline.ORIGIN,code,6)
            put(report['redirect_address'],bytes.fromhex(report['redirect_bytes']))
            m['inline_huffman_patches'] = dict(report,enabled=True)
        else:
            m['inline_huffman_patches'] = dict(enabled=False,reason='table tail too large',table_body_bytes=table_bytes)
        old_decoder_end=m['decoder_labels']['end']
        if self.bank2_zx0:
            from bank2_zx0 import install_player
            m['bank2_zx0']=install_player(read8,put,m,h)
        # Both low overlays must survive until all decompression has finished.
        put(0xa100,bytes(read8(i) for i in range(0x6000,0x6100)))
        put(0xa200,bytes(read8(i) for i in range(0x6100,0x6200)))
        code = installer()
        # The old ring reader at DB00 is replaced completely by slot_queue.
        import stream_reader_z80
        if stream_reader_z80.CODE != INSTALL or h.r['end'] > 0xdc00:
            raise ValueError('retired ring-reader layout changed')
        m['retired_ring_reader_sha256'] = sha(bytes(read8(i) for i in range(INSTALL,0xdc00)))
        put(INSTALL,bytes(0xdc00-INSTALL))
        put(INSTALL,code)
        # The bootstrap restores already initialized RAM, and the packet
        # parser calls compiled masks in bank 7. Neither old entry is used.
        import frame_output_pipeline as pipeline
        retired = [(h.frame.metadata_labels['decode'],h.frame.metadata_labels['end']),
                   (pipeline.INITIALIZER,pipeline.INITIALIZER+len(h.frame.init_code))]
        m['retired_fixed_code'] = []
        for lo,hi in retired:
            m['retired_fixed_code'].append(dict(start=lo,end=hi,sha256=sha(bytes(read8(i) for i in range(lo,hi)))))
            put(lo,bytes(hi-lo))
        # Old ring decoder/loader tails left beyond the shorter replacements.
        for lo,hi in ((old_decoder_end,0x7d50),(m['producer_labels']['end'],0x7f00)):
            if lo > hi: raise ValueError('producer or decoder overlaps its successor')
            put(lo,bytes(hi-lo))
        # All but the last section use the visible bitmap as temporary input.
        # The last restores that bitmap, using only the future packet window.
        layout = [(6,0xc000,16384,0x4000),(2,0x8000,16384,0x4000),
                  (7,0xc000,0x2400,0x4000),
                  (5,0x6400,7168,0x4000),(5,0x4000,6912,0x6400)]
        sections = []
        for bank,address,length,buffer in layout:
            raw = bytes(banks[bank][address & 16383:(address & 16383)+length])
            packed = self.compress(raw); storage = raw; filtered = False
            baseline_bytes = len(packed)
            if self.startup_delta and bank == 6:
                delta = raw[:1]+bytes((b-a)&255 for a,b in zip(raw,raw[1:]))
                candidate = self.compress(delta)
                if sectors(candidate) < sectors(packed):
                    packed,storage,filtered = candidate,delta,True
            capacity = 6912 if buffer == 0x4000 else 4608
            if len(padded(packed)) > capacity: raise ValueError(('startup staging overflow',bank,address,len(packed)))
            section = dict(bank=bank,address=address,buffer=buffer,sectors=sectors(packed),
                decoded_bytes=len(raw),compressed_bytes=len(packed),sha256=sha(raw),data=padded(packed))
            if filtered: section.update(startup_delta=True,storage_sha256=sha(storage),
                baseline_compressed_bytes=baseline_bytes,restore_tstates=541426)
            sections.append(section)
        m.update(integrated_slot_queue=True,slot_queue_fixture=False,fixture_checkpoint_copies=[],
            bootstrap_video_preload_sectors=0,runtime_video_preload_sectors=0,initial_cached_track=255,
            startup_overlay_entry=INSTALL,startup_overlay_bytes=len(code),startup_overlay_tstates=10812,
            checkpoint_runtime_copy_tstates=0,checkpoint_copy_saved_tstates=102194,
            bootstrap_packet_staging=[0x6400,0x7600],release=False)
        m.update(decoder_end=m['decoder_labels']['end'],clock_end=m['clock_labels']['end'],
                 driver_end=m['player_labels']['end'])
        m.pop('slot_queue_patches',None)
        self.expected_banks = banks
        return sections,m
