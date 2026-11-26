import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from crystalx.xrd_io import read_ras,read_xrd

RAS='''*RAS_DATA_START
*RAS_HEADER_START
*MEAS_SCAN_AXIS_X_INTERNAL "TwoTheta"
*MEAS_SCAN_UNIT_X "deg"
*MEAS_SCAN_UNIT_Y "cps"
*MEAS_DATA_COUNT "3"
*RAS_HEADER_END
*RAS_INT_START
10 100 1
10.02 250 2
10.04 75 1
*RAS_INT_END
*RAS_DATA_END
'''

class XrdTests(unittest.TestCase):
    def test_ras_columns_metadata_and_multiscan(self):
        a,b=read_ras(RAS+RAS.replace('TwoTheta','Omega'))
        self.assertEqual(a.x,[10,10.02,10.04]); self.assertEqual(a.intensity,[100,250,75])
        self.assertEqual(a.attenuation,[1,2,1]); self.assertEqual(a.axis_label,'2θ (°)')
        self.assertEqual(b.axis_label,'ω (°)')
        coupled=read_ras(RAS.replace('TwoTheta','TwoThetaOmega'))[0]
        self.assertEqual(coupled.axis_label,'2θ (°)')
        self.assertEqual(coupled.metadata['MEAS_SCAN_AXIS_X_INTERNAL'],'TwoThetaOmega')
    def test_reject_corrupt_or_nonfinite_ras(self):
        for text in (RAS.replace('*RAS_INT_END',''),RAS.replace('"3"','"4"'),RAS.replace('250','nan'),'not ras'):
            with self.assertRaises(ValueError): read_ras(text)
    def test_text_encoding_and_formats(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/'scan.ras'; p.write_bytes(RAS.replace('*RAS_HEADER_END','*FILE_COMMENT "試料"\n*RAS_HEADER_END').encode('cp932'))
            self.assertEqual(read_xrd(p)[0].metadata['FILE_COMMENT'],'試料')
            p=Path(directory)/'scan.csv'; p.write_text('angle,intensity\n10,100\n11,250\n',encoding='utf-8-sig')
            self.assertEqual(read_xrd(p)[0].intensity,[100,250])
            p.write_text('10 inf\n11 2')
            with self.assertRaises(ValueError): read_xrd(p)
