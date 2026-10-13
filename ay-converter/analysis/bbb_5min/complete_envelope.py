"""Package the accepted complete hardware-envelope fit and listening audio."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
HERE=Path(__file__).resolve().parent;CORE=HERE.parents[1];sys.path.insert(0,str(CORE))
from ay_format import AyFrame,registers
from music_player import build_disk
from verify_preview import expected_registers,native_check,extract_player
import quality


def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('fit',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--node',required=True);args=parser.parse_args()
    root=args.baseline;out=args.output
    if out.exists() and any(out.iterdir()):raise ValueError('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'report.json').read_bytes());envelope=json.loads((args.fit/'hardware-envelope.json').read_bytes())
    raw=gzip.decompress((args.fit/'registers.gz').read_bytes())
    assert envelope['selected'] and sha(raw)==envelope['registers_sha256'] and len(raw)==15000*14
    assert envelope['initial_registers_sha256']==report['registers_sha256']
    assert envelope['normalized_pcm_sha256']==report['input_normalization']['normalized_pcm_sha256']
    rows=np.frombuffer(raw,np.uint8).reshape(-1,14)
    frames=[AyFrame(tuple(int(row[c*2])+(int(row[c*2+1])<<8) for c in range(3)),
        tuple(map(int,row[8:11])),int(row[6]),int(row[7]),int(row[11])+(int(row[12])<<8),int(row[13]),12) for row in rows]
    packed=b''.join(frame.serialize() for frame in frames)
    assert expected_registers(packed,12)==raw and b''.join(registers(f) for f in frames)==raw
    for name in ('registers.gz','hardware-envelope.json'):shutil.copyfile(args.fit/name,out/name)
    (out/'soundtrack.ay12.gz').write_bytes(gzip.compress(packed,mtime=0))
    for name in ('input-normalization.json','simulation-feedback.json','noise-fit.json.gz','mixer-fit.json.gz',
        'scheduling-check.json','objective-check.json','original-preview.wav','note-events.json'):
        shutil.copyfile(root/name,out/name)
    shutil.copytree(root/'baseline',out/'baseline')
    shutil.copyfile(root/'ay-preview.wav',out/'baseline/ay-before-hardware.wav')
    save(out/'baseline/pre-envelope-report.json',report)
    states=json.loads(gzip.decompress((root/'channel-states.json.gz').read_bytes()))
    for state,frame in zip(states['states'],frames):
        state.update(volumes=list(frame.volumes),mixer=frame.mixer,envelope_period=frame.envelope_period,
            envelope_shape_write=frame.envelope_shape,envelope_channels=[c for c in range(3) if frame.volumes[c]&16])
    (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(states,separators=(',',':')).encode(),mtime=0))
    fit=json.loads((root/'analysis.json').read_bytes())
    fit.update(hardware_envelope=envelope,model='persistent_components_and_running_hardware_envelope_v6',
        packed_state_bytes=12,register_bytes_per_state=14)
    save(out/'analysis.json',fit)
    subprocess.run([args.node,str(CORE/'render_ym2149.js'),str(out/'registers.gz'),str(out/'chip.f32'),
        '50',str(out/'chip-render.json'),'14'],check=True)
    rendered=np.fromfile(out/'chip.f32','<f4').astype(float)
    assert len(rendered)==300*44100
    quality.write_wav(out/'ay-preview.wav',rendered*report['fixed_model_gain'],44100)
    (out/'chip.f32').unlink()
    parts=[]
    for number,lo in enumerate((0,5000,10000),1):
        part=out/f'part{number:02d}';part.mkdir()
        regs=raw[lo*14:(lo+5000)*14];ay=packed[lo*12:(lo+5000)*12]
        disk,metadata=build_disk(regs,title=f'BIG BUCK BUNNY {number}/3',loop=False,assembly_dir=part/'assembly',register_bytes=14)
        (part/'audio-preview.trd').write_bytes(disk)
        (part/'registers.gz').write_bytes(gzip.compress(regs,mtime=0))
        (part/'soundtrack.ay12.gz').write_bytes(gzip.compress(ay,mtime=0))
        save(part/'player.json',metadata)
        native=native_check(extract_player(disk),metadata,regs);save(part/'native.json',native)
        save(part/'report.json',dict(complete=True,preview_only=True,ticks=5000,duration_seconds=100,
            start_seconds=lo/50,profile='auto',loop_playback=False,disk_timing_verified=False,hardware_tested=False,
            artifacts={p.relative_to(part).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in part.rglob('*') if p.is_file()}))
        parts.append(dict(number=number,start_tick=lo,end_tick=lo+5000,duration_seconds=100,
            disk=(part/'audio-preview.trd').relative_to(out).as_posix(),trd_sha256=sha(disk),native=native))
    report.update(parts=parts,registers_sha256=sha(raw),packed_sha256=sha(packed),packed_state_bytes=12,register_bytes_per_state=14,
        hardware_envelope=envelope,all_disks_fuse_verified=False,
        limits='Three independently bootable one-shot resident disks, 100 s each. Manual disk swaps pause sound; the full 300-s WAV is continuous. No complete film rebuild or physical-hardware claim.')
    save(out/'report.json',report)
    print(json.dumps(dict(complete=True,seconds=300,ticks=15000,disks=3,hardware_envelope_ticks=envelope['envelope_channel_ticks'],
        native_register_writes=sum(p['native']['register_writes'] for p in parts))),flush=True)


if __name__=='__main__':main()
