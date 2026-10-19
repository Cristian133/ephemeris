"""Configuración de la app, leída de variables de entorno (o de un `.env`)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """`CORS_ORIGINS` es una lista de orígenes separados por coma desde los
    que el navegador puede llamar a la API. Por defecto, solo el servidor
    de desarrollo del frontend; en producción hay que fijarla al dominio
    real (`*` habilita cualquiera: solo para pruebas)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
