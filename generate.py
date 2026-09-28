"""
Stage 5 of the pipeline: writing the answer.

This is the only part of your system that calls out to a service. Everything
else runs on your laptop.

Every outgoing call in this course goes through `generate()` below. That
matters for a practical reason: the free tier allows only a small number of
calls per minute, and a previous cohort ran into that wall hard. Rather than
asking three hundred students to each write their own pacing code, the pacing
lives here, once.

What this function does for you:

  • Paces requests so you stay under the per-minute limit, and tells you when
    it's waiting. A pause is the limiter doing its job, not a hang.
  • (Unit 2 stretch) Rotates across the models in config.MODEL_POOL, each with
    its own per-minute window, so the free tier's per-model cap isn't the
    ceiling. A model that answers 429 or 503 is cooled down and the call moves
    to the next one; `last_model` says which model produced the last answer.
  • Caches repeated prompts while you're building, so re-running the same
    question twenty times while you debug costs one call.
  • Stops with a warning if a session goes through an unreasonable number of
    calls, instead of silently draining your whole day's allowance.
  • Retries when the service says you're going too fast.
  • Counts your calls, and the tokens they used, so what a run cost is a
    number you can see rather than one you estimate.

⚠️ Caching is ON while you build and OFF during evaluation. Your unit 2
testing needs three real answers to the same question, not one answer three
times over.
`run_eval.py` passes cache=False for you.
"""

import hashlib
import json
import os
import sys
import time

import config

_call_times: list[float] = []
_session_calls = 0
_session_prompt_tokens = 0
_session_output_tokens = 0
_cache_hits = 0
_client = None
_budget_warned = False


class QuotaGuard(Exception):
    """Raised when a session blows through its request budget."""


# ─── Cache ───────────────────────────────────────────────────────────────────


def _cache_key(prompt: str, system: str | None) -> str:
    blob = json.dumps([config.MODEL, system or "", prompt], sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_read(key: str) -> str | None:
    path = config.CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    except Exception:
        return None


def _cache_write(key: str, response: str) -> None:
    config.CACHE_DIR.mkdir(exist_ok=True)
    path = config.CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({"response": response}), encoding="utf-8")


def clear_cache() -> int:
    """Delete every cached response. Returns how many were removed."""
    if not config.CACHE_DIR.exists():
        return 0
    files = list(config.CACHE_DIR.glob("*.json"))
    for f in files:
        f.unlink()
    return len(files)


# ─── Pacing and guards ───────────────────────────────────────────────────────


# Unit 2 stretch: model rotation.
#
# The free tier caps each model separately, per minute. One model gives you 15
# calls; four models give you 40. So instead of one sliding window, there is
# one per model in config.MODEL_POOL, and each call goes to the first model in
# priority order that still has a free slot this minute. A model that answers
# 429 anyway is put on cooldown for however long the service asked, and the
# call moves down the list instead of sleeping. Only when every model is used
# up or cooling down do we actually wait — and then only until the earliest
# slot frees, on whichever model that is.

_calls_by_model: dict[str, list[float]] = {}
_calls_total_by_model: dict[str, int] = {}
_cooldown_until: dict[str, float] = {}
_disabled: set[str] = set()      # model ids the service says don't exist
last_model: str | None = None    # which model produced the most recent answer


def _pool() -> list[tuple[str, int]]:
    return [(m, q) for m, q in config.MODEL_POOL if m not in _disabled] or []


def _window(model: str, now: float) -> list[float]:
    times = _calls_by_model.setdefault(model, [])
    times[:] = [t for t in times if now - t < 60.0]
    return times


def _pick_model() -> str:
    """
    Return the highest-priority model with a free slot this minute, sleeping
    first if there isn't one anywhere.
    """
    while True:
        now = time.monotonic()
        pool = _pool()
        if not pool:
            raise RuntimeError(
                "Every model in config.MODEL_POOL has been disabled this session "
                "(the service said it doesn't exist). Check the ids."
            )

        soonest = None
        for model, quota in pool:
            if _cooldown_until.get(model, 0.0) > now:
                soonest = min(soonest or 1e9, _cooldown_until[model])
                continue
            window = _window(model, now)
            if len(window) < quota:
                return model
            soonest = min(soonest or 1e9, window[0] + 60.0)

        sleep_for = max(0.0, soonest - now) + 0.1
        print(
            f"  [rate limit] all {len(pool)} models used up this minute. "
            f"Waiting {sleep_for:.0f}s. This is normal.",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(sleep_for)


def _retry_after_seconds(message: str) -> float:
    """How long the service asked us to wait, if it said. Default a minute."""
    import re

    m = re.search(r"retry in ([\d.]+)\s*s", message) or re.search(
        r"retryDelay['\"]?:\s*['\"]?([\d.]+)s", message
    )
    return float(m.group(1)) if m else 60.0


def _wait_for_slot() -> None:
    """Kept for compatibility; the per-model pacing now lives in _pick_model."""
    return


def _check_budget() -> None:
    global _budget_warned
    if _session_calls < config.SESSION_REQUEST_BUDGET:
        return
    if not _budget_warned:
        _budget_warned = True
    raise QuotaGuard(
        f"This session has made {_session_calls} requests, which is the "
        f"budget set in config.py (SESSION_REQUEST_BUDGET).\n"
        f"That usually means a loop is running away rather than that you've "
        f"done {_session_calls} requests' worth of real work.\n"
        f"Stop the program and look for the loop. If you really do need more, "
        f"raise the number in config.py — but look first."
    )


def _record_tokens(response) -> None:
    """Add one response's token counts to this session's running totals.

    These come off the response itself, which is the point. When you work out
    what a run costs, a number read back from the service is a measurement and
    a number multiplied out of the pricing page is a guess — they disagree more
    often than you'd think, and only one of them is evidence.

    Deliberately forgiving: `usage_metadata` is missing on some responses and
    half-filled on others, and a token count you didn't get is never a good
    enough reason to end someone's run.
    """
    global _session_prompt_tokens, _session_output_tokens

    try:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return
        _session_prompt_tokens += int(getattr(meta, "prompt_token_count", 0) or 0)
        _session_output_tokens += int(getattr(meta, "candidates_token_count", 0) or 0)
    except Exception:
        pass  # accounting never breaks the thing it is accounting for


def usage() -> str:
    """One line on what this session has spent. Printed by app.py on exit."""
    tokens = ""
    total = _session_prompt_tokens + _session_output_tokens
    if total:
        tokens = (
            f", {total} tokens "
            f"({_session_prompt_tokens} in, {_session_output_tokens} out)"
        )
    by_model = ""
    if len(_calls_total_by_model) > 1 or (
        _calls_total_by_model and next(iter(_calls_total_by_model)) != config.MODEL
    ):
        parts = ", ".join(f"{m} {n}" for m, n in _calls_total_by_model.items())
        by_model = f" [{parts}]"
    return (
        f"{_session_calls} model calls this session"
        f"{by_model}"
        f"{tokens}"
        f"{f', {_cache_hits} served from cache' if _cache_hits else ''}"
    )


def call_count() -> int:
    return _session_calls


def token_counts() -> dict[str, int]:
    """Tokens this session actually used, as reported by the service.

    Cache hits are not in here, because they never reached the service and so
    cost nothing. That is a real difference between a run and a cached rerun,
    and it is worth knowing which one you measured.
    """
    return {
        "prompt": _session_prompt_tokens,
        "output": _session_output_tokens,
        "total": _session_prompt_tokens + _session_output_tokens,
    }


# ─── The call ────────────────────────────────────────────────────────────────


def _get_client():
    global _client
    if _client is None:
        from google import genai

        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "No GEMINI_API_KEY found.\n"
                "Copy .env.example to .env and paste your key in, then try "
                "again. `python test.py` will confirm it's working."
            )
        _client = genai.Client(api_key=key)
    return _client


def generate(prompt: str, system: str | None = None, cache: bool = True) -> str:
    """
    Send a prompt and get text back.

    Args:
        prompt: what you're asking.
        system: an optional instruction about how to behave.
        cache:  reuse an identical earlier answer if there is one. Leave this
                True while building. Pass False when you're evaluating — three
                runs of the same question have to be three real answers.

    Every call in this course goes through here. If you need to change how the
    model is called, change it in this one place.
    """
    global _session_calls, _cache_hits

    use_cache = cache and config.CACHE_ENABLED
    key = _cache_key(prompt, system)

    if use_cache:
        hit = _cache_read(key)
        if hit is not None:
            _cache_hits += 1
            return hit

    _check_budget()

    global last_model

    last_error: Exception | None = None
    # One attempt per model in the pool, at minimum — a 429 on one model is a
    # reason to try the next one, not a reason to give up.
    attempts = max(config.MAX_RETRIES, len(config.MODEL_POOL))
    for attempt in range(attempts):
        model = _pick_model()
        try:
            client = _get_client()
            now = time.monotonic()
            _call_times.append(now)
            _window(model, now).append(now)
            _session_calls += 1
            _calls_total_by_model[model] = _calls_total_by_model.get(model, 0) + 1

            kwargs = {"model": model, "contents": prompt}
            if system:
                kwargs["config"] = {"system_instruction": system}

            response = client.models.generate_content(**kwargs)
            _record_tokens(response)
            text = (response.text or "").strip()
            last_model = model

            if use_cache:
                _cache_write(key, text)
            return text

        except Exception as exc:  # noqa: BLE001 — surfaced below
            last_error = exc
            message = str(exc).lower()
            rate_limited = (
                "429" in message
                or "resource" in message and "exhaust" in message
                or "rate" in message and "limit" in message
            )
            missing = "404" in message or "not found" in message
            if missing:
                # A typo in MODEL_POOL shouldn't end the run — drop that model
                # for the session and carry on with the others.
                _disabled.add(model)
                print(
                    f"  [model pool] {model!r} isn't available to this key — "
                    f"dropping it for this session.",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            # 503 / "high demand" / "overloaded" is the service, not us — but
            # for a pool it means the same thing as a 429: this model is not
            # usable right now, and another one probably is.
            overloaded = (
                "503" in message
                or "unavailable" in message
                or "overloaded" in message
                or "high demand" in message
            )
            if not rate_limited and not overloaded:
                raise
            wait = _retry_after_seconds(message) if rate_limited else 30.0
            _cooldown_until[model] = time.monotonic() + wait
            why = "pushed back (rate limit)" if rate_limited else "is overloaded (503)"
            print(
                f"  [model pool] {model} {why}; cooling it down for "
                f"{wait:.0f}s and moving to the next model "
                f"(attempt {attempt + 1} of {attempts}).",
                file=sys.stderr,
                flush=True,
            )

    raise RuntimeError(
        f"Still rate limited after {attempts} attempts across "
        f"{len(config.MODEL_POOL)} model(s). Wait a minute and try again — "
        f"your key is fine.\nLast error: {last_error}"
    )


# ─── The grounded answer ─────────────────────────────────────────────────────

GROUNDING_INSTRUCTION = """You answer questions using only the documents provided to you.

Rules:
- Use only the information in the documents below. Do not use anything you know from elsewhere.
- If the documents don't cover the question, say you don't have enough information. Do not guess.
- Name the document your answer came from, using the filename given in each excerpt.
- Be brief. Two or three sentences is usually enough."""


def build_prompt(question: str, results) -> str:
    """
    Assemble the grounded prompt out of retrieved chunks.

    Split out from `answer_from_chunks` so the prompt can be looked at without
    being sent — `python app.py ask "..." --show-prompt` prints exactly what
    this returns. Reading it once is the fastest way to see that retrieval,
    not the model, decides what an answer can possibly be based on.
    """
    context = "\n\n".join(
        f"[from {r.source}]\n{r.text}" for r in results
    )
    return (
        f"Documents:\n\n{context}\n\n"
        f"---\n\nQuestion: {question}\n\n"
        f"Answer using only the documents above, and name the file you used."
    )


def answer_from_chunks(question: str, results, cache: bool = True) -> str:
    """
    Build a grounded prompt out of retrieved chunks and send it.

    This is the second layer of grounding. The relevance gate in gate.py is the
    first — it has already decided these chunks are close enough to be worth
    answering from.
    """
    prompt = build_prompt(question, results)
    return generate(prompt, system=GROUNDING_INSTRUCTION, cache=cache)
