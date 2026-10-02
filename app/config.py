from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    """Environment settings. The old achievement engine's settings (email,
    Discord, XP start, verification, Wrapped, backfill) were removed with it;
    the last version that used them is git tag `pre-dungeon-final`."""
    absstats_base_url: str = Field(default="http://localhost:3010")
    state_db_path: str = Field(default="/data/state.db")
    series_refresh_seconds: int = Field(default=24 * 3600)
    completed_endpoint: str = Field(default="/api/completed")
    radar_check_interval_hours: int = Field(default=12)
    allowed_users: str = Field(default="")   # ABS usernames who can play; empty = everyone


def load_settings() -> Settings:
    def i(name: str, default: int) -> int:
        v = os.getenv(name)
        if v is None:
            return default
        try:
            return int(v.strip())
        except Exception:
            return default

    return Settings(
        absstats_base_url=os.getenv("ABSSTATS_BASE_URL", "http://localhost:3010").rstrip("/"),
        state_db_path=os.getenv("STATE_DB_PATH", "/data/state.db"),
        series_refresh_seconds=i("SERIES_REFRESH_SECONDS", 24 * 3600),
        completed_endpoint=os.getenv("COMPLETED_ENDPOINT", "/api/completed"),
        radar_check_interval_hours=i("RADAR_CHECK_INTERVAL_HOURS", 12),
        allowed_users=os.getenv("ALLOWED_USERS", "").strip(),
    )
