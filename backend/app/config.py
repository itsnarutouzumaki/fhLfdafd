from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_base_url: str = os.getenv("ELEXON_API_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
    request_timeout_seconds: float = float(os.getenv("ELEXON_TIMEOUT_SECONDS", "20"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
    max_retries: int = int(os.getenv("ELEXON_MAX_RETRIES", "3"))
    static_dir: Path = Path(os.getenv("STATIC_DIR", str(Path(__file__).parent / "static")))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )


settings = Settings()
