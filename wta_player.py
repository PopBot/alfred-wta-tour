#!/usr/bin/env python3
"""
wta_player.py — Alfred keyword: wtap {player}
Unified WTA Player Profile, Season Service/Return Stats & Inline Recent Match Results:
  - Multi-match: Lists matching WTA players with World Rank, 2026 YTD & Career W-L/Titles/Prize,
    `⌘` 2026 Service Stats, and `⌥` 2026 Return Stats.
  - Single-player match:
      Row 1     → Player Overview (Rank, YTD & Career W-L/Titles/Prize, ⌘ Serve Stats, ⌥ Return Stats)
      Rows 2..11→ Last 10 tournament matches inline (Tournament, Surface, Round, Opponent & Seed, W/L, Set Score)
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import os
import re
import sys

from utils import (
    alfred_error, alfred_output,
    api_get, cache_get, cache_get_stale, cache_set,
    extract_ioc_from_flag_url, ioc_to_flag_emoji, matchup_flag_icon_path,
    player_headshot_path, sanitize_espn_url, WORKFLOW_DIR,
)

WTA_PLAYER_SEARCH_URL = "https://api.wtatennis.com/tennis/players/"
ESPN_SEARCH_URL = "https://site.web.api.espn.com/apis/search/v2"
CACHE_TTL = 600  # 10 minutes


def search_wta_players(query: str) -> list[dict]:
    key = f"wta_player_search_{query.lower().strip()}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    def _fetch_pulselive():
        try:
            res = api_get(WTA_PLAYER_SEARCH_URL, params={"page": 0, "pageSize": 8, "name": query}, timeout=5)
            return res.get("content", []) if isinstance(res, dict) else []
        except Exception:
            return []

    def _fetch_espn():
        try:
            res = api_get(ESPN_SEARCH_URL, params={"query": query, "limit": 8, "type": "player"}, timeout=5)
            out = []
            for grp in res.get("results", []):
                for item in grp.get("contents", []):
                    if item.get("sport") == "tennis" and item.get("defaultLeagueSlug") == "wta":
                        uid = item.get("uid", "")
                        aid = uid.split("~a:")[-1] if "~a:" in uid else str(item.get("id", ""))
                        out.append({
                            "espn_id": aid,
                            "name": item.get("displayName", ""),
                            "web_url": sanitize_espn_url(item.get("link", {}).get("web"), fallback_id=aid),
                            "headshot_url": item.get("image", {}).get("default"),
                        })
            return out
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_pl = pool.submit(_fetch_pulselive)
        f_es = pool.submit(_fetch_espn)
        pl_list = f_pl.result()
        es_list = f_es.result()

    # Map ESPN results by lowercase full name or last name
    espn_by_name: dict[str, dict] = {}
    for e in es_list:
        dn = e["name"].lower().strip()
        espn_by_name[dn] = e
        espn_by_name[dn.split()[-1]] = e

    # Also check cached ESPN WTA rankings for headshot/id
    rk_cache = cache_get_stale("wta_espn_rankings")
    if rk_cache:
        for entry in rk_cache.get("rankings", [{}])[0].get("ranks", []):
            ath = entry.get("athlete", {})
            dn = ath.get("displayName", "").lower().strip()
            aid = str(ath.get("id", ""))
            if dn and aid and dn not in espn_by_name:
                e_obj = {
                    "espn_id": aid,
                    "name": ath.get("displayName", ""),
                    "web_url": sanitize_espn_url(None, fallback_id=aid),
                    "headshot_url": ath.get("headshot"),
                    "rank": entry.get("current"),
                }
                espn_by_name[dn] = e_obj
                espn_by_name[dn.split()[-1]] = e_obj

    merged: list[dict] = []
    seen_names: set[str] = set()

    for p in pl_list:
        full_name = p.get("fullName", "").strip()
        if not full_name:
            continue
        fn_low = full_name.lower()
        seen_names.add(fn_low)
        es_match = espn_by_name.get(fn_low) or espn_by_name.get(fn_low.split()[-1], {})
        merged.append({
            "wta_id": str(p.get("id", "")),
            "espn_id": str(es_match.get("espn_id", "")),
            "name": full_name,
            "ioc": (p.get("countryCode") or "").upper(),
            "dob": p.get("dateOfBirth", ""),
            "headshot_url": es_match.get("headshot_url"),
            "web_url": es_match.get("web_url"),
            "rank": es_match.get("rank"),
        })

    for e in es_list:
        fn_low = e["name"].lower().strip()
        if fn_low not in seen_names:
            merged.append({
                "wta_id": "",
                "espn_id": e["espn_id"],
                "name": e["name"],
                "ioc": "",
                "dob": "",
                "headshot_url": e.get("headshot_url"),
                "web_url": e.get("web_url"),
                "rank": e.get("rank"),
            })

    q_low = query.lower().strip()
    exact = [
        m for m in merged
        if m["name"].lower() == q_low or m["name"].lower().split()[-1] == q_low
    ]
    if len(exact) == 1:
        merged = exact

    cache_set(key, merged)
    return merged


def _compute_age(dob_str: str) -> int | None:
    if not dob_str:
        return None
    try:
        b = date.fromisoformat(dob_str[:10])
        today = date.today()
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    except Exception:
        return None


def fetch_wta_season_stats_and_matches(wta_id: str, include_matches: bool = False) -> tuple[dict, list[dict]]:
    if not wta_id:
        return {}, []
    year = datetime.now().year
    s_key = f"wta_yr_stats_{wta_id}_{year}"
    m_key = f"wta_yr_matches_{wta_id}_{year}"

    stats_data = cache_get(s_key, CACHE_TTL)
    matches_data = cache_get(m_key, CACHE_TTL) if include_matches else []

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_stat = None if stats_data is not None else pool.submit(
            api_get, f"https://api.wtatennis.com/tennis/players/{wta_id}/year/{year}", None, 5
        )
        f_mtch = None if (not include_matches or matches_data is not None) else pool.submit(
            api_get,
            f"https://api.wtatennis.com/tennis/players/{wta_id}/matches",
            {"page": 0, "pageSize": 100, "year": year},
            6,
        )
        if f_stat:
            try:
                stats_data = f_stat.result()
                cache_set(s_key, stats_data)
            except Exception:
                stats_data = cache_get_stale(s_key) or {}
        if f_mtch:
            try:
                raw_m = f_mtch.result()
                matches_data = raw_m.get("matches", []) if isinstance(raw_m, dict) else []
                cache_set(m_key, matches_data)
            except Exception:
                matches_data = cache_get_stale(m_key) or []

    return (stats_data or {}).get("stats", {}), (matches_data or [])


def fetch_espn_wta_career(espn_id: str) -> dict:
    if not espn_id:
        return {}
    key = f"wta_espn_career_{espn_id}"
    cached = cache_get(key, CACHE_TTL)
    if cached is not None:
        return cached

    info: dict = {}
    try:
        st = api_get(f"https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta/athletes/{espn_id}/statistics", timeout=5)
        for cat in st.get("splits", {}).get("categories", []):
            for s in cat.get("stats", []):
                info[s.get("name", "")] = s.get("displayValue")
    except Exception:
        pass
    cache_set(key, info)
    return info


def build_player_overview_item(p: dict, include_matches: bool = False) -> tuple[dict, list[dict]]:
    wta_id = p.get("wta_id", "")
    espn_id = p.get("espn_id", "")
    name = p.get("name", "WTA Player")

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_wta = pool.submit(fetch_wta_season_stats_and_matches, wta_id, True)
        f_esp = pool.submit(fetch_espn_wta_career, espn_id)
        wta_stats, raw_matches = f_wta.result()
        espn_car = f_esp.result()

    # Compute 2026 Singles W-L & Titles from matches list
    singles_matches = [m for m in raw_matches if m.get("s_d_flag") == "S" and m.get("reason_code") != "B"]
    ytd_w = sum(1 for m in singles_matches if m.get("winner") == 1)
    ytd_l = sum(1 for m in singles_matches if m.get("winner") == 2)
    ytd_titles = sum(1 for m in singles_matches if m.get("round_name") == "F" and m.get("winner") == 1)

    rank = wta_stats.get("Current_Rank") or p.get("rank")
    ioc = (wta_stats.get("Nationality") or p.get("ioc") or "").upper()
    flag_emoji = ioc_to_flag_emoji(ioc)
    age = _compute_age(p.get("dob", ""))

    car_w = espn_car.get("singlesWon", "—")
    car_l = espn_car.get("singlesLost", "—")
    car_t = espn_car.get("singlesTitles", "0")
    car_p = ""
    if espn_car.get("prize"):
        try:
            car_p = f"${int(float(espn_car['prize'])):,}"
        except Exception:
            car_p = ""

    rank_prefix = f"#{rank} " if rank else ""
    age_str = f"  (Age {age})" if age else ""
    title = f"{rank_prefix}{name}  {flag_emoji} {ioc}{age_str}".strip()

    sub_parts = []
    if singles_matches:
        sub_parts.append(f"2026: {ytd_w}-{ytd_l} ({ytd_titles} Titles · {len(singles_matches)} Matches)")
    elif wta_stats.get("MatchCount"):
        sub_parts.append(f"2026 Matches: {wta_stats['MatchCount']}")

    if car_w != "—":
        car_str = f"Career: {car_w}-{car_l} ({car_t} Titles" + (f" · {car_p}" if car_p else "") + ")"
        sub_parts.append(car_str)

    slug = name.lower().replace(" ", "-")
    wta_profile_url = f"https://www.wtatennis.com/players/{wta_id}/{slug}" if wta_id else (p.get("web_url") or "https://www.wtatennis.com/players")
    wta_stats_url = f"{wta_profile_url}/stats" if wta_id else wta_profile_url

    if wta_stats:
        aces = wta_stats.get("Aces", "—")
        df = wta_stats.get("Double_Faults", "—")
        fs_pct = wta_stats.get("first_serve_percent", "—")
        fs_won = wta_stats.get("first_serve_won_percent", "—")
        ss_won = wta_stats.get("second_serve_won_percent", "—")
        sg_won = wta_stats.get("service_games_won_percent", "—")
        bp_svd = wta_stats.get("breakpoint_saved_percent", "—")
        cmd_sub = (
            f"⌘ Serve (2026): {aces} Aces · {df} DF · {fs_pct}% 1st Srv · "
            f"{fs_won}% 1st Won · {ss_won}% 2nd Won · {sg_won}% Srv Gms Won · {bp_svd}% BP Saved"
        )

        r1_won = wta_stats.get("first_return_percent", "—")
        r2_won = wta_stats.get("second_return_percent", "—")
        rg_won = wta_stats.get("return_games_won_percent", "—")
        bp_cnv = wta_stats.get("breakpoint_converted_percent", "—")
        bp_won = wta_stats.get("Break_Points_Converted", "—")
        bp_ch = wta_stats.get("Break_Point_Chances", "—")
        tp_won = wta_stats.get("total_points_won_percent", "—")
        alt_sub = (
            f"⌥ Return (2026): {r1_won}% 1st Ret Won · {r2_won}% 2nd Ret Won · "
            f"{rg_won}% Ret Gms Won · {bp_cnv}% BP Conv ({bp_won}/{bp_ch}) · {tp_won}% Tot Pts Won"
        )
    else:
        cmd_sub = f"⌘ Open {name}'s WTA Statistics Profile"
        alt_sub = f"⌥ Open {name}'s WTA Match History"

    icon_path = player_headshot_path(espn_id or wta_id, direct_url=p.get("headshot_url"), fallback_ioc=ioc)

    overview_item = {
        "title": title,
        "subtitle": "  ·  ".join(sub_parts) if sub_parts else "WTA Tour Player Profile",
        "arg": wta_profile_url,
        "icon": {"path": icon_path},
        "mods": {
            "cmd": {"subtitle": cmd_sub, "arg": wta_stats_url},
            "alt": {"subtitle": alt_sub, "arg": f"{wta_profile_url}/matches" if wta_id else wta_profile_url},
        },
    }

    match_items: list[dict] = []
    if include_matches and singles_matches:
        # Reverse so most recent matches appear first
        for m in reversed(singles_matches[-12:]):
            won = m.get("winner") == 1
            wl_badge = "✅ W" if won else "❌ L"
            opp = m.get("opponent") or {}
            opp_name = opp.get("fullName") or m.get("team_name_2", "Opponent")
            opp_ioc = (opp.get("countryCode") or "").upper()
            opp_flag = ioc_to_flag_emoji(opp_ioc)
            opp_seed = f"[{m['seed_2']}] " if m.get("seed_2") else ""
            opp_rk = f"(#{m['rank_2']})" if m.get("rank_2") else ""

            raw_scores = re.sub(r"\s+", ", ", (m.get("scores") or "").strip())
            t_obj = m.get("tournament", {})
            t_title = (t_obj.get("title") or m.get("TournamentName", "WTA")).split(" - ")[0].strip()
            t_level = t_obj.get("level", "")
            surface = t_obj.get("surface") or m.get("Surface", "").title()
            round_name = m.get("round_name", "")
            s_date = (m.get("StartDate") or "")[:10]

            m_title = f"{wl_badge}  vs  {opp_flag} {opp_seed}{opp_name} {opp_rk}   {raw_scores}   —  {t_title} ({round_name})"
            m_sub = "  ·  ".join([x for x in [s_date, t_title, t_level, surface, f"Round: {round_name}"] if x])
            m_icon = matchup_flag_icon_path(ioc, opp_ioc)

            match_items.append({
                "title": m_title,
                "subtitle": m_sub,
                "arg": f"{wta_profile_url}/matches" if wta_id else wta_profile_url,
                "icon": {"path": m_icon},
            })

    return overview_item, match_items[:10]


def main():
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if len(query) < 2:
        alfred_output([{
            "title": "Type a WTA player's name...",
            "subtitle": "e.g. wtap sabalenka, wtap swiatek, wtap rybakina, wtap gauff, wtap pegula",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    matched = search_wta_players(query)
    if not matched:
        alfred_output([{
            "title": f"No WTA players found for '{query}'",
            "subtitle": "Try searching by last name (e.g. wtap sabalenka, wtap swiatek, wtap gauff)",
            "valid": False,
            "icon": {"path": os.path.join(WORKFLOW_DIR, "icon.png")},
        }])
        return

    # Single-player Unified View: Row 1 = Overview + Serve/Return Mods, Rows 2..11 = Recent Matches
    if len(matched) == 1:
        p = matched[0]
        overview, recent = build_player_overview_item(p, include_matches=True)
        items = [overview]
        if recent:
            items.append({
                "title": f"── 🎾 {p['name']} · Recent {datetime.now().year} Singles Matches ({len(recent)}) ──",
                "subtitle": "Hold ⌘ on Row 1 for 2026 Service Stats · Hold ⌥ on Row 1 for 2026 Return Stats",
                "valid": False,
                "icon": overview["icon"],
            })
            items.extend(recent)
        alfred_output(items)
        return

    # Multi-player match: fetch top 5 in parallel
    subset = matched[:5]
    built: list[tuple[int, dict]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_map = {pool.submit(build_player_overview_item, p, False): idx for idx, p in enumerate(subset)}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            try:
                ov, _ = fut.result()
                built.append((idx, ov))
            except Exception:
                pass

    built.sort(key=lambda x: x[0])
    alfred_output([it for _, it in built])


if __name__ == "__main__":
    main()
