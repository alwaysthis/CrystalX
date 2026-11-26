"""Transient selection overlay; never enters exported scientific figures."""
from PyQt6.QtCore import Qt,QPointF,QRectF
from PyQt6.QtGui import QPainter,QPen,QColor
from PyQt6.QtWidgets import QWidget
import numpy as np
from .math_ui import draw_text

def projected_points(plot,index):
    curve=plot.curves[index]
    points=plot.data_axes.transData.transform(np.column_stack((curve.x,curve.display_y)))
    ratio=plot.canvas.figure.bbox.width/plot.width()
    return np.column_stack((points[:,0]/ratio,plot.height()-points[:,1]/ratio))

def curve_hit(plot,position,threshold=7):
    best=None; distance=threshold*threshold
    if not plot.area().contains(position) or not plot.curve_visible: return None
    target=np.array([position.x(),position.y()])
    for index,curve in enumerate(plot.curves):
        if not curve.visible: continue
        if curve.style['style']=='none' and curve.style['marker']=='none': continue
        points=projected_points(plot,index)
        a,b=points[:-1],points[1:]; good=np.isfinite(a).all(axis=1)&np.isfinite(b).all(axis=1)
        a,b=a[good],b[good]
        if len(a):
            delta=b-a; denominator=(delta*delta).sum(axis=1)
            amount=np.clip(((target-a)*delta).sum(axis=1)/np.maximum(denominator,1e-20),0,1)
            current=float(np.min(((a+amount[:,None]*delta-target)**2).sum(axis=1)))
            if current<=distance: distance=current; best=index
        finite=points[np.isfinite(points).all(axis=1)]
        if len(finite):
            current=float(np.min(((finite-target)**2).sum(axis=1)))
            if current<=distance: distance=current; best=index
    return best

def nearest_point(plot,index,position):
    points=projected_points(plot,index); target=np.array([position.x(),position.y()])
    distance=((points-target)**2).sum(axis=1); distance[~np.isfinite(distance)]=np.inf
    return int(np.argmin(distance))

class LegendHandle(QWidget):
    """Screen-only empty legend surface and hover grip, excluded from export."""
    def __init__(self,plot):
        super().__init__(plot); self.plot=plot
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self,event):
        plot=self.plot
        if not hasattr(plot,'data_axes') or plot.data_axes.get_legend() is None: return
        empty=not plot.data_axes.legend_curve_indices
        if not empty and not plot.legend_hover and plot.legend_drag is None: return
        rect=plot.legend_rect().adjusted(-2,-2,2,2)
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor('#7c9788' if plot.legend_hover else '#b4c3ba'),1,Qt.PenStyle.DashLine))
            painter.setBrush(QColor(237,244,239,180) if empty else Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect,4,4)
            painter.setPen(QPen(QColor('#65816f'),1.3))
            center=rect.center().x()
            for dy in (4,7): painter.drawLine(QPointF(center-8,rect.top()+dy),QPointF(center+8,rect.top()+dy))

class CurveSelection(QWidget):
    def __init__(self,plot):
        super().__init__(plot); self.plot=plot
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def paintEvent(self,event):
        plot=self.plot; index=plot.selected_curve
        hover=plot.hover_point
        if (index is None or not plot.curve_visible or not plot.curves[index].visible) and hover is None and plot.peak_rect is None: return
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(plot.area())
        if plot.peak_rect is not None:
            painter.setPen(QPen(QColor('#356849'),1.3,Qt.PenStyle.DashLine)); painter.setBrush(QColor(53,104,73,35)); painter.drawRect(plot.peak_rect)
        # Keep the actual stroke visible while selecting or editing its style.
        # A continuous overlay used to hide its color, width and dash pattern.
        if index is not None and plot.curve_visible and plot.curves[index].visible:
            points=projected_points(plot,index)
            area=plot.area()
            visible=np.isfinite(points).all(axis=1)&(points[:,0]>=area.left())&(points[:,0]<=area.right())&(points[:,1]>=area.top())&(points[:,1]<=area.bottom())
            points=points[visible]
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor('#566b60'),1))
            last=None
            for position in np.linspace(0,len(points)-1,min(12,len(points)),dtype=int):
                x,y=points[position]; point=QPointF(float(x),float(y))
                if last is not None and (point-last).manhattanLength()<24: continue
                painter.drawEllipse(point,5,5); last=point
        if hover is not None:
            curve_index,point_index=hover; curve=plot.curves[curve_index]
            point=plot.point(curve.x[point_index],curve.display_y[point_index])
            painter.setPen(QPen(QColor('#be7812'),1.5)); painter.setBrush(QColor('#ffffff')); painter.drawEllipse(point,4.5,4.5)
            text=f'{curve.label}: ({curve.x[point_index]:.6g}, {curve.display_y[point_index]:.6g})'
            box=painter.fontMetrics().boundingRect(text).adjusted(-5,-3,5,3)
            box.moveTopLeft((point+QPointF(10,-box.height()-8)).toPoint())
            if box.right()>plot.area().right(): box.moveRight(int(plot.area().right()-2))
            if box.top()<plot.area().top(): box.moveTop(int(point.y()+10))
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(255,255,255,235)); painter.drawRoundedRect(box,3,3)
            painter.setPen(QColor('#333333')); draw_text(painter,QRectF(box),Qt.AlignmentFlag.AlignCenter,text)
