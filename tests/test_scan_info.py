import unittest
from crystalx.afm_io import read_unit_xy
from crystalx.scan_info import afm_statistics,scan_information
from crystalx.plot_style import math_label,default_style
from crystalx.plot_curves import PlotCurve

class ScanInfoTests(unittest.TestCase):
    def test_afm_statistics_are_weighted_by_pixel_counts(self):
        scan=read_unit_xy('X Unit: nm\nY Unit: Pixel\nX Y\n0 1\n2 3\n4 0')
        stats=afm_statistics(scan)
        self.assertEqual(stats['mean'],1.5); self.assertEqual(stats['variance'],.75)
        self.assertEqual(stats['mode'],2); self.assertEqual(stats['pixels'],4)
        self.assertEqual(stats['minimum'],0); self.assertEqual(stats['maximum'],2)
        self.assertEqual(stats['median'],2); self.assertEqual(stats['ra'],.75)

    def test_zero_frequency_has_clear_statistics_message(self):
        scan=read_unit_xy('X Unit: nm\nY Unit: Pixel\nX Y\n0 0\n2 0')
        with self.assertRaises(ValueError): afm_statistics(scan)
        self.assertTrue(any('像素总数为0' in text for _,text in scan_information(scan)))

    def test_math_annotation_clipboard_preserves_source(self):
        self.assertEqual(math_label('I_{001}'),'I_{001}')
        self.assertEqual(math_label('x^2'),'x^2'); self.assertEqual(math_label('plot 1'),'plot 1')
        self.assertEqual(math_label('$I_{001}$'),'$I_{001}$'); self.assertEqual(math_label('$$x^2$$'),'$x^2$')
        style=default_style(); curve=PlotCurve([0,1],[2,3],style['curve'],'I_{001}',points=[1],point_labels={1:r'\alpha_{1}'})
        copied=PlotCurve.from_clipboard(curve.clipboard(style['general']))
        self.assertEqual(copied.point_labels,{1:r'\alpha_{1}'})
