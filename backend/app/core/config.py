"""
Application configuration.

Every secret and environment-specific value is read from the environment (or a
local `.env` that is never committed). Nothing here has a usable default: an
unset API key means the corresponding capability is off, not silently mocked.

`cors_origins` deliberately defaults to the two local dev ports rather than `*`.
Wildcard origins combined with credentials are rejected by browsers anyway, and a
permissive default is the wrong posture for a deployment artefact. To widen it,
set `CORS_ORIGINS` explicitly; `*` is only honoured when `env` is `development`
AND `ALLOW_WILDCARD_CORS=true` is set, so it can never happen by accident.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import BACKEND_DIR, DEFAULT_DB_PATH


class Settings(BaseSettings):
    # ── Core ────────────────────────────────────────────────────────────────
    env: str = "development"
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"
    seed_on_startup: bool = True

    # ── Network ─────────────────────────────────────────────────────────────
    # Comma-separated. Default is local development only.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Wildcard CORS is refused unless this is explicitly enabled.
    allow_wildcard_cors: bool = False

    # ── Optional AI providers ───────────────────────────────────────────────
    # Unset => that provider is disabled. The core product never depends on it.
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # ── Data providers ──────────────────────────────────────────────────────
    data_gov_in_api_key: str = ""
    census_api_key: str = ""
    overpass_timeout_seconds: float = 7.0

    # ── Demo mode ───────────────────────────────────────────────────────────
    # When true the application makes no outbound network calls and the
    # provider clients fall back to bundled fixtures.
    #
    # This does NOT tag returned values with InputSource.DEMO_DATA. That enum
    # member exists and carries a confidence weight, but nothing assigns it, so
    # a per-field provenance trail is not how demo data is disclosed. What
    # actually happens: `disclose_data_mode` in app/main.py stamps every
    # response with X-YuktiFi-Data-Mode, and the frontend shows a banner. That
    # is a per-response disclosure rather than a per-field one, and it is the
    # mechanism that is real.
    demo_mode: bool = False
    # When true, external providers may be called even if demo_mode is on.
    demo_allow_network: bool = False

    # ── Admin / API key guard ───────────────────────────────────────────────
    # Empty disables the guard. Set it for any shared deployment.
    api_key: str = ""

    # ── RAG ─────────────────────────────────────────────────────────────────
    # RAG ingestion is restricted to these roots. Prevents arbitrary file read.
    rag_ingest_roots: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Derived helpers ─────────────────────────────────────────────────────
    @property
    def database_path(self) -> Path | None:
        """
        Absolute path for a SQLite URL, or None for a server database.

        `sqlite:///./yukti.db` is relative to the *current working directory*, so
        the database file lands in a different place depending on whether the app
        was started from the repo root or from `backend/`. It is resolved here
        against `backend/` so the file is always the same one.
        """
        if not self.database_url.startswith("sqlite"):
            return None
        raw = self.database_url.split("///", 1)[-1]
        if not raw or raw == ":memory:":
            return None
        p = Path(raw).expanduser()
        return p if p.is_absolute() else (BACKEND_DIR / p).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if raw == "*":
            if self.allow_wildcard_cors and self.env == "development":
                return ["*"]
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def is_demo(self) -> bool:
        return bool(self.demo_mode)

    @property
    def network_allowed(self) -> bool:
        """Outbound network is permitted unless demo mode is on and not overridden."""
        if self.is_demo and not self.demo_allow_network:
            return False
        return True

    @property
    def rag_ingest_root_list(self) -> list[Path]:
        if not self.rag_ingest_roots.strip():
            return []
        return [Path(p).expanduser().resolve() for p in self.rag_ingest_roots.split(",") if p.strip()]

    @property
    def has_any_llm(self) -> bool:
        return bool(self.gemini_api_key or self.llm_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
