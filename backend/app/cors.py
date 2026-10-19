"""Explicit browser-origin allowlist; empty configuration denies all origins."""
import os
from urllib.parse import urlsplit


def allowed_origins():
    origins = [value.strip() for value in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if value.strip()]
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or '*' in origin
                or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError('CORS_ORIGINS must contain comma-separated explicit HTTP(S) origins')
    return origins
