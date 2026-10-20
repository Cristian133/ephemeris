# Calculadora Solar — Plan Técnico

Estado: **etapas 1 (Sol) y 2 (Luna, eclipses, calendario y mareas teóricas) implementadas y verificadas.** Las secciones 3 a 6 describen lo construido; la 7, lo que sigue.

## 1. Decisiones tomadas

| Decisión | Elegido | Motivo |
|---|---|---|
| Backend | Python (FastAPI) | Ecosistema científico maduro (numpy, astropy, skyfield). Consistente con `satellite-tracker`. |
| Frontend | React + TypeScript + Vite | Ecosistema de gráficos amplio (Plotly.js/Recharts/D3). Consistente con `satellite-tracker`. |
| Motor de cálculo | Python + `numpy` para vectorizar rangos (año completo, grillas) | Las fórmulas son cerradas, no iterativas ni de alto costo — un core en Rust/C sería optimización prematura. Se revisita solo si el profiling muestra un cuello de botella real (candidato futuro: grillas globales de eclipses en etapa 2). |
| Infra dev | Docker Compose | Consistente con `satellite-tracker`. Sin Postgres/Redis por ahora: la etapa 1 es *stateless* (cálculo puro sin persistencia). Se suma si etapa 3 lo requiere (cache de datos meteorológicos). |
| Precisión astronómica | Método de baja precisión de Meeus (*Astronomical Algorithms* cap. 25, error < 0.01°) + ΔT, nutación corta y tiempo sidéreo aparente | Orto/ocaso con error < 4 s frente a astropy; VSOP87 añade complejidad de tablas sin beneficio práctico para el Sol. Para la Luna (etapa 2) la precisión necesaria es mayor. |
| Alcance punto 5 (potencia solar) | Modelo de cielo despejado de Ineichen y Perez (turbidez de Linke, altitud del lugar) con componentes directa y difusa; el panel suma además la reflejada por el suelo | Autocontenido, no depende de fuentes de datos externas ni adelanta la etapa 3. Resuelve el pendiente de la sección 10. |
| "Mareas" (etapa 2) | Fuerzas de marea teóricas (posición relativa Sol-Luna-Tierra) | Es astronomía, encaja en el motor ya construido. Las mareas oceánicas reales (altura de marea costera) son oceanografía aplicada — dominio distinto, fuera de alcance salvo que se redefina explícitamente más adelante. |
| Mobile | Pospuesto | Web responsive alcanza por ahora; se evalúa app nativa/PWA cuando la web esté funcional. |

## 2. Fuentes de referencia

Los libros están en `~/Documentos/Algoritmos Astronómicos/` (uso privado de referencia para implementar código propio, ver nota de copyright abajo). **No se distribuyen con el repositorio.**

Fuente primaria:

- `Astronomical Algorithms - Jean Meeus - 1998 - 2ed.pdf`
- `Mathematical Astronomy Morsels - Jean Meeus - 1997 - 1ed.pdf`
- `More Mathematical Astronomy Morsels - Jean Meeus - 2002 - 1ed.pdf`

Fuentes de respaldo, para lo que Meeus no cubre:

- `Explanatory Supplement to the Astronomical Almanac - P. Kenneth Seidelmann - 1992 - 1ed.pdf`: escalas de tiempo, ΔT, precesión y nutación, refracción.
- `Davis Vallado - Methods of Astrodynamics.pdf`: conversiones de tiempo, tiempo sidéreo, posición del Sol y la Luna; útil para validar la etapa 2.
- `Computer Programs for Sun and Moon Illuminance - P. M. Janiczek y J. A. DeYoung - 1987 - 1ed.pdf`: iluminancia (lux) del Sol, la Luna y el cielo, incluidos crepúsculos. Pendiente de usar (iluminancia en lux: crepúsculos, luz lunar).

Los modelos de irradiancia (Ineichen y Perez, Kasten y Young, Liu y Jordan) son de la literatura de ingeniería solar y no están en esos libros.

**Nota de copyright**: estos libros no son de dominio público (términos de vida+70 años vigentes). Los algoritmos/fórmulas en sí no son objeto de copyright; lo que no debe reproducirse textualmente en artefactos públicos (repo público, documentación publicada) es la prosa/tablas compiladas de los libros. Uso interno como referencia técnica: sin problema.

## 3. Estructura de carpetas

```
ephemeris/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app (CORS configurable, ver config.py)
│   │   ├── config.py               # variables de entorno (CORS_ORIGINS)
│   │   ├── solar/                  # motor de cálculo astronómico (puro, sin framework)
│   │   │   ├── time.py             # JD, calendario juliano/gregoriano, ΔT, TT, tiempo sidéreo
│   │   │   ├── nutation.py         # nutación en longitud y oblicuidad, ecuación de los equinoccios
│   │   │   ├── coordinates.py      # posición solar: L0, M, C, longitud verdadera, RA/dec
│   │   │   ├── horizontal.py       # ecuatorial -> horizontal (azimut/altitud)
│   │   │   ├── events.py           # orto, tránsito, ocaso; trayectoria; irradiación diaria
│   │   │   ├── refraction.py       # refracción atmosférica
│   │   │   ├── irradiance.py       # cielo despejado: DNI, DHI, GHI
│   │   │   ├── twilight.py         # crepúsculos, hora azul y dorada
│   │   │   ├── seasons.py          # equinoccios y solsticios
│   │   │   ├── panel.py            # orientación óptima de un panel fijo
│   │   │   ├── calendars.py        # Pascua, día de la semana, día del año (Meeus caps. 7-8)
│   │   │   ├── moon.py             # posición, paralaje, iluminación, salida/puesta (caps. 47, 48, 40, 15)
│   │   │   ├── phases.py           # fases principales de la Luna (cap. 49)
│   │   │   ├── apsides.py          # perigeo y apogeo (cap. 50)
│   │   │   ├── eclipses.py         # eclipses de Sol y de Luna (cap. 54)
│   │   │   ├── tides.py            # marea de equilibrio de Sol y Luna
│   │   │   └── *_terms.py          # tablas de coeficientes de Meeus (datos puros)
│   │   ├── api/                    # routers FastAPI
│   │   └── schemas/                # modelos Pydantic
│   └── tests/                      # tests del motor y de la API
└── frontend/                       # React + TypeScript + Vite (ESLint + Vitest)
```

`app/solar/` es el módulo clave: agnóstico de FastAPI, testeable de forma aislada, y es el que crece en las etapas 2 y 3 sin tocar el resto.

## 4. Motor de cálculo — Etapa 1

Todos los ángulos en grados salvo que se indique lo contrario; conversión a radianes solo en el borde de las funciones trigonométricas. Longitud positiva al este, azimut desde el Norte en sentido horario.

### 4.1 Tiempo y escalas (`time.py`, `nutation.py`)
- Fecha calendario -> Día Juliano (JD) -> siglos julianos desde J2000.0 (T).
- La app calcula en UT y convierte a hora local solo en la capa de presentación. Los `datetime` son gregorianos prolépticos; el calendario histórico de Meeus (juliano hasta 1582-10-04) está en `julian_day_from_calendar` / `calendar_from_julian_day`, que trabajan con tuplas para no mezclar calendarios (lo necesitarán la Pascua y el calendario de la etapa 2).
- **ΔT = TT - UT**: datos medidos IERS 1990-2026 interpolados, polinomios de Espenak y Meeus antes, y extrapolación empalmada después. La posición del Sol se evalúa en TT (`julian_century_tt`) y el ángulo horario en UT.
- **Tiempo sidéreo aparente** (`apparent_sidereal_time`): medio más ecuación de los equinoccios, con la nutación en su versión corta (Meeus cap. 22, ~0.5").

### 4.2 `coordinates.py` — posición solar (Meeus cap. 25, baja precisión)
- L0, M, e, ecuación del centro, longitud verdadera y aparente, oblicuidad, α y δ, radio vector.

### 4.3 `horizontal.py` — ecuatorial a horizontal (Meeus cap. 13)
- Ángulo horario, altitud y azimut. Base de la trayectoria y el mediodía.

### 4.4 `events.py` — orto, tránsito y ocaso (Meeus cap. 15)
- Altitud estándar h0 = -0.8333°.
- El cruce de una altitud se resuelve iterando sobre el **ángulo horario** (semiarco H0 con la declinación de cada instante), no por Newton sobre la altitud: es estable cuando el Sol apenas roza el umbral (días límite en latitudes altas, donde la versión anterior llegó a errar más de 15 minutos).
- **Día solar local:** el parámetro `date` es el día que va de una medianoche media local a la siguiente (0h UT menos longitud/15 h). Las series muestreadas (trayectoria, irradiancia, panel) parten de ahí y no de 0h UT; con 0h UT, a longitudes al este de ~+90° el amanecer quedaba fuera de la ventana y la energía diaria se subestimaba.

### 4.5 `refraction.py` — refracción (Meeus cap. 16)
- Sæmundsson (verdadera -> aparente) y Bennett (inversa), con corrección por presión y temperatura. Los endpoints `/sol/mediodia` y `/sol/trayectoria` aceptan `pressure_mbar` y `temperature_c`. El orto/ocaso sigue usando la altitud estándar -0.8333° (que ya incluye la refracción típica del horizonte).

### 4.6 `irradiance.py` — cielo despejado
- Masa de aire de Kasten y Young (1989), corregida por la presión según la altitud del lugar.
- Ineichen y Perez (2002): DNI, DHI y GHI en función de la turbidez de Linke y la altitud. Parámetros: `elevation_m`, `linke_turbidity`.
- `panel.py` suma sobre el plano inclinado la directa (coseno de incidencia), la difusa isótropa de Liu y Jordan y la reflejada por el suelo (`albedo`).
- Límites: cielo despejado sin nubes ni sombras, turbidez fija (no medida). Es una estimación del potencial solar, no un dimensionamiento fotovoltaico.

### 4.7 Verificación
- Ejemplos numéricos de Meeus (caps. 7, 12, 22, 25) y calendario/ΔT en `tests/solar/`.
- `tests/solar/test_reference.py`: orto/ocaso contra astropy (efemérides ERFA independientes) en 7 casos que incluyen longitudes al este de +150° y latitudes de 65°, más una propiedad (la altitud en el instante devuelto es la pedida) en latitudes de 60° a 70°.
- Medición puntual (10 ubicaciones x 7 fechas x 3 umbrales): error máximo de orto/ocaso 3.3 s; antes de los cambios, 5.5 s y, en días límite polares, de 16 minutos o más.

## 5. Endpoints — Etapas 1 y 2

| # | Feature | Endpoint | Módulos usados |
|---|---|---|---|
| 1 | Horas de sol en un día | `GET /sol/dia` | time, coordinates, events |
| 2 | Evolución anual | `GET /sol/anual` (vectorizado sobre el año, con caché) | events |
| 3 | Trayectoria del sol | `GET /sol/trayectoria` | horizontal, refraction |
| 4 | Mediodía solar e inclinación | `GET /sol/mediodia` | events, horizontal, refraction |
| 5 | Potencia por m2 | `GET /sol/irradiancia` | irradiance |
| 6 | Crepúsculos, hora azul y dorada | `GET /sol/crepusculos` | twilight |
| 7 | Equinoccios y solsticios | `GET /sol/estaciones` | seasons |
| 8 | Panel solar óptimo | `GET /sol/panel` (con caché) | panel |
| 9 | Luna: día, trayectoria, fases del año, perigeo y apogeo | `GET /luna/dia`, `/luna/trayectoria`, `/luna/fases`, `/luna/apsides` | moon, phases, apsides |
| 10 | Eclipses del año | `GET /eclipses/anio` | eclipses |
| 11 | Pascua | `GET /calendario/pascua` | calendars |
| 12 | Marea teórica del día | `GET /mareas/dia` | tides |

`/sol/anual` y `/sol/panel` cachean el resultado por ubicación (redondeada a 4 decimales) y parámetros.

## 6. Etapa 2 — Luna, eclipses, calendario y mareas (implementada)

### 6.1 Método de trabajo con los libros
Los libros de Meeus están escaneados (sin capa de texto). Las tablas de coeficientes se transcribieron de las imágenes a `app/solar/*_terms.py` (datos puros) y se validaron dos veces: una lectura visual independiente de cada tabla y la reproducción numérica de los ejemplos resueltos del propio libro, que detecta cualquier dígito mal copiado en los términos relevantes. Cada módulo se contrastó además con astropy.

### 6.2 Módulos y fuentes
| Módulo | Fuente | Qué hace |
|---|---|---|
| `moon.py` | Meeus caps. 47, 48, 40, 15 | Posición geocéntrica y aparente (60 + 60 términos), paralaje, fracción iluminada, ángulo de posición del limbo, salida/tránsito/puesta con h0 = 0.7275 π - 0.5667° |
| `phases.py` | cap. 49 | Nueva, cuartos y llena (25 términos + 14 planetarios), numeración de Brown, edad de la Luna |
| `apsides.py` | cap. 50 | Perigeo y apogeo, con distancia (desde la paralaje de la tabla 50.B) |
| `eclipses.py` | cap. 54 | Eclipses globales de Sol (tipo, gamma, magnitud) y de Luna (tipo, magnitudes, contactos) |
| `calendars.py` | caps. 7-8 | Pascua gregoriana y juliana, día de la semana, día del año |
| `tides.py` | teoría de equilibrio (Explanatory Supplement, Vallado) | Marea de equilibrio de la Luna y el Sol, extremos, ciclo vivas/muertas |

La salida/puesta de la Luna se resuelve explorando la altitud cada 10 minutos y afinando por bisección, en lugar de la iteración del cap. 15: es más robusta para un astro que se mueve ~13° por día y que algunos días no sale o no se pone dentro del día local.

### 6.3 Verificación (contra astropy y datos conocidos)
- Posición geocéntrica de la Luna: 0.5" en ascensión recta, 0.2" en declinación, 40 km en distancia (40 fechas entre 2000 y 2026). Reproduce el ejemplo 47.a del libro a la sexta cifra.
- Fases: error máximo 23 s (2023-2026); reproduce los ejemplos 49.a y 49.b.
- Salida/puesta de la Luna: altitud topocéntrica del centro de -0.837° en los instantes devueltos (el valor esperado con refracción y semidiámetro).
- Perigeo y apogeo: instante hasta 28 min (perigeo) y 18 min (apogeo) y distancia hasta 42 km frente a astropy, dentro de lo que declara el libro. El supermoon del 5/11/2025 sale a 356 832 km.
- Eclipses: los 16 eclipses de 2023 a 2026 coinciden en fecha, tipo y hora (menos de 3 min), incluidos el híbrido de abril de 2023 y el total de abril de 2024; los 4 eclipses lunares de 1991 se confirmaron con astropy; reproduce los 4 ejemplos del cap. 54 y los ejercicios del capítulo.
- Pascua: propiedad de que cae siempre domingo entre el 22/3 y el 25/4 para 1583-3999 (y domingo en el calendario juliano para 326-1582).

### 6.4 Límites conocidos
- **Eclipses solares:** solo condiciones globales. El libro excluye las circunstancias locales (horas de contacto, cobertura en una ciudad), que requieren elementos besselianos. Es la mejora natural siguiente. Cerca del límite de visibilidad (|gamma| ≈ 0.9972 o ≈ 1.5433 + u) el tipo puede ser incierto, como advierte el libro.
- **Perigeo:** el instante puede errar hasta ~30 minutos (la distancia casi no varía cerca del mínimo). En el ejemplo 50.a la suma impresa del libro difiere 50 s de la que dan sus propias tablas (verificado dos veces contra el escaneo): se toma como imprecisión del libro.
- **Mareas:** es la marea de equilibrio, no la altura real en una costa (la respuesta real depende de las cuencas, la profundidad y la resonancia). No incluye la elasticidad de la Tierra sólida.
- **Rango de años:** fases y apsides, 1000-3000 (el error crece lejos del presente); eclipses, 1800-2200; Pascua, 1583-9999.
- **Posición lunar:** la serie truncada del cap. 47 tiene ~10" en longitud; alcanza para todo lo anterior pero no para ocultaciones de estrellas ni eclipses solares locales de precisión.

## 7. Etapa 3 — meteorología

Fuera del alcance de los libros disponibles: requiere integración con fuentes de datos externas (ej. Open-Meteo, NASA POWER) para series históricas de lluvia/nubosidad. Es trabajo de integración de datos, no de cálculo astronómico — se planifica en detalle cuando se llegue a esa etapa.

## 8. Backlog de la etapa 1 (completado)

1. `time.py` + tests con casos de ejemplo verificados a mano/con el libro.
2. `coordinates.py` (posición solar) + tests contra ejemplos numéricos de Meeus cap. 25.
3. `events.py` (orto/tránsito/ocaso) → cierra el punto 1.
4. Endpoint + gráfica del punto 2 (vectorizado con numpy sobre el año).
5. `horizontal.py` → cierra puntos 3 y 4.
6. Gráfica polar del punto 3.
7. `refraction.py` (mejora de precisión sobre lo ya construido).
8. `irradiance.py` → cierra punto 5.
9. Revisión de estructura para confirmar que agregar etapa 2 no requiere tocar `app/solar/` existente, solo sumar módulos nuevos.

## 9. Convenciones de desarrollo

pre-commit (ruff, pytest, eslint), CI en push y pull request, Ruff para Python, ESLint 9 + typescript-eslint para el frontend, pytest y Vitest. Comentarios y mensajes en español, sin emojis.

## 10. Riesgos y pendientes

Resueltos en la etapa 1:
- Zona horaria: el motor es UT; el frontend convierte a la hora local del lugar. El parámetro `date` es el día solar local (sección 4.4).
- Modelo de irradiancia: Ineichen y Perez (sección 4.6).
- Ubicación: buscador de direcciones (Nominatim) con límite de uso respetado y coordenadas manuales.

Abiertos:
- La precisión del Sol (~3 s en orto/ocaso) y de la Luna (~10") alcanza para lo implementado; los eclipses solares locales y las ocultaciones necesitarían VSOP87, ELP-2000/82 completo y nutación completa (63 términos).
- ΔT más allá de 2026 es un pronóstico; conviene actualizar la tabla medida una vez al año.
- Dependencia de servicios externos en el frontend (Nominatim, Open-Meteo para la zona horaria): sin SLA; considerar un proxy en el backend si se publica.
- El modelo de cielo despejado no representa nubosidad (etapa 3).
- Las tablas de coeficientes de Meeus (`*_terms.py`) son datos numéricos transcriptos del libro, igual que la tabla 27.C de `seasons.py`. Los algoritmos y las fórmulas no están protegidos por derecho de autor, pero una tabla compilada podría considerarse una obra: si el repositorio se hace público, conviene evaluarlo (alternativa: regenerar las series desde una teoría de dominio público, por ejemplo VSOP87 y ELP-2000/82 de la IMCCE).
