"""Reference parity and optional-backend behavior, with real compiled kernels."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from crystalx import bonds,sphere_material,native_backend
from crystalx import render_material
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from crystalx.structure import Structure,read_poscar
from crystalx.operations import supercell


class BackendTests(unittest.TestCase):
    def test_missing_disabled_and_mismatched_backend(self):
        with patch.dict('os.environ',{'CRYSTALX_DISABLE_NATIVE':'1'}):
            self.assertIsNone(native_backend._load())
        with patch.dict('os.environ',{'CRYSTALX_DISABLE_NATIVE':'0'}):
            with patch.object(native_backend,'import_module',side_effect=ModuleNotFoundError(name='crystalx._native')):
                self.assertIsNone(native_backend._load())
            with patch.object(native_backend,'import_module',side_effect=ImportError('DLL unavailable')):
                with self.assertLogs('crystalx.native_backend',level='WARNING'):
                    self.assertIsNone(native_backend._load())
            with patch.object(native_backend,'import_module',return_value=SimpleNamespace(API_VERSION=0)):
                with self.assertLogs('crystalx.native_backend',level='WARNING'):
                    self.assertIsNone(native_backend._load())

    def test_python_fallback_routes(self):
        s=read_poscar(Path(__file__).resolve().parents[1]/'examples/Si.vasp')
        with patch.object(bonds,'kernels',None):
            self.assertEqual(bonds.automatic_bonds(s),bonds.python_automatic_bonds(s))
        with patch.object(sphere_material,'kernels',None):
            self.assertEqual(sphere_material.sphere_image.__wrapped__((.2,.3,.8)),
                             sphere_material.python_sphere_image((.2,.3,.8)))


@unittest.skipIf(native_backend.kernels is None,'Optional C++ module not built or disabled')
class NativeParityTests(unittest.TestCase):
    def compare_bonds(self,s,ranges=None):
        original=deepcopy(s); python_matched={('existing',0,1)}; native_matched=set(python_matched)
        a=bonds.python_automatic_bonds(s,ranges,matched_ranges=python_matched)
        b=bonds.automatic_bonds(s,ranges,matched_ranges=native_matched)
        self.assertEqual(s,original); self.assertEqual(python_matched,native_matched)
        self.assertEqual(len(a),len(b))
        for x,y in zip(a,b):
            self.assertEqual(x[2:],y[2:])
            for u,v in zip(x[:2],y[:2]):
                for p,q in zip(u,v): self.assertAlmostEqual(p,q,places=11)

    def test_periodic_oblique_short_and_multirange_order(self):
        def structure(lattice,elements,positions):
            return Structure('parity',lattice,elements,positions,[['T']*3 for _ in positions],['']*len(positions))
        self.compare_bonds(structure([[10,0,0],[0,10,0],[0,0,10]],['H','H'],[[.97,.5,.5],[.03,.5,.5]]),{'H-H':[[0,.5],[.5,.7],[.5,.8]]})
        self.compare_bonds(structure([[.7,0,0],[0,.7,0],[0,0,.7]],['H'],[[.5,.5,.5]]),{'H-H':[[0,.75]]})
        self.compare_bonds(structure([[3,0,0],[2.8,.6,0],[.2,.1,4]],['H'],[[.5,.5,.5]]),{'H-H':[[0,.75]]})
        self.compare_bonds(structure([[10,0,0],[0,10,0],[0,0,10]],['Si','O'],[[.5,.5,.5],[.5,.5,.5]]))
        self.compare_bonds(structure([[10,0,0],[0,10,0],[0,0,10]],['H','H'],[[.5,.5,.5],[.56,.5,.5]]))
        s=read_poscar(Path(__file__).resolve().parents[1]/'examples/Si.vasp')
        supercell(s,[4,4,4]); self.compare_bonds(s)

    def test_random_cells_rules_and_outside_positions(self):
        rng=Random(20261116)
        for _ in range(20):
            n=12
            s=Structure('random',[[5,0,0],[rng.uniform(-2,2),5,0],[.3,-.4,6]],
                [rng.choice(['Si','O','H']) for _ in range(n)],
                [[rng.uniform(-1,2) for _ in range(3)] for _ in range(n)],[['T']*3 for _ in range(n)],['']*n)
            self.compare_bonds(s)
            self.compare_bonds(s,{'H-O':[[0,1.2],[1.2,2.1]],'Si-Si':[[0,2.6]]})
            self.compare_bonds(s,{})

    def test_threshold_tolerance_and_boundary_coordinates(self):
        for gap in (-2e-12,0.,2e-12):
            s=Structure('threshold',[[10,0,0],[0,10,0],[0,0,10]],['H','O'],
                [[0,0,0],[(1.2+gap)/10,0,0]],[['T']*3]*2,['',''])
            self.compare_bonds(s,{'H-O':[[0,1.2],[1.2,2.1]]})
        # Noncanonical or malformed pair keys have never matched pair_key().
        self.compare_bonds(s,{'O-H':[[0,2]],'H':[[0,2]]})
        s.positions=[[-1e-20,1+1e-10,0],[.12,-1e-20,0]]
        self.compare_bonds(s,{'H-O':[[0,1.2],[1.2,2.1]]})

    def test_cylinder_gradient_matches_reference_at_varied_orientations(self):
        rng=Random(73)
        for _ in range(20):
            start=QPointF(rng.random(),rng.random()); end=QPointF(rng.random()*100,rng.random()*100)
            args=(start,end,QColor('#637b6b'),3.,rng.random(),1+2*rng.random(),rng.random())
            a=render_material.material_brush(*args)
            with patch.object(render_material,'kernels',None): b=render_material.material_brush(*args)
            self.assertEqual(len(a.stops()),33)
            for (ta,ca),(tb,cb) in zip(a.stops(),b.stops()):
                self.assertEqual(ta,tb)
                for x,y in zip(ca.getRgbF(),cb.getRgbF()): self.assertAlmostEqual(x,y,delta=1/65535)

    def test_pixels_multicolor_random_parameters_and_alpha(self):
        rng=Random(20261116)
        cases=[(rgb,r,i,g) for rgb in ((0.,0.,0.),(1.,1.,1.),(.2,.4,.8))
               for r in (0.,.35,1.) for i in (1.,1.5,3.) for g in (0.,.35,1.)]
        cases.extend((tuple(rng.random() for _ in range(3)),rng.random(),1+2*rng.random(),rng.random()) for _ in range(12))
        for rgb,r,i,g in cases:
            a=sphere_material.python_sphere_image(rgb,r,i,g)
            b=sphere_material.sphere_image.__wrapped__(rgb,r,i,g)
            ba=a.constBits().asstring(a.sizeInBytes()); bb=b.constBits().asstring(b.sizeInBytes())
            self.assertLessEqual(max(abs(x-y) for x,y in zip(ba,bb)),1)
            self.assertEqual(ba[3::4],bb[3::4])

    def test_native_input_boundaries_and_concurrent_material_calls(self):
        k=native_backend.kernels
        with self.assertRaises(ValueError): k.sphere_pixels(1,0,0,float('nan'),1.5,1)
        with self.assertRaises(ValueError): k.bond_candidates([],[],[],[],[1,1,1],1)
        with self.assertRaises(ValueError): k.bond_candidates([[1,0,0],[0,1,0],[0,0,1]],[[0,0,0]],[],[],[1,1,1],1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda _:k.sphere_pixels(.2,.4,.8,.3,1.5,.7),range(12)))
        self.assertTrue(all(value==values[0] for value in values))


if __name__=='__main__': unittest.main()
