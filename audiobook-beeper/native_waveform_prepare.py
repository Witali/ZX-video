"""Exact C preparation of waveform targets; Python stays the reference.

No source, search feature, query grid, workset or encoded-data format changes.
Only the reference state recurrence and gathering are accelerated. The same
NumPy ILP64 OpenBLAS and strict compiler flags preserve operation ordering.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import uuid

import numpy as np

from build_pdm import CPU_CLOCK
import waveform_kernel

HERE=Path(__file__).resolve().parent
_library=None
_blas_library=None


def _load():
    global _library,_blas_library
    if _library is not None:return _library
    command=waveform_kernel._command()
    if command is None:raise RuntimeError('Native preparation needs the installed C compiler')
    source=(HERE/'native_waveform_prepare.c').read_text(encoding='utf-8')
    key=hashlib.sha256((source+repr(command)+platform.machine()).encode()).hexdigest()[:24]
    cache=HERE/'.native-cache'/('waveform-prepare-'+key)
    binary=cache/('kernel.dll' if os.name=='nt' else 'kernel.so')
    if not binary.is_file():
        build=cache/('build-'+uuid.uuid4().hex);build.mkdir(parents=True)
        (build/'kernel.c').write_text(source,encoding='utf-8',newline='\n')
        result=subprocess.run(command,cwd=build,capture_output=True,timeout=120,
            creationflags=0x08000000 if os.name=='nt' else 0)
        (build/'build.log').write_bytes(result.stdout+result.stderr)
        if result.returncode or not (build/binary.name).is_file():
            raise RuntimeError(f'Native preparation build failed; see {build/"build.log"}')
        try:(build/binary.name).rename(binary)
        except FileExistsError:pass
    directory=Path(np.__file__).resolve().parent.parent/'numpy.libs'
    for candidate in sorted(directory.glob('*openblas*')):
        try:
            blas=ctypes.CDLL(str(candidate));gemv=getattr(blas,'scipy_cblas_dgemv64_')
        except (OSError,AttributeError):continue
        _blas_library=blas;break
    else:raise RuntimeError('Native preparation needs NumPy ILP64 OpenBLAS')
    library=ctypes.CDLL(str(binary))
    floats=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
    units=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
    octets=np.ctypeslib.ndpointer(dtype=np.uint8,flags='C_CONTIGUOUS')
    library.waveform_prepare_reference.argtypes=[octets,ctypes.c_size_t,units,
        ctypes.c_size_t,floats,floats,floats,floats,ctypes.c_void_p,floats]
    library.waveform_prepare_reference.restype=ctypes.c_int
    library.waveform_prepare_unique_holds.argtypes=[floats,ctypes.c_size_t,
        units,units,ctypes.POINTER(ctypes.c_size_t)]
    library.waveform_prepare_unique_holds.restype=ctypes.c_int
    library._prepare_gemv=ctypes.cast(gemv,ctypes.c_void_p)
    library._prepare_source_sha256=hashlib.sha256(source.encode()).hexdigest()
    library._prepare_binary=str(binary);library._prepare_blas=str(candidate)
    _library=library;return library


def reference(model,source,queries):
    """Drop-in ``WaveformModel.reference(source,queries)`` implementation.

    Model coefficients and reference-query quantization follow the Python
    implementation verbatim. C computes all six filter states in the same
    sequence, then gathers and reduces each target without large temporaries.
    """
    source=np.asarray(source)
    if source.ndim!=1 or source.dtype!=np.uint8 or not len(source):
        raise ValueError('Need a nonempty mono PCM8 source')
    source=np.ascontiguousarray(source)
    queries=np.asarray(queries)
    units=np.rint(queries*80).astype(np.int64)
    if not units.size or np.max(abs(queries*80-units))>=1e-6 or np.any(units<0):
        raise ValueError('Need nonnegative queries on the existing 1/80-T grid')
    units=np.ascontiguousarray(units)
    e,u=model.transition(CPU_CLOCK/8000)
    f=np.arange(35469)/35469
    row=np.zeros((35469,6))
    for coefficient in reversed(model.coefficients):row=row*f[:,None]+model.c@coefficient
    output=np.empty(units.shape,dtype=np.float64)
    library=_load()
    status=library.waveform_prepare_reference(source,len(source),units,units.size,
        np.ascontiguousarray(e),np.ascontiguousarray(u),row,
        np.ascontiguousarray(model.steady),library._prepare_gemv,output)
    if status:raise RuntimeError(f'Native waveform preparation failed with status {status}')
    return output


def unique_holds(holds):
    """Exact unique positive float64 rows and lexicographic inverse IDs.

    Physical intervals are strictly positive and finite. C validates that
    contract while hashing all sixteen unrounded float64 values per row.
    This reduces sorting from every source row to the unique packet shapes.
    """
    holds=np.asarray(holds)
    if holds.ndim!=2 or holds.shape[1]!=16 or holds.dtype!=np.float64 or not len(holds):
        raise ValueError('Need nonempty float64 pulse intervals with sixteen columns')
    holds=np.ascontiguousarray(holds)
    indices=np.empty(len(holds),dtype=np.int64)
    inverse=np.empty(len(holds),dtype=np.int64)
    count=ctypes.c_size_t()
    status=_load().waveform_prepare_unique_holds(holds,len(holds),indices,inverse,ctypes.byref(count))
    if status:raise ValueError(f'Native unique-hold preparation rejected input: {status}')
    return holds[indices[:count.value]],inverse
