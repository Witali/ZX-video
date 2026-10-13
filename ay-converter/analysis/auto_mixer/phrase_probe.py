"""Bounded lossless AY phrase-code experiment; no Spectrum decoder change.

AYP1 stores a dictionary of exact 2/4/8/16-state phrases, literal runs and
repeat-previous runs. Count dictionary/header bytes, then compare against
actual AYH1 and ordinary gzip. This is a host prototype, not a release wire.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import ay_interrupt
import ay_huffman_stream
from build_long_video_trd import AyFrame


def encode(raw):
    if len(raw) % 9:
        raise ValueError('expected whole AY9 states')
    states = [raw[p:p+9] for p in range(0, len(raw), 9)]
    frequencies = Counter()
    for size in (2, 4, 8, 16):
        frequencies.update(tuple(states[p:p+size]) for p in range(len(states)-size+1))
    # A repeated single state already has a cheaper run code. Rank only
    # varying phrases; actual overlap is resolved by the encoder below.
    choices = [(n*(9*len(word)-2)-(1+9*len(word)), word) for word,n in frequencies.items()
               if n>1 and len(set(word))>1]
    words = [word for saving,word in sorted(choices,reverse=True)[:64] if saving>0]
    # First calculate actual dictionary use; remove entries hidden by longer
    # greedy matches, so unused estimates never inflate the shipped dictionary.
    def stream(dictionary):
        output = bytearray(); used = Counter(); p = 0
        starts = {}
        for i,word in enumerate(dictionary):
            starts.setdefault(word[0], []).append((i,word))
        for options in starts.values():
            options.sort(key=lambda x:len(x[1]),reverse=True)
        def match(p):
            return next(((i,w) for i,w in starts.get(states[p],[]) if tuple(states[p:p+len(w)])==w),None)
        while p<len(states):
            if p and states[p]==states[p-1]:
                end=p+1
                while end<len(states) and end-p<255 and states[end]==states[p-1]: end+=1
                output.extend((1,end-p)); p=end; continue
            found=match(p)
            if found:
                i,word=found; output.extend((2,i)); used[i]+=1; p+=len(word); continue
            end=p+1
            while end<len(states) and end-p<255 and states[end]!=states[end-1] and match(end) is None: end+=1
            output.extend((3,end-p)); output.extend(b''.join(states[p:end])); p=end
        return output,used
    body, used = stream(words)
    words = [word for i,word in enumerate(words) if used[i]*(9*len(word)-2)>1+9*len(word)]
    body, used = stream(words)
    header = b'AYP1'+struct.pack('<IB',len(states),len(words))
    header += b''.join(bytes([len(word)])+b''.join(word) for word in words)
    return header+body,dict(dictionary_entries=len(words),dictionary_bytes=len(header)-9,
        dictionary_references=sum(used.values()),unchanged_ticks=sum(a==b for a,b in zip(states,states[1:])))


def decode(data):
    if data[:4]!=b'AYP1' or len(data)<9:
        raise ValueError('invalid phrase header')
    count, words = struct.unpack_from('<IB',data,4)
    position=9; dictionary=[]
    def take(n):
        nonlocal position
        result=data[position:position+n]; position+=n
        if len(result)!=n: raise ValueError('truncated phrase stream')
        return result
    for _ in range(words):
        size=take(1)[0]
        if size not in (2,4,8,16): raise ValueError('invalid phrase size')
        dictionary.append(take(size*9))
    output=bytearray()
    while len(output)<count*9:
        token,n=take(2)
        if token==1:
            if not output or not n: raise ValueError('invalid previous-state run')
            output.extend(output[-9:]*n)
        elif token==2:
            if n>=len(dictionary): raise ValueError('invalid dictionary index')
            output.extend(dictionary[n])
        elif token==3:
            if not n: raise ValueError('empty literal run')
            output.extend(take(n*9))
        else: raise ValueError('invalid phrase token')
    if len(output)!=count*9 or position!=len(data): raise ValueError('wrong phrase output length')
    return bytes(output)


def measure(raw):
    coded, info = encode(raw)
    if decode(coded)!=raw: raise AssertionError('phrase round trip failed')
    frames=[AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    records=ay_interrupt.encode_ticks(frames)
    huffman,_=ay_huffman_stream.encode(records)
    if ay_huffman_stream.decode(huffman)[1]!=records: raise AssertionError('AYH1 round trip failed')
    info.update(ticks=len(frames),raw_ay9_bytes=len(raw),raw_delta_bytes=sum(map(len,records)),
        phrase_bytes=len(coded),gzip_ay9_bytes=len(gzip.compress(raw,mtime=0)),
        gzip_phrase_bytes=len(gzip.compress(coded,mtime=0)),resident_ayh1_bytes=len(huffman),
        phrase_vs_resident_delta_bytes=len(coded)-len(huffman),exact_round_trip=True)
    return info


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--new-results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    paths={
        'current-entertainer':args.source_root/'ay-converter/analysis/noise_colour/evidence/release/soundtrack.ay9.gz',
        'current-o-henry':args.source_root/'ay-converter/analysis/o_henry/evidence/release/soundtrack.ay9.gz',
        'current-full-movie':args.source_root/'.tmp/refined-av-movie/audio.bin'}
    paths.update({f'new-{p.parent.parent.name}':p for p in args.new_results.glob('*/auto/soundtrack.ay9.gz')})
    results={}
    for name,path in paths.items():
        data=path.read_bytes(); raw=gzip.decompress(data) if path.suffix=='.gz' else data
        results[name]=measure(raw)
        print(name,json.dumps(results[name]),flush=True)
    args.output.write_text(json.dumps(dict(date='2026-10-13',cases=results,
        scope='Lossless host prototype; dictionary overhead counted; no native decoder or disk-delivery claim.'),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
