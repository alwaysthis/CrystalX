import unittest
import math
from copy import deepcopy
from crystalx.curve_data import XYScan
from crystalx.plot_units import prepare_scan,prepare_curve,prepare_state
from crystalx.plot_style import default_style

class PlotUnitTests(unittest.TestCase):
    def test_rasx_structured_scan_information(self):
        import zipfile
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from crystalx.xrd_io import read_xrd
        xml='''<MeasurementConditions><ScanInformation><AxisName>TwoThetaOmega</AxisName><Mode>CONTINUOUS</Mode><Start>10</Start><Stop>20</Stop><Step>0.01</Step><Speed>5</Speed><SpeedUnit>deg/min</SpeedUnit><PositionUnit>deg</PositionUnit><IntensityUnit>counts</IntensityUnit><DataCount>2</DataCount></ScanInformation></MeasurementConditions>'''
        with TemporaryDirectory() as folder:
            path=Path(folder)/'test.rasx'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('Data0/MesurementConditions0.xml',xml)
                archive.writestr('Data0/Profile0.txt','10 6 1\n20 12 1\n')
            scan=read_xrd(path)[0]; prepared=prepare_scan(scan)
            self.assertEqual(scan.intensity,[6,12]); self.assertEqual(prepared.intensity,[50,100])

    def scan(self,axis='Omega'):
        return XYScan([1,2,3],[6,12,3],dict(MEAS_SCAN_AXIS_X_INTERNAL=axis,MEAS_SCAN_UNIT_X='deg',MEAS_SCAN_UNIT_Y='counts',MEAS_SCAN_STEP='.001',MEAS_SCAN_SPEED='1',MEAS_SCAN_SPEED_UNIT='deg/min',HW_XG_WAVE_LENGTH_ALPHA1='1.540593',HW_XG_WAVE_LENGTH_UNIT='angstrom'))

    def test_rate_and_no_double_conversion(self):
        raw=self.scan(); before=deepcopy(raw); prepared=prepare_scan(raw)
        self.assertEqual(prepared.intensity,[100,200,50]); self.assertEqual(raw,before)
        self.assertEqual(prepare_scan(prepared),prepared)
        raw.metadata.update(MEAS_SCAN_STEP='.01',MEAS_SCAN_SPEED='5',EXPERIMENT_TYPE='XRD')
        self.assertEqual(prepare_scan(raw).intensity,[50,100,25])

    def test_unknown_time_retains_units_and_data(self):
        raw=self.scan(); del raw.metadata['MEAS_SCAN_SPEED']
        prepared=prepare_scan(raw)
        self.assertEqual(prepared.intensity,raw.intensity); self.assertEqual(prepared.metadata['MEAS_SCAN_UNIT_Y'],'counts')
        self.assertIn('CRYSTALX_UNIT_NOTE',prepared.metadata)

    def test_qz_and_wavelength_units(self):
        raw=self.scan('TwoThetaOmega'); prepared=prepare_scan(raw)
        self.assertAlmostEqual(prepared.x[1],4*math.pi*math.sin(math.radians(1))/1.540593)
        self.assertEqual(prepared.intensity,raw.intensity); self.assertEqual(prepared.metadata['MEAS_SCAN_UNIT_X'],'1/angstrom')
        self.assertEqual(prepare_scan(prepared),prepared)
        raw.metadata.update(HW_XG_WAVE_LENGTH_ALPHA1='.1540593',HW_XG_WAVE_LENGTH_UNIT='nm')
        self.assertAlmostEqual(prepare_scan(raw).x[1],prepared.x[1])

    def test_legacy_document_analysis_and_bounds_migrate_once(self):
        raw=self.scan(); style=default_style(); curve=prepare_curve(raw,style['curve'],'test')
        curve.y=list(raw.intensity); curve.metadata=deepcopy(raw.metadata)
        curve.background=[1,2,3]; curve.peak_analysis={'positions':[dict(index=1,x=2.,y=12.)]}
        state=dict(curves=[curve],bounds=(0,4,0,12),style=style)
        prepare_state(raw,state)
        self.assertEqual(curve.y,[100,200,50]); self.assertEqual(curve.background,[1/.06,2/.06,3/.06])
        self.assertEqual(curve.peak_analysis['positions'][0]['y'],200)
        self.assertEqual(state['bounds'],(0,4,0,200))
        before=deepcopy(state); prepare_state(raw,state); self.assertEqual(state,before)
