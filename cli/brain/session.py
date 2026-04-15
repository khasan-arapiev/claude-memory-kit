"""Session id minting for `/ProjectSync`.

Lives outside sync.py because minting an id has nothing to do with
inspecting pending state — the old placement was convenient, not honest.
Pure function, stdlib only, zero filesystem access.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime


def new_session_id() -> str:
    """Return a fresh session id: `YYYY-MM-DD-HHMM-<4 lowercase alnum>`.

    stdlib Python, no shell dependencies. `/ProjectSync` shells out to
    `brain sync new-session-id` so the id generation works identically
    on Git Bash / macOS / Linux without `/dev/urandom` or `md5sum`.
    """
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    alphabet = string.digits + string.ascii_lowercase
    suffix = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{stamp}-{suffix}"
