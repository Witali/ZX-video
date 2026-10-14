"""Complete C PCM-error IMA trellis; ima_beam.py remains the reference.

One C call encodes the entire source and carries predictor/index across blocks.
Integer scores, decoder-state merging and candidate-ID ties match Python. No
BLAS dependency is needed; the optional raw-PCM executable also needs no Python
runtime. Compilers and binaries stay in the existing ignored private cache.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import uuid

import numpy as np
from ima_beam import code_alphabet
import waveform_kernel


HERE=Path(__file__).resolve().parent
_library=None


def _source():
    return waveform_kernel.SOURCE+'\n'+(HERE/'native_ima_encoder.c').read_text(encoding='utf-8')


def _build(executable=False):
    command=waveform_kernel._command()
    if command is None:
        raise RuntimeError('Native PCM encoder requires the installed C compiler')
    if executable:
        if os.name!='nt' or not isinstance(command,str) or '/LD /MT' not in command:
            raise RuntimeError('The standalone PCM executable currently requires Windows/MSVC')
        command=command.replace('/LD /MT','/DNIMA_STANDALONE /MT').replace('/OUT:kernel.dll','/OUT:kernel.exe')
    source=_source()
    identity='complete-pcm-v1\n'+source+repr(command)+platform.machine()+str(ctypes.sizeof(ctypes.c_void_p))
    key=hashlib.sha256(identity.encode()).hexdigest()[:24]
    cache=HERE/'.native-cache'/('complete-pcm-'+key)
    binary=cache/('kernel.exe' if executable else 'kernel.dll' if os.name=='nt' else 'kernel.so')
    if not binary.is_file():
        build=cache/('build-'+uuid.uuid4().hex);build.mkdir(parents=True)
        (build/'kernel.c').write_text(source,encoding='utf-8',newline='\n')
        result=subprocess.run(command,cwd=build,capture_output=True,timeout=120,
                              creationflags=0x08000000 if os.name=='nt' else 0)
        (build/'build.log').write_bytes(result.stdout+result.stderr)
        compiled=build/binary.name
        if result.returncode or not compiled.is_file():
            raise RuntimeError(f'Native PCM build failed; see {build / "build.log"}')
        try:
            compiled.rename(binary)
        except FileExistsError:
            pass
    return binary,hashlib.sha256(source.encode()).hexdigest()


def _load():
    global _library
    if _library is not None:return _library
    binary,source_sha=_build()
    library=ctypes.CDLL(str(binary))
    octets=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
    integers=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
    library.native_ima_encode.argtypes=[octets,ctypes.c_size_t,octets,ctypes.c_size_t,
        ctypes.c_size_t,ctypes.c_size_t,ctypes.c_int64,ctypes.c_int64,
        ctypes.c_int64,ctypes.c_int64,octets,integers]
    library.native_ima_encode.restype=ctypes.c_int
    library._nima_binary=str(binary);library._nima_source_sha256=source_sha
    _library=library;return library


def encode_pcm_native(pcm8,width=32,block_samples=64,predictor=0,index=0,
                      allowed_codes=None,predictor_bounds=(-32768,32767),statistics=None):
    """Whole-source exact PCM trellis with the unchanged low-nibble-first format.

    Sources must be integer mono PCM8 without implicit clipping/conversion.
    All original code alphabets and valid seeds/bounds are supported. Excessive
    scratch budgets and invalid/unreachable bounds fail explicitly.
    """
    source=np.asarray(pcm8)
    if (source.ndim!=1 or not np.issubdtype(source.dtype,np.integer) or len(source)%2
            or np.any(source<0) or np.any(source>255)):
        raise ValueError('Need an even integer mono PCM8 source within0..255')
    source=np.ascontiguousarray(source,dtype=np.uint8)
    if (not isinstance(width,int) or not 1<=width<=4096 or
            not isinstance(block_samples,int) or not 2<=block_samples<=65536 or block_samples%2 or
            width*block_samples>16777216):
        raise ValueError('Need a positive supported beam and even block with bounded scratch memory')
    if not isinstance(predictor,(int,np.integer)) or not isinstance(index,(int,np.integer)) or not 0<=index<=88:
        raise ValueError('Need an integer predictor and IMA index within0..88')
    try:lower,upper=predictor_bounds
    except (TypeError,ValueError):raise ValueError('Predictor bounds must contain two integer endpoints') from None
    if (not isinstance(lower,(int,np.integer)) or not isinstance(upper,(int,np.integer)) or
            not -32768<=lower<=predictor<=upper<=32767):
        raise ValueError('Predictor must be inside valid signed PCM16 bounds')
    codes=np.ascontiguousarray(code_alphabet(allowed_codes),dtype=np.uint8)
    library=_load();packed=np.empty(len(source)//2,dtype=np.uint8);counts=np.zeros(7,dtype=np.int64)
    status=library.native_ima_encode(source,len(source),codes,len(codes),width,block_samples,
                                   predictor,index,lower,upper,packed,counts)
    if status==3:
        raise ValueError(f'No unclipped decoder path at sample {counts[6]} within the requested bounds/alphabet')
    if status:
        raise RuntimeError(f'Native PCM encoder failed with status {status}')
    if statistics is not None:
        statistics.update(backend='complete-c-pcm',samples=int(counts[0]),
            final_predictor=int(counts[1]),final_index=int(counts[2]),
            raw_min=int(counts[3]) if len(source) else None,
            raw_max=int(counts[4]) if len(source) else None,saturation_events=int(counts[5]),
            original_python_reference_unchanged=True,native_source_sha256=library._nima_source_sha256,
            native_library=library._nima_binary,blas_dependency=False)
    return packed.tobytes()


def build_executable():
    """Standalone default width32/block64 raw-PCM program; no BLAS/Python DLL."""
    return _build(executable=True)[0]


def execute_pcm_file(source,output,statistics=None):
    """Encode an even raw mono uint8 file in a separate C process."""
    executable=build_executable()
    result=subprocess.run([str(executable),str(Path(source).resolve()),str(Path(output).resolve())],
                          capture_output=True,text=True,creationflags=0x08000000 if os.name=='nt' else 0)
    if result.returncode:
        raise RuntimeError(f'Standalone PCM encoder failed ({result.returncode}): {result.stderr.strip()}')
    if statistics is not None:
        statistics.update(json.loads(result.stdout),backend='standalone-c-pcm',
                          executable=str(executable),child_python_runtime=False,blas_dependency=False)
    return Path(output).read_bytes()
