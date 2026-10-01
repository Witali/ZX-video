"""Archive exact-stream optional-read admission tests and complete window runs."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from optional_read_gate import build


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    stem='ZX-video-front_part07';folder=tmp/'optional-read-last-field-window';work=folder/'work'/stem
    oldfolder=tmp/'dictionary-budgeted-window';oldwork=oldfolder/'work'/stem
    m=read(folder/(stem+'.json'));old=read(oldfolder/(stem+'.json'))
    gate=m['optional_read_gate'];assert bytes.fromhex(gate['code_hex'])==build(m)[0]
    assert m['video_bytes']==old['video_bytes'] and m['lzsa2']['regions']==old['lzsa2']['regions']
    assert m['cell_codebook']['native']==old['cell_codebook']['native']
    hashes={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1','rows.json','states.npz'):
        data=(work/name).read_bytes();assert data==(oldwork/name).read_bytes();hashes[name]=sha(data)
    cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
    cpu=read(work/'cpu.json');fuse=read(work/'timing.json');before=read(oldwork/'timing.json')
    screens=read(work/'screens.json')
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['frames_checked']==256
    assert cpu['sector_cache_fifo_bounds_guarded']
    assert fuse['complete'] and not fuse['errors'] and not fuse['failure']
    assert fuse['trace_nonce_exact'] and fuse['ay_records_exact'] and fuse['runtime_sectors_checked']==719
    assert not fuse['audio_underruns'] and not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
    assert screens['complete'] and screens['full_screens_exact'] and screens['compared_bytes']==256*6912
    for r in (fuse,screens,cpu):assert r['trd_sha256']==m['trd_sha256']
    assert sha((work/'timing.trace.txt').read_bytes())==fuse['trace_sha256']
    testlog=(tmp/'optional-read-gate-tests.log').read_text();assert testlog.strip().endswith('OK') and "'cases': 1680" in testlog
    def timing(r):return {k:r[k] for k in ('nominal_late_frames','actual_out_over_one_field','max_late_fields','bad_actual_intervals','late_runs')}
    artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();data=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz');(a.evidence/filename).write_bytes(data)
        artifacts.append(dict(file=filename,raw_sha256=sha(raw),archive_sha256=sha(data),raw_bytes=len(raw),archive_bytes=len(data)))
    for path in sorted(folder.rglob('*')):
        if path.is_file() and not any(k in ('zx0','lzsa') for k in path.relative_to(folder).parts):
            if path.suffix in ('.json','.trd','.stream','.raw','.npz','.ayh1','.txt'):
                archive(path,path.relative_to(folder).as_posix().replace('/','-'))
    for name in ('optional-read-gate-tests.log','optional-read-last-field-build.log'):
        archive(tmp/name,name)
    # Preserve the superseded cold-only build's code/metadata, not a release.
    archive(tmp/'optional-read-window'/(stem+'.json'),'superseded-early-ready-metadata.json')
    archive(tmp/'optional-read-window/timing.json','superseded-early-ready-cold.json')
    strict=tmp/'optional-read-safe-window'
    for name in (stem+'.json','timing.json','work/'+stem+'/cpu.json','work/'+stem+'/timing.json',
                 'work/'+stem+'/timing.trace.txt','work/'+stem+'/screens.json'):
        archive(strict/name,'rejected-four-field-'+name.replace('/','-'))
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='d3127c0',scope=__doc__,
        frames=256,frame_start=4096,frame_end_exclusive=4352,source_hashes=hashes,
        trd_sha256=m['trd_sha256'],decoder_code_identical=True,renderer_code_identical=True,
        used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
        video_bytes=m['video_bytes'],pixel_changes=0,ay_changes=0,cold=cold,
        component_state_cases=1680,publication_races='At every gate instruction boundary; register-preserving publication state updates, not actual IRQ timing',
        gate=gate,gate_tstates_before=0,gate_tstates_after=[30,77,91,104,148,168,205,225,230,244,262,287,301],
        cycle_scope='Additional deterministic background-step admission instructions only; unchanged CALL costs 17 T before/after; excludes queued work, IRQ/ULA/ROM/physical disk latency',
        full_native_frames=256,full_fuse_screen_bytes=screens['compared_bytes'],fuse_ay_ticks=1280,fuse_runtime_sectors=719,
        timing_before=timing(before),timing_after=timing(fuse),
        rejected_four_field_timing=timing(read(strict/'work'/stem/'timing.json')),
        selected=False,
        decision='Reject both admission thresholds. The isolated frame-123 miss disappears, but reduced read-ahead increases sustained starvation: '
            'four fields gives 30 misses/max38/unrecovered EOF, two fields gives 11 misses/max15/recovery248, versus 9/max6/recovery245. '
            'Retain default player and exact-stream cached baselines. Resume verification of the already-built branch-bypass streaming decoder before another format or memory-layout experiment.',
        release_checks_pending=['complete volume','all four volumes','preceding-disk EOF continuations'],
        artifacts=artifacts,source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('optional_read_gate.py','test_optional_read_gate.py','cell_codebook_player.py','rebuild_cell_player.py','verify_optional_read_gate.py')})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),before=result['timing_before'],after=result['timing_after'],release=False)))


if __name__=='__main__':main()
