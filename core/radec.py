import math

def xyz_to_radec(X: float, Y: float, Z: float):
    r = math.sqrt(X*X + Y*Y + Z*Z)
    ra = math.atan2(Y, X)
    if ra < 0:
        ra += 2 * math.pi
    dec = math.asin(Z / r)
    return ra, dec
