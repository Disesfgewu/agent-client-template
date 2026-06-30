"""Shared helpers for gating integration tests on a configured live API.

Importing this module loads the project's ``.env`` so that ``EMBEDDING_API`` is
visible at class-decoration time (when ``skipUnless`` is evaluated). Tests that
hit real LLM / embedding endpoints decorate their class with::

    @unittest.skipUnless(live_api_available(), SKIP_REASON)

so a fresh clone of the template (no ``config/api.local.json``, no embedding
key) still produces a green unit-test run instead of a wall of errors.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_CONFIG = os.path.join(ROOT, "config", "api.local.json")


def live_api_available() -> bool:
    """True when both the model config and the embedding key are present."""
    return os.path.exists(API_CONFIG) and bool(os.getenv("EMBEDDING_API"))


SKIP_REASON = (
    "Live API not configured: copy config/api.example.json to "
    "config/api.local.json and set EMBEDDING_API in .env (see README)."
)
