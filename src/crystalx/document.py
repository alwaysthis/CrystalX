"""Undoable document operations independent of Qt."""
class TranslateCommand:
    def __init__(self,structure,indices,vector):
        self.structure=structure
        self.before={i:structure.positions[i][:] for i in indices}
        self.after={i:[a+b for a,b in zip(point,vector)] for i,point in self.before.items()}

    def redo(self):
        for i,point in self.after.items(): self.structure.positions[i]=point[:]

    def undo(self):
        for i,point in self.before.items(): self.structure.positions[i]=point[:]


class StructureDocument:
    def __init__(self,structure=None):
        self.structure=structure; self.commands=[]; self.index=0; self.saved_index=0

    @property
    def dirty(self): return self.index!=self.saved_index

    def execute(self,command):
        if self.saved_index>self.index: self.saved_index=-1
        del self.commands[self.index:]
        command.redo(); self.commands.append(command); self.index+=1

    def undo(self):
        if self.index:
            self.index-=1; self.commands[self.index].undo()

    def redo(self):
        if self.index<len(self.commands):
            self.commands[self.index].redo(); self.index+=1


class SnapshotCommand:
    """Prepare on a copy; commit all fields together and retain exact undo data."""
    def __init__(self,structure,operation,*args):
        from copy import deepcopy
        self.structure=structure
        self.before=deepcopy(structure.__dict__)
        work=deepcopy(structure)
        operation(work,*args)
        self.after=deepcopy(work.__dict__)

    def restore(self,state):
        from copy import deepcopy
        self.structure.__dict__.update(deepcopy(state))

    def redo(self): self.restore(self.after)
    def undo(self): self.restore(self.before)
