from math import fabs, sqrt, exp, floor
import numpy as np
from statistics import NormalDist
import sys

A = (3.1611237438705656, 113.864154151050156, 377.485237685302021, 3209.37758913846947, 0.185777706184603153)
B = (23.6012909523441209, 244.024637934444173, 1282.61652607737228, 2844.23683343917062)
C = (0.564188496988670089, 8.88314979438837594, 66.1191906371416295, 298.635138197400131, 881.95222124176909, 1712.04761263407058, 2051.07837782607147, 1230.33935479799725, 2.15311535474403846e-8)
D = (15.7449261107098347, 117.693950891312499, 537.181101862009858, 1621.38957456669019, 3290.79923573345963, 4362.61909014324716, 3439.36767414372164, 1230.33935480374942)
P = (0.305326634961232344, 0.360344899949804439, 0.125781726111229246, 0.0160837851487422766, 6.58749161529837803e-4, 0.0163153871373020978)
Q = (2.56852019228982242, 1.87295284992346047, 0.527905102951428412, 0.0605183413124413191, 0.00233520497626869185)

ZERO = 0.0
HALF = 0.5
ONE = 1.0
TWO = 2.0
FOUR = 4.0
SQRPI = 0.56418958354775628695
THRESH = 0.46875
SIXTEEN = 16.0
XINF = 1.79e308
XNEG = -26.628
XSMALL = 1.11e-16
XBIG = 26.543
XHUGE = 6.71e7
XMAX = 2.53e307

DBL_EPSILON = sys.float_info.epsilon
DBL_MAX = sys.float_info.max
DBL_MIN = sys.float_info.min
ONE_OVER_SQRT_TWO_PI = 0.3989422804014326779399460599343818684758586311649
ONE_OVER_SQRT_TWO = 0.7071067811865475244008443621048490392848359376887


def d_int(x):
    return floor(x) if x > 0 else -floor(-x)


def fix_up_for_negative_argument_erf_etc(jint, result, x):
    if jint == 0:
        result = (HALF - result) + HALF
        if x < ZERO:
            result = -result
    elif jint == 1:
        if x < ZERO:
            result = TWO - result
    else:
        if x < ZERO:
            if x < XNEG:
                result = XINF
            else:
                d__1 = x * SIXTEEN
                ysq = d_int(d__1) / SIXTEEN
                _del = (x - ysq) * (x + ysq)
                y = exp(ysq * ysq) * exp(_del)
                result = y + y - result
    return result


def d1(S, K, t, r, sigma):

    sigma_squared = sigma * sigma
    numerator = np.log(S / float(K)) + (r + sigma_squared / 2.0) * t
    denominator = sigma * np.sqrt(t)

    if not denominator:
        print("")
    return numerator / denominator


def calerf(x, jint):
    y = fabs(x)
    if y <= THRESH:
        ysq = ZERO
        if y > XSMALL:
            ysq = y * y
        xnum = A[4] * ysq
        xden = ysq
        for i__ in range(0, 3):
            xnum = (xnum + A[i__]) * ysq
            xden = (xden + B[i__]) * ysq
        result = x * (xnum + A[3]) / (xden + B[3])
        if jint != 0:
            result = ONE - result
        if jint == 2:
            result *= exp(ysq)

        return result
    elif y <= FOUR:
        xnum = C[8] * y
        xden = y
        for i__ in range(0, 7):
            xnum = (xnum + C[i__]) * y
            xden = (xden + D[i__]) * y
        result = (xnum + C[7]) / (xden + D[7])
        if jint != 2:
            d__1 = y * SIXTEEN
            ysq = d_int(d__1) / SIXTEEN
            _del = (y - ysq) * (y + ysq)
            d__1 = exp(-ysq * ysq) * exp(-_del)
            result *= d__1
    else:
        result = ZERO
        if y >= XBIG:
            if jint != 2 or y >= XMAX:
                return fix_up_for_negative_argument_erf_etc(jint, result, x)
            if y >= XHUGE:
                result = SQRPI / y
                return fix_up_for_negative_argument_erf_etc(jint, result, x)
        ysq = ONE / (y * y)
        xnum = P[5] * ysq
        xden = ysq
        for i__ in range(0, 4):
            xnum = (xnum + P[i__]) * ysq
            xden = (xden + Q[i__]) * ysq
        result = ysq * (xnum + P[4]) / (xden + Q[4])
        result = (SQRPI - result) / y
        if jint != 2:
            d__1 = y * SIXTEEN
            ysq = d_int(d__1) / SIXTEEN
            _del = (y - ysq) * (y + ysq)
            d__1 = exp(-ysq * ysq) * exp(-_del)
            result *= d__1
    return fix_up_for_negative_argument_erf_etc(jint, result, x)


def erfc_cody(x):
    return calerf(x, 1)


def norm_pdf(x):
    return ONE_OVER_SQRT_TWO_PI * exp(-0.5 * x * x)


norm_cdf_asymptotic_expansion_first_threshold = -10.0
norm_cdf_asymptotic_expansion_second_threshold = -1 / sqrt(DBL_EPSILON)


def norm_cdf(z):
    if z <= norm_cdf_asymptotic_expansion_first_threshold:
        sum = 1
        if z >= norm_cdf_asymptotic_expansion_second_threshold:
            zsqr = z * z
            i = 1
            g = 1
            x = 0
            y = 0
            a = DBL_MAX

            lasta = a
            x = (4 * i - 3) / zsqr
            y = x * ((4 * i - 1) / zsqr)
            a = g * (x - y)
            sum -= a
            g *= y
            i += 1
            a = fabs(a)
            while lasta > a >= fabs(sum * DBL_EPSILON):
                lasta = a
                x = (4 * i - 3) / zsqr
                y = x * ((4 * i - 1) / zsqr)
                a = g * (x - y)
                sum -= a
                g *= y
                i += 1
                a = fabs(a)
        return -norm_pdf(z) * sum / z
    return 0.5 * erfc_cody(-z * ONE_OVER_SQRT_TWO)


def delta(flag, S, K, t, r, sigma):

    d_1 = d1(S, K, t, r, sigma)

    if flag == "p":
        return norm_cdf(d_1) - 1.0
    else:
        return norm_cdf(d_1)


def delta_calc(r, S, K, T, sigma, type="c"):
    d1 = (np.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    try:
        if type == "c":
            delta_calc = NormalDist().cdf(d1)
        elif type == "p":
            delta_calc = -NormalDist().cdf(-d1)
        return delta_calc, delta(type, S, K, T, r, sigma)
    except Exception as e:
        print(e)
        print("Please confirm option type, either 'c' for Call or 'p' for Put!")
