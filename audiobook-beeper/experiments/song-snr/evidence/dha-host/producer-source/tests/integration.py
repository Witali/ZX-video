"""File-level CLI checks using only Python's standard library (not a runtime dependency)."""
from pathlib import Path
import argparse,hashlib,json,math,struct,subprocess,tempfile,wave,zlib

def write_wave(path,samples,channels=1,rate=25000):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(struct.pack('<'+'h'*len(samples),*samples))

def read_wave(path):
    with wave.open(str(path),'rb') as w:
        meta=(w.getnchannels(),w.getframerate(),w.getnframes(),w.getsampwidth())
        return meta,w.readframes(w.getnframes())

def packets(data):
    assert data[:4]==b'DHAF' and len(data)>=1572
    assert zlib.crc32(data[:1568])==struct.unpack_from('<I',data,1568)[0]
    at=1572;result=[]
    while at<len(data):
        n=struct.unpack_from('<I',data,at+4)[0];p=data[at:at+n]
        assert p[:4]==b'DHF1' and 32<=n<=8224 and len(p)==n
        assert zlib.crc32(p[:28]+p[32:])==struct.unpack_from('<I',p,28)[0]
        result.append(p);at+=n
    assert at==len(data)
    return result

def run_tests(cli,output):
    output.mkdir(parents=True,exist_ok=True)
    output=Path(tempfile.mkdtemp(prefix='case-',dir=output))
    count=0;cases=[]
    def run(*args,ok=True):
        nonlocal count
        result=subprocess.run([str(cli),*map(str,args)],capture_output=True,text=True)
        assert (result.returncode==0)==ok,(args,result.returncode,result.stdout,result.stderr)
        count+=1;return result
    fixtures=[('empty',[],1,25000,4096),('one',[1234],1,25000,1),
        ('silence',[0]*4097,1,25000,4096),
        ('stereo',[v for i in range(769) for v in (int(9000*math.sin(i*.04)),int(5000*math.cos(i*.06)))],2,44100,256),
        ('voice-like',[int((7000*math.sin(i*.035)+2000*math.sin(i*.105))*(.65+.35*math.cos(i*.001))) for i in range(5001)],1,25000,4096),
        ('abrupt',[32767 if i&1 else -32768 for i in range(513)],1,48000,256)]
    for name,samples,channels,rate,frame in fixtures:
        source=output/(name+'.wav');packed=output/(name+'.dhaf');decoded=output/(name+'-decoded.wav')
        write_wave(source,samples,channels,rate)
        run('encode',source,packed,'--frame',frame,'--fast')
        inspection=run('info',packed).stdout
        run('decode',packed,decoded)
        meta,pcm=read_wave(decoded)
        assert meta==(channels,rate,len(samples)//channels,2)
        data=packed.read_bytes();p=packets(data)
        expected_groups=(len(samples)//channels+frame-1)//frame
        assert len(p)==channels*expected_groups
        for index,packet in enumerate(p):
            assert struct.unpack_from('<I',packet,8)[0]==index//channels
            assert packet[14]==index%channels
        raw=sum(packet[15]==0 for packet in p)
        if name in ('abrupt',):
            # The final one-sample frame is a valid constant extreme and can
            # use lossy DHA; only frames containing jumps require PCM.
            assert all(packet[15]==0 for packet in p if struct.unpack_from('<H',packet,12)[0]>1)
            expected=struct.pack('<'+'h'*len(samples),*samples)
            assert raw>=2 and pcm[:1024]==expected[:1024]
            assert abs(struct.unpack_from('<h',pcm,1024)[0]-samples[-1])<=18*256
        if name=='silence':assert len(data)<2*len(samples) and raw==0
        cases.append(dict(name=name,channels=channels,samples_per_channel=len(samples)//channels,
            sample_rate=rate,frame_samples=frame,packets=len(p),DHA_frames=len(p)-raw,PCM_frames=raw,
            input_pcm_bytes=2*len(samples),file_bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            inspection=inspection))
        before=packed.read_bytes();run('encode',source,packed,'--fast',ok=False);assert packed.read_bytes()==before
        run('decode',packed,decoded,ok=False)
    # Nonstandard RIFF chunk ordering with an odd JUNK chunk is still valid.
    fmt=struct.pack('<HHIIHH',1,1,25000,50000,2,16)
    chunk=lambda tag,payload:tag+struct.pack('<I',len(payload))+payload+(b'\0' if len(payload)&1 else b'')
    body=b'WAVE'+chunk(b'JUNK',b'abc')+chunk(b'data',b'\0\0'*257)+chunk(b'fmt ',fmt)
    odd=output/'odd-order.wav';odd.write_bytes(b'RIFF'+struct.pack('<I',len(body))+body)
    run('encode',odd,output/'odd-order.dhaf','--fast');run('info',output/'odd-order.dhaf')
    before=odd.read_bytes();run('encode',odd,odd,'--fast',ok=False);assert odd.read_bytes()==before
    same=output/'silence.dhaf';before=same.read_bytes();run('decode',same,same,ok=False);assert same.read_bytes()==before
    base=(output/'stereo.dhaf').read_bytes();p=packets(base);header=base[:1572]
    bad={
        'truncated-header':base[:1560], 'truncated-frame':base[:-1],
        'trailing-byte':base+b'\0','missing-channel':header+p[0],
        'swapped-channel':header+p[1]+p[0]+b''.join(p[2:]),
        'repeated-group':base+b''.join(p[:2]),
    }
    crc_bad=bytearray(base);crc_bad[1572+32]^=1;bad['bad-crc']=bytes(crc_bad)
    unknown=bytearray(base);struct.pack_into('<Q',unknown,16,2**64-1)
    struct.pack_into('<I',unknown,1568,zlib.crc32(unknown[:1568]))
    unknown_path=output/'unknown-length.dhaf';unknown_path.write_bytes(unknown)
    run('info',unknown_path);run('decode',unknown_path,output/'unknown-length.wav',ok=False)
    assert not (output/'unknown-length.wav').exists()
    for name,data in bad.items():
        path=output/(name+'.dhaf');dest=output/(name+'.wav');path.write_bytes(data)
        run('info',path,ok=False);run('decode',path,dest,ok=False);assert not dest.exists()
    invalid_wav={
        'outside-riff':odd.read_bytes()+b'x','short-riff':odd.read_bytes()[:-1],
        'not-wave':b'RIFF'+struct.pack('<I',4)+b'AVI ',
        'no-format':b'RIFF'+struct.pack('<I',12)+b'WAVEdata'+struct.pack('<I',0),
    }
    for name,data in invalid_wav.items():
        source=output/(name+'.wav');dest=output/(name+'.dhaf');source.write_bytes(data)
        run('encode',source,dest,'--fast',ok=False);assert not dest.exists()
    run('encode',odd,output/'invalid-frame.dhaf','--frame','0',ok=False)
    run('encode',odd,output/'invalid-frame.dhaf','--frame','4097',ok=False)
    return dict(status='passed',CLI_invocations=count,cases=cases,malformed_streams=len(bad),
        malformed_WAV_files=len(invalid_wav),no_resampling=True,quality_measured=False,
        cli_sha256=hashlib.sha256(cli.read_bytes()).hexdigest(),fixtures_directory=str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cli',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    report=run_tests(args.cli.resolve(),args.output.resolve())
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],CLI_invocations=report['CLI_invocations'],cases=len(report['cases']))))
