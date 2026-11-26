import unittest
import numpy as np
from crystalx.background import fit_background
from crystalx.peak_finding import detect_peaks,PeakSettings,half_maximum_width
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class BackgroundTests(unittest.TestCase):
    def test_sloping_background_under_narrow_peaks(self):
        x=np.linspace(10,50,2001); baseline=10+.5*x
        y=baseline+100*np.exp(-.5*((x-20)/.08)**2)+60*np.exp(-.5*((x-35)/.12)**2)
        original=y.copy(); fitted=fit_background(x,y)
        np.testing.assert_array_equal(y,original)
        np.testing.assert_allclose(fitted,baseline,atol=.05)
        result=detect_peaks(x,y-fitted,PeakSettings(prominence=10))
        np.testing.assert_allclose([p.fwhm for p in result.peaks],2*np.sqrt(2*np.log(2))*np.array([.08,.12]),atol=.002)

    def test_irregular_descending_and_flat_background(self):
        x=np.linspace(0,10,1001)**1.1; y=5+.2*x+50*np.exp(-.5*((x-4)/.1)**2)
        a=fit_background(x,y); b=fit_background(x[::-1],y[::-1])
        np.testing.assert_allclose(a,b[::-1],atol=1e-7)
        np.testing.assert_allclose(a,5+.2*x,atol=.1)  # Natural endpoints are an estimate, not clamped.
        np.testing.assert_allclose(fit_background(x,np.full(len(x),7)),7,atol=1e-8)

    def test_bad_inputs(self):
        for x,y in (([1,2],[1,2]),([1,1,2,3,4],[0]*5),([1,2,3,4,5],[1,2,float('nan'),4,5])):
            with self.assertRaises(ValueError): fit_background(x,y)

    def test_fwhm_background_offset_and_descending(self):
        x=np.linspace(-2,2,4001); y=30+80*np.exp(-.5*(x/.2)**2)
        for xx,yy in ((x,y),(x[::-1],y[::-1])):
            peak=detect_peaks(xx,yy,PeakSettings(prominence=5)).peaks[0]
            self.assertAlmostEqual(peak.fwhm,2*np.sqrt(2*np.log(2))*.2,delta=1e-4)
            self.assertAlmostEqual(peak.intensity,110)
        self.assertIsNone(half_maximum_width(x,y,0,0,10))

    def test_clipboard_retains_raw_data_and_background_without_template_data(self):
        curve=PlotCurve([1,2,3],[3,8,4],default_style()['curve'],'sample',background=[2,2,2],show_background=True,subtract_background=True)
        restored=PlotCurve.from_clipboard(curve.clipboard(default_style()['general']))
        self.assertEqual(restored.y,[3,8,4]); self.assertEqual(restored.display_y,[1,6,2]); self.assertTrue(restored.show_background)
        self.assertNotIn('background',curve.settings())
        restored.subtract_background=False; self.assertEqual(restored.display_y,restored.y)
