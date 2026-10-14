"""Combine the four native and two complete actual sector-cadence UI proofs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',type=Path,required=True)
    args=parser.parse_args()
    metadata=args.metadata.resolve()
    meta=json.loads(metadata.read_text())
    natives=[]
    for profile in ('128','scorpion','pentagon512','pentagon1024'):
        proof=json.loads((HERE/('native-'+profile+'.json')).read_text())
        provenance=json.loads((HERE/('native-'+profile+'-provenance.json')).read_text())
        assert proof['complete'] and proof['bits_verified']==11526111
        assert provenance['trd_sha256']==meta['trd_sha256']
        natives.append(dict(profile=profile,report='native-'+profile+'.json',
                            provenance='native-'+profile+'-provenance.json',
                            bits_verified=proof['bits_verified'],reloads=proof['reloads'],
                            maximum_hold_tstates=proof['maximum_native_hold_tstates']))
    captures=[]
    for suffix,profile in (('512','pentagon512'),('1024','pentagon1024')):
        folder=HERE/('installed-full-'+suffix)
        run=json.loads((folder/'report.json').read_text())
        assert run['complete'] and run['profiles']==[profile]
        assert run['ui_trd_sha256']==meta['trd_sha256']
        assert run['fuse_executable_sha256']=='e7aba457ea405f8e2fcab9d4bc703e9f1013453726e178d8c7333ce9685a1266'
        proof=run['independent_cold_Fuse_runs'][0]
        assert proof['complete'] and proof['bits_verified']==11526111
        assert proof['every_source_bit_and_state_exact']
        assert proof['audio_progress_ui']['complete']
        assert proof['before_after_ui_clock']['maximum_introduced_timing_change_tstates']==0
        geometry=[]
        for update in proof['audio_progress_ui']['live_progress']:
            # A bank event precedes the pending last source bit. The decoder
            # has consumed two initial samples and one bit, hence +33 pulses
            # recovers the exact compressed-byte boundary independently of
            # the player's precomputed bar commands.
            assert (update['pulse']+33)%8192==0
            consumed=(update['pulse']+33)//32
            expected=32*consumed//(meta['audio_sectors']*256)
            assert update['filled_columns']==expected
            geometry.append(dict(pulse=update['pulse'],compressed_bytes_consumed=consumed,
                expected_filled_columns=expected,actual_filled_columns=update['filled_columns']))
        assert len(geometry)==22
        captures.append(dict(profile=profile,report=(folder/'report.json').relative_to(HERE).as_posix(),
            source_bits_verified=proof['bits_verified'],reloads=proof['reloads'],
            source_clock=proof['before_after_ui_clock'],ui=proof['audio_progress_ui'],
            exact_global_prefix_geometry=True,global_prefix_geometry=geometry))
    producer=HERE/'producer-source'
    producer.mkdir(exist_ok=True)
    hashes={}
    for path in (ROOT/'audiobook-beeper/verify_stream_trd.py',HERE/'verify.py',HERE/'finish.py'):
        data=path.read_bytes()
        hashes[path.relative_to(ROOT).as_posix()]=sha(data)
        (producer/(path.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    (producer/'player.json.gz').write_bytes(gzip.compress(metadata.read_bytes(),mtime=0))
    report=dict(date='2026-10-14',complete_audio=True,complete_ui=True,
        ui_trd_sha256=meta['trd_sha256'],packed_sha256=meta['packed_sha256'],
        source_samples=meta['pcm_samples'],native_profiles=natives,Fuse_profiles=captures,
        strict_loading_phase_acceptance_preserved=True,
        quality_reuse=dict(snr_db=20.25031588676249,remeasured=False,
            scope='Exact compressed input/model and every complete actual source pulse/time match the prior best disk. Explicit post-source mute is reported separately.'),
        producer_sha256=hashes,physical_hardware_tested=False,
        screen_scope='Actual control bytes observed during complete cold Fuse runs; unchanged pixels outside the UI come from the exact COVER file, rather than a full-screen debugger dump.',
        failed_initial_attempt='../audio-ui-emulator/frames-phase-control.json')
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(complete_audio=True,complete_ui=True,trd_sha256=meta['trd_sha256'],
                          native_profiles=4,Fuse_profiles=2)))


if __name__=='__main__':main()
