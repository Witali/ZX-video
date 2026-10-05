"""Verify the next bit-identical PVQ optimization against archived round12 data."""
import gzip
import json
import struct
import wave
import numpy as np
from pvq_port import build,execute
from verify import ROOT,HERE,sha,image


def read_encoded(encoded):
    magic,version,dimensions,bits,reserved,rate,samples,size=struct.unpack('<4sBBBBIII',encoded[:20])
    assert (magic,version,bits,reserved,rate)==(b'PVQ8',1,10,0,8000)
    assert dimensions in (3,4)
    book=np.frombuffer(encoded[32:32+1024*dimensions],'i1').reshape(1024,dimensions)
    stream=encoded[32+1024*dimensions:];assert len(stream)==size
    assert size==((samples+dimensions*4-1)//(dimensions*4))*5
    expected=[];last=128
    for start in range(0,len(stream),5):
        header=stream[start]
        for i in range(4):
            if len(expected)>=samples:break
            index=stream[start+1+i]|(((header>>(i*2))&3)<<8)
            base=last//2+64
            values=[int(x)+base for x in book[index]]
            assert all(0<=x<=255 for x in values)
            expected.extend(values);last=values[-1]
    return book,stream,bytes(expected[:samples])


def check_variant(out,encoded,*,tight):
    book,stream,expected=read_encoded(encoded)
    group=book.shape[1]*4
    # Bounded first comparison exercises every slot, another group and a tail.
    n=group*2+1;probe=out/'probe';build(probe,n,book,True,tight=tight)
    execute(probe,stream[:((n+group-1)//group)*5],expected[:n],True,dimensions=book.shape[1])
    results={}
    for name,paced in [('unpaced',False),('paced',True)]:
        folder=out/name;build(folder,len(expected),book,paced,tight=tight)
        results[name]=execute(folder,stream,expected,paced,dimensions=book.shape[1])
    results['instruction_audit']=execute(out/'paced',stream,expected,True,audit_first=True,dimensions=book.shape[1])
    tails=[]
    for n in range(1,2*group+2):
        folder=out/f'tail-{n}';build(folder,n,book,True,tight=tight)
        r=execute(folder,stream[:((n+group-1)//group)*5],expected[:n],True,dimensions=book.shape[1])
        tails.append(dict(samples=n,exact=r['all_pcm8_exact_to_vq_reference'],paced=r['nominal_437_438_schedule_verified']))
    results['tails']=tails
    results.update(samples=len(expected),encoded_sha256=sha(encoded),pcm8_sha256=sha(expected),
                   total_stored_bytes=len(encoded),compression_vs_pcm8=len(expected)/len(encoded))
    (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
    with wave.open(str(out/'preview.wav'),'wb') as w:
        w.setparams((1,1,8000,0,'NONE','not compressed'));w.writeframes(expected)
    return results


def archive(out,round_id,encoded,report):
    target=HERE/'rounds'/round_id;target.mkdir(exist_ok=True)
    for name in ('decoder.s','player.ihx','player.map','out-times.u64.gz'):
        (target/name).write_bytes((out/'paced'/name).read_bytes())
    (target/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (target/'audio.pvq.gz').write_bytes(gzip.compress(encoded,mtime=0))


def main():
    old=HERE/'rounds/12';baseline=json.loads((old/'report.json').read_text())
    encoded=gzip.decompress((old/'audio.pvq.gz').read_bytes())
    assert sha(encoded)==baseline['encoded_sha256']
    out=ROOT/'build/speex-port/pvq-r13';out.mkdir(parents=True,exist_ok=True)
    report=check_variant(out,encoded,tight=True)
    assert report['pcm8_sha256']==baseline['pcm8_sha256']
    # The optional generator flag must not change the historical default image.
    book,_,expected=read_encoded(encoded);rebuild=out/'baseline-rebuild'
    build(rebuild,len(expected),book,True)
    mem=image(rebuild/'player.ihx')
    assert sha(bytes(mem[a] for a in sorted(mem)))==baseline['paced']['binary_sha256']
    total=report['unpaced']['total_cpu_tstates']
    report.update(baseline_round='12',baseline_rebuild_identical=True,
                  baseline_tstates=baseline['unpaced']['total_cpu_tstates'],
                  delta_tstates=total-baseline['unpaced']['total_cpu_tstates'],
                  mean_tstates_per_sample=total/report['samples'],
                  raw_source_snr_db=baseline['raw_source_snr_db'],
                  all_stored_bytes_and_decoded_pcm8_unchanged=True,
                  decision='Select: same format and sound, meets <=84-T/sample nominal CPU target.')
    assert report['mean_tstates_per_sample']<=84
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    archive(out,'13',encoded,report)
    print({k:v for k,v in report.items() if k not in ('paced','unpaced','tails','instruction_audit')},flush=True)


if __name__=='__main__':main()
