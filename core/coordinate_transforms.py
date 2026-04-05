import math

def rotate_z(x: float, y: float, z: float, angle: float):
    c = math.cos(angle)
    s = math.sin(angle)
    return (c*x - s*y, s*x + c*y, z)

def rotate_x(x: float, y: float, z: float, angle: float):
    c = math.cos(angle)
    s = math.sin(angle)
    return (x, c*y - s*z, s*y + c*z)

def orbital_to_inertial(x: float, y: float, z: float, Omega: float, inc: float, omega: float):
    x1, y1, z1 = rotate_z(x, y, z, omega)
    x2, y2, z2 = rotate_x(x1, y1, z1, inc)
    x3, y3, z3 = rotate_z(x2, y2, z2, Omega)
    return x3, y3, z3
