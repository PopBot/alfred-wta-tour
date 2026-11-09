# WTA Tour Alfred Workflow

An Alfred 5 workflow for tracking women's professional tennis on the Hologic WTA Tour—including live and daily tournament match scores, official PIF WTA Rankings, the full-season tournament calendar, tournament draws, and player profiles with current-season service/return statistics and recent match results.

## Language

**WTA Tour**:
The top-tier women's professional tennis circuit organized by the Women's Tennis Association, comprising Grand Slams, WTA Finals, WTA 1000, WTA 500, WTA 250, and the United Cup (with WTA 125 and ITF circuits excluded by default unless explicitly queried).
_Avoid_: Women's tennis, WTP, ITF tour

**Tournament Tier**:
The official category and ranking-point weight of an event on the calendar: `Grand Slam` (2000), `WTA Finals` (1500), `WTA 1000`, `WTA 500`, `WTA 250`, `WTA 125`, or `Team Event` (United Cup / Billie Jean King Cup).
_Avoid_: Division, conference

**Grouping (Draw Discipline)**:
A competition division within a tournament event—specifically `Women's Singles` (`womens-singles`, the default scoreboard view) or `Women's Doubles` (`womens-doubles`).
_Avoid_: League, category, bracket

**Smart Active Window**:
The default scoreboard filtering rule when invoking `wta` with no query: displays all currently `Live` matches, all `Today` scheduled/completed matches, and recent Main Draw matches (`Round of 64` through `Final`), omitting completed early-week Qualifying matches unless the tournament is still in its qualifying phase or the user filters by `qual` or `all`.
_Avoid_: Raw tournament dump, full draw dump

**Seed**:
A player's or doubles pair's tournament draw placement (`1`–`32`), rendered in square brackets (`[1] A. Sabalenka`) to distinguish a tournament seed from a player's world ranking (`#1`).
_Avoid_: Curated rank, poll rank

**Set Linescore**:
The sequence of games won per set by each competitor (e.g., `6-3, 6-7(4), 6-2`), with tiebreak points rendered in parentheses next to the losing tiebreak game score (`6(4)`).
_Avoid_: Quarters, periods, innings

**Boundary-Aware Subcommand**:
A single-letter command suffix (`r` for Rankings, `s` for Schedule/Calendar, `t` for Tournament Draw, `p` for Player Profile & Stats) attached directly to the base `wta` keyword (`wtar`, `wtas`, `wtat`, `wtap`) that only triggers when the suffix is the entire query or is immediately followed by whitespace, preventing collisions with space-separated scoreboard filters (`wta sabalenka`, `wta wuhan`, `wta top10`).
_Avoid_: Prefix route, raw prefix

**Unified Player View**:
The response layout when `wtap {player}` resolves to a single WTA player: Row 1 displays the player's World Rank, YTD & Career W-L record, Titles, and Prize Money (with `⌘` Service Stats and `⌥` Return Stats from the official WTA PulseLive API), and Rows 2+ display the player's recent 2026 tournament match results inline.
_Avoid_: Separate player schedule tab
