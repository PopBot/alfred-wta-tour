# Use Hybrid ESPN + Official WTA PulseLive JSON APIs

Status: accepted

We will combine ESPN's public tennis JSON API (`site.api.espn.com`, `sports.core.api.espn.com`, `site.web.api.espn.com`) with the official, keyless WTA Tour PulseLive REST API (`api.wtatennis.com/tennis/...`) rather than relying on a single upstream provider.

## Context & Trade-offs

- **ESPN Public API**: Provides fast (~120ms) tournament scoreboards (`/sports/tennis/wta/scoreboard`), Top 150 Singles rankings (`/sports/tennis/wta/rankings`), high-resolution player headshots (`a.espncdn.com/i/headshots/tennis/players/full/{id}.png`), and country flags (`a.espncdn.com/i/teamlogos/countries/500/{ioc}.png`). However, ESPN omits current-season player service/return statistics, Doubles rankings, and a lightweight full-year tournament calendar.
- **WTA PulseLive API (`api.wtatennis.com/tennis`)**: Provides clean, keyless JSON for the full-season tournament calendar (`/tennis/tournaments/?excludeLevels=ITF`), Singles and Doubles official rankings (`/tennis/players/ranked`), player lookup (`/tennis/players/?name={query}`), detailed current-season Service & Return statistics (`/tennis/players/{id}/year/{year}`), and recent player match logs (`/tennis/players/{id}/matches`).
- **SofaScore (`api.sofascore.com`)**: Returns HTTP 403 Forbidden due to Cloudflare bot protection.

## Consequences

- Scoreboard (`wta`) and Tournament Draw (`wtat`) leverage ESPN's scoreboard JSON (enriched with WTA live match point/serve states when active).
- Rankings (`wtar`) supports both Singles (via ESPN + WTA PulseLive) and Doubles (`wtar doubles` via WTA PulseLive).
- Schedule (`wtas`) uses WTA PulseLive `/tennis/tournaments/` to display the full WTA 1000/500/250/Grand Slam/Finals calendar.
- Player Search & Stats (`wtap`) combines ESPN headshots with WTA PulseLive `/tennis/players/{id}/year/{year}` and `/matches` for 2026 Service (`⌘`) & Return (`⌥`) stats and inline match history.
