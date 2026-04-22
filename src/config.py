"""
Production Configuration — Single Source of Truth.
Implements Model Routing: different tiers for different agents.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # --- API Keys ---
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # --- Model Routing (Interview Q8: Tiered Cost Optimization) ---
    # Router: cheap/fast model (classification is easy)
    router_model: str = "gemini-2.5-flash"
    router_temperature: float = 0.0  # deterministic classification

    # Writer: medium model (creative drafting)
    writer_model: str = "gemini-2.5-flash"
    writer_temperature: float = 0.5  # some creativity

    # Verifier: smartest model (needs to catch subtle errors)
    verifier_model: str = "gemini-2.5-flash"
    verifier_temperature: float = 0.1  # near-deterministic review

    # Researcher: fast model (just extraction)
    researcher_model: str = "gemini-2.5-flash"
    researcher_temperature: float = 0.0

    # --- Graph Config ---
    max_revisions: int = 3          # Max Writer↔Verifier loops
    recursion_limit: int = 15       # Hard failsafe for LangGraph

    # --- DB Config ---
    db_name: str = "beaver.db"

    # --- App Config ---
    app_name: str = "Beaver Agent"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
