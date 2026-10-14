"""Score every complete prototype on its own executed Pentagon clock."""
import argparse
import gzip
import json
from pathlib import Path
import shutil

import numpy as np

from build_pdm import CPU_CLOCK,write_wav
from probe_reconstruction_error import wav8
from verify_direct import reference
from verify_pcm import save

from study import filtered,metrics,uniform
from general import timeline


def measure(root,profile,ffmpeg,scratch):
    meta=json.loads((root/'player.json').read_bytes());verify=root/'verification'/profile
    executed=json.loads((verify/'report.json').read_bytes());assert executed['complete'] and executed['trd_sha256']==meta['trd_sha256']
    packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes());source=wav8(root/'source-preview.wav')
    pcm,_,_,bits=reference(packed,cycles=1,model=meta['model'])
    raw=np.frombuffer(gzip.decompress((verify/'times.u32.gz').read_bytes()),'<u4').astype(float)
    count=executed['bits_verified'];assert len(raw)==count
    times=raw*CPU_CLOCK/3584000;expected=timeline(len(pcm),'pentagon')[:count]
    np.testing.assert_array_equal(times,expected)
    actual=filtered(bits[:count-1],times,ffmpeg,scratch)
    sample_edges=np.r_[times[::16],times[-1]];n=len(sample_edges)-1
    decoded=filtered((pcm[:n].astype(float)+32768)/65536,sample_edges,ffmpeg,scratch)
    shared=filtered(source[:n]/256,sample_edges,ffmpeg,scratch)
    values,edges=uniform(source/256,times[-1]);fixed=filtered(values,edges,ffmpeg,scratch)
    result=dict(complete=True,measured_on_own_complete_fuse_clock=True,source_samples=len(source),
                fixed_clock=metrics(fixed,actual),total_on_shared_clock_diagnostic=metrics(shared,actual),
                pdm_only_diagnostic=metrics(decoded,actual),trd_sha256=meta['trd_sha256'],
                complete_native_schedule_matches_every_actual_output_interval=True,
                main_release_or_physical_hardware_claim=False)
    write_wav(root/(profile+'-actual.wav'),actual*.5)
    save(verify/'quality.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('evidence',type=Path)
    p.add_argument('--scratch',type=Path,required=True);p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=True);root=a.evidence.resolve();rows=[]
    for name in ('speech','entertainer','sea_foam','loud3000','silence','quiet997'):
        dest=root/'prototype'/name;after=measure(dest,'pentagon512',a.ffmpeg,a.scratch)
        before=None
        if name in ('speech','entertainer'):
            before=measure(root/'legacy-controls'/name,'pentagon512',a.ffmpeg,a.scratch)
        elif name=='sea_foam':before=measure(root/'study/inputs/song','pentagon512',a.ffmpeg,a.scratch)
        row=dict(source=name,after=after,before=before,
                 actual_before_after_available=before is not None,shared_preset_for_every_source=True)
        if before:
            row['pdm_only_change_db']=after['pdm_only_diagnostic']['snr_db']-before['pdm_only_diagnostic']['snr_db']
            row['total_shared_clock_change_db']=after['total_on_shared_clock_diagnostic']['snr_db']-before['total_on_shared_clock_diagnostic']['snr_db']
        rows.append(row);print(json.dumps(row),flush=True)
        save(root/'prototype/quality-partial.json',dict(complete=False,rows=rows))
    save(root/'prototype/quality.json',dict(complete=True,rows=rows,source_specific_parameter_tuning=False,
         scope='Own complete Fuse clock; diagnostic gains distinguished from strict unfitted fixed8-kHz SNR; no unconditional source-independent release accepted'))


if __name__=='__main__':main()
