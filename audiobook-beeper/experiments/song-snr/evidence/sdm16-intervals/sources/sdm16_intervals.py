"""Exact selector-oriented representations of the full-input B packet map.

This experiment measures complete reachable domains, never a song-specific
palette. Compact byte counts are data-layout evidence, not a timed player,
release, or proof that a selector fits the existing 8-kHz instruction budget.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

from sdm16_precision import HOLDS, python_packet


HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = HERE/'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load(path=DEFAULT_TABLE):
    with np.load(path) as data:
        words, successors = data['words'].copy(), data['successors'].copy()
    assert words.shape == successors.shape == (65536,32)
    reached = {16}
    while True:
        expanded = reached | set(map(int,successors[:,sorted(reached)].ravel()))
        if expanded == reached:
            break
        reached = expanded
    return words,successors,sorted(reached)


def runs(row):
    starts = np.r_[0,np.flatnonzero(row[1:]!=row[:-1])+1]
    return starts,row[starts]


def area(word):
    return sum(hold for bit,hold in enumerate(HOLDS) if word & (1 << (15-bit)))


def q_parameters():
    """Exact floor decomposition; no division or float fitting at playback.

    qcode=floor(seedq+u/512+1/2-128*area/449+epsilon). Set
    t=128*area/449-1/2-epsilon, m=floor(t), T=ceil(512*(t-m)).
    Then qcode=seedq+(u>>9)-m-(low9<T), followed by historical clipping.
    """
    output=[]
    for weight_area in range(450):
        value=Fraction(128*weight_area,449)-Fraction(1,2)-Fraction(1,10**12)
        m=value.__floor__(); threshold=(512*(value-m)).__ceil__()
        assert -128<=m<=127 and 0<=threshold<=512
        output.append((m,threshold))
    return np.asarray(output,dtype='<i2')


def block_formats(words,successors,states,output):
    raw=(words[:,states].astype('u4')<<5)|successors[:,states]
    records,indices=np.unique(raw,return_inverse=True)
    grid=indices.reshape(65536,len(states)).T.reshape(len(states),256,256)
    record_data=b''.join(struct.pack('>HB',int(value)>>5,int(value)&31) for value in records)
    (output/'record-dictionary.bin').write_bytes(record_data)
    root=np.empty((len(states),256),'<u2'); shifted_root=np.empty_like(root)
    shifts=np.zeros_like(root,dtype='u1')
    exact_data=bytearray(); shifted_data=bytearray(); exact_ids={}; shifted_ids={}
    interval_counts=[]
    for rowid,rows in enumerate(grid):
        for high,row in enumerate(rows):
            starts,values=runs(row); count=len(values); interval_counts.append(count)
            if count==1:
                root[rowid,high]=shifted_root[rowid,high]=int(values[0])
                continue
            code=bytes([count])+struct.pack('<H',int(values[0]))+b''.join(
                struct.pack('<BH',int(at),int(value)) for at,value in zip(starts[1:],values[1:]))
            if code not in exact_ids:
                exact_ids[code]=len(exact_data); exact_data.extend(code)
            root[rowid,high]=0x8000|exact_ids[code]
            shift=int(starts[1]); shifted=bytes([count])+struct.pack('<H',int(values[0]))+b''.join(
                struct.pack('<BH',int(at)-shift,int(value)) for at,value in zip(starts[1:],values[1:]))
            if shifted not in shifted_ids:
                shifted_ids[shifted]=len(shifted_data);shifted_data.extend(shifted)
            shifted_root[rowid,high]=0x8000|shifted_ids[shifted];shifts[rowid,high]=shift
    assert len(exact_data)<32768 and len(shifted_data)<32768
    root.tofile(output/'high8-root.bin');(output/'high8-leaves.bin').write_bytes(exact_data)
    shifted_root.tofile(output/'shift-high8-root.bin');shifts.tofile(output/'shift-high8-offsets.bin')
    (output/'shift-high8-leaves.bin').write_bytes(shifted_data)
    # Exhaust every low byte through the actual selected descriptor format.
    for rowid in range(len(states)):
        for high in range(256):
            for roots,data,offsets in ((root,exact_data,None),(shifted_root,shifted_data,shifts)):
                entry=int(roots[rowid,high])
                if entry<0x8000:
                    decoded=np.full(256,entry,'u2')
                else:
                    at=entry&0x7fff;count=data[at];initial=struct.unpack_from('<H',data,at+1)[0]
                    starts=[0];values=[initial]
                    for k in range(count-1):
                        threshold,value=struct.unpack_from('<BH',data,at+3+3*k)
                        starts.append(threshold+(int(offsets[rowid,high]) if offsets is not None else 0));values.append(value)
                    decoded=np.asarray(values)[np.searchsorted(starts,np.arange(256),side='right')-1]
                np.testing.assert_array_equal(decoded,grid[rowid,high])
    histogram=dict(sorted(Counter(interval_counts).items()))
    return dict(high8_blocks=grid.shape[0]*256,intervals=sum(interval_counts),
        max_intervals=max(interval_counts),mean_intervals=float(np.mean(interval_counts)),
        interval_count_histogram=histogram,record_dictionary_records=len(records),
        record_dictionary_bytes=len(record_data),
        fixed6_records=dict(bytes_per_block=19,leaf_bytes=grid.shape[0]*256*19,
            total_bytes=grid.shape[0]*256*19+len(record_data)),
        variable_without_dedup=dict(root_bytes=root.nbytes,
            leaf_bytes=sum(3*k for k in interval_counts if k>1),
            total_bytes=root.nbytes+sum(3*k for k in interval_counts if k>1)+len(record_data)),
        exact_deduplicated=dict(variable_leaves=len(exact_ids),root_bytes=root.nbytes,
            leaf_bytes=len(exact_data),total_bytes=root.nbytes+len(exact_data)+len(record_data)),
        shifted_deduplicated=dict(variable_leaves=len(shifted_ids),root_bytes=shifted_root.nbytes+shifts.nbytes,
            leaf_bytes=len(shifted_data),total_bytes=shifted_root.nbytes+shifts.nbytes+len(shifted_data)+len(record_data)),
        all_reachable_cells_verified=True)


def hybrid(words,successors,states,output,root_bits=(0,4,5,6,8)):
    selected=words[:,states]
    word_values=np.unique(selected)
    assert len(word_values)<2048
    word_ids=np.full(65536,-1,'i4');word_ids[word_values]=np.arange(len(word_values))
    areas=np.array([area(int(word)) for word in word_values],dtype='<u2')
    dictionary=b''.join(struct.pack('>HB',int(word),int(a)&255) for word,a in zip(word_values,areas))
    (output/'hybrid-word-dictionary.bin').write_bytes(dictionary)
    params=q_parameters()
    param_bytes=b''.join(struct.pack('<bH',int(m),int(t)) for m,t in params)
    (output/'hybrid-q-parameters.bin').write_bytes(param_bytes)
    save(output/'hybrid-word-dictionary.json',dict(words=word_values.tolist(),weighted_areas=areas.tolist(),
        fields=['big-endian word16','weighted_area_low8'],area_high_in_interval_payload_bit=11,
        q_parameters=[dict(area=k,m=int(m),threshold=int(t)) for k,(m,t) in enumerate(params)]))
    body=bytearray(); row_starts=[]; all_records=[]; cut_offsets=[]; cut_deltas=[]; widths=[]; cut_counts=[]
    unsigned=np.arange(65536,dtype='i4')
    decoded_words=np.empty((65536,len(states)),'<u2')
    decoded_next=np.empty((65536,len(states)),'u1')
    for rowid,seed in enumerate(states):
        row_starts.append(len(body)); records=[]
        starts,values=runs(selected[:,rowid]);ends=np.r_[starts[1:],65536]
        for start,stop,word in zip(starts,ends,values):
            word_id=int(word_ids[int(word)]);a=int(areas[word_id]);recent=successors[start:stop,seed]&1
            changes=np.flatnonzero(recent[1:]!=recent[:-1])+1
            assert len(changes)<=1 and (not len(changes) or (recent[0]==0 and recent[-1]==1))
            payload=word_id|((a>>8)<<11)|(int(recent[0])<<12)|(bool(len(changes))<<13)
            position=len(body); body.extend(struct.pack('<HH',int(stop)-1,payload))
            if len(changes):body.extend(struct.pack('<H',int(start)+int(changes[0])))
            records.append((int(start),int(stop),position,payload))
            # Decode only serialized data and the shared dictionary/formula.
            endpoint,encoded=struct.unpack_from('<HH',body,position)
            literal,alow=struct.unpack_from('>HB',dictionary,3*(encoded&2047))
            decoded_area=alow+(((encoded>>11)&1)<<8)
            m,threshold=struct.unpack_from('<bH',param_bytes,3*decoded_area)
            u=unsigned[start:endpoint+1]
            qcode=np.clip(seed//2+(u>>9)-m-((u&511)<threshold),0,15)
            r=np.full(len(u),(encoded>>12)&1,'u1')
            if encoded&8192:r|=(u>=struct.unpack_from('<H',body,position+4)[0])
            decoded_words[start:endpoint+1,rowid]=literal
            decoded_next[start:endpoint+1,rowid]=(2*qcode+r).astype('u1')
            transitions=successors[start:stop,seed].astype('i4')
            cuts=np.flatnonzero(transitions[1:]!=transitions[:-1])+1
            deltas=transitions[cuts]-transitions[cuts-1]
            assert np.all((deltas==1)|(deltas==2))
            cut_offsets.extend(map(int,cuts));cut_deltas.extend(map(int,deltas))
            widths.append(int(stop-start));cut_counts.append(len(cuts))
        all_records.append(records)
    np.testing.assert_array_equal(decoded_words,words[:,states])
    np.testing.assert_array_equal(decoded_next,successors[:,states])
    assert len(body)<65536
    (output/'hybrid-intervals.bin').write_bytes(body)
    # Two bounded compact-q layouts. For every selected word the actual
    # difference u-C fits signed16, including C=-256 for area0. Thus storing
    # C modulo65536 is exact; no exceptional negative flag is required.
    distinct_areas=np.unique(areas)
    area_ids={int(a):k for k,a in enumerate(distinct_areas)}
    constants=np.array([(Fraction(65536*int(a),449)-256).__ceil__() for a in distinct_areas],dtype='i4')
    compact_params=(constants&65535).astype('<u2').tobytes()
    compact_dictionary=b''.join(struct.pack('>HB',int(word),area_ids[int(a)]&255)
        for word,a in zip(word_values,areas))
    inline_dictionary=b''.join(struct.pack('>H',int(word))+struct.pack('<H',
        (Fraction(65536*int(a),449)-256).__ceil__()&65535) for word,a in zip(word_values,areas))
    compact_body=bytearray(body);inline_body=bytearray(body);difference_min=32767;difference_max=-32768
    qraw_min=100;qraw_max=-100
    for rowid,records in enumerate(all_records):
        seed=states[rowid]
        for start,stop,position,payload in records:
            wid=payload&2047;a=int(areas[wid]);aid=area_ids[a]
            compact_payload=(payload&~(1<<11))|((aid>>8)<<11)
            struct.pack_into('<H',compact_body,position+2,compact_payload)
            struct.pack_into('<H',inline_body,position+2,payload&~(1<<11))
            u=unsigned[start:stop]
            for descriptor,compact_words,qdata in ((compact_body,compact_dictionary,compact_params),
                                               (inline_body,inline_dictionary,None)):
                endpoint,packed=struct.unpack_from('<HH',descriptor,position);word_id=packed&2047
                if qdata is None:
                    literal=struct.unpack_from('>H',compact_words,4*word_id)[0]
                    cmod=struct.unpack_from('<H',compact_words,4*word_id+2)[0]
                else:
                    literal,alow=struct.unpack_from('>HB',compact_words,3*word_id)
                    identifier=alow+(((packed>>11)&1)<<8)
                    cmod=struct.unpack_from('<H',qdata,2*identifier)[0]
                difference=((u-cmod+32768)&65535)-32768
                actual_c=(Fraction(65536*a,449)-256).__ceil__()
                np.testing.assert_array_equal(difference,u-actual_c)
                qraw=seed//2+(difference>>9)
                assert np.all((qraw>=0)&(qraw<=15))
                r=np.full(len(u),(packed>>12)&1,'u1')
                if packed&8192:r|=u>=struct.unpack_from('<H',descriptor,position+4)[0]
                np.testing.assert_array_equal(np.full(len(u),literal),words[start:stop,seed])
                np.testing.assert_array_equal(2*qraw+r,successors[start:stop,seed])
                difference_min=min(difference_min,int(difference.min()));difference_max=max(difference_max,int(difference.max()))
                qraw_min=min(qraw_min,int(qraw.min()));qraw_max=max(qraw_max,int(qraw.max()))
    (output/'hybrid-compactC-word-dictionary.bin').write_bytes(compact_dictionary)
    (output/'hybrid-compactC-parameters.bin').write_bytes(compact_params)
    (output/'hybrid-compactC-intervals.bin').write_bytes(compact_body)
    (output/'hybrid-inlineC-word-dictionary.bin').write_bytes(inline_dictionary)
    (output/'hybrid-inlineC-intervals.bin').write_bytes(inline_body)
    np.asarray(row_starts,dtype='<u2').tofile(output/'hybrid-state-starts.bin')
    state_map=np.full(32,255,'u1');state_map[states]=np.arange(len(states));state_map.tofile(output/'state-index.bin')
    roots=[]
    for bits in root_bits:
        root=np.empty((len(states),1<<bits),'<u2');visits=[]
        for rowid,records in enumerate(all_records):
            begins=np.array([record[0] for record in records]);ends=np.array([record[1] for record in records])
            for high in range(1<<bits):
                start=high<<(16-bits);stop=(high+1)<<(16-bits)
                first=int(np.searchsorted(ends,start,side='right'))
                root[rowid,high]=records[first][2]
                visits.append(int(np.count_nonzero((begins<stop)&(ends>start))))
                # One-byte low-input witness survives actual root traversal.
            for u in (0,32768+37,32768+38,65535):
                pointer=int(root[rowid,u>>(16-bits)])
                while True:
                    endpoint,payload=struct.unpack_from('<HH',body,pointer)
                    if u<=endpoint:break
                    pointer+=6 if payload&8192 else 4
                word,alow=struct.unpack_from('>HB',dictionary,3*(payload&2047))
                a=alow+(((payload>>11)&1)<<8);m,t=struct.unpack_from('<bH',param_bytes,3*a)
                # Use this row's seed, not the last seed from another loop.
                q=max(0,min(15,states[rowid]//2+(u>>9)-m-int((u&511)<t)))
                r=(payload>>12)&1
                if payload&8192:r|=int(u>=struct.unpack_from('<H',body,pointer+4)[0])
                assert (word,2*q+r)==(int(words[u,states[rowid]]),int(successors[u,states[rowid]])),(rowid,bits,u,word,q,r)
        root.tofile(output/f'hybrid-root-high{bits}.bin')
        total=root.nbytes+len(body)+len(dictionary)+len(param_bytes)+state_map.nbytes
        roots.append(dict(high_bits=bits,input_cells_per_root=1<<(16-bits),root_bytes=root.nbytes,
            max_word_records_per_root=max(visits),mean_word_records_per_root=float(np.mean(visits)),
            total_table_bytes_including_state_map=total,
            compactC_total_bytes=root.nbytes+len(compact_body)+len(compact_dictionary)+len(compact_params)+state_map.nbytes,
            inlineC_total_bytes=root.nbytes+len(inline_body)+len(inline_dictionary)+state_map.nbytes,
            memory_map=[dict(name='state-index',bytes=state_map.nbytes),dict(name='root',bytes=root.nbytes),
                dict(name='word intervals including optional recent cut',bytes=len(body)),
                dict(name='word16 and area-low dictionary',bytes=len(dictionary)),
                dict(name='area q-parameters',bytes=len(param_bytes))]))
    witness=[]
    for pcm in (37,38):
        state=16;trajectory=[]
        for _ in range(8):
            rowid=states.index(state);u=pcm+32768
            word=int(decoded_words[u,rowid]);state=int(decoded_next[u,rowid]);trajectory.append([word,state])
        witness.append(dict(pcm16=pcm,trajectory=trajectory))
    assert witness[0]['trajectory'][2][0]!=witness[1]['trajectory'][2][0]
    return dict(word_intervals=len(widths),word_dictionary_count=len(word_values),
        successor_cuts=len(cut_offsets),successor_delta_histogram=dict(Counter(cut_deltas)),
        recent_sign_cuts=cut_deltas.count(1),qcode_cuts=cut_deltas.count(2),
        max_successor_cuts_inside_word=max(cut_counts),max_word_interval_width=max(widths),
        successor_cut_offsets_le255=sum(offset<=255 for offset in cut_offsets),
        word_intervals_without_successor_cut=cut_counts.count(0),
        interval_body_bytes=len(body),dictionary_bytes=len(dictionary),q_parameter_bytes=len(param_bytes),
        compactC=dict(actual_weighted_areas=len(distinct_areas),word_dictionary_bytes=len(compact_dictionary),
            q_parameter_bytes=len(compact_params),interval_bytes=len(compact_body),
            q_parameters='C=ceil(65536*weighted_area/449-256), stored modulo65536 in areaID order',
            areaID_order=distinct_areas.tolist(),no_negative_exception_flag_required=True),
        inlineC=dict(word_dictionary_bytes=len(inline_dictionary),interval_bytes=len(inline_body),
            fields=['big-endian word16','little-endian C modulo65536'],record_bytes=4,
            area_high_payload_bit_not_used=True),
        valid_selected_difference_range=[difference_min,difference_max],qraw_range=[qraw_min,qraw_max],
        compact_q_raw_exact_without_clipping=True,
        root_formats=roots,all_reachable_cells_words_and_next_states_exact=True,
        verified_cells=65536*len(states),lower_one_bit_trajectory=witness,
        runtime_qcode_formula='clip(seed//2+(unsigned>>9)-m-(low9<threshold),0,15)',
        payload_bits=dict(word_id=[0,10],area_high=11,initial_recent=12,has_absolute_recent_cut=13),
        interval_layout='u16 inclusive endpoint,u16 payload,optional u16 absolute recent0-to1 cutoff; little endian',
        selector_timing_verified=False,banked_player_ram_fit_verified=False)


def run(table,output):
    table,output=Path(table).resolve(),Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('Preserve existing evidence; use an empty output')
    output.mkdir(parents=True,exist_ok=True)
    words,successors,states=load(table)
    report=dict(complete=False,table_sha256=sha(table.read_bytes()),reachable_states=states,
        reachable_cells=65536*len(states),model='Full16input B, beta.5, original449weights, q16/r2 packet state',
        no_source_specific_palette=True,original_encoder_or_player_changed=False,
        original_signed_PCM16_mapping='unsigned=PCM16+32768',
        producer_sha256=sha(Path(__file__).read_bytes()))
    report['blocks']=block_formats(words,successors,states,output)
    report['hybrid']=hybrid(words,successors,states,output)
    report['complete']=True
    report['decision']='Exact selector-friendly data representations only. Root traversal, qcode arithmetic, literal-to-pattern dispatch, state updates, alignment and full player allocation still require counted native integration; compression alone is not playback feasibility or release proof.'
    save(output/'report.json',report)
    files={path.name:dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for path in sorted(output.iterdir()) if path.is_file()}
    save(output/'manifest.json',dict(complete=True,artifact_files=files,artifact_count=len(files)))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table',type=Path,default=DEFAULT_TABLE)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=run(args.table,args.output)
    print(json.dumps(dict(complete=report['complete'],blocks=report['blocks'],hybrid=report['hybrid'])))
