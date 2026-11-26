import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from crystalx.afm_io import read_unit_xy,has_unit_header
from crystalx.xrd_io import read_plot_data
from crystalx.plot_style import axis_label
from crystalx.plot_presets import read_plot_config

SAMPLE='X Unit:\tNanoMeter\nY Unit:\tPixel\n\nX\tY\n2\t0\t\n1\t5\t\n0\t8\t\n-1\t2\t\n'

class AfmTests(unittest.TestCase):
    def test_length_profile_shares_afm_template_and_keeps_signed_heights(self):
        from crystalx.scan_info import scan_information
        sample='X Unit: MicroMeter\nY Unit: PicoMeter\nX Y\n0 -3\n1 6\n2 0\n'
        scan=read_unit_xy(sample)
        self.assertEqual(scan.template_name,'AFM'); self.assertEqual(scan.metadata['AFM_TYPE'],'profile')
        self.assertEqual(scan.axis_label,'Distance (µm)'); self.assertEqual(scan.y_label,'Height (pm)')
        self.assertEqual(scan.intensity,[-3,6,0])
        rows=dict(scan_information(scan)); self.assertEqual(rows['平均高度'],'1 pm')
        self.assertEqual(rows['峰谷高度差'],'9 pm'); self.assertNotIn('像素总数',rows)

    def test_height_distribution_preserves_values_and_units(self):
        scan=read_unit_xy(SAMPLE)
        self.assertEqual(scan.x,[2,1,0,-1]); self.assertEqual(scan.intensity,[0,5,8,2])
        self.assertEqual(scan.template_name,'AFM'); self.assertEqual(scan.data_kind,'AFM')
        self.assertEqual(scan.axis_label,'Height (nm)'); self.assertEqual(axis_label(scan,'left'),'Pixel count')
        self.assertEqual(scan.metadata['X_UNIT'],'NanoMeter'); self.assertTrue(has_unit_header(SAMPLE))
        self.assertEqual(read_unit_xy(SAMPLE.replace('NanoMeter','MicroMeter')).axis_label,'Height (µm)')

    def test_generic_unit_text_does_not_gain_diffraction_labels(self):
        scan=read_unit_xy(SAMPLE.replace('NanoMeter','Volt').replace('Pixel','Ampere'))
        self.assertEqual(scan.axis_label,'X (Volt)'); self.assertEqual(scan.y_label,'Y (Ampere)')
        self.assertEqual(scan.template_name,'global'); self.assertEqual(scan.data_kind,'XY')

    def test_dispatch_is_content_based_and_retains_plain_xy(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'arbitrary.txt'; path.write_text(SAMPLE,encoding='utf-8-sig')
            self.assertEqual(read_plot_data(path)[0].template_name,'AFM')
            path.write_text('1 2\n2 3\n')
            self.assertEqual(read_plot_data(path)[0].axis_label,'2θ (°)')
        path=Path(__file__).resolve().parents[1]/'config/default/plot-templates/AFM.json'
        style,_=read_plot_config(path)
        self.assertEqual(style['general']['size'],25); self.assertFalse(style['axes']['bottom']['log'])

    def test_reject_incomplete_or_corrupt_unit_exports(self):
        for text in (SAMPLE.replace('Y Unit:\tPixel\n',''),SAMPLE.replace('2\t0','2\tnan'),
                     SAMPLE.replace('2\t0','2\t0\t5'),SAMPLE.replace('2\t0','2\t-1'),
                     SAMPLE.replace('X\tY','X Unit:\tNanoMeter\nX\tY'),
                     'X Unit: nm\nY Unit: Pixel\nX Y\n1 2'):
            with self.subTest(text=text),self.assertRaises(ValueError): read_unit_xy(text)
