"""Experimental integer polygons and flat rectangles for 128x72 shade maps.

Offline tracing/simplification; the independent reference rasterizer uses
integer arithmetic only. No Z80 renderer, playback speed or RAM fit claim.
Four shades are logical dither levels, not four global Spectrum colours.
"""
from collections import defaultdict
import struct

import cv2
import numpy as np

WIDTH,HEIGHT=128,72


class Reader:
    def __init__(self,data): self.data=data; self.pos=0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data): raise ValueError('truncated contour record')
        out=self.data[self.pos:self.pos+n]; self.pos+=n; return out
    def byte(self): return self.take(1)[0]
    def word(self): return struct.unpack('<H',self.take(2))[0]
    def end(self):
        if self.pos!=len(self.data): raise ValueError('trailing contour bytes')


def trace(mask):
    """Directed pixel-corner boundaries, right-turn choice at diagonal contact."""
    height,width=mask.shape; padded=np.pad(mask,1); edges=defaultdict(list)
    definitions=((~padded[:-2,1:-1],(0,0),(1,0)),
        (~padded[1:-1,2:],(1,0),(1,1)),
        (~padded[2:,1:-1],(1,1),(0,1)),
        (~padded[1:-1,:-2],(0,1),(0,0)))
    stride=width+1
    for outside,(ax,ay),(bx,by) in definitions:
        yy,xx=np.where(mask & outside)
        for y,x in zip(yy.tolist(),xx.tolist()):
            edges[(y+ay)*stride+x+ax].append((y+by)*stride+x+bx)
    loops=[]; directions={1:0,stride:1,-1:2,-stride:3}; rank={1:0,0:1,3:2,2:3}
    while edges:
        start=next(iter(edges)); here=start; previous=None; path=[]
        while True:
            path.append((here%stride,here//stride)); choices=edges[here]
            nxt=choices[0] if previous is None else min(choices,
                key=lambda target:rank[(directions[target-here]-previous)%4])
            previous=directions[nxt-here]; choices.remove(nxt)
            if not choices: del edges[here]
            here=nxt
            if here==start: break
        # Remove collinear grid vertices; keep holes and one-pixel components.
        pts=np.array(path,dtype=np.int32)
        incoming=pts-np.roll(pts,1,axis=0); outgoing=np.roll(pts,-1,axis=0)-pts
        corners=np.any(incoming!=outgoing,axis=1)
        loops.append(pts[corners])
    return loops


def simplify(loops,epsilon):
    if not epsilon: return loops
    return [cv2.approxPolyDP(p.reshape(-1,1,2),epsilon,True).reshape(-1,2)
            for p in loops]


def fill(loops,shape=(HEIGHT,WIDTH)):
    """Even-odd scan conversion at pixel centres, with half-open edge ranges.

    Ceil((intersection_x - 1/2)) gives the first covered pixel. All values
    are integers; a Z80 implementation can replace repeated division with
    a precomputed per-edge quotient/remainder stepping record.
    """
    height,width=shape; events=[[] for _ in range(height)]; updates=0
    for polygon in loops:
        if len(polygon)<3: continue
        for (x0,y0),(x1,y1) in zip(polygon,np.roll(polygon,-1,axis=0)):
            x0,y0,x1,y1=map(int,(x0,y0,x1,y1))
            if y1<y0: x0,y0,x1,y1=x1,y1,x0,y0
            dy=y1-y0
            if not dy: continue
            dx=x1-x0; denominator=2*dy
            for y in range(max(0,y0),min(height,y1)):
                numerator=2*dy*x0+(2*(y-y0)+1)*dx-dy
                events[y].append(-((-numerator)//denominator)); updates+=1
    out=np.zeros(shape,dtype=bool); spans=touches=0
    for y,xs in enumerate(events):
        xs.sort()
        if len(xs)%2: raise AssertionError('odd polygon intersections')
        for left,right in zip(xs[::2],xs[1::2]):
            left=max(0,min(width,left)); right=max(0,min(width,right))
            if right>left:
                out[y,left:right]=True; spans+=1
                touches+=2*((right+3)//4-left//4)
    return out,dict(edge_row_updates=updates,fill_spans=spans,native_byte_touches=touches)


def runs(values,where):
    """Integer horizontal spans; only marked pixels with identical values."""
    records=[]
    for y in range(values.shape[0]):
        x=0
        while x<values.shape[1]:
            if not where[y,x]: x+=1; continue
            start=x; value=int(values[y,x]); x+=1
            while x<values.shape[1] and where[y,x] and values[y,x]==value: x+=1
            records.append((start,y,x-start,value))
    return records


def rectangles(values,where):
    active={}; completed=[]; rows=defaultdict(list)
    for x,y,w,v in runs(values,where): rows[y].append((x,w,v))
    for y in range(values.shape[0]+1):
        current=set(rows[y])
        for key in list(active):
            if key not in current:
                x,w,v=key; first=active.pop(key); completed.append((x,first,w,y-first,v))
        for key in rows[y]:
            if key not in active: active[key]=y
    return completed


def polygon_packet(values,base_loops,epsilon):
    bg=int(np.bincount(values.ravel(),minlength=4).argmax())
    image=np.full(values.shape,bg,dtype=np.uint8); out=bytearray([2,bg]); count=vertices=updates=spans=touches=0
    saved={}
    for shade in range(4):
        if shade==bg: continue
        loops=simplify(base_loops[shade],epsilon); saved[shade]=loops
        out+=struct.pack('<H',len(loops))
        for polygon in loops:
            if len(polygon)>65535: raise ValueError('too many vertices')
            out+=struct.pack('<H',len(polygon))+polygon.astype(np.uint8).tobytes()
            count+=1; vertices+=len(polygon)
        mask,work=fill(loops,values.shape); image[mask]=shade
        updates+=work['edge_row_updates']; spans+=work['fill_spans']; touches+=work['native_byte_touches']
    differences=image!=values; patches=runs(values,differences)
    out+=struct.pack('<H',len(patches))
    for x,y,w,v in patches:
        out+=bytes((x,y,w,v)); touches+=2*((x+w+3)//4-x//4)
    return bytes(out),dict(epsilon=epsilon,contours=count,vertices=vertices,
        edge_row_updates=updates,fill_spans=spans,correction_spans=len(patches),
        pixels_before_correction=int(differences.sum()),background=bg,
        native_byte_touches_including_clear=4608+touches),saved,image


def rectangle_packet(values,previous):
    rects=rectangles(values,values!=previous)
    return bytes([1])+struct.pack('<H',len(rects))+b''.join(bytes(r) for r in rects),dict(rectangles=len(rects))


def packed_packet(values):
    grouped=values.reshape(HEIGHT,WIDTH//4,4)
    return bytes([0])+((grouped[:,:,0]<<6)|(grouped[:,:,1]<<4)|(grouped[:,:,2]<<2)|grouped[:,:,3]).tobytes()


def decode_pixels(data,previous):
    r=Reader(data); mode=r.byte()
    if mode==0:
        b=np.frombuffer(r.take(2304),dtype=np.uint8)
        result=((b[:,None]>>np.array([6,4,2,0]))&3).reshape(HEIGHT,WIDTH).copy()
    elif mode==1:
        result=previous.copy()
        for _ in range(r.word()):
            x,y,w,h,v=r.take(5)
            if not w or not h or x+w>WIDTH or y+h>HEIGHT or v>3: raise ValueError('invalid rectangle')
            result[y:y+h,x:x+w]=v
    elif mode in (2,3,4):
        bg=r.byte()
        if bg>3: raise ValueError('invalid shade')
        result=np.full((HEIGHT,WIDTH),bg,dtype=np.uint8)
        for shade in range(4):
            if shade==bg: continue
            loops=[]
            for _ in range(r.word()):
                count=r.word()
                if mode==2:
                    polygon=np.frombuffer(r.take(2*count),dtype=np.uint8).reshape(-1,2).astype(np.int32)
                elif mode==3:
                    x,y=r.take(2); start=(x,y); points=[]
                    for _ in range(count):
                        points.append((x,y)); step=r.byte(); direction,length=step>>6,(step&63)+1
                        dx,dy=((1,0),(0,1),(-1,0),(0,-1))[direction]; x+=dx*length; y+=dy*length
                    if (x,y)!=start: raise ValueError('unclosed grid contour')
                    polygon=np.array(points,dtype=np.int32).reshape(-1,2)
                else:
                    points=[]
                    if count:
                        x,y=r.take(2); points.append((x,y))
                        for _ in range(count-1):
                            step=r.byte()
                            if step==255: x,y=r.take(2)
                            else:
                                if step>>4==15 or step&15==15: raise ValueError('reserved vertex delta')
                                x+=(step>>4)-7; y+=(step&15)-7
                            points.append((x,y))
                    polygon=np.array(points,dtype=np.int32).reshape(-1,2)
                if np.any(polygon<0) or np.any(polygon[:,0]>WIDTH) or np.any(polygon[:,1]>HEIGHT): raise ValueError('invalid vertex')
                loops.append(polygon)
            result[fill(loops)[0]]=shade
        for _ in range(r.word()):
            x,y,w,v=r.take(4)
            if not w or x+w>WIDTH or y>=HEIGHT or v>3: raise ValueError('invalid correction')
            result[y,x:x+w]=v
    else: raise ValueError('unknown pixel mode')
    r.end(); return result


def compact_contours(data,*,grid=False):
    """Lossless format-only transcode: direction/run or short integer deltas."""
    r=Reader(data)
    if r.byte()!=2: raise ValueError('absolute polygons expected')
    bg=r.byte(); out=bytearray([3 if grid else 4,bg])
    for shade in range(4):
        if shade==bg: continue
        count=r.word(); out+=struct.pack('<H',count)
        for _ in range(count):
            n=r.word(); points=np.frombuffer(r.take(2*n),dtype=np.uint8).reshape(-1,2).astype(np.int32)
            if grid:
                commands=bytearray()
                for (x0,y0),(x1,y1) in zip(points,np.roll(points,-1,axis=0)):
                    dx,dy=int(x1-x0),int(y1-y0)
                    if bool(dx)==bool(dy): raise ValueError('nonorthogonal grid edge')
                    direction=0 if dx>0 else 2 if dx<0 else 1 if dy>0 else 3
                    left=abs(dx or dy)
                    while left:
                        part=min(left,64); commands.append((direction<<6)|(part-1)); left-=part
                out+=struct.pack('<H',len(commands))+points[0].astype(np.uint8).tobytes()+commands
            else:
                out+=struct.pack('<H',n)
                if n: out+=points[0].astype(np.uint8).tobytes()
                for first,second in zip(points,points[1:]):
                    dx,dy=map(int,second-first)
                    if -7<=dx<=7 and -7<=dy<=7: out.append(((dx+7)<<4)|(dy+7))
                    else: out.append(255); out+=second.astype(np.uint8).tobytes()
    count=r.word(); out+=struct.pack('<H',count)+r.take(count*4); r.end()
    return bytes(out)


def pack_attributes(current,previous):
    changed=np.flatnonzero(current!=previous); runs=[]; i=0
    while i<len(changed):
        first=int(changed[i]); last=first+1; i+=1
        while i<len(changed) and changed[i]==last and last-first<255: last+=1; i+=1
        runs.append(struct.pack('<HB',first,last-first)+current[first:last].tobytes())
    sparse=b'\x01'+struct.pack('<H',len(runs))+b''.join(runs)
    return min((b'\x00'+current.tobytes(),sparse),key=len)


def read_attributes(r,previous):
    mode=r.byte()
    if mode==0: return np.frombuffer(r.take(576),dtype=np.uint8).copy()
    if mode!=1: raise ValueError('unknown attribute mode')
    out=previous.copy()
    for _ in range(r.word()):
        start,n=struct.unpack('<HB',r.take(3))
        if not n or start+n>576: raise ValueError('invalid attribute span')
        out[start:start+n]=np.frombuffer(r.take(n),dtype=np.uint8)
    return out
