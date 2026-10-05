"""Optional exact C kernels for PC waveform search; no Spectrum code changes.

Build once with the installed MSVC or cc compiler, in an ignored cache keyed
by source, platform and flags. There is no download or mandatory compiler:
the caller retains its NumPy implementation. The C source lives here so that
the converter's existing Python producer hashes also authenticate the kernel.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import uuid
import warnings

import numpy as np


SOURCE = r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif

/* Keep the exact elementwise NumPy order. NumPy still performs the final
   reduction of these 16 terms, preserving its pairwise summation order. */
API void waveform_terms(const double *base, const double *response,
    const int64_t *words, const double *desired, const double *weights,
    size_t parents, size_t branches, double *out) {
    for (size_t p=0; p<parents; ++p) {
        for (size_t b=0; b<branches; ++b) {
            size_t k=p*branches+b;
            const double *row=response+16*words[k];
            for (size_t j=0; j<16; ++j) {
                double observed=base[p*16+j]+row[j];
                double error=observed-desired[j];
                double square=error*error;
                out[k*16+j]=square*weights[j];
            }
        }
    }
}

/* Total order matches lexsort((candidate_id, score)); all scores are finite. */
static int worse(int64_t a, int64_t b, const double *score) {
    return score[a]>score[b] || (score[a]==score[b] && a>b);
}
static void down(int64_t *heap, size_t count, size_t root, const double *score) {
    for (;;) {
        size_t child=2*root+1;
        if (child>=count) return;
        if (child+1<count && worse(heap[child+1],heap[child],score)) ++child;
        if (!worse(heap[child],heap[root],score)) return;
        int64_t swap=heap[root]; heap[root]=heap[child]; heap[child]=swap;
        root=child;
    }
}

/* Hash-merge exact decoder keys, then retain a bounded max-heap. Candidate
   IDs settle both merge and beam ties, so hash iteration order is irrelevant.
   The table is a power of two, at least twice the maximum candidate count. */
API size_t waveform_select(const int64_t *candidates, const int64_t *keys,
    const double *score, size_t count, size_t width, int64_t *table_keys,
    int64_t *table_values, size_t capacity, int64_t *heap) {
    memset(table_keys,0xff,capacity*sizeof(int64_t));
    for (size_t i=0; i<count; ++i) {
        uint64_t h=(uint64_t)keys[i];
        h^=h>>30; h*=UINT64_C(0xbf58476d1ce4e5b9);
        h^=h>>27; h*=UINT64_C(0x94d049bb133111eb); h^=h>>31;
        size_t slot=(size_t)h&(capacity-1);
        while (table_keys[slot]!=-1 && table_keys[slot]!=keys[i])
            slot=(slot+1)&(capacity-1);
        int64_t id=candidates[i];
        if (table_keys[slot]==-1 || worse(table_values[slot],id,score)) {
            table_keys[slot]=keys[i]; table_values[slot]=id;
        }
    }
    size_t used=0;
    for (size_t i=0; i<capacity; ++i) {
        if (table_keys[i]==-1) continue;
        int64_t id=table_values[i];
        if (used<width) {
            size_t at=used++; heap[at]=id;
            while (at) {
                size_t parent=(at-1)/2;
                if (!worse(heap[at],heap[parent],score)) break;
                int64_t swap=heap[parent];heap[parent]=heap[at];heap[at]=swap;
                at=parent;
            }
        } else if (worse(heap[0],id,score)) {
            heap[0]=id; down(heap,used,0,score);
        }
    }
    /* Heap sort only the retained beam, in ascending (score, ID) order. */
    for (size_t end=used; end>1;) {
        --end;int64_t swap=heap[0];heap[0]=heap[end];heap[end]=swap;
        down(heap,end,0,score);
    }
    return used;
}
'''

_library = None
_attempted = False
_failure = None


def _command():
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return None  # Candidate IDs use NumPy's 64-bit native indexing ABI.
    if os.name != 'nt':
        compiler = shutil.which('cc')
        if not compiler:
            return None
        return [compiler, '-O3', '-std=c99', '-fno-fast-math', '-ffp-contract=off',
                '-shared', '-fPIC', 'kernel.c', '-o', 'kernel.so']
    locator = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
    locator /= 'Microsoft Visual Studio/Installer/vswhere.exe'
    if not locator.is_file():
        return None
    result = subprocess.run([str(locator), '-latest', '-products', '*', '-requires',
                             'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
                             '-property', 'installationPath'], capture_output=True,
                            text=True, check=True, creationflags=0x08000000)
    location = result.stdout.strip()
    if not location or platform.machine().lower() not in ('amd64', 'x86_64'):
        return None
    setup = Path(location)/'VC/Auxiliary/Build/vcvarsall.bat'
    # Only an installed compiler path is interpolated; outputs have fixed names
    # inside our cache directory. Do not print or persist the compiler's env.
    # cmd.exe needs its own quoting, not the CRT list2cmdline escaping of an
    # argument list (which would turn the batch path's quotes into backslashes).
    return (f'cmd /d /s /c "call "{setup}" x64 >nul && '
            'cl /nologo /O2 /std:c11 /fp:strict /LD /MT '
            'kernel.c /link /OUT:kernel.dll"')


def _load():
    command = _command()
    if command is None:
        return None
    # Version the cache/publication contract as well as the compiled source.
    identity = 'private-build-v1\n' + SOURCE + repr(command) + platform.machine() + str(ctypes.sizeof(ctypes.c_void_p))
    key = hashlib.sha256(identity.encode()).hexdigest()[:24]
    cache = Path(__file__).resolve().parent/'.native-cache'/key
    library_path = cache/('kernel.dll' if os.name == 'nt' else 'kernel.so')
    if not library_path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        # Concurrent converters compile privately and publish only a complete
        # library. Keep their small build logs in the ignored cache.
        build=cache/('build-'+uuid.uuid4().hex)
        build.mkdir()
        (build/'kernel.c').write_text(SOURCE, encoding='utf-8', newline='\n')
        result = subprocess.run(command, cwd=build, capture_output=True, timeout=120,
                                creationflags=0x08000000 if os.name == 'nt' else 0)
        (build/'build.log').write_bytes(result.stdout+result.stderr)
        compiled=build/library_path.name
        if result.returncode or not compiled.is_file():
            raise RuntimeError(f'waveform kernel build failed; see {build / "build.log"}')
        assert compiled.resolve().is_relative_to(cache.resolve())
        assert library_path.resolve().is_relative_to(cache.resolve())
        try:
            compiled.rename(library_path)
        except FileExistsError:
            pass  # Another completed build won publication on Windows.
    library = ctypes.CDLL(str(library_path))
    floats = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    integers = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
    size = ctypes.c_size_t
    library.waveform_terms.argtypes = [floats, floats, integers, floats, floats, size, size, floats]
    library.waveform_terms.restype = None
    library.waveform_select.argtypes = [integers, integers, floats, size, size,
                                        integers, integers, size, integers]
    library.waveform_select.restype = size
    return library


class Workspace:
    """One private scratch area per encoder; loaded code can be shared."""
    def __init__(self, library, width, branches):
        self.library = library
        self.width = width
        self.branches = branches
        count = width*branches
        capacity = 1 << (2*count-1).bit_length()
        self.terms = np.empty((count, 16), dtype=np.float64)
        self.keys = np.empty(capacity, dtype=np.int64)
        self.values = np.empty(capacity, dtype=np.int64)
        self.best = np.empty(width, dtype=np.int64)

    def errors(self, base, response, words, desired, weights):
        result = self.terms[:len(words)]
        self.library.waveform_terms(base, response, words, desired, weights,
                                    len(base), self.branches, result)
        return result

    def select(self, candidates, score, keys):
        count = self.library.waveform_select(candidates, keys, score, len(candidates),
                                             self.width, self.keys, self.values,
                                             len(self.keys), self.best)
        return self.best[:count]


def workspace(width, branches, backend='auto'):
    """auto uses the optional kernel; native requires it; numpy never builds."""
    global _library, _attempted, _failure
    if backend not in ('auto', 'numpy', 'native'):
        raise ValueError('waveform backend must be auto, numpy or native')
    if backend == 'numpy':
        return None
    if not _attempted:
        _attempted = True
        try:
            _library = _load()
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            _failure = error
            warnings.warn(f'{error}; using the exact NumPy waveform backend', RuntimeWarning)
    if _library is None:
        if backend == 'native':
            raise RuntimeError('native waveform backend unavailable') from _failure
        return None
    return Workspace(_library, width, branches)
