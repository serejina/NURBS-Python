"""
    NURBS Python Package
    Licensed under MIT License
    Developed by Onur Rauf Bingol (c) 2016-2017
"""

import decimal
import math


# Implementation of http://stackoverflow.com/a/7267280
def frange(x, y, step):
    step_str = str(step)
    while x <= y:
        yield float(x)
        x += decimal.Decimal(step_str)


def normalize_knotvector(knotvector=()):
    if len(knotvector) == 0:
        return knotvector

    first_knot = float(knotvector[0])
    last_knot = float(knotvector[-1])

    knotvector_out = []
    for kv in knotvector:
        knotvector_out.append((float(kv) - first_knot) / (last_knot - first_knot))

    return knotvector_out


def autogen_knotvector(degree=0, num_ctrlpts=0):
    if degree == 0 or num_ctrlpts == 0:
        raise ValueError("Input values should be different than zero.")

    # Min and max knot vector values
    knot_min = 0.0
    knot_max = 1.0

    # Equation to use: m = n + p + 1
    # p: degree, n+1: number of ctrlpts; m+1: number of knots
    m = degree + num_ctrlpts + 1

    # Initialize return value and counter
    knotvector = []
    i = 0

    # First degree+1 knots are "knot_min"
    while i < degree+1:
        knotvector.append(knot_min)
        i += 1

    # Calculate a uniform interval for middle knots
    num_segments = (m - (degree+1)*2)+1  # number of segments in the middle
    spacing = (knot_max - knot_min) / num_segments  # spacing between the knots (uniform)
    midknot = knot_min + spacing  # first middle knot
    # Middle knots
    while i < m-(degree+1):
        knotvector.append(midknot)
        midknot += spacing
        i += 1

    # Last degree+1 knots are "knot_max"
    while i < m:
        knotvector.append(knot_max)
        i += 1

    # Return autogenerated knot vector
    return knotvector


# Algorithm A2.1
def find_span(degree=0, knotvector=(), knot=0):
    # Number of knots; m + 1
    # Number of basis functions, n +1
    # n = m - p - 1; where p = degree
    m = len(knotvector) - 1
    n = m - degree - 1
    if knotvector[n + 1] == knot:
        return n

    low = degree
    high = n + 1
    mid = int((low + high) / 2)

    while (knot < knotvector[mid]) or (knot >= knotvector[mid + 1]):
        if knot < knotvector[mid]:
            high = mid
        else:
            low = mid
        mid = int((low + high) / 2)

    return mid


# Algorithm A2.2
def basis_functions(degree=0, knotvector=(), span=0, knot=0):
    left = [0.0] * (degree+1)
    right = [0.0] * (degree+1)

    # N[0] = 1.0 by definition
    bfuncs_out = [1.0]

    j = 1
    while j <= degree:
        left[j] = knot - knotvector[span+1-j]
        right[j] = knotvector[span+j] - knot
        saved = 0.0
        r = 0
        while r < j:
            temp = bfuncs_out[r] / (right[r+1] + left[j-r])
            bfuncs_out[r] = saved + right[r+1] * temp
            saved = left[j-r] * temp
            r += 1
        bfuncs_out.append(saved)
        j += 1

    return bfuncs_out


def basis_functions_ders(degree=0, knotvector=(), span=0, knot=0, order=0):
    # Initialize variables for easy access
    left = [None for x in range(degree+1)]
    right = [None for x in range(degree+1)]
    ndu = [[None for x in range(degree+1)] for y in range(degree+1)]

    # N[0][0] = 1.0 by definition
    ndu[0][0] = 1.0

    for j in range(1, degree+1):
        left[j] = knot - knotvector[span+1-j]
        right[j] = knotvector[span+j] - knot
        saved = 0.0
        r = 0
        for r in range(r, j):
            # Lower triangle
            ndu[j][r] = right[r+1] + left[j-r]
            temp = ndu[r][j-1] / ndu[j][r]
            # Upper triangle
            ndu[r][j] = saved + (right[r+1] * temp)
            saved = left[j-r] * temp
        ndu[j][j] = saved

    # Load the basis functions
    ders = [[None for x in range(degree+1)] for y in range((min(degree, order)+1))]
    for j in range(0, degree+1):
        ders[0][j] = ndu[j][degree]

    # Start calculating derivatives
    a = [[None for x in range(degree+1)] for y in range(2)]
    # Loop over function index
    for r in range(0, degree+1):
        # Alternate rows in array a
        s1 = 0
        s2 = 1
        a[0][0] = 1.0
        # Loop to compute k-th derivative
        for k in range(1, order+1):
            d = 0.0
            rk = r - k
            pk = degree - k
            if r >= k:
                a[s2][0] = a[s1][0] / ndu[pk+1][rk]
                d = a[s2][0] * ndu[rk][pk]
            if rk >= -1:
                j1 = 1
            else:
                j1 = -rk
            if (r - 1) <= pk:
                j2 = k - 1
            else:
                j2 = degree - r
            for j in range(j1, j2+1):
                a[s2][j] = (a[s1][j] - a[s1][j-1]) / ndu[pk+1][rk+j]
                d += (a[s2][j] * ndu[rk+j][pk])
            if r <= pk:
                a[s2][k] = -a[s1][k-1] / ndu[pk+1][r]
                d += (a[s2][k] * ndu[r][pk])
            ders[k][r] = d

            # Switch rows
            j = s1
            s1 = s2
            s2 = j

    # Multiply through by the the correct factors
    r = float(degree)
    for k in range(1, order+1):
        for j in range(0, degree+1):
            ders[k][j] *= r
        r *= (degree - k)

    # Return the basis function derivatives list
    return ders


def check_uv(u=-1, v=-1, test_normal=False, delta=0.1):
    # Check u value
    if u < 0.0 or u > 1.0:
        raise ValueError('"u" value should be between 0 and 1.')
    # Check v value
    if v < 0.0 or v > 1.0:
        raise ValueError('"v" value should be between 0 and 1.')

    if test_normal:
        # Check if we are on any edge of the surface
        if u + delta > 1.0 or u + delta < 0.0 or v + delta > 1.0 or v + delta < 0.0:
            raise ValueError("Cannot calculate normal on an edge.")


def cross_vector(vect1=(), vect2=()):
    if not vect1 or not vect2:
        raise ValueError("Input arguments are empty.")

    retval = [(vect1[1] * vect2[2]) - (vect1[2] * vect2[1]),
              (vect1[2] * vect2[0]) - (vect1[0] * vect2[2]),
              (vect1[0] * vect2[1]) - (vect1[1] * vect2[0])]

    # Return the cross product of input vectors
    return retval


def normalize_vector(vect=()):
    if not vect:
        raise ValueError("Input argument is empty.")

    # Calculate magnitude of the vector
    magnitude = math.sqrt(math.pow(vect[0], 2) + math.pow(vect[1], 2) + math.pow(vect[2], 2))

    if magnitude != 0:
        # Normalize the vector
        retval = [vect[0] / magnitude,
                  vect[1] / magnitude,
                  vect[2] / magnitude]
        # Return the normalized vector
        return retval
    else:
        raise ValueError("The magnitude of the vector is zero.")
