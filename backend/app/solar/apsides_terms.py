"""Datos del perigeo y apogeo de la Luna (Meeus, Astronomical Algorithms,
2da ed., cap. 50, pp. 355-360).

Solo datos, sin logica. Formato de las tablas de terminos:

    (d, m, f, coef, coef_t)

- d, m, f: multiplicadores enteros de los argumentos D (elongacion media de la
  Luna), M (anomalia media del Sol) y F (argumento de latitud de la Luna).
  El argumento del termino es  d*D + m*M + f*F.
- coef: coeficiente constante del termino.
- coef_t: coeficiente que multiplica a T (T = k / 1325.55); 0.0 si el libro no
  da termino en T para esa fila. El coeficiente efectivo es coef + coef_t * T.

Las filas conservan el orden del libro: primero la columna izquierda completa y
luego la derecha. Cada tabla se transcribio y se verifico dos veces.

- PERIGEO_TIEMPO / APOGEO_TIEMPO (Tabla 50.A): terminos periodicos para el
  instante, en dias. Se usa el SENO del argumento y se suman al JDE medio.
- PERIGEO_PARALAJE / APOGEO_PARALAJE (Tabla 50.B): terminos de la paralaje
  horizontal ecuatorial, en segundos de arco. Se usa el COSENO del argumento.
  El libro da, ademas, un termino constante inicial (*_PARALAJE_BASE).
- El capitulo NO da una tabla de distancias: la distancia se obtiene de la
  paralaje (sin(pi) = 6378.14 / distancia, cap. 47). Ver RADIO_ECUATORIAL_KM.

Los polinomios se dan en tuplas de coeficientes (c0, c1, c2, ...) de k y de T:
    valor = c0 + c1*k + c2*T**2 + c3*T**3 + c4*T**4
Se codifican como diccionarios con claves explicitas para evitar ambiguedad.
"""

# --- Constantes y polinomios (formulas 50.1, 50.2, 50.3 y angulos) ---

# Formula 50.1: JDE medio. k entero -> perigeo; k entero + 0.5 -> apogeo.
# k = 0 corresponde al perigeo del 22 de diciembre de 1999.
JDE_MEDIO = {
    "c0": 2451534.6698,
    "k": 27.55454989,
    "t2": -0.0006691,
    "t3": -0.000001098,
    "t4": 0.0000000052,
}

# Formula 50.2: k aproximado = (anio_con_decimales - K_ANIO_BASE) * K_POR_ANIO
K_ANIO_BASE = 1999.97
K_POR_ANIO = 13.2555

# Formula 50.3: T = k / K_DIVISOR_T (siglos julianos desde J2000.0)
K_DIVISOR_T = 1325.55

# Elongacion media de la Luna D, en grados.
ARG_D = {
    "c0": 171.9179,
    "k": 335.9106046,
    "t2": -0.0100383,
    "t3": -0.00001156,
    "t4": 0.000000055,
}

# Anomalia media del Sol M, en grados.
ARG_M = {
    "c0": 347.3477,
    "k": 27.1577721,
    "t2": -0.000813,
    "t3": -0.000001,
    "t4": 0.0,
}

# Argumento de latitud de la Luna F, en grados.
ARG_F = {
    "c0": 316.6109,
    "k": 364.5287911,
    "t2": -0.0125053,
    "t3": -0.0000148,
    "t4": 0.0,
}

# Radio ecuatorial terrestre usado para pasar de paralaje a distancia (cap. 47).
RADIO_ECUATORIAL_KM = 6378.14

# --- Tabla 50.A: terminos periodicos del instante, en dias (seno) ---

# (d, m, f, coef, coef_t)   -- 60 terminos
PERIGEO_TIEMPO = (
    # Columna izquierda
    (2, 0, 0, -1.6769, 0.0),
    (4, 0, 0, +0.4589, 0.0),
    (6, 0, 0, -0.1856, 0.0),
    (8, 0, 0, +0.0883, 0.0),
    (2, -1, 0, -0.0773, +0.00019),
    (0, 1, 0, +0.0502, -0.00013),
    (10, 0, 0, -0.0460, 0.0),
    (4, -1, 0, +0.0422, -0.00011),
    (6, -1, 0, -0.0256, 0.0),
    (12, 0, 0, +0.0253, 0.0),
    (1, 0, 0, +0.0237, 0.0),
    (8, -1, 0, +0.0162, 0.0),
    (14, 0, 0, -0.0145, 0.0),
    (0, 0, 2, +0.0129, 0.0),
    (3, 0, 0, -0.0112, 0.0),
    (10, -1, 0, -0.0104, 0.0),
    (16, 0, 0, +0.0086, 0.0),
    (12, -1, 0, +0.0069, 0.0),
    (5, 0, 0, +0.0066, 0.0),
    (2, 0, 2, -0.0053, 0.0),
    (18, 0, 0, -0.0052, 0.0),
    (14, -1, 0, -0.0046, 0.0),
    (7, 0, 0, -0.0041, 0.0),
    (2, 1, 0, +0.0040, 0.0),
    (20, 0, 0, +0.0032, 0.0),
    (1, 1, 0, -0.0032, 0.0),
    (16, -1, 0, +0.0031, 0.0),
    (4, 1, 0, -0.0029, 0.0),
    (9, 0, 0, +0.0027, 0.0),
    (4, 0, 2, +0.0027, 0.0),
    # Columna derecha
    (2, -2, 0, -0.0027, 0.0),
    (4, -2, 0, +0.0024, 0.0),
    (6, -2, 0, -0.0021, 0.0),
    (22, 0, 0, -0.0021, 0.0),
    (18, -1, 0, -0.0021, 0.0),
    (6, 1, 0, +0.0019, 0.0),
    (11, 0, 0, -0.0018, 0.0),
    (8, 1, 0, -0.0014, 0.0),
    (4, 0, -2, -0.0014, 0.0),
    (6, 0, 2, -0.0014, 0.0),
    (3, 1, 0, +0.0014, 0.0),
    (5, 1, 0, -0.0014, 0.0),
    (13, 0, 0, +0.0013, 0.0),
    (20, -1, 0, +0.0013, 0.0),
    (3, 2, 0, +0.0011, 0.0),
    (4, -2, 2, -0.0011, 0.0),
    (1, 2, 0, -0.0010, 0.0),
    (22, -1, 0, -0.0009, 0.0),
    (0, 0, 4, -0.0008, 0.0),
    (6, 0, -2, +0.0008, 0.0),
    (2, 1, -2, +0.0008, 0.0),
    (0, 2, 0, +0.0007, 0.0),
    (0, -1, 2, +0.0007, 0.0),
    (2, 0, 4, +0.0007, 0.0),
    (0, -2, 2, -0.0006, 0.0),
    (2, 2, -2, -0.0006, 0.0),
    (24, 0, 0, +0.0006, 0.0),
    (4, 0, -4, +0.0005, 0.0),
    (2, 2, 0, +0.0005, 0.0),
    (1, -1, 0, -0.0004, 0.0),
)

# (d, m, f, coef, coef_t)   -- 32 terminos
APOGEO_TIEMPO = (
    # Columna izquierda
    (2, 0, 0, +0.4392, 0.0),
    (4, 0, 0, +0.0684, 0.0),
    (0, 1, 0, +0.0456, -0.00011),
    (2, -1, 0, +0.0426, -0.00011),
    (0, 0, 2, +0.0212, 0.0),
    (1, 0, 0, -0.0189, 0.0),
    (6, 0, 0, +0.0144, 0.0),
    (4, -1, 0, +0.0113, 0.0),
    (2, 0, 2, +0.0047, 0.0),
    (1, 1, 0, +0.0036, 0.0),
    (8, 0, 0, +0.0035, 0.0),
    (6, -1, 0, +0.0034, 0.0),
    (2, 0, -2, -0.0034, 0.0),
    (2, -2, 0, +0.0022, 0.0),
    (3, 0, 0, -0.0017, 0.0),
    (4, 0, 2, +0.0013, 0.0),
    # Columna derecha
    (8, -1, 0, +0.0011, 0.0),
    (4, -2, 0, +0.0010, 0.0),
    (10, 0, 0, +0.0009, 0.0),
    (3, 1, 0, +0.0007, 0.0),
    (0, 2, 0, +0.0006, 0.0),
    (2, 1, 0, +0.0005, 0.0),
    (2, 2, 0, +0.0005, 0.0),
    (6, 0, 2, +0.0004, 0.0),
    (6, -2, 0, +0.0004, 0.0),
    (10, -1, 0, +0.0004, 0.0),
    (5, 0, 0, -0.0004, 0.0),
    (4, 0, -2, -0.0004, 0.0),
    (0, 1, 2, +0.0003, 0.0),
    (12, 0, 0, +0.0003, 0.0),
    (2, -1, 2, +0.0003, 0.0),
    (1, -1, 0, -0.0003, 0.0),
)

# --- Tabla 50.B: terminos de la paralaje horizontal ecuatorial, en segundos
# de arco (coseno del argumento) ---

# Termino constante inicial de la paralaje (segundos de arco).
PERIGEO_PARALAJE_BASE = 3629.215
APOGEO_PARALAJE_BASE = 3245.251

# (d, m, f, coef, coef_t)   -- 46 terminos
PERIGEO_PARALAJE = (
    # Columna izquierda
    (2, 0, 0, +63.224, 0.0),
    (4, 0, 0, -6.990, 0.0),
    (2, -1, 0, +2.834, -0.0071),
    (6, 0, 0, +1.927, 0.0),
    (1, 0, 0, -1.263, 0.0),
    (8, 0, 0, -0.702, 0.0),
    (0, 1, 0, +0.696, -0.0017),
    (0, 0, 2, -0.690, 0.0),
    (4, -1, 0, -0.629, +0.0016),
    (2, 0, -2, -0.392, 0.0),
    (10, 0, 0, +0.297, 0.0),
    (6, -1, 0, +0.260, 0.0),
    (3, 0, 0, +0.201, 0.0),
    (2, 1, 0, -0.161, 0.0),
    (1, 1, 0, +0.157, 0.0),
    (12, 0, 0, -0.138, 0.0),
    (8, -1, 0, -0.127, 0.0),
    (2, 0, 2, +0.104, 0.0),
    (2, -2, 0, +0.104, 0.0),
    (5, 0, 0, -0.079, 0.0),
    (14, 0, 0, +0.068, 0.0),
    # Columna derecha
    (10, -1, 0, +0.067, 0.0),
    (4, 1, 0, +0.054, 0.0),
    (12, -1, 0, -0.038, 0.0),
    (4, -2, 0, -0.038, 0.0),
    (7, 0, 0, +0.037, 0.0),
    (4, 0, 2, -0.037, 0.0),
    (16, 0, 0, -0.035, 0.0),
    (3, 1, 0, -0.030, 0.0),
    (1, -1, 0, +0.029, 0.0),
    (6, 1, 0, -0.025, 0.0),
    (0, 2, 0, +0.023, 0.0),
    (14, -1, 0, +0.023, 0.0),
    (2, 2, 0, -0.023, 0.0),
    (6, -2, 0, +0.022, 0.0),
    (2, -1, -2, -0.021, 0.0),
    (9, 0, 0, -0.020, 0.0),
    (18, 0, 0, +0.019, 0.0),
    (6, 0, 2, +0.017, 0.0),
    (0, -1, 2, +0.014, 0.0),
    (16, -1, 0, -0.014, 0.0),
    (4, 0, -2, +0.013, 0.0),
    (8, 1, 0, +0.012, 0.0),
    (11, 0, 0, +0.011, 0.0),
    (5, 1, 0, +0.010, 0.0),
    (20, 0, 0, -0.010, 0.0),
)

# (d, m, f, coef, coef_t)   -- 17 terminos
APOGEO_PARALAJE = (
    # Columna izquierda
    (2, 0, 0, -9.147, 0.0),
    (1, 0, 0, -0.841, 0.0),
    (0, 0, 2, +0.697, 0.0),
    (0, 1, 0, -0.656, +0.0016),
    (4, 0, 0, +0.355, 0.0),
    (2, -1, 0, +0.159, 0.0),
    (1, 1, 0, +0.127, 0.0),
    (4, -1, 0, +0.065, 0.0),
    # Columna derecha
    (6, 0, 0, +0.052, 0.0),
    (2, 1, 0, +0.043, 0.0),
    (2, 0, 2, +0.031, 0.0),
    (2, 0, -2, -0.023, 0.0),
    (2, -2, 0, +0.022, 0.0),
    (2, 2, 0, +0.019, 0.0),
    (0, 2, 0, -0.016, 0.0),
    (6, -1, 0, +0.014, 0.0),
    (8, 0, 0, +0.010, 0.0),
)
