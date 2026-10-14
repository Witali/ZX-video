"""Complete fixed-corpus byte parity and DLL/standalone C wall-time evidence.

Run from the research worktree. The archived whole Python reference is used
by default; --python-reference repeats every unchanged Python sample loop.
No player execution or new audio-quality claim is made by this speed audit.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np

from clock_control import prepare,PARAMETERS
from general import models,timeline
from ima_waveform_encoder import encode_waveform
from native_waveform_encoder import encode_waveform_native,write_workset,execute_workset,build_executable,_load
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from build_pdm import CPU_CLOCK
from ima_codec import require_unclipped


NAMES=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam')
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python-reference',action='store_true')
    parser.add_argument('--source',action='append')
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/native-waveform-final'))
    args=parser.parse_args();scratch=args.scratch.resolve();scratch.mkdir(parents=True,exist_ok=True)
    evidence=Path('audiobook-beeper/experiments/song-snr/evidence')
    archive=json.loads((Path(__file__).parent/'python-reference.json').read_bytes())
    assert archive['parameters']==PARAMETERS
    reference={row['source']:row for row in archive['rows']}
    model=dict(models())[PARAMETERS['model_name']];assert model==archive['model']
    started=time.perf_counter();library=_load();executable=build_executable();startup=time.perf_counter()-started
    rows=[]
    report=dict(date='2026-10-14',complete=False,scope='All requested complete sources; C DLL and separate standalone executable against archived full unchanged Python outputs and saved clock-joint streams. Same arrays, no fitted gain/delay/clock. No new player execution or quality qualification.',parameters=PARAMETERS,model=model,startup_seconds=startup,numpy_version=np.__version__,matrix_library=library._nwf_blas_path,matrix_library_sha256=sha(Path(library._nwf_blas_path).read_bytes()),native_source_sha256=library._nwf_source_sha256,executable=str(executable),child_python_runtime=False,rows=rows)
    for name in args.source or NAMES:
        start=time.perf_counter();source=wav8(evidence/'general/inputs'/(name+'.wav'))
        assert sha(source.tobytes())==reference[name]['input_sha256']
        times=timeline(len(source),'pentagon');target=compensate(source,times[::16],period=CPU_CLOCK/8000)
        desired,features,ids,nxt,_=prepare(source,times,model);preparation=time.perf_counter()-start
        inputs=(target,desired,features,ids,nxt);statistics={}
        start=time.perf_counter();native=encode_waveform_native(*inputs,statistics=statistics);native_seconds=time.perf_counter()-start
        assert sha(native)==reference[name]['packed_sha256'],name+' differs from complete Python reference'
        saved=gzip.decompress((evidence/'clock-joint'/name/'soundtrack.ima.gz').read_bytes())
        assert native==saved,name+' differs from saved Python clock-joint'
        python_seconds=reference[name]['python_seconds']
        if args.python_reference:
            start=time.perf_counter();python=encode_waveform(*inputs,width=32,block_size=128,commit_size=64,regularization=.1,backend='native');python_seconds=time.perf_counter()-start
            assert native==python,name+' differs from freshly repeated Python reference'
        with tempfile.TemporaryDirectory(dir=scratch,prefix=name+'-') as temporary:
            root=Path(temporary);workset=root/'source.nwf';output=root/'encoded.ima'
            start=time.perf_counter();write_workset(workset,*inputs);workset_seconds=time.perf_counter()-start
            workset_bytes=workset.stat().st_size;workset_sha=sha(workset.read_bytes());standalone_statistics={}
            start=time.perf_counter();standalone=execute_workset(workset,output,standalone_statistics);standalone_seconds=time.perf_counter()-start
            assert standalone==native,name+' standalone bytes differ'
        row=dict(source=name,samples=len(source),input_sha256=sha(source.tobytes()),packed_sha256=sha(native),saved_python_packed_sha256=sha(saved),all_bytes_identical=True,python_reference_freshly_repeated=args.python_reference,python_reference_seconds=python_seconds,complete_c_seconds=native_seconds,standalone_seconds=standalone_seconds,speedup_vs_python=python_seconds/native_seconds,preparation_seconds=preparation,workset_write_seconds=workset_seconds,workset_bytes=workset_bytes,workset_sha256=workset_sha,packet_shapes=len(features),statistics=statistics,standalone_statistics=standalone_statistics,saturation_guard=require_unclipped(native))
        rows.append(row);(scratch/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({key:row[key] for key in ('source','samples','all_bytes_identical','complete_c_seconds','standalone_seconds','speedup_vs_python','packet_shapes')}),flush=True)
    report['complete']=list(args.source or NAMES)==list(NAMES)
    producers=('audiobook-beeper/native_waveform_encoder.c','audiobook-beeper/native_waveform_encoder.py','audiobook-beeper/test_native_waveform_encoder.py','audiobook-beeper/ima_waveform_encoder.py','audiobook-beeper/waveform_kernel.py','audiobook-beeper/ima_beam.py','audiobook-beeper/experiments/song-snr/clock_control.py','audiobook-beeper/experiments/song-snr/general.py',str(Path(__file__)))
    report['producer_sha256']={name:sha(Path(name).read_bytes()) for name in producers}
    (scratch/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
