import unittest,tempfile
from pathlib import Path
from crystalx.cif_io import read_cif

CIF="""data_test
_cell_length_a 4
_cell_length_b 4
_cell_length_c 4
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt 'P -1'
loop_
_space_group_symop_operation_xyz
'x,y,z'
'-x,-y,-z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Si1 Si .1 .2 .3 1
"""
class CifTests(unittest.TestCase):
    def test_symmetry(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.cif'; p.write_text(CIF)
            s=read_cif(p); self.assertEqual(len(s.elements),2)
            self.assertAlmostEqual(s.positions[1][0],.9)
            p.write_text(CIF.replace('.3 1','.3 0.5'))
            with self.assertRaises(ValueError): read_cif(p)
