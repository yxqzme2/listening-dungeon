<p align="center"><img src="docs/images/icon.png" width="120" alt=""></p>

# The Listening Dungeon

**Every audiobook you finish becomes a dungeon you can play.**

A self-hosted game for [Audiobookshelf](https://www.audiobookshelf.org/) households. It reads what your family listens to and turns it into a paper-cutout dungeon crawler: finish a book, a dungeon unlocks; clear it for XP and loot; finish a whole series for bonus rewards. Built for a family of LitRPG fans, so it leans that way, but every monster, item and theme can be changed.

![Your books, your dungeons](docs/images/series-dungeons.jpg)

## What's in it

- **Your books are the dungeons.** Every finished book unlocks a three-floor dungeon. Longer books drop better loot; dungeon scenery follows the book's genre, and many popular series have their own look and villain.
- **Seven classes:** Brawler, Paladin, Runeblade, Hexcaster, Ranger, Beastmaster (pets) and Necromancer (minions), each with its own powers. Level up, collect gear, upgrade in the Forge, dress up in the Wardrobe.
- **The Arena:** fight the *ghost* of another player's crawler (their real stats and gear), climb the ladder, win weekly prizes.
- **The System Store:** a daily, shared shop. If someone buys it first, it's gone. Once in a while, a Legendary.
- **December party boss:** one shared health bar for the whole household, with banners, scars and consequences if he escapes.
- **Reading extras:** series rewards, badges, Tier Lists, Recommendations from your own tastes, a Chronicle of everything you've listened to, Release Radar for new books in your series, and book Requests.
- **Make it yours:** an admin Workshop to build or import monsters and loot, and a Monster Maker players can submit to.

| | |
|---|---|
| ![The Arena](docs/images/arena.jpg) | ![The ladder](docs/images/ladder.jpg) |
| ![The daily Store](docs/images/store.jpg) | |

## How it works

Two containers:

| Container | What it does |
|---|---|
| `listening-dungeon-abs-stats` | Talks to your Audiobookshelf server: finished books, listening time, series, covers. It only **reads**, except when a player taps "add this series to my playlist" on the Recommendations page. |
| `listening-dungeon` | The game and its pages. Keeps its own SQLite database in `/data`. |

Nothing about your listening leaves your network. The server looks up public book info on Audible and Royal Road (Release Radar, Requests, series tags for Recommendations), and the pages load fonts from Google Fonts.

## Install

You need an Audiobookshelf **admin API token**: in ABS go to *Settings → Users → (your admin user)* and copy the API token.

The easiest way to get your settings right is the **setup builder**: download [`tools/setup-builder.html`](tools/setup-builder.html), open it in your browser, fill it in, and download ready-made Unraid templates, a Docker `.env`, or a Portainer stack. It runs entirely in your browser.

### Unraid

1. Put the two templates from the setup builder (or [`templates/unraid/`](templates/unraid/)) in `/boot/config/plugins/dockerMan/templates-user/` (the **flash** share).
2. Docker → **Add Container** → pick **listening-dungeon-abs-stats** → fill in your ABS address and token → Apply.
3. Docker → **Add Container** → pick **listening-dungeon** → set the admin password and the abs-stats address → Apply.
4. Open `http://<your-server>:8000`.

On the default bridge network the containers reach each other by your server's IP (e.g. `http://192.168.1.50:3000`). If you put both on a custom Docker network you can use container names instead.

### Docker / Docker Desktop

```bash
git clone https://github.com/yxqzme2/listening-dungeon.git
cd listening-dungeon
cp .env.example .env      # then fill it in (or use the setup builder)
docker compose up -d
```

Open `http://localhost:8000` (or the machine's IP).

### Portainer

Stacks → Add stack → paste the stack from the setup builder → Deploy.

## Playing from outside your home

The game is plain HTTP on port 8000. To play away from home, put it behind something you trust: a VPN (Tailscale, WireGuard) is simplest and safest, or a reverse proxy with HTTPS. See [docs/reverse-proxy.md](docs/reverse-proxy.md). Don't forward port 8000 straight to the internet.

## First steps

- Each player picks their ABS username on the title screen and sets a 4-digit PIN the first time.
- Admin pages live at `/admin` (the password you set). From there: build or import monsters (see [docs/MONSTER_PROMPT.md](docs/MONSTER_PROMPT.md) for an AI prompt that writes them for you), edit loot, approve player-made monsters, run Release Radar.
- Books finished before you installed it show up as dungeons too, so nobody starts empty-handed.

## Updating

- **Unraid:** Docker → *Check for updates* → update both.
- **Docker:** `docker compose pull && docker compose up -d`.

Your `/data` folder (database, covers) is kept. Back it up now and then.

## Modding

The whole thing was built with Claude (Anthropic's AI) and is meant to be easy to change: point Claude Code (or your AI of choice) at this repo and describe what you want. Good starting points:

- `app/game_rules.py`: every number (XP, loot odds, prices, scaling).
- `app/game_monsters.py`: the built-in monsters.
- `static/game/dungeon-themes.js`: dungeon scenery and the series looks (see [docs/SERIES_THEMES.md](docs/SERIES_THEMES.md)).
- `csv/loot.csv`: the item catalog.

Tests: `python -m unittest discover tests`.

## Feedback

Ideas, bugs and feature requests are welcome in [Issues](https://github.com/yxqzme2/listening-dungeon/issues). This is a family hobby project, so updates come when they come.

## License

[MIT](LICENSE). Item icons were gathered from around the web for this hobby project; if you own one and want it credited or removed, open an issue.
