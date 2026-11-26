import unittest
import numpy as np
from crystalx.xrr_thickness import estimate_thickness,detect_fringe_maxima,wavelength_from_metadata

class ThicknessTests(unittest.TestCase):
    def test_fifty_nm_two_theta_theta_and_q(self):
        q=np.arange(3,12)*2*np.pi/500; theta=np.rad2deg(np.arcsin(q*1.5406/(4*np.pi)))
        for values,axis in ((theta*2,'2theta'),(theta,'theta'),(q,'q_a'),(q*10,'q_nm')):
            result=estimate_thickness(values,axis=axis); self.assertAlmostEqual(result.thickness_nm,50,places=9)
            self.assertAlmostEqual(result.r2,1); self.assertLess(result.standard_error_nm,1e-10)
        self.assertAlmostEqual(estimate_thickness((theta*2)[::-1]).thickness_nm,50)

    def test_missing_orders_and_critical_angle(self):
        orders=np.array([3,4,6,7]); wavelength=1.5406; qc=4*np.pi*np.sin(np.deg2rad(.2))/wavelength
        q=np.sqrt((orders*2*np.pi/800)**2+qc**2); theta=np.rad2deg(np.arcsin(q*wavelength/(4*np.pi)))
        result=estimate_thickness(theta*2,orders=orders,critical_angle=.2)
        self.assertAlmostEqual(result.thickness_nm,80,places=8)
        self.assertIsNone(estimate_thickness([1,2]).standard_error_nm)

    def test_invalid_inputs(self):
        for values,kwargs in (([1],{}),([1,1],{}),([1,float('nan')],{}),([1,2],{'orders':[1,1]}),([1,2],{'orders':[1,2.5]}),([.1,.2],{'critical_angle':.5})):
            with self.assertRaises(ValueError): estimate_thickness(values,**kwargs)

    def test_metadata_units_and_fallback(self):
        value,note=wavelength_from_metadata({'HW_XG_WAVE_LENGTH_ALPHA1':'.15406','HW_XG_WAVE_LENGTH_UNIT':'nm'})
        self.assertAlmostEqual(value,1.5406)
        self.assertEqual(wavelength_from_metadata({})[0],1.5406)

    def test_synthetic_fringe_period(self):
        x=np.linspace(.5,5,6001); wavelength=1.5406; q=4*np.pi*np.sin(np.deg2rad(x/2))/wavelength
        y=(1+.45*np.cos(q*600))/(x+.1)**4
        peaks=detect_fringe_maxima(x,y,.7,4.8)
        self.assertGreater(len(peaks),5); result=estimate_thickness(peaks,wavelength)
        self.assertAlmostEqual(result.thickness_nm,60,delta=1)

    def test_marks_clipboard_preserves_independent_markers(self):
        from crystalx.plot_curves import PlotCurve
        from crystalx.plot_style import default_style
        style=default_style(); marks=[{'x':.6,'order':1},{'x':.8,'order':3}]
        curve=PlotCurve([.5,.6,.8,1],[1,5,4,1],style['curve'],'XRR',points=[0],peaks=[1],thickness_marks=marks)
        restored=PlotCurve.from_clipboard(curve.clipboard(style['general']))
        self.assertEqual(restored.thickness_marks,marks); self.assertEqual(restored.points,[0]); self.assertEqual(restored.peaks,[1])
        self.assertNotIn('thickness_marks',curve.settings())
