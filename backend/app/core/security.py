"""
VeriTrace AI — Security and Resilience Core.

Provides:
  1. URL validation and SSRF (Server-Side Request Forgery) protection.
  2. In-memory sliding-window request rate limiter and middleware.
  3. Client IP extraction with proxy safety.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import threading
import time
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)

# Dangerous URL schemes that must never be processed server-side
DISALLOWED_SCHEMES = frozenset([
    "file", "ftp", "gopher", "javascript", "data", "blob", "vbscript",
    "view-source", "ldap", "dict", "jar", "telnet",
])

# Cloud metadata hostnames
METADATA_HOSTNAMES = frozenset([
    "metadata.google.internal",
    "metadata.internal",
    "169.254.169.254",
    "instance-data",
])

# Additional restricted IPv4 networks (e.g. Carrier-grade NAT 100.64.0.0/10)
RESTRICTED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),  # RFC 6598 Carrier-Grade NAT
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark testing
    ipaddress.ip_network("0.0.0.0/8"),      # Current network
    ipaddress.ip_network("240.0.0.0/4"),    # Reserved
]


def is_valid_url(url: str, allow_http: bool = True) -> bool:
    """Check whether a URL has valid syntax and an allowed web scheme."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        allowed_schemes = ("http", "https") if allow_http else ("https",)
        if parsed.scheme.lower() not in allowed_schemes:
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


def validate_safe_url(
    url: str,
    allow_http: bool = True,
    resolve_dns: bool = True,
) -> tuple[bool, Optional[str]]:
    """
    Validate a URL for syntactic safety and SSRF resistance.

    Checks:
      1. Web scheme is allowed (http/https only).
      2. No dangerous schemes (file, ftp, javascript, data, etc.).
      3. Host is present and not a known cloud metadata endpoint.
      4. If resolve_dns is True, resolves DNS and verifies that NONE of the
         destination IP addresses reside in private, loopback, link-local,
         cloud-metadata, or reserved address spaces.

    Returns:
      (is_safe, error_message_if_unsafe)
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    trimmed = url.strip()

    try:
        parsed = urlparse(trimmed)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    scheme = parsed.scheme.lower()
    if scheme in DISALLOWED_SCHEMES:
        return False, f"Forbidden URL scheme '{scheme}'"

    allowed_schemes = ("http", "https") if allow_http else ("https",)
    if scheme not in allowed_schemes:
        return False, f"Unsupported scheme '{scheme}'. Only HTTP(S) permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname"

    # Block metadata hostnames directly
    lower_host = hostname.lower().strip("[]")
    if lower_host in METADATA_HOSTNAMES or lower_host.endswith(".internal"):
        return False, "Access to internal cloud metadata service is blocked (SSRF)"

    # Check if host is a raw IP literal
    try:
        ip_obj = ipaddress.ip_address(lower_host)
        is_safe, reason = _check_ip_safety(ip_obj)
        if not is_safe:
            return False, reason
    except ValueError:
        # Not a raw IP literal, it's a domain name. Resolve if requested.
        if resolve_dns:
            try:
                addr_info = socket.getaddrinfo(lower_host, None)
                for family, _, _, _, sockaddr in addr_info:
                    ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    is_safe, reason = _check_ip_safety(resolved_ip)
                    if not is_safe:
                        return False, f"Domain '{hostname}' resolves to restricted IP {ip_str}: {reason}"
            except socket.gaierror as dns_err:
                logger.debug("DNS resolution failed for %s: %s", hostname, dns_err)
                return False, f"DNS resolution failed for hostname '{hostname}'"
            except Exception as e:
                logger.warning("Error resolving host '%s': %s", hostname, e)
                return False, f"Failed to verify host safety: {e}"

    return True, None


def _check_ip_safety(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> tuple[bool, Optional[str]]:
    """Verify an IP is a globally routable public address."""
    if ip.is_loopback:
        return False, "Loopback addresses (127.0.0.0/8, ::1) are blocked (SSRF)"

    if ip.is_private:
        return False, "Private network addresses (RFC 1918 / ULA) are blocked (SSRF)"

    if ip.is_link_local:
        return False, "Link-local addresses (169.254.0.0/16) are blocked (SSRF)"

    if ip.is_multicast:
        return False, "Multicast addresses are blocked"

    if ip.is_unspecified:
        return False, "Unspecified addresses (0.0.0.0, ::) are blocked"

    if ip.is_reserved:
        return False, "Reserved addresses are blocked"

    # Explicit cloud metadata check (169.254.169.254)
    if str(ip) == "169.254.169.254":
        return False, "Cloud metadata IP (169.254.169.254) is blocked (SSRF)"

    for restricted in RESTRICTED_NETWORKS:
        if ip in restricted:
            return False, f"Address belongs to restricted network {restricted}"

    return True, None


# ── In-Memory Sliding-Window Rate Limiter ─────────────────────────────────


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter.

    Tracks request timestamps per client identifier (e.g. IP).
    """

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_rate_limited(
        self,
        key: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int, int]:
        """
        Check whether the client key has exceeded the rate limit.

        Returns:
          (is_limited, remaining_requests, reset_seconds, retry_after)
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            records = self._history.get(key, [])
            # Prune timestamps outside the current sliding window
            active = [t for t in records if t > cutoff]

            if len(active) >= max_requests:
                # Limit exceeded
                oldest = active[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                reset_seconds = retry_after
                self._history[key] = active
                return True, 0, reset_seconds, retry_after

            # Allowed — record current request timestamp
            active.append(now)
            self._history[key] = active
            remaining = max(0, max_requests - len(active))
            oldest = active[0]
            reset_seconds = max(1, int(oldest + window_seconds - now))
            return False, remaining, reset_seconds, 0

    def reset(self) -> None:
        """Clear all rate limit histories."""
        with self._lock:
            self._history.clear()


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extract the effective client IP address from a request.
    Inspects X-Forwarded-For if available, otherwise falls back to client.host.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in X-Forwarded-For chain is the client
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


# Paths exempt from rate limiting (health checks and documentation)
RATE_LIMIT_EXEMPT_PATHS = frozenset([
    "/health",
    "/readiness",
    "/model-health",
    "/api/v1/health",
    "/api/v1/readiness",
    "/api/v1/model-health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/favicon.ico",
])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware enforcing client rate limits with standard headers:
      - X-RateLimit-Limit
      - X-RateLimit-Remaining
      - X-RateLimit-Reset
      - Retry-After (on 429)
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Exempt monitoring & documentation endpoints
        path = request.url.path
        if path in RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        client_ip = get_client_ip(request)
        is_limited, remaining, reset_secs, retry_after = rate_limiter.is_rate_limited(
            key=client_ip,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

        if is_limited:
            logger.warning(
                "Rate limit exceeded for IP %s on %s %s (retry_after=%ds)",
                client_ip, request.method, path, retry_after,
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Maximum {settings.rate_limit_requests} requests per {settings.rate_limit_window_seconds} seconds.",
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_secs),
                },
            )
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_secs)
        return response
