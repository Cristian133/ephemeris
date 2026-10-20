from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import calendario, eclipses, luna, mareas, meteo, sol
from app.config import settings

app = FastAPI(title="Calculadora Solar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(sol.router, prefix="/sol", tags=["sol"])
app.include_router(luna.router, prefix="/luna", tags=["luna"])
app.include_router(calendario.router, prefix="/calendario", tags=["calendario"])
app.include_router(mareas.router, prefix="/mareas", tags=["mareas"])
app.include_router(eclipses.router, prefix="/eclipses", tags=["eclipses"])
app.include_router(meteo.router, prefix="/meteo", tags=["meteo"])
