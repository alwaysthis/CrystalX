from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from crystalx.plot_curves import PlotCurve
from crystalx.plot_presets import PlotDefaults,PlotTemplates,read_plot_config,write_plot_config
from crystalx.plot_style import default_style,tick_mode,validate_style

class CurveDataTests(unittest.TestCase):
    def test_templates_follow_content_and_user_override(self):
        from crystalx.xrd_io import XrdScan
        samples=[(XrdScan([10,110],[1,2],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'}),'XRD'),
                 (XrdScan([.1,6],[100,1],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'}),'XRR'),
                 (XrdScan([20,21],[1,2],{'MEAS_SCAN_AXIS_X_INTERNAL':'Omega'}),'Rocking Curve'),
                 (XrdScan([1,2],[3,4]),'global')]
        for scan,name in samples:
            self.assertEqual(scan.template_name,name)
            # Built-in expectations must not depend on the user's saved overrides.
            path=PlotTemplates().root/'default/plot-templates'/f'{name}.json'
            style,curves=read_plot_config(path)
            self.assertEqual(style['axes']['left']['log'],name=='XRR')
        with TemporaryDirectory() as folder:
            style=default_style(); style['general']['size']=17; style['axes']['left']['label']='document only'
            write_plot_config(Path(folder)/'custom/plot-templates/XRD.json',style)
            restored=PlotTemplates(folder).resolve(samples[0][0])[0]
            self.assertEqual(restored['general']['size'],17); self.assertEqual(restored['axes']['left']['label'],'document only')

    def test_copy_retains_inheritance_and_adopts_target_appearance(self):
        style=default_style(); style['general'].update(color='#ff0000',width=3)
        curve=PlotCurve([1,2],[3,4],deepcopy(style['curve']),'named curve',points=[1])
        copied=PlotCurve.from_clipboard(curve.clipboard(style['general']))
        self.assertEqual(copied.label,'named curve'); self.assertEqual(copied.points,[1])
        self.assertEqual(copied.style['color'],''); self.assertEqual(copied.style['width'],0)
        copied.style.update(color='#ff0000',width=3,face='#ff0000'); copied.inherit_plot_appearance()
        self.assertEqual(copied.style['color'],''); self.assertEqual(copied.style['width'],0); self.assertEqual(copied.style['face'],'auto')
        copied.x[0]=999; self.assertEqual(curve.x,[1,2]); self.assertEqual(curve.style['color'],'')
    def test_clipboard_validation(self):
        style=default_style(); valid=json.loads(PlotCurve([1,2],[3,4],style['curve'],'plot 1').clipboard(style['general']))
        for patch in ({'x':[1]},{'x':[float('inf'),2]},{'points':[8]},{'label':3},{'visible':'yes'},{'style':{'bad':'x'}}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                PlotCurve.from_clipboard(json.dumps(valid|patch).encode())
    def test_array_has_priority_over_interval(self):
        style=default_style(); axis=style['axes']['bottom']; axis.update(ticks='[0:10:100]',interval=5)
        self.assertEqual(tick_mode(axis),'array'); validate_style(style)
        axis['ticks']=''; self.assertEqual(tick_mode(axis),'spacing')
        axis['interval']=0; self.assertEqual(tick_mode(axis),'auto')
    def test_configuration_and_global_defaults_are_data_free(self):
        style=default_style(); self.assertTrue(style['legend']['visible']); self.assertFalse(style['legend']['frame'])
        settings=PlotCurve([1,2],[3,4],style['curve'],'plot 1').settings()
        with TemporaryDirectory() as directory:
            store=PlotDefaults(Path(directory)/'custom/plot.json'); store.save(style,[settings])
            restored,curves=PlotDefaults(store.path).read()
            self.assertEqual(restored,style); self.assertEqual(curves,[settings])
            document=json.loads(store.path.read_text()); self.assertNotIn('x',document['curves'][0])
            bad=Path(directory)/'bad.json'; bad.write_text('{"format":"bad"}')
            with self.assertRaises(ValueError): read_plot_config(bad)
