"""Prepare and preview source-native CB47 frames without changing the source."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import native_lineart as line


def scaffold_frames(count, directory):
    """Valid empty legacy input only for the retained boot/audio compiler.

    CB47 replaces every legacy picture consumer and installs independent
    native screen histories. These bytes never generate a published image.
    Keep an explicit portable scaffold instead of quantizing a discarded2x2
    picture; full native CPU/Fuse references remain the actual6912-byte frames.
    """
    states=np.lib.format.open_memmap(Path(directory)/'states.npy',mode='w+',dtype=np.uint8,shape=(count,3840))
    states[:]=0;states[:,3072:]=1;states.flush()
    np.savez(Path(directory)/'conversion.npz',states=states)
    return states,dict(scaffold_only=True,published_pixel_reference=False)


def prepare_frames(images, directory, *, dark_fills=True):
    if images.ndim != 4 or images.shape[1:] != (144,256,3) or not len(images):raise ValueError('expected native256x144 RGB frames')
    states = np.lib.format.open_memmap(Path(directory)/'native-states.npy',mode='w+',dtype=np.uint8,shape=(len(images),6912))
    image = np.zeros((192,256,3),np.uint8);errors=[];fine_blocks=[]
    for i,active in enumerate(images):
        image[24:168] = active;state=line.encode(image,dark_fills=dark_fills);states[i] = np.frombuffer(state,np.uint8)
        actual=line.pixels(state);errors.append(float(np.mean((actual[24:168]-active)**2)))
        bits,_=line.unpack(state);blocks=bits.reshape(96,2,128,2).transpose(0,2,1,3).reshape(96,128,4)
        fine_blocks.append(int((blocks.max(-1) != blocks.min(-1))[12:84].sum()))
        if i%100 == 0:print(f'Native lineart: {i+1}/{len(images)}',flush=True)
    states.flush()
    return states,dict(metric='Native-pixel RGB MSE, active256x144 original source',mean_mse=float(np.mean(errors)),
        frame_mse=errors,native_resolution=[256,192],active_resolution=[256,144],host_frame_bytes=6912,
        dither='none',contour_sampling_native_pixels=1,thin_strokes_keep_source_width=True,
        thin_strokes_add_parallel_contours=False,dark_fills=dark_fills,parameters=line.PARAMETERS,
        nonuniform_two_by_two_blocks=fine_blocks,contours=True,semantic_person_model=False,
        scope='Stylistic source tracing with source-close solid fills, not photographic or semantic recognition grade.')


def write_preview(images,states,path):
    selected=np.linspace(0,len(images)-1,min(6,len(images)),dtype=int)
    canvas=Image.new('RGB',(1024,len(selected)*312),'#181818');draw=ImageDraw.Draw(canvas)
    for row,i in enumerate(selected):
        for col,(name,picture) in enumerate((('Source native',images[i]),('CB47 native',line.pixels(states[i])[24:168].astype(np.uint8)))):
            draw.text((col*512+4,row*312+4),f'{i/10:.1f}s {name}',fill='white')
            canvas.paste(Image.fromarray(picture).resize((512,288),Image.Resampling.NEAREST),(col*512,row*312+24))
    canvas.save(path)
