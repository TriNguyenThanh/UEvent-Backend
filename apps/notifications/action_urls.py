from urllib.parse import quote

from django.conf import settings


def build_event_action_url(event_slug: str) -> str:
    base_url = getattr(
        settings, "PUBLIC_WEB_BASE_URL", "http://localhost:3000"
    ).rstrip("/")
    return f"{base_url}/events/share/{quote(event_slug, safe='')}"
