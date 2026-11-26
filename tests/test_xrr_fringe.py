import unittest
import numpy as np
from crystalx.xrr_fringe import analyze_fringes

class FringeTests(unittest.TestCase):
    def sample(self,n=3001):
        q=np.linspace(.03,.35,n)
        y=1000*np.exp(-12*q)*(1+.35*np.cos(2*np.pi*q/.025))
        return q,y

    def test_period_and_crop_invariance(self):
        q,y=self.sample(); original=y.copy(); all_peaks=analyze_fringes(q,y)
        self.assertAlmostEqual(all_peaks.period,.025,delta=.001)
        self.assertGreater(sum(p.status=='可靠' for p in all_peaks.result.peaks),6)
        crop=analyze_fringes(q,y,.08,.23)
        expected=[p.x for p in all_peaks.result.peaks if .08<=p.x<=.23]
        np.testing.assert_allclose([p.x for p in crop.result.peaks],expected)
        np.testing.assert_array_equal(y,original)
        self.assertTrue(all(p.fwhm is None for p in crop.result.peaks))

    def test_sampling_and_reversed_source_indices(self):
        centers=[]
        for n in (1501,3001):
            q,y=self.sample(n);r=analyze_fringes(q[::-1],y[::-1],.08,.23)
            centers.append([p.x for p in r.result.peaks])
            for p in r.result.peaks: self.assertEqual(q[::-1][p.index],p.x)
        np.testing.assert_allclose(centers[0],centers[1],atol=.0005)

    def test_monotonic_and_white_noise_do_not_make_reliable_fringe_sequence(self):
        q=np.linspace(.03,.35,3001)
        for y in (1000*np.exp(-15*q),100+np.random.default_rng(4).normal(0,5,len(q))):
            result=analyze_fringes(q,y)
            self.assertLess(sum(p.status=='可靠' for p in result.result.peaks),3)

    def test_multiple_periods_require_confirmation(self):
        q=np.linspace(.03,.55,5001);y=1000*np.exp(-4*q)*(1+.2*np.cos(2*np.pi*q/.025)+.2*np.cos(2*np.pi*q/.04))
        result=analyze_fringes(q,y)
        self.assertTrue(any('多个' in note for note in result.notes))

    def test_invalid_data(self):
        with self.assertRaises(ValueError): analyze_fringes([1,2,3],[1,2,1])
        with self.assertRaises(ValueError): analyze_fringes([1]*20,[2]*20)
