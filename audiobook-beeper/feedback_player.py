"""Build live IMA/block-feedback PDM without emitting machine instructions."""
import ast,gzip,hashlib,json,subprocess,sys,wave
from pathlib import Path
import numpy as np
from ima_codec import decoder_table,require_unclipped,encode
from ima_player import screen
from pdm_player import CPU_CLOCK,ORIGIN
from pcm_player import TrdFile,basic_line,place_files,calculate_file_start
from verify_pdm import save

HERE=Path(__file__).resolve().parent
INITIAL_STATE=34


def loading_screen(samples):
    """Ready image hides the startup-only message in its top 24 pixel rows."""
    from PIL import Image, ImageDraw, ImageFont
    from pcm_player import spectrum_bitmap_offset
    data=bytearray(screen(samples,'IMA / FEEDBACK PDM'))
    tile=Image.new('1',(256,24));draw=ImageDraw.Draw(tile)
    font=ImageFont.load_default(size=13);text='Loading audio data'
    box=draw.textbbox((0,0),text,font=font)
    draw.text(((256-(box[2]-box[0]))//2,4),text,font=font,fill=1)
    for y in range(24):
        for x in range(256):
            if tile.getpixel((x,y)):data[spectrum_bitmap_offset(x//8,y)]|=128>>(x&7)
    data[6144:6144+96]=bytes(96)
    return bytes(data)


def transition(pcm6,state):
    """Eight beta=.5 decisions; quantize/clamp history only at block end.

    Recent error has 16 midpoint bins in [-.5,.5], older error has four.
    Binary fractions are exact here; there is no floating-point roundoff in
    these eight steps. PCM uses the midpoint of its six-bit bin.
    """
    recent=((state>>2)*2-15)/32
    older=((state&3)*2-3)/8
    word=0
    for _ in range(8):
        value=(pcm6*4+2)/256+1.5*recent-.5*older
        bit=int(value>=.5)
        older,recent=recent,value-bit
        word=(word<<1)|bit
    i=max(0,min(15,int(np.floor(recent*16+8))))
    j=max(0,min(3,int(np.floor(older*4+2))))
    return word,(i*4+j)


def feedback_table():
    table=np.empty((64,64),dtype='<u2')
    for pcm in range(64):
        for state in range(64):
            word,nxt=transition(pcm,state)
            table[pcm,state]=word|(nxt*2<<8)
    return table.tobytes()


def layout():
    return [dict(bank=b,bytes=8192 if b==5 else 16384,sectors=32 if b==5 else 64,
                 address=0xe000 if b==5 else 0xc000,sector=0) for b in (0,4,6,1,3,7,5)]


def program(sections,work):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    source=(HERE/'ima-feedback-player.asm').read_text()
    (work/'player.asm').write_text(source,encoding='utf-8',newline='\n')
    config=['initial_predictor: EQU 0','initial_index: EQU 0',f'initial_feedback: EQU {INITIAL_STATE}']
    for i,s in enumerate(sections):
        config += [f'disk_{i}: EQU {(s["sector"]//16)*256+s["sector"]%16}',
                   f'address_{i}: EQU {s["address"]}',f'sectors_{i}: EQU {s["sectors"]}']
    (work/'config.inc').write_text('\n'.join(config)+'\n',encoding='ascii')
    (work/'decoder-table.bin').write_bytes(decoder_table(0x8700,False))
    (work/'pointer-low.bin').write_bytes(bytes((x&4)<<5 for x in range(256)))
    (work/'pointer-high.bin').write_bytes(bytes(0xa0+(x>>3) for x in range(256)))
    (work/'feedback.bin').write_bytes(feedback_table())
    (work/'screen.bin').write_bytes(loading_screen(sum(s['bytes'] for s in sections)*2))
    command=[sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm']
    result=subprocess.run(command,cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    labels=next(ast.literal_eval(x) for x in result.stdout.splitlines() if x.startswith('{'))
    blob=(work/'player.bin').read_bytes()
    assert len(blob)==23296 and labels['feedback']==0xa000
    return blob,labels


def build_disk(packed,work):
    sections=layout();assert len(packed)==sum(s['bytes'] for s in sections)
    guard=require_unclipped(packed)
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
                   basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
                   basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(23296),start=ORIGIN)])
    pos=track*16+sector
    for s in sections:s['sector']=pos;pos+=s['sectors']
    blob,labels=program(sections,work)
    files=[boot,TrdFile('PLAYER','C',blob,start=ORIGIN)];offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+s['bytes']],start=s['address']))
        offset+=s['bytes']
    disk,directory,capacity=place_files(files,'IMAPDM')
    labels['out_0_0_0']=labels['high_out0']
    meta=dict(origin=ORIGIN,sections=sections,player_labels=labels,directory=directory,capacity=capacity,
              code_bytes=labels['code_end']-ORIGIN,code_reserve=1792,resident_reserve=16384,
              table_base=0x8700,feedback_base=0xa000,feedback_bytes=8192,
              initial_predictor=0,initial_index=0,initial_feedback=INITIAL_STATE,
              initial_word_latency_slots=0,repeat=True,steady=True,record_stop_offset=2,
              paging_value_register='a',stack_top=0x6000,source_sample_rate_hz=8000,
              pcm_samples=2*len(packed),packed_bytes=len(packed),cpu_clock_hz=CPU_CLOCK,
              packed_sha256=hashlib.sha256(packed).hexdigest(),saturation_guard=guard,
              output_labels=[k for k in labels if '_out' in k],
              mutable_addresses=[labels['bank_jump']+1,labels['bank_jump']+2,labels['disk_position'],labels['disk_position']+1],
              feedback=True,ordinary_low_tstates=428,ordinary_high_tstates=[436,436,436,446],
              loading_message=dict(text='Loading audio data',attribute_address=0x5800,
                                   attribute_bytes=96,visible_attribute=0x47,hidden_attribute=0),
              ordinary_mean_tstates=433.25,ordinary_slots=8,unrolled_input_bytes=4,
              model=dict(beta=.5,pcm_levels=64,recent_error_bins=16,older_error_bins=4,
                         state_quantization='clipped midpoint bins over [-.5,.5], once per eight-bit block',rc=False),
              memory=dict(total_ram_bytes=131072,adpcm_bytes=len(packed),resident_code_and_tables=16384,
                          screen_bytes=6912,workspace_stack_bytes=1280,pcm_buffer_bytes=0,pdm_buffer_bytes=0),
              assembly=dict(instruction_bytes_emitted_by_python=False,assembler='pyz80 1.3.0',
                            binary_sha256=hashlib.sha256(blob).hexdigest()))
    assert sum(meta['memory'][k] for k in ('adpcm_bytes','resident_code_and_tables','screen_bytes','workspace_stack_bytes'))==131072
    return disk,meta


def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with wave.open(str(HERE/'ima-preview/pcm8k-preview.wav'),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,8000)
        pcm=np.frombuffer(w.readframes(sum(s['bytes'] for s in layout())*2),'u1').copy()
    # Shorten to the new full-memory capacity, retaining a 20-ms loop fade.
    pcm[-160:]=np.rint(128+(pcm[-160:].astype(float)-128)*np.linspace(1,0,160)).astype('u1')
    packed=encode(pcm)
    disk,meta=build_disk(packed,out/'assembly')
    with wave.open(str(out/'source-preview.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())
    (out/'audiobook-preview.trd').write_bytes(disk)
    (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    save(out/'player.json',meta)
    return disk,meta,packed


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();_,meta,_=prepare(args.output)
    print(json.dumps(meta))
