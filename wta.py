#!/usr/bin/env python3
"""
wta.py — Alfred keyword: wta
Single entry-point router and Smart Active Window Match Scoreboard module.

Boundary-aware routing (withspace: false):
  wta                → Current WTA Tour scoreboard (Live → Today Upcoming/Final → Recent Main Draw, Singles default)
  wta {filter}       → Filter scoreboard (e.g. `wta sabalenka`, `wta hong kong`, `wta live`, `wta doubles`, `wta qual`, `wta all`)
  wtar [query]       → Official PIF WTA Singles & Doubles Rankings (Top 50 default, `wtar doubles`, `wtar top10`, `wtar all`, `wtar usa`)
  wtas [query]       → Full-Season WTA Tour Calendar (Active → Upcoming → Completed; filter by `1000`, `slam`, `clay`, month, city)
  wtat [query]       → Full Tournament Draw & Results by Round (Final → SF → QF → R16 → R32 → R64)
  wtap {player}      → Unified Player Profile (Rank, Career & 2026 Stats, ⌘ Serve, ⌥ Return) + Inline Recent Matches
"""
from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    extract_ioc_from_flag_url, format_seed, format_set_linescores,
    ioc_to_flag_emoji, matchup_flag_icon_path, sanitize_espn_url,
    utc_to_local, utc_to_local_datetime, utc_to_short_date, WORKFLOW_DIR,
)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard"
CACHE_TTL = 30
RERUN_LIVE = 5.0

ROUND_ORDER: dict[str, int] = {
    "Final": 1,
    "Finals": 1,
    "Championship": 1,
    "3rd Place": 2,
    "Semifinal": 3,
    "Semifinals": 3,
    "Quarterfinal": 4,
    "Quarterfinals": 4,
    "Round of 16": 5,
    "4th Round": 5,
    "Round 4": 5,
    "Round of 32": 6,
    "3rd Round": 6,
    "Round 3": 6,
    "Round of 64": 7,
    "2nd Round": 7,
    "Round 2": 7,
    "Round of 128": 8,
    "1st Round": 8,
    "Round 1": 8,
    "Round Robin": 5,
    "Qualifying Final": 10,
    "Qualifying 2nd Round": 11,
    "Qualifying 1st Round": 12,
}


def _is_subcommand(raw: str, prefix: str) -> bool:
    """
    True only when raw starts directly with `prefix` (no leading space) AND
    either equals `prefix` or is immediately followed by whitespace.
    """
    if not raw.startswith(prefix):
        return False
    rest = raw[len(prefix):]
    return rest == "" or rest[0].isspace()


def main():
    raw_query = sys.argv[1] if len(sys.argv) > 1 else ""
    raw_lower = raw_query.lower()

    if raw_lower and not raw_lower[0].isspace():
        if _is_subcommand(raw_lower, "r"):
            arg = raw_query[1:].strip()
            sys.argv = [sys.argv[0], arg]
            from wta_rankings import main as rankings_main
            rankings_main()
            return

        if _is_subcommand(raw_lower, "s") or _is_subcommand(raw_lower, "c"):
            arg = raw_query[1:].strip()
            sys.argv = [sys.argv[0], arg]
            from wta_schedule import main as schedule_main
            schedule_main()
            return

        if _is_subcommand(raw_lower, "t"):
            arg = raw_query[1:].strip()
            sys.argv = [sys.argv[0], arg]
            from wta_tournament import main as tournament_main
            tournament_main()
            return

        if _is_subcommand(raw_lower, "p"):
            arg = raw_query[1:].strip()
            sys.argv = [sys.argv[0], arg]
            from wta_player import main as player_main
            player_main()
            return

    scores_main(raw_query.strip())


def fetch_scoreboard() -> dict:
    key = "wta_scoreboard"
    data = cache_get(key, CACHE_TTL)
    if data:
        return data
    stale = cache_get_stale(key)
    try:
        data = api_get(SCOREBOARD_URL)
        cache_set(key, data)
        return data
    except Exception:
        if stale:
            return stale
        raise


def extract_competitor_info(comp: dict) -> dict:
    """Extract normalized display info for either a Singles athlete or Doubles pair."""
    is_doubles = comp.get("type") == "team" or "roster" in comp
    seed_str = format_seed(comp)

    if is_doubles:
        roster = comp.get("roster", {})
        athletes = roster.get("athletes", [])
        short_name = roster.get("shortDisplayName") or roster.get("displayName", "Doubles Pair")
        full_name = roster.get("displayName", short_name)
        flags = []
        iocs = []
        links = []
        for a in athletes:
            fl_url = a.get("flag", {}).get("href", "")
            ioc = extract_ioc_from_flag_url(fl_url)
            if ioc:
                iocs.append(ioc)
                flags.append(ioc_to_flag_emoji(ioc))
            for l in a.get("links", []):
                if "playercard" in l.get("rel", []):
                    links.append(sanitize_espn_url(l.get("href")))
        flag_emoji = "".join(flags[:2]) if flags else "🎾"
        primary_ioc = iocs[0] if iocs else ""
        profile_url = links[0] if links else "https://www.wtatennis.com/scores"
        return {
            "id": str(comp.get("id", "")),
            "short_name": short_name,
            "full_name": full_name,
            "seed_str": seed_str,
            "ioc": primary_ioc,
            "flag_emoji": flag_emoji,
            "profile_url": profile_url,
            "winner": bool(comp.get("winner")),
            "linescores": comp.get("linescores", []),
        }

    ath = comp.get("athlete", {})
    aid = str(comp.get("id") or ath.get("id", ""))
    short_name = ath.get("shortName") or ath.get("displayName", "Player")
    full_name = ath.get("displayName") or ath.get("fullName", short_name)
    fl_url = ath.get("flag", {}).get("href", "")
    ioc = extract_ioc_from_flag_url(fl_url)
    flag_emoji = ioc_to_flag_emoji(ioc)

    profile_url = ""
    for l in ath.get("links", []):
        if "playercard" in l.get("rel", []):
            profile_url = sanitize_espn_url(l.get("href"), fallback_id=aid)
            break
    if not profile_url:
        profile_url = sanitize_espn_url(None, fallback_id=aid)

    return {
        "id": aid,
        "short_name": short_name,
        "full_name": full_name,
        "seed_str": seed_str,
        "ioc": ioc,
        "flag_emoji": flag_emoji,
        "profile_url": profile_url,
        "winner": bool(comp.get("winner")),
        "linescores": comp.get("linescores", []),
    }


def format_match_item(
    comp: dict,
    tournament_name: str,
    tournament_url: str,
    discipline_label: str,
) -> tuple[dict, tuple]:
    """
    Format a single WTA match competition into an Alfred item and sort key.
    Sort key: (state_bucket, round_rank, date_sort)
    """
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        raise ValueError("Incomplete competitors")

    c1 = extract_competitor_info(competitors[0])
    c2 = extract_competitor_info(competitors[1])

    status_obj = comp.get("status", {})
    status_type = status_obj.get("type", {})
    state = status_type.get("state", "pre")
    status_detail = status_type.get("shortDetail") or status_type.get("detail", "")
    period = status_obj.get("period", 0)

    round_name = comp.get("round", {}).get("displayName", "Match")
    round_ord = ROUND_ORDER.get(round_name, 9)

    venue_obj = comp.get("venue", {})
    court = venue_obj.get("court", "")
    date_str = comp.get("date") or comp.get("startDate", "")
    short_date = utc_to_short_date(date_str)

    # 1. COMPLETED MATCH (Winner listed first with 'd.')
    if state == "post":
        if c2["winner"] and not c1["winner"]:
            w, l = c2, c1
        else:
            w, l = c1, c2

        linescore_str = format_set_linescores(w["linescores"], l["linescores"])
        score_part = f"  {linescore_str}" if linescore_str else ""
        title = (
            f"{w['flag_emoji']} {w['seed_str']}{w['short_name']}  d.  "
            f"{l['flag_emoji']} {l['seed_str']}{l['short_name']}{score_part}   —  {status_detail or 'Final'}"
        )
        icon_path = matchup_flag_icon_path(w["ioc"], l["ioc"])
        sub_parts = [s for s in [tournament_name, round_name, court, short_date] if s]
        p1_info, p2_info = w, l
        bucket = 2

    # 2. LIVE MATCH
    elif state == "in":
        linescore_str = format_set_linescores(c1["linescores"], c2["linescores"])
        set_label = f"Set {period}" if period else (status_detail or "LIVE")
        score_part = f"  {linescore_str}" if linescore_str else ""
        title = (
            f"🔴 {c1['flag_emoji']} {c1['seed_str']}{c1['short_name']}{score_part}  vs  "
            f"{c2['flag_emoji']} {c2['seed_str']}{c2['short_name']}   —  {set_label}"
        )
        icon_path = matchup_flag_icon_path(c1["ioc"], c2["ioc"])
        sub_parts = [s for s in ["🔴 LIVE", tournament_name, round_name, court] if s]
        p1_info, p2_info = c1, c2
        bucket = 0

    # 3. UPCOMING / SCHEDULED MATCH
    else:
        time_display = utc_to_local(date_str) if comp.get("timeValid", True) and date_str else (short_date or "TBD")
        title = (
            f"{c1['flag_emoji']} {c1['seed_str']}{c1['short_name']}  vs  "
            f"{c2['flag_emoji']} {c2['seed_str']}{c2['short_name']}   —  {time_display}"
        )
        icon_path = matchup_flag_icon_path(c1["ioc"], c2["ioc"])
        sub_parts = [s for s in [tournament_name, round_name, court, discipline_label] if s]
        p1_info, p2_info = c1, c2
        bucket = 1

    item = {
        "title": title,
        "subtitle": " · ".join(sub_parts),
        "arg": tournament_url,
        "icon": {"path": icon_path},
        "mods": {
            "cmd": {
                "subtitle": f"⌘ Open {p1_info['full_name']} ({p1_info['ioc'] or 'WTA'}) Player Profile",
                "arg": p1_info["profile_url"],
            },
            "alt": {
                "subtitle": f"⌥ Open {p2_info['full_name']} ({p2_info['ioc'] or 'WTA'}) Player Profile",
                "arg": p2_info["profile_url"],
            },
        },
    }
    return item, (bucket, round_ord, date_str)


def _is_in_smart_window(comp: dict, now_local: datetime, include_qual: bool, show_all: bool) -> bool:
    if show_all:
        return True
    state = comp.get("status", {}).get("type", {}).get("state", "pre")
    if state in ("in", "pre"):
        return True

    round_name = comp.get("round", {}).get("displayName", "")
    if not include_qual and "qualifying" in round_name.lower():
        return False

    date_str = comp.get("date") or comp.get("startDate", "")
    if date_str:
        try:
            dt = utc_to_local_datetime(date_str)
            if (now_local.date() - dt.date()) <= timedelta(days=3):
                return True
        except Exception:
            pass

    return ROUND_ORDER.get(round_name, 9) <= 5


def _matches_query(comp: dict, tournament_name: str, discipline_slug: str, q: str) -> bool:
    if not q or q in ("all", "doubles", "dbl", "qual", "qualifying"):
        return True
    state = comp.get("status", {}).get("type", {}).get("state", "pre")
    if q == "live":
        return state == "in"
    if q in ("final", "completed", "finished", "results"):
        return state == "post"
    if q in ("upcoming", "scheduled", "next"):
        return state == "pre"

    round_name = comp.get("round", {}).get("displayName", "").lower()
    if q in ("sf", "semi", "semifinal", "semifinals"):
        return "semi" in round_name
    if q in ("qf", "quarter", "quarterfinal", "quarterfinals"):
        return "quarter" in round_name

    haystack_parts = [tournament_name.lower(), round_name, discipline_slug.lower()]
    for c in comp.get("competitors", []):
        info = extract_competitor_info(c)
        haystack_parts.extend([
            info["full_name"].lower(),
            info["short_name"].lower(),
            info["ioc"].lower(),
        ])
    haystack = " ".join(haystack_parts)
    return all(tok in haystack for tok in q.split())


def scores_main(filter_query: str = ""):
    try:
        sb = fetch_scoreboard()
    except Exception as e:
        alfred_error("Could not fetch WTA Tour scoreboard", str(e))
        return

    events = sb.get("events", [])
    q = filter_query.lower().strip()

    want_doubles = q in ("doubles", "dbl") or "doubles" in q.split()
    want_qual = q in ("qual", "qualifying") or "qual" in q.split()
    show_all = bool(q)

    now_local = datetime.now().astimezone()
    output_items: list[dict] = []
    has_live = False

    for ev in events:
        groupings = ev.get("groupings", [])
        if not groupings:
            continue

        t_name = ev.get("name", "WTA Tournament")
        t_venue = ev.get("venue", {}).get("fullName", "")
        t_url = "https://www.wtatennis.com/scores"
        for l in ev.get("links", []):
            if l.get("href") and "/null/" not in l.get("href", ""):
                t_url = l["href"]
                break

        for grp in groupings:
            g_info = grp.get("grouping", {})
            g_slug = g_info.get("slug", "")
            g_label = g_info.get("displayName", "Singles")

            if want_doubles and "doubles" not in g_slug:
                continue
            if not want_doubles and "doubles" in g_slug and not (q and q not in ("live", "final", "upcoming", "qual", "all")):
                continue

            comps = grp.get("competitions", [])
            has_main_draw = any("qualifying" not in c.get("round", {}).get("displayName", "").lower() for c in comps)

            matched_tuples = []
            for comp in comps:
                if not _is_in_smart_window(comp, now_local, include_qual=(want_qual or not has_main_draw), show_all=show_all):
                    continue
                if not _matches_query(comp, t_name, g_slug, q):
                    continue
                try:
                    item, sort_key = format_match_item(comp, t_name, t_url, g_label)
                    if sort_key[0] == 0:
                        has_live = True
                    matched_tuples.append((sort_key, item))
                except Exception:
                    continue

            if matched_tuples:
                matched_tuples.sort(key=lambda x: (x[0][0], x[0][1], x[0][2]))
                loc_suffix = f" ({t_venue} · {g_label})" if t_venue else f" ({g_label})"
                output_items.append({
                    "title": f"── 🏆 {t_name}{loc_suffix} ──",
                    "subtitle": "Filter: wta live · wta doubles · wta {player} · Full draw: wtat · Rankings: wtar · Schedule: wtas",
                    "valid": False,
                    "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
                })
                output_items.extend(it for _, it in matched_tuples[:25])

    if not output_items:
        msg = f"No WTA matches found for '{filter_query}'" if filter_query else "No active WTA matches in the current window 🎾"
        sub = "Try: wta all, wta doubles, wtat (full tournament draw), wtas (tour calendar), or wtar (rankings)"
        alfred_output([{
            "title": msg,
            "subtitle": sub,
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    alfred_output(output_items, rerun=RERUN_LIVE if has_live else None)


if __name__ == "__main__":
    main()
