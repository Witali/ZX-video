"""Audit saved paired ZX0 measurements; --rebuild also regenerates both decoders.

The default uses only the standard library and does not re-execute Z80.
Native instruction timing checks occurred during the full benchmark.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).parent


def sha(blob):return hashlib.sha256(blob).hexdigest()


def audit(rebuild=False):
    path=ROOT/'faster_zx0_cpu.json';r=json.loads(path.read_bytes())
    if not r['complete'] or r['blocks']!=188 or r['compressed_stream_delta_bytes']:
        raise ValueError('incomplete or different-stream measurement')
    for name,digest in r['source_sha256_lf'].items():
        if sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))!=digest:raise ValueError(('source changed',name))
    for name,digest in r['references'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('reference changed',name))
    prior=json.loads((ROOT/'inplace_streaming_cpu.json').read_bytes())
    probe=json.loads((ROOT/'inplace_zx0_probe.json').read_bytes())
    counts={name:0 for name in r['totals']}
    for v in r['volumes']:
        part=v['part'];name=f'block15872-part{part:02}.stream.gz'
        packed=(ROOT/'inplace_zx0_evidence'/name).read_bytes()
        record=next(x for x in probe['archives'] if x['file']==name)
        if sha(packed)!=record['sha256']:raise ValueError('archive differs')
        stream=gzip.decompress(packed)
        if sha(stream)!=v['stream_sha256'] or len(stream)!=v['stream_bytes']:raise ValueError('stream differs')
        at=0;blocks=[]
        while at<len(stream):
            n,size=struct.unpack_from('<HH',stream,at);at+=4
            payload=stream[at:at+size];at+=size;blocks.append((n,payload))
        if at!=len(stream):raise ValueError('trailing stream')
        old=prior['volumes'][part-1]['baseline']
        for variant,x in v['variants'].items():
            summary=x['summary'];counts[variant]+=len(x['blocks'])
            if not summary['complete'] or not summary['decoder_instruction_table_checked']:
                raise ValueError('incomplete CPU check')
            for b,ref,(n,payload) in zip(x['blocks'],old,blocks,strict=True):
                if not b['exact'] or b['decoded_bytes']!=n or b['payload_sha256']!=sha(payload):
                    raise ValueError('block identity differs')
                for key in ('raw_sha256','producer_tstates','sectors','carry_copy_bytes'):
                    if b[key]!=ref[key]:raise ValueError(('producer/output differs',key))
                if (sum(b['slice_tstates'])!=b['decoder_tstates'] or
                    b['begin_tstates']+sum(b['step_tstates'])!=b['producer_tstates'] or
                    b['decoder_delta_tstates']!=b['decoder_tstates']-ref['decoder_tstates']):
                    raise ValueError('block arithmetic differs')
            for field in ('producer_tstates','decoder_tstates'):
                if sum(b[field] for b in x['blocks'])!=summary[field]:raise ValueError('volume sum differs')
            ticks=sum(i['tstates']*i['count'] for i in summary['decoder_instruction_histogram'])
            if ticks!=summary['decoder_tstates']:raise ValueError('instruction sum differs')
            if summary['decoder_bank5_tstates']+summary['decoder_bank2_tstates']!=ticks:
                raise ValueError('placement sum differs')
            if variant=='baseline':
                if ticks!=prior['volumes'][part-1]['baseline_summary']['decoder_tstates']:
                    raise ValueError('baseline decoder differs')
            else:
                layout=x['layout']
                for region in layout['regions']:
                    if sha(bytes.fromhex(region['code_hex']))!=region['sha256']:raise ValueError('code hash differs')
                if rebuild:
                    from faster_zx0 import build
                    if build(variant)[2]!=layout:raise ValueError('generated decoder differs')
        print(f'part {part}: {len(blocks)} unchanged blocks, three CPU variants verified',flush=True)
    if set(counts.values())!={188}:raise ValueError('missing blocks')
    summary=dict(complete=True,release=False,cpu_report_sha256=sha(path.read_bytes()),
        sources_verified=True,all_block_and_instruction_sums_match=True,
        unchanged_compressed_bytes=sum(v['stream_bytes'] for v in r['volumes']),
        variants={})
    for variant,t in r['totals'].items():
        for key in ('producer_tstates','decoder_tstates','total_tstates','sector_reads',
                    'carry_copy_bytes','decoder_bank5_tstates','decoder_bank2_tstates'):
            if t[key]!=sum(v['variants'][variant]['summary'][key] for v in r['volumes']):
                raise ValueError('total differs')
        if t['producer_tstates']+t['decoder_tstates']!=t['total_tstates']:raise ValueError('component sum differs')
        baseline=r['totals']['baseline'];delta=t['decoder_tstates']-baseline['decoder_tstates']
        rows=[b for v in r['volumes'] for b in v['variants'][variant]['blocks']]
        if sum(b['decoder_delta_tstates'] for b in rows)!=delta:raise ValueError('total delta differs')
        if variant!='baseline' and (t['faster_blocks']!=sum(b['decoder_delta_tstates']<0 for b in rows)
                or t['slower_blocks']!=sum(b['decoder_delta_tstates']>0 for b in rows)):
            raise ValueError('block regression count differs')
        slice_deltas=[];slice_values=[]
        for v in r['volumes']:
            for b,old in zip(v['variants'][variant]['blocks'],v['variants']['baseline']['blocks'],strict=True):
                for new_ticks,old_ticks in zip(b['slice_tstates'],old['slice_tstates'],strict=True):
                    slice_deltas.append(new_ticks-old_ticks);slice_values.append(new_ticks)
        summary['variants'][variant]=dict(**t,decoder_saving_percent=-100*delta/baseline['decoder_tstates'],
            producer_decoder_saving_percent=-100*delta/baseline['total_tstates'],
            decoder_calls=len(slice_deltas),slower_calls=sum(d>0 for d in slice_deltas),
            largest_call_regression_tstates=max(0,max(slice_deltas)),max_call_tstates=max(slice_values))
    path_report=ROOT/'faster_zx0_paths.json';paths=json.loads(path_report.read_bytes())
    if not paths['complete']:raise ValueError('incomplete path probe')
    for name,digest in paths['sources'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('path-probe source differs')
    summary['path_report_sha256']=sha(path_report.read_bytes())
    summary['audit_and_test_sources_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n'))
        for n in ('audit_faster_zx0.py','test_faster_zx0.py')}
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rebuild',action='store_true');p.add_argument('--write',action='store_true')
    a=p.parse_args();summary=audit(a.rebuild)
    if a.write:(ROOT/'faster_zx0_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    else:
        saved=json.loads((ROOT/'faster_zx0_summary.json').read_bytes())
        if summary!=saved:raise ValueError('saved summary differs')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
