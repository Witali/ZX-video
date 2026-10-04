"""Close the follow-up worklist: extra exact checks, reproducible images, archived timing evidence."""
import gzip
import json
import struct
import subprocess
import sys
from check_primitives import primitives,audit
from check_streams import control_cases
from verify import native,ROOT,HERE,sha,image


def digest(folder):
    mem=image(folder/'player.ihx')
    return sha(bytes(mem[a] for a in sorted(mem)))


def main():
    out=ROOT/'build/speex-port';folder=out/'pure-r9';fresh=out/'followup-rebuild'
    subprocess.run([sys.executable,str(HERE/'build.py'),'--skip-host','--output',str(fresh)],check=True)
    assert digest(fresh/'pure-r9')==digest(folder)==json.loads((HERE/'rounds/09/report.json').read_text())['binary_sha256']
    final=dict(fresh_default_build_sha256=digest(folder),general_primitives=primitives(folder),controls=control_cases(folder))
    random=out/'checks/random-packets';random.mkdir(exist_ok=True)
    for name in ('input.spxraw','reference.pcm16'):
        (random/name).write_bytes(gzip.decompress((HERE/'rounds/05'/('random-'+name+'.gz')).read_bytes()))
    r=native(random,'pure-r9',folder);r.pop('out_intervals_histogram',None)
    final['random_packets']=r
    silence=out/'checks/silence'
    final['cached_silence_audit']=audit(folder,(silence/'input.spxraw').read_bytes(),(silence/'reference.pcm16').read_bytes(),frames=2)
    # Reuse the completed same-binary full speech and signal/capacity runs.
    checks=json.loads((HERE/'rounds/09/checks.json').read_text())
    speech=json.loads((HERE/'rounds/09/report.json').read_text())
    for item in [speech,*checks['fixtures'].values(),r]:
        assert item['binary_sha256']==digest(folder)
        assert item['complete'] and item['every_pcm8_exact'] and item['every_pcm16_exact']
    final['exact_samples_verified']=speech['samples']+sum(x['samples'] for x in checks['fixtures'].values())+r['samples']
    manifest=json.loads((HERE/'evidence/manifest.json').read_text())
    for path,want in manifest.items():
        data=(HERE/path).read_bytes()
        if not path.endswith('.gz'):data=data.replace(b'\r\n',b'\n')
        assert sha(data)==want,('baseline evidence changed',path)
    for round_id in ('07','08','09','10'):
        p=HERE/'rounds'/round_id
        assert digest(p)==json.loads((p/'report.json').read_text())['binary_sha256']
    pvq=HERE/'rounds/12';report=json.loads((pvq/'report.json').read_text())
    assert digest(pvq)==report['paced']['binary_sha256']
    assert sha(gzip.decompress((pvq/'audio.pvq.gz').read_bytes()))==report['encoded_sha256']
    ticks=struct.unpack('<'+'Q'*report['samples'],gzip.decompress((pvq/'out-times.u64.gz').read_bytes()))
    assert all(t-ticks[0]==437*i+i//2 for i,t in enumerate(ticks))
    final['archived_pvq_deadlines_verified']=len(ticks)
    final['baseline_manifest_unchanged']=True
    final['selection']=dict(exact_speex='pure-r9',exact_real_time=False,nominal_cpu_pcm8_player='PVQ3x1024',
                            approximate_speex_selected=False,wavetable_selected=False,ula_and_hardware_verified=False)
    (HERE/'FOLLOWUP_VERIFICATION.json').write_text(json.dumps(final,indent=2)+'\n')
    print('Follow-up complete:',final['exact_samples_verified'],'exact samples;',len(ticks),'PVQ deadlines checked.',flush=True)


if __name__=='__main__':main()
