"""Bounded LZSA2 compression-search experiment; standard wire format unchanged.

Alter a copy of pinned upstream source, never the original checkout. Increase
host-only match/arrival tables, build with the existing MSVC toolchain, and
compare against archived payloads on identical independently reset raw blocks.
This does not modify player code, dictionaries, block size or video quality.
"""
import argparse,json,shutil,struct,subprocess,time
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
from inplace_zx0 import layout
import lzsa2_stream

REVISION='15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5'
ROOT=Path(__file__).resolve().parent
CHANGES={
    'NARRIVALS_PER_POSITION_V2_BIG':(32,128),
    'NARRIVALS_PER_POSITION_V2_MAX':(64,256),
    'ARRIVALS_PER_POSITION_SHIFT_V2':(6,8),
    'NMATCHES_PER_INDEX_V2':(64,128),
    'MATCHES_PER_INDEX_SHIFT_V2':(6,7),
}


def run(args,**kwargs):
    result=subprocess.run([str(x) for x in args],capture_output=True,**kwargs)
    if result.returncode:
        raise RuntimeError((result.returncode,result.stdout.decode(errors='replace'),result.stderr.decode(errors='replace')))
    return result


def prepare(source,output,vs,*,deep=False):
    revision=run(['git','-C',source,'rev-parse','HEAD']).stdout.decode().strip()
    if revision!=REVISION:raise ValueError(('unexpected upstream revision',revision))
    if run(['git','-C',source,'status','--porcelain','--untracked-files=no']).stdout:
        raise ValueError('upstream tracked sources must be unmodified')
    target=output/'source';header=Path('src/shrink_context.h');changed={}
    text=(source/header).read_text();original=sha(text.encode())
    for key,(before,after) in CHANGES.items():
        old=f'#define {key} {before}\n';new=f'#define {key} {after}\n'
        if text.count(old)!=1:raise ValueError(('unexpected macro',key))
        text=text.replace(old,new)
    text='/* Altered ZX-video experiment: wider host-only LZSA2 search tables. */\n'+text
    changed[header]=text
    if deep:
        file=Path('src/shrink_block_v2.c');body=(source/file).read_text()
        replacements=[('m < 15','m < 63',2),('m < 46','m < 95',2),
            ('m < 63','m < 127',2),('nInserted >= 12','nInserted >= 48',2),
            ('((nPosition + 16) < nEndOffset) ? 16 :','((nPosition + 64) < nEndOffset) ? 64 :',3)]
        # Simultaneous replacements: 15->63 must not subsequently become 127.
        import re
        mapping={before:after for before,after,_ in replacements}
        for before,_,count in replacements:
            if body.count(before)!=count:raise ValueError(('unexpected supplement source',before))
        body=re.sub('|'.join(re.escape(x) for x in mapping),lambda m:mapping[m[0]],body)
        changed[file]='/* Altered ZX-video experiment: wider supplemental match search. */\n'+body
    if target.exists():
        for src in (source/'src').rglob('*'):
            if src.is_file():
                relative=src.relative_to(source)
                actual=(target/relative).read_text() if relative in changed else (target/relative).read_bytes()
                expected=changed[relative] if relative in changed else src.read_bytes()
                if actual!=expected:
                    raise ValueError(('unexpected candidate edit',str(src)))
    else:
        shutil.copytree(source/'src',target/'src')
        for name in ('LICENSE','LICENSE.zlib.md','LICENSE.cc0.md','BlockFormat_LZSA2.md'):
            shutil.copy2(source/name,target/name)
        for file,content in changed.items():(target/file).write_text(content,encoding='utf-8',newline='\n')
    build=output/'build';build.mkdir(exist_ok=True)
    result=run(['cmd.exe','/d','/c',ROOT/'build_lzsa_windows.cmd',vs,target,build])
    (output/'build.log').write_bytes(result.stdout+result.stderr)
    manifest=dict(upstream_revision=revision,changed_macros=CHANGES,deep_supplements=deep,
        original_header_sha256_lf=original,candidate_header_sha256_lf=sha(text.encode()),
        source_sha256_lf={str(x.relative_to(target)).replace('\\','/'):sha(x.read_bytes().replace(b'\r\n',b'\n'))
            for x in sorted((target/'src').rglob('*')) if x.is_file()},
        candidate_exe_sha256=sha((build/'lzsa.exe').read_bytes()),
        note='Standard format and unchanged writer/decoder. The optional deep variant widens specified supplement limits; both variants still use bounded heuristic search.')
    save(output/'build.json',manifest)
    return build/'lzsa.exe',manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--deep',action='store_true',help='Also widen supplemental candidate count and length limits')
    for n in ('source','baseline-exe','vs','output','raw','stream'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    candidate,build=prepare(a.source.resolve(),a.output,a.vs.resolve(),deep=a.deep)
    raw=a.raw.read_bytes();stream=a.stream.read_bytes();at=out=0;rows=[];streams={'baseline':bytearray(),'wide':bytearray()}
    report=dict(complete=False,release=False,scope=__doc__,raw_sha256=sha(raw),baseline_stream_sha256=sha(stream),
        build=build,baseline_exe_sha256=sha(a.baseline_exe.read_bytes()),flags=['-r','-f','2','--prefer-ratio'],
        rows=rows,pc_timing_scope='One sequential run including process/file overhead; not a rigorous PC benchmark.')
    for index in range(1000):
        if at==len(stream):break
        n,size=struct.unpack_from('<HH',stream,at);at+=4;old=stream[at:at+size];at+=size
        data=raw[out:out+n];out+=n
        if not 1<=n<=15872:raise ValueError('wrong native block size')
        src=a.output/'input.raw';src.write_bytes(data)
        row=dict(index=index,raw_sha256=sha(data),decoded_bytes=n)
        for name,exe in (('baseline',a.baseline_exe.resolve()),('wide',candidate)):
            packed=a.output/f'{name}-{index:03}.lzsa2';restored=a.output/'restored.raw'
            start=time.perf_counter()
            run([exe,'-r','-f','2','--prefer-ratio',src,packed])
            seconds=time.perf_counter()-start;payload=packed.read_bytes()
            if name=='baseline' and payload!=old:raise AssertionError(('baseline does not reproduce archive',index))
            run([a.baseline_exe.resolve(),'-d','-r','-f','2',packed,restored])
            if restored.read_bytes()!=data:raise AssertionError(('author round trip',name,index))
            decoded,proof=lzsa2_stream.trace(payload,limit=n)
            if decoded!=data:raise AssertionError(('host round trip',name,index))
            space=layout(len(payload),n,proof['minimum_input_start'],len(streams[name]))
            if not space['sector_aligned_fits']:raise AssertionError(('in-place layout',name,index,space))
            lzsa2_stream.trace(payload,limit=n,input_start=space['input_start'])
            streams[name]+=struct.pack('<HH',n,len(payload))+payload
            row[name]=dict(payload_bytes=len(payload),payload_sha256=sha(payload),seconds=seconds,
                layout=space,proof=proof)
        row['wide_minus_baseline_bytes']=row['wide']['payload_bytes']-row['baseline']['payload_bytes'];rows.append(row)
        save(a.output/'probe.json',report)
        print(index,row['wide_minus_baseline_bytes'],'bytes;',round(row['wide']['seconds'],3),'s',flush=True)
    if at!=len(stream) or out!=len(raw):raise AssertionError('fixture extent differs')
    for name,data in streams.items():(a.output/(name+'.stream')).write_bytes(data)
    report.update(complete=True,blocks=len(rows),decoded_bytes=out,
        stream_bytes={name:len(data) for name,data in streams.items()},
        stream_sha256={name:sha(data) for name,data in streams.items()},
        sectors={name:(len(data)+255)//256 for name,data in streams.items()},
        pc_seconds={name:sum(r[name]['seconds'] for r in rows) for name in streams},
        improved_blocks=sum(r['wide_minus_baseline_bytes']<0 for r in rows),
        regressed_blocks=sum(r['wide_minus_baseline_bytes']>0 for r in rows),
        native_cpu_measured=False,player_source_changed=False,format_changed=False)
    save(a.output/'probe.json',report)
    print(json.dumps({k:report[k] for k in ('complete','blocks','stream_bytes','sectors','pc_seconds','improved_blocks','regressed_blocks')}),flush=True)


if __name__=='__main__':main()
