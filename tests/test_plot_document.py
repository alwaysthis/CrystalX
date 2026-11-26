import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from crystalx.plot_document import read_document,state_from_json,state_to_json
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class PlotDocumentTests(unittest.TestCase):
    def state(self):
        style=default_style()
        curve=PlotCurve([1,2],[3,4],style['curve'],r'$I_1$',metadata={'DATA_KIND':'XY'},fill_baseline=[1,1])
        return dict(style=style,curves=[curve],bounds=(0,3,0,5),legend_anchor=(.3,.7),selected_curve=0,curve_visible=True,template_name='global')

    def test_lossless_curve_state(self):
        original=self.state(); restored=state_from_json(state_to_json(original))
        for key in original:
            self.assertEqual(original[key],restored[key])

    def test_invalid_state_rejected(self):
        valid=state_to_json(self.state())
        for patch in ({'bounds':[0,1,2,1]},{'bounds':[0,1,float('inf'),4]},{'curve_visible':'false'},
                      {'legend_anchor':[0,float('nan')]},{'curves':valid['curves']*2}):
            with self.subTest(patch=patch),self.assertRaises(ValueError): state_from_json(valid|patch)

    def test_document_and_metadata_validation(self):
        valid=dict(format='CrystalX.PlotDocument',version=1,name='Saved plot',active=0,
            scans=[dict(scan=dict(x=[1,2],intensity=[3,4],metadata={'DATA_KIND':'XY'}),plot=state_to_json(self.state()))])
        with TemporaryDirectory() as directory:
            path=Path(directory)/'plot.cxplot'; path.write_text(json.dumps(valid),encoding='utf-8')
            scans,states,active,name=read_document(path)
            self.assertEqual((name,active,scans[0].data_kind),('Saved plot',0,'XY'))
            for key,value in [('metadata',[]),('x',[float('nan'),2]),('attenuation',[1])]:
                invalid=deepcopy(valid); invalid['scans'][0]['scan'][key]=value; path.write_text(json.dumps(invalid),encoding='utf-8')
                with self.subTest(key=key),self.assertRaises(ValueError): read_document(path)

    def test_empty_plot_supported(self):
        state=self.state(); state.update(curves=[],selected_curve=None)
        self.assertEqual(state_from_json(state_to_json(state))['curves'],[])
