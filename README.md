# 🎾 WTA Tour — Alfred 5 Workflow

Track **Women's Hologic WTA Tour** live and daily tournament match scores, official PIF WTA Singles & Doubles Rankings, the full-season tournament calendar, tournament draws, and player profiles with current-season Service & Return statistics and recent match results directly inside Alfred 5.

## Features
- **Hybrid Zero-Auth API Architecture**: Combines ESPN's public tennis API (scoreboards, Top 150 rankings, player headshots, country flags, career totals) with the official WTA Tour PulseLive API (`api.wtatennis.com/tennis/...` for the full-season tournament calendar, Singles & Doubles rankings, 2026 Service & Return stats, and single-call recent match history).
- **Smart Active Window Scoreboard (`wta`)**: Displays live matches first, then today's upcoming/completed matches and recent Main Draw matches (`Singles` default), with standard tennis set linescores (`6-3, 6-7(4), 6-2`) and dual country-flag matchup icons.
- **Official PIF WTA Rankings (`wtar`)**: Top 50 Singles default plus **Doubles Rankings (`wtar doubles`)**, with instant filters for `wtar top10`, `wtar top25`, `wtar all` (Top 150), country codes (`wtar usa`, `wtar cze`, `wtar pol`), or player names (`wtar sabalenka`).
- **Full-Season Tournament Calendar (`wtas`)**: Complete Hologic WTA Tour & Grand Slam calendar (excluding ITF and WTA 125 clutter by default) grouped into `Active This Week`, `Upcoming`, and `Completed`, with tier badges (`Grand Slam`, `Finals`, `WTA 1000`, `WTA 500`, `WTA 250`), surface, indoor/outdoor, draw sizes, and prize money.
- **Tournament Draw Viewer (`wtat`)**: Browse the full round-by-round Main Draw (`Final` → `Semifinal` → `Quarterfinal` → `R16` → `R32` → `R64`), plus `wtat doubles` and `wtat qual`.
- **Unified Player View (`wtap {player}`)**: Row 1 displays World Rank, 2026 YTD & Career W-L/Titles/Prize, **`⌘` 2026 Service Stats** (Aces, DF, 1st Serve %, 1st/2nd Serve Won %, Service Games Won %, BP Saved %), and **`⌥` 2026 Return Stats** (1st/2nd Return Won %, Return Games Won %, BP Converted %, Total Points Won %); Rows 2–11 display the player's last 10 tournament matches inline.
- **Zero Dependencies**: Bundled `requests` in `lib/` and pure-Python PNG compositing in `image_utils.py`.

## Usage

| Command | Description |
| :--- | :--- |
| `wta` | Active WTA tournament scores (Live → Upcoming → Final, Singles default) |
| `wta sabalenka` / `wta hong kong` | Filter active scoreboard by player or tournament |
| `wta doubles` / `wta live` / `wta all` | View Doubles matches, Live matches only, or full tournament draw |
| `wtar` / `wtar doubles` / `wtar top10` / `wtar all` | View Top 50 Singles, Top 50 Doubles, Top 10, or Top 150 PIF WTA Rankings |
| `wtar usa` / `wtar cze` / `wtar pol` | Filter Top 150 rankings by country |
| `wtas` / `wtas slam` / `wtas 1000` / `wtas clay` | View full-season WTA Tour calendar or filter by tier/surface/city/month |
| `wtat` / `wtat doubles` | View full round-by-round tournament draw for active WTA events |
| `wtap sabalenka` / `wtap swiatek` / `wtap gauff` | View player rank, YTD & Career W-L/Titles/Prize (`⌘` Serve, `⌥` Return) + last 10 matches |

## Building
```bash
python3 build.py
```
Creates `WTA Tour.alfredworkflow`. Double-click to install in Alfred 5.
