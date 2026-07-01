import ipaddress
import os
import threading
import time
from collections import OrderedDict

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# Keyless geolocation upstream. ip-api.com's free tier needs no API key
# (HTTP only, ~45 req/min). Override with GEOIP_URL if you switch providers.
GEOIP_URL = os.getenv("GEOIP_URL", "http://ip-api.com/json")
_FIELDS = "status,message,lat,lon,city,country,query"
_TIMEOUT = float(os.getenv("GEOIP_TIMEOUT", "5"))

# In-memory cache of successful lookups. An IP's location is stable, so we hold
# results for a long TTL to stay well under the upstream rate limit; the LRU cap
# bounds memory. Sync routes run in a threadpool, so guard with a lock.
_CACHE_TTL = float(os.getenv("GEOIP_CACHE_TTL", "86400"))   # seconds (default 24h)
_CACHE_MAX = int(os.getenv("GEOIP_CACHE_MAX", "10000"))      # max distinct IPs
_cache: "OrderedDict[str, tuple[dict, float]]" = OrderedDict()
_cache_lock = threading.Lock()


def clear_cache() -> None:
    """Empty the geolocation cache (used by tests)."""
    with _cache_lock:
        _cache.clear()


def _cache_get(ip: str):
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(ip)
        if entry is None:
            return None
        result, expires_at = entry
        if expires_at < now:
            del _cache[ip]
            return None
        _cache.move_to_end(ip)  # mark as recently used
        return result


def _cache_put(ip: str, result: dict) -> None:
    with _cache_lock:
        _cache[ip] = (result, time.monotonic() + _CACHE_TTL)
        _cache.move_to_end(ip)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)  # evict least-recently-used


def geolocate_ip(ip: str) -> dict:
    """
    Resolve an IP to coordinates via the upstream geolocation service, caching
    successful results in memory.

    Raises HTTPException(502) if the upstream is unreachable/errors, and
    HTTPException(404) if the upstream can't locate the address (e.g. private or
    reserved IPs, which don't geolocate). Failures are not cached.
    """
    cached = _cache_get(ip)
    if cached is not None:
        return cached

    try:
        resp = httpx.get(f"{GEOIP_URL}/{ip}", params={"fields": _FIELDS}, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"geolocation upstream error: {exc}")

    if data.get("status") != "success":
        raise HTTPException(
            status_code=404,
            detail=data.get("message", "could not locate IP"),
        )

    result = {
        "ip": data.get("query", ip),
        "latitude": data["lat"],
        "longitude": data["lon"],
        "city": data.get("city"),
        "country": data.get("country"),
    }
    _cache_put(ip, result)
    return result


@router.get("/get_coords")
def get_coords(ip: str = Query(..., description="IPv4/IPv6 address to locate")):
    """Return the geographic coordinates (lat/lon) for an IP address."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"invalid IP address: {ip!r}")

    return geolocate_ip(ip)
