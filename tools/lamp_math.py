import math
from typing import Tuple

from lamp_types import IDENTITY, Matrix3, Vec3

Quaternion = Tuple[float, float, float, float]
Affine = Tuple[Matrix3, Vec3]

ORIGIN: Vec3 = (0.0, 0.0, 0.0)
UNIT_SCALE: Vec3 = (1.0, 1.0, 1.0)
IDENTITY_QUATERNION: Quaternion = (0.0, 0.0, 0.0, 1.0)
IDENTITY_AFFINE: Affine = (IDENTITY, ORIGIN)


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scaled(v: Vec3, factor: float) -> Vec3:
    return (v[0] * factor, v[1] * factor, v[2] * factor)


def distance_squared(a: Vec3, b: Vec3) -> float:
    dx, dy, dz = subtract(a, b)
    return dx * dx + dy * dy + dz * dz


def transform(m: Matrix3, v: Vec3) -> Vec3:
    return tuple(row[0] * v[0] + row[1] * v[1] + row[2] * v[2] for row in m)


def multiply(a: Matrix3, b: Matrix3) -> Matrix3:
    return tuple(tuple(sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3)) for row in range(3))


def diagonal(v: Vec3) -> Matrix3:
    return ((v[0], 0.0, 0.0), (0.0, v[1], 0.0), (0.0, 0.0, v[2]))


def rotation_x(radians: float) -> Matrix3:
    c, s = math.cos(radians), math.sin(radians)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def rotation_y(radians: float) -> Matrix3:
    c, s = math.cos(radians), math.sin(radians)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def rotation_z(radians: float) -> Matrix3:
    c, s = math.cos(radians), math.sin(radians)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def quaternion_matrix(q: Quaternion) -> Matrix3:
    length = math.sqrt(sum(component * component for component in q))
    if length == 0.0 or not math.isfinite(length):
        return IDENTITY
    x, y, z, w = (component / length for component in q)
    return ((1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
            (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
            (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)))


def apply_affine(affine: Affine, p: Vec3) -> Vec3:
    linear, offset = affine
    return add(transform(linear, p), offset)


def compose_affine(outer: Affine, inner: Affine) -> Affine:
    outer_linear, outer_offset = outer
    inner_linear, inner_offset = inner
    return multiply(outer_linear, inner_linear), add(transform(outer_linear, inner_offset), outer_offset)


def pivoted_affine(pivot: Vec3, translation: Vec3, rotation: Quaternion, scale: Vec3) -> Affine:
    linear = multiply(quaternion_matrix(rotation), diagonal(scale))
    return linear, subtract(add(pivot, translation), transform(linear, pivot))
