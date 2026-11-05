"""A small, careful client for Stacksync AI inference (chat completions).

What "careful" means here:
- the key comes from the environment and is never printed or stored in an exception
- max_tokens is always set, and capped, so one call cannot be huge
- only HTTP 429 (busy) is retried. 401 and 402 are not. Ambiguous failures (502, 503,
  network errors) are NOT retried automatically, because a repeated paid request
  may be charged twice
- cost is read as a Decimal, never a float

    export STACKSYNC_AI_KEY=...        # set it in your deployment variables
    export STACKSYNC_AI_MODEL=...      # an exact id from `eos inference models`

Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Callable

BASE_URL = "https://enterprise-os.stacksync.ai/api/inference/v1"
MAX_TOKENS_CAP = 1024  # your own ceiling. The platform default output cap is also 1,024


class AIError(Exception):
    def __init__(self, message: str, status: int | None = None, ambiguous: bool = False):
        super().__init__(message)
        self.status = status
        self.ambiguous = ambiguous  # True when the request may have been charged


class InvalidKey(AIError):
    """401: the key is invalid, revoked, or its owner lost access."""


class BudgetExceeded(AIError):
    """402: the key cannot cover this request's reservation. Do not retry blindly."""


class Busy(AIError):
    """429: model capacity is busy. Safe to retry with backoff."""


class Unavailable(AIError):
    """502/503 or a network failure. The request may or may not have been charged."""


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    max_tokens: int = 256,
    key: str | None = None,
    base_url: str = BASE_URL,
    timeout: float = 120,
    retries: int = 2,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Send a chat request. Returns {"text": str, "cost": Decimal | None, "usage": dict, "raw": dict}."""
    key = key or os.environ.get("STACKSYNC_AI_KEY")
    model = model or os.environ.get("STACKSYNC_AI_MODEL")
    if not key:
        raise AIError("STACKSYNC_AI_KEY is not set")
    if not model:
        raise AIError("no model. Pass model= or set STACKSYNC_AI_MODEL to an id from `eos inference models`")
    if not 1 <= max_tokens <= MAX_TOKENS_CAP:
        raise AIError(f"max_tokens must be between 1 and {MAX_TOKENS_CAP}")

    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens}).encode()
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            break
        except urllib.error.HTTPError as err:
            status = err.code
            if status == 401:
                raise InvalidKey("the inference key is invalid or revoked", status) from None
            if status == 402:
                raise BudgetExceeded("the key cannot cover this request. Check its remaining budget and the request size", status) from None
            if status == 429:
                if attempt == retries:
                    raise Busy("the model is busy. Try again later", status) from None
                sleep(min(2**attempt, 8))
                continue
            if status in (502, 503):
                raise Unavailable("inference is unavailable. The request may have been charged. Check the logs before repeating it", status, ambiguous=True) from None
            raise AIError(f"unexpected HTTP {status}", status) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Unavailable("could not reach inference. The request may have been charged. Check the logs before repeating it", None, ambiguous=True) from None

    usage = data.get("usage") or {}
    cost = usage.get("cost")
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return {"text": text, "cost": Decimal(str(cost)) if cost is not None else None, "usage": usage, "raw": data}
