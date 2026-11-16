"""Lattice-relative standard crystal view, independent of GUI state."""
import math
from .structure import dot, cross


def unit(vector):
    length=math.sqrt(dot(vector,vector))
    return [v/length for v in vector]


def standard_orientation(lattice):
    """c up, b right, a toward the observer; shallow azimuth/elevation.

    Build an orthonormal frame from actual lattice vectors, then swing the eye
    around c by atan(1/3) and raise it by atan(1/6). The resulting matrix maps
    Cartesian vectors to screen-right, screen-up and observer-facing depth.
    """
    up=unit(lattice[2])
    right=unit([v-dot(lattice[1],up)*u for v,u in zip(lattice[1],up)])
    toward=cross(right,up)
    azimuth,elevation=math.atan(1/3),math.atan(1/6)
    ca,sa,ce,se=math.cos(azimuth),math.sin(azimuth),math.cos(elevation),math.sin(elevation)
    swung=[ca*a+sa*b for a,b in zip(toward,right)]
    return [[ca*b-sa*a for a,b in zip(toward,right)],
            [ce*c-se*a for c,a in zip(up,swung)],
            [ce*a+se*c for c,a in zip(up,swung)]]
