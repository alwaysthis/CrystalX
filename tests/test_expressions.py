import unittest
import numpy as np
from crystalx.expressions import expression_curves

class ExpressionTests(unittest.TestCase):
    def test_mathematica_domain_and_arbitrary_variable(self):
        x,y=expression_curves('Sin[t]^2, {t,-Pi,Pi}','0,1',(-5,5,-2,2))[0]
        self.assertAlmostEqual(x[0],-np.pi)
        np.testing.assert_allclose(y,np.sin(x)**2)
        x,y=expression_curves('u^2','-2,2',(-5,5,-2,2))[0]
        self.assertEqual((y[0],y[-1]),(4,4))

    def test_equations_and_constant(self):
        x,y=expression_curves('x=1','-2,2',(-2,2,-3,3))[0]
        np.testing.assert_allclose(x,1); self.assertAlmostEqual(min(y),-3)
        x,y=expression_curves('x^2+y^2=1','-2,2',(-2,2,-2,2))[0]
        np.testing.assert_allclose(np.array(x)**2+np.array(y)**2,1,atol=.0002)
        x,y=expression_curves('3','-2,2',(-2,2,-2,5))[0]
        self.assertTrue(all(value==3 for value in y))

    def test_no_code_execution_or_invalid_domains(self):
        for expression,domain in [('__import__("os")','0,1'),('x.real','0,1'),('x','1,0'),('x+z','0,1'),('x^1000','0,1')]:
            with self.subTest(expression=expression),self.assertRaises(ValueError):
                expression_curves(expression,domain,(-2,2,-2,2))
