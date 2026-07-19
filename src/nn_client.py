"""HTTP klijent za narodne-novine.nn.hr — rate limit, retry, raw cache, robots.

Endpointi dokumentirani u docs/01-izvor-podataka-nn.md. Svaki odgovor se sprema
na disk (data/raw/nn/...); ako datoteka vec postoji, mrezni zahtjev se preskace.
"""

from __future__ import annotations

import pathlib
import time
import urllib.parse

import httpx

BASE = "https://narodne-novine.nn.hr"
USER_AGENT = "zakoni.domovina.ai (stepanic.matija@gmail.com)"
MIN_INTERVAL = 0.6  # sekundi izmedju zahtjeva (~1.5 req/s)

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "nn"


class NotFound(Exception):
    pass


class FetchError(Exception):
    pass


_client = httpx.Client(
    headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0
)
_last_request = 0.0
_disallowed: list[str] | None = None


def get(url: str) -> bytes:
    """GET s rate limitom i retryjem (3x, eksponencijalni backoff). 404 -> NotFound."""
    global _last_request
    last_exc: Exception | None = None
    for attempt in range(3):
        wait = MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            r = _client.get(url)
        except httpx.HTTPError as exc:
            last_exc = exc
            time.sleep(2**attempt)
            continue
        if r.status_code == 200:
            return r.content
        if r.status_code == 404:
            raise NotFound(url)
        last_exc = FetchError(f"{r.status_code} {url}")
        time.sleep(2**attempt)
    raise FetchError(f"{url}: {last_exc}")


def fetch_cached(url: str, path: pathlib.Path) -> bytes:
    """Ako `path` postoji (i nije prazan), citaj s diska; inace dohvati pa spremi."""
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    data = get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


# --- robots.txt -------------------------------------------------------------

def _load_disallowed() -> list[str]:
    global _disallowed
    if _disallowed is None:
        raw = fetch_cached(f"{BASE}/robots.txt", RAW_DIR / "robots.txt").decode(
            "utf-8", "replace"
        )
        _disallowed = [
            line.split(":", 1)[1].strip()
            for line in raw.splitlines()
            if line.lower().startswith("disallow:") and line.split(":", 1)[1].strip()
        ]
    return _disallowed


def is_disallowed(url: str) -> bool:
    path = urllib.parse.urlparse(url).path
    return any(path.startswith(p) for p in _load_disallowed())


# --- URL helperi (formati iz docs/01) ---------------------------------------

def search_url(godina: int, broj: int) -> str:
    return (
        f"{BASE}/search.aspx?sortiraj=4&kategorija=1"
        f"&godina={godina}&broj={broj}&rpp=200&qtype=1&pretraga=da"
    )


def rdf_url(godina: int, broj: int, clanak: str | int) -> str:
    """`clanak` je STRING — vidi docs/01 §11 (npr. '0000', rijetko sa slovom)."""
    return f"{BASE}/eli/sluzbeni/{godina}/{broj}/{clanak}/rdf"


def full_html_url(godina: int, mjesec: int, broj: int, clanak: str | int) -> str:
    return f"{BASE}/clanci/sluzbeni/full/{godina}_{mjesec:02d}_{broj}_{clanak}.html"
