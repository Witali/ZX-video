"""Complete C waveform beam search; the original Python stays the reference.

Only model preparation and array validation remain in Python. One ctypes call
per complete source performs search, prefix replay, settling guard and packing.
Exact arithmetic depends on the same installed ILP64 OpenBLAS as NumPy. The
wrapper fails explicitly when that backend or unsupported options are used.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import platform
import json
import struct
import subprocess
import uuid

import numpy as np

from ima_codec import STEPS, INDEX
import waveform_kernel


HERE = Path(__file__).resolve().parent
_library = None
_blas_library = None


def _load():
    global _library, _blas_library
    if _library is not None:
        return _library
    command = waveform_kernel._command()
    if command is None:
        raise RuntimeError('Complete C waveform encoder needs the installed C compiler')
    source = waveform_kernel.SOURCE + '\n' + (HERE/'native_waveform_encoder.c').read_text(encoding='utf-8')
    identity = ('complete-waveform-v1\n' + source + repr(command) + platform.machine()
                + str(ctypes.sizeof(ctypes.c_void_p)))
    key = hashlib.sha256(identity.encode()).hexdigest()[:24]
    cache = HERE/'.native-cache'/('complete-waveform-'+key)
    binary = cache/('kernel.dll' if os.name == 'nt' else 'kernel.so')
    if not binary.is_file():
        build = cache/('build-'+uuid.uuid4().hex)
        build.mkdir(parents=True)
        (build/'kernel.c').write_text(source, encoding='utf-8', newline='\n')
        result = subprocess.run(command, cwd=build, capture_output=True, timeout=120,
                                creationflags=0x08000000 if os.name == 'nt' else 0)
        (build/'build.log').write_bytes(result.stdout+result.stderr)
        compiled = build/binary.name
        if result.returncode or not compiled.is_file():
            raise RuntimeError(f'Complete C encoder build failed; see {build / "build.log"}')
        try:
            compiled.rename(binary)
        except FileExistsError:
            pass
    # NumPy's own ILP64 exports preserve its matrix-product reduction order.
    # Selecting another BLAS silently would weaken byte-parity evidence.
    directory = Path(np.__file__).resolve().parent.parent/'numpy.libs'
    candidates = sorted(directory.glob('*openblas*')) if directory.is_dir() else []
    for candidate in candidates:
        try:
            library = ctypes.CDLL(str(candidate))
            gemm = getattr(library, 'scipy_cblas_dgemm64_')
            gemv = getattr(library, 'scipy_cblas_dgemv64_')
        except (OSError, AttributeError):
            continue
        _blas_library = library
        break
    else:
        raise RuntimeError('Exact C encoder needs NumPy\'s installed ILP64 OpenBLAS exports')
    library = ctypes.CDLL(str(binary))
    floats = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    integers = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
    octets = np.ctypeslib.ndpointer(dtype=np.uint8, flags='C_CONTIGUOUS')
    size = ctypes.c_size_t
    library.native_waveform_encode.argtypes = [octets, size, floats, floats, floats,
        floats, floats, floats, integers, size, integers, integers, integers,
        size, size, size, ctypes.c_double, ctypes.c_void_p, ctypes.c_void_p,
        octets, integers]
    library.native_waveform_encode.restype = ctypes.c_int
    library.native_waveform_encode_centered.argtypes = (library.native_waveform_encode.argtypes[:17]
        + [ctypes.c_int64] + library.native_waveform_encode.argtypes[17:])
    library.native_waveform_encode_centered.restype = ctypes.c_int
    library.native_waveform_quantize.argtypes = [integers,size,ctypes.c_int64,integers]
    library.native_waveform_quantize.restype = ctypes.c_int
    library._nwf_gemm = ctypes.cast(gemm, ctypes.c_void_p)
    library._nwf_gemv = ctypes.cast(gemv, ctypes.c_void_p)
    library._nwf_binary = str(binary)
    library._nwf_blas_path = str(candidate)
    library._nwf_source_sha256 = hashlib.sha256(source.encode()).hexdigest()
    _library = library
    return library


def _prepare_arrays(source, desired, features, ids, nxt, width=32,
                    block_size=128, regularization=.1, history_bins=0,
                    allowed_codes=None, level_bounds=None,
                    commit_size=64, backend='native', pcm_quantization_bias=0):
    if type(pcm_quantization_bias) is not int or pcm_quantization_bias not in (0,512):
        raise ValueError('pcm_quantization_bias must be builtin integer0 or512')
    if backend != 'native':
        raise ValueError('Complete C encoder backend must be native')
    if history_bins or level_bounds is not None:
        raise ValueError('Complete C encoder supports history_bins=0 and no level_bounds')
    if allowed_codes is not None:
        alphabet = np.asarray(allowed_codes)
        if (not np.issubdtype(alphabet.dtype,np.integer) or
                not np.array_equal(alphabet,np.arange(16))):
            raise ValueError('Complete C encoder supports all 16 integer IMA nibbles in their original order')
    source = np.asarray(source)
    if source.ndim != 1 or source.dtype != np.uint8 or len(source)<128 or len(source)%2:
        raise ValueError('Need an even uint8 mono source with a 128-sample guard')
    source = np.ascontiguousarray(source)
    if np.any(source[-128:] != 128):
        raise ValueError('Settling guard must already be silent; it may not discard source content')
    if (not isinstance(width, int) or not 32 <= width <= 4096 or
            not isinstance(block_size, int) or not 64 <= block_size <= 8192):
        raise ValueError('Need integer width>=32 and horizon>=64 within supported bounds')
    commit_size = block_size if commit_size is None else commit_size
    if not isinstance(commit_size, int) or not 1 <= commit_size <= block_size:
        raise ValueError('Commit must be within the lookahead horizon')
    if not np.isfinite(regularization) or regularization < 0:
        raise ValueError('Regularization must be finite and nonnegative')
    if not np.issubdtype(np.asarray(ids).dtype,np.integer):
        raise ValueError('Packet IDs must be integer indices')
    ids = np.ascontiguousarray(ids, dtype=np.int64)
    count = len(source)-128
    if ids.shape != (count,):
        raise ValueError('Packet IDs must cover exactly the source before its 128-sample guard')
    desired = np.ascontiguousarray(desired, dtype=np.float64)
    if desired.shape != (count,16) or not np.all(np.isfinite(desired)):
        raise ValueError('Desired waveform must be finite with 16 pulse targets per encoded sample')
    if not np.issubdtype(np.asarray(nxt).dtype,np.integer):
        raise ValueError('Feedback successors must be integer states')
    nxt = np.ascontiguousarray(nxt, dtype=np.int64)
    if nxt.shape != (64,32) or np.any(nxt<0) or np.any(nxt>=32):
        raise ValueError('Need a closed 64-bin/32-state feedback table')
    if not len(features) or np.any(ids<0) or np.any(ids>=len(features)):
        raise ValueError('Packet IDs must address a nonempty feature catalogue')
    shapes = ((6,6),(16,6),(2048,16),(2048,6),(16,))
    columns = []
    for column, shape in enumerate(shapes):
        if any(len(feature)!=5 or np.shape(feature[column])!=shape for feature in features):
            raise ValueError(f'Feature column {column} must have shape {shape}')
        array = np.ascontiguousarray([feature[column] for feature in features], dtype=np.float64)
        if not np.all(np.isfinite(array)):
            raise ValueError('All feature coefficients must be finite')
        columns.append(array)
    if np.any(columns[-1]<0):
        raise ValueError('Quadrature weights must be nonnegative')
    codes = np.arange(16, dtype=np.int64)
    steps = np.asarray(STEPS, dtype=np.int64)[:,None]
    delta = ((steps>>3) + steps*((codes&4)!=0) + (steps>>1)*((codes&2)!=0)
             + (steps>>2)*((codes&1)!=0)) * np.where(codes&8,-1,1)
    successor = np.ascontiguousarray(np.clip(np.arange(89)[:,None]
        + np.asarray(INDEX)[codes&7],0,88), dtype=np.int64)
    return source,desired,columns,ids,nxt,delta,successor,width,block_size,commit_size,regularization,pcm_quantization_bias


def encode_waveform_native(source, desired, features, ids, nxt, width=32,
                           block_size=128, regularization=.1, history_bins=0,
                           allowed_codes=None, level_bounds=None,
                           commit_size=64, backend='native', statistics=None,
                           pcm_quantization_bias=0):
    """One C call for a complete source, matching the unchanged Python API.

    The proved path has all 16 nibbles,64 PCM bins/32 feedback states and the
    existing 128-sample settling guard. Width>=32 and horizon>=64 use the same
    algorithm; options outside that contract fail before entering native code.
    """
    source,desired,columns,ids,nxt,delta,successor,width,block_size,commit_size,regularization,bias = _prepare_arrays(
        source,desired,features,ids,nxt,width,block_size,regularization,history_bins,
        allowed_codes,level_bounds,commit_size,backend,pcm_quantization_bias)
    library = _load()
    packed = np.empty(len(source)//2, dtype=np.uint8)
    counts = np.zeros(3, dtype=np.int64)
    if not bias:
        status = library.native_waveform_encode(source, len(source), desired, *columns,
            ids, len(columns[0]), nxt, delta, successor, width, block_size, commit_size,
            regularization, library._nwf_gemm, library._nwf_gemv, packed, counts)
    else:
        status = library.native_waveform_encode_centered(source, len(source), desired, *columns,
            ids, len(columns[0]), nxt, delta, successor, width, block_size, commit_size,
            regularization, bias, library._nwf_gemm, library._nwf_gemv, packed, counts)
    if status:
        raise RuntimeError(f'Complete C waveform encoder failed with status {status}')
    if statistics is not None:
        statistics.update(backend='complete-c', search_iterations=int(counts[0]),
            final_predictor=int(counts[1]), final_index=int(counts[2]),
            original_python_reference_unchanged=True,
            native_source_sha256=library._nwf_source_sha256,
            matrix_backend='Same installed NumPy ILP64 OpenBLAS',
            native_library=library._nwf_binary)
        if bias:statistics['pcm_quantization_bias']=bias
    return packed.tobytes()


def write_workset(path, source, desired, features, ids, nxt, **options):
    """Write deterministic little-endian input for the C executable.

    The executable independently validates the header, finite coefficients,
    feedback closure, silent guard and exact IMA transition table before search.
    Default bias0 preserves every version1 byte. Opt-in bias512 writes version2
    with one int64 bias after the original56-byte header.
    """
    arrays = _prepare_arrays(source,desired,features,ids,nxt,**options)
    source,desired,columns,ids,nxt,delta,successor,width,horizon,commit,reg,bias = arrays
    path = Path(path)
    with path.open('wb') as stream:
        magic=b'NWFB002\0' if bias else b'NWFB001\0'
        stream.write(struct.pack('<8sQQQQQd',magic,len(source),len(features),
                                 width,horizon,commit,reg))
        if bias:stream.write(struct.pack('<q',bias))
        source.tofile(stream)
        for array in (desired,*columns):
            np.asarray(array,dtype='<f8').tofile(stream)
        for array in (ids,nxt,delta,successor):
            np.asarray(array,dtype='<i8').tofile(stream)
    return path


def quantize_pcm_levels(predictors,pcm_quantization_bias=0):
    """Expose the C integer lookup for exhaustive signed-PCM16 verification."""
    if type(pcm_quantization_bias) is not int or pcm_quantization_bias not in (0,512):
        raise ValueError('pcm_quantization_bias must be builtin integer0 or512')
    values=np.asarray(predictors)
    if (not np.issubdtype(values.dtype,np.integer) or
            np.any(values < -32768) or np.any(values>32767)):
        raise ValueError('Predictors must be signed PCM16 integers')
    values=np.ascontiguousarray(values,dtype=np.int64);levels=np.empty_like(values)
    status=_load().native_waveform_quantize(values,values.size,pcm_quantization_bias,levels)
    if status:raise RuntimeError('Native PCM lookup rejected its validated input')
    return levels


def build_executable():
    """Build the standalone Windows C program with the installed MSVC only."""
    if os.name != 'nt':
        raise RuntimeError('The standalone executable currently targets Windows; use the C library elsewhere')
    command = waveform_kernel._command()
    if not isinstance(command,str) or '/LD /MT' not in command:
        raise RuntimeError('Standalone C encoder needs the installed MSVC command')
    command = command.replace('/LD /MT','/DNWF_STANDALONE /MT').replace('/OUT:kernel.dll','/OUT:kernel.exe')
    source = waveform_kernel.SOURCE+'\n'+(HERE/'native_waveform_encoder.c').read_text(encoding='utf-8')
    key = hashlib.sha256(('standalone-waveform-v1\n'+source+command).encode()).hexdigest()[:24]
    cache = HERE/'.native-cache'/('standalone-waveform-'+key)
    binary = cache/'kernel.exe'
    if not binary.is_file():
        build = cache/('build-'+uuid.uuid4().hex);build.mkdir(parents=True)
        (build/'kernel.c').write_text(source,encoding='utf-8',newline='\n')
        result = subprocess.run(command,cwd=build,capture_output=True,timeout=120,creationflags=0x08000000)
        (build/'build.log').write_bytes(result.stdout+result.stderr)
        compiled = build/binary.name
        if result.returncode or not compiled.is_file():
            raise RuntimeError(f'Standalone C build failed; see {build / "build.log"}')
        try:
            compiled.rename(binary)
        except FileExistsError:
            pass
    return binary


def execute_workset(workset, output, statistics=None):
    """Run encoding in a separate C process; no Python runtime in that child."""
    library = _load()
    executable = build_executable()
    result = subprocess.run([str(executable),str(Path(workset).resolve()),str(Path(output).resolve()),
                             library._nwf_blas_path],capture_output=True,text=True,
                            creationflags=0x08000000 if os.name=='nt' else 0)
    if result.returncode:
        raise RuntimeError(f'Standalone C encoder failed ({result.returncode}): {result.stderr.strip()}')
    report = json.loads(result.stdout)
    if statistics is not None:
        statistics.update(report,backend='standalone-c',executable=str(executable),
                          matrix_library=library._nwf_blas_path,
                          child_python_runtime=False,native_source_sha256=library._nwf_source_sha256)
    return Path(output).read_bytes()
