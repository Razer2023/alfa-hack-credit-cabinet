from functools import lru_cache

from app.clients.integrations import HttpIntegrationsClient, IntegrationsClient, StubIntegrationsClient
from app.clients.scoring import HttpScoringClient, ScoringClient, StubScoringClient
from app.config import settings


@lru_cache
def get_integrations() -> IntegrationsClient:
    if settings.integrations_mode == "http":
        return HttpIntegrationsClient(settings.integrations_url, settings.external_timeout_seconds)
    return StubIntegrationsClient()


@lru_cache
def get_scoring() -> ScoringClient:
    if settings.scoring_mode == "http":
        return HttpScoringClient(settings.scoring_url, settings.external_timeout_seconds)
    return StubScoringClient()
