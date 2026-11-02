"""Display-only periodic images and reciprocal basis (without 2π)."""
from itertools import product
from .structure import cross,dot,cartesian

def reciprocal(lattice):
    volume=dot(lattice[0],cross(lattice[1],lattice[2]))
    return [[v/volume for v in cross(lattice[(i+1)%3],lattice[(i+2)%3])] for i in range(3)]

def periodic_images(structure):
    points=[]; sources=[]
    for i,point in enumerate(structure.positions):
        wrapped=[v%1 for v in point]
        wrapped=[0. if min(v,1-v)<1e-8 else v for v in wrapped]
        for image in product(*([0.,1.] if v==0 else [v] for v in wrapped)):
            points.append(cartesian(image,structure.lattice)); sources.append(i)
    return points,sources
