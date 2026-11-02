import unittest
from copy import deepcopy
from pathlib import Path
from crystalx.structure import read_poscar, cartesian, fractional
from crystalx.document import StructureDocument, SnapshotCommand
from crystalx import operations as op

class OperationTests(unittest.TestCase):
    def setUp(self):
        self.s=read_poscar(Path(__file__).resolve().parents[1]/'examples/Si.vasp')

    def test_skew_rotation_preserves_distance(self):
        self.s.lattice=[[3,0,0],[1,4,0],[.5,1,5]]
        self.s.positions[0]=fractional([1,0,0],self.s.lattice)
        op.rotate(self.s,{0},[0,0,1],90,[0,0,0])
        point=self.s.cartesian_positions[0]
        for a,b in zip(point,[0,1,0]): self.assertAlmostEqual(a,b)
        op.rotate(self.s,{0},[0,0,1],-90,[0,0,0])
        for a,b in zip(self.s.cartesian_positions[0],[1,0,0]): self.assertAlmostEqual(a,b)

    def test_supercell_metadata_and_exact_undo(self):
        self.s.flags[0]=['F','T','F']; self.s.tags[0]='anchor'
        before=deepcopy(self.s); doc=StructureDocument(self.s)
        doc.execute(SnapshotCommand(self.s,op.supercell,[2,1,3]))
        self.assertEqual(len(self.s.elements),48)
        self.assertEqual(self.s.tags.count('anchor'),6)
        self.assertEqual(self.s.flags[0],['F','T','F'])
        self.assertEqual(self.s.lattice[0],[10.86,0,0])
        self.assertEqual(self.s.lattice[2],[0,0,16.29])
        doc.undo(); self.assertEqual(self.s,before)
        doc.redo(); self.assertEqual(len(self.s.elements),48)

    def test_copy_delete_wrap_flags_and_undo(self):
        before=deepcopy(self.s); doc=StructureDocument(self.s)
        for operation,args in [(op.duplicate,({0},[1.2,-.3,0])),(op.wrap,({8},)),(op.set_flags,({8},['F']*3)),(op.delete,({0},))]:
            doc.execute(SnapshotCommand(self.s,operation,*args))
        self.assertEqual(len(self.s.elements),8)
        self.assertTrue(self.s.selective)
        self.assertAlmostEqual(self.s.positions[-1][0],.2)
        for _ in range(4): doc.undo()
        self.assertEqual(self.s,before)

    def test_failed_operation_is_atomic(self):
        before=deepcopy(self.s)
        with self.assertRaises(ValueError): SnapshotCommand(self.s,op.delete,set(range(8)))
        with self.assertRaises(ValueError): SnapshotCommand(self.s,op.rotate,{0},[0,0,0],90,[0,0,0])
        self.assertEqual(self.s,before)
