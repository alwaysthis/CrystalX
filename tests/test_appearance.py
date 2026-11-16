import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from copy import deepcopy
from crystalx.appearance import FACTORY_STYLE,AppearanceStore,read_preset,write_preset,validate_settings
from crystalx.render_material import radius
from crystalx.sphere_material import sphere_image

class AppearanceTests(unittest.TestCase):
    def test_default_roundtrip_is_user_owned(self):
        original=deepcopy(FACTORY_STYLE)
        with TemporaryDirectory() as folder:
            path=Path(folder)/'custom/display.json'; store=AppearanceStore(path)
            settings=deepcopy(store.current); settings.update(cell_line=5,cell_roughness=.7,atom_radius_type=3,atom_radius=.8,bond_line=5)
            store.set_default(settings)
            self.assertEqual(AppearanceStore(path).defaults,settings)
            export=Path(folder)/'style.json'; write_preset(export,settings); self.assertEqual(read_preset(export),settings)
        self.assertEqual(FACTORY_STYLE,original)
    def test_bad_presets_rejected(self):
        for settings in [{'cell_line':6},{'axes_colors':['#fff']},{'atom_ior':float('nan')},{'gloss':1.01},{'cell_gloss':-.1},{'atom_ior':.99},{'axes_ior':3.01},{'atom_radius':-1},{'unknown':3}]:
            with self.assertRaises(ValueError): validate_settings(settings)
    def test_radius_definitions_and_custom(self):
        settings=deepcopy(FACTORY_STYLE)
        self.assertAlmostEqual(radius('Si',settings),1.18*.42)
        settings['atom_radius_type']=1; self.assertAlmostEqual(radius('Si',settings),.26*.42)
        settings['atom_radius_type']=2; self.assertAlmostEqual(radius('Si',settings),2.1*.42)
        settings['atom_radius_type']=3; settings['atom_radius']=.8; self.assertAlmostEqual(radius('Si',settings),.8)
    def test_material_controls_change_rendered_pixels(self):
        def pixels(image): return image.constBits().asstring(image.sizeInBytes())
        rgb=(.2,.4,.8); base=pixels(sphere_image(rgb,.3,1.5,True))
        self.assertNotEqual(base,pixels(sphere_image(rgb,.8,1.5,True)))
        self.assertNotEqual(base,pixels(sphere_image(rgb,.3,2.5,True)))
        self.assertNotEqual(base,pixels(sphere_image(rgb,.3,1.5,False)))

    def test_fresnel_and_ggx_follow_material_parameters(self):
        from crystalx.material_math import fresnel,ggx_distribution
        self.assertAlmostEqual(fresnel(1.5,1),.04)
        self.assertEqual(fresnel(1,0),0)
        self.assertGreater(fresnel(2.4,1),fresnel(1.5,1))
        self.assertGreater(fresnel(1.5,.1),fresnel(1.5,1))
        self.assertGreater(ggx_distribution(1,.1),ggx_distribution(1,.8))
        self.assertGreater(ggx_distribution(.7,.8),ggx_distribution(.7,.1))
    def test_matte_is_independent_of_ior(self):
        a=sphere_image((.2,.4,.8),.3,1.05,False)
        b=sphere_image((.2,.4,.8),.3,2.4,False)
        self.assertEqual(a,b)
    def test_legacy_custom_radius_is_still_supported(self):
        settings=validate_settings({'atom_radius_type':3,'atom_radius':.65})
        self.assertAlmostEqual(radius('Si',settings),.65)
        self.assertEqual(settings['atom_radius_source'],0)

    def test_continuous_gloss_and_legacy_presets(self):
        from crystalx.material_math import shade_terms
        for key in ('gloss','cell_gloss','axes_gloss'):
            self.assertEqual(validate_settings({key:True})[key],1.)
            self.assertEqual(validate_settings({key:False})[key],0.)
            self.assertEqual(validate_settings({key:.35})[key],.35)
        levels=[shade_terms(.8,.8,.95,.4,1.5,g)[1] for g in (0.,.25,.75,1.)]
        self.assertEqual(levels[0],0.)
        self.assertTrue(all(a<b for a,b in zip(levels,levels[1:])))
        images=[sphere_image((.2,.4,.8),.4,1.5,g) for g in (0.,.25,.75,1.)]
        self.assertTrue(all(a!=b for a,b in zip(images,images[1:])))
        self.assertEqual(validate_settings({'atom_ior':1})['atom_ior'],1)
        self.assertEqual(validate_settings({'atom_ior':3})['atom_ior'],3)
