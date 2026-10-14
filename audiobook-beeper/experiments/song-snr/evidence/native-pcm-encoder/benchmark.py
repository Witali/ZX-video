"""Full-corpus fresh Python/C/standalone PCM-trellis parity and speed proof.

Historical general streams are checked and reported independently: agreement
with current Python is proved directly, never inferred from archived metadata.
No player instructions, preparation or source-clock measurement changes here.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np
from ima_beam import encode
from ima_codec import require_unclipped,decode
from native_ima_encoder import encode_pcm_native,execute_pcm_file,build_executable,_load
from probe_reconstruction_error import wav8


NAMES=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam')
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/native-pcm-final'))
    parser.add_argument('--source',action='append')
    args=parser.parse_args();scratch=args.scratch.resolve();scratch.mkdir(parents=True,exist_ok=True)
    evidence=Path('audiobook-beeper/experiments/song-snr/evidence')
    start=time.perf_counter();library=_load();binary=build_executable();startup=time.perf_counter()-start
    rows=[];report=dict(date='2026-10-14',complete=False,scope='Every requested complete original PCM source freshly encoded by unchanged ima_beam.py, complete C DLL and standalone C. Fixed width32/block64, zero initial state, all16 nibbles, full signed bounds. Historical streams checked independently. No new audio/player execution or quality claim.',startup_seconds=startup,parameters=dict(width=32,block_samples=64,predictor=0,index=0,allowed_codes=list(range(16)),predictor_bounds=[-32768,32767]),blas_dependency=False,child_python_runtime=False,numpy_version=np.__version__,native_source_sha256=library._nima_source_sha256,standalone_executable=str(binary),rows=rows)
    for name in args.source or NAMES:
        source=wav8(evidence/'general/inputs'/(name+'.wav'));statistics={}
        start=time.perf_counter();native=encode_pcm_native(source,statistics=statistics);c_seconds=time.perf_counter()-start
        start=time.perf_counter();python=encode(source,width=32,block_samples=64);python_seconds=time.perf_counter()-start
        assert native==python,name+' current Python/C mismatch'
        pcm,indices=decode(native);assert (int(pcm[-1]),int(indices[-1]))==(0,0),name+' silent guard lost'
        with tempfile.TemporaryDirectory(dir=scratch,prefix=name+'-') as temporary:
            root=Path(temporary);input_path=root/'source.raw';output=root/'encoded.ima';source.tofile(input_path)
            child={};start=time.perf_counter();standalone=execute_pcm_file(input_path,output,child);standalone_seconds=time.perf_counter()-start
            assert native==standalone,name+' standalone mismatch'
        historical_path=evidence/'general/inputs'/(name+'.ima.gz')
        historical=gzip.decompress(historical_path.read_bytes()) if historical_path.is_file() else None
        row=dict(source=name,samples=len(source),source_sha256=sha(source.tobytes()),packed_sha256=sha(native),fresh_python_sha256=sha(python),all_current_bytes_identical=True,python_seconds=python_seconds,c_seconds=c_seconds,standalone_seconds=standalone_seconds,speedup=python_seconds/c_seconds,historical_general_sha256=sha(historical) if historical is not None else None,historical_general_byte_identity=native==historical if historical is not None else None,historical_comparison='Byte comparison, not assumed from saved metadata',statistics=statistics,standalone_statistics=child,saturation_guard=require_unclipped(native))
        rows.append(row);(scratch/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({key:row[key] for key in ('source','samples','all_current_bytes_identical','python_seconds','c_seconds','standalone_seconds','speedup','historical_general_byte_identity')}),flush=True)
    report['complete']=list(args.source or NAMES)==list(NAMES)
    producers=('audiobook-beeper/native_ima_encoder.c','audiobook-beeper/native_ima_encoder.py','audiobook-beeper/test_native_ima_encoder.py','audiobook-beeper/ima_beam.py','audiobook-beeper/ima_codec.py','audiobook-beeper/waveform_kernel.py',str(Path(__file__)))
    report['producer_sha256']={name:sha(Path(name).read_bytes()) for name in producers}
    (scratch/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
