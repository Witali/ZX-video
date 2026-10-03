"""Execute a PVQ decoder CPU probe; no PDM, ULA or TRD timing claim."""
import argparse,ast,gzip,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from z80 import Z80Machine


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
    data=gzip.decompress((a.input/'pvq3x1024-half.data.gz').read_bytes())
    bits=np.unpackbits(np.frombuffer(data,'u1'));count=8196;codes=(bits[:count//3*10].reshape(-1,10)@(1<<np.arange(9,-1,-1))).astype(int)
    book=np.frombuffer(gzip.decompress((a.input/'pvq3x1024-half.book.gz').read_bytes()),'i1').reshape(1024,3)
    stream=bytearray()
    for start in range(0,len(codes),4):
        group=codes[start:start+4];assert len(group)==4
        stream.append(sum(int(code>>8)<<(2*i) for i,code in enumerate(group)))
        stream.extend((group&255).tolist())
    expected=[];last=128
    for code in codes:
        base=last//2+64;values=book[code].astype(int)+base
        assert np.all((values>=0)&(values<=255));expected.extend(values);last=int(values[-1])
    # One unused guard byte per vector simplifies address formation in this probe.
    dictionary=np.full((1024,4),0xa5,dtype='u1');dictionary[:,:3]=book.view('u1')
    (out/'dictionary.bin').write_bytes(dictionary.tobytes())
    (out/'pointer-low.bin').write_bytes(bytes((i*4)&255 for i in range(256)))
    (out/'pointer-high.bin').write_bytes(bytes(0x90+(i>>6) for i in range(256)))
    (out/'compressed.bin').write_bytes(stream)
    shutil.copy2(Path(__file__).with_name('probe-pvq-decoder.asm'),out/'player.asm')
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],cwd=out,capture_output=True,text=True)
    (out/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,(out/'player.bin').read_bytes());m.set_memory_block(0xc000,stream)
    before=bytes(m.memory);times=[];actual=[];budget=10_000_000
    def emit(port,value):
        assert port&255==1
        actual.append(value);times.append(budget-m.ticks_to_stop)
        if len(actual)==count:m.set_breakpoint(m.pc)
    m.set_output_callback(emit);m.pc=labels['start'];m.ticks_to_stop=budget
    while len(actual)<count:
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('native probe timeout')
    assert actual==expected and bytes(m.memory)==before
    intervals=np.diff(times);sample=np.arange(1,count)
    wanted=np.where(sample%3,51,np.where(sample%12,193,216))+21
    assert np.array_equal(intervals,wanted),list(zip(intervals[:16],wanted[:16]))
    report=dict(scope=__doc__,samples_verified=count,complete_input_samples=186880,partial_source_probe=True,
                every_pcm_byte_exact=True,all_memory_unchanged=True,header_layout='four 10-bit indices: one low-first high-field byte then four low bytes',
                decoder_body_tstates=dict(within_vector=51,new_vector=193,new_header_and_vector=216,mean_per_12_samples=100.25),
                test_driver_excluded_tstates=21,ima_direct_decoder_and_nibble_control_tstates=131,
                mean_delta_tstates=-30.75,worst_delta_tstates=85,
                dictionary_data_bytes=3072,dictionary_probe_ram_bytes=4096,pointer_table_bytes=512,
                full_source_grouped_payload_bytes=((186880+11)//12)*5,
                full_source_grouped_payload_over_bitpacked_bytes=((186880+11)//12)*5-len(data),
                all_source_codec_quality_report=str(a.input/'report.json'),
                binary_sha256=hashlib.sha256((out/'player.bin').read_bytes()).hexdigest(),
                real_time_pdm_verified=False,decision='Promising average CPU budget; boundary work must be prefetched/interleaved before a PDM player can qualify.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
