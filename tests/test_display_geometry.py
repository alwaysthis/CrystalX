import unittest
from copy import deepcopy
from crystalx.structure import Structure,dot
from crystalx.display_geometry import reciprocal,periodic_images

class DisplayGeometryTests(unittest.TestCase):
    def test_reciprocal_skew(self):
        cell=[[2,0,0],[1,3,0],[.5,1,4]]
        rec=reciprocal(cell)
        for i in range(3):
            for j in range(3): self.assertAlmostEqual(dot(cell[i],rec[j]),float(i==j))

    def test_images_preserve_model_and_source_identity(self):
        s=Structure('test',[[2,0,0],[1,3,0],[0,0,4]],['Si','O'],[[1,-1,0],[1.2,-.3,.5]],[['T']*3]*2,['',''])
        before=deepcopy(s); points,ids=periodic_images(s)
        self.assertEqual(s,before)
        self.assertEqual(ids.count(0),8); self.assertEqual(ids.count(1),1)
        self.assertEqual(len(points),9)
