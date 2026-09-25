"""Experimental ZX0 block-grid phase; packet bytes and decoder ABI stay fixed."""
import struct
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder

BLOCK_SIZE=8192


def ranges(start,end,phase):
    if not 0<=phase<BLOCK_SIZE or not 0<=start<end:
        raise ValueError('invalid block range or phase')
    while start<end:
        stop=min(end,((start-phase)//BLOCK_SIZE+1)*BLOCK_SIZE+phase)
        if not 1<=stop-start<=BLOCK_SIZE:raise AssertionError('block outside slot capacity')
        yield start,stop
        start=stop


class Builder(ReadThroughBuilder):
    def __init__(self,*args,block_phase=0,**kwargs):
        if not 0<=block_phase<BLOCK_SIZE:raise ValueError('invalid phase')
        super().__init__(*args,**kwargs)
        self.block_phase=block_phase

    def stream(self,start,end):
        result=bytearray();blocks=[]
        for lo,stop in ranges(self.offsets[start],self.offsets[end],self.block_phase):
            raw=self.stream_block(lo,stop,start,end);payload=self.compress(raw)
            if not 1<=len(payload)<=BLOCK_SIZE:raise ValueError('compressed block exceeds input slot')
            result+=struct.pack('<HH',len(raw),len(payload))+payload
            blocks.append(dict(raw_start=lo,raw_end=stop,decoded_bytes=len(raw),zx0_bytes=len(payload),sha256=sha(raw)))
        return bytes(result),blocks

    def volume(self,start,end,part):
        image,metadata=super().volume(start,end,part)
        metadata['zx0_block_phase']=self.block_phase
        return image,metadata
