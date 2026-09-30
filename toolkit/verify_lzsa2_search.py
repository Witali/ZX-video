"""Cross-check new standard LZSA2 streams on the unchanged full-flags Z80 core."""
import argparse,json,struct
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
from verify_lzsa2_dispatch import execute
import resumable_lzsa2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('stream','raw','cpu','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();stream=a.stream.read_bytes();raw=a.raw.read_bytes();reference=json.loads(a.cpu.read_bytes())
    assert reference['complete'] and reference['stream_sha256']==sha(stream) and reference['raw_sha256']==sha(raw)
    regions,labels,native=resumable_lzsa2.build()
    assert native==reference['native']
    at=out=0;rows=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        payload=stream[at:at+size];expected=raw[out:out+n];at+=size;out+=n
        row=execute(regions,labels,native,payload,expected,source=0x1000)
        assert row['slices']==reference['blocks'][len(rows)]['slice_tstates']
        irq=execute(regions,labels,native,payload,expected,source=0x1000,interrupts=True)
        rows.append(dict(index=len(rows),**row,interrupt_run=irq))
    assert at==len(stream) and out==len(raw)
    result=dict(complete=True,release=False,scope=__doc__,stream_sha256=sha(stream),raw_sha256=sha(raw),
        rows=rows,decoder_tstates=sum(r['tstates'] for r in rows),
        injected_interrupts=sum(r['interrupt_run']['injected_interrupts'] for r in rows),
        unavailable_interrupt_events=sum(r['interrupt_run']['unavailable_interrupt_events'] for r in rows))
    assert result['injected_interrupts']>0
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('complete','decoder_tstates','injected_interrupts','unavailable_interrupt_events')}))


if __name__=='__main__':main()
