"""Authenticate three installed S01 selections against frozen native proofs.

This runs source/wheel/API/export checks, never a decoder benchmark. Historical
private-source replays remain historical; exact regions/every label bind them
to the installed raw APIs. All prior71 selections/defaults stay available.
"""
import argparse
from datetime import date
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
for package in ('zx0','lzsa'):
    sys.path.insert(0,str(ROOT/'libraries'/package/'src'))

EXPECTED_PROOFS={
    'next_s01_zx0_full.json.gz':'2a202c04484bc67ce1d32e15e68d130b2a97bc17a21d32947561728ac6fc6223',
    'next_s01_lzsa_full.json.gz':'05cf06edbb09b2c1aea741f46aebabe13c6964370bd370875f994524b154f48f',
    'next_s01_prior_sources.json.gz':'176d974d6335a21ca73c1a80a36fb55f575ed63447bb3bddde7d1e4b98da7bdb'}


def sha(blob):return hashlib.sha256(blob).hexdigest()


def normalized(value):return json.loads(json.dumps(value))


def layout(profile):
    return dict(regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]],
        labels=profile[1],metadata=normalized(profile[2]))


def identity(current,saved):
    assert current['regions']==saved['regions']
    assert current['labels']==saved['labels']


def service(profile):
    meta=profile[2]
    return meta['service_memory_bytes']


def qualification(rows,key):
    for row in rows:
        assert row['model_exact'] and row['c_guarded']['exact']
        modes=row[key]
        assert len(modes)==6
        assert all(mode['exact'] for mode in modes.values())
        for name in ('plain','relocated','inplace_plain','inplace_relocated'):
            assert modes[name]['tstates']==row['c_guarded']['tstates']
        for name in ('inplace_plain','inplace_irq','inplace_relocated'):
            assert modes[name]['host_read_order_exact'] and modes[name]['code_protected'] and modes[name]['raw_abi_exact']
            assert modes[name]['host_minimum_input_start']==modes[name]['native_minimum_input_start']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zx0-wheel',type=Path,required=True)
    parser.add_argument('--lzsa-wheel',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    proofs={}
    def read(name):
        blob=(ROOT/'libraries/evidence'/name).read_bytes()
        proofs[name]=sha(blob)
        if name in EXPECTED_PROOFS:assert proofs[name]==EXPECTED_PROOFS[name],name
        return json.loads(gzip.decompress(blob) if name.endswith('.gz') else blob)
    native_zx=read('next_s01_zx0_full.json.gz')
    native_lz=read('next_s01_lzsa_full.json.gz')
    prior=read('next_s01_prior_sources.json.gz')
    assert native_zx['complete'] and native_zx['raw_qualification_complete'] and native_lz['complete']
    changed_sources=[]
    for native in (native_zx,native_lz):
        assert native['launch_source_sha256_lf']==native['final_source_sha256_lf']
        for relative,digest in native['final_source_sha256_lf'].items():
            current=sha((ROOT/relative).read_bytes().replace(b'\r\n',b'\n'))
            if current!=digest:
                assert relative=='libraries/lzsa/src/lzsa/compact.py',relative
                assert prior[relative]['sha256_lf']==digest==sha(prior[relative]['text'].encode())
                changed_sources.append(relative)
    finalized=native_lz['reporting_finalization']
    assert not finalized['guest_execution'] and finalized['measured_sources_unchanged']
    assert sha((ROOT/finalized['source_path']).read_bytes().replace(b'\r\n',b'\n'))==finalized['source_sha256_lf']
    reporting_archives=[]
    for attempt in native_lz['attempts']:
        if attempt.get('archive'):
            path=ROOT/attempt['archive']
            assert sha(path.read_bytes())==attempt['archive_sha256']
            reporting_archives.append(dict(path=attempt['archive'],sha256=attempt['archive_sha256'],
                native_matrix_complete=attempt.get('native_matrix_complete'),decoder_failure=attempt.get('decoder_failure')))
    old_table=json.loads(prior['libraries/evidence/decoder_variants_verification.json']['text'])
    assert old_table['complete'] and len(old_table['profiles'])==71
    probes=[]
    old_selections=[]
    for row in old_table['profiles']:
        module=row['builder'].removesuffix('.build')
        profile=importlib.import_module(module).build(**row['kwargs'])
        current=layout(profile)
        assert current['regions']==row['regions'],row['name']
        code=sum(len(blob) for _,blob in profile[0])
        assert code==row['code_state_table_padding_bytes']
        if 'service_memory_bytes' in profile[2]:assert service(profile)==row['service_bytes']
        else:assert code+(row['service_bytes']-row['code_state_table_padding_bytes'])==row['service_bytes']
        old_selections.append({field:row[field] for field in ('name','codec','kind','builder','kwargs','service_bytes','real_cpu_tstates','regions')})
        probes.append(dict(module=module,kwargs=row['kwargs'],codec=row['codec'],expected=current))

    # False opt-in must preserve the entire historical Small layout/metadata,
    # including its instruction listing, at every low-byte alignment.
    from lzsa import compact,block
    scope=dict(vars(compact))
    archived_compact=prior['libraries/lzsa/src/lzsa/compact.py']
    assert sha(archived_compact['text'].encode())==archived_compact['sha256_lf']
    exec(compile(archived_compact['text'],'<archived pre-S01 compact>','exec'),scope)
    for low in range(256):
        kwargs=dict(core=0x8000+low,core_limit=0x8400+low)
        old=layout(scope['build'](**kwargs))
        assert layout(compact.build(**kwargs))==layout(compact.build(compact_eof=False,**kwargs))==old
        assert layout(block.build('small',**kwargs))==layout(block.build('small',compact_eof=False,**kwargs))==old

    e01=read('next_e01_lzsa_full.json.gz')
    for name,row in e01['profiles'].items():
        builder=importlib.import_module(row['module']).build
        for origin,field in ((0x8000,'candidate'),(0x9103,'relocated')):
            current=layout(builder(**dict(row['kwargs'],cold_match_extension=True,core=origin)))
            assert current=={key:row[field][key] for key in current},(name,origin)
        current=layout(builder(**row['kwargs']))
        assert current=={key:row['baseline'][key] for key in current},name
    f00=read('next_f00_public_verification.json')
    f00_native=read('next_f00_full.json.gz')
    for row in f00['current_public_calls']:
        builder=importlib.import_module(row['module']).build
        current=layout(builder(**row['kwargs']))
        assert current=={key:row[key] for key in current}
        moved=layout(builder(**dict(row['kwargs'],core=0x9103)))
        identity(moved,f00_native['profiles'][row['native_profile']]['relocated'])

    from zx0.small import build as zx_build
    from zx0.block import build as zx_block
    both_current=zx_block('standard',fast_jumps=True,core=0x8000,core_limit=0x8400)
    assert layout(both_current)['regions']==native_zx['existing_both_jumps']['byte_regions']
    assert sum(len(blob) for _,blob in both_current[0])+6==native_zx['existing_both_jumps']['service_bytes']==76
    calls=[]
    historical=read('fast_jumps.json')['profiles']['zx0-standard']
    historical_rows={row['case']:row for row in historical['blocks']}
    for mode,setup in (('smc',43),('gamma-jp',34)):
        saved=native_zx['profiles'][mode]
        assert saved['C_complete'] and saved['native_complete'] and saved['qualification']['complete']
        assert len(saved['blocks'])==473 and len(saved['alignments'])==256
        qualification(saved['blocks'],'native')
        for origin,field in ((0x8000,None),(0x9103,'relocated'),(0x0800,'high_word'),(0x0703,'high_word_relocated')):
            current=layout(zx_build(mode,core=origin,core_limit=origin+0x400))
            identity(current,saved if field is None else saved[field])
            assert current['metadata']['service_memory_bytes']==saved['metadata']['service_memory_bytes']
            probes.append(dict(module='zx0.small',kwargs=dict(profile=mode,core=origin,core_limit=origin+0x400),
                codec='zx0',expected=current,new_profile=True))
        for row in saved['alignments']:
            p=zx_build(mode,core=0x8000+row['low_byte'])
            identity(layout(p),row)
            assert service(p)==row['metadata']['service_memory_bytes']
        profile=zx_build(mode)
        blob=profile[0][0][1]
        if mode=='smc':
            assert blob[:10]==bytes.fromhex('01ffffed43')+profile[1]['s01_offset'].to_bytes(2,'little')+bytes.fromhex('033e80')
        else:assert blob[:7]==bytes.fromhex('01ffffc5033e80')
        vs_standard=[];vs_both=[];all_comparisons=[]
        for row,base in zip(saved['blocks'],native_zx['baseline']['blocks']):
            assert row['case']==base['case'] and row['payload_sha256']==base['payload_sha256'] and row['raw_sha256']==base['raw_sha256']
            old=base['c_guarded']['tstates']
            both=old-2*(base['counts']['gamma_backtracks']+base['counts']['copy_back_jumps'])
            if row['case'] in historical_rows:assert historical_rows[row['case']]['candidate_tstates']==both
            actual=row['c_guarded']['tstates']
            comparison=dict(case=row['case'],real=row['real'],high_word=row['large_layout'],candidate_tstates=actual,
                standard_tstates=old,both_jumps_tstates=both,delta_vs_standard=actual-old,delta_vs_both_jumps=actual-both)
            all_comparisons.append(comparison)
            if actual>old:vs_standard.append(dict(comparison))
            if actual>both:vs_both.append(dict(comparison))
        assert sum(row['both_jumps_tstates'] for row in all_comparisons if row['real'])==native_zx['existing_both_jumps']['real_tstates']
        assert vs_standard==saved['summary']['slower_cases']==[]
        current=layout(profile)
        calls.append(dict(module='zx0.small',kwargs=dict(profile=mode),codec='zx0',native_profile=mode,
            native_proof='next_s01_zx0_full.json.gz',**current,service_bytes=service(profile),
            real_cpu_tstates=saved['summary']['real_tstates'],qualification=saved['qualification'],
            initialization=dict(per_block_setup_tstates_included=setup,external_target_initializer_tstates=0,caller_CALL_excluded_tstates=17),
            comparisons=dict(standard_real_tstates=sum(row['standard_tstates'] for row in all_comparisons if row['real']),
                both_jumps_real_tstates=native_zx['existing_both_jumps']['real_tstates'],
                slower_vs_standard=vs_standard,slower_vs_both_jumps=vs_both,all_cases=all_comparisons)))

    saved=native_lz['profiles']['eof_stack']
    assert saved['C_complete'] and saved['native_complete'] and saved['qualification']['complete']
    assert len(saved['blocks'])==675 and len(saved['supplemental'])==8 and len(saved['alignments'])==256
    qualification(saved['blocks']+saved['supplemental'],'protected')
    for origin,field in ((0x8000,None),(0x9103,'relocated')):
        p=compact.build(compact_eof=True,core=origin,core_limit=origin+0x400)
        identity(layout(p),saved if field is None else saved[field])
        alias=block.build('small',compact_eof=True,core=origin,core_limit=origin+0x400)
        assert layout(alias)==layout(p)
        for module,kwargs in (('lzsa.compact',dict(compact_eof=True)),('lzsa.block',dict(variant='small',compact_eof=True))):
            probes.append(dict(module=module,kwargs=dict(kwargs,core=origin,core_limit=origin+0x400),
                codec='lzsa2',expected=layout(p),new_profile=True))
    for row in saved['alignments']:
        p=compact.build(compact_eof=True,core=0x8000+row['low_byte'])
        identity(layout(p),row)
        assert service(p)==row['metadata']['service_memory_bytes']
    p=compact.build(compact_eof=True)
    assert p[0][0][1][:4]==bytes.fromhex('af470818')
    slower=[dict(row) for row in saved['summary']['slower_cases']]
    assert len(slower)==643 and not any(row['real'] for row in slower)
    supplemental_slower=[dict(case=row['case'],delta_tstates=row['delta_tstates']) for row in saved['supplemental'] if row['delta_tstates']>0]
    calls.append(dict(module='lzsa.compact',kwargs=dict(compact_eof=True),codec='lzsa2',native_profile='eof_stack',
        native_proof='next_s01_lzsa_full.json.gz',**layout(p),service_bytes=service(p),
        real_cpu_tstates=saved['summary']['real_tstates'],qualification=saved['qualification'],
        aliases=[dict(module='lzsa.block',kwargs=dict(variant='small',compact_eof=True))],
        initialization=dict(per_block_setup_tstates_included=24,external_target_initializer_tstates=0,caller_CALL_excluded_tstates=17),
        timing_components=saved['timing_components'],slower_frozen_cases=slower,slower_supplemental_cases=supplemental_slower))
    assert len(calls)==3 and len(probes)==83

    # Do not archive a partial/failed suite or accept a smaller test selection.
    logs={};archive=ROOT/'libraries/evidence/next_s01_public';archive.mkdir(exist_ok=True)
    for name,minimum in (('next-s01-library-tests.log',100),('next-s01-toolkit-tests.log',24),('next-s01-wheel.log',None)):
        blob=(ROOT/'.tmp'/name).read_bytes();text=blob.decode('utf-8')
        if minimum is None:assert 'Successfully built' in text;count=None
        else:
            assert '\nOK' in text and not re.search(r'\n(?:FAILED|ERROR)',text)
            count=int(re.search(r'Ran (\d+) tests',text)[1]);assert count>=minimum,(name,count,minimum)
        compressed=gzip.compress(blob,mtime=0);(archive/(name+'.gz')).write_bytes(compressed)
        logs[name]=dict(tests=count,sha256=sha(compressed),decoded_sha256=sha(blob))
    resources=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=resources['original_resources']+resources['added_pinned_resources']
    assert len(resources)==6
    for row in resources:
        assert sha((ROOT/'libraries'/row['package']/'src'/row['package']/'asm'/row['file']).read_bytes())==row['sha256']
    wheel_checks={}
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='next-s01-wheel-') as temporary:
        folder=Path(temporary);installed=folder/'installed';installed.mkdir()
        for path,package in ((args.zx0_wheel,'zx0'),(args.lzsa_wheel,'lzsa')):
            with zipfile.ZipFile(path) as wheel:
                assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in wheel.namelist())
                wheel.extractall(installed);checked=[]
                for source in (ROOT/'libraries'/package/'src'/package).rglob('*'):
                    if source.is_file() and (source.suffix in ('.py','.asm') or source.name=='LICENSE'):
                        relative=source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                        assert wheel.read(relative)==source.read_bytes(),relative
                        checked.append(relative)
                wheel_checks[path.name]=checked
        inputs=folder/'probes.json';inputs.write_text(json.dumps(probes),encoding='utf-8')
        child="""import hashlib,importlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);probes=json.loads(Path(sys.argv[2]).read_text());destination=Path(sys.argv[3])
def restored(path):
    rows=[]
    for line in path.read_text().splitlines():
        if line.startswith('org '):rows.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rows[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
    return [(at,bytes(blob)) for at,blob in rows]
for index,row in enumerate(probes):
    p=importlib.import_module(row['module']).build(**row['kwargs'])
    current=dict(regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in p[0]],labels=p[1],metadata=p[2])
    assert json.loads(json.dumps(current))==row['expected']
    package='zx0' if row['codec']=='zx0' else 'lzsa'
    output=destination/str(index);importlib.import_module(package+'.export').export(output,*p)
    assert restored(output/'decoder.asm')==p[0]
    if row.get('new_profile'):assert 'initializ' in (output/'decoder.asm').read_text().lower()
cli=[('zx0','small-smc',dict(profile='smc')),('zx0','small-gamma-jp',dict(profile='gamma-jp')),('lzsa','small-block',dict(compact_eof=True))]
for package,selector,kwargs in cli:
    output=destination/('cli-'+selector)
    sys.argv=[package,'build','--variant' if package=='zx0' else '--profile',selector,'--core','0x8000','--core-limit','0x8400','--output',str(output)]
    if package=='lzsa':sys.argv.append('--compact-eof')
    importlib.import_module(package+'.__main__').main()
    p=importlib.import_module('zx0.small' if package=='zx0' else 'lzsa.compact').build(**kwargs,core=0x8000,core_limit=0x8400)
    assert restored(output/'decoder.asm')==p[0]
    metadata=json.loads((output/'metadata.json').read_text())
    assert all(metadata[key]==value for key,value in json.loads(json.dumps(p[2])).items())
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
assert all('/installed/' in str(Path(sys.modules[name].__file__)).replace('\\\\','/') for name in ('zx0','lzsa'))
print(json.dumps(dict(exports=len(probes),cli_profiles=3)))
"""
        result=subprocess.run([sys.executable,'-I','-c',child,str(installed),str(inputs),str(folder/'exports')],
            capture_output=True,text=True,check=True)
        smoke=json.loads(result.stdout.splitlines()[-1]);assert smoke==dict(exports=83,cli_profiles=3)
    from test_libraries import profiles
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    sources=[Path(__file__)]
    for package in ('zx0','lzsa'):sources.extend((ROOT/'libraries'/package/'src'/package).glob('*.py'))
    report=dict(date=date.today().isoformat(),complete=True,release=False,resident_only=True,current_public_calls=calls,
        proof_sha256=proofs,source_changes_since_native_matrix=sorted(set(changed_sources)),
        source_authentication='Current public package source is authenticated here; prior compact source is archived and remains the native execution provenance.',
        reporting_finalization=finalized,reporting_archives=reporting_archives,
        preceding_table_calls_exact=71,preceding_e01_LZSA_calls_metadata_exact=12,preceding_F00_calls_exact=3,
        preceding_selection_sha256=sha(json.dumps(old_selections,sort_keys=True,separators=(',',':')).encode()),
        default_profiles_exact=31,upstream_resources_exact=6,archived_logs=logs,
        isolated_wheel_exports=83,isolated_cli_profiles=3,wheels={path.name:sha(path.read_bytes()) for path in (args.zx0_wheel,args.lzsa_wheel)},
        wheel_source_and_resources_exact=wheel_checks,legacy_small_false_all256_metadata_exact=True,
        native_cases_reexecuted=0,native_evidence_reused_by_exact_bytes_and_all_labels=True,
        source_sha256_lf={path.relative_to(ROOT).as_posix():sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in sources},
        benchmark_scope='All entry setup/EOF/RET included. No required external target initializer; caller CALL17 and API argument publication remain outside the documented entry boundary.',
        exclusions=['Coroutine/guarded qualification','ULA/WAIT','Physical disk/ROM','Movie/application cold-boot timing'],
        frontier_scope='Finite measured size/speed choices; no global optimum claim',default_instruction_delta_tstates=0,payload_delta_bytes=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,public_calls=3,preceding_calls=71,**smoke)))


if __name__=='__main__':main()
