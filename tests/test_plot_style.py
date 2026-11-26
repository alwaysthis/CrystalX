import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from crystalx.matlab_literals import parse_literal
from crystalx.plot_style import default_style,validate_style,inherited,tick_text
from crystalx.session_state import SessionState
from crystalx.scientific_figure import make_figure,IntervalLocator
from crystalx.xrd_io import XrdScan

class LiteralTests(unittest.TestCase):
    def test_arrays_ranges_nested_and_numeric_labels(self):
        self.assertEqual(parse_literal('[0:10:100]'),list(range(0,101,10)))
        self.assertEqual(parse_literal('[1,2,[2,3]]'),[1,2,2,3])
        self.assertEqual(parse_literal('[3:-1:1; 1e2 .5]'),[3,2,1,100,.5])
        self.assertEqual(parse_literal("{'A',2,'it''s',[3,4]}",True),['A','2',"it's",'3','4'])
        self.assertEqual(parse_literal('["a" "b"]',True),['a','b'])
        self.assertEqual(parse_literal('[5:1]'),[])
    def test_reject_bad_or_executable_input(self):
        for text in ('[1:0:3]','[0:.000001:1000]','[1,2','[1:2:3:4]','nan','__import__("os")',"[1,'text']",'[1e999]'):
            with self.subTest(text=text), self.assertRaises(ValueError): parse_literal(text)

class PlotStyleTests(unittest.TestCase):
    def test_defaults_inheritance_and_validation(self):
        style=default_style(); self.assertEqual(style['general']['font'],'Times New Roman')
        self.assertEqual(inherited(style,style['axes']['left'],'color'),'#000000')
        style['general']['color']='#cc0000'; self.assertEqual(inherited(style,style['curve'],'color'),'#cc0000')
        style['axes']['left'].update(log=True,tick_mode='array',ticks='[0 1 10]')
        with self.assertRaises(ValueError): validate_style(style)
        style['axes']['left'].update(ticks='[1 10 100]',labels="{'low',2,'high'}")
        self.assertEqual(validate_style(style),style)
        style['axes']['left']['labels']="{'too','few'}"
        self.assertEqual(validate_style(style),style)  # MATLAB pads missing labels.
    def test_formats_and_log_spacing(self):
        axis=dict(precision=1,number_format='E'); self.assertEqual(tick_text(120,axis),'1.2E2')
        axis['number_format']='e'; self.assertEqual(tick_text(120,axis),'1.2e2')
        axis['number_format']='fixed'; axis['precision']=0; self.assertEqual(tick_text(120,axis),'120')
        self.assertEqual(IntervalLocator(1,True).tick_values(.5,1500),[1,10,100,1000])
    def test_scientific_format_renders_exponent_as_superscript(self):
        from matplotlib.mathtext import MathTextParser
        from matplotlib.font_manager import FontProperties
        axis=dict(precision=1,number_format='scientific')
        text=tick_text(120,axis); self.assertEqual(text,r'$1.2\times10^{2}$')
        self.assertEqual(tick_text(0,axis),'0'); self.assertEqual(tick_text(-.012,axis),r'$-1.2\times10^{-2}$')
        parsed=MathTextParser('path').parse(text,prop=FontProperties(size=20))
        self.assertFalse(any(glyph[2]==ord('^') for glyph in parsed.glyphs))
        self.assertTrue(any(glyph[1]<20 and glyph[4]>0 for glyph in parsed.glyphs))
        style=default_style(); style['axes']['left']['number_format']='scientific'; validate_style(style)
    def test_four_axes_math_legend_and_curve(self):
        style=default_style()
        style['general']['grid']=True
        for side,axis in style['axes'].items():
            axis.update(visible=True,label=r'$\rm{I}+\mathscr{A}+\bf{B}_{\alpha}$',color='#114488',size=12,width=2,direction='out')
        style['axes']['bottom'].update(tick_mode='array',ticks='[0:2:10]',labels="{'a','b',3,4,5,6}")
        style['axes']['right'].update(log=True,tick_mode='spacing',interval=1)
        style['legend'].update(visible=True,text=r'$\mathscr{I}$',frame=True)
        style['curve'].update(style='dashdotdot',marker='diamond',face='#ff0000',edge='#0000ff',marker_size=6)
        before=deepcopy(style); scan=XrdScan([0,2,4,6,8,10],[1,10,30,80,120,200])
        fig,data,axes=make_figure(scan,validate_style(style),(0,10,1,220),(900,650))
        self.assertEqual(style,before); self.assertEqual(len(axes),4)
        self.assertEqual(data.lines[0].get_marker(),'D'); self.assertEqual(data.get_legend().get_frame_on(),True)
        self.assertEqual(axes['right'].get_yscale(),'log')
        self.assertTrue(any(line.get_visible() for line in axes['bottom'].get_xgridlines()))
        self.assertEqual([t.get_text() for t in axes['bottom'].get_xticklabels()],['a','b','3','4','5','6'])
        fig.clear()

    def test_numeric_labels_are_text_and_missing_labels_are_blank(self):
        style=default_style(); style['axes']['bottom'].update(tick_mode='array',ticks='[0:2:10]',labels='120')
        figure,data,axes=make_figure(XrdScan([0,10],[1,5]),validate_style(style),(0,10,0,6),(650,450))
        self.assertEqual([t.get_text() for t in axes['bottom'].get_xticklabels()],['120','','','','',''])
        figure.clear()

    def test_log_nonpositive_samples_are_gaps(self):
        import math
        style=default_style(); style['axes']['left']['log']=True
        figure,data,axes=make_figure(XrdScan([1,2,3],[1,0,10]),style,(1,3,.5,20),(650,450))
        self.assertFalse(math.isfinite(float(data.yaxis.get_transform().transform(0))))
        figure.clear()

    def test_classic_log_minor_ticks_and_spacing_on_four_axes(self):
        import numpy as np
        style=default_style()
        for axis in style['axes'].values(): axis.update(visible=True,log=True)
        figure,data,axes=make_figure(XrdScan([1,10,100],[1,10,100]),style,(1,100,1,100),(800,650))
        for side,axis in axes.items():
            coordinate=axis.xaxis if side in ('bottom','top') else axis.yaxis
            minor=coordinate.get_minorticklocs()
            for value in [*range(2,10),*range(20,100,10)]: self.assertTrue(np.any(np.isclose(minor,value)),(side,value))
            self.assertTrue(all(not text.get_text() for text in coordinate.get_minorticklabels()))
            self.assertLess(coordinate.get_minor_ticks()[0].tick1line.get_markersize(),coordinate.get_major_ticks()[0].tick1line.get_markersize())
        positions=data.transData.transform(np.column_stack((np.arange(2,10),np.ones(8))))[:,0]
        self.assertTrue(np.all(np.diff(np.diff(positions))<0))  # 2–9 get progressively closer.
        figure.clear()

    def test_explicit_tick_arrays_do_not_gain_unrequested_minor_ticks(self):
        style=default_style(); style['axes']['left'].update(log=True,ticks='[]')
        figure,data,axes=make_figure(XrdScan([1,2],[1,100]),style,(1,2,1,100),(700,500))
        self.assertEqual(len(axes['left'].yaxis.get_majorticklocs()),0)
        self.assertEqual(len(axes['left'].yaxis.get_minorticklocs()),0)
        self.assertEqual(len(axes['bottom'].xaxis.get_minorticklocs()),0)
        figure.clear()

    def test_layout_uses_measured_label_margins(self):
        from matplotlib.transforms import Bbox
        scan=XrdScan([10,110],[1,100]); style=default_style()
        for width,height in ((1400,700),(700,800)):
            figure,data,axes=make_figure(scan,style,(10,110,0,110),(width,height))
            frame=data.get_window_extent(); renderer=figure.canvas.get_renderer()
            self.assertGreater(frame.width/width,.80)  # 25 pt labels reserve more room.
            self.assertGreater(frame.height/height,.80)
            boxes=[axis.get_tightbbox(renderer) for axis in axes.values()]
            total=Bbox.union(boxes)
            self.assertGreaterEqual(total.x0,6); self.assertGreaterEqual(total.y0,6)
            self.assertLessEqual(total.x1,width-6); self.assertLessEqual(total.y1,height-6)
            figure.clear()
        for axis in style['axes'].values(): axis.update(visible=True,size=20,label_size=24,label=r'$\mathscr{I}_{\alpha}$')
        figure,data,axes=make_figure(scan,style,(10,110,1,110),(1000,700))
        renderer=figure.canvas.get_renderer(); total=Bbox.union([axis.get_tightbbox(renderer) for axis in axes.values()])
        self.assertGreaterEqual(total.x0,4); self.assertGreaterEqual(total.y0,4)
        self.assertLessEqual(total.x1,996); self.assertLessEqual(total.y1,696)
        figure.clear()

class SessionTests(unittest.TestCase):
    def test_restart_and_shared_success_directory(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); a=root/'structure'; b=root/'data'; a.mkdir(); b.mkdir()
            path=root/'session.json'; state=SessionState(path)
            state.opened(a/'POSCAR'); self.assertEqual(SessionState(path).directory,str(a.resolve()))
            state.opened(b/'scan.ras'); self.assertEqual(SessionState(path).directory,str(b.resolve()))
