"""Datos puros para las fases de la Luna (Meeus, Astronomical Algorithms,
2da ed., cap. 49 "Phases of the Moon", pp. 349-352 del libro).

Sin logica: solo constantes y tablas transcriptas.

FORMATO DE LOS POLINOMIOS
-------------------------
Cada polinomio es una tupla de coeficientes en orden creciente de potencia
de T (o de k para el termino lineal), es decir (c0, c1, c2, c3, c4):

    valor = c0 + c1*k + c2*T**2 + c3*T**3 + c4*T**4

OJO: el segundo elemento multiplica a k (no a T) y los siguientes a T^2,
T^3, T^4. No hay termino en T^1. Un coeficiente ausente en el libro se
representa con 0.0 para mantener la forma de 5 elementos.

FORMATO DE LAS TABLAS PERIODICAS
--------------------------------
Los argumentos se expresan como tupla de multiplos enteros
(m, mp, f, omega):

    argumento = m*M + mp*M' + f*F + omega*Omega

donde M = anomalia media del Sol, M' = anomalia media de la Luna,
F = argumento de latitud de la Luna, Omega = longitud del nodo ascendente.

NEW_FULL_MOON_TERMS: tuplas (argumento, coef_nueva, coef_llena, pot_E).
QUARTER_TERMS:       tuplas (argumento, coef, pot_E)  (cuartos creciente
                     y menguante comparten coeficientes).
Cada termino se suma como  coef * E**pot_E * sin(argumento)  (en dias).
Las filas conservan el orden del libro.

ADDITIONAL_CORRECTIONS: tuplas (angulo_base, vel_k, coef_T2, coef) para
A1..A14; A_i = angulo_base + vel_k*k + coef_T2*T**2 (coef_T2 solo no nulo
en A1). El termino aditivo es coef * sin(A_i) (en dias), comun a todas las
fases.
"""

# --- Fase media (ec. 49.1) ---------------------------------------------
# JDE = 2451550.09766 + 29.530588861*k + 0.00015437*T^2
#       - 0.000000150*T^3 + 0.00000000073*T^4
# k entero: Luna nueva; +0.25 cuarto creciente; +0.50 llena; +0.75 menguante.
JDE_MEDIO = (2451550.09766, 29.530588861, 0.00015437, -0.000000150, 0.00000000073)

# Ec. 49.2: k aproximado = (anio - 2000) * 12.3685
K_POR_ANIO = 12.3685
ANIO_BASE_K = 2000.0

# Ec. 49.3: T = k / 1236.85 (siglos julianos desde J2000.0)
K_POR_SIGLO = 1236.85

# Ec. 47.6: E = 1 - 0.002516*T - 0.0000074*T^2 (excentricidad de la
# orbita terrestre; ver cap. 47, no esta en el cap. 49).
E_COEF = (1.0, -0.002516, -0.0000074)

# Ec. 49.4: anomalia media del Sol, M
# M = 2.5534 + 29.10535670*k - 0.0000014*T^2 - 0.00000011*T^3
M_COEF = (2.5534, 29.10535670, -0.0000014, -0.00000011, 0.0)

# Ec. 49.5: anomalia media de la Luna, M'
# M' = 201.5643 + 385.81693528*k + 0.0107582*T^2 + 0.00001238*T^3
#      - 0.000000058*T^4
MP_COEF = (201.5643, 385.81693528, 0.0107582, 0.00001238, -0.000000058)

# Ec. 49.6: argumento de latitud de la Luna, F
# F = 160.7108 + 390.67050284*k - 0.0016118*T^2 - 0.00000227*T^3
#     + 0.000000011*T^4
F_COEF = (160.7108, 390.67050284, -0.0016118, -0.00000227, 0.000000011)

# Ec. 49.7: longitud del nodo ascendente de la orbita lunar, Omega
# Omega = 124.7746 - 1.56375588*k + 0.0020672*T^2 + 0.00000215*T^3
OMEGA_COEF = (124.7746, -1.56375588, 0.0020672, 0.00000215, 0.0)

# --- Terminos periodicos de Luna nueva y Luna llena (p. 351) -----------
# (argumento (M, M', F, Omega), coef_nueva, coef_llena, potencia_de_E)
NEW_FULL_MOON_TERMS = (
    ((0, 1, 0, 0), -0.40720, -0.40614, 0),  # M'
    ((1, 0, 0, 0), +0.17241, +0.17302, 1),  # M
    ((0, 2, 0, 0), +0.01608, +0.01614, 0),  # 2M'
    ((0, 0, 2, 0), +0.01039, +0.01043, 0),  # 2F
    ((-1, 1, 0, 0), +0.00739, +0.00734, 1),  # M' - M
    ((1, 1, 0, 0), -0.00514, -0.00515, 1),  # M' + M
    ((2, 0, 0, 0), +0.00208, +0.00209, 2),  # 2M
    ((0, 1, -2, 0), -0.00111, -0.00111, 0),  # M' - 2F
    ((0, 1, 2, 0), -0.00057, -0.00057, 0),  # M' + 2F
    ((1, 2, 0, 0), +0.00056, +0.00056, 1),  # 2M' + M
    ((0, 3, 0, 0), -0.00042, -0.00042, 0),  # 3M'
    ((1, 0, 2, 0), +0.00042, +0.00042, 1),  # M + 2F
    ((1, 0, -2, 0), +0.00038, +0.00038, 1),  # M - 2F
    ((-1, 2, 0, 0), -0.00024, -0.00024, 1),  # 2M' - M
    ((0, 0, 0, 1), -0.00017, -0.00017, 0),  # Omega
    ((2, 1, 0, 0), -0.00007, -0.00007, 0),  # M' + 2M
    ((0, 2, -2, 0), +0.00004, +0.00004, 0),  # 2M' - 2F
    ((3, 0, 0, 0), +0.00004, +0.00004, 0),  # 3M
    ((1, 1, -2, 0), +0.00003, +0.00003, 0),  # M' + M - 2F
    ((0, 2, 2, 0), +0.00003, +0.00003, 0),  # 2M' + 2F
    ((1, 1, 2, 0), -0.00003, -0.00003, 0),  # M' + M + 2F
    ((-1, 1, 2, 0), +0.00003, +0.00003, 0),  # M' - M + 2F
    ((-1, 1, -2, 0), -0.00002, -0.00002, 0),  # M' - M - 2F
    ((1, 3, 0, 0), -0.00002, -0.00002, 0),  # 3M' + M
    ((0, 4, 0, 0), +0.00002, +0.00002, 0),  # 4M'
)

# --- Terminos periodicos de cuartos creciente y menguante (p. 352) -----
# (argumento (M, M', F, Omega), coef, potencia_de_E)
QUARTER_TERMS = (
    ((0, 1, 0, 0), -0.62801, 0),  # M'
    ((1, 0, 0, 0), +0.17172, 1),  # M
    ((1, 1, 0, 0), -0.01183, 1),  # M' + M
    ((0, 2, 0, 0), +0.00862, 0),  # 2M'
    ((0, 0, 2, 0), +0.00804, 0),  # 2F
    ((-1, 1, 0, 0), +0.00454, 1),  # M' - M
    ((2, 0, 0, 0), +0.00204, 2),  # 2M
    ((0, 1, -2, 0), -0.00180, 0),  # M' - 2F
    ((0, 1, 2, 0), -0.00070, 0),  # M' + 2F
    ((0, 3, 0, 0), -0.00040, 0),  # 3M'
    ((-1, 2, 0, 0), -0.00034, 1),  # 2M' - M
    ((1, 0, 2, 0), +0.00032, 1),  # M + 2F
    ((1, 0, -2, 0), +0.00032, 1),  # M - 2F
    ((2, 1, 0, 0), -0.00028, 2),  # M' + 2M
    ((1, 2, 0, 0), +0.00027, 1),  # 2M' + M
    ((0, 0, 0, 1), -0.00017, 0),  # Omega
    ((-1, 1, -2, 0), -0.00005, 0),  # M' - M - 2F
    ((0, 2, 2, 0), +0.00004, 0),  # 2M' + 2F
    ((1, 1, 2, 0), -0.00004, 0),  # M' + M + 2F
    ((-2, 1, 0, 0), +0.00004, 0),  # M' - 2M
    ((1, 1, -2, 0), +0.00003, 0),  # M' + M - 2F
    ((3, 0, 0, 0), +0.00003, 0),  # 3M
    ((0, 2, -2, 0), +0.00002, 0),  # 2M' - 2F
    ((-1, 1, 2, 0), +0.00002, 0),  # M' - M + 2F
    ((1, 3, 0, 0), -0.00002, 0),  # 3M' + M
)

# Correccion W solo para los cuartos (p. 352):
# W = 0.00306 - 0.00038*E*cos(M) + 0.00026*cos(M') - 0.00002*cos(M' - M)
#     + 0.00002*cos(M' + M) + 0.00002*cos(2F)
# Cuarto creciente: +W; cuarto menguante: -W.
# Formato: (constante, ((coef, pot_E, (M, M', F, Omega)), ...)); cada
# elemento suma coef * E**pot_E * cos(argumento).
W_CONSTANTE = 0.00306
W_TERMS = (
    (-0.00038, 1, (1, 0, 0, 0)),  # E cos M
    (+0.00026, 0, (0, 1, 0, 0)),  # cos M'
    (-0.00002, 0, (-1, 1, 0, 0)),  # cos (M' - M)
    (+0.00002, 0, (1, 1, 0, 0)),  # cos (M' + M)
    (+0.00002, 0, (0, 0, 2, 0)),  # cos 2F
)

# --- Correcciones aditivas, comunes a todas las fases (p. 351-352) -----
# (angulo_base_grados, vel_por_k_grados, coef_T2, coef_dias)
# A_i = angulo_base + vel_por_k*k + coef_T2*T^2 ; correccion = coef*sin(A_i)
ADDITIONAL_CORRECTIONS = (
    (299.77, 0.107408, -0.009173, 0.000325),  # A1
    (251.88, 0.016321, 0.0, 0.000165),  # A2
    (251.83, 26.651886, 0.0, 0.000164),  # A3
    (349.42, 36.412478, 0.0, 0.000126),  # A4
    (84.66, 18.206239, 0.0, 0.000110),  # A5
    (141.74, 53.303771, 0.0, 0.000062),  # A6
    (207.14, 2.453732, 0.0, 0.000060),  # A7
    (154.84, 7.306860, 0.0, 0.000056),  # A8
    (34.52, 27.261239, 0.0, 0.000047),  # A9
    (207.19, 0.121824, 0.0, 0.000042),  # A10
    (291.34, 1.844379, 0.0, 0.000040),  # A11
    (161.72, 24.198154, 0.0, 0.000037),  # A12
    (239.56, 25.513099, 0.0, 0.000035),  # A13
    (331.55, 3.592518, 0.0, 0.000023),  # A14
)
