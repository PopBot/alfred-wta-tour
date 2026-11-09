#!/usr/bin/env python3
"""
wta_schedule.py — Alfred keywords: wtas [query], wtac [query]
Full-Season Hologic WTA Tour & Grand Slam Calendar (via WTA PulseLive API):
  - `wtas`            → Active Tournaments → Upcoming → Completed (excludes ITF & WTA 125 clutter by default)
  - `wtas slam` / `gs`→ Filter to Grand Slams
  - `wtas 1000`       → Filter to WTA 1000 events
  - `wtas 500` / `250`→ Filter to WTA 500 or WTA 250 events
  - `wtas 125`        → Filter to WTA 125 events
  - `wtas clay`/`grass`/`hard` → Filter by Surface
  - `wtas {month/city/name}`   → Filter by Month, City, or Tournament Name
"""
from __future__ import annotations

from datetime import date, datetime
import os
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    flag_logo_path, ioc_to_flag_emoji, WORKFLOW_DIR,
)

WTA_TOURNAMENTS_URL = "https://api.wtatennis.com/tennis/tournaments/"
CACHE_TTL = 3600  # 1 hour


def fetch_wta_calendar() -> list[dict]:
    year = datetime.now().year
    key = f"wta_tour_calendar_{year}"
    data = cache_get(key, CACHE_TTL)
    if data is not None:
        return data

    stale = cache_get_stale(key)
    try:
        all_items: list[dict] = []
        for page in range(0, 3):
            res = api_get(
                WTA_TOURNAMENTS_URL,
                params={
                    "page": page,
                    "pageSize": 100,
                    "excludeLevels": "ITF",
                    "from": f"{year}-01-01",
                    "to": f"{year}-12-31",
                },
                timeout=8,
            )
            content = res.get("content", [])
            if not content:
                break
            all_items.extend(content)
            if len(content) < 100:
                break
        cache_set(key, all_items)
        return all_items
    except Exception:
        if stale is not None:
            return stale
        raise


def _format_date_range(start_str: str, end_str: str) -> str:
    try:
        s = date.fromisoformat(start_str)
        e = date.fromisoformat(end_str)
        if s.month == e.month:
            return f"{s.strftime('%b %-d')}–{e.strftime('%-d')}"
        return f"{s.strftime('%b %-d')} – {e.strftime('%b %-d')}"
    except Exception:
        return f"{start_str} to {end_str}"


def _matches_filter(t: dict, q: str, include_125: bool) -> bool:
    level = str(t.get("tournamentGroup", {}).get("level", "")).strip()
    level_low = level.lower()

    if not include_125 and "125" in level_low:
        return False

    if not q or q == "all":
        return True
    if q in ("slam", "slams", "gs", "grand slam", "major", "majors"):
        return "grand slam" in level_low
    if q in ("1000", "wta 1000"):
        return "1000" in level_low
    if q in ("500", "wta 500"):
        return "500" in level_low
    if q in ("250", "wta 250"):
        return "250" in level_low
    if q in ("125", "wta 125"):
        return "125" in level_low
    if q in ("finals", "wta finals"):
        return "finals" in level_low or "finals" in str(t.get("title", "")).lower()

    start_str = t.get("startDate", "")
    month_name = ""
    try:
        dt = date.fromisoformat(start_str)
        month_name = f"{dt.strftime('%B')} {dt.strftime('%b')}".lower()
    except Exception:
        pass

    in_out = "indoor" if str(t.get("inOutdoor", "")).upper() == "I" else "outdoor"
    haystack = " ".join([
        str(t.get("title", "")),
        str(t.get("tournamentGroup", {}).get("name", "")),
        str(t.get("city", "")),
        str(t.get("country", "")),
        level,
        str(t.get("surface", "")),
        in_out,
        month_name,
    ]).lower()
    return all(tok in haystack for tok in q.split())


def _build_wta_tournament_item(t: dict, status_kind: str) -> dict:
    tg = t.get("tournamentGroup", {})
    tid = tg.get("id", "")
    raw_title = t.get("title", tg.get("name", "WTA Tournament"))
    # Clean trailing ' - City, COUNTRY' if present
    clean_name = raw_title.split(" - ")[0].strip() if " - " in raw_title else raw_title
    level = tg.get("level", "WTA Tour")
    city = t.get("city", "").title()
    ioc = str(t.get("country", "")).upper()
    flag_emoji = ioc_to_flag_emoji(ioc)
    icon_path = flag_logo_path(ioc) if ioc else os.path.join(WORKFLOW_DIR, "icon.png")

    start_str = t.get("startDate", "")
    end_str = t.get("endDate", "")
    date_range = _format_date_range(start_str, end_str)

    surface = t.get("surface", "")
    in_out = "Indoor" if str(t.get("inOutdoor", "")).upper() == "I" else "Outdoor"
    surf_str = f"{surface} ({in_out})" if surface else in_out

    s_draw = t.get("singlesDrawSize")
    d_draw = t.get("doublesDrawSize")
    draw_str = f"Draw: {s_draw}S/{d_draw}D" if s_draw else ""

    prize = t.get("prizeMoney")
    curr = t.get("prizeMoneyCurrency", "USD")
    purse_str = f"Purse: ${int(prize):,}" if prize and curr == "USD" else (f"Purse: {int(prize):,} {curr}" if prize else "")

    prefix = "🔴 " if status_kind == "active" else ("✅ " if status_kind == "completed" else "📅 ")
    title = f"{prefix}{flag_emoji} {clean_name}  [{level}]   —  {date_range}"
    loc_str = f"{city}, {ioc}" if city and ioc else (city or ioc)
    sub_parts = [s for s in [loc_str, surf_str, draw_str, purse_str] if s]

    slug = tg.get("name", clean_name).lower().replace(" ", "-").replace("'", "")
    year = t.get("year", datetime.now().year)
    wta_url = f"https://www.wtatennis.com/tournaments/{tid}/{slug}/{year}" if tid else "https://www.wtatennis.com/tournaments"

    return {
        "title": title,
        "subtitle": "  ·  ".join(sub_parts),
        "arg": wta_url,
        "icon": {"path": icon_path},
        "mods": {
            "cmd": {
                "subtitle": f"⌘ Open {clean_name} Draws & Results on WTA Tour",
                "arg": f"{wta_url}/draws",
            },
            "alt": {
                "subtitle": f"⌥ Open {clean_name} Match Scores on WTA Tour",
                "arg": f"{wta_url}/scores",
            },
        },
    }


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = query.lower()

    try:
        tournaments = fetch_wta_calendar()
    except Exception as e:
        alfred_error("Could not fetch WTA Tour calendar", str(e))
        return

    include_125 = "125" in q or q == "all"
    today_iso = date.today().isoformat()

    active_list: list[dict] = []
    upcoming_list: list[dict] = []
    completed_list: list[dict] = []

    for t in tournaments:
        if not _matches_filter(t, q, include_125=include_125):
            continue
        s_date = t.get("startDate", "")
        e_date = t.get("endDate", "")
        if s_date <= today_iso <= e_date:
            active_list.append(_build_wta_tournament_item(t, "active"))
        elif s_date > today_iso:
            upcoming_list.append(_build_wta_tournament_item(t, "upcoming"))
        else:
            completed_list.append(_build_wta_tournament_item(t, "completed"))

    completed_list.reverse()

    items: list[dict] = []
    if active_list:
        items.append({
            "title": f"── 🔴 Active This Week ({len(active_list)}) ──",
            "subtitle": "Filter: wtas slam · wtas 1000 · wtas 500 · wtas 250 · wtas 125 · wtas clay · wtas {city}",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(active_list)

    if upcoming_list:
        items.append({
            "title": f"── 📅 Upcoming WTA Tournaments ({len(upcoming_list)}) ──",
            "subtitle": "Press Enter for Tournament Overview, ⌘ for Draws, ⌥ for Scores",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(upcoming_list)

    if completed_list:
        items.append({
            "title": f"── ✅ Completed Season Tournaments ({len(completed_list)}) ──",
            "subtitle": "Most recent tournaments listed first (WTA 125 hidden by default; type 'wtas 125' to view)",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        })
        items.extend(completed_list)

    if not items:
        alfred_output([{
            "title": f"No WTA tournaments matching '{query}'",
            "subtitle": "Try: wtas slam, wtas 1000, wtas 500, wtas 250, wtas 125, wtas clay, wtas grass, or a city",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    alfred_output(items)


if __name__ == "__main__":
    main()
