"""Experimental exact row-video player with resumable LZSA2 outer blocks.

Bootstrap remains ZX0. No change to FAP3, AY, screens, slot capacity or disk
service. Reject blocks that cannot share their input/output bank safely.
"""
from copy import deepcopy
import struct
from row_dictionary_video import Builder as PreviousBuilder
from build_fap3_trd import sha,padded,sectors
from probe_adaptive_block_codecs import ExternalCodec
from inplace_zx0 import layout
import inplace_slot_input_z80 as producer
import lzsa2_stream
import resumable_lzsa2


def install(read8,put,m):
    if not m.get('fast_zx0',{}).get('enabled'):raise ValueError('requires adapted Fast ZX0 baseline')
    old=m['decoder_labels'];before=m['fast_zx0'];place=m['pre_fast_bank2_zx0']
    old_regions=[(r['address'],bytes.fromhex(r['code_hex'])) for r in before['regions']]
    for at,data in old_regions:
        if bytes(read8(at+i) for i in range(len(data)))!=data:raise ValueError(('old Fast decoder differs',hex(at)))
    regions,z,report=resumable_lzsa2.build(core=place['new_origin'],core_limit=place['new_end'])
    old_end=old_regions[0][0]+len(old_regions[0][1])
    if any(read8(at) for at in range(old_end,report['prefix_end'])):raise ValueError('prefix space occupied')
    names=('begin','slice_until','fatal','slice_output','slice_target','slice_caller_sp',
           'slice_decoder_sp','block_length','block_end','block_stored','input_pointer')
    remap={old[k]:z[k] for k in names};external=[]
    for pc,row in sorted({r['address']:r for r in m['slot_queue_instruction_listing']}.items()):
        if any(at<=pc<at+len(data) for at,data in old_regions):continue
        op,name,offset=read8(pc),row['instruction'],None
        if name.startswith('LD '):
            if op in (1,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
            if op in (0xdd,0xfd) and read8(pc+1) in (0x21,0x22,0x2a):offset=2
            if op==0xed and read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x63,0x6b,0x73,0x7b):offset=2
        if name.startswith(('CALL ','JP ')) and op in (0xc3,0xc2,0xca,0xd2,0xda,0xcd,0xc4,0xcc,0xd4,0xdc):offset=1
        if offset is None:continue
        original=read8(pc+offset)+256*read8(pc+offset+1)
        if any(at<=original<at+len(data) for at,data in old_regions) and original not in remap:
            raise ValueError(('unknown decoder reference',hex(pc),hex(original)))
        target=remap.get(original,original)
        if target==original:continue
        put(pc+offset,target.to_bytes(2,'little'))
        external.append(dict(address=pc,operand_address=pc+offset,instruction=name,old=original,new=target,
            previous_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
    if not any(r['old']==old['begin'] for r in external):raise ValueError('entry not remapped')
    pregions,p,prows=producer.build(z,m['disk_labels'],elapsed_fields=m['player_labels']['elapsed_fields'])
    if p!=m['producer_labels']:raise ValueError('producer state moved')
    for at,data in pregions:
        if bytes(read8(at+i) for i in range(len(data)))!=data:raise ValueError('producer remap differs')
    for at,data in old_regions:put(at,bytes(len(data)))
    for at,data in regions:put(at,data)
    put(0xa200,bytes(read8(at) for at in range(0x6100,0x6200)))
    m['previous_fast_zx0']=deepcopy(before);m['fast_zx0']=dict(enabled=False,replaced_by='lzsa2')
    m['decoder_labels']=z;m['decoder_end']=report['core_end'];m['player_labels']['zx0_fatal']=z['fatal']
    m['bank2_zx0']=dict(enabled=False,replaced_by='lzsa2')
    m['outer_codec']='lzsa2';m['inplace_video']['producer_listing']=prows
    m['inplace_video']['regions']=[dict(address=at,code_hex=data.hex()) for at,data in pregions]
    m['lzsa2']=dict(enabled=True,experimental=True,layout=report,external_operands=external,
        regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in regions],
        producer_reassembled_exact=True,cold_bridge_overlay_updated=True,extra_buffer_bytes=0,
        previous_decoder_bytes=before['decoder_bytes'],decoder_bytes=report['code_bytes'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


class Builder(PreviousBuilder):
    def __init__(self,*args,lzsa,**kwargs):
        super().__init__(*args,**kwargs)
        self.lzsa=ExternalCodec('lzsa2',lzsa,lzsa,'pinned local upstream LZSA2')

    def stream(self,start,end):
        key=start,end
        if key not in self.inplace_streams:
            video,_=self.separated(start,end);stream=bytearray();blocks=[]
            for lo in range(0,len(video),producer.MAX_OUTPUT):
                raw=video[lo:lo+producer.MAX_OUTPUT];payload=self.lzsa.encode_verified(raw,None,self.cache)
                exact,proof=lzsa2_stream.trace(payload,limit=len(raw))
                space=layout(len(payload),len(raw),proof['minimum_input_start'],len(stream))
                if exact!=raw or not space['sector_aligned_fits']:raise ValueError('unsafe LZSA2 in-place block')
                lzsa2_stream.trace(payload,limit=len(raw),input_start=space['input_start'])
                blocks.append(dict(raw_start=lo,raw_end=lo+len(raw),decoded_bytes=len(raw),codec='lzsa2',
                    compressed_bytes=len(payload),sha256=sha(raw),inplace_proof=proof,inplace_layout=space))
                stream+=struct.pack('<HH',len(raw),len(payload))+payload
            self.inplace_streams[key]=bytes(stream),blocks
        return self.inplace_streams[key]

    def ram(self,*args):
        sections,m=super().ram(*args);banks=self.expected_banks
        def bank(at):return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at):return banks[bank(at)][at&16383]
        def put(at,data):
            if (at&16383)+len(data)>16384:raise ValueError('cross-bank LZSA2 install')
            banks[bank(at)][at&16383:(at&16383)+len(data)]=data
        install(read8,put,m);result=[]
        for section in sections:
            at=section['address']&16383;raw=bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']:result.append(section);continue
            if section.get('startup_delta'):raise ValueError('unexpected startup table delta')
            coded=self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m
