# Ephemeris — Plan Técnico

Estado: **etapas 1 (Sol) y 2 (Luna, eclipses, calendario y mareas teóricas) implementadas y verificadas; etapa 3 (meteorología) implementada (sección 7).** Las secciones 3 a 6 describen lo construido; la 7, lo que sigue.

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

## 7. Etapa 3 — meteorología (implementada)

Datos de la API histórica de Open-Meteo (reanálisis ERA5, desde 1940), consumidos desde el backend. Es de uso personal, así que el caché es un archivo SQLite (`METEO_DB_PATH`) y no hay servicios nuevos en Docker Compose.

### 7.1 Estructura (`backend/app/meteo/`)
- `grid.py`: celdas de 0.25° (la resolución nativa de ERA5); se consulta y se guarda por celda, no por punto.
- `client.py`: cliente HTTP con reintentos y espera creciente ante 429 y 5xx. Pide `timezone=auto`: cada fila es un día local del lugar.
- `store.py` y `service.py`: caché por celda y año completo, más la altitud de la celda; solo se piden los tramos de años que faltan. Solo admite años ya terminados (el año en curso está incompleto y ERA5 tiene unos días de demora).
- `aggregate.py`: tabla año × mes. La suma exige el mes completo y sin huecos; la media tolera huecos.
- `rain.py`: estadísticas de lluvia. Día de lluvia = 1 mm o más (criterio de la OMM); un año entra en las cifras anuales solo con sus 12 meses completos.
- `sky.py`: nubosidad (día despejado: hasta 20 % de nubes; cubierto: desde 80 %) y horas de sol. La insolación relativa es la media de horas de sol sobre la duración astronómica del día, que sale de `app.solar.events` para el centro de la celda y un año de referencia (la duración casi no cambia entre años). En un día polar cuenta 24 h o 0 h; sin sol posible, la insolación es `None`. `estimated_sunshine_statistics` estima las horas de sol desde la radiación con la relación de Ångström-Prescott (kt = a + b·n/N) con a = 0.27 y b = 0.51, ajustados a veinte estaciones de Argentina, España, Japón y Hong Kong (los de FAO-56, a = 0.25 y b = 0.50, quedan como referencia en `FAO_ANGSTROM_*`), porque la duración de sol efectivo del reanálisis sobreestima mucho (ver 7.3). La radiación extraterrestre de cada día sale de `app.solar.insolation.extraterrestrial_daily_kwh`.
- `radiation.py`: radiación global horizontal real (onda corta del reanálisis, en kWh/m²) frente a la de cielo despejado, e índice de claridad (real / despejado). La energía de cielo despejado de cada día del año sale de `app.solar.insolation` (vectorizado, misma cadena que `panel.py`) para el centro de la celda, con la altitud y la turbidez de Linke indicadas. `estimate_panel_real_sky` aplica a la energía mensual del panel el índice de claridad de cada mes.
- Las estadísticas comunes (media, mediana, percentiles 10 y 90 entre años) viven en `aggregate.py`.

### 7.2 Endpoints y páginas
| Fase | Endpoint | Estado |
|---|---|---|
| 2 | `GET /meteo/lluvia` (`first_year`, `last_year`; por defecto 1991-2020) y página Lluvia | implementada |
| 3 | `GET /meteo/nubosidad` y `GET /meteo/horas-sol` (con la versión del modelo y la estimada desde la radiación), con las páginas Nubosidad y Sol real | implementada; horas de sol y lluvia contrastadas con veinte estaciones y la nubosidad con una (7.3) |
| 4 | `GET /meteo/irradiancia-real` (más `elevation_m`, `linke_turbidity` y `albedo`; sin `elevation_m` usa la altitud de la celda) y página Radiación real | implementada |

### 7.3 Verificación y límites
- El motor se prueba con series sintéticas de resultado calculable a mano y con respuestas simuladas de la fuente; no hay tests que dependan de la red.
- **Contraste con veinte estaciones medidas** (`backend/scripts/validar_estaciones.py`, período 1991-2020; entre paréntesis la diferencia con lo medido; las horas de sol son el total anual). Argentina y Madrid (`--ajustar` y sin opciones):

  | Estación | Lluvia medida / ERA5 (mm) | Sol medido (h) | Modelo ERA5 | Estimado, FAO-56 | Estimado, calibrado |
  |---|---|---|---|---|---|
  | Buenos Aires, Obs. Central | 1258 / 1071 (-15 %) | 2384 | 3498 (+47 %) | 2752 (+15 %) | 2524 (+6 %) |
  | Córdoba, Observatorio | 816 / 904 (+11 %) | 2562 | 3655 (+43 %) | 2814 (+10 %) | 2585 (+1 %) |
  | Madrid, Retiro (AEMET) | 416 / 408 (-2 %) | 2744 | 3783 (+38 %) | 3096 (+13 %) | 2860 (+4 %) |
  | Mendoza, Aeropuerto | 238 / 561 (+136 %) | 2976 | 3851 (+29 %) | 3289 (+11 %) | 3051 (+3 %) |
  | Tucumán | 1010 / 1181 (+17 %) | 2250 | 3410 (+52 %) | 2294 (+2 %) | 2076 (-8 %) |
  | Ushuaia, Aeropuerto | 458 / 843 (+84 %) | 1404 | 2985 (+113 %) | 2015 (+44 %) | 1802 (+28 %) |
  | Salta, Aeropuerto | 738 / 2240 (+203 %) | 2287 | 3708 (+62 %) | 2586 (+13 %) | 2362 (+3 %) |
  | Bariloche, Aeropuerto | 812 / 1018 (+25 %) | 2558 | 3535 (+38 %) | 2974 (+16 %) | 2743 (+7 %) |

  Japón (JMA) y Hong Kong (HKO) (`--asia`):

  | Estación | Lluvia medida / ERA5 (mm) | Sol medido (h) | Modelo ERA5 | Estimado, FAO-56 | Estimado, calibrado |
  |---|---|---|---|---|---|
  | Sapporo | 1146 / 1191 (+4 %) | 1718 | 3144 (+83 %) | 2227 (+30 %) | 2009 (+17 %) |
  | Sendai | 1277 / 1342 (+5 %) | 1837 | 3026 (+65 %) | 2001 (+9 %) | 1788 (-3 %) |
  | Niigata | 1846 / 1727 (-6 %) | 1643 | 3031 (+84 %) | 1941 (+18 %) | 1728 (+5 %) |
  | Nagoya | 1579 / 1524 (-3 %) | 2140 | 3188 (+49 %) | 2222 (+4 %) | 2004 (-6 %) |
  | Tokio | 1598 / 1458 (-9 %) | 1927 | 2987 (+55 %) | 1880 (-2 %) | 1669 (-13 %) |
  | Hiroshima | 1572 / 1569 (0 %) | 2033 | 3163 (+56 %) | 2072 (+2 %) | 1857 (-9 %) |
  | Osaka | 1338 / 1459 (+9 %) | 2049 | 3201 (+56 %) | 2134 (+4 %) | 1918 (-6 %) |
  | Takamatsu | 1150 / 1460 (+27 %) | 2048 | 3240 (+58 %) | 2138 (+4 %) | 1921 (-6 %) |
  | Fukuoka | 1687 / 1749 (+4 %) | 1889 | 2959 (+57 %) | 1886 (0 %) | 1676 (-11 %) |
  | Kagoshima | 2435 / 2210 (-9 %) | 1952 | 2988 (+53 %) | 1881 (-4 %) | 1671 (-14 %) |
  | Naha | 2161 / 1756 (-19 %) | 1727 | 3154 (+83 %) | 2081 (+21 %) | 1867 (+8 %) |
  | Hong Kong, King's Park | 2431 / 1750 (-28 %) | 1829 | 3178 (+74 %) | 1962 (+7 %) | 1750 (-4 %) |

- **Fuentes de la referencia, con cautela.** Argentina y Madrid: tablas climáticas de Wikipedia, que citan al SMN y a la AEMET (no se pudo leer el portal del SMN); son secundarias y tienen problemas conocidos: los períodos de las horas de sol no coinciden (SMN 1991-2020 en Buenos Aires, Córdoba y Mendoza; solo 1991-2000 en Tucumán y Salta; OMM 1981-2010 en Bariloche; AEMET 1981-2010 en Madrid; Ushuaia cita 1901-1990 para el porcentaje de sol); Mendoza tiene dos estaciones en la ciudad y el Observatorio da 2636 h, un 13 % menos que el Aeropuerto; en Bariloche la suma mensual (2558 h) no coincide con el total que da la página (2595 h); la página de Córdoba avisa de texto sin verificar; y las horas de sol de Tucumán tienen julio por encima de junio, que llama la atención. Japón y Hong Kong salen directamente de las tablas de normales 1991-2020 de la JMA y del HKO (fuentes oficiales y primarias), pero las coordenadas de las ciudades son aproximadas y en Hong Kong la nubosidad se observa en el Observatorio y la radiación y el sol se miden en King's Park, a pocos kilómetros. Antes de citar las cifras de Argentina y Madrid conviene cotejarlas con las normales oficiales.
- **Lluvia: no sirve en terreno complicado ni en monzón.** En ciudades llanas el total anual quedó entre -15 % y +17 % (Argentina y España) y, en la mayoría de las japonesas, entre -9 % y +9 %. Pero en zonas montañosas, áridas o subpolares sobreestima mucho: Mendoza +136 %, Salta +203 %, Ushuaia +84 %, Bariloche +25 % (la celda de ~25 km promedia la montaña con el valle); y en zonas de monzón y tifones subestima: Hong Kong -28 %, Naha -19 %. En Japón el error medio absoluto fue de 10 % (sesgo -2 %); Takamatsu +27 % es la excepción llana. No se calibra: el error cambia de signo y de tamaño según el relieve y el clima. Una conclusión anterior de este documento, que el error anual estaba entre -15 % y +11 % sin sentido fijo, se había sacado de tres ciudades llanas y no se sostiene.
- **Horas de sol: el modelo del reanálisis sobreestima 29-84 %** en 19 de las 20 estaciones y +113 % en Ushuaia (`sunshine_duration` es un valor modelado, no una medición). La estimación desde la radiación, que el reanálisis reproduce mejor, con los coeficientes de FAO-56 (a = 0.25, b = 0.50) lo reduce, pero con sesgo según la región: +15 % de media en Argentina y Madrid, +8 % en Asia, con valores de -4 % (Kagoshima) a +44 % (Ushuaia).
- **Coeficientes calibrados (a = 0.27, b = 0.51), con una corrección importante.** Una primera calibración con las ocho estaciones de Argentina y Madrid (a = 0.29, b = 0.49) daba 7 % de error anual en validación cruzada, pero **no se transfirió a Asia**: con las doce estaciones de Japón y Hong Kong como prueba fuera de muestra subestimó 11 % de media (hasta -20 % en Kagoshima y -19 % en Tokio) y su error medio (11 a 12 % según cómo se calcule) fue peor que el de FAO-56 (9 %). Al revés tampoco: un ajuste hecho solo con Asia (a = 0.31, b = 0.40) sobreestima 16 % en Argentina y Madrid. La relación entre claridad y fracción de sol cambia con el clima: en Asia el índice de claridad medio es más bajo (0.48 contra 0.555) para una fracción de sol medida parecida. Por eso se re-ajustó con las veinte estaciones (96 + 144 puntos mensuales; `--ajustar`): a = 0.272, b = 0.506, con a + b = 0.78, la suma clásica de Ångström; se adoptan a = 0.27 y b = 0.51. En validación cruzada (cada estación queda fuera del ajuste) el error anual medio es de 9.0 % (Argentina y Madrid 8.5 %, Asia 9.3 %) y el sesgo medio de +0.3 %, contra 11.4 % y +10.8 % con FAO-56. Es una mejora moderada sobre FAO-56 y el sesgo regional no desaparece: en las ciudades japonesas la estimación queda por debajo (Tokio -13 %, Kagoshima -14 %, Fukuoka -11 %) y en Argentina por encima (Buenos Aires +6 %, Bariloche +7 %). Los peores casos son Ushuaia (+28 %, subpolar y con referencia antigua) y Sapporo (+17 %). No hay estaciones de trópico húmedo continental, desierto ni latitudes altas del norte. Volver a los de FAO-56 es cambiar dos constantes en `app/meteo/sky.py`.
- **Nubosidad: contrastada con una sola estación (Hong Kong).** ERA5 da una nubosidad anual de 64 % contra 68 % medido en el Observatorio (-4 puntos), con un error medio absoluto mensual de 6 puntos. El sesgo es estacional: de octubre a enero ERA5 queda 11 a 14 puntos por debajo (44-54 % contra 57-62 %) y en junio 7 puntos por encima (84 % contra 77 %). La referencia es una observación visual y ERA5 una fracción modelada, así que no son exactamente la misma magnitud. Con una sola estación, de clima de monzón, no se puede generalizar.
- **Radiación real: contrastada con una red de piranómetros, en la Pampa Húmeda.** La red solarimétrica de GERSolar (UNLu) e INTA mide con solarímetros de primera calidad (Kipp & Zonen y Eppley, calibrados cada dos años); su atlas preliminar (2010-2018, diez estaciones) publica la distribución de los días según el índice de claridad kt (irradiación diaria sobre extraterrestre). Con `scripts/validar_estaciones.py --radiacion`, la de ERA5 en seis puntos de la zona (Luján, Pergamino, Paraná, Rafaela, Manfredi y Anguil, con coordenadas aproximadas) queda a menos de 3.7 puntos porcentuales de la medida en todas las clases:
- **Radiación real: en Hong Kong ERA5 sobreestima 19 %.** Con las normales del HKO (King's Park, 1991-2020) la radiación global media anual de ERA5 es de 15.71 MJ/m² por día contra 13.23 medido (+19 %), con un error medio absoluto mensual de 19 %; el sesgo va de +11 % (diciembre) a +34 % (marzo) y es positivo todos los meses. Es un clima de monzón y con aire con aerosoles, el caso donde un reanálisis sobreestima más. Junto con el +6 % de Buenos Aires y la buena coincidencia de la distribución de claridad en la Pampa Húmeda, indica que el sesgo depende de la región: razonable en llanura templada, alto en monzón. Afecta la radiación real, el índice de claridad y la estimación del panel.

  | Días con kt | < 0.3 (cubierto) | 0.3-0.55 | 0.55-0.7 | >= 0.7 (despejado) |
  |---|---|---|---|---|
  | Medido (red GERSolar, toda la red) | 15 % | 24 % | 35 % | 26 % |
  | ERA5, Luján | 12.8 % | 23.9 % | 36.8 % | 26.5 % |
  | ERA5, los seis puntos juntos | 11.3 % | 23.1 % | 37.1 % | 28.5 % |

  ERA5 tiene algo menos de días cubiertos (11 % contra 15 %), lo que explica que su radiación media salga algo alta, coherente con el +6 % que se vio en Buenos Aires. Las cartas de enero y julio del mismo atlas (isolíneas cada 0.5 kWh/m² por día) dan 6.8-7.8 y 2.0-2.5 kWh/m² por día; ERA5 da 7.2-7.8 en enero y 2.4-2.5 en julio en Luján y Pergamino (2.7-3.0 más al oeste, donde la carta solo tiene una clase abierta de 2.5 o más): coherente, pero la resolución del mapa es gruesa. Límites: es una sola zona (llanura templada), el porcentaje medido es el de toda la red y no el de cada punto, y no se pudo confirmar la lista de estaciones. No cubre zonas montañosas ni tropicales. El atlas de energía solar de la Argentina (Grossi Gallegos y Righini, 2007) trae cartas mensuales de irradiación y de heliofanía para todo el país, pero como mapas sin tablas: sirve de control grueso, no para validar.
- **Panel con cielo real: aproximado.** Supone que las nubes restan al panel inclinado lo mismo que al plano horizontal (no separa directa y difusa) y no descuenta pérdidas del sistema. Para el panel óptimo da 2025 kWh/m² al año en Madrid y 1956 en Buenos Aires. Es una referencia, no un dimensionamiento.
- **Altitud de la celda.** Open-Meteo informa la altitud del punto que resuelve en cada respuesta; el caché la guarda por celda (tabla `cells`) y es la que usa `GET /meteo/irradiancia-real` si no se pasa `elevation_m`. Los datos pedidos antes de que se guardara no la tienen: se recupera con una consulta mínima de un día, una sola vez. La respuesta trae `elevation_source` (`user`, `cell` o `default`); si la fuente no responde solo para dar la altitud, no se rechaza el pedido (los datos están en el caché) sino que se usa 0 m y la página lo advierte. Efecto en el índice de claridad anual: Buenos Aires (20 m) 0.78 y sin cambio; Madrid (689 m) 0.84 → 0.83; La Paz (3972 m) 0.86 → 0.67, que es donde el cielo despejado a nivel del mar subestimaba el techo. La altitud es la del punto que resuelve la fuente (un modelo digital de terreno), que puede diferir de la del centro de una ciudad.
- La estimación del panel casi no depende de la altitud (La Paz: 2324 kWh/m² con 0 m y con 3972 m): al subir el techo de cielo despejado, el índice de claridad baja en la misma proporción y se compensan.
- La primera consulta de un lugar tarda unos 3 s (30 años de datos); la segunda sale del caché en ~0.1 s.
- Open-Meteo gratuito es solo para uso no comercial.

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
