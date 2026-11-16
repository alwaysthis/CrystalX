"""Periodic distance-based bonds, clipped to the displayed unit cell."""
from itertools import product
from collections import defaultdict
from math import ceil, floor, sqrt
import json
from pathlib import Path

DEFAULT_RANGES=json.loads((Path(__file__).resolve().parents[2]/'config/default/bond-ranges.json').read_text(encoding='utf-8'))['ranges']

def pair_key(a,b): return '-'.join(sorted((a,b)))
from .structure import cartesian, dot
from .display_geometry import reciprocal


def clip_segment(a, b):
    low, high = 0., 1.
    for x, y in zip(a, b):
        d = y-x
        if abs(d)<1e-12:
            if x < -1e-9 or x > 1+1e-9: return None
        else:
            u, v = sorted((-x/d, (1-x)/d))
            low, high = max(low,u), min(high,v)
            if high-low<1e-9: return None
    return tuple(tuple(x+t*(y-x) for x,y in zip(a,b)) for t in (low,high))


def automatic_bonds(structure, ranges=None, *, matched_ranges=None):
    """Search only configured element pairs, using distance bounds in angstrom.

    Defaults use VESTA 3.5.8 element-pair limits; missing pairs have no fallback.
    Reciprocal bounds include oblique/short-cell neighbors. Bins avoid all-pairs
    search. Returned segments are display-only and clipped to the unit cell.
    """
    ranges=DEFAULT_RANGES if ranges is None else ranges
    species=set(structure.elements)
    active={key:bounds for key,bounds in ranges.items() if set(key.split('-'))<=species and bounds}
    cutoff=max((high for bounds in active.values() for low,high in bounds),default=0.)
    if cutoff<=0: return []
    margin=[cutoff*sqrt(dot(v,v)) for v in reciprocal(structure.lattice)]
    images=[]; bins=defaultdict(list)
    for source,position in enumerate(structure.positions):
        f=[v%1 for v in position]
        ranges=[range(ceil(-m-x-1e-9),floor(1+m-x+1e-9)+1) for m,x in zip(margin,f)]
        for shift in product(*ranges):
            frac=tuple(x+s for x,s in zip(f,shift)); point=cartesian(frac,structure.lattice)
            key=tuple(floor(v/cutoff) for v in point)
            images.append((frac,point,source)); bins[key].append(len(images)-1)
    result=[]; seen=set(); offsets=list(product((-1,0,1),repeat=3))
    for i,(fa,a,source) in enumerate(images):
        key=tuple(floor(v/cutoff) for v in a)
        for delta in offsets:
            for j in bins.get(tuple(x+y for x,y in zip(key,delta)),()):
                if j<=i: continue
                fb,b,target=images[j]
                pair=pair_key(structure.elements[source],structure.elements[target])
                bounds=active.get(pair,())
                if not bounds: continue
                distance=sum((x-y)**2 for x,y in zip(a,b))
                if distance<1e-16 or not any(low**2-1e-12<=distance<=high**2+1e-12 for low,high in bounds): continue
                clipped=clip_segment(fa,fb)
                if clipped is None: continue
                if matched_ranges is not None:
                    matched_ranges.update((pair,low,high) for low,high in bounds if low**2-1e-12<=distance<=high**2+1e-12)
                token=tuple(sorted(tuple(round(v,8) for v in p) for p in clipped))
                if token in seen: continue
                seen.add(token)
                result.append((cartesian(clipped[0],structure.lattice),cartesian(clipped[1],structure.lattice),source,target))
    return result
