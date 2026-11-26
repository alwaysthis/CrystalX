"""Shared centered checkbox delegate for compact editor tables."""
from PyQt6.QtCore import Qt,QEvent,QRect
from PyQt6.QtWidgets import QStyledItemDelegate,QStyle,QStyleOptionViewItem
from .theme import CHECKBOX_SIZE

class CenteredCheckDelegate(QStyledItemDelegate):
    def paint(self,painter,option,index):
        check=QStyleOptionViewItem(option); check.rect=QRect(0,0,CHECKBOX_SIZE+2,CHECKBOX_SIZE+2); check.rect.moveCenter(option.rect.center())
        check.state=QStyle.StateFlag.State_Enabled
        state=index.data(Qt.ItemDataRole.CheckStateRole)
        check.state|=QStyle.StateFlag.State_On if state==Qt.CheckState.Checked.value else QStyle.StateFlag.State_Off
        option.widget.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,check,painter,option.widget)
    def editorEvent(self,event,model,option,index):
        if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton or event.type()==QEvent.Type.KeyPress and event.key()==Qt.Key.Key_Space:
            value=Qt.CheckState.Unchecked if index.data(Qt.ItemDataRole.CheckStateRole)==Qt.CheckState.Checked.value else Qt.CheckState.Checked
            return model.setData(index,value,Qt.ItemDataRole.CheckStateRole)
        return False
