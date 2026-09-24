"""
Per-product access resolution for the launcher.

A licence says the organization bought the product. Access additionally needs
the product to be launchable and, for role_api products, the user to hold a
role inside it. That role is read live from the product's internal API, never
cached, so revocations take effect on the next launch.

The check fails closed: a product with no integration config, or one that
cannot be reached, is reported as "unavailable" and never as "ready".
Unavailable is kept distinct from "not_provisioned" so an outage is not
misreported as a missing account.

Integration config is per deployment (settings.PRODUCT_INTEGRATIONS, keyed by
Product.slug):

    "dms": {"base_url": ..., "api_key": ..., "public_url": ..., "role_field": "dms_role"}
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

READY = "ready"
NOT_PROVISIONED = "not_provisioned"
UNAVAILABLE = "unavailable"

PROBE_TIMEOUT_SECONDS = 5
MAX_PARALLEL_PROBES = 8


@dataclass(frozen=True)
class Access:
    status: str
    launch_url: str = ""
    role: str = ""
    message: str | None = None


class _ProbeFailed(Exception):
    """The product's API could not give a trustworthy answer."""


def integration_config(slug: str) -> dict:
    return (getattr(settings, "PRODUCT_INTEGRATIONS", None) or {}).get(slug, {})


def launch_url_for(product) -> str:
    return product.launch_url or integration_config(product.slug).get("public_url", "") or ""


def _fetch_role(cfg: dict, email: str, role_field: str) -> str:
    """Return the user's role in the product, or "" if the product has no such user."""
    base = (cfg.get("base_url") or "").rstrip("/")
    api_key = cfg.get("api_key") or ""
    url = f"{base}/users/authorization/?{urlencode({'email': email})}"
    request = Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=PROBE_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return ""
        raise _ProbeFailed(f"HTTP {exc.code}") from exc
    except (URLError, OSError, ValueError) as exc:
        raise _ProbeFailed(str(exc)) from exc

    if not isinstance(payload, dict):
        raise _ProbeFailed("unexpected response shape")
    return str(payload.get(role_field) or "").strip()


def resolve_access(user, product) -> Access:
    launch_url = launch_url_for(product)
    if not launch_url:
        return Access(
            UNAVAILABLE,
            message=f"{product.name} is not connected to the launcher yet. Contact your administrator.",
        )

    if product.provisioning_mode == product.Provisioning.LICENSE_ONLY:
        return Access(READY, launch_url)

    cfg = integration_config(product.slug)
    if not (cfg.get("base_url") and cfg.get("api_key")):
        logger.error("No role-API integration configured for product '%s'", product.slug)
        return Access(
            UNAVAILABLE,
            launch_url,
            message=f"{product.name} is not configured for sign-in on this deployment. Contact your administrator.",
        )

    try:
        role = _fetch_role(cfg, user.email, cfg.get("role_field") or f"{product.slug}_role")
    except _ProbeFailed as exc:
        logger.warning("Role probe failed for product '%s': %s", product.slug, exc)
        return Access(
            UNAVAILABLE,
            launch_url,
            message=f"{product.name} is not responding right now. Try again in a few minutes.",
        )

    if not role:
        return Access(
            NOT_PROVISIONED,
            launch_url,
            message=(
                f"Your organization is licensed for {product.name}, but your account has not "
                "been provisioned there. Contact your administrator."
            ),
        )
    return Access(READY, launch_url, role=role)


def resolve_access_many(user, products) -> dict[str, Access]:
    """Resolve several products concurrently so one slow product cannot stall the launcher."""
    products = list(products)
    if not products:
        return {}
    workers = min(MAX_PARALLEL_PROBES, len(products))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda p: resolve_access(user, p), products))
    return {p.slug: access for p, access in zip(products, results)}
