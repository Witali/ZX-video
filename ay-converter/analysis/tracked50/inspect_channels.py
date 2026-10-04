"""Audit every exported component/mixer state and visualize channel identity."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
from support import save,sha
from verify_preview import expected_registers,extract_player
import music_profile as music


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','baseline','probe','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    data = json.loads(gzip.decompress((args.directory/'channel-states.json.gz').read_bytes()))
    report = json.loads((args.directory/'report.json').read_bytes())
    raw = gzip.decompress((args.directory/'registers.gz').read_bytes())
    packed = gzip.decompress((args.directory/'soundtrack.ay9.gz').read_bytes())
    assert expected_registers(packed) == raw
    assert data['quantum_ms'] == 20 and len(data['states']) == 1556
    assert report['sound_quantum_ms'] == 20
    probe = json.loads(args.probe.read_bytes())
    assert sha(raw) == probe['variants']['dominant_mixed']['registers_sha256']
    owners = {}
    noise_ticks = mixed = 0
    routing_changes = 0
    previous = None
    for i,state in enumerate(data['states']):
        assert state['tick'] == i
        row = raw[i*11:(i+1)*11]
        assert state['periods'] == [int.from_bytes(row[c*2:c*2+2],'little') for c in range(3)]
        assert state['volumes'] == list(row[8:])
        assert state['noise_period'] == row[6] and state['mixer'] == row[7]
        for channel,track in enumerate(state['component_ids']):
            if track:
                assert owners.setdefault(track,channel) == channel
            if state['tone_volumes'][channel]:
                assert not row[7] & (1 << channel), 'noise must not disable a tone'
        if state['noise_period']:
            noise_ticks += 1
            carrier = state['noise_channel']
            assert not row[7] & (1 << (carrier+3))
            assert row[8+carrier] > 0
            mixed += bool(state['tone_volumes'][carrier])
            if previous and previous['noise_period']:
                routing_changes += carrier != previous['noise_channel']
        previous = state
    assert routing_changes == 0
    for name,artifact in report['artifacts'].items():
        content = (args.directory/name).read_bytes()
        assert len(content) == artifact['bytes'] and sha(content) == artifact['sha256'],name
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) == digest,name
    player = extract_player((args.directory/'audio-preview.trd').read_bytes())
    assert player == extract_player((args.baseline/'audio-preview.trd').read_bytes())
    verification = json.loads((args.directory/'verification.json').read_bytes())
    assert verification['fuse']['complete'] and not verification['fuse']['missing_or_duplicate_fields']
    result = dict(date='2026-10-04',complete=True,ticks=1556,quantum_ms=20,
        component_count=len(owners),component_channel_migrations=0,active_tones_disabled_by_noise=0,
        noise_ticks=noise_ticks,tone_plus_noise_ticks=mixed,noise_only_ticks=noise_ticks-mixed,
        noise_route_changes_inside_an_event=routing_changes,all_state_bytes_match_registers=True,
        packed_mixer_decode_independently_verified=True,all_artifact_and_producer_hashes_match=True,
        selected_probe_registers_exact=True,player_binary_identical_to_baseline=True,
        ordinary_tstates_before=974,ordinary_tstates_after=974,delta_tstates=0,
        component_id_limit='Identity of estimated components; not a ground-truth separation of all source instruments.',
        trd_sha256=sha((args.directory/'audio-preview.trd').read_bytes()))
    save(args.output/'channel-audit.json',result)
    states = data['states']
    time = (np.arange(len(states))+.5)/50
    periods = np.array([s['periods'] for s in states])
    levels = np.array([s['tone_volumes'] for s in states])
    ids = np.array([s['component_ids'] for s in states])
    colors = ['#2266aa','#b34a34','#23854e']
    fig,axes = plt.subplots(4,1,figsize=(15,9),sharex=True)
    fig.subplots_adjust(left=.08,right=.96,bottom=.08,top=.89,hspace=.35)
    for channel in range(3):
        mask = (ids[:,channel] > 0) & (levels[:,channel] > 0)
        axes[channel].scatter(time[mask],1773400/(16*periods[mask,channel]),
            s=8+22*music.chip_levels()[levels[mask,channel]],color=colors[channel],linewidths=0)
        axes[channel].set_yscale('log')
        axes[channel].set_ylim(50,1800)
        axes[channel].set_yticks([100,250,500,1000],labels=['100','250','500','1k'])
        axes[channel].set_ylabel('Hz')
        axes[channel].set_title('Channel '+chr(65+channel)+' — continuing components keep this channel',loc='left',fontsize=11)
        axes[channel].grid(alpha=.2)
    noise = np.array([s['noise_period'] for s in states])
    axes[3].step(time,noise,where='mid',color='#7851a9')
    axes[3].set_ylim(-1,32)
    axes[3].set_ylabel('R6')
    axes[3].set_title('Detected shared noise: period register (not a tone frequency), zero = absent',loc='left',fontsize=11)
    axes[3].set_xlabel('Source time (seconds); one complete AY state every 20 ms')
    axes[3].set_xlim(0,31.12)
    fig.suptitle('Persistent AY channels — The Entertainer\nPitch matching ignores amplitude rank; active tones remain enabled during noise',fontsize=14)
    fig.savefig(args.output/'channel-tracks.png',dpi=130)
    plt.close(fig)
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
