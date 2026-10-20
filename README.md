# Ephemeris

Aplicación web para calcular y visualizar fenómenos solares (horas de sol,
trayectoria del sol, mediodía solar, crepúsculos, estaciones, irradiancia y
orientación óptima de paneles) y de la Luna (fases, salida y puesta,
perigeo y apogeo, eclipses, mareas teóricas y Pascua) a partir de la
latitud/longitud del observador y la fecha. Pensada como base escalable
para etapas futuras (meteorología).

**Estado actual: etapas 1 (Sol) y 2 (Luna, eclipses, calendario y mareas
teóricas) completas.** Ver
[`docs/plan_tecnico.md`](docs/plan_tecnico.md) para la arquitectura, las
fórmulas por módulo, la precisión verificada y el plan de las etapas 2 y 3.

## Funciones

| Página | Endpoint | Qué calcula |
|---|---|---|
| Horas de sol | `GET /sol/dia`, `GET /sol/anual` | Orto, tránsito, ocaso y duración del día; evolución anual |
| Trayectoria | `GET /sol/trayectoria` | Altitud y azimut del Sol a lo largo del día (gráfico polar) |
| Mediodía | `GET /sol/mediodia` | Hora del mediodía solar y altitud máxima, con refracción |
| Irradiancia | `GET /sol/irradiancia` | Potencia y energía por m² en cielo despejado (directa + difusa) |
| Crepúsculos | `GET /sol/crepusculos` | Civil, náutico, astronómico, hora azul y hora dorada |
| Estaciones | `GET /sol/estaciones` | Equinoccios y solsticios del año |
| Panel solar | `GET /sol/panel` | Inclinación y orientación óptimas de un panel fijo |
| Luna | `GET /luna/dia`, `/luna/trayectoria`, `/luna/fases`, `/luna/apsides` | Fase e iluminación, salida/tránsito/puesta, trayectoria, fases y perigeo/apogeo del año |
| Eclipses | `GET /eclipses/anio` | Eclipses de Sol y de Luna del año (condiciones globales; visibilidad lunar por ubicación) |
| Mareas | `GET /mareas/dia` | Marea de equilibrio del Sol y la Luna, pleamares y bajamares teóricas, mareas vivas y muertas |
| Pascua | `GET /calendario/pascua` | Pascua occidental y ortodoxa |

La documentación interactiva de la API está en `/docs` (Swagger) con el
backend corriendo.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI (Python), numpy para cálculos vectorizados |
| Frontend | React + TypeScript + Vite + Recharts |
| Infra | Docker Compose |

## Getting Started

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

Sin Docker:

```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload

# frontend
cd frontend && npm ci && npm run dev
```

### Configuración

| Variable | Dónde | Por defecto | Uso |
|---|---|---|---|
| `CORS_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes (separados por coma) que pueden llamar a la API. En producción, el dominio del frontend |
| `VITE_API_URL` | frontend | `http://localhost:8000` | URL base de la API |

## Desarrollo

```bash
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest
cd frontend && npm run lint && npm test && npm run build
```

La CI (`.github/workflows/ci.yml`) corre lo mismo. Los tests del motor
incluyen los ejemplos numéricos de Meeus y comparaciones contra astropy
(orto/ocaso del Sol y de la Luna, posición lunar, fases, perigeo y apogeo,
eclipses reales de 2023 a 2026): ver `backend/tests/solar/test_reference.py`,
`test_moon.py`, `test_phases.py`, `test_apsides.py` y `test_eclipses.py`.

## Estructura

```
ephemeris/
├── docs/               # plan técnico y brief original del proyecto
├── backend/            # FastAPI + motor de cálculo astronómico
│   └── app/solar/      # motor puro (sin FastAPI): tiempo, Sol, Luna, eclipses, mareas, irradiancia
└── frontend/           # React + TypeScript + Vite
```

## Fuentes

Los algoritmos astronómicos se basan en *Astronomical Algorithms* (2nd ed.) y
*(More) Mathematical Astronomy Morsels* de Jean Meeus. Como respaldo, para lo
que Meeus no cubre: el *Explanatory Supplement to the Astronomical Almanac*
(escalas de tiempo, ΔT), *Methods of Astrodynamics* de Vallado (tiempo,
sidéreo, posición del Sol) y *Computer Programs for Sun and Moon
Illuminance* de Janiczek y DeYoung (iluminancia; todavía sin usar).
Los libros no se distribuyen con el repositorio.
