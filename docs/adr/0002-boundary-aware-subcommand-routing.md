# Use Boundary-Aware Subcommand Routing for Tennis Modules

Status: accepted

We will configure a single Script Filter (`keyword: wta`, `withspace: false`) in `info.plist` invoking `python3 wta.py "$1"`, and route to subcommands (`r` Rankings, `s` Schedule/Calendar, `t` Tournament Draw, `p` Player Stats & Recent Matches) only when the subcommand character has no leading space and is either the entire query or immediately followed by whitespace.

## Context & Trade-offs

Users need to filter the live/daily scoreboard by typing a space followed by a player name, tournament city, or status (`wta sabalenka`, `wta swiatek`, `wta tokyo`, `wta pegula`, `wta rybakina`). Naive prefix matching after `.strip()` would misroute `wta sabalenka` (`"sabalenka"`) to Schedule (`wtas abalenka`), `wta tokyo` to Tournament (`wtat okyo`), `wta pegula` to Player (`wtap egula`), and `wta rybakina` to Rankings (`wtar ybakina`).

## Consequences

- Typing a space after `wta` (`raw_query.startswith(" ")`, e.g., `wta sabalenka`, `wta wuhan`, `wta doubles`, `wta live`) always routes to the **Scoreboard (`wta.py`)** as a filter.
- Typing a suffix directly attached to `wta` (`wtar`, `wtar doubles`, `wtas`, `wtas 1000`, `wtat wuhan`, `wtap sabalenka`) routes cleanly to the corresponding module without collisions.
