"""Small vector icons rendered locally, independent of installed symbol fonts."""
from PyQt6.QtCore import QByteArray,Qt
from PyQt6.QtGui import QPixmap,QPainter,QIcon
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
for i,label in enumerate(['a','b','c','a*','b*','c*','iso']):
    cube='<path d="m3 8 9-5 9 5v10l-9 4-9-4ZM3 8l9 5 9-5M12 13v9"/>'
    PATHS['view'+str(i)]=f'<rect x="4" y="7" width="17" height="12" fill="#fafbf9" stroke="none"/><text x="12" y="17" text-anchor="middle" stroke="none" fill="#285d41" font-size="12" font-family="sans-serif">{label}</text>'

PATHS['atom']='<circle cx="12" cy="12" r="4"/><path d="m3 7 3-4M18 3l3 4M21 17l-3 4M6 21l-3-4"/>'
PATHS['undo']='<path d="m9 4-6 6 6 6M3 10h11a7 7 0 0 1 7 7v3"/>'
PATHS['redo']='<path d="m15 4 6 6-6 6M21 10H10a7 7 0 0 0-7 7v3"/>'

PATHS['window_minimize']='<path d="M5 16h14"/>'
PATHS['window_maximize']='<rect x="5" y="5" width="14" height="14"/>'
PATHS['window_restore']='<path d="M9 8V4h11v11h-4"/><rect x="4" y="9" width="11" height="11"/>'
PATHS['window_close']='<path d="m6 6 12 12M18 6 6 18"/>'

def icon(name):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#456451" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    pixmap=QPixmap(96,96);  pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap); QSvgRenderer(QByteArray(svg.encode())).render(painter); painter.end()
    return QIcon(pixmap)
