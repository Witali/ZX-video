"""Prove identical video/AY streams and per-frame mask-path CPU deltas."""
import argparse
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from profile_integrated_timing import stats
from test_fast_cell_masks import delta,FastCellMaskTests


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();inputs=[]
    for folder in (a.before,a.after):
        records=json.loads((folder/'volumes.json').read_bytes());assert len(records)==1
        r=records[0];m=json.loads((folder/r['metadata']).read_bytes());work=folder/'work'/Path(r['file']).stem
        cpu=json.loads((work/'cpu.json').read_bytes());assert cpu['complete'] and cpu['all_native_screens_exact']
        hashes={name:sha((work/name).read_bytes()) for name in ('codebook.raw','codebook.stream','audio.ayh1')}
        inputs.append((m,cpu,hashes,work))
    before,after=inputs
    assert before[2]==after[2]
    assert before[0]['frame_start']==after[0]['frame_start'] and before[0]['frames']==after[0]['frames']
    assert before[0]['states_sha256']==after[0]['states_sha256']
    assert not before[0]['cell_codebook']['native'].get('fast_masks',False)
    assert after[0]['cell_codebook']['native']['fast_masks']
    raw=(after[3]/'codebook.raw').read_bytes();at=2056;deltas=[]
    while at<len(raw):
        size=struct.unpack_from('<H',raw,at)[0];at+=2
        if size&32768:at+=(size&32767)*3;continue
        packet=raw[at:at+size];at+=size;deltas.append(delta(packet))
    assert len(deltas)==after[0]['frames']
    # Frame zero is primed inside the bootstrap; per-call CPU records start at one.
    assert len(before[1]['frames'])==len(after[1]['frames'])==len(deltas)-1
    frames=[]
    for i,(b,c) in enumerate(zip(before[1]['frames'],after[1]['frames']),1):
        assert b['frame']==c['frame']
        old,new=b['draw']['tstates'],c['draw']['tstates']
        assert new-old==deltas[i],(i,old,new,deltas[i])
        packet_delta=c['next_packet']['tstates']-b['next_packet']['tstates'] if b['next_packet'] else None
        frames.append(dict(frame=b['frame'],before=old,after=new,delta=new-old,next_packet_delta=packet_delta))
    cases=FastCellMaskTests();cases.test_all_masks_both_screens()
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='0bb033f',stream_sha256=before[2],
        states_sha256=before[0]['states_sha256'],frames=frames,
        before_draw=stats([f['before'] for f in frames]),after_draw=stats([f['after'] for f in frames]),
        delta_draw=stats([f['delta'] for f in frames]),all_frames_formula_delta=stats(deltas),
        next_packet_delta=stats([f['next_packet_delta'] for f in frames if f['next_packet_delta'] is not None]),
        next_packet_note='Unchanged stream; startup sector growth shifts track/side crossings and service calls. Do not assert equal packet cost.',
        cycle_cases=cases.results,
        code_bytes_before=before[0]['cell_codebook']['native']['code_bytes'],
        code_bytes_after=after[0]['cell_codebook']['native']['code_bytes'],
        used_sectors_before=before[0]['used_sectors'],used_sectors_after=after[0]['used_sectors'],
        trd_sha256_before=before[0]['trd_sha256'],trd_sha256_after=after[0]['trd_sha256'],
        cpu_sha256=[sha((v[3]/'cpu.json').read_bytes()) for v in inputs])
    write_json(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','cycle_cases','scope','cpu_sha256','stream_sha256')}))


if __name__=='__main__':main()
