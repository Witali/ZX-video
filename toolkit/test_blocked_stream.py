"""ZX0 reference/machine-code agreement and real-player block transitions."""
from pathlib import Path
import hashlib
import random
import tempfile
import unittest
from unittest.mock import patch

import blocked_stream
import disk_layout
import build_fast_sparse_trd as codec
import packed_stream
import zx0_codec
from validate_fast_sparse import CPU, validate_volume

# Produced by upstream ZX0 2.2 from 500 empty v7 frames. Exercises long Elias
# lengths, overlapping matches and an independently restarting second block.
EMPTY_COMPRESSED = bytes.fromhex('210a0039e851405d5556')
EMPTY_DECODED = (bytes((10,0))+bytes(10))*500


class BlockedStreamTests(unittest.TestCase):
    def test_heavy_frames_do_not_force_light_neighbors_to_be_stored(self):
        frames=[b'a'*3,b'b'*4,b'c',b'd'*8,b'e']
        captured=[]
        def inspect(groups,*args,stored_groups=()):
            captured.extend((data,count,index in stored_groups) for index,(data,count) in enumerate(groups))
            return groups
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(blocked_stream,'iter_compress_groups',side_effect=inspect):
                groups=blocked_stream.compress_frames(frames,Path('unused'),Path(directory),
                    max_block_bytes=8,store_over_bytes=3,separate_stored=True)
        self.assertEqual(b''.join(data for data,count in groups),b''.join(frames))
        self.assertEqual(captured,[(frame,1,len(frame)>3) for frame in frames])

    def test_cached_packets_preserve_both_bank_histories_at_every_boundary(self):
        rng=random.Random(437);state=bytearray(3840);states=[]
        for frame in range(10):
            for _ in range(80):state[rng.randrange(len(state))]=rng.randrange(256)
            states.append(bytes(state))
        sound=[bytes([i])*9 for i in range(len(states))]
        _,cached=codec.make_volume_packets(states,sound,0,0x100000,packed=True)
        for start in range(len(states)):
            for limit in (0,1,2,3):
                end,actual=codec.cached_volume_packets(states,sound,cached,start,max_frames=limit)
                expected_end,expected=codec.make_volume_packets(states,sound,start,0x100000,packed=True,max_frames=limit)
                self.assertEqual(end,expected_end)
                self.assertEqual([packed_stream.frame_bytes(p) for p in actual],
                                 [packed_stream.frame_bytes(p) for p in expected])

    def test_volume_planner_does_not_bank_reads_beyond_ring_capacity(self):
        idle=blocked_stream.Block(b'x',b'x',100,True,0)
        dense=blocked_stream.Block(bytes(6140),bytes(6140),3,True,0)
        queue=blocked_stream.planned_queue_after_block(320,idle,320,3,128)
        self.assertEqual(queue,320)
        accepted=0
        while True:
            next_queue=blocked_stream.planned_queue_after_block(queue,dense,320,3,128)
            if next_queue is None:break
            queue=next_queue;accepted+=1
        self.assertEqual(accepted,12)
        self.assertEqual(queue,140)
        self.assertEqual(blocked_stream.planned_queue_after_block(queue,idle,320,3,128),320)

    def test_large_frames_can_use_the_existing_stored_block_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(blocked_stream.subprocess,'run',side_effect=AssertionError('must not launch compressor')):
                blocks=blocked_stream.compress_frames([EMPTY_DECODED],Path('unused'),Path(directory),store_over_bytes=1800)
        self.assertEqual(len(blocks),1)
        self.assertTrue(blocks[0].stored)
        self.assertEqual(blocks[0].data,EMPTY_DECODED)

    def test_lazy_compression_stops_at_the_volume_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)
            (cache/(hashlib.sha256(EMPTY_DECODED).hexdigest()+'.zx0')).write_bytes(EMPTY_COMPRESSED)
            stream=blocked_stream.iter_compress_groups([(EMPTY_DECODED,500),(b'',0)],Path('unused'),cache)
            first=next(stream)
            self.assertEqual(first.data,EMPTY_COMPRESSED)
            self.assertEqual(first.decoded,EMPTY_DECODED)
            with self.assertRaises(ValueError):next(stream)

    def test_selected_block_limit_preserves_whole_frames(self):
        frames = [b'a'*3,b'b'*4,b'c',b'd'*8,b'e']
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(blocked_stream,'iter_compress_groups',side_effect=lambda groups,*a,**kw:groups):
                groups=blocked_stream.compress_frames(frames,Path('unused'),Path(directory),max_block_bytes=8)
                self.assertEqual(groups,[(b'aaabbbbc',3),(b'd'*8,1),(b'e',1)])
                self.assertEqual(b''.join(data for data,_ in groups),b''.join(frames))
                for limit in (0,8193):
                    with self.assertRaises(ValueError):
                        blocked_stream.compress_frames(frames,Path('unused'),Path(directory),max_block_bytes=limit)
                for invalid in ([b'x'*9],[b'']):
                    with self.assertRaises(ValueError):
                        blocked_stream.compress_frames(invalid,Path('unused'),Path(directory),max_block_bytes=8)

    def run_player(self, states, blocks, *, clocked=False, ay_states=None, stream_version=None, **player_options):
        ay = ay_states if ay_states is not None else [bytes(9)]*len(states)
        video = blocked_stream.serialize_volume(blocks,25/3,clocked=clocked)
        logical_bytes = len(video)
        boot = codec.streaming.build_boot_basic()
        provisional,_ = codec.build_player(0,0,blocked=True,clocked=clocked,**player_options)
        files = [codec.base.TrdFile('boot','B',boot,basic_variables_offset=len(boot),autostart_line=10),
                 codec.base.TrdFile('PLAYER','C',provisional,start=0x6000)]
        track,sector = codec.streaming.calculate_file_start(files)
        player,labels = codec.build_player(track,sector,blocked=True,clocked=clocked,**player_options)
        if player_options.get('interleaved'):
            version = stream_version if stream_version is not None else (10 if player_options.get('ay_noise') else 9)
            video = disk_layout.arrange(video[:4]+bytes([version])+video[5:],sector)
        files[1] = codec.base.TrdFile('PLAYER','C',player,start=0x6000)
        files.append(codec.base.TrdFile('VIDEO','C',video,start=0))
        trd,_,_ = codec.streaming.place_files(files,'BLOCK')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.trd'; path.write_bytes(trd)
            result = validate_volume(path,labels,states,ay,interrupt_every=701 if clocked else None)
        self.assertEqual(result['disk_bytes'],logical_bytes)
        if clocked: self.assertGreater(result['injected_interrupts'],100)
        if player_options.get('lookahead'):
            self.assertGreaterEqual(result['minimum_sp'],0x9D00 if player_options.get('uncontended') else 0x7D00)
        elif player_options.get('incremental'):
            self.assertGreaterEqual(result['minimum_sp'],0x7D80)
        elif player_options.get('irq_disk'):
            self.assertGreater(result['minimum_sp'],0xBF00)

    def test_reference_and_both_upstream_decoders(self):
        self.assertEqual(zx0_codec.decompress(EMPTY_COMPRESSED),EMPTY_DECODED)
        for variant in ('standard','turbo'):
            a = codec.base.MiniAssembler(0x6000)
            zx0_codec.emit_decoder(a,variant)
            cpu = CPU(a.resolve(),b'')
            cpu.set_hl(0xA000); cpu.set_de(0x8000); cpu.push(0x5F00)
            for i,value in enumerate(EMPTY_COMPRESSED): cpu.write8(0xA000+i,value)
            while cpu.pc != 0x5F00:
                self.assertLess(cpu.steps,100000)
                cpu.step()
            self.assertEqual(bytes(cpu.banks[2][:len(EMPTY_DECODED)]),EMPTY_DECODED)

    def test_two_blocks_share_one_disk_sector(self):
        block = blocked_stream.Block(EMPTY_COMPRESSED,EMPTY_DECODED,500,False,0)
        self.run_player([bytes(3840)]*1000,[block,block])

    def test_irq_during_decompression_preserves_registers(self):
        block = blocked_stream.Block(EMPTY_COMPRESSED,EMPTY_DECODED,500,False,0)
        self.run_player([bytes(3840)]*1000,[block,block],clocked=True)

    def test_uncompressed_fallback_with_dense_frames(self):
        rng = random.Random(7)
        states = [rng.randbytes(3840) for _ in range(4)]
        _,packets = codec.make_volume_packets(states,[bytes(9)]*4,0,2530,packed=True)
        frames = [packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks = [blocked_stream.Block(frame,frame,1,True,0) for frame in frames]
        self.run_player(states,blocks)

    def test_fast_drawing_and_deadline_clock_with_irq_stress(self):
        rng = random.Random(83)
        states = [rng.randbytes(3840) for _ in range(4)]
        _,packets = codec.make_volume_packets(states,[bytes(9)]*4,0,2530,packed=True)
        frames = [packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks = [blocked_stream.Block(frame,frame,1,True,0) for frame in frames]
        self.run_player(states,blocks,clocked=True,deadline=True,fast_disk=True,
                        irq_disk=True,interleaved=True,fast_draw=True)

    def test_corrupt_stream_is_rejected_by_reference(self):
        for data in (EMPTY_COMPRESSED[:-1],EMPTY_COMPRESSED+b'\0',b'\0'):
            with self.assertRaises(ValueError): zx0_codec.decompress(data)


if __name__ == '__main__': unittest.main()
