"""Three measured optimizations of exact ADPCM3-step6 -> IMA expansion."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from z80 import Z80Machine
from build_lpc_disk import assemble
from ima_codec import decode,STEPS,INDEX,require_unclipped
from verify_pcm import save
from convert_audio import pcm_wav


def run(source,out):
    out.mkdir(parents=True,exist_ok=True)
    stream=gzip.decompress((source/'adpcm3-step6.data.gz').read_bytes())
    codes=(np.unpackbits(np.frombuffer(stream,'u1')).reshape(-1,3)@np.array([4,2,1])).astype('u1')
    nibbles=codes<<1
    packed=(nibbles[::2]|(nibbles[1::2]<<4)).tobytes()
    pcm,indices=decode(packed)
    # Independent original three-bit recurrence proves no PCM requantization.
    predictor=index=0
    for i,code in enumerate(codes):
        step=STEPS[index];mag=int(code)&3
        delta=(step>>3)+(step//2 if mag&1 else 0)+(step if mag&2 else 0)
        predictor+=-delta if code&4 else delta
        index=max(0,min(88,index+(-1,-1,2,6)[mag]))
        assert predictor==int(pcm[i]) and index==int(indices[i])
    require_unclipped(packed)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    (out/'soundtrack.ima3.gz').write_bytes(gzip.compress(stream,mtime=0))
    pcm_wav(out/'expanded-preview.wav',np.clip((pcm.astype(np.int32)+32768)>>8,0,255).astype('u1'))
    tables=bytes(((v>>4)&14)|((v<<3)&224) for v in range(256))
    tables+=bytes(((v>>6)&2)|((v<<1)&224) for v in range(256))
    tables+=bytes((v&14)|((v&1)<<7) for v in range(256))
    tables+=bytes(((v>>2)&14)|((v<<5)&224) for v in range(256))
    rows=[]
    for version in range(4):
        work=out/f'round-{version}';work.mkdir(exist_ok=True)
        (work/'lookup.bin').write_bytes(tables)
        shutil.copy2(Path(__file__).with_name('ima3-expand.asm'),work/'expand.asm')
        groups_per_chunk=4096
        (work/'expand-config.inc').write_text(f'optimization: EQU {version}\ngroups: EQU {groups_per_chunk}\n')
        labels=assemble(work,'expand');blob=(work/'expand.bin').read_bytes()
        total=0;times=[];chunks=[];actual=bytearray()
        for offset in range(0,len(stream),groups_per_chunk*3):
            chunk=stream[offset:offset+groups_per_chunk*3];groups=len(chunk)//3
            m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,blob)
            m.set_memory_block(0xC000,chunk)
            # Start at the loop after equivalent setup; IX is the actual tail
            # length. Charge DI4 + LD SP/HL/DE10*3 + LD IX14 + LD B7 =55T.
            m.sp=0xBFF0;m.hl=0xC000;m.de=0x4000;m.ix=groups;m.b=1
            m.pc=labels['group_loop'];m.set_breakpoint(labels['group_loop']);m.set_breakpoint(labels['complete'])
            budget=100_000_000;m.ticks_to_stop=budget;start=budget
            before=bytes(m.memory[0x8000:0x9400])
            m.step_over_breakpoint()
            while m.pc!=labels['complete']:
                if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('expansion timeout')
                if m.pc in (labels['group_loop'],labels['complete']):
                    elapsed=start-m.ticks_to_stop;times.append(elapsed);start=m.ticks_to_stop
                    if m.pc!=labels['complete']:m.step_over_breakpoint()
            used=budget-m.ticks_to_stop
            data=bytes(m.memory[0x4000:0x4000+groups*4])
            assert data==packed[offset//3*4:(offset//3+groups)*4],(version,offset)
            assert bytes(m.memory[0x8000:0x9400])==before
            assert bytes(m.memory[0xC000:0xC000+len(chunk)])==chunk
            assert bytes(m.memory[0x4000+groups*4:0x8000])==b'\xa5'*(16384-groups*4)
            actual.extend(data);total+=used+55
            chunks.append(dict(input_bytes=len(chunk),output_bytes=len(data),tstates=used+55))
        assert bytes(actual)==packed
        assert len(set(times))==1,(version,sorted(set(times)))
        assert times[0]==(2515,1947,397,285)[version],('instruction count',version,times[0])
        row=dict(round=version,group_tstates=times[0],per_sample_tstates=times[0]/8,
                 total_tstates=total,cpu_only_seconds=total/3546900,
                 groups_verified=len(times),expanded_bytes_verified=len(actual),
                 every_byte_exact=True,code_tables_input_unchanged=True,
                 fixed_lookup_bytes=1024 if version==3 else 0,chunks=chunks,
                 binary_sha256=hashlib.sha256(blob).hexdigest())
        if rows:row['delta_from_previous_tstates']=total-rows[-1]['total_tstates']
        row['delta_from_baseline_tstates']=total-(rows[0]['total_tstates'] if rows else total)
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(complete=True,scope=__doc__,samples=len(pcm),pcm16_reference_bytes=len(pcm)*2,
                ima3_bytes=len(stream),ima_bytes=len(packed),framing_allowance_bytes=32,
                pcm16_to_ima3_ratio=len(pcm)*2/(len(stream)+32),
                ratio_including_fixed_lookup=len(pcm)*2/(len(stream)+32+1024),
                exact_three_bit_recurrence_verified=True,final_predictor=int(pcm[-1]),final_index=int(indices[-1]),
                rows=rows,physical_hardware_tested=False,integrated_trd_tested=False,
                limitation='Native CPU/buffer proof; excludes disk/ROM, ULA and full resident-bank loader. No PDM quality claim.')
    save(out/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.input,a.output)
