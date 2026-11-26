"""Small safe numeric expression language with Mathematica-style calls/domains."""
import ast,re
import numpy as np

FUNCTIONS={name:getattr(np,target) for name,target in {'sin':'sin','cos':'cos','tan':'tan','asin':'arcsin','acos':'arccos','atan':'arctan','exp':'exp','log':'log','sqrt':'sqrt','abs':'abs','sinh':'sinh','cosh':'cosh','tanh':'tanh','log10':'log10'}.items()}
CONSTANTS={'pi':np.pi,'e':np.e}

def parse(text):
    try: tree=ast.parse(text.replace('^','**').replace('[','(').replace(']',')'),mode='eval')
    except SyntaxError as error: raise ValueError('表达式语法无效。') from error
    if sum(1 for _ in ast.walk(tree))>200: raise ValueError('表达式过长。')
    for node in ast.walk(tree):
        if not isinstance(node,(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Constant,ast.Name,ast.Load,ast.Call,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.USub,ast.UAdd,ast.Mod)):
            raise ValueError('只支持数学运算和常用数学函数。')
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id.lower() not in FUNCTIONS or node.keywords): raise ValueError('不支持该函数。')
        if isinstance(node,ast.Constant) and (type(node.value) not in (int,float) or abs(node.value)>1e100): raise ValueError('数值无效。')
    return tree.body

def evaluate(node,variables):
    if isinstance(node,ast.Constant): return node.value
    if isinstance(node,ast.Name):
        if node.id in variables: return variables[node.id]
        if node.id.lower() in CONSTANTS: return CONSTANTS[node.id.lower()]
        raise ValueError('未定义的变量：'+node.id)
    if isinstance(node,ast.UnaryOp): return -evaluate(node.operand,variables) if isinstance(node.op,ast.USub) else evaluate(node.operand,variables)
    if isinstance(node,ast.Call): return FUNCTIONS[node.func.id.lower()](*[evaluate(arg,variables) for arg in node.args])
    left,right=evaluate(node.left,variables),evaluate(node.right,variables)
    if isinstance(node.op,ast.Pow) and np.ndim(right)==0 and abs(right)>100: raise ValueError('指数超出支持范围。')
    for kind,operation in ((ast.Add,np.add),(ast.Sub,np.subtract),(ast.Mult,np.multiply),(ast.Div,np.divide),(ast.Pow,np.power),(ast.Mod,np.mod)):
        if isinstance(node.op,kind): return operation(left,right)
    raise ValueError('不支持的表达式。')

def expression_curves(text,domain,bounds):
    text=text.strip(); match=re.search(r',\s*\{\s*([^,{}]+),\s*([^,{}]+),\s*([^,{}]+)\}\s*$',text)
    variable=None
    if match: variable,low,high=match.groups(); text=text[:match.start()]
    else:
        parts=domain.strip().strip('{}[]').split(',')
        if len(parts)==3: variable,low,high=parts
        elif len(parts)==2: low,high=parts
        else: raise ValueError('定义域请输入最小值,最大值或{变量,最小值,最大值}。')
    low=float(evaluate(parse(low.strip()),{})); high=float(evaluate(parse(high.strip()),{}))
    if not np.isfinite([low,high]).all() or low>=high: raise ValueError('定义域须为有限的递增范围。')
    with np.errstate(all='ignore'):
        if '=' in text:
            sides=re.split(r'==|=',text)
            if len(sides)!=2: raise ValueError('方程只支持一个等号。')
            left,right=map(parse,sides); xs=np.linspace(low,high,350); ys=np.linspace(bounds[2],bounds[3],350)
            xx,yy=np.meshgrid(xs,ys); values=np.asarray(evaluate(left,{'x':xx,'y':yy})-evaluate(right,{'x':xx,'y':yy}))+np.zeros_like(xx)
            from matplotlib.figure import Figure
            figure=Figure(); axis=figure.add_subplot(); contour=axis.contour(xx,yy,values,levels=[0]); segments=[segment for segment in contour.allsegs[0] if len(segment)>=2]; figure.clear()
        else:
            node=parse(text); names={n.id for n in ast.walk(node) if isinstance(n,ast.Name) and n.id.lower() not in FUNCTIONS and n.id.lower() not in CONSTANTS}
            if variable is None: variable=next(iter(names),'x')
            variable=variable.strip()
            if names-{variable}: raise ValueError('函数只能包含一个自变量。')
            xs=np.linspace(low,high,1501); values=np.broadcast_to(evaluate(node,{variable:xs}),xs.shape)
            valid=np.isfinite(values)&(abs(values)<1e15); indices=np.flatnonzero(np.diff(np.r_[False,valid,False]))
            segments=[np.column_stack((xs[a:b],values[a:b])) for a,b in zip(indices[::2],indices[1::2]) if b-a>=2]
    if not segments: raise ValueError('当前范围没有可绘制的曲线，请检查定义域/纵轴范围。')
    return [(segment[:,0].tolist(),segment[:,1].tolist()) for segment in segments]
