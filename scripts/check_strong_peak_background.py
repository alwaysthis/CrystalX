"""Read-only comparison on a supplied RAS, never copying research source files."""
import sys
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from crystalx.xrd_io import read_xrd
from crystalx.background import fit_background

scan=read_xrd(sys.argv[1])[0]; x=np.array(scan.x); y=np.array(scan.intensity)
old=np.array(fit_background(x,y,method='asls')); new=np.array(fit_background(x,y))
assert np.isfinite(new).all() and np.all(new>=0)
figure=Figure(figsize=(12,7),dpi=150,layout='constrained'); FigureCanvasAgg(figure)
top,bottom=figure.subplots(2,1,sharex=True,gridspec_kw={'height_ratios':[2,1]})
top.set_yscale('log',nonpositive='mask'); top.plot(x,y,color='#333333',lw=.6,label='Raw XRD')
top.plot(x,old,color='#d55e00',ls='--',lw=1.4,label='Previous AsLS')
top.plot(x,new,color='#0072b2',lw=1.8,label='Updated automatic')
top.set_ylabel('Intensity (counts)',fontfamily='Times New Roman',fontsize=18); top.legend(frameon=False,fontsize=11,loc='upper left')
bottom.plot(x,old,color='#d55e00',ls='--',lw=1.4,label='Previous AsLS')
bottom.plot(x,new,color='#0072b2',lw=1.8,label='Updated automatic'); bottom.axhline(0,lw=.7,color='#777777')
bottom.set_ylabel('Baseline (counts)',fontfamily='Times New Roman',fontsize=18); bottom.set_xlabel(r'$2\theta$ (°)',fontsize=18)
for axis in (top,bottom): axis.tick_params(direction='in',labelsize=12); axis.margins(x=.01)
target=Path(__file__).resolve().parents[1]/'output/xrd-background-comparison.png'; figure.savefig(target)
print('Previous baseline range:',float(old.min()),float(old.max()))
print('New baseline range:',float(new.min()),float(new.max()))
print('Comparison:',target)
