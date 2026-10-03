"""Baseline and three exact Z80 PVQ3x512 decoder optimizations, full input.

CPU/buffer proof only. No IMA re-encoding, disk, ULA or beeper integration
is included. The final two vector-padding samples are verified but inaudible.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from z80 import Z80Machine
from build_lpc_disk import assemble
from verify_pcm import save
from convert_audio import pcm_wav


def run(source,out):
    out.mkdir(parents=True,exist_ok=True)
    out.mkdir(parents=True,exist_ok=True)
    codec='pvq3x512-half';samples=186880;vectors=(samples+2)//3
    bits=np.unpackbits(np.frombuffer(gzip.decompress((source/(codec+'.data.gz')).read_bytes()),'u1'))
    ids=(bits[:vectors*9].reshape(-1,9)@(1<<np.arange(8,-1,-1))).astype(int)
    packed_book=gzip.decompress((source/(codec+'.book.gz')).read_bytes())
    book=np.frombuffer(packed_book,'i1').reshape(512,3)
    expected=[];last=128
    for code in ids:
        values=book[code].astype(int)+last//2+64
        assert values.min()>=0 and values.max()<=255
        expected.extend(values);last=int(values[-1])
    expected=bytes(expected)
    pcm_wav(out/'decoded-preview.wav',np.frombuffer(expected[:samples],'u1'))
    padded=np.full((512,4),0xa5,dtype='u1');padded[:,:3]=book.view('u1')
    rows=[];stream_size=0
    for version in range(4):
        work=out/f'round-{version}';work.mkdir(exist_ok=True)
        (work/'pvq-config.inc').write_text(f'optimization: EQU {version}\n')
        (work/'dictionary.bin').write_bytes(padded.tobytes())
        (work/'pointer-low.bin').write_bytes(bytes((i*4)&255 for i in range(256)))
        (work/'pointer-high.bin').write_bytes(bytes(0x90+(i>>6) for i in range(256)))
        shutil.copy2(Path(__file__).with_name('pvq3-decode.asm'),work/'decode.asm')
        labels=assemble(work,'decode');blob=(work/'decode.bin').read_bytes()
        total=0;actual=bytearray();times=[];hist=Counter();stream_size=0;chunks=[]
        for begin in range(0,vectors,5456):
            group=ids[begin:begin+5456];stream=bytearray()
            for i in range(0,len(group),8):
                eight=group[i:i+8]
                stream.append(sum(int(v>>8)<<k for k,v in enumerate(eight)))
                stream.extend((eight&255).tolist())
            stream_size+=len(stream);count=len(group)*3
            last=expected[begin*3-1] if begin else 128
            m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,blob)
            m.set_memory_block(0xC000,stream);m.sp=0xBFF0;m.de=0x4000
            m.bc=len(group) if version==3 else count
            m.alt_de=0xC000;m.alt_hl=0x9000;m.alt_bc=0x8000
            m.ix=last<<8;m.iy=0x0101;m.memory[labels['last_pcm']]=last
            before=bytes(m.memory[0x8800:0x9800]);m.pc=labels['loop']
            m.set_breakpoint(labels['loop']);m.set_breakpoint(labels['complete'])
            budget=100_000_000;m.ticks_to_stop=budget;start=budget
            m.step_over_breakpoint()
            while m.pc!=labels['complete']:
                if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('PVQ timeout')
                if m.pc in (labels['loop'],labels['complete']):
                    used=start-m.ticks_to_stop;hist[used]+=1;start=m.ticks_to_stop
                    if m.pc!=labels['complete']:m.step_over_breakpoint()
            used=budget-m.ticks_to_stop;total+=used
            data=bytes(m.memory[0x4000:0x4000+count]);actual.extend(data)
            assert data==expected[begin*3:begin*3+count],(version,begin)
            assert bytes(m.memory[0x4000+count:0x8000])==b'\xa5'*(16384-count)
            assert bytes(m.memory[0x8800:0x9800])==before
            assert bytes(m.memory[0xC000:0xC000+len(stream)])==stream
            chunks.append(dict(vectors=len(group),samples=count,input_bytes=len(stream),tstates=used))
        assert bytes(actual)==expected
        counted=({120,259,262,282,285},{115,249,252,272,275},
                 {115,234,237,257,260},{276,279,299,302})[version]
        assert set(hist)==counted,('instruction count',version,hist)
        row=dict(round=version,total_tstates=total,cpu_only_seconds=total/3546900,
                 mean_tstates_per_sample=total/len(expected),samples_verified=len(actual),
                 every_pcm_byte_exact=True,table_input_unchanged=True,
                 iteration_samples=3 if version==3 else 1,
                 iteration_tstate_histogram=dict(sorted(hist.items())),chunks=chunks,
                 additional_pointer_table_bytes=512 if version>=2 else 0,
                 binary_sha256=hashlib.sha256(blob).hexdigest())
        if rows:row['delta_from_previous_tstates']=total-rows[-1]['total_tstates']
        row['delta_from_baseline_tstates']=total-(rows[0]['total_tstates'] if rows else total)
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(complete=True,scope=__doc__,source_samples=samples,verified_padding_samples=2,
                payload_bytes=stream_size,stored_dictionary_bytes=len(packed_book),
                expanded_dictionary_ram_bytes=2048,framing_allowance_bytes=32,
                pcm16_to_codec_ratio=2*samples/(stream_size+len(packed_book)+32),
                ratio_including_pointer_tables=2*samples/(stream_size+len(packed_book)+32+512),
                rows=rows,integrated_trd_tested=False,physical_hardware_tested=False,
                comparison_scope='Exact unchanged PCM, output writes and loop control; excludes IMA encoding and startup/ROM/ULA/banking')
    save(out/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input,a.output)
