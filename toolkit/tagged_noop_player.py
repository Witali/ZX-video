"""Optional lossless run-tag format on the retained resident-AY player.

The disk-set identity must differ from the untagged format. Its original
FAP3 source stays unchanged; only separated runtime video receives tags.
"""
import struct
from build_fap3_trd import sha, padded, sectors
from inplace_keepalive_player import Builder as PreviousBuilder
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
import tagged_noop_runs as tags


def transcode_video(source, minimum=4, *, inverse=False):
    r=Reader(source); result=bytearray()
    while r.pos<len(source):
        length=r.u16(); body=r.take(length)
        if length<288: raise ValueError('short video-only packet')
        masks_size=int.from_bytes(body[1:3],'little')
        masks=restore(body[200:200+masks_size],1,480,4)[:384]
        vectors=body[8:200]
        replacement=(tags.decode_vectors(vectors,masks,inplace=True)[0] if inverse
                     else tags.encode(vectors,masks,minimum))
        result+=struct.pack('<H',length)+body[:8]+replacement+body[200:]
    r.end()
    return bytes(result)


class Builder(PreviousBuilder):
    def __init__(self,*args,minimum_run=4,**kwargs):
        super().__init__(*args,**kwargs)
        self.minimum_run=minimum_run; self.tagged_streams={}

    def separated(self,start,end):
        key=start,end
        if key not in self.tagged_streams:
            video,sound=super().separated(start,end)
            tagged=transcode_video(video,self.minimum_run)
            if transcode_video(tagged,inverse=True)!=video: raise AssertionError('video inverse differs')
            self.tagged_streams[key]=(tagged,sound)
        return self.tagged_streams[key]

    def ram(self,start,end,next_sector,remaining):
        sections,m=super().ram(start,end,next_sector,remaining); banks=self.expected_banks
        def bank_at(at): return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at,code):
            if (at&16383)+len(code)>16384: raise ValueError('cross-bank run-tag patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(code)]=code
        reference=m['cached_huffman_lookahead']['implementation']
        report=tags.build(read8,reference['listing'],reference['labels'])
        put(tags.CODE,bytes.fromhex(report['code_hex']))
        put(report['hook_address'],bytes.fromhex(report['hook_hex']))
        m['tagged_noop_runs']=dict(report,enabled=True,minimum_run=self.minimum_run,
            original_video_sha256=sha(self.resident_streams[start,end][0]),
            tagged_video_sha256=sha(self.separated(start,end)[0]),
            exact_packet_inverse=True,format='positional-interior-runs-v1')
        result=[]
        for section in sections:
            at=section['address']&16383; raw=bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded=self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m
