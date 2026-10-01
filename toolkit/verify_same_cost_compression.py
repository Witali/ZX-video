"""Verify/archive bounded encoder-only compression and native/Fuse evidence."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    stem='ZX-video-front_part07';folder=tmp/'dictionary-budgeted-window';work=folder/'work'/stem
    oldfolder=tmp/'sector-cache-window';oldwork=oldfolder/'work'/stem
    m=read(folder/(stem+'.json'));old=read(oldfolder/(stem+'.json'))
    distance=read(tmp/'lzsa2-same-cost/report.json');numbering=read(tmp/'dictionary-numbering/report.json')
    assert distance['complete'] and distance['individual_tokens_and_slices_no_slower'] and numbering['complete']
    flat=numbering['variants']['budgeted'];assert flat['host_candidate_eligible']
    assert flat['every_block_within_original_byte_and_cpu_budget']
    assert m['cell_codebook']['raw_sha256']==flat['raw_sha256'] and m['video_bytes']==flat['bytes']
    assert m['lzsa2']['regions']==old['lzsa2']['regions']
    assert m['cell_codebook']['native']==old['cell_codebook']['native']
    assert m['compressed_sector_cache']==old['compressed_sector_cache']
    assert (work/'audio.ayh1').read_bytes()==(oldwork/'audio.ayh1').read_bytes()
    cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
    cpu=read(work/'cpu.json');prior=read(oldwork/'cpu-cache-guard.json')
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['sector_cache_fifo_bounds_guarded']
    assert len(cpu['frames'])==len(prior['frames'])==255
    assert all(new['draw']['new_component_stages']==base['draw']['new_component_stages']
        for new,base in zip(cpu['frames'],prior['frames']))
    fuse=read(work/'timing.json');before=read(oldwork/'cache-timing.json');screens=read(work/'screens.json')
    assert fuse['complete'] and fuse['ay_records_exact'] and fuse['runtime_sectors_checked']==719
    assert not fuse['audio_underruns'] and not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
    assert screens['complete'] and screens['full_screens_exact'] and screens['compared_bytes']==256*6912
    for r in (fuse,screens):assert r['trd_sha256']==m['trd_sha256']
    assert (tmp/'dictionary-numbering-tests.log').read_text().strip().endswith('OK')
    def timing(r):return {k:r[k] for k in ('nominal_late_frames','actual_out_over_one_field','max_late_fields','bad_actual_intervals','late_runs')}
    artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();data=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz');(a.evidence/filename).write_bytes(data)
        artifacts.append(dict(file=filename,raw_sha256=sha(raw),archive_sha256=sha(data),raw_bytes=len(raw),archive_bytes=len(data)))
    for directory in (tmp/'lzsa2-same-cost',tmp/'dictionary-numbering',tmp/'dictionary-numbering-window',folder):
        for path in sorted(directory.rglob('*')):
            if not path.is_file() or any(k in ('lzsa','zx0') for k in path.relative_to(directory).parts):continue
            if path.suffix in ('.json','.trd','.stream','.raw','.npz','.ayh1','.txt'):
                archive(path,directory.name+'-'+path.relative_to(directory).as_posix().replace('/','-'))
    for name in ('dictionary-numbering-tests.log','dictionary-numbering-profile.json','lzsa2-same-cost.log','dictionary-budgeted.log'):
        archive(tmp/name,name)
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='bc615ab',
        scope='One cached CB46 [4096,4352) window. Host encoding only; unchanged decoder, renderer, AY and physical image content.',
        default_player_changed=False,pixel_changes=0,decoder_code_identical=True,renderer_code_identical=True,
        renderer_tstates_delta_per_frame=0,full_native_frames=256,full_fuse_screen_bytes=screens['compared_bytes'],
        cold=cold,distance_only=dict(bytes_saved=distance['saved_bytes'],
            decoder_delta_tstates=distance['candidate_decoder_tstates']-distance['baseline_decoder_tstates'],brute=distance['brute']),
        variants={name:{k:v[k] for k in ('bytes','sectors','bytes_delta','decoder_delta_tstates','host_candidate_eligible')}
            for name,v in numbering['variants'].items()},
        selected='budgeted',video_before_bytes=old['video_bytes'],video_after_bytes=m['video_bytes'],
        total_sectors_before=old['used_sectors'],total_sectors_after=m['used_sectors'],
        decoder_before_tstates=numbering['baseline_decoder_tstates'],decoder_after_tstates=flat['decoder_tstates'],
        max_slice_before_tstates=max(t for b in numbering['baseline_blocks'] for t in b['slices']),
        max_slice_after_tstates=max(t for b in flat['blocks'] for t in b['native']['slices']),
        slower_individual_blocks=sum(b['native']['tstates']>old['tstates'] for b,old in zip(flat['blocks'],numbering['baseline_blocks'])),
        every_block_within_original_byte_and_cpu_budget=True,
        short_matches_removed=sum(c['removed_matches'] for c in flat['changes']),
        next_packet_cpu_before=sum(f['next_packet']['tstates'] for f in prior['frames'] if f['next_packet']),
        next_packet_cpu_after=sum(f['next_packet']['tstates'] for f in cpu['frames'] if f['next_packet']),
        timing_before=timing(before),timing_after=timing(fuse),trd_sha256=m['trd_sha256'],
        decision='Retain budgeted dictionary numbering as a measured compression improvement: every block is no larger and '
            'no slower to decode; pixels and AY are exact. Do not claim a release: physical timing still fails both gates. '
            'The extra isolated late frame remains despite improved maximum lateness/interval counts. '
            'Full-volume and continuation checks remain required before generic integration or replacing root images.',
        artifacts=artifacts,source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('optimize_lzsa2_distances.py','probe_lzsa2_same_cost.py','probe_dictionary_numbering.py','test_dictionary_numbering.py',
             'fit_lzsa2_cpu_budget.py','rebuild_cell_player.py','verify_same_cost_compression.py','resumable_lzsa2.py','lzsa2_distance_cost.py')})
    write_json(a.output,result);print(json.dumps(dict(complete=True,artifacts=len(artifacts),saved_video_bytes=old['video_bytes']-m['video_bytes'],
        used_sectors=m['used_sectors'],decoder_delta=flat['decoder_tstates']-numbering['baseline_decoder_tstates'],release=False)))


if __name__=='__main__':main()
