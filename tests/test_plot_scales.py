from copy import deepcopy
import unittest
import numpy as np
from crystalx.plot_scales import RootTransform,RootLocator,axis_scale
from crystalx.plot_style import default_style,validate_style,aspect_ratio
from crystalx.scientific_figure import make_figure,IntervalLocator
from crystalx.xrd_io import XrdScan

class RootScaleTests(unittest.TestCase):
    def test_aspect_presets_custom_and_invalid_values(self):
        self.assertIsNone(aspect_ratio('auto')); self.assertEqual(aspect_ratio('4:3'),4/3)
        self.assertEqual(aspect_ratio('1:1'),1); self.assertEqual(aspect_ratio('1.5'),1.5)
        for text in ('0:1','1:0','-1','nan','1:2:3','infinity','0.001'):
            style=default_style(); style['general']['aspect']=text
            with self.subTest(text=text),self.assertRaises(ValueError): validate_style(style)

    def test_transform_spacing_inverse_and_negative_mask(self):
        transform=RootTransform(); data=np.array([-1.,0.,1.,4.,9.])
        mapped=transform.transform(data)
        self.assertTrue(np.ma.is_masked(mapped[0])); np.testing.assert_allclose(mapped[1:],[0,1,2,3])
        np.testing.assert_allclose(transform.inverted().transform(mapped[1:]),data[1:])
        ticks=RootLocator().tick_values(0,100)
        self.assertTrue((ticks>=0).all()); self.assertGreater(len(ticks),3)
        np.testing.assert_allclose(np.diff(np.sqrt(ticks)),np.diff(np.sqrt(ticks))[0])

    def test_render_uses_same_transform_for_data_and_axis(self):
        style=default_style(); style['axes']['left']['sqrt']=True
        scan=XrdScan([1,2,3,4],[0,1,4,9]); figure,data,axes=make_figure(scan,style,(0,5,0,9),(700,500))
        points=data.transData.transform(np.column_stack((scan.x,scan.intensity)))
        np.testing.assert_allclose(np.diff(points[:,1]),np.diff(points[:,1])[0])
        self.assertEqual(data.get_yscale(),'sqrt'); self.assertEqual(axes['left'].get_yscale(),'sqrt')
        self.assertEqual(axes['bottom'].get_xscale(),'linear'); figure.clear()
        self.assertEqual(IntervalLocator(1,False,True).tick_values(0,9),[0,1,4,9])

    def test_validation_and_legacy_log_compatibility(self):
        style=default_style(); axis=style['axes']['left']; axis['sqrt']=True
        validate_style(style); self.assertEqual(axis_scale(axis),'sqrt')
        for patch in ({'ticks':'[-1 0 1]'},{'minimum':'-1'},{'log':True}):
            candidate=deepcopy(style); candidate['axes']['left'].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError): validate_style(candidate)
        legacy=default_style()
        for axis in legacy['axes'].values(): del axis['sqrt']
        legacy['axes']['left']['log']=True
        self.assertEqual(axis_scale(validate_style(legacy)['axes']['left']),'log')
