import unittest
from copy import deepcopy
from crystalx.structure import Structure
from crystalx.lattice_edit import set_parameters,transform_basis,parameters
from crystalx.document import StructureDocument,SnapshotCommand

class LatticeEditTests(unittest.TestCase):
    def setUp(self): self.s=Structure('cell',[[3,0,0],[1,4,0],[.2,.5,5]],['Si'],[[.2,.3,.4]],[['T']*3],[''])
    def test_constants_preserve_fractions_and_undo(self):
        before=deepcopy(self.s); doc=StructureDocument(self.s)
        values=[4,5,6,80,85,75]; doc.execute(SnapshotCommand(self.s,set_parameters,values))
        self.assertEqual(self.s.positions,before.positions)
        for a,b in zip(parameters(self.s.lattice),values): self.assertAlmostEqual(a,b)
        doc.undo(); self.assertEqual(self.s,before)
    def test_basis_vesta_column_convention_preserves_cartesian(self):
        before=self.s.cartesian_positions
        doc=StructureDocument(self.s); original=deepcopy(self.s)
        doc.execute(SnapshotCommand(self.s,transform_basis,[[1,1,0],[0,1,0],[0,0,2]]))
        self.assertEqual(self.s.lattice[1],[4,4,0])
        for a,b in zip(self.s.cartesian_positions[0],before[0]): self.assertAlmostEqual(a,b)
        doc.undo(); self.assertEqual(self.s,original)
    def test_singular_and_invalid_cell_are_atomic(self):
        before=deepcopy(self.s)
        with self.assertRaises(ValueError): SnapshotCommand(self.s,transform_basis,[[0]*3 for _ in range(3)])
        with self.assertRaises(ValueError): SnapshotCommand(self.s,set_parameters,[1,1,1,10,10,170])
        self.assertEqual(self.s,before)

    def test_fractional_basis_is_rejected_without_mutation(self):
        before=deepcopy(self.s)
        with self.assertRaisesRegex(ValueError,'整数'):
            SnapshotCommand(self.s,transform_basis,[[1,.5,0],[0,1,0],[0,0,1]])
        self.assertEqual(self.s,before)
    def test_combined_metric_then_matrix_coordinate_invariants(self):
        fractions=deepcopy(self.s.positions)
        set_parameters(self.s,[4,5,6,80,85,75])
        self.assertEqual(self.s.positions,fractions)
        points=self.s.cartesian_positions
        transform_basis(self.s,[[1,1,0],[0,1,0],[0,0,2]])
        for p,q in zip(points,self.s.cartesian_positions):
            for a,b in zip(p,q): self.assertAlmostEqual(a,b)
