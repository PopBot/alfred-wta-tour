#!/usr/bin/env python3
"""
wta_rankings.py — Alfred keyword: wtar [query]
Official PIF WTA Singles & Doubles Rankings (ESPN + WTA PulseLive API):
  - `wtar`            → Top 50 WTA Singles Players
  - `wtar doubles`    → Top 50 WTA Doubles Players (via WTA PulseLive API)
  - `wtar top10`      → Top 10 WTA Singles Players
  - `wtar top25`      → Top 25 WTA Singles Players
  - `wtar all`        → Full Top 150 WTA Singles Players
  - `wtar usa` / `cze`→ Filter Top 150 by Country (IOC code or country name)
  - `wtar sabalenka`  → Filter Top 150 by Player Name
"""
from __future__ import annotations

import os
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    extract_ioc_from_flag_url, flag_logo_path, ioc_to_flag_emoji,
    player_headshot_path, sanitize_espn_url, WORKFLOW_DIR,
)

RANKINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/rankings"
WTA_RANKED_URL = "https://api.wtatennis.com/tennis/players/ranked"
CACHE_TTL = 600  # 10 minutes


def fetch_espn_rankings() -> dict:
    key = "wta_espn_rankings"
    data = cache_get(key, CACHE_TTL)
    if data:
        return data
    stale = cache_get_stale(key)
    try:
        data = api_get(RANKINGS_URL)
        cache_set(key, data)
        return data
    except Exception:
        if stale:
            return stale
        raise


def fetch_wta_pulselive_ranked(metric: str = "SINGLES", rtype: str = "rankSingles") -> list[dict]:
    key = f"wta_pulselive_ranked_{metric.lower()}"
    data = cache_get(key, CACHE_TTL)
    if data is not None:
        return data
    try:
        res = api_get(
            WTA_RANKED_URL,
            params={"page": 0, "pageSize": 100, "type": rtype, "sort": "asc", "metric": metric},
            timeout=5,
        )
        if isinstance(res, list):
            cache_set(key, res)
            return res
    except Exception:
        pass
    return cache_get_stale(key) or []


def _format_trend(trend: str | None, current: int, previous: int) -> str:
    if previous and previous > 0:
        if previous == current:
            return "—"
        diff = previous - current
        return f"▲{diff}" if diff > 0 else f"▼{abs(diff)}"
    if trend and trend not in ("-", ""):
        if trend.startswith("+"):
            return f"▲{trend[1:]}"
        if trend.startswith("-"):
            return f"▼{trend[1:]}"
        return trend
    return "—"


def render_doubles_rankings(filter_q: str):
    entries = fetch_wta_pulselive_ranked(metric="DOUBLES", rtype="rankDoubles")
    if not entries:
        alfred_error("Could not fetch PIF WTA Doubles Rankings", "WTA PulseLive endpoint returned no entries.")
        return

    filtered = []
    for e in entries:
        p = e.get("player", {})
        name = p.get("fullName", "").lower()
        ioc = (p.get("countryCode") or "").lower()
        if not filter_q or filter_q == ioc or filter_q in name:
            filtered.append(e)

    filtered = filtered[:50]
    items = [{
        "title": f"── 🏆 PIF WTA Doubles Rankings (Top {len(filtered)}) ──",
        "subtitle": "Switch to Singles: wtar · Filter Doubles: wtar doubles usa",
        "valid": False,
        "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
    }]

    for e in filtered:
        rk = e.get("ranking", 0)
        pts = int(e.get("points", 0))
        tourn_cnt = e.get("tournamentsPlayed", 0)
        mov = int(e.get("movement", 0) or 0)
        mov_str = f"▲{mov}" if mov > 0 else (f"▼{abs(mov)}" if mov < 0 else "—")

        p = e.get("player", {})
        wta_id = p.get("id", "")
        full_name = p.get("fullName", "Player")
        ioc = (p.get("countryCode") or "").upper()
        flag_emoji = ioc_to_flag_emoji(ioc)
        slug = full_name.lower().replace(" ", "-")
        wta_url = f"https://www.wtatennis.com/players/{wta_id}/{slug}"

        items.append({
            "title": f"#{rk} {full_name}  {flag_emoji} {ioc}   —  {pts:,} pts  ({mov_str})",
            "subtitle": f"Tournaments Played: {tourn_cnt}  ·  WTA Doubles World Ranking",
            "arg": wta_url,
            "icon": {"path": flag_logo_path(ioc)},
        })

    alfred_output(items)


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = query.lower()

    if q.startswith("doubles") or q.startswith("dbl"):
        rest = q.replace("doubles", "").replace("dbl", "").strip()
        render_doubles_rankings(rest)
        return

    try:
        data = fetch_espn_rankings()
    except Exception as e:
        alfred_error("Could not fetch PIF WTA Rankings", str(e))
        return

    rankings_list = data.get("rankings", [])
    if not rankings_list or not rankings_list[0].get("ranks"):
        alfred_error("WTA Rankings data unavailable", "Please try again shortly.")
        return

    # Enrich with WTA PulseLive tournamentsPlayed map
    pulse_sgl = fetch_wta_pulselive_ranked(metric="SINGLES", rtype="rankSingles")
    tourn_by_last: dict[str, int] = {}
    for pe in pulse_sgl:
        ln = (pe.get("player", {}).get("lastName") or "").lower().strip()
        if ln and pe.get("tournamentsPlayed"):
            tourn_by_last[ln] = int(pe["tournamentsPlayed"])

    poll = rankings_list[0]
    ranks = poll.get("ranks", [])

    limit = 50
    filter_term = ""
    if q in ("top10", "10"):
        limit = 10
    elif q in ("top20", "20"):
        limit = 20
    elif q in ("top25", "25"):
        limit = 25
    elif q in ("top50", "50", ""):
        limit = 50
    elif q in ("all", "top100", "100", "top150", "150"):
        limit = 150
    else:
        filter_term = q
        limit = 150

    filtered_entries = []
    for entry in ranks:
        if not filter_term:
            filtered_entries.append(entry)
            continue
        ath = entry.get("athlete", {})
        name = ath.get("displayName", "").lower()
        ioc = (ath.get("citizenshipCountry") or extract_ioc_from_flag_url(ath.get("flag"))).lower()
        country_name = ath.get("flagAltText", "").lower()
        birth = ath.get("birthPlace", {}).get("summary", "").lower()

        if filter_term == ioc or filter_term in name or filter_term in country_name or filter_term in birth:
            filtered_entries.append(entry)

    filtered_entries = filtered_entries[:limit]
    if not filtered_entries:
        alfred_output([{
            "title": f"No ranked WTA players matching '{query}'",
            "subtitle": "Try: wtar top10, wtar doubles, wtar all, wtar usa, wtar cze, or wtap {player}",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    header_label = f"PIF WTA Singles Rankings (Filtered: '{query}')" if filter_term else f"PIF WTA Singles Rankings (Top {len(filtered_entries)})"
    items = [{
        "title": f"── 🏆 {header_label} ──",
        "subtitle": "Filter: wtar doubles · wtar top10 · wtar all · wtar usa · wtar {player}",
        "valid": False,
        "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
    }]

    for idx, entry in enumerate(filtered_entries):
        curr = int(entry.get("current", 0))
        prev = int(entry.get("previous", 0))
        pts = int(float(entry.get("points", 0)))
        trend_str = _format_trend(entry.get("trend"), curr, prev)

        ath = entry.get("athlete", {})
        aid = str(ath.get("id", ""))
        name = ath.get("displayName", "Unknown Player")
        last_name = (ath.get("lastName") or name.split()[-1]).lower()
        ioc = (ath.get("citizenshipCountry") or extract_ioc_from_flag_url(ath.get("flag"))).upper()
        flag_emoji = ioc_to_flag_emoji(ioc)
        country_full = ath.get("flagAltText", ioc)
        age = ath.get("age")
        birth = ath.get("birthPlace", {}).get("summary", "")
        t_played = tourn_by_last.get(last_name)

        headshot_url = ath.get("headshot")
        if idx < 15 or len(filtered_entries) <= 25:
            icon_path = player_headshot_path(aid, direct_url=headshot_url, fallback_ioc=ioc)
        else:
            cached_hs = os.path.join(os.path.dirname(flag_logo_path(ioc)), "headshots", f"{aid}.png")
            icon_path = cached_hs if os.path.exists(cached_hs) else flag_logo_path(ioc)

        profile_url = ""
        for l in ath.get("links", []):
            if "playercard" in l.get("rel", []):
                profile_url = sanitize_espn_url(l.get("href"), fallback_id=aid)
                break
        if not profile_url:
            profile_url = sanitize_espn_url(None, fallback_id=aid)

        results_url = f"https://www.espn.com/tennis/player/results/_/id/{aid}"

        title = f"#{curr} {name}  {flag_emoji} {ioc}   —  {pts:,} pts  ({trend_str})"
        sub_parts = [f"Prev: #{prev}" if prev else "Prev: —"]
        if t_played:
            sub_parts.append(f"Tournaments: {t_played}")
        if age:
            sub_parts.append(f"Age: {age}")
        if birth:
            sub_parts.append(birth)
        elif country_full:
            sub_parts.append(country_full)

        items.append({
            "title": title,
            "subtitle": "  ·  ".join(sub_parts),
            "arg": profile_url,
            "icon": {"path": icon_path},
            "mods": {
                "cmd": {
                    "subtitle": f"⌘ Open {name}'s Season Results & Match Log on ESPN",
                    "arg": results_url,
                },
                "alt": {
                    "subtitle": f"⌥ Tip: Type 'wtap {last_name}' for 2026 Serve/Return stats",
                    "arg": profile_url,
                },
            },
        })

    alfred_output(items)


if __name__ == "__main__":
    main()
