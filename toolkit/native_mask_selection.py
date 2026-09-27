"""Choose existing sparse/dense output on the host, without changing pixels.

The Gray-cell renderer's variable band cost is 5853+4*parity for a full
band, or 261*marked-136*zero_groups for a partial band. Shared work cancels.
These costs exclude attributes (unchanged), IRQ/ULA, ZX0 and disk service.
"""
import numpy as np
from bulk_frame_stream import read_packet
from cell_screen_z80 import expected_tstates
from probe_cell_output_masks import masks
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header

OPTIONS=dict(fast_mask_dispatch=True,constant_attribute_borders=True,
             skip_black_borders=True,gray_cells=True)


def band_cost(flags,band):
    if len(flags)!=4 or not 0<=band<20: raise ValueError('invalid band')
    if flags==b'\xff'*4: return 5853+4*(band&1)
    return 261*sum(v.bit_count() for v in flags)-136*flags.count(0)


def choose_map(required):
    if len(required)!=80: raise ValueError('expected 80 map bytes')
    result=bytearray(required)
    # Keep the already omitted top/bottom bands unchanged.
    for band in range(1,19):
        flags=required[4*band:4*band+4]
        if band_cost(b'\xff'*4,band)<band_cost(flags,band):
            result[4*band:4*band+4]=b'\xff'*4
    return bytes(result)


def maps_for_states(states):
    baseline=masks(states,18)[0].reshape(-1,80)
    required=masks(states,32)[0].reshape(-1,80)
    chosen=np.array([list(choose_map(v.tobytes())) for v in required],dtype=np.uint8)
    # Verify all 32 cells, including unmarked bytes, against n-2 on the host.
    bitmap=states[:,256:2816].reshape(-1,20,4,32)
    previous=np.zeros_like(bitmap); previous[2:]=bitmap[:-2]
    marked=np.unpackbits(chosen.reshape(-1,20,4),axis=2).astype(bool)
    np.copyto(previous,bitmap,where=marked[:,:,None,:])
    if not np.array_equal(previous,bitmap): raise AssertionError('omitted changed pixel')
    return baseline,chosen


def rewrite(raw,baseline,chosen,start,end):
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    if len(baseline)!=count or len(chosen)!=count or not 0<=start<end<=count:
        raise ValueError('different frame/map ranges')
    result=bytearray(raw); rows=[]
    for index in range(count):
        at=r.pos; _,packet=read_packet(r,stored_guards=False)
        offset=at+2+packet['coded_offset']-80
        old=raw[offset:offset+80]
        if old!=baseline[index].tobytes(): raise ValueError(('baseline map differs',index))
        if not start<=index<end: continue
        # Later independent boots replace their first two maps with FF.
        cold=bool(start and index<start+2)
        new=old if cold else chosen[index].tobytes()
        result[offset:offset+80]=new
        effective_old=b'\xff'*80 if cold else old
        effective_new=b'\xff'*80 if cold else new
        before=expected_tstates(effective_old,**OPTIONS)
        after=expected_tstates(effective_new,**OPTIONS)
        delta=sum(band_cost(effective_new[b*4:b*4+4],b)-band_cost(effective_old[b*4:b*4+4],b)
                  for b in range(1,19))
        if after-before!=delta or delta>0: raise AssertionError('output formula differs or regresses')
        rows.append(dict(frame=index,offset=offset,baseline_map_hex=old.hex(),map_hex=new.hex(),
            cold_map_preserved=cold,changed_bands=sum(old[b*4:b*4+4]!=new[b*4:b*4+4] for b in range(1,19)),
            baseline_formula_tstates=before,formula_tstates=after,delta_tstates=delta))
    r.end(); inverse=bytearray(result)
    for row in rows: inverse[row['offset']:row['offset']+80]=bytes.fromhex(row['baseline_map_hex'])
    if inverse!=raw: raise AssertionError('changed bytes outside native maps')
    return bytes(result),rows
