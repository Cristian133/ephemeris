"""Motor de cálculo astronómico: puro, sin dependencias de FastAPI.

Módulos (ver docs/plan_tecnico.md, sección 4):

- time.py: Día Juliano, calendario juliano/gregoriano, ΔT, TT, tiempo
  sidéreo medio y aparente. Hecho.
- nutation.py: nutación en longitud y oblicuidad (Meeus, cap. 22, versión
  corta). Hecho.
- coordinates.py: posición solar (Meeus, cap. 25, método de baja precisión).
  Hecho.
- horizontal.py: transformación ecuatorial -> horizontal (azimut/altitud).
  Hecho.
- events.py: orto, tránsito y ocaso (Meeus, cap. 15). Hecho.
- refraction.py: refracción atmosférica (Meeus, cap. 16: Sæmundsson y
  Bennett). Hecho.
- irradiance.py: irradiancia de cielo despejado (fuente de respaldo, no
  Meeus; Kasten-Young + Ineichen-Perez: directa, difusa y global). Hecho.
- seasons.py: equinoccios y solsticios (Meeus, cap. 27). Hecho.
- twilight.py: crepúsculos, hora azul y hora dorada (cruces de altitud sobre
  events.py). Hecho.
- panel.py: inclinación y orientación óptimas de un panel fijo (directa,
  difusa y reflejada; usa irradiance.py). Hecho.
- calendars.py: Pascua, día de la semana y día del año (Meeus, caps. 7-8).
  Hecho.
- moon.py: posición de la Luna, paralaje, iluminación, salida y puesta
  (Meeus, caps. 47, 48, 40 y 15). Hecho.
- phases.py: fases principales de la Luna (Meeus, cap. 49). Hecho.
- apsides.py: perigeo y apogeo (Meeus, cap. 50). Hecho.
- eclipses.py: eclipses de Sol y de Luna, condiciones globales (Meeus,
  cap. 54). Hecho.
- tides.py: marea de equilibrio del Sol y la Luna. Hecho.
- *_terms.py: tablas de coeficientes de Meeus, solo datos.
"""
