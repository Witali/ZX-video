"""Exact G.726-16 host library, packing and separately compiled Z80 builds."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from waveform_kernel import _command


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')


def annotate_assembly(path):
    """Keep algorithm/ABI comments in generated listings across rebuilds."""
    comments = {
        '_to_float:': 'Convert a signed bounded value to sign/exponent/mantissa Float11.\nZero is exponent0/mantissa32. OPT1 bounds intermediates; OPT2 uses bit-length lookup.',
        '_multiply:': 'Multiply two Float11 predictor terms. Round mantissa product with +48 before\nshifting by four, apply exponent, then signed16 modular result. OPT2 uses a 1-KiB table.',
        '_g726_reset::': 'Initialize all100 bytes of adaptive state, including special floating zeros\nand the mandated fast/slow step sizes. Call only at stream start, not each packed byte.',
        '_g726_decode_one::': 'Decode one two-bit G.726 code; inverse quantize, update two poles/six zeros,\nadapt step size and activity, shift histories, predict the next sample.\nSDCC ABI: state pointer HL; one code byte on stack above return address.\nPCM16 result DE; callee discards the code byte. IX preserved; AF, BC, DE, HL\nand IY are scratch. Stack measurement includes compiler helpers.\nOPT3 replaces sign products and inverse quantization by exact bounded operations.\nNo OUT/interrupt deadline: this complete decoder is timed by verify_z80.py.',
        '_entry::': 'Flat benchmark entry; caller must provide SP and mailbox8F00. Four MSB-first\ncodes per byte; decode directly to PCM16, preserving state between calls.\nWrite final state to8F20 and completion/count to8F08..8F0D. No ULA/ROM/disk/PDM.\nReturns with IX/SP preserved; other registers, including IY, may be clobbered.',
    }
    text = Path(path).read_text()
    for label, comment in comments.items():
        prefix = '; G726 routine contract\n' + ''.join('; '+line+'\n' for line in comment.splitlines())
        if prefix+label not in text:
            text = text.replace('\n'+label+'\n', '\n'+prefix+label+'\n')
    Path(path).write_text(text)


def tables(folder):
    """Generic mathematical tables: no recording-specific data or state."""
    def array(name,values,width='uint8_t'):
        flat=np.asarray(values).ravel().tolist()
        shape=''.join(f'[{n}]' for n in np.shape(values))
        # A two-dimensional C initializer needs row braces, not a flat list
        # on all supported target compilers.
        if len(np.shape(values))==2:
            text=',\n'.join('{'+','.join(map(str,row))+'}' for row in values)
        else:text=',\n'.join(','.join(map(str,flat[i:i+32])) for i in range(0,len(flat),32))
        return f'static const {width} {name}{shape}={{\n{text}\n}};\n'
    log=[x.bit_length() for x in range(256)]
    product=[(a*b+48)>>4 for a in range(32,64) for b in range(32,64)]
    (folder/'small_tables.inc').write_text(array('g726_log',log)+array('g726_product',product))
    iq=[[(128+((level+y)&127))<<(((level+y)>>7)&15)>>7 for y in range(136,1281)] for level in (116,365)]
    (folder/'inverse_tables.inc').write_text(array('g726_inverse',iq,'uint16_t'))


def build_host(out,opt=3):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    tables(out)
    (out/'kernel.c').write_text(f'#define OPT {opt}\n'+(HERE/'core.c').read_text())
    cmd=_command()
    if cmd is None:raise RuntimeError('A local C compiler is required for this experimental codec')
    result=subprocess.run(cmd,cwd=out,capture_output=True,text=True,errors='replace')
    (out/'build.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    library=out/('kernel.dll' if os.name=='nt' else 'kernel.so')
    save(out/'build.json',dict(opt=opt,source_sha256=sha(HERE/'core.c'),library_sha256=sha(library)))
    return library


class Codec:
    def __init__(self,library):
        self.lib=ctypes.CDLL(str(Path(library).resolve()))
        self.lib.g726_state_bytes.restype=ctypes.c_uint16
        assert self.lib.g726_state_bytes()==100,'State ABI must match the Z80'
        self.lib.g726_reset.argtypes=[ctypes.c_void_p]
        self.lib.g726_decode_one.argtypes=[ctypes.c_void_p,ctypes.c_uint8]
        self.lib.g726_decode_one.restype=ctypes.c_int16
        self.lib.g726_decode_codes.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32]
        self.lib.g726_encode_pcm.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32]

    def state(self):
        result=ctypes.create_string_buffer(100);self.lib.g726_reset(result);return result

    def decode(self,codes,state=None):
        codes=np.ascontiguousarray(codes,dtype='u1')
        if np.any(codes>3):raise ValueError('G.726-16 codes must be 0..3')
        pcm=np.empty(len(codes),dtype='<i2');state=self.state() if state is None else state
        self.lib.g726_decode_codes(state,codes.ctypes.data,pcm.ctypes.data,len(codes))
        return pcm,state

    def encode(self,pcm):
        pcm=np.ascontiguousarray(pcm,dtype='<i2');codes=np.empty(len(pcm),dtype='u1')
        self.lib.g726_encode_pcm(pcm.ctypes.data,codes.ctypes.data,len(pcm));return codes


def pack(codes,little_endian=False):
    codes=np.asarray(codes,dtype='u1')
    if len(codes)%4 or np.any(codes>3):raise ValueError('Four valid two-bit codes per byte required')
    shifts=np.arange(0,8,2) if little_endian else np.arange(6,-1,-2)
    return np.sum(codes.reshape(-1,4).astype(np.uint16)<<shifts,axis=1).astype('u1').tobytes()


def unpack(data,little_endian=False):
    shifts=np.arange(0,8,2) if little_endian else np.arange(6,-1,-2)
    return ((np.frombuffer(data,'u1')[:,None]>>shifts)&3).astype('u1').ravel()


def ffmpeg_encode(pcm,ffmpeg,little_endian=False):
    name='g726le' if little_endian else 'g726'
    return subprocess.run([str(ffmpeg),'-v','error','-nostdin','-f','s16le','-ar','8000','-ac','1','-i','-',
        '-c:a',name,'-b:a','16000','-f',name,'-'],input=np.asarray(pcm,dtype='<i2').tobytes(),capture_output=True,check=True).stdout


def ffmpeg_decode(data,ffmpeg,little_endian=False):
    name='g726le' if little_endian else 'g726'
    raw=subprocess.run([str(ffmpeg),'-v','error','-nostdin','-f',name,'-code_size','2','-ar','8000','-ac','1','-i','-',
        '-f','s16le','-'],input=data,capture_output=True,check=True).stdout
    return np.frombuffer(raw,'<i2')


def build_z80(out,sdcc,opt):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);sdcc=Path(sdcc).resolve()
    tables(out);shutil.copy2(HERE/'core.c',out/'decoder.c')
    flags=['-mz80','--std-c11','--opt-code-speed','--max-allocs-per-node','100000',
           '--no-std-crt0','--code-loc','0x0200','--data-loc','0x8000',f'-DOPT={opt}']
    env=os.environ.copy();env['PATH']=str(sdcc.parent)+os.pathsep+env['PATH']
    run=subprocess.run([str(sdcc),*flags,'decoder.c','-o','decoder.ihx'],cwd=out,env=env,capture_output=True,text=True,errors='replace')
    (out/'build.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    annotate_assembly(out/'decoder.asm')
    version=subprocess.run([str(sdcc),'--version'],env=env,capture_output=True,text=True,check=True).stdout
    save(out/'build.json',dict(opt=opt,flags=flags,compiler=version,compiler_sha256=sha(sdcc),source_sha256=sha(HERE/'core.c')))
    return out
