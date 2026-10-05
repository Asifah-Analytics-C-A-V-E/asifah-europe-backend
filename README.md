# asifah-europe-backend

**Europe & Eurasia theatre backend for [Asifah Analytics](https://asifahanalytics.com)**

Open-source monitoring of geopolitical pressure, conflict escalation and
humanitarian stress across the Europe–Eurasia theatre. Sister backends cover the
Middle East & North Africa, Asia & the Pacific, Africa and the Western Hemisphere.

> **What this is.** A one-person project, built on nights and weekends, running
> on free tiers and stubbornness. No affiliation with or endorsement by any
> government or organisation. If it has been useful to you,
> ☕ [a coffee](https://buymeacoffee.com/asifahanalytics) pays for the hosting
> that keeps it up.

> 🚨 **Not for operational use.** Analytical and research purposes only. See
> [`LICENSE`](./LICENSE).

> ⚠️ **The repo is `asifah-europe-backend`. The deployed service is
> `asifa-europe-backend` — no `h`.** That typo is canonical: sister backends and
> the Global Pressure Index resolve Europe at
> `https://asifa-europe-backend.onrender.com`. Do not "fix" it without changing
> `EUROPE_BACKEND_URL` everywhere first.

---

## 🌍 Coverage

Thirteen rhetoric trackers — the largest theatre on the platform, and the one
that hosts the two biggest wheels.

| Country | Role |
|---|---|
| 🇷🇺 Russia | **Resident hub.** Also carries the stability module |
| 🇹🇷 Turkey | **Resident hub.** Swing-state tracker — alignment divergence (Jun 2026) |
| 🇺🇦 Ukraine | Active war; humanitarian module |
| 🇧🇾 Belarus | Aligned multiplier |
| 🇬🇱 Greenland | Arctic sovereignty; inbound-target node |
| 🇵🇱 Poland | Consensus-integrity tracker — *inbound target, not a drift spoke* (Jul 2026); refugee + financial modules |
| 🇭🇺 Hungary | Axis-reversal tracker (May 2026) |
| 🇦🇿 Azerbaijan | Four-wheel spoke (Jun 2026); financial pulse |
| 🇦🇲 Armenia | Peace-implementation tracker — tenth rim spoke (Jul 2026) |
| 🇨🇾 Cyprus | Inverted single-hub spoke — pressured by Turkey (Jun 2026) |
| 🇬🇷 Greece | Anchored frontline spoke — peer rivalry with Turkey (Jun 2026); migration + financial modules |
| 🇰🇿 Kazakhstan | Multi-vector hedging-integrity tracker (Jul 2026); financial pulse |
| 🇲🇩 Moldova | Inbound target; refugee tracker |

All thirteen expose `/history` and `/summary`. Countries without a tracker are
absent from the Europe read, not assessed as quiet.

**Resident hubs:** `russia` and `turkey`. Europe is where those two wheels live,
so their rims — including spokes that sit in other theatres, such as Mali, Sudan,
Syria, Libya, Cuba and Venezuela — are assembled here and read everywhere else
through the shared Redis keyspace.

**Next in the queue:** Baltics (slot reserved in `europe_regional_bluf.py`).

---

## 🏗 Architecture

- **Flask + gunicorn** on Render
- **Shared Upstash Redis** for cross-theatre fingerprints and per-tracker caches
- **Multi-source OSINT ingestion** — GDELT (multilingual), NewsAPI, Brave Search,
  RSS (Kyiv Independent, Meduza, ISW, Arctic Today and others), Reddit, Telegram,
  Bluesky
- **Corridor registry** — Europe is the *producer* for corridor data; other
  backends read it rather than keeping copies

### Modules

| Area | Files |
|---|---|
| Rhetoric trackers (13) | `rhetoric_tracker_russia.py`, `_turkey`, `_ukraine`, `_belarus`, `_greenland`, `_poland`, `_hungary`, `_azerbaijan`, `_armenia`, `_cyprus`, `_greece`, `_kazakhstan`, `_moldova` |
| Interpreters | one per tracker — `russia_signal_interpreter.py` and siblings |
| Regional synthesis | `europe_regional_bluf.py` |
| Financial pulses | `azerbaijan_financial_pulse.py`, `greece_financial_pulse.py`, `kazakhstan_financial_pulse.py`, `poland_financial_pulse.py` |
| Humanitarian / displacement | `ukraine_humanitarian.py`, `moldova_refugee_tracker.py`, `poland_refugee_tracker.py`, `greece_migration.py` |
| Country modules | `russia_stability.py`, `europe_weather_bundle.py` |
| Registries | `corridor_registry.py` (produced here), `convergence_registry.py` (see note below) |
| Proxies to ME canon | `commodity_proxy_europe.py`, `butterfly_proxy_europe.py` |
| Ingestion | `gdelt_gateway.py`, `telegram_signals_europe.py`, `bluesky_signals_europe.py` |
| Shared libraries | `spoke_wheel_reader.py`, `trajectory_reader.py`, `theatre_state.py`, `feed_health.py` |

**Shared libraries deploy byte-identical to every backend.** `spoke_wheel_reader.py`,
`trajectory_reader.py`, `theatre_state.py` and `gdelt_gateway.py` are library
code, not data. If you change one here, change it everywhere.

> ### ⚠️ Known drift: `convergence_registry.py`
>
> Europe carries a **local copy** of the convergence registry
> (v1.0.0, 3 May 2026, 4 convergences) and `europe_regional_bluf.py` imports it
> directly. The canonical registry on the ME backend is **v1.1.0+ with 23
> convergences**. Both files open by calling themselves "single source of truth."
>
> Asia and Africa do not do this — they read the ME registry through
> `convergence_proxy_*`. Europe is the exception, and it is a standing violation
> of **one writer, many readers**: Europe is currently blind to nineteen
> convergences the rest of the platform can see. Resolving it means replacing the
> local import with a proxy, not syncing the copy.

---

## 🚀 Deployment

Deploys to Render via GitHub auto-deploy.

### Required environment variables

| Variable | Purpose |
|---|---|
| `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_REST_URL` | Upstash Redis REST endpoint |
| `UPSTASH_REDIS_TOKEN` / `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST bearer token |
| `NEWSAPI_KEY` | NewsAPI.org API key |
| `BRAVE_API_KEY` | Brave Search API key (tertiary OSINT fallback) |
| `ALPHA_VANTAGE_KEY` | Market data for the financial-pulse modules |
| `DTM_API_KEY` | IOM Displacement Tracking Matrix (refugee trackers) |
| `ME_BACKEND_URL` | ME backend base, for the commodity and butterfly proxies |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_PHONE` | Telegram MTProto credentials |
| `PYTHONUNBUFFERED` | Set to `1` — forces stdout flush for Render Live Tail visibility |

Optional tuning: `FEED_HEALTH_TTL_SEC`, `FEED_SILENT_DAYS`, `FEED_DEAD_DAYS`,
`DISABLE_BOOT_STAGGER`.

### Render configuration

```
Language:        Python 3
Build Command:   pip install -r requirements.txt
Start Command:   gunicorn app:app --timeout 300 --workers 2
Health Check:    /health
```

> ⚠️ **CRITICAL:** the start command MUST include `--timeout 300 --workers 2`.
> Render's default 30-second timeout is shorter than a full scan cycle, and this
> is the single most common deploy bug across Asifah backends. Earlier revisions
> of this file documented a bare `gunicorn app:app` — that is wrong, and with
> thirteen trackers on this service it is the most wrong here.

### Manual redeploy

Auto-deploy is enabled, but the canonical practice is to confirm each deploy
manually in the Render dashboard so the deploy log can be read before scans run.

> On a 404 after deploy, read the **startup sequence** in the log, not the tail.
> An import error prints its traceback at boot and has usually scrolled away by
> the time you look.

---

## 📡 Endpoints

84 routes are registered; full inventory at `/debug/routes`. The ones used most:

| Endpoint | Purpose |
|---|---|
| `/api/rhetoric/<country>` | Country tracker — all thirteen listed above |
| `/api/rhetoric/<country>/history` | Scan history, newest first — all thirteen |
| `/api/rhetoric/<country>/summary` | Compact read for card rendering — all thirteen |
| `/api/rhetoric/europe/bluf` | Regional BLUF — `?force=true` rebuilds |
| `/api/rhetoric/europe/bluf/debug` | Cache state and per-tracker inventory |
| `/api/europe/dashboard` | All threat scores in one call |
| `/api/europe/threat/<target>` | Threat score for one target |
| `/api/corridors` · `/api/corridors/<corridor_id>` · `/api/corridors/health` | Corridor registry — Europe is the producer |
| `/api/europe/commodity/<target>` | Commodity proxy to the ME backend |
| `/api/europe/butterfly/<consumer_theater>` | Butterfly (second-order effect) read |
| `/api/stability/russia` | Russia stability module |
| `/api/ukraine/humanitarian` · `/api/ukraine/news` | Ukraine humanitarian and news reads |
| `/api/europe/refugees/moldova` · `/api/europe/refugees/poland` · `/api/greece/migration` | Displacement modules |
| `/api/europe/financial/poland` · `/api/europe/financial/kazakhstan` · `/api/europe/greece/financial-pulse` · `/api/europe/azerbaijan/financial-pulse` | Financial pulses |
| `/api/military-posture/<target>` | Military posture |
| `/api/europe/notams` · `/api/europe/flights` · `/api/europe/travel-advisories` | Aviation notices, flight disruption, official travel advisories |
| `/api/europe/weather` | Weather bundle |
| `/api/europe/cache-status` · `/health` · `/rate-limit` · `/debug/routes` | Operational |

`?force=true` bypasses the cache and runs a live scan.

> ⚠️ `?force=true` on a cold service can exceed a five-minute client timeout.
> With thirteen trackers this is the slowest backend to rebuild. Prefer the
> cached read unless a rebuild is genuinely needed.

---

## 🤝 Cross-backend integration

Europe sits in the three-altitude architecture: sensors below, analyst in the
middle, global index above — and it is the only theatre that is also a *producer*
for two of the platform's cross-cutting layers.

```
Thirteen rhetoric trackers (Russia, Turkey, Ukraine, Belarus, Greenland,
                            Poland, Hungary, Azerbaijan, Armenia,
                            Cyprus, Greece, Kazakhstan, Moldova)
              │
              ▼
   europe_regional_bluf.py  ─────►  Global Pressure Index (GPI)
              ▲                              ▲
              │                              │
   commodity / butterfly proxies      corridor_registry.py
              ▲                       (produced HERE, read elsewhere)
              │
        ME backend's canonical registries
```

**Russia and Turkey wheels are assembled here.** Their rims reach well outside
Europe — Mali, Sudan, Libya, Syria, Somalia, Cuba, Venezuela — so a spoke
lighting in Africa or the Western Hemisphere is read against a hub that lives on
this backend, through shared Redis rather than cross-backend HTTP.

---

## 📋 Working practices

**Doctrine.** Every module here follows the platform-wide analytical discipline:

- **Convergence, not prediction.** Report the signals that are present. Never
  assert that an outcome is imminent, likely, or dated.
- **`unknown` is a state, never a silence.** A sensor that could not read
  something says so. It does not emit a zero.
- **A real zero is not an unread zero.** "Measured, found nothing" and "nobody
  measured" are different findings and render differently.
- **Absence is reported, not inferred.** A country without a tracker is absent
  from the regional read, not assessed as quiet.
- **Silence can be the signal.** For claiming actors, quiet against their own
  baseline is a tempo change, not calm.
- **Claims are labelled as claims.** Where a reading rests on an interested
  party's unconfirmed assertions, it is reported as claimed, not established.
- **One writer, many readers.** Data has exactly one producer; everything else
  proxies to it. (See the `convergence_registry.py` note above — this backend is
  currently the exception, and that is a defect, not a pattern.)

**Engineering.**

- Surgical find/replace edits preferred over full-file rewrites
- AST validation before every deploy is mandatory:
  `python3 -c "import ast; ast.parse(open('FILE.py').read()); print('ok')"`
- Static reference data carries `source`, source URL and a `data_as_of` date —
  date-stamp rather than hardcode, so staleness is visible rather than assumed
- A diagnostic that lies is worse than no diagnostic. A health check that cannot
  fail is not a health check.

---

## 📞 Contact

Built and maintained by RCGG / Asifah Analytics. Licensing: see
[`LICENSE`](./LICENSE).

- ☕ [Buy Me a Coffee](https://buymeacoffee.com/asifahanalytics) — pays for hosting
- [asifahanalytics.com](https://asifahanalytics.com) · *Not for operational use*

Donations support running costs. They buy no licence, no warranty, no support
obligation and no influence over what gets built.

---

*© 2025–2026 RCGG / Asifah Analytics. All rights reserved.*

*Last updated: 5 October 2026*
