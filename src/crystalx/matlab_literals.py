"""Safe MATLAB-style literal concatenation, ranges and cell/string labels.

No eval, functions or workspace variable execution. Nested rows flatten in input
order for use as ticks/labels; quoted strings support doubled quote escaping.
"""
import math
import re

TOKEN=re.compile(r'''\s*(?:(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|(?P<string>'(?:[^']|'')*'|"(?:[^"]|"")*")|(?P<symbol>[\[\]{}:,;]))''')
LIMIT=10000

def parse_literal(text,strings=False):
    text=text.strip()
    if not text: return []
    tokens=[]; pos=0
    while pos<len(text):
        match=TOKEN.match(text,pos)
        if not match: raise ValueError('请输入数值、引号文本、数组或 start:step:end；不支持执行MATLAB代码。')
        tokens.append((match.lastgroup,match.group(match.lastgroup))); pos=match.end()
    index=0
    def sequence(end=None):
        nonlocal index
        values=[]
        while index<len(tokens):
            kind,value=tokens[index]; index+=1
            if value==end: return values
            if value in (',',';'): continue
            if value in ('[','{'): values.extend(sequence(']' if value=='[' else '}'))
            elif kind=='string':
                if not strings: raise ValueError('刻度位置必须是数值。')
                quote=value[0]; values.append(value[1:-1].replace(quote*2,quote))
            elif kind=='number':
                start=float(value)
                if not math.isfinite(start): raise ValueError('数值必须有限。')
                parts=[start]
                while index<len(tokens) and tokens[index][1]==':':
                    index+=1
                    if index>=len(tokens) or tokens[index][0]!='number': raise ValueError('范围缺少数值。')
                    parts.append(float(tokens[index][1])); index+=1
                if len(parts)==1: values.append(start)
                elif len(parts) in (2,3):
                    start=parts[0]; step=1. if len(parts)==2 else parts[1]; stop=parts[-1]
                    if not all(math.isfinite(v) for v in (start,step,stop)) or step==0: raise ValueError('范围步长必须有限且非零。')
                    count=max(0,math.floor((stop-start)/step+1e-10)+1)
                    if count>LIMIT: raise ValueError('刻度/标签最多10000项。')
                    values.extend(start+i*step for i in range(count))
                else: raise ValueError('范围应为start:end或start:step:end。')
            else: raise ValueError('数组括号不匹配。')
            if len(values)>LIMIT: raise ValueError('刻度/标签最多10000项。')
        if end is not None: raise ValueError('数组缺少闭合括号。')
        return values
    result=sequence()
    if strings: return [v if isinstance(v,str) else f'{v:g}' for v in result]
    return result
