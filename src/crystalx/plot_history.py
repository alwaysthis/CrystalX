"""Per-scan plot snapshots covering curves, processing and appearance."""
from copy import deepcopy

class PlotHistory:
    def init_history(self):
        self.history={}; self.redo_history={}; self.committed={}; self.history_locked=False

    def snapshot(self):
        memo={id(array):array for curve in self.curves for array in (curve.x,curve.y)}
        return deepcopy(dict(style=self.style,curves=self.curves,bounds=self.bounds,legend_anchor=self.legend_anchor,
            selected_curve=self.selected_curve,curve_visible=self.curve_visible,template_name=self.template_name,template_path=self.template_path),memo)

    def remember(self):
        if self.scan is None or self.history_locked: return
        key=id(self.scan); state=self.snapshot(); previous=self.committed.get(key)
        if previous is not None:
            keys=('style','curves','bounds','legend_anchor','curve_visible')
            if all(previous[k]==state[k] for k in keys): return
            self.history.setdefault(key,[]).append(previous); self.redo_history[key]=[]
            self.history[key]=self.history[key][-100:]
        self.committed[key]=state; self.history_changed.emit()

    @property
    def can_undo(self): return bool(self.history.get(id(self.scan)))
    @property
    def can_redo(self): return bool(self.redo_history.get(id(self.scan)))

    def restore_history(self,redo=False):
        key=id(self.scan); source=self.redo_history if redo else self.history; destination=self.history if redo else self.redo_history
        if not source.get(key): return False
        destination.setdefault(key,[]).append(self.snapshot()); state=deepcopy(source[key].pop())
        self.history_locked=True
        try:
            for name,value in state.items(): setattr(self,name,value)
            self.close_editors()
            self.rebuild(); self.committed[key]=self.snapshot()
        finally: self.history_locked=False
        self.selection_changed.emit(); self.history_changed.emit(); self.curve_removed.emit(); return True
