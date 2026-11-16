import unittest
from copy import deepcopy
from crystalx.bonds import automatic_bonds,DEFAULT_RANGES
from crystalx.structure import Structure, read_poscar, fractional
from pathlib import Path

class BondTests(unittest.TestCase):
    def structure(self,lattice,elements,points):
        return Structure('test',lattice,elements,points,[[True]*3 for _ in points],['']*len(points))
    def test_periodic_crossing_and_no_mutation(self):
        s=self.structure([[10,0,0],[0,10,0],[0,0,10]],['H','H'],[[.97,.5,.5],[.03,.5,.5]])
        original=deepcopy(s); bonds=automatic_bonds(s,{'H-H':[[0,.75]]})
        self.assertEqual(len(bonds),2)
        self.assertEqual(s,original)
        for a,b,i,j in bonds:
            self.assertAlmostEqual(sum((x-y)**2 for x,y in zip(a,b))**.5,.3)
            self.assertNotEqual(i,j)
    def test_self_images_of_short_cell(self):
        s=self.structure([[.7,0,0],[0,.7,0],[0,0,.7]],['H'],[[.5,.5,.5]])
        self.assertEqual(len(automatic_bonds(s,{'H-H':[[0,.75]]})),6)
    def test_silicon_and_threshold(self):
        s=read_poscar(Path(__file__).resolve().parents[1]/'examples/Si.vasp')
        self.assertGreater(len(automatic_bonds(s)),0)
        self.assertEqual(automatic_bonds(s,{'Si-Si':[[0,2.]]}),[])
        self.assertEqual(automatic_bonds(s,{'Si-Si':[[3,3.2]]}),[])
    def test_oblique_cell_clip_and_deduplication(self):
        s=self.structure([[3,0,0],[2.8,.6,0],[.2,.1,4]],['H'],[[.5,.5,.5]])
        bonds=automatic_bonds(s,{'H-H':[[0,.75]]}); self.assertGreater(len(bonds),0)
        tokens=set()
        for a,b,_,_ in bonds:
            f=[fractional(p,s.lattice) for p in (a,b)]
            self.assertTrue(all(-1e-8<=v<=1+1e-8 for point in f for v in point))
            token=tuple(sorted(tuple(round(v,8) for v in point) for point in f))
            self.assertNotIn(token,tokens); tokens.add(token)

    def test_vesta_default_pair_ranges(self):
        self.assertEqual(DEFAULT_RANGES['Si-Si'],[[0.,2.6]])
        self.assertEqual(DEFAULT_RANGES['O-Si'],[[0.,1.99002]])
        self.assertEqual(DEFAULT_RANGES['Cl-Na'],[[0.,3.39412]])
        self.assertEqual(DEFAULT_RANGES['H-O'],[[0.,1.2],[1.2,2.1]])
        # VESTA does not list H-H: no radius-based fallback.
        s=self.structure([[10,0,0],[0,10,0],[0,0,10]],['H','H'],[[.5,.5,.5],[.56,.5,.5]])
        self.assertEqual(automatic_bonds(s),[])
        s.elements=['Si','O']; s.positions=[[.5,.5,.5],[.69,.5,.5]]
        self.assertEqual(len(automatic_bonds(s)),1)
        s.positions[1][0]=.71
        self.assertEqual(automatic_bonds(s),[])
    def test_distinct_windows_and_zero_distance(self):
        s=self.structure([[10,0,0],[0,10,0],[0,0,10]],['H','O'],[[.5,.5,.5],[.65,.5,.5]])
        self.assertEqual(automatic_bonds(s,{'H-O':[[0,1],[2,3]]}),[])
        s.positions[1]=s.positions[0][:]
        self.assertEqual(automatic_bonds(s,{'H-O':[[0,1]]}),[])

    def test_matched_ranges_use_full_periodic_distance_before_clipping(self):
        s=self.structure([[10,0,0],[0,10,0],[0,0,10]],['H','H'],[[.97,.5,.5],[.03,.5,.5]])
        matched=set()
        bonds=automatic_bonds(s,{'H-H':[[0,.5],[.5,.7],[.5,.8]]},matched_ranges=matched)
        self.assertEqual(len(bonds),2)
        self.assertEqual(matched,{('H-H',.5,.7),('H-H',.5,.8)})
