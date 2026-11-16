import unittest
import math
from crystalx.view_orientation import standard_orientation
from crystalx.structure import dot,cross

class OrientationTests(unittest.TestCase):
    def test_standard_axis_directions(self):
        camera=standard_orientation([[1,0,0],[0,1,0],[0,0,1]])
        a,b,c=[tuple(dot(row,axis) for row in camera) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
        self.assertLess(a[0],0); self.assertLess(a[1],0); self.assertGreater(a[2],0)
        self.assertGreater(b[0],0); self.assertAlmostEqual(c[0],0); self.assertGreater(c[1],0)
        self.assertAlmostEqual(a[0],-1/math.sqrt(10))
        self.assertAlmostEqual(c[2],1/math.sqrt(37))
    def test_oblique_and_rotated_lattices_keep_geometry(self):
        lattice=[[4,0,0],[1,3,0],[2,1,5]]
        camera=standard_orientation(lattice)
        for i in range(3):
            for j in range(3): self.assertAlmostEqual(dot(camera[i],camera[j]),int(i==j))
        self.assertAlmostEqual(dot(camera[0],cross(camera[1],camera[2])),1)
        rotate=lambda v:[-v[1],v[0],v[2]]
        rotated=standard_orientation(list(map(rotate,lattice)))
        for vector in lattice:
            for a,b in zip(camera,rotated): self.assertAlmostEqual(dot(a,vector),dot(b,rotate(vector)))
