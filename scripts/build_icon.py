from pathlib import Path
import struct
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QBuffer,QIODevice
app=QApplication([])
root=Path(__file__).resolve().parents[1]
icon=QIcon(str(root/'assets/crystalx.svg'))
images=[]
for size in [16,32,48,64,128,256]:
    buffer=QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    icon.pixmap(size,size).save(buffer,'PNG'); images.append((size,bytes(buffer.data())))
offset=6+16*len(images); entries=[]; payload=b''
for size,data in images:
    entries.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset)); payload+=data; offset+=len(data)
(root/'assets/crystalx.ico').write_bytes(struct.pack('<HHH',0,1,len(images))+b''.join(entries)+payload)
