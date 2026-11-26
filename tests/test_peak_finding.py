import unittest
import numpy as np
from crystalx.peak_finding import detect_peaks,PeakSettings
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class PeakFindingTests(unittest.TestCase):
    def test_manual_rectangle_returns_source_indices_and_filters_y(self):
        x=np.linspace(-1,4,1001); y=10+100*np.exp(-.5*(x/.08)**2)+60*np.exp(-.5*((x-2.5)/.15)**2)
        settings=PeakSettings(prominence=2)
        result=detect_peaks(x,y,settings,(-.5,.5,0,200))
        self.assertEqual(len(result.peaks),1); self.assertEqual(result.peaks[0].index,200)
        result=detect_peaks(x[::-1],y[::-1],settings,(2,3,0,90))
        self.assertEqual(len(result.peaks),1); self.assertEqual(x[::-1][result.peaks[0].index],2.5)
        self.assertEqual(len(detect_peaks(x,y,settings,(-1,4,0,90)).peaks),1)
        with self.assertRaises(ValueError): detect_peaks(x,y,settings,(0,.001,0,200))

    def test_known_peak_positions_width_and_source_unchanged(self):
        x=np.linspace(-1,4,1001); y=10+100*np.exp(-.5*(x/.08)**2)+60*np.exp(-.5*((x-2.5)/.15)**2)
        original=y.copy(); result=detect_peaks(x,y,PeakSettings(prominence=5,min_distance=.5))
        np.testing.assert_array_equal(y,original)
        self.assertEqual(len(result.peaks),2)
        np.testing.assert_allclose([p.x for p in result.peaks],[0,2.5],atol=.006)
        np.testing.assert_allclose([p.width for p in result.peaks],2*np.sqrt(2*np.log(2))*np.array([.08,.15]),atol=.005)
        self.assertAlmostEqual(result.peaks[0].intensity,110)

    def test_noise_threshold_and_flat_signal(self):
        x=np.linspace(0,10,2001); rng=np.random.default_rng(7); y=rng.normal(0,.2,len(x))+10*np.exp(-.5*((x-4)/.1)**2)
        result=detect_peaks(x,y,PeakSettings(min_width=.05,min_distance=.3))
        self.assertTrue(any(abs(p.x-4)<.03 for p in result.peaks)); self.assertGreater(result.threshold,0)
        self.assertEqual(detect_peaks(x,np.zeros(len(x))).peaks,[])

    def test_physical_spacing_nonuniform_and_descending_index_mapping(self):
        x=np.linspace(0,3,3001)**1.1; y=10*np.exp(-.5*((x-1)/.03)**2)+5*np.exp(-.5*((x-1.3)/.03)**2)
        result=detect_peaks(x,y,PeakSettings(prominence=1,min_distance=.5))
        self.assertEqual(len(result.peaks),1); self.assertAlmostEqual(result.peaks[0].x,1,delta=.003)
        reversed_result=detect_peaks(x[::-1],y[::-1],PeakSettings(prominence=1))
        for peak in reversed_result.peaks: self.assertEqual(x[::-1][peak.index],peak.x)
        with self.assertRaises(ValueError): detect_peaks(x,y,PeakSettings(smoothing=True))

    def test_smoothing_and_width_filters(self):
        x=np.linspace(0,5,1001); y=np.exp(-.5*((x-2)/.1)**2)
        result=detect_peaks(x,y,PeakSettings(prominence=.1,min_width=.1,max_width=.5,smoothing=True,window=7))
        self.assertEqual(len(result.peaks),1)
        self.assertEqual(detect_peaks(x,y,PeakSettings(prominence=.1,min_width=.5)).peaks,[])
        for settings in (PeakSettings(smoothing=True,window=4),PeakSettings(prominence=-1),PeakSettings(min_width=2,max_width=1)):
            with self.assertRaises(ValueError): detect_peaks(x,y,settings)
        with self.assertRaises(ValueError): detect_peaks([1,1,2],[1,2,1])
        with self.assertRaises(ValueError): detect_peaks([1,2,3],[1,float('nan'),1])

    def test_peak_markers_copy_without_entering_presets(self):
        style=default_style(); curve=PlotCurve([1,2,3],[2,5,3],style['curve'],'plot 1',points=[0],peaks=[1])
        copied=PlotCurve.from_clipboard(curve.clipboard(style['general']))
        self.assertEqual(copied.peaks,[1]); self.assertEqual(copied.points,[0]); self.assertNotIn('peaks',curve.settings())
