"""Measure CB42 on a bounded real window and audit four-volume RAM constraints."""
import argparse
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from build_long_video_trd import AyFrame
from cell_codebook_player import packet_code
from convert_cb41 import pack_blocks
from convert_video import write_json
import dynamic_row_dictionary as dynamic
from generic_cell_codebook import representation, row_sets
from measure_cell_codebook_movie import audio_size
from probe_adaptive_block_codecs import ExternalCodec
from test_dynamic_row_dictionary import fixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','metadata','lzsa','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    prepared=json.loads(args.prepared.read_bytes())
    frames=[]
    for chunk in prepared['chunks']:
        path=args.prepared.parent/chunk['file']
        assert sha(path.read_bytes())==chunk['sha256']
        with np.load(path,allow_pickle=False) as data:
            frames.extend(data['five_states'])
    frames=np.stack(frames)
    assert len(frames)==prepared['frames']
    raw_audio=(args.prepared.parent/'audio.bin').read_bytes()
    assert sha(raw_audio)==prepared['ay_sha256']
    audio=[AyFrame.deserialize(raw_audio[i:i+9]) for i in range(0,len(raw_audio),9)]
    metadata=json.loads(args.metadata.read_bytes())
    sets=row_sets(frames)
    boundaries=[round(len(frames)*i/4) for i in range(5)]
    quarters=[]
    for start,end in zip(boundaries,boundaries[1:]):
        _,sound=audio_size(audio,start,end,metadata['audio_labels'],frame_fields=5)
        quarters.append(dict(start=start,end=end,rows=len({0}.union(*sets[max(0,start-2):end])),
                             audio=sound))
    codec=ExternalCodec('lzsa2',args.lzsa,args.lzsa,'existing repository executable')
    cache=args.output/'lzsa';cache.mkdir(exist_ok=True)
    start,end=4216,4280
    variants={}
    for name,encode in (('static',representation),('dynamic',dynamic.representation)):
        chosen=encode(frames,start,end)
        packed,blocks=pack_blocks(chosen['raw'],codec,cache)
        (args.output/(name+'.raw')).write_bytes(chosen['raw'])
        (args.output/(name+'.stream')).write_bytes(packed)
        variants[name]=dict(raw_bytes=len(chosen['raw']),compressed_bytes=len(packed),
            raw_sha256=sha(chosen['raw']),stream_sha256=sha(packed),blocks=blocks,
            rows=chosen['rows'],frames=chosen['details'],row_updates=chosen.get('row_updates',0),
            screens_exact=chosen['full_host_screens_exact'],screen_sha256=chosen['screen_sha256'])
    assert variants['static']['screen_sha256']==variants['dynamic']['screen_sha256']
    code,labels,listing=packet_code(metadata,metadata['cell_codebook']['native_labels'],
        metadata['cell_codebook']['screen_base'],dynamic_rows=True)
    setup=sum(row['tstates'] for row in listing if labels['row_updates']<=row['address']<labels['replace_row'])
    loop=sum((max(row['tstates']) if isinstance(row['tstates'],list) else row['tstates'])
             for row in listing if labels['replace_row']<=row['address']<labels['state'] and row['instruction']!='JP body')
    fixture_dir=args.output/'fixture';fixture_dir.mkdir(exist_ok=True)
    synthetic=fixture()
    np.savez_compressed(fixture_dir/'frames.npz',five_states=synthetic)
    sound=b''.join(AyFrame((0,0,0),(0,0,0),0).serialize() for _ in range(len(synthetic)*5))
    (fixture_dir/'audio.bin').write_bytes(sound)
    write_json(fixture_dir/'preparation.json',dict(complete=True,frames=len(synthetic),ay_sha256=sha(sound),
        contract=dict(frame_fields=5,fps='10'),chunks=[dict(start=0,end=len(synthetic),file='frames.npz',
            sha256=sha((fixture_dir/'frames.npz').read_bytes()))],
        quality=[dict(screen_sha256=sha(dynamic.screen(synthetic,i))) for i in range(len(synthetic))]))
    proof=dynamic.representation(synthetic,0,len(synthetic))
    report=dict(complete=True,release=False,scope=__doc__,whole_movie_timing_verified=False,
        prepared_sha256=sha(args.prepared.read_bytes()),frames_sha256=sha(frames.tobytes()),
        ay_sha256=sha(raw_audio),four_equal_parts=quarters,
        window=[start,end],variants=variants,synthetic_updates=proof['row_updates'],
        packet_native=dict(code_bytes=len(code),code_sha256=sha(code),labels=labels,listing=listing,
            ordinary_packet_delta_tstates=18,renderer_delta_tstates=0,
            update_setup_tstates=setup,update_loop_tstates=loop,
            update_handler_formula=f'{setup+10-5} + {loop} * replaced_rows',
            excludes='queue take body, dispatch, packet length read, IRQ, contention and disk latency'),
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('dynamic_row_dictionary.py','cell_codebook_player.py','probe_dynamic_rows.py')})
    write_json(args.output/'report.json',report)
    print(json.dumps(dict(quarters=[dict(start=q['start'],end=q['end'],rows=q['rows'],
        audio_bytes=q['audio']['resident_bytes']) for q in quarters],
        window_bytes={name:v['compressed_bytes'] for name,v in variants.items()},
        synthetic_row_updates=proof['row_updates'],update_handler_formula=report['packet_native']['update_handler_formula'])))


if __name__=='__main__':main()
