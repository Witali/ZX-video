"""Experimental literal borrowing from retained LZSA2 slots.

Host validation restricts the fast path to temporal/no-op and whole-fragment
commands. Headers, vectors, masks and Huffman input remain in fixed RAM.
Contained packets borrow their literal suffix until compact reconstruction;
cross-block packets and packets ending a completed slot use normal copying.
"""
import struct
from build_zxv_trd import MiniAssembler
from build_fap3_trd import player_harness, sha, padded, sectors
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from lzsa2_row_player import Builder as PreviousBuilder
from pipelined_frame_z80 import PAGE, helpers
from bulk_frame_z80 import LENGTH
from uncontended_frame import INPUT

COPY_OFFSET = 0x100


def validate_video(video):
    at = 0; rows = []
    while at < len(video):
        n = struct.unpack_from('<H', video, at)[0]
        body = video[at+2:at+2+n]
        if len(body) != n or n < 288:
            raise ValueError('truncated video-only packet')
        flags, masks, coded = struct.unpack_from('<BHH', body)
        if flags & 128 or any(v not in (0, 85, 86, 87, 88) for v in body[8:200]):
            raise ValueError('borrowed literals require temporal/whole-fragment packets without motion cache')
        prefix = 280 + masks + coded
        if prefix > n:
            raise ValueError('invalid literal suffix')
        rows.append(dict(offset=at, bytes=n, prefix_bytes=prefix, literal_bytes=n-prefix))
        at += n+2
    if at != len(video):
        raise ValueError('unconsumed video bytes')
    return rows


def generate(m, recon, wrapper):
    q = m['queue_labels']; rows = []
    fixed_origin, fixed_limit = recon['motion'], recon['clear_tile']
    a = MiniAssembler(fixed_origin); e, n = helpers(a, rows, 'borrowed_literals')
    def call(target): n('CALL '+str(target), 0xcd, target, 17)
    def jump(op, target): n('JP '+str(target), op, target, 10)
    def load(target): n('LD A,('+str(target)+')', 0x3a, target, 13)
    def ret(): e('RET', [0xc9], 10)

    a.label('prepare')
    load('borrowed_page'); e('OR A', [0xb7], 4); jump(0xca, 'prepare_run')
    n('LD HL,(literal pointer)', 0x2a, 'borrowed_pointer', 16)
    n('LD (wrapper literal pointer),HL', 0x22, wrapper['literal_pointer'], 16)
    call(PAGE)
    a.label('prepare_run'); jump(0xc3, wrapper['run'])

    # A pair of small bridges keeps table/code reads in bank 6. AF/BC must
    # survive paging, including the cached Huffman input held in B/C.
    a.label('page_huffman')
    e('PUSH AF', [0xf5], 11); e('PUSH BC', [0xc5], 11)
    e('LD A,16h', [0x3e, 0x16], 7); jump(0xc3, 'page_common')
    a.label('page_literals')
    e('PUSH AF', [0xf5], 11); e('PUSH BC', [0xc5], 11)
    load('borrowed_page'); e('OR A', [0xb7], 4); jump(0xc2, 'page_common')
    e('LD A,16h', [0x3e, 0x16], 7)
    a.label('page_common'); call(PAGE)
    e('POP BC', [0xc1], 10); e('POP AF', [0xf1], 10); ret()

    a.label('patch')
    call('page_huffman'); call(m['inline_huffman_patches']['origin']); call('page_literals'); ret()
    a.label('attributes')
    load(wrapper['raw_attribute_flag']); e('OR A', [0xb7], 4)
    jump(0xc2, recon['attribute_pass'])
    call('page_huffman'); call(recon['attribute_pass']); call('page_literals'); ret()
    a.label('state'); a.label('borrowed_page'); a.emit(0)
    a.label('borrowed_pointer'); a.word(0); a.label('fixed_end')
    labels = dict(a.labels); fixed = a.resolve()
    if a.pc > fixed_origin+COPY_OFFSET: raise ValueError('literal bridges exceed reserved motion prefix')

    a = MiniAssembler(fixed_origin+COPY_OFFSET); e, n = helpers(a, rows, 'borrowed_packet')
    def wl(target): n('LD HL,('+str(target)+')', 0x2a, target, 16)
    def ws(target): n('LD ('+str(target)+'),HL', 0x22, target, 16)
    a.label('copy')
    # Every new length read resets the borrowed pointer. A partial packet
    # cannot enable borrowing because its copy count differs from LENGTH.
    e('PUSH AF', [0xf5], 11); e('XOR A', [0xaf], 4)
    n('LD (borrowed page),A', 0x32, labels['borrowed_page'], 13)
    e('LD A,D', [0x7a], 4); e('CP input high', [0xfe, INPUT>>8], 7); jump(0xc2, 'fallback_pop')
    e('LD A,E', [0x7b], 4); e('OR A', [0xb7], 4); jump(0xc2, 'fallback_pop')
    e('POP AF', [0xf1], 10); n('LD (region),A', 0x32, 'region', 13)
    e('PUSH HL', [0xe5], 11); wl(LENGTH); e('OR A', [0xb7], 4)
    e('SBC HL,BC', [0xed, 0x42], 15); e('POP HL', [0xe1], 10); jump(0xc2, 'fallback')
    # No completed slot can be released while its bytes are borrowed.
    # With count=0 the partial active slot stays owned even if slot_left=0.
    e('PUSH HL', [0xe5], 11); wl(q['slot_left']); e('LD A,H', [0x7c], 4); e('OR L', [0xb5], 4)
    e('POP HL', [0xe1], 10); jump(0xc2, 'eligible')
    load(q['count']); e('OR A', [0xb7], 4); jump(0xc2, 'fallback')
    a.label('eligible')
    ws('source'); e('PUSH HL', [0xe5], 11); e('EX DE,HL', [0xeb], 4)
    e('ADD HL,BC', [0x09], 11); ws('virtual_end'); e('EX DE,HL', [0xeb], 4); e('POP HL', [0xe1], 10)
    # First 280 bytes include the header and vectors. The second copy is
    # the remaining metadata/Huffman prefix, with two actual lookahead bytes.
    n('LD DE,packet', 0x11, INPUT, 10)
    n('LD BC,280', 0x01, 280, 10); load('region'); call(q['bridge']['copy'])
    e('PUSH HL', [0xe5], 11); wl(INPUT+1); n('LD DE,(coded length)', (0xed,0x5b), INPUT+3, 20)
    e('ADD HL,DE', [0x19], 11); n('LD DE,282', 0x11, 282, 10); e('ADD HL,DE', [0x19], 11)
    ws('prefix'); n('LD DE,(packet length)', (0xed,0x5b), LENGTH, 20)
    e('OR A', [0xb7], 4); e('SBC HL,DE', [0xed,0x52], 15); jump(0xd2, 'copy_rest')
    wl('prefix'); n('LD DE,-280', 0x11, (-280)&65535, 10); e('ADD HL,DE', [0x19], 11)
    e('LD B,H', [0x44], 4); e('LD C,L', [0x4d], 4); e('POP HL', [0xe1], 10)
    n('LD DE,prefix suffix', 0x11, INPUT+280, 10); load('region'); call(q['bridge']['copy'])
    e('DEC HL', [0x2b], 6); e('DEC HL', [0x2b], 6); ws(labels['borrowed_pointer'])
    load('region'); e('CP 2', [0xfe,2], 7); jump(0xda, 'page_ready'); e('INC A', [0x3c], 4)
    a.label('page_ready'); e('OR 10h', [0xf6,0x10], 7); n('LD (borrowed page),A', 0x32, labels['borrowed_page'], 13)
    n('LD DE,(virtual end)', (0xed,0x5b), 'virtual_end', 20); ret()
    a.label('copy_rest')
    wl(LENGTH); n('LD DE,-280', 0x11, (-280)&65535, 10); e('ADD HL,DE', [0x19], 11)
    e('LD B,H', [0x44], 4); e('LD C,L', [0x4d], 4); e('POP HL', [0xe1], 10)
    n('LD DE,suffix', 0x11, INPUT+280, 10)
    a.label('fallback'); load('region'); jump(0xc3, q['bridge']['copy'])
    a.label('fallback_pop'); e('POP AF', [0xf1], 10); jump(0xc3, q['bridge']['copy'])
    a.label('region'); a.emit(0)
    for name in ('source', 'virtual_end', 'prefix'): a.label(name); a.word(0)
    a.label('end')
    code = a.resolve()
    if a.pc > fixed_limit: raise ValueError(('borrowed packet helper exceeds motion body', hex(a.pc)))
    return [(fixed_origin, fixed), (fixed_origin+COPY_OFFSET, code)], labels | a.labels, rows


def install(read8, put, m, raw):
    _, _, _, mapping, tables = read_header(Reader(raw), magic=b'FAP3')
    h = player_harness(bytes(4), tables, mapping, m['frames'],
        **{k:m[k] for k in ('inline_matches','fast_noop_scan','irq_safe_paging',
                           'static_cache_borders','carry_huffman','register_fragments')},
        cached_huffman_byte=True)
    recon, wrapper = h.frame.recon, h.frame.w
    regions, lab, rows = generate(m, recon, wrapper)
    overwritten=[]
    for at, blob in regions:
        before=bytes(read8(at+i) for i in range(len(blob)))
        overwritten.append(dict(address=at,bytes=len(blob),before_sha256=sha(before),
                                previous_use='host-excluded motion handler'))
        put(at, blob)
    patches = []
    def replace(pc, old, new, name):
        if bytes(read8(pc+i) for i in range(len(old))) != old: raise ValueError(('patch differs',name,hex(pc)))
        put(pc,new); patches.append(dict(address=pc,before_hex=old.hex(),code_hex=new.hex(),name=name,
                                        baseline_tstates=10 if old[0]==0xc3 else 17,tstates=10 if new[0]==0xc3 else 17))
    def transfer(pc, op, old, new, name):replace(pc,bytes([op])+old.to_bytes(2,'little'),bytes([op])+new.to_bytes(2,'little'),name)
    q=m['queue_labels']; sites=[r['address'] for r in m['slot_queue_instruction_listing'] if r['instruction']==f"CALL {q['bridge']['copy']}"]
    if len(sites)!=1: raise ValueError('queue copy caller differs')
    transfer(sites[0],0xcd,q['bridge']['copy'],lab['copy'],'borrow packet literal suffix')
    start,end=m['packet_labels']['prepare_bridge'],m['packet_labels']['draw_bridge']
    sites=[pc for pc in range(start,end-2) if bytes(read8(pc+i) for i in range(3))==b'\xcd'+wrapper['run'].to_bytes(2,'little')]
    if len(sites)!=1: raise ValueError('prepare bridge caller differs')
    transfer(sites[0],0xcd,wrapper['run'],lab['prepare'],'map borrowed literals for preparation')
    transfer(m['inline_huffman_patches']['redirect_address'],0xc3,m['inline_huffman_patches']['origin'],lab['patch'],'page Huffman patches')
    sites=[r['address'] for r in h.frame.instructions.values() if r['instruction']=='CALL attribute_pass']
    if len(sites)!=1: raise ValueError('attribute pass caller differs')
    transfer(sites[0],0xcd,recon['attribute_pass'],lab['attributes'],'page coded attributes')
    report=dict(enabled=True,experimental=True,regions=[dict(address=at,code_hex=blob.hex()) for at,blob in regions],
        labels=lab,listing=rows,patches=patches,overwritten=overwritten,code_and_state_bytes=sum(len(b) for _,b in regions),
        extra_buffer_bytes=0,readable_huffman_lookahead_bytes=2,compressed_video_delta_bytes=0,
        ownership='Borrow only when the take call retains its slot; reconstruct before another packet read.',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    m['borrowed_literals']=report
    return report


class Builder(PreviousBuilder):
    def ram(self,*args):
        sections,m=super().ram(*args)
        video,_=self.separated(m['frame_start'],m['frame_end_exclusive'])
        validation=validate_video(video)
        banks=self.expected_banks
        def bank(at):return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at):return banks[bank(at)][at&16383]
        def put(at,data):banks[bank(at)][at&16383:(at&16383)+len(data)]=data
        report=install(read8,put,m,self.raw)
        report['validated_packets']=len(validation);report['video_sha256']=sha(video)
        result=[]
        for section in sections:
            at=section['address']&16383; blob=bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(blob)==section['sha256']:result.append(section);continue
            coded=self.compress(blob)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(blob)))
        return result,m
