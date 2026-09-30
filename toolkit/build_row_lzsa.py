"""Build one LZSA2 row-video comparison from an already encoded exact clip."""
import argparse,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
import build_inplace_keepalive as checks
from test_fap3_disk import DiskCPU
from row_dictionary_video import reference_tables
from lzsa2_row_player import Builder


class LzsaDiskCPU(DiskCPU):
    def instruction(self):
        if self.read8(self.pc)==0x37:
            self.pc=(self.pc+1)&65535;self.carry=True;return 4
        return super().instruction()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','metadata','options','zx0','lzsa','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    raw=a.raw.read_bytes();m=json.loads(a.metadata.read_text())
    with np.load(a.states,allow_pickle=False) as data:states=data['states']
    options=json.loads(a.options.read_text())['contract']['options'];options['startup_delta']=False
    with reference_tables(m['row_dictionary']):
        b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',row_dictionary=m['row_dictionary'],
            lzsa=a.lzsa.resolve(),series_fingerprint=b'AYH1R5L2'+bytes.fromhex(sha(raw))[:6],**options)
        b.ends=[len(states)];image,meta=b.volume(0,len(states),1)
        if image is None:raise ValueError('does not fit disk')
        (a.output/'candidate.trd').write_bytes(image)
        (a.output/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
        result=check_cold(image,meta,b.expected_banks)
        with patch.object(checks,'DiskCPU',LzsaDiskCPU):result.update(checks.prime(image,meta,states))
    report=dict(complete=True,release=False,scope=__doc__,trd_sha256=sha(image),raw_sha256=sha(raw),
        states_sha256=sha(states.tobytes()),checks=result,
        **{k:meta[k] for k in ('video_bytes','video_sectors','used_sectors','free_sectors','frames')})
    (a.output/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','scope')}))


if __name__=='__main__':main()
