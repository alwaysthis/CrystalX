"""Square-root axes with ticks spaced in transformed coordinates."""
import numpy as np
from matplotlib.scale import ScaleBase
from matplotlib.transforms import Transform
from matplotlib.ticker import Locator,MaxNLocator,ScalarFormatter,NullLocator

def axis_scale(axis): return 'log' if axis['log'] else 'sqrt' if axis.get('sqrt',False) else 'linear'

class SquareTransform(Transform):
    input_dims=output_dims=1; is_separable=True; has_inverse=True
    def transform_non_affine(self,values): return np.ma.asarray(values)**2
    def inverted(self): return RootTransform()

class RootTransform(Transform):
    input_dims=output_dims=1; is_separable=True; has_inverse=True
    def transform_non_affine(self,values): return np.ma.sqrt(np.ma.masked_less(values,0))
    def inverted(self): return SquareTransform()

class RootLocator(Locator):
    def __call__(self): return self.tick_values(*self.axis.get_view_interval())
    def tick_values(self,low,high):
        low,high=sorted((max(0,low),max(0,high)))
        ticks=MaxNLocator(nbins=6,min_n_ticks=3).tick_values(np.sqrt(low),np.sqrt(high))
        return ticks[ticks>=0]**2

class RootScale(ScaleBase):
    name='sqrt'
    def get_transform(self): return RootTransform()
    def set_default_locators_and_formatters(self,axis):
        axis.set_major_locator(RootLocator()); axis.set_major_formatter(ScalarFormatter()); axis.set_minor_locator(NullLocator())
    def limit_range_for_scale(self,vmin,vmax,minpos): return max(0,vmin),max(0,vmax)

def apply_scale(axes,horizontal,settings):
    coordinate=axes.xaxis if horizontal else axes.yaxis
    scale=axis_scale(settings)
    setter=axes.set_xscale if horizontal else axes.set_yscale
    if scale=='sqrt': setter(RootScale(coordinate))
    elif scale=='log': setter('log',nonpositive='mask')
    else: setter('linear')
