"""Measure direct-player loop periods cheaply before a full output trace.

This is only a phase probe. It neither validates sample contents nor qualifies
a release; the complete native/Fuse checks remain mandatory after calibration.
"""
import argparse,gzip,json,re,shutil,subprocess
from pathlib import Path
from direct_player import build_disk
from smoke_test_fuse import hidden_startupinfo
from verify_pcm import save


def measure(out,fuse):
    meta=json.loads((out/'player.json').read_bytes());n=meta['outputs_per_cycle']
    stamp='spectrum:frames*70908+ula:tstates'
    lines=['base 10','set $r 0','set $bits 0',f"breakpoint {meta['player_labels']['ready']}",
           'commands 1','set $r 1','continue','end',
           'breakpoint port write 254','condition 2 $r==1','commands 2','set $bits $bits+1','continue','end',
           'breakpoint port write 254',f'condition 3 $r==1 && ($bits==1 || $bits=={n+1} || $bits=={2*n+1})',
           'commands 3','print '+stamp,'continue','end',
           'breakpoint port write 254',f'condition 4 $bits>={2*n+1}', 'commands 4','exit 77','end']
    script='\n'.join(lines);(out/'phase-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    result=subprocess.run([str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
                           '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())],
                          cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=180)
    (out/'phase-trace.txt').write_bytes(result.stdout);(out/'phase-stderr.txt').write_bytes(result.stderr)
    assert result.returncode==77,(result.returncode,result.stderr[:1000])
    times=[int(s,0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:\d+|0x[\da-fA-F]+)',s)]
    assert len(times)==3,times
    periods=[times[i+1]-times[i] for i in range(2)]
    report=dict(scope=__doc__,first_output_absolute_tstates=times,field_phases=[t%70908 for t in times],
                cycle_tstates=periods,target_cycle_tstates=1169*70908,
                deltas_from_target=[t-1169*70908 for t in periods],exact_repeat_phase=all(t==1169*70908 for t in periods),
                idle_pairs=meta['loop_idle_pairs'],idle_pad_tstates=meta['loop_idle_pad_tstates'])
    save(out/'phase-probe.json',report);print(json.dumps(report),flush=True);return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--pairs',type=int,required=True)
    p.add_argument('--pad',type=int,default=0);p.add_argument('--fuse',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if out.exists() and any(out.iterdir()):p.error('output must be empty')
    out.mkdir(parents=True);meta=json.loads((a.input/'player.json').read_bytes())
    packed=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes())
    disk,new_meta=build_disk(packed,out/'assembly',meta['model'],meta['hot_indices'],a.pairs,a.pad)
    if 'compensated_reference_rate_hz' in meta:new_meta['compensated_reference_rate_hz']=meta['compensated_reference_rate_hz']
    (out/'audiobook-preview.trd').write_bytes(disk);save(out/'player.json',new_meta)
    for name in ('source-preview.wav','soundtrack.ima.gz'):shutil.copy2(a.input/name,out/name)
    measure(out,a.fuse)


if __name__=='__main__':main()
