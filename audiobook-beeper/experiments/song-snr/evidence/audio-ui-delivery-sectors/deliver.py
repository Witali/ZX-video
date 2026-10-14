"""Verify the completed UI release evidence, then update the named snapshot."""
import gzip
import hashlib
import json
from pathlib import Path


HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
MAIN=REPO.parents[1]
EVIDENCE=HERE.parent
EXECUTION=EVIDENCE/'audio-ui-emulator-sectors'
NAME='ZX-music-Sea-Foam-SNR20-RAM-auto.trd'
OLD='ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074'
NEW='b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e'


def sha(data):return hashlib.sha256(data).hexdigest()


def read(path):return json.loads(path.read_bytes())


def main():
    selected=(HERE/'generated/audio.trd').read_bytes()
    meta=read(HERE/'generated/player.json')
    generation=read(HERE/'generated/generation.json')
    execution=read(EXECUTION/'report.json')
    assert sha(selected)==NEW==meta['trd_sha256']==execution['ui_trd_sha256']
    assert len(selected)==655360 and generation['only_player_file_changes']
    assert execution['complete_audio'] and execution['complete_ui']
    before=(EVIDENCE/'achieved-disk/generated/audio.trd').read_bytes()
    assert sha(before)==OLD and before[:4352]==selected[:4352] and before[20736:]==selected[20736:]
    profiles=[]
    for profile in ('128','scorpion','pentagon512','pentagon1024'):
        native=read(EXECUTION/('native-'+profile+'.json'))
        assert native['complete'] and native['bits_verified']==11526111
        assert native['every_bit_predictor_index_exact'] and native['every_continuous_native_hold_exact']
        assert native['memory_guards_passed']
    for size in (512,1024):
        profile='pentagon'+str(size)
        folder=EXECUTION/('installed-full-'+str(size))/profile
        report=read(folder/'report.json')
        clock=read(folder/'clock-comparison.json')
        assert report['complete'] and report['trd_sha256']==NEW
        assert report['bits_verified']==11526111 and report['every_source_bit_and_state_exact']
        assert report['reloads']==report['runtime_disk_reads_during_live_audio']==0
        assert clock['every_relative_source_out_timestamp_exact'] and clock['maximum_introduced_timing_change_tstates']==0
        actual=gzip.decompress((folder/'times.u32.gz').read_bytes())
        previous=gzip.decompress((EVIDENCE/'clock-joint/sea_foam/verification'/profile/'times.u32.gz').read_bytes())
        assert actual==previous and len(actual)==11526111*4
        ui=report['audio_progress_ui'];assert ui['complete']
        assert ui['loading_dot_phases']==[1+i%3 for i in range(92)]
        assert len(ui['live_progress'])==22
        for observation in ui['live_progress']:
            assert (observation['pulse']+33)%32==0
            consumed=(observation['pulse']+33)//32
            assert observation['filled_columns']==32*consumed//meta['packed_bytes']
        profiles.append(dict(profile=profile,complete=True,source_pulses_verified=11526111,
            every_relative_source_timestamp_exact=True,reloads=0,loading_dot_phases=92,
            live_progress_updates=22,teardown_mute_delta_tstates=clock['teardown_mute']['delta_tstates'],
            report=folder.relative_to(REPO).as_posix(),report_sha256=sha((folder/'report.json').read_bytes())))
    copies=[]
    for destination in (REPO/NAME,MAIN/NAME):
        if destination.exists():
            assert sha(destination.read_bytes()) in (OLD,NEW), 'Unexpected existing named snapshot; preserve it'
        destination.write_bytes(selected)
        assert sha(destination.read_bytes())==NEW
        copies.append(dict(path=str(destination),bytes=len(selected),sha256=NEW))
    result=dict(date='2026-10-14',complete=True,name=NAME,trd_sha256=NEW,
        previous_trd_sha256=OLD,encoder='c',external_conversion_seconds=generation['external_process_wall_seconds'],
        snr_db=20.25031588676249,source_waveform_and_clock_exact=True,
        raw_post_source_mute_interval_reported_separately=True,
        full_cold_Fuse=profiles,copies=copies,physical_hardware_tested=False,
        source_independent_noise_research_complete=False)
    (HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
