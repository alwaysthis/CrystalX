import unittest,json
import numpy as np
from crystalx.peak_finding import detect_peaks,PeakSettings,PEAK_METHODS
from crystalx.background import fit_background
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class PeakMethodTests(unittest.TestCase):
    def test_three_methods_find_known_peaks_and_contours(self):
        x=np.linspace(0,10,2001); y=5+80*np.exp(-.5*((x-3)/.08)**2)+50*np.exp(-.5*((x-7)/.15)**2)
        original=y.copy()
        for method in PEAK_METHODS:
            with self.subTest(method=method):
                result=detect_peaks(x,y,PeakSettings(prominence=5,method=method))
                np.testing.assert_allclose([p.x for p in result.peaks],[3,7],atol=.01)
                np.testing.assert_allclose([p.fwhm for p in result.peaks],2*np.sqrt(2*np.log(2))*np.array([.08,.15]),atol=.005)
                self.assertEqual(len(result.overlays['contours']),2)
                for curve in result.overlays['contours']:
                    self.assertEqual(len(curve['x']),len(curve['y'])); self.assertGreater(max(np.array(curve['y'])-curve['baseline']),10)
        np.testing.assert_array_equal(original,y)

    def test_smoothed_roi_descending_keeps_source_indices(self):
        x=np.linspace(0,10,2001); y=5+80*np.exp(-.5*((x-3)/.08)**2)+50*np.exp(-.5*((x-7)/.15)**2)
        for method in PEAK_METHODS:
            result=detect_peaks(x[::-1],y[::-1],PeakSettings(prominence=5,smoothing=True,method=method),(2,4,0,100))
            self.assertEqual(len(result.peaks),1)
            self.assertAlmostEqual(x[::-1][result.peaks[0].index],result.peaks[0].x,delta=(x[1]-x[0])/2)
            smooth=result.overlays['smooth']; self.assertGreaterEqual(min(smooth['x']),2); self.assertLessEqual(max(smooth['x']),4)
            self.assertEqual(len(smooth['x']),len(smooth['y']))

    def test_invalid_method_and_wavelet_scales(self):
        for settings in (PeakSettings(method='bad'),PeakSettings(method='wavelet',wavelet_min=2,wavelet_max=1)):
            with self.assertRaises(ValueError): detect_peaks([1,2,3],[0,2,0],settings)

    def test_million_count_peak_does_not_lift_background(self):
        x=np.linspace(10,110,10001); baseline=2+.005*x; rng=np.random.default_rng(4)
        y=rng.poisson(baseline).astype(float)+1e6*np.exp(-.5*((x-46.47)/.02)**2)+600*np.exp(-.5*((x-44.2)/.25)**2)
        original=y.copy(); fitted=np.array(fit_background(x,y))
        self.assertTrue(np.all(fitted>=0)); self.assertLess(np.median(abs(fitted-baseline)),.5)
        self.assertLess(fitted[np.argmin(abs(x-46.47))],3)
        np.testing.assert_array_equal(original,y)
        np.testing.assert_allclose(fit_background(x[::-1],y[::-1]),fitted[::-1])

    def test_analysis_clipboard_and_style_settings_are_separate(self):
        x=np.linspace(0,4,401); y=5+30*np.exp(-.5*((x-2)/.1)**2)
        result=detect_peaks(x,y,PeakSettings(prominence=2,smoothing=True))
        curve=PlotCurve(x.tolist(),y.tolist(),default_style()['curve'],'peak',peak_analysis=result.overlays)
        restored=PlotCurve.from_clipboard(curve.clipboard(default_style()['general']))
        self.assertEqual(restored.peak_analysis,result.overlays); self.assertNotIn('peak_analysis',curve.settings())
        payload=json.loads(curve.clipboard(default_style()['general'])); payload['peak_analysis']['smooth']['y']=[float('nan')]*len(x)
        with self.assertRaises(ValueError): PlotCurve.from_clipboard(json.dumps(payload).encode())
