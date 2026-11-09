# 🎯 WTA Tour (`wta`) Alfred Workflow — Specification & Architecture Plan

## 1. Overview
Build a standalone, zero-dependency Alfred 5 workflow for the **Women's Hologic WTA Tour** (`wta`) inside `/Users/jarodwong/Documents/Alfred Workflows/wta/alfred-wta-tour/`. It mirrors the **ATP Tour** workflow and evolves the architecture of [alfred-mlb-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/mlb/alfred-mlb-scores), [alfred-nfl-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/nfl/alfred-nfl-scores), and [alfred-ncaaf-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/ncaaf/alfred-ncaaf-scores), tailored for women's professional tournament tennis.

### Key Architectural Highlights
- **Hybrid Zero-Auth API Architecture ([ADR-0001](file:///Users/jarodwong/Documents/Alfred%20Workflows/wta/docs/adr/0001-hybrid-espn-and-official-wta-pulselive-api-architecture.md))**:
  - **ESPN Public Tennis API** (`site.api.espn.com`, `sports.core.api.espn.com`, `site.web.api.espn.com`) powers the Tournament & Match Scoreboard, Top 150 Singles Rankings, Player Headshots, and Country Flag PNGs.
  - **Official WTA Tour PulseLive API** (`api.wtatennis.com/tennis/...`) powers the Full-Season WTA Tournament Calendar, Singles & Doubles Official Rankings, Live Match Point/Serve Enrichment, 2026 Service (`⌘`) & Return (`⌥`) Player Statistics (`/players/{id}/year/{year}`), and Single-Call Recent Player Match History (`/players/{id}/matches`).
- **Official WTA Tour Workflow Logo (`icon.png`)**: Rendered from the official WTA Tour vector mark (`File:WTA 2025.svg` via Wikimedia Commons) centered onto a crisp 64×64 square PNG.
- **Boundary-Aware Subcommand Routing ([ADR-0002](file:///Users/jarodwong/Documents/Alfred%20Workflows/wta/docs/adr/0002-boundary-aware-subcommand-routing.md))**: Single Script Filter (`keyword: wta`, `withspace: false`) distinguishes space-separated scoreboard filters (`wta sabalenka`, `wta wuhan`, `wta doubles`, `wta live`) from attached subcommand suffixes (`wtar`, `wtas`, `wtat`, `wtap`).
- **Dual Country Flag Matchup Icons + Player Headshots**:
  - **Scoreboard (`wta`) & Tournament Draw (`wtat`)**: Composite 64×64 side-by-side Country Flag icons (`matchup_{ioc1}_{ioc2}.png`) via [`image_utils.py`](file:///Users/jarodwong/Documents/Alfred%20Workflows/ncaaf/alfred-ncaaf-scores/image_utils.py) for instant rendering across main and qualifying draws, paired with inline flag emojis (`🇧🇾`, `🇵🇱`, `🇺🇸`, `🇰🇿`).
  - **Rankings (`wtar`) & Player Search (`wtap`)**: High-resolution ESPN Player Headshots (`headshots/{athlete_id}.png`, 7-day cache TTL) with Country Flag PNG fallback.
- **URL Sanitization**: Replaces broken `https://www.espn.com/null/player/...` links in ESPN's WTA rankings response with valid `https://www.espn.com/tennis/player/_/id/{id}/{slug}` and `https://www.wtatennis.com/players/{wta_id}/{slug}` URLs.

---

## 2. Alfred Keystroke Commands & UX Flow

A single Script Filter in `info.plist` (`keyword: wta`, `withspace: false`) passes `"$1"` (unstripped) to `python3 wta.py "$1"`:

| Command | Raw `$1` | Routed Module & Behavior |
| :--- | :--- | :--- |
| `wta` | `""` | **Scoreboard (`wta.py`)**: Smart Active Window of current WTA tournaments—`Live` matches first, then `Today` Upcoming/Final matches, then recent Main Draw matches (`Singles` default). |
| `wta {filter}` | `" {filter}"` (starts with space) | **Filtered Scoreboard (`wta.py`)**: Filters active tournament matches by player (`wta sabalenka`, `wta gauff`), tournament (`wta hong kong`), `wta live`, `wta doubles`, `wta qual`, or `wta all`. |
| `wtar` / `wtar {query}` | `"r"` or `"r {query}"` | **Rankings (`wta_rankings.py`)**: Official PIF WTA Rankings—Singles Top 50 by default; supports `wtar doubles` (WTA Doubles Rankings via PulseLive), `wtar top10`, `wtar top25`, `wtar all` (Top 150), player name (`wtar swiatek`), or country (`wtar usa`, `wtar cze`). |
| `wtas` / `wtas {query}` | `"s"` or `"s {query}"` | **Tour Schedule / Calendar (`wta_schedule.py`)**: Full-season WTA Tour & Grand Slam calendar (excluding ITF & WTA 125 clutter by default) grouped by `Active This Week` → `Upcoming` → `Completed`. Filter by tier (`wtas slam`, `wtas 1000`, `wtas 500`, `wtas 250`, `wtas 125`), surface (`wtas clay`, `wtas grass`, `wtas hard`), month, or city/name. |
| `wtat` / `wtat {query}` | `"t"` or `"t {query}"` | **Tournament Draw & Results (`wta_tournament.py`)**: Full round-by-round Main Draw progression (`Final` → `Semifinals` → `Quarterfinals` → `R16` → `R32` → `R64` → `R128`) for active WTA tournaments. Supports `wtat doubles` or tournament name filter. |
| `wtap {player}` | `"p {player}"` | **Unified Player Profile, Stats & Recent Matches (`wta_player.py`)**: Multi-match shows matching WTA players with rank, YTD & Career W-L/Titles/Prize, `⌘` Serve stats, and `⌥` Return stats. Single-player match shows Row 1 as Player Overview + Rows 2–11 as the player's last 10 tournament matches inline. |

---

## 3. Directory & File Structure

```text
wta/
├── CONTEXT.md                  ← Domain model & ubiquitous language glossary
├── AGY_WTA_ALFRED_SPEC.md      ← This specification and architecture plan
├── docs/
│   └── adr/
│       ├── 0001-hybrid-espn-and-official-wta-pulselive-api-architecture.md
│       └── 0002-boundary-aware-subcommand-routing.md
└── alfred-wta-tour/            ← Workflow source & packaging root (when implemented)
    ├── wta.py                  ← Router + Smart Active Window Match Scoreboard
    ├── wta_rankings.py         ← Top 150 WTA Singles & Doubles Rankings (Country / Slice / Player filters)
    ├── wta_schedule.py         ← Full-Season WTA Tournament Calendar (Active / Upcoming / Completed)
    ├── wta_tournament.py       ← Round-by-round Tournament Draw & Results viewer
    ├── wta_player.py           ← Unified Player Profile (⌘ Serve / ⌥ Return) + Inline Recent Matches
    ├── utils.py                ← Cache, HTTP session, IOC flag emoji & PNG helpers, set linescore formatter
    ├── image_utils.py          ← Pure-Python PNG decoder, resizer, and dual-flag matchup compositor
    ├── download_assets.py      ← One-time build script for official WTA `icon.png` and common IOC flags
    ├── build.py                ← Packages `WTA Tour.alfredworkflow`
    ├── info.plist              ← Alfred 5 workflow XML (`keyword: wta`, `withspace: false`)
    ├── icon.png                ← Official WTA Tour 64×64 PNG workflow icon
    ├── flags/                  ← Pre-bundled 64×64 PNG country flags (`usa.png`, `pol.png`, `kaz.png`, etc.)
    └── lib/                    ← Vendored Python HTTP dependencies (`requests`, `urllib3`, `certifi`, `idna`, `charset_normalizer`)
```

---

## 4. API Endpoints & Data Nuances

### 4.1 Match Scoreboard (`wta.py`) & Tournament Draw (`wta_tournament.py`)
1. **Primary Endpoint (ESPN WTA Scoreboard)**:
   ```http
   GET https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard
   ```
   - Returns `events[]` (active WTA tournaments this week).
   - Note: Events with empty `groupings: []` (such as cancelled or placeholder WTA 125 entries like `1083-2026 American Tennis Open Miami`) are filtered out automatically or cross-filled via WTA PulseLive.
   - Inside each event, `groupings[]` separates `"womens-singles"` (`grouping.slug == "womens-singles"`) and `"womens-doubles"` (`grouping.slug == "womens-doubles"`).
2. **WTA PulseLive Match Enrichment**:
   ```http
   GET https://api.wtatennis.com/tennis/tournaments/{tournamentGroupId}/{year}/matches
   ```
   - Provides live in-game point scores (`PointA`, `PointB`), server indicator (`Serve`), tiebreak scores (`ScoreTbSet1..3`), and total match duration (`MatchTimeTotal`).
3. **Row Display Format**:
   - **Tournament Section Header (`valid: false`)**:
     - *Title*: `── 🏆 Prudential Hong Kong Tennis Open (Hong Kong · Women's Singles) ──`
     - *Subtitle*: `Filter: wta live · wta doubles · wta qual · wta {player} · Full draw: wtat`
   - **Live Match (`state == "in"`)**:
     - *Title*: `🔴 🇧🇾 [1] A. Sabalenka  6-3, 4-3 (30-15*)  vs  🇵🇱 [2] I. Swiatek  —  Set 2`
     - *Subtitle*: `WTA Finals · Semifinal · Centre Court · 1h 12m`
   - **Upcoming Match (`state == "pre"`)**:
     - *Title*: `🇺🇸 C. Liu  vs  🇵🇭 [2] A. Eala  —  Sun 12:00 AM`
     - *Subtitle*: `Prudential Hong Kong Tennis Open · Final · Centre Court`
   - **Completed Match (`state == "post"`, Winner Listed First with `d.`)**:
     - *Title*: `🇬🇧 M. Stojsavljevic  d.  🇷🇺 [7] A. Ibragimova   1-6, 6-2, 6-1  —  Final`
     - *Subtitle*: `Prudential Hong Kong Tennis Open · Qualifying R1 · Court 3`
   - **Icon**: Composite 64×64 dual-flag icon `matchup_{ioc1}_{ioc2}.png`.

### 4.2 World Rankings (`wta_rankings.py`)
1. **Singles Rankings (ESPN + WTA PulseLive Enrichment)**:
   ```http
   GET https://site.api.espn.com/apis/site/v2/sports/tennis/wta/rankings
   GET https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankSingles&sort=asc&metric=SINGLES
   ```
   - Combines ESPN's Top 150 WTA Singles rankings (which include `headshot`, `flag`, `age`, `birthPlace`, and `previous` rank) with WTA PulseLive's `tournamentsPlayed` count.
2. **Doubles Rankings (`wtar doubles`)**:
   ```http
   GET https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankDoubles&sort=asc&metric=DOUBLES
   ```
   - Displays Top Doubles players (e.g., `#1 Katerina Siniakova 🇨🇿 CZE — 11,050 pts · 15 Tournaments`).
3. **Row Format**:
   - *Title*: `#1 Elena Rybakina  🇰🇿 KAZ  —  8,099 pts  (—)`
   - *Subtitle*: `Prev: #1  ·  Tournaments: 20  ·  Age: 27  ·  Moscow, Russia`
   - *Icon*: Cached player headshot `headshots/{athlete_id}.png` (falls back to `flags/{ioc}.png`).
- **Supported Filters**:
  - Default (`wtar`): Top 50 Singles.
  - Doubles (`wtar doubles` / `wtar dbl`): Top 50 Doubles.
  - Slice (`wtar top10`, `wtar top25`, `wtar all`): Top 10, Top 25, or all 150.
  - Country (`wtar usa`, `wtar cze`, `wtar pol`, `wtar kaz`): All ranked players from that country.
  - Player Name (`wtar sabalenka`, `wtar gauff`): Direct filter by player name.

### 4.3 Full-Season Tour Schedule / Calendar (`wta_schedule.py`)
```http
GET https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100&excludeLevels=ITF&from={year}-01-01&to={year}-12-31
```
- Returns all WTA Tour events for the year.
- **Default Tier Filtering**: By default, includes `Grand Slam`, `Finals`, `WTA 1000`, `WTA 500`, and `WTA 250` (excluding lower-tier `WTA 125` events unless the user types `wtas 125` or `wtas all`).
- **Grouping & Sorting**:
  1. `── 🔴 Active This Week ──` (`startDate <= today <= endDate`)
  2. `── 📅 Upcoming WTA Tournaments ──` (`startDate > today`, chronological)
  3. `── ✅ Completed 2026 Tournaments ──` (`endDate < today`, reverse-chronological)
- **Row Format**:
  - *Title*: `📅 FAGE WTA Finals Indian Wells  [Finals]  —  Nov 8–15`
  - *Subtitle*: `Indian Wells, USA  ·  Hard (Outdoor)  ·  Draw: 8S / 8D  ·  Purse: $15,250,000`
  - *`Enter`*: Open Tournament page on `wtatennis.com`.

### 4.4 Unified Player Profile, Stats & Recent Matches (`wta_player.py`)
Combines ESPN's player headshots/career totals with WTA PulseLive's rich current-season stats and single-call match log:
1. **Player Lookup & Headshot**:
   ```http
   GET https://api.wtatennis.com/tennis/players/?page=0&pageSize=8&name={query}
   GET https://site.web.api.espn.com/apis/search/v2?query={query}&limit=6&type=player
   ```
2. **2026 Season Service & Return Stats (WTA PulseLive)**:
   ```http
   GET https://api.wtatennis.com/tennis/players/{wta_id}/year/{year}
   ```
   - Returns `Current_Rank`, `MatchCount`, `Aces`, `Double_Faults`, `first_serve_percent`, `first_serve_won_percent`, `second_serve_won_percent`, `service_games_won_percent`, `breakpoint_saved_percent`, `first_return_percent`, `second_return_percent`, `return_games_won_percent`, `breakpoint_converted_percent`, and `total_points_won_percent`.
3. **Career Totals (ESPN Core API)**:
   ```http
   GET https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta/athletes/{espn_id}/statistics
   ```
   - Returns `singlesWon`, `singlesLost`, `singlesTitles`, `doublesTitles`, and `prize`.
4. **Row 1 (Player Overview & Modifier Stats)**:
   - *Title*: `#2 Aryna Sabalenka  🇧🇾 BLR  (Age 28 · 58 Matches in 2026)`
   - *Default Subtitle*: `Rank: #2  ·  Career: 412-185 (18 Singles Titles · $32.4M Prize)`
   - *`⌘` (Cmd — 2026 Service Stats)*: `⌘ Serve (2026): 298 Aces · 138 DF · 63.8% 1st Srv · 70.7% 1st Won · 53.9% 2nd Won · 81.5% Srv Gms Won · 64.2% BP Saved`
   - *`⌥` (Alt — 2026 Return Stats)*: `⌥ Return (2026): 35.5% 1st Ret Won · 56.9% 2nd Ret Won · 36.0% Ret Gms Won · 44.6% BP Conv (217/487) · 54.2% Tot Pts Won`
5. **Rows 2–11 (Inline Recent Match Results when `len(matched_players) == 1`)**:
   ```http
   GET https://api.wtatennis.com/tennis/players/{wta_id}/matches?page=0&pageSize=10&year={year}
   ```
   - Returns the player's 10 most recent 2026 tournament matches in a single HTTP request, displaying Tournament Name, Surface, Round, Opponent & Seed, W/L, and Set Scores inline.

---

## 5. Caching Strategy (`utils.py`)
- Uses Alfred's `$alfred_workflow_cache` (`~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/com.popbot.alfred-wta-tour`).
- Stale-while-revalidate fallback on network errors.
- **TTLs**:
  - Scoreboard & Live Matches (`wta`): `30` seconds (`"rerun": 5.0` when any displayed match is live)
  - Tournament Draw (`wtat`): `120` seconds (2 minutes)
  - Rankings (`wtar`): `600` seconds (10 minutes)
  - Tour Calendar (`wtas`): `3600` seconds (1 hour)
  - Player Stats & Recent Matches (`wtap`): `600` seconds (10 minutes)
  - Player Headshots & Country Flags: `604800` seconds (7 days)
