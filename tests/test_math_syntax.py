import unittest
from matplotlib.mathtext import MathTextParser
from crystalx.math_syntax import contains_math,figure_text
from crystalx.plot_curves import PlotCurve
from crystalx.plot_style import default_style

class DollarMathTests(unittest.TestCase):
    def test_no_implicit_math_commands_or_subscripts(self):
        for text in (r'\alpha','I_{001}','x^2',r'\notacommand{','price $5',r'\$5'):
            self.assertFalse(contains_math(text),text)
            self.assertEqual(figure_text(text),text)
        # Plain command-looking text is legal curve content without dollar markers.
        curve=PlotCurve([1,2],[3,4],default_style()['curve'],r'\notacommand{')
        self.assertEqual(PlotCurve.from_clipboard(curve.clipboard(default_style()['general'])).label,curve.label)

    def test_mixed_text_and_display_math(self):
        for text in (r'$\alpha$',r'强度 $I_{001}$ 和 $x^2$',r'$$\frac{1}{2}$$'):
            self.assertTrue(contains_math(text),text)
            MathTextParser('path').parse(figure_text(text))
        self.assertEqual(figure_text('$$x^2$$'),'$x^2$')
