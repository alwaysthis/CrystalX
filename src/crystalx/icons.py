"""Small vector icons rendered locally, independent of installed symbol fonts."""
from PyQt6.QtCore import QByteArray,Qt
from PyQt6.QtGui import QPixmap,QPainter,QIcon,QColor
from PyQt6.QtSvg import QSvgRenderer

PATHS={
'select':'<path d="M5 3v17l5-5 4 7 3-2-4-7 7-1Z"/>',
'rotate':'<path d="M19 8a8 8 0 1 0 1 8M19 3v6h-6"/>',
'pan':'<path d="M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4"/>',
'zoom':'<circle cx="10" cy="10" r="7"/><path d="m15 15 7 7M6 10h8M10 6v8"/>',
'more':'<circle cx="4" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="20" cy="12" r="1"/>',
'expand':'<path d="m5 9 7 7 7-7"/>'}

PATHS['rotate']=PATHS['select']
PATHS['select']='<rect x="3" y="3" width="18" height="18" stroke-dasharray="3 3"/>'
PATHS['clear']='<rect x="3" y="3" width="18" height="18" stroke-dasharray="3 3"/><path d="m7 7 10 10M17 7 7 17"/>'
PATHS['fit']='<path d="M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6"/><rect x="8" y="8" width="8" height="8"/>'
for i,label in enumerate(['a','b','c','a*','b*','c*','P']):
    cube='<path d="m3 8 9-5 9 5v10l-9 4-9-4ZM3 8l9 5 9-5M12 13v9"/>'
    PATHS['view'+str(i)]=f'<text x="12" y="17" text-anchor="middle" stroke="none" fill="#285d41" font-size="12" font-family="sans-serif">{label}</text>'

PATHS['atom']='<circle cx="12" cy="12" r="4"/><path d="m3 7 3-4M18 3l3 4M21 17l-3 4M6 21l-3-4"/>'
PATHS['undo']='<path d="m9 4-6 6 6 6M3 10h11a7 7 0 0 1 7 7v3"/>'
PATHS['redo']='<path d="m15 4 6 6-6 6M21 10H10a7 7 0 0 0-7 7v3"/>'

PATHS['window_minimize']='<path d="M5 16h14"/>'
PATHS['window_maximize']='<rect x="5" y="5" width="14" height="14"/>'
PATHS['window_restore']='<path d="M9 8V4h11v11h-4"/><rect x="4" y="9" width="11" height="11"/>'
PATHS['window_close']='<path d="m6 6 12 12M18 6 6 18"/>'

PATHS['view6']='<path d="m4 5 16-3-2 18-14-3ZM4 5l10 5 6-8M14 10l-1 10M14 10 4 17"/>'
PATHS['fit']='<path d="m3 11 9-8 9 8M6 9v12h12V9M10 21v-7h4v7"/>'

PATHS['view6']='<path d="M3 8h12v13H3ZM8 3h13v13h-6M3 8l5-5M15 8l6-5M15 21l6-5"/>'
PATHS['copy_image']='<rect x="7" y="7" width="14" height="14" rx="2"/><path d="M17 7V3H3v14h4m3-1 3-4 3 3 2-2 3 5"/>'

PATHS['view6']='<path d="M2 9h12v13H2ZM9 2h13v13h-8M2 9l7-7M14 9l8-7M14 22l8-7"/><path d="M9 2v13H2m7 0 13 0" stroke-dasharray="2 2" stroke-opacity=".6"/>'

PATHS['eye']='<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>'
PATHS['help']='<circle cx="12" cy="12" r="10"/><path d="M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3M12 17h.01"/>'

from functools import lru_cache
@lru_cache(maxsize=64)
def icon(name):
    if name=='app':
        from pathlib import Path
        return QIcon(str(Path(__file__).resolve().parents[2]/'assets/crystalx.svg'))
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#395c47" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    result=QIcon(); renderer=QSvgRenderer(QByteArray(svg.encode()))
    for size in (16,18,19,20,21,22,24,28,32,36,40,48,64,96,128):
        pixmap=QPixmap(size,size); pixmap.fill(Qt.GlobalColor.transparent)
        painter=QPainter(pixmap); renderer.render(painter); painter.end(); result.addPixmap(pixmap)
        disabled=pixmap.copy(); painter=QPainter(disabled); painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); painter.fillRect(disabled.rect(),QColor('#b0b8b3')); painter.end()
        result.addPixmap(disabled,QIcon.Mode.Disabled)
    return result
