import tempfile
import unittest
from pathlib import Path
from crystalx.structure import read_poscar, write_poscar, fractional, cartesian
from crystalx.document import StructureDocument, TranslateCommand

class StructureTests(unittest.TestCase):
    def test_skew_cartesian_roundtrip_flags_and_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'POSCAR'
            source.write_text('test\n2\n2 0 0\n1 3 0\n0 1 4\nSi O\n1 1\nSelective dynamics\nCartesian\n1 2 3 F T F atom one\n0 0 0 T T T oxygen\n')
            structure=read_poscar(source)
            self.assertEqual(structure.cartesian_positions[0],[2.,4.,6.])
            for direct in (True,False):
                target=Path(folder)/'out'; write_poscar(structure,target,direct)
                restored=read_poscar(target)
                self.assertEqual(restored.flags,structure.flags)
                self.assertEqual(restored.tags,structure.tags)
                for a,b in zip(restored.positions[0],structure.positions[0]): self.assertAlmostEqual(a,b)

    def test_negative_volume_and_reject_trailing(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'POSCAR'
            text='test\n-8\n1 0 0\n0 1 0\n0 0 1\nSi\n1\nDirect\n0 0 0\n'
            source.write_text(text); self.assertAlmostEqual(read_poscar(source).lattice[0][0],2)
            source.write_text(text+'velocities\n')
            with self.assertRaises(ValueError): read_poscar(source)

    def test_history_branch_after_save(self):
        s=read_poscar(Path(__file__).resolve().parents[1]/'examples/Si.vasp'); doc=StructureDocument(s)
        doc.execute(TranslateCommand(s,{0},[.1,0,0])); doc.saved_index=doc.index
        doc.undo(); doc.execute(TranslateCommand(s,{0},[.2,0,0]))
        self.assertTrue(doc.dirty); self.assertEqual(len(doc.commands),1)
        doc.undo(); self.assertEqual(s.positions[0],[0,0,0])

if __name__=='__main__': unittest.main()
