import unittest
from crystalx.sphere_material import sphere_image,fogged_sphere

class SphereMaterialTests(unittest.TestCase):
    def test_fog_never_rebuilds_lighting_material_and_preserves_alpha(self):
        sphere_image.cache_clear(); fogged_sphere.cache_clear()
        rgb=(.15,.3,.8)
        base=sphere_image(rgb)
        for bucket in range(16):
            image=fogged_sphere(rgb,bucket)
            self.assertEqual(image.pixelColor(0,0).alpha(),0)
            self.assertEqual(image.pixelColor(64,64).alpha(),255)
        self.assertEqual(sphere_image.cache_info().misses,1)
        self.assertGreater(fogged_sphere(rgb,15).pixelColor(64,64).red(),base.pixelColor(64,64).red())
