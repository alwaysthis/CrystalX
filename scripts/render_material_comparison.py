"""Actual cached shader output across roughness/IOR, for visual verification."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtCore import Qt,QRectF
from PyQt6.QtGui import QImage,QPainter,QColor,QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.sphere_material import sphere_image
app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
image=QImage(660,570,QImage.Format.Format_ARGB32_Premultiplied); image.fill(QColor('#f1f3f2'))
p=QPainter(image); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform); p.setFont(QFont('Microsoft YaHei',11)); p.setPen(QColor('#344b3c'))
for column,roughness in enumerate((.1,.35,.8)):
    p.drawText(QRectF(130+column*170,12,160,30),Qt.AlignmentFlag.AlignCenter,f'粗糙度 {roughness:g}')
for row,ior in enumerate((1.05,1.5,2.4)):
    p.drawText(QRectF(8,90+row*170,110,30),Qt.AlignmentFlag.AlignCenter,f'IOR {ior:g}')
    for column,roughness in enumerate((.1,.35,.8)):
        p.drawImage(QRectF(150+column*170,50+row*170,130,130),sphere_image((.18,.38,.8),roughness,ior,True))
p.end(); image.save('output/material-comparison.png'); print('Material comparison rendered')
