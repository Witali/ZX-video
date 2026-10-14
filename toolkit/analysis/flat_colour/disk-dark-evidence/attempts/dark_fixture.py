import numpy as np
import lineart_colour as line
from cell_palette_quality import averaged
saved = np.load('toolkit/analysis/flat_colour/disk-attempts/capacity-1005/cache-inputs.npz')
image = np.zeros((96,128,3), np.uint8)
for i in range(401, 501):
    image[12:84] = saved['source'][i]
    old = averaged(saved['states'][i])
    proposed = averaged(line.render_fills(line.source_fills(image, dark_fills=True),line.source_lines(image)))
    bad = np.mean((proposed-image)**2, -1)>np.mean((old-image)**2, -1)
    if bad.any():
        print(i, np.argwhere(bad).tolist(), flush=True)
        np.savez_compressed('.tmp/dark-regression-fixture.npz', source=image, baseline=saved['states'][i], frame=i)
        break
