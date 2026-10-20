"""Datos numericos para eclipses de Sol y de Luna.

Fuente: Jean Meeus, "Astronomical Algorithms", 2da ed. (1998), cap. 54
"Eclipses" (paginas 379-388 del libro), mas las formulas de los capitulos
49 (ecuaciones 49.1 a 49.7 y argumentos A1) y 47 (ecuacion 47.6, E) que el
cap. 54 invoca explicitamente. Solo datos puros; sin logica.

FORMATO DE LAS TABLAS DE TERMINOS PERIODICOS
--------------------------------------------
Cada termino es una tupla:

    (coeficiente, potencia_de_E, (cM, cMp, cF1, cA1, cOmega))

- coeficiente: float, con el signo del libro. En dias para
  TERMINOS_MAXIMO_*; en radios terrestres ecuatoriales para P, Q y u.
- potencia_de_E: 0, 1 o 2. El coeficiente se multiplica por E**potencia.
  (En el cap. 54 solo aparecen 0 y 1; el 2 existe en cap. 49, no aqui.)
- La tupla de 5 enteros son los multiplos de los argumentos, en este orden:
      cM     -> M   (anomalia media del Sol)
      cMp    -> M'  (anomalia media de la Luna)
      cF1    -> F1  (argumento de latitud corregido: F1 = F - 0.02665 sin(Omega))
      cA1    -> A1  (argumento planetario A1, en grados)
      cOmega -> Omega (longitud del nodo ascendente de la orbita lunar)
  El argumento del termino es cM*M + cMp*M' + cF1*F1 + cA1*A1 + cOmega*Omega.
- Cada termino se evalua con seno (TERMINOS_MAXIMO_*, TERMINOS_P) o con
  coseno (TERMINOS_Q, TERMINOS_U), segun indica el nombre de la tabla.
- Los terminos constantes de Q y u se dan aparte (Q_CONSTANTE, U_CONSTANTE).

Los polinomios (F, M, ...) se dan como tuplas de coeficientes en orden de
potencias crecientes (c0, c1, c2, ...), con variable k o T segun el nombre.
Angulos en grados; JDE en dias.
"""

# --- Orden de los argumentos en las tuplas de multiplos --------------------
ORDEN_ARGUMENTOS = ("M", "Mp", "F1", "A1", "Omega")

# --- Polinomios de los capitulos 49 y 47 (usados por el cap. 54) -----------
# JDE de la Luna nueva/llena media (49.1). Variable: k (en los coeficientes
# lineales) y T = k / 1236.85 (49.3) en los de T^2, T^3, T^4.
# JDE = c0 + c1*k + c2*T^2 + c3*T^3 + c4*T^4
JDE_MEDIA = (2451550.09766, 29.530588861, 0.00015437, -0.000000150, 0.00000000073)

# k aproximado (49.2): k = (anio_con_decimales - 2000) * K_POR_ANIO
K_POR_ANIO = 12.3685
# T = k / DIVISOR_T_SOBRE_K (49.3)
DIVISOR_T_SOBRE_K = 1236.85

# Excentricidad de la orbita terrestre (47.6): E = 1 + e1*T + e2*T^2
E_COEFICIENTES = (1.0, -0.002516, -0.0000074)

# Anomalia media del Sol (49.4): c0 + c1*k + c2*T^2 + c3*T^3
M_SOL = (2.5534, 29.10535670, -0.0000014, -0.00000011)
# Anomalia media de la Luna (49.5): c0 + c1*k + c2*T^2 + c3*T^3 + c4*T^4
M_LUNA = (201.5643, 385.81693528, 0.0107582, 0.00001238, -0.000000058)
# Argumento de latitud de la Luna (49.6): c0 + c1*k + c2*T^2 + c3*T^3 + c4*T^4
F_LUNA = (160.7108, 390.67050284, -0.0016118, -0.00000227, 0.000000011)
# Longitud del nodo ascendente (49.7): c0 + c1*k + c2*T^2 + c3*T^3
OMEGA_LUNA = (124.7746, -1.56375588, 0.0020672, 0.00000215)

# Pagina 380: F1 = F - F1_COEF_SIN_OMEGA * sin(Omega)
F1_COEF_SIN_OMEGA = 0.02665
# Pagina 380: A1 = c0 + c1*k + c2*T^2 (grados). Igual al A1 del cap. 49.
A1_COEFICIENTES = (299.77, 0.107408, -0.009173)

# --- Criterios de existencia de eclipse segun F (pagina 380) ---------------
# Si |F - multiplo_mas_cercano_de_180| < F_CIERTO_GRADOS: eclipse seguro.
F_CIERTO_GRADOS = 13.9
# Si la diferencia es > F_SIN_ECLIPSE_GRADOS: no hay eclipse.
F_SIN_ECLIPSE_GRADOS = 21.0
# Regla alternativa: no hay eclipse si |sin F| > SIN_F_MAX
SIN_F_MAX = 0.36
# Incremento de F por lunacion (grados)
F_POR_LUNACION = 30.6705

# --- Terminos para el instante del maximo (54.1), en dias ------------------
# Se suman al JDE de la Luna nueva/llena media (49.1). Todos con seno.
# Eclipses de SOL (Luna nueva, k entero):
TERMINOS_MAXIMO_SOL = (
    (-0.4075, 0, (0, 1, 0, 0, 0)),  # sin M'
    (+0.1721, 1, (1, 0, 0, 0, 0)),  # E sin M
    (+0.0161, 0, (0, 2, 0, 0, 0)),  # sin 2M'
    (-0.0097, 0, (0, 0, 2, 0, 0)),  # sin 2F1
    (+0.0073, 1, (-1, 1, 0, 0, 0)),  # E sin(M' - M)
    (-0.0050, 1, (1, 1, 0, 0, 0)),  # E sin(M' + M)
    (-0.0023, 0, (0, 1, -2, 0, 0)),  # sin(M' - 2F1)
    (+0.0021, 1, (2, 0, 0, 0, 0)),  # E sin 2M
    (+0.0012, 0, (0, 1, 2, 0, 0)),  # sin(M' + 2F1)
    (+0.0006, 1, (1, 2, 0, 0, 0)),  # E sin(2M' + M)
    (-0.0004, 0, (0, 3, 0, 0, 0)),  # sin 3M'
    (-0.0003, 1, (1, 0, 2, 0, 0)),  # E sin(M + 2F1)
    (+0.0003, 0, (0, 0, 0, 1, 0)),  # sin A1
    (-0.0002, 1, (1, 0, -2, 0, 0)),  # E sin(M - 2F1)
    (-0.0002, 1, (-1, 2, 0, 0, 0)),  # E sin(2M' - M)
    (-0.0002, 0, (0, 0, 0, 0, 1)),  # sin Omega
)

# Eclipses de LUNA (Luna llena, k = entero + 0.5): mismos terminos, pero los
# coeficientes de sin M' y de E sin M cambian a -0.4065 y +0.1727.
# (Pagina 380: "for lunar eclipses, change these constants to -0.4065 and +0.1727")
TERMINOS_MAXIMO_LUNA = (
    (-0.4065, 0, (0, 1, 0, 0, 0)),  # sin M'
    (+0.1727, 1, (1, 0, 0, 0, 0)),  # E sin M
    (+0.0161, 0, (0, 2, 0, 0, 0)),  # sin 2M'
    (-0.0097, 0, (0, 0, 2, 0, 0)),  # sin 2F1
    (+0.0073, 1, (-1, 1, 0, 0, 0)),  # E sin(M' - M)
    (-0.0050, 1, (1, 1, 0, 0, 0)),  # E sin(M' + M)
    (-0.0023, 0, (0, 1, -2, 0, 0)),  # sin(M' - 2F1)
    (+0.0021, 1, (2, 0, 0, 0, 0)),  # E sin 2M
    (+0.0012, 0, (0, 1, 2, 0, 0)),  # sin(M' + 2F1)
    (+0.0006, 1, (1, 2, 0, 0, 0)),  # E sin(2M' + M)
    (-0.0004, 0, (0, 3, 0, 0, 0)),  # sin 3M'
    (-0.0003, 1, (1, 0, 2, 0, 0)),  # E sin(M + 2F1)
    (+0.0003, 0, (0, 0, 0, 1, 0)),  # sin A1
    (-0.0002, 1, (1, 0, -2, 0, 0)),  # E sin(M - 2F1)
    (-0.0002, 1, (-1, 2, 0, 0, 0)),  # E sin(2M' - M)
    (-0.0002, 0, (0, 0, 0, 0, 1)),  # sin Omega
)

# --- Serie P (pagina 381), con seno ----------------------------------------
TERMINOS_P = (
    (+0.2070, 1, (1, 0, 0, 0, 0)),  # E sin M
    (+0.0024, 1, (2, 0, 0, 0, 0)),  # E sin 2M
    (-0.0392, 0, (0, 1, 0, 0, 0)),  # sin M'
    (+0.0116, 0, (0, 2, 0, 0, 0)),  # sin 2M'
    (-0.0073, 1, (1, 1, 0, 0, 0)),  # E sin(M' + M)
    (+0.0067, 1, (-1, 1, 0, 0, 0)),  # E sin(M' - M)
    (+0.0118, 0, (0, 0, 2, 0, 0)),  # sin 2F1
)

# --- Serie Q (pagina 381): Q = Q_CONSTANTE + suma de terminos con coseno ---
Q_CONSTANTE = +5.2207
TERMINOS_Q = (
    (-0.0048, 1, (1, 0, 0, 0, 0)),  # E cos M
    (+0.0020, 1, (2, 0, 0, 0, 0)),  # E cos 2M
    (-0.3299, 0, (0, 1, 0, 0, 0)),  # cos M'
    (-0.0060, 1, (1, 1, 0, 0, 0)),  # E cos(M' + M)
    (+0.0041, 1, (-1, 1, 0, 0, 0)),  # E cos(M' - M)
)

# --- Serie u (pagina 381): u = U_CONSTANTE + suma de terminos con coseno ---
U_CONSTANTE = +0.0059
TERMINOS_U = (
    (+0.0046, 1, (1, 0, 0, 0, 0)),  # E cos M
    (-0.0182, 0, (0, 1, 0, 0, 0)),  # cos M'
    (+0.0004, 0, (0, 2, 0, 0, 0)),  # cos 2M'
    (-0.0005, 0, (1, 1, 0, 0, 0)),  # cos(M + M')
)

# gamma = (P cos F1 + Q sin F1) * (1 - GAMMA_FACTOR_W * W),  W = |cos F1|
GAMMA_FACTOR_W = 0.0048

# --- Constantes de eclipses de Sol (paginas 381-382) -----------------------
# Eclipse central si |gamma| < GAMMA_CENTRAL_MAX (el libro avisa que varia
# entre 0.9970 y 0.9974 segun el eclipse; pagina 387).
GAMMA_CENTRAL_MAX = 0.9972
# Radio de la penumbra en el plano fundamental: u + PENUMBRA_SOL_BASE
PENUMBRA_SOL_BASE = 0.5461
# No hay eclipse visible si |gamma| > LIMITE_SOL_BASE + u
LIMITE_SOL_BASE = 1.5433
# Eclipses totales/anulares no centrales: GAMMA_CENTRAL_MAX < |gamma| < 1.0260
GAMMA_NO_CENTRAL_MAX = 1.0260
# Tipo de eclipse central: u < 0 total; u > U_ANULAR_MIN anular;
# 0 <= u <= U_ANULAR_MIN ambiguo, se resuelve con omega.
U_ANULAR_MIN = 0.0047
# omega = OMEGA_COEF * sqrt(1 - gamma^2); si u < omega -> anular-total
# (hibrido); si no, anular.
OMEGA_COEF = 0.00464
# Magnitud de eclipse parcial (54.2):
#   (LIMITE_SOL_BASE + u - |gamma|) / (PENUMBRA_SOL_BASE + 2u)
# Margen de busqueda recomendado (pagina 387): usar 1.000 o 1.005 en vez de
# GAMMA_CENTRAL_MAX para no omitir eclipses centrales.
GAMMA_CENTRAL_BUSQUEDA = (1.000, 1.005)

# --- Constantes de eclipses de Luna (paginas 382-383) ----------------------
# Dos juegos de constantes: la "regla francesa" (por defecto, con la
# atmosfera terrestre segun Connaissance des Temps) y la regla tradicional
# (radios teoricos aumentados 1/50).
#
# Claves:
#   rho_base   : radio de la penumbra   rho   = rho_base + u
#   sigma_base : radio de la umbra      sigma = sigma_base - u
#   mag_pen    : numerador magnitud penumbral  (mag_pen + u - |gamma|) / mag_den
#   mag_umb    : numerador magnitud umbral     (mag_umb - u - |gamma|) / mag_den
#   p_base     : p = p_base - u   (semiduracion fase parcial en umbra)
#   t_base     : t = t_base - u   (semiduracion fase total)
#   h_base     : h = h_base + u   (semiduracion fase parcial en penumbra)
#   mag_den    : denominador de las magnitudes (0.5450)
#   n_const, n_cos : n = n_const + n_cos * cos(M')
CONSTANTES_LUNA_REGLA_FRANCESA = {
    "rho_base": 1.2848,
    "sigma_base": 0.7403,
    "mag_pen": 1.5573,
    "mag_umb": 1.0128,
    "mag_den": 0.5450,
    "p_base": 1.0128,
    "t_base": 0.4678,
    "h_base": 1.5573,
    "n_const": 0.5458,
    "n_cos": 0.0400,
}
# Regla tradicional (1/50): pagina 383 "replace 1.2848 by 1.2985, 0.7403 by
# 0.7432, 1.5573 by 1.5710, 1.0128 by 1.0157, 0.4678 by 0.4707".
CONSTANTES_LUNA_REGLA_TRADICIONAL = {
    "rho_base": 1.2985,
    "sigma_base": 0.7432,
    "mag_pen": 1.5710,
    "mag_umb": 1.0157,
    "mag_den": 0.5450,
    "p_base": 1.0157,
    "t_base": 0.4707,
    "h_base": 1.5710,
    "n_const": 0.5458,
    "n_cos": 0.0400,
}

# Aplastamiento de la umbra terrestre mencionado en el libro (pagina 384,
# informativo): Meeus 1/214; Soulsby (observaciones 1974-1989) 1/102.
APLASTAMIENTO_UMBRA_MEEUS = 1.0 / 214.0
APLASTAMIENTO_UMBRA_SOULSBY = 1.0 / 102.0
