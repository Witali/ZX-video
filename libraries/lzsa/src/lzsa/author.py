"""Small ctypes binding to a locally built, unmodified author LZSA library."""
import ctypes
from pathlib import Path


class Author:
    def __init__(self,path):
        self.dll=ctypes.CDLL(str(Path(path).resolve()))
        for name in ('zxv_compress','zxv_decompress'):
            f=getattr(self.dll,name);f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
            f.restype=ctypes.c_size_t

    def call(self,name,data,capacity):
        source=ctypes.create_string_buffer(data);dest=ctypes.create_string_buffer(max(capacity,1))
        n=getattr(self.dll,name)(source,len(data),dest,capacity)
        if n>capacity:raise ValueError((name,'author codec failed',n))
        return dest.raw[:n]

    def compress(self,raw):return self.call('zxv_compress',raw,len(raw)+1024)

    def decompress(self,payload,n):
        raw=self.call('zxv_decompress',payload,n)
        if len(raw)!=n:raise AssertionError('author output extent differs')
        return raw
