"""Independently authenticate completed DHA evidence without encoding or fitting.

The audit reads existing files, checks archived producers and container CRCs,
and decodes with the pinned DLL. It does not rerun a listening filter, native
player, compiler, encoder, or external tester producer. Failures are retained.
"""
import argparse
import ctypes as ct
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import traceback
import wave
import zlib

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EVIDENCE = HERE/'evidence'
NAMES = ('sea_foam','silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')
DEFAULT_MODEL = '70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f'
ANS = 'af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8'
COMMON_MODEL = '199a17a9967bfbb941099039f32a47192af8933faf37cf015047abb51bfb9a7b'
SETTINGS = dict(frame_samples=4096,beam_width=64,gain_candidates=8,lookahead=2,rate_penalty=82,allow_pcm_fallback=True)


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(Path(path).read_bytes())
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def wav(path,width,rate):
    with wave.open(str(path),'rb') as stream:
        assert (stream.getnchannels(),stream.getsampwidth(),stream.getframerate())==(1,width,rate)
        raw=stream.readframes(stream.getnframes())
    return np.frombuffer(raw,'u1' if width==1 else '<i2').copy()


class Stream(ct.Structure):
    _fields_=[('rate',ct.c_uint32),('channels',ct.c_uint16),('frame_samples',ct.c_uint16),
              ('total_samples',ct.c_uint64),('model',ct.c_int8*1024),('ans',ct.c_uint8*512)]


class Audit:
    def __init__(self,out):
        self.out=out; self.checks=[]; self.failures=[]; self.information=[]
        self.manifests=[]; self.containers=[]; self.qualities=[]; self.producers=[]
        self.original_code=[]; self.snapshots=[]; self.bridge=[]

    def section(self,name,fn):
        try:
            value=fn(); self.checks.append(dict(check=name,passed=True)); return value
        except Exception as error:
            item=dict(check=name,error=repr(error),traceback=traceback.format_exc())
            self.failures.append(item); self.checks.append(dict(check=name,passed=False))
            save(self.out/'failures.json',self.failures)
            return None

    def manifest(self,folder):
        folder=EVIDENCE/folder; path=folder/'manifest.json'; meta=load(path)
        records=meta.get('artifact_files',meta.get('artifacts'))
        if isinstance(records,dict): records=[dict(path=k,**v) for k,v in records.items()]
        assert isinstance(records,list) and len(records)>0
        seen=set(); total=0
        for item in records:
            name=item['path']; assert name not in seen; seen.add(name)
            target=(folder/name).resolve(); assert target.is_relative_to(folder.resolve())
            raw=target.read_bytes(); assert len(raw)==item['bytes'],name
            assert sha(raw)==item['sha256'],name; total+=len(raw)
        if 'files' in meta: assert meta['files']==len(records)
        actual={p.relative_to(folder).as_posix() for p in folder.rglob('*')
                if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
        assert actual==seen,dict(unlisted=sorted(actual-seen),missing=sorted(seen-actual))
        self.manifests.append(dict(folder=str(folder.relative_to(EVIDENCE)),files=len(records),bytes=total,
                                   manifest_sha256=sha(path.read_bytes())))

    def producer(self,archive,current,declared=None,historical=False):
        archived=gzip.decompress(archive.read_bytes()) if archive.suffix=='.gz' else archive.read_bytes()
        raw=current.read_bytes(); same=archived==raw
        if declared is not None: assert sha(archived)==declared
        if not historical: assert same,(str(archive),str(current))
        self.producers.append(dict(archive=str(archive.relative_to(EVIDENCE)),current=str(current.relative_to(ROOT)),
            archived_sha256=sha(archived),current_sha256=sha(raw),byte_equal=same,historical_control=historical))

    def pinned_sources(self):
        host=EVIDENCE/'dha-host'; snapshot=load(host/'source-snapshot.json')
        for name,item in snapshot['snapshot_files'].items():
            raw=(host/'producer-source'/name).read_bytes()
            assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],name
            live=Path(snapshot['external_library_read_only'])/name
            same=live.exists() and live.read_bytes()==raw
            self.snapshots.append(dict(path=name,sha256=sha(raw),live_tester_equal=same))
            assert same,('live_tester_source_changed',str(live))
        table=(host/'producer-source/src/dha_tables.inc.h').read_text()
        for name,length,wanted in [('model',1024,DEFAULT_MODEL),('ans',512,ANS)]:
            text=re.search(r'dha_default_'+name+r'\['+str(length)+r'\]\s*=\s*\{(.*?)\}',table,re.S).group(1)
            values=[int(x) for x in re.findall(r'-?\d+',text)]
            assert len(values)==length
            raw=bytes(value&255 for value in values); assert sha(raw)==wanted
        build=load(host/'build.json')
        assert build['complete'] and all(x['passed'] for x in build['tests'])
        for name in ('dha.exe','dha_codec.dll'):
            binary=ROOT/'.tmp/dha-host-scratch/build'/name
            assert sha(binary.read_bytes())==build['builds'][name]['sha256']
        lib=ct.CDLL(str(ROOT/'.tmp/dha-host-scratch/build/dha_codec.dll'))
        lib.dha_header_read.argtypes=[ct.POINTER(Stream),ct.c_void_p,ct.c_size_t];lib.dha_header_read.restype=ct.c_int
        lib.dha_decode_frame.argtypes=[ct.POINTER(Stream),ct.c_void_p,ct.c_size_t,ct.POINTER(ct.c_int16),ct.c_size_t,ct.POINTER(ct.c_size_t),ct.c_void_p]
        lib.dha_decode_frame.restype=ct.c_int;self.dll=lib

    def container(self,path,source,decoded,rate,model):
        data=path.read_bytes(); assert data[:4]==b'DHAF'
        assert struct.unpack_from('<HH',data,4)==(1,1572)
        assert zlib.crc32(data[:1568])==struct.unpack_from('<I',data,1568)[0]
        assert struct.unpack_from('<IHHQ',data,8)==(rate,1,4096,len(source))
        assert sha(data[32:1056])==model and sha(data[1056:1568])==ANS
        info=Stream(); header=ct.create_string_buffer(data[:1572])
        assert self.dll.dha_header_read(ct.byref(info),header,1572)==0
        at=1572; index=0; rows=[]; native=[]
        while at<len(data):
            assert data[at:at+4]==b'DHF1'
            size,seq,count,channel,kind=struct.unpack_from('<IIHBB',data,at+4)
            bits=struct.unpack_from('<I',data,at+24)[0]
            assert seq==len(rows) and channel==0 and kind in (0,1) and 0<count<=4096
            assert at+size<=len(data) and size>=32
            payload=data[at+32:at+size]
            assert zlib.crc32(data[at:at+28]+payload)==struct.unpack_from('<I',data,at+28)[0]
            assert len(payload)==(bits+7)//8
            if kind==0:
                assert bits==16*count and payload==source[index:index+count].astype('<i2').tobytes()
                np.testing.assert_array_equal(decoded[index:index+count],source[index:index+count])
            packet=ct.create_string_buffer(data[at:at+size]);pcm=(ct.c_int16*4096)();written=ct.c_size_t()
            assert self.dll.dha_decode_frame(ct.byref(info),packet,size,pcm,4096,ct.byref(written),None)==0
            assert written.value==count
            native.append(np.ctypeslib.as_array(pcm)[:count].copy())
            rows.append(dict(sequence=seq,file_offset=at,packet_bytes=size,samples=count,
                kind='DHA' if kind else 'PCM16',payload_bits=bits,payload_bytes=len(payload)))
            index+=count;at+=size
        assert at==len(data) and index==len(source)==len(decoded)==info.total_samples
        np.testing.assert_array_equal(np.concatenate(native),decoded)
        return dict(file_bytes=len(data),file_sha256=sha(data),frames=rows,
                    dha_frames=sum(x['kind']=='DHA' for x in rows),pcm16_fallback_frames=sum(x['kind']=='PCM16' for x in rows),
                    source_samples=len(source),all_CRC_counts_fallback_samples_and_DLL_decode_exact=True)

    def corpus(self,common):
        root=EVIDENCE/('dha-common-host' if common else 'dha-host-corpus')
        aggregate=load(root/'report.json');assert aggregate['complete'] and len(aggregate['rows'])==9
        rows=aggregate['rows'] if common else [x['report'] for x in aggregate['rows']]
        assert {x['source'] for x in rows}==set(NAMES)
        for report in rows:
            name=report['source']; folder=root/name
            if not common and name=='sea_foam':folder=EVIDENCE/'dha-host/sea_foam'
            source=wav(EVIDENCE/'general/inputs'/(name+'.wav'),1,8000)
            pcm=((source.astype('i4')-128)*256).astype('<i2')
            assert (folder/'source-pcm16.bin').read_bytes()==pcm.tobytes()
            decoded=wav(folder/'decoded.wav',2,8000)
            assert (folder/'decoded-pcm16.bin').read_bytes()==decoded.tobytes()
            assert report['input_samples']==report['decoded_samples']==len(source)
            assert report['source_u8_sha256']==sha(source.tobytes())
            assert report['source_pcm16_sha256']==sha(pcm.tobytes())
            assert report['decoded_pcm16_sha256']==sha(decoded.tobytes())
            assert report['settings']==SETTINGS
            item=self.container(folder/'audio.dhaf',pcm,decoded,8000,COMMON_MODEL if common else DEFAULT_MODEL)
            for key in ('file_bytes','file_sha256','frames','dha_frames','pcm16_fallback_frames'):
                assert item[key]==report[key],(name,key)
            parity='DLL_decode_matches_every_C_adapter_sample' if common else 'DLL_decode_matches_every_CLI_sample'
            assert report[parity]
            if common:
                assert report['all_PCM16_fallback_samples_exact'] and report['all_C_progress_rows_match_serialized_frames']
                assert report['source_is_training_member']==(name in ('speech','entertainer'))
            else: assert report['CLI_info_fully_validated']
            item.update(model='common' if common else 'default',source=name)
            item['encode_seconds']=report['encode_and_C_decode' if common else 'encode']['elapsed_seconds']
            item['frame_count']=len(item.pop('frames'));self.containers.append(item)

    def common_model(self):
        folder=EVIDENCE/'dha-common-model'; report=load(folder/'report.json')
        assert report['complete'] and report['training_names']==['speech','entertainer']
        assert set(report['holdout_names'])==set(NAMES)-{'speech','entertainer'}
        assert not report['heldout_song_used_for_fit'] and not report['evaluation_fit']
        assert sum(x['training_rows'] for x in report['inputs'])==report['training_rows']==373752
        for row in report['inputs']:
            path=EVIDENCE/'general/inputs'/(row['name']+'.wav');source=wav(path,1,8000)
            assert row['wav_sha256']==sha(path.read_bytes()) and row['pcm8_sha256']==sha(source.tobytes())
            assert row['samples']==len(source) and row['training_rows']==len(source)-4
        domains=[np.r_[256,np.arange(1,256)],*[np.arange(-128,128)]*3]
        model=np.concatenate([np.clip(np.rint(c*d),-127 if i==0 else -128,127).astype('i1')
                for i,(c,d) in enumerate(zip(report['coefficients'],domains))]).tobytes()
        assert model==(folder/'model.bin').read_bytes()==(EVIDENCE/'dha-common-host/model.bin').read_bytes()
        assert sha(model)==report['model_sha256']==COMMON_MODEL
        control=EVIDENCE/'dha-common-host/adapter-control'
        assert (control/'native/audio.dhaf').read_bytes()==(EVIDENCE/'dha-host/sea_foam/pilot-first-frame/audio.dhaf').read_bytes()
        assert load(control/'report.json')['original_CLI_container_byte_identical']

    def quality(self,common,name):
        path=EVIDENCE/('dha-quality-common' if common else 'dha-quality-default')/name
        report=load(path/'report.json');assert report['complete'] and report['source']==name
        folder=EVIDENCE/('dha-common-host' if common else 'dha-host-corpus')/name
        if not common and name=='sea_foam':folder=EVIDENCE/'dha-host/sea_foam'
        source_path=EVIDENCE/'general/inputs'/(name+'.wav');source=wav(source_path,1,8000)
        actual=wav(folder/'decoded.wav',2,8000)
        packed=gzip.decompress((source_path.with_suffix('.ima.gz')).read_bytes())
        from ima_codec import decode
        ima,_=decode(packed)
        assert len(source)==len(actual)==len(ima)==report['source_samples']
        assert report['source_PCM8_sha256']==sha(source.tobytes())
        assert report['source_WAV_sha256']==sha(source_path.read_bytes())
        assert report['DHA_file_sha256']==sha((folder/'audio.dhaf').read_bytes())
        assert report['DHA_WAV_sha256']==sha((folder/'decoded.wav').read_bytes())
        assert report['frozen_IMA4_sha256']==sha(packed) and report['frozen_IMA4_bytes']==len(packed)
        assert report['filter_intermediate_hz']==768000 and report['filter_output_hz']==44100
        assert not report['score_source_clock_fitted'] and not report['gain_delay_or_bandwidth_fitted']
        summary={x['codec']:x for x in report['rows']};assert set(summary)=={'IMA4','DHA'}
        for codec,pcm in [('IMA4',ima),('DHA',actual)]:
            row=summary[codec];assert row['PCM16_sha256']==sha(pcm.astype('<i2').tobytes())
            wanted=source[800:-800].astype('f8')-128;error=pcm[800:-800].astype('f8')/256-wanted
            signal=float(np.mean(wanted*wanted));noise=float(np.mean(error*error))
            snr=None if signal<1e-24 or noise==0 else 10*math.log10(signal/noise)
            assert row['unfiltered']['snr_db']==snr
            assert row['unfiltered']['error_rms_PCM8_units']==math.sqrt(noise)
        host=load(folder/'report.json');container=report['container']
        assert container['file_bytes']==host['file_bytes'] and container['predictive_frames']==host['dha_frames']
        assert container['PCM16_fallback_frames']==host['pcm16_fallback_frames']
        self.qualities.append(dict(model='common' if common else 'default',source=name,samples=len(source),
            IMA_filtered_snr=summary['IMA4']['filtered']['snr_db'],DHA_filtered_snr=summary['DHA']['filtered']['snr_db'],
            unfiltered_metrics_recomputed=True,filtered_report_authenticated_not_rerendered=True))

    def retained_sources(self):
        architecture=EVIDENCE/'dha-architecture'
        for path,item in load(architecture/'inputs.json').items():
            raw=Path(path).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],path
        for item in load(EVIDENCE/'dha-precision/report.json')['sources']:
            path=Path('C:/Work/z80-tester')/item['path'];raw=path.read_bytes()
            assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],str(path)
        meta=load(architecture/'manifest.json')
        assert sha((HERE/'dha_architecture.py').read_bytes())==meta['producer_sha256']
        report=load(architecture/'report.json')
        assert report['samples']==375000 and not report['native_execution_rerun']
        assert all(report['independent_whole_wire'][key] for key in ('exact_q','exact_symbols','exact_gains','exact_DAC','ROM_tables_exact'))
        assert report['identities']['model_sha256']==DEFAULT_MODEL
        failed=EVIDENCE/'dha-architecture-attempt-1'
        self.information.append(dict(preserved_failed_attempt=str(failed.relative_to(EVIDENCE)),
            has_manifest=(failed/'manifest.json').exists(),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in failed.iterdir() if p.is_file()]))

    def pcm8(self):
        folder=EVIDENCE/'dha-pcm8';report=load(folder/'report.json')
        assert report['code_sha256']==sha((folder/'kernel.bin').read_bytes())
        bits=gzip.decompress((folder/'trajectory-bits.u8.gz').read_bytes())
        times=gzip.decompress((folder/'trajectory-times.u32.gz').read_bytes())
        assert sha(bits)==report['artifacts']['trajectory_bits_sha256']
        assert sha(times)==report['artifacts']['trajectory_times_sha256']
        source=(folder/'trajectory.pcm8').read_bytes();assert sha(source)==report['artifacts']['pcm8_sha256']
        samples=report['native']['trajectory']['samples'];acc=0;expected=bytearray()
        for sample in source[:samples]:
            for _ in range(8):
                total=acc+(sample<<8);expected.append(total>>16);acc=total&65535
        assert bits==bytes(expected) and acc==report['native']['trajectory']['final_accumulator']
        ticks=np.frombuffer(times,'<u4')
        np.testing.assert_array_equal(ticks,29+56*np.arange(len(bits),dtype='u4'))
        assert report['native']['all_input_phase_pairs']==65536 and report['native']['total_outputs']==655368

    def bridge2(self,zero):
        name='dha-bridge2-quality0-pilot' if zero else 'dha-bridge2-pilot';folder=EVIDENCE/name
        report=load(folder/'report.json');assert report['complete']
        source=np.frombuffer((EVIDENCE/'dha-host/sea_foam/source-pcm16.bin').read_bytes(),'<i2')
        physical=np.frombuffer((folder/'source-physical-pcm16.bin').read_bytes(),'<i2')
        coded=np.frombuffer((folder/'coded-targets-pcm16.bin').read_bytes(),'<i2')
        count=len(physical);assert count==16384 and len(coded)==2*count
        np.testing.assert_array_equal(physical,source[:count]);np.testing.assert_array_equal(coded[::2],physical)
        midpoint=(source[:count].astype('i4')+source[1:count+1].astype('i4'))//2
        np.testing.assert_array_equal(coded[1::2],midpoint)
        actual=np.frombuffer((folder/'decoded-coded-pcm16.bin').read_bytes(),'<i2')
        actual_physical=np.frombuffer((folder/'decoded-physical-pcm16.bin').read_bytes(),'<i2')
        np.testing.assert_array_equal(actual_physical,actual[::2]);assert len(actual_physical)==count
        item=self.container(folder/'audio.dhaf',coded,actual,16000,DEFAULT_MODEL)
        for key in ('file_bytes','file_sha256','dha_frames','pcm16_fallback_frames','frames'):assert item[key]==report[key]
        scored=EVIDENCE/('dha-bridge2-quality0-score' if zero else 'dha-bridge2-quality-pilot')
        quality=load(scored/'report.json');assert quality['complete'] and not quality['complete_song_measured']
        assert quality['original_physical_PCM16_sha256']==sha(physical.tobytes())
        assert quality['codec_file_bytes']==len((folder/'audio.dhaf').read_bytes())
        assert quality['measured_physical_samples']==count and quality['coded_samples_charged']==2*count
        for row in quality['rows']:
            if row['codec']=='DHA_bridge2':assert row['PCM16_sha256']==sha(actual_physical.tobytes())
        self.bridge.append(dict(name=name,samples=count,file_bytes=report['file_bytes'],
            dha_frames=report['dha_frames'],fallback_frames=report['pcm16_fallback_frames'],
            source_even_mapping_midpoints_and_DLL_decode_exact=True,
            quality_report_authenticated_not_rerendered=True))

    def git_and_disk(self):
        for ref in ('f009fb18','9879e8a9'):
            full=subprocess.check_output(['git','rev-parse',ref+'^{commit}'],cwd=ROOT,text=True).strip()
            names=subprocess.check_output(['git','ls-tree','-rz','--name-only',full,'audiobook-beeper','toolkit'],cwd=ROOT).decode().split('\0')
            originals=[name for name in names if Path(name).suffix in ('.py','.c','.h','.asm')]
            delta=subprocess.check_output(['git','diff','--no-ext-diff','--name-status',full,'--','audiobook-beeper','toolkit'],cwd=ROOT,text=True)
            changes=[line for line in delta.splitlines() if Path(line.split('\t')[-1]).suffix in ('.py','.c','.h','.asm') and not line.startswith('A\t')]
            assert not changes,changes
            self.original_code.append(dict(ref=full,tracked_source_paths=len(originals),modified_original_source_paths=changes,
                newly_added_files_excluded=True,git_diff_worktree_including_index=True))
            pointer=subprocess.check_output(['git','show',full+':ZX-music-Sea-Foam-SNR20-RAM-auto.trd'],cwd=ROOT)
            match=re.search(rb'oid sha256:([0-9a-f]{64})',pointer)
            expected=match.group(1).decode() if match else sha(pointer)
            delivered=Path('C:/Work/ZX-video/ZX-music-Sea-Foam-SNR20-RAM-auto.trd')
            assert sha(delivered.read_bytes())==expected and expected.startswith('b96763ca')
        self.delivered_disk=dict(path=str(delivered),bytes=delivered.stat().st_size,sha256=expected,
            exact_against_both_original_Git_LFS_identities=True)

    def links(self):
        path=ROOT/'audiobook-beeper/DHA_TRIAL.md';text=path.read_text(encoding='utf-8');rows=[]
        for url in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in url or url.startswith('#'):continue
            target=path.parent/url.split('#')[0];rows.append(dict(link=url,exists=target.exists()))
            assert target.exists(),url
        self.documentation_links=dict(path=str(path.relative_to(ROOT)),links=rows,
            dha_host_report_is_valid_aggregate=True,first_song_nested_report_exists=(EVIDENCE/'dha-host/sea_foam/report.json').exists())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=EVIDENCE/'dha-audit')
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve prior audit; choose a new empty output')
    out.mkdir(parents=True,exist_ok=True);audit=Audit(out)
    folders=['dha-host','dha-host-corpus','dha-common-model','dha-common-host','dha-architecture','dha-precision','dha-pcm8',
             'dha-bridge2-pilot','dha-bridge2-quality-pilot','dha-bridge2-quality0-pilot','dha-bridge2-quality0-score']
    folders += [family+'/'+name for family in ('dha-quality-default','dha-quality-common') for name in NAMES]
    for name in folders:audit.section('manifest:'+name,lambda name=name:audit.manifest(name))
    producers=[('dha-host/harness.py.gz','dha_host_probe.py'),('dha-host-corpus/harness.py.gz','dha_host_corpus.py'),
        ('dha-common-model/producer.py.gz','dha_fit_common.py'),('dha-common-host/dha_common_host.py.gz','dha_common_host.py'),
        ('dha-common-host/dha_common_host.c.gz','dha_common_host.c'),('dha-bridge2-pilot/harness.py.gz','dha_bridge2_pilot.py'),
        ('dha-bridge2-pilot/dha_bridge2_pilot.c','dha_bridge2_pilot.c'),
        ('dha-bridge2-quality0-pilot/harness.py.gz','dha_quality_host.py'),('dha-bridge2-quality0-pilot/dha_quality_host.c','dha_quality_host.c'),
        ('dha-bridge2-quality-pilot/producer.py.gz','dha_bridge2_score.py'),('dha-bridge2-quality0-score/producer.py.gz','dha_bridge2_score.py')]
    producers += [(family+'/'+name+'/producer.py.gz','dha_host_score.py') for family in ('dha-quality-default','dha-quality-common') for name in NAMES]
    for archive,current in producers:
        audit.section('producer:'+archive,lambda archive=archive,current=current:audit.producer(EVIDENCE/archive,HERE/current))
    audit.section('pinned-library-source-tables-and-binary-identities',audit.pinned_sources)
    audit.section('default-whole-nine-container-DLL-source-parity',lambda:audit.corpus(False))
    audit.section('common-whole-nine-container-DLL-source-parity',lambda:audit.corpus(True))
    audit.section('common-model-training-and-adapter-control',audit.common_model)
    for common in (False,True):
        for name in NAMES:audit.section('quality-inputs-and-unfiltered-metrics:'+str(common)+':'+name,
            lambda common=common,name=name:audit.quality(common,name))
    audit.section('retained-external-architecture-precision-source-identities',audit.retained_sources)
    audit.section('resident-pcm8-saved-native-bit-and-tick-recheck',audit.pcm8)
    for zero in (False,True):audit.section('bridge2-pilot:'+str(zero),lambda zero=zero:audit.bridge2(zero))
    audit.section('original-code-and-delivered-TRD',audit.git_and_disk)
    audit.section('DHA-documentation-relative-paths',audit.links)
    report=dict(complete=not audit.failures,date='2026-10-20',read_only_evidence_audit=True,
        checks=audit.checks,failures=audit.failures,manifest_archives=audit.manifests,
        manifest_artifact_count=sum(x['files'] for x in audit.manifests),
        producers=audit.producers,pinned_source_files=audit.snapshots,containers=audit.containers,
        quality_reports=audit.qualities,bridge_pilots=audit.bridge,original_code=audit.original_code,
        delivered_disk=getattr(audit,'delivered_disk',None),documentation_links=getattr(audit,'documentation_links',None),
        retained_information=audit.information,no_encoding_compilation_native_filter_or_fit_rerun=True,
        filtered_scores_authenticated_not_recomputed=True,physical_hardware_tested=False,release_accepted=False,
        producer_sha256=sha(Path(__file__).read_bytes()))
    save(out/'report.json',report)
    (out/'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'}
    save(out/'manifest.json',dict(artifact_files=artifacts))
    print(json.dumps(dict(complete=report['complete'],checks=len(audit.checks),failures=[x['check'] for x in audit.failures],
        manifests=len(audit.manifests),artifacts=report['manifest_artifact_count'],containers=len(audit.containers),qualities=len(audit.qualities))))
    if audit.failures:raise SystemExit(1)


if __name__=='__main__':main()
