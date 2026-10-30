#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Answer "is it a good moment to start a DeepSeek run" before spending anything.

Two things decide that, and both are invisible until the bill arrives:

**Balance.** A run that starts under-funded does not fail cleanly. It dies
mid-flight on a 402, and pi still emits `agent_settled`, so `pi-workers.py`
reports the worker `done` rather than `dead`. In the run that motivated this
script three workers were killed that way with their work uncommitted — about
$1.45 of real spend that produced nothing committable.

**Peak hours.** DeepSeek repriced on 2026-08-16 and bills peak at double.
Peak is 01:00-04:00 and 06:00-10:00 UTC, Monday-Friday; everything else,
weekends included, is off-peak. That is only 35 of 168 hours, so this is a trap
to avoid rather than a discount to chase - and the trap is that those windows
land on a US Eastern evening, which is exactly when someone kicks off an
overnight run. 01:00 UTC Monday is 21:00 Eastern on *Sunday*.

It also prints OpenCode Go's quota, which never changes the exit code: the gateway's
`cloud` overflows to DeepSeek by itself when Go runs out.

Exit codes: 0 clear, 1 something wants a human's attention, 2 could not tell
(no key, network down). 1 and 2 are deliberately different: "you are nearly out
of money" and "I could not reach the API" call for different reactions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

BALANCE_URL = "https://api.deepseek.com/user/balance"
# Undocumented; anomalyco/opencode#43983 names it.
GO_USAGE_URL = "https://opencode.ai/zen/go/v1/usage"

# (start_hour, end_hour) in UTC, Monday-Friday only. End is exclusive.
PEAK_WINDOWS_UTC = ((1, 4), (6, 10))

# Per 1M tokens, from api-docs.deepseek.com/quick_start/pricing/ as of
# 2026-10-14. deepseek-v4-flash is a legacy name now served by V4.1-Flash. pi 0.84.3's built-in catalog predates the 2026-08-16 repricing and
# under-reports by about 3x, so anything that wants a real number prices it here
# rather than reading pi's `cost` object. Keyed cache-hit / input-miss / output.
PRICES = {
    "deepseek-v4-pro": {"off": (0.022, 0.66, 1.98), "peak": (0.044, 1.32, 3.96)},
    "deepseek-flash": {"off": (0.003, 0.15, 0.60), "peak": (0.006, 0.30, 1.20)},
    "deepseek-v4-flash": {"off": (0.003, 0.15, 0.60), "peak": (0.006, 0.30, 1.20)},
}


def is_peak(when: dt.datetime) -> bool:
    """Is `when` (an aware datetime) inside a peak window?

    The UTC weekday is what counts, not the local one - which is the whole trap
    for a US caller, since a Sunday evening in Eastern is already Monday in UTC.
    """
    u = when.astimezone(dt.timezone.utc)
    if u.weekday() >= 5:  # Saturday, Sunday
        return False
    return any(start <= u.hour < end for start, end in PEAK_WINDOWS_UTC)


def turn_cost(model: str | None, usage: dict, when: dt.datetime) -> float:
    """What one pi turn cost, at the rate in force when it ran.

    `usage` is pi's per-message usage. A model missing from PRICES, such as the
    LiteLLM gateway's `cloud` alias, is priced as Flash, which is what it serves.
    """
    rates = PRICES.get(model or "", PRICES["deepseek-flash"])
    hit, miss, output = rates["peak" if is_peak(when) else "off"]
    return (usage.get("cacheRead", 0) * hit + usage.get("input", 0) * miss
            + usage.get("output", 0) * output) / 1e6


def minutes_until_peak(when: dt.datetime) -> int | None:
    """Minutes until the next peak window opens, or None if none within a week.

    Returns 0 when already inside one. Walks forward in whole minutes rather
    than doing calendar arithmetic, because the windows are few and the search
    is bounded by a week - clarity is worth more here than cleverness.
    """
    if is_peak(when):
        return 0
    step = dt.timedelta(minutes=1)
    cursor = when.astimezone(dt.timezone.utc).replace(second=0, microsecond=0)
    for minute in range(1, 7 * 24 * 60 + 1):
        if is_peak(cursor + step * minute):
            return minute
    return None


def fetch_balance(key: str, timeout: float = 10.0) -> tuple[float, str]:
    """Return (total_balance, currency). Raises on transport or shape trouble."""
    req = urllib.request.Request(
        BALANCE_URL, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    infos = payload.get("balance_infos") or []
    if not infos:
        raise ValueError("no balance_infos in the response")
    info = infos[0]
    return float(info["total_balance"]), str(info.get("currency", "USD"))


def fetch_go_usage(key: str, timeout: float = 10.0) -> dict:
    """Return Go's rolling, weekly and monthly windows. Raises on transport or shape trouble."""
    req = urllib.request.Request(
        GO_USAGE_URL,
        # Cloudflare answers 403 to urllib's default agent.
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "toolbox-preflight/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["usage"]


def go_summary(usage: dict) -> str:
    """One line per window's percent used, naming any window that is not ok."""
    parts = []
    for name in ("rolling", "weekly", "monthly"):
        window = usage[name]
        status = window.get("status", "ok")
        parts.append(f"{name} {window['percent']:g}%" + ("" if status == "ok" else f" ({status})"))
    return ", ".join(parts)


def _eastern(when: dt.datetime) -> str:
    """Render `when` in US Eastern without depending on tzdata being present."""
    try:
        from zoneinfo import ZoneInfo

        return when.astimezone(ZoneInfo("America/New_York")).strftime("%a %H:%M %Z")
    except Exception:
        return "(Eastern unavailable: no tzdata)"


def evaluate(balance: float | None, when: dt.datetime, min_balance: float, warn_minutes: int):
    """Decide what to say. Pure, so the tests never touch the network or a clock."""
    peak_now = is_peak(when)
    until = minutes_until_peak(when)
    soon = not peak_now and until is not None and until <= warn_minutes

    problems: list[str] = []
    if balance is not None and balance < min_balance:
        problems.append(
            f"balance ${balance:.2f} is under the ${min_balance:.2f} floor - "
            "top up, or a worker will die mid-flight on a 402 with its work uncommitted"
        )
    if peak_now:
        problems.append(
            "it is PEAK now (01:00-04:00 / 06:00-10:00 UTC, Mon-Fri) - "
            "every token costs double; wait, or accept 2x"
        )
    elif soon:
        problems.append(
            f"peak opens in {until} min - a run started now crosses into it and "
            "the second half bills at double"
        )
    return {
        "balance": balance,
        "min_balance": min_balance,
        "utc": when.astimezone(dt.timezone.utc).strftime("%a %Y-%m-%d %H:%M UTC"),
        "eastern": _eastern(when),
        "peak_now": peak_now,
        "minutes_until_peak": until,
        "peak_soon": soon,
        "problems": problems,
        "ok": not problems,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-balance", type=float, default=2.0,
                    help="warn below this many USD (default: 2)")
    ap.add_argument("--warn-minutes", type=int, default=90,
                    help="warn if peak opens within this many minutes (default: 90)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--skip-balance", action="store_true",
                    help="check the clock only; makes no network call")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    balance: float | None = None
    currency = "USD"
    unreachable: str | None = None

    if not args.skip_balance:
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            unreachable = ("DEEPSEEK_API_KEY is not set. Claude Code's Bash tool does not "
                           "inherit it; source it with "
                           "`set -a; . ~/Git/toolbox/nixos/secrets/.env; set +a`")
        else:
            try:
                balance, currency = fetch_balance(key)
            except urllib.error.HTTPError as exc:
                unreachable = f"balance endpoint returned HTTP {exc.code}"
            except Exception as exc:  # noqa: BLE001 - any failure means "cannot tell"
                unreachable = f"could not reach the balance endpoint: {exc}"

    go: str | None = None
    if not args.skip_balance:
        go_key = os.environ.get("OPENCODE_API_KEY")
        if not go_key:
            go = "unknown - OPENCODE_API_KEY is not set"
        else:
            try:
                go = go_summary(fetch_go_usage(go_key))
            except Exception as exc:  # noqa: BLE001 - it never decides the verdict
                go = f"unknown - {exc}"

    verdict = evaluate(balance, now, args.min_balance, args.warn_minutes)
    verdict["currency"] = currency
    verdict["unreachable"] = unreachable
    verdict["go"] = go

    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        print(f"  when     {verdict['utc']}   /   {verdict['eastern']}")
        if verdict["peak_now"]:
            rate = "PEAK - 2x rates"
        elif verdict["minutes_until_peak"] is None:
            rate = "off-peak"
        else:
            rate = f"off-peak (peak opens in {verdict['minutes_until_peak']} min)"
        print(f"  rate     {rate}")
        if balance is None:
            print(f"  balance  unknown - {unreachable}")
        else:
            print(f"  balance  ${balance:.2f} {currency}   (floor ${args.min_balance:.2f})")
        if go:
            print(f"  go       {go}")
        print()
        if verdict["problems"]:
            for p in verdict["problems"]:
                print(f"  ! {p}")
        else:
            print("  clear to orchestrate.")

    if unreachable and balance is None and not args.skip_balance:
        return 2
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
