import unittest
import numpy as np
from crystalx.peak_finding import detect_peaks,PeakSettings
from crystalx.peak_fit import profile,FIT_MODELS
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class PeakFitTests(unittest.TestCase):
    def test_low_count_broad_peaks_fit_raw_observations(self):
        x=np.linspace(33,35.4,2401)
        for seed,center,height,width in ((31,34.2,4.8,.48),(72,34.61,4.1,.45)):
            truth=.25+profile(x,height,center,width,width,.6)
            y=np.random.default_rng(seed).poisson(truth).astype(float); original=y.copy()
            result=detect_peaks(x,y,PeakSettings(method='fit',min_distance=.005,min_width=.002))
            self.assertEqual(len(result.peaks),1)
            peak=result.peaks[0]
            self.assertAlmostEqual(peak.x,center,delta=.05); self.assertAlmostEqual(peak.fwhm,width,delta=.06)
            self.assertLess(peak.r2,.65); self.assertTrue(result.overlays['low_signal'])
            xx=np.array(result.overlays['smooth']['x']); fitted=np.array(result.overlays['smooth']['y'])
            mask=(x>=xx[0])&(x<=xx[-1]); predicted=np.interp(x[mask],xx,fitted)
            measured_r2=1-sum((y[mask]-predicted)**2)/sum((y[mask]-y[mask].mean())**2)
            self.assertAlmostEqual(peak.r2,measured_r2,delta=1e-5)
            np.testing.assert_array_equal(y,original)

    def test_low_signal_noise_is_not_accepted_as_a_broad_peak(self):
        x=np.linspace(0,2.4,2401)
        y=2+np.random.default_rng(21).normal(0,1,len(x))
        result=detect_peaks(x,y,PeakSettings(method='fit'))
        self.assertFalse(result.peaks)

    def test_noisy_broad_asymmetric_peak_is_one_smooth_model(self):
        x=np.linspace(19,25,1201); truth=10+profile(x,5000,22.21,.75,.60,.4)
        rng=np.random.default_rng(12); y=truth+rng.normal(0,np.sqrt(truth)*1.5); original=y.copy()
        result=detect_peaks(x,y,PeakSettings(method='fit'))
        self.assertEqual(len(result.peaks),1); peak=result.peaks[0]
        self.assertAlmostEqual(peak.x,22.21,delta=.004); self.assertAlmostEqual(peak.fwhm,.675,delta=.01); self.assertGreater(peak.r2,.99)
        smooth=result.overlays['smooth']; xx=np.array(smooth['x']); yy=np.array(smooth['y'])
        np.testing.assert_allclose(yy,10+profile(xx,5000,22.21,.75,.60,.4),atol=25)
        self.assertEqual(len(result.overlays['positions']),1); self.assertGreater(len(xx),len(x))
        np.testing.assert_array_equal(original,y)

    def test_known_symmetric_models_and_fwhm(self):
        x=np.linspace(-2,2,1001)
        for model in FIT_MODELS:
            eta=0 if model=='gaussian' else 1 if model=='lorentzian' else .35
            y=20+.3*x+profile(x,100,.1234,.4,.4,eta)
            result=detect_peaks(x,y,PeakSettings(method='fit',fit_model=model,prominence=2))
            self.assertEqual(len(result.peaks),1)
            self.assertAlmostEqual(result.peaks[0].x,.1234,delta=1e-4); self.assertAlmostEqual(result.peaks[0].fwhm,.4,delta=1e-4)

    def test_joint_peaks_are_not_blindly_merged(self):
        x=np.linspace(-2,3,2001); y=5+profile(x,100,0,.25,.25,.3)+profile(x,60,.5,.3,.3,.5)
        result=detect_peaks(x,y,PeakSettings(method='fit',prominence=2))
        self.assertEqual(len(result.peaks),2)
        np.testing.assert_allclose([peak.x for peak in result.peaks],[0,.5],atol=.003)

    def test_descending_roi_source_indices_and_clipboard(self):
        x=np.linspace(0,10,2001); y=5+profile(x,100,3.123,.3,.4,.5)+profile(x,80,7,.3,.3,.5)
        result=detect_peaks(x[::-1],y[::-1],PeakSettings(method='fit'),(2,4,0,200))
        self.assertEqual(len(result.peaks),1); peak=result.peaks[0]
        self.assertLess(abs(x[::-1][peak.index]-peak.x),.003)
        curve=PlotCurve(x[::-1].tolist(),y[::-1].tolist(),default_style()['curve'],'fit',peaks=[peak.index],peak_analysis=result.overlays)
        restored=PlotCurve.from_clipboard(curve.clipboard(default_style()['general']))
        self.assertEqual(restored.peak_position(peak.index),(peak.x,peak.fitted_y))
        self.assertNotIn('peak_analysis',curve.settings())

    def test_short_or_invalid_fits_report_error(self):
        with self.assertRaises(ValueError): detect_peaks([1,2,3],[1,2,1],PeakSettings(method='fit'))
        with self.assertRaises(ValueError): detect_peaks(np.arange(10),np.ones(10),PeakSettings(method='fit',fit_model='bad'))
