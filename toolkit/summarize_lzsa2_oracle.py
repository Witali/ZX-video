"""Archive exact-parser evidence without presenting short cases as playback."""
import argparse,gzip,json
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('work','output','evidence'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();probe=json.loads((a.work/'probe.json').read_bytes());cpu=json.loads((a.work/'cpu.json').read_bytes())
    assert probe['complete'] and cpu['complete']
    assert probe['native_cases']==len(cpu['blocks'])==len(cpu['independent'])
    for name,digest in probe['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==digest,name
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert probe['raw_sha256']==retained['video_sha256'] and probe['baseline_stream_sha256']==retained['stream_sha256']
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    result={k:v for k,v in probe.items() if k!='rows'}
    result.update(root_trd_unchanged=True,root_trd_sha256=retained['trd_sha256'],
        current_measured_fps=retained['fps'],current_missed_deadlines=retained['missed_nominal_deadlines'],
        candidate_playback_measured=False,goal_achieved=False,
        decision='No compression-size gap found in this bounded corpus. Retain the exact oracle as a verifier; do not replace the production parser. Some equal-size alternatives are faster, others slower.',
        next='On one complete difficult LZSA2 block, optimize valid match distances while retaining command positions/lengths and the original byte budget. Preserve full last-offset/nibble state and verify actual decoder costs; short reset snippets cannot be spliced into production.')
    faster=[r for r in probe['rows'] if r.get('decoder_delta_tstates',0)<0]
    result['faster_examples']=sorted(faster,key=lambda r:r['decoder_delta_tstates'])[:4]
    result['evidence']=[];a.evidence.mkdir(parents=True,exist_ok=True)
    for n in ('probe.json','cpu.json'):
        data=(a.work/n).read_bytes();packed=gzip.compress(data,mtime=0);(a.evidence/(n+'.gz')).write_bytes(packed)
        result['evidence'].append(dict(file=n+'.gz',sha256=sha(packed),raw_sha256=sha(data)))
    result['source_sha256_lf']['summarize_lzsa2_oracle.py']=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('cases','strict_improvements','changed_equal_size_parses',
        'faster_equal_size_parses','video_faster_equal_size_parses','native_cases','root_trd_unchanged')}))


if __name__=='__main__':main()
