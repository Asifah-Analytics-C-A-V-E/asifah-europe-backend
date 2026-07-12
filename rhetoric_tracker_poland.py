"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — POLAND CONSENSUS TRACKER
  rhetoric_tracker_poland.py  ·  v1.0.0 (Jul 12 2026)  ·  Europe backend
═══════════════════════════════════════════════════════════════════════

Poland has been in NATO since MARCH 1999. It is not a recent accession, it is
not a buffer, and it is not drifting. Nobody is flipping Poland and Moscow
knows it -- so Moscow is not trying.

Russia is trying to make Poland's support for Ukraine TOO EXPENSIVE TO SUSTAIN.
Below the threshold of war. Indefinitely. Defence24 calls it "Phase 0."

Poland is not the buffer. POLAND IS THE SPINE -- the main logistical hub for
aid to Kyiv since 2022, which is precisely when the hybrid-attack tempo spiked.
That is not a coincidence; that is a target set.

So this tracker does not ask "is Poland drifting." It asks:

    IS THE CONSENSUS HOLDING, AND AT WHAT RATE IS IT BEING SPENT?

Same instrument family as Kazakhstan's hedging-integrity index. Opposite
question. Node class on the Russia wheel: `inbound_target` -- and unlike
Kazakhstan's China spoke, THIS one has a reader already waiting.

WHAT IT READS (all server-side, all absence-honest)
  - Refugee tracker  -> /api/europe/refugees/poland. NOT a humanitarian sensor
    on this page: it is the AMMUNITION STOCKPILE for the wedge. ~1M Ukrainians
    hosted for four years without incident -- the count is inert. What matters
    is whether the RHETORIC ABOUT the count is heating up. The count is the
    dial; the rhetoric is the signal.
  - Financial pulse  -> the attrition tile (debt-financed defence spending).
  - Commodity proxy  -> the grain-blockade convergence, where the commodity IS
    the weapon: Ukrainian grain transits Poland, Polish farmers blockade over
    it, and the blockade severs the corridor AND widens the wedge in one motion.
  - Tempo baseline   -> mode='tape' (Russia never claims; measure the tape).

WHAT IT WRITES
  - rhetoric:poland:latest / :history
  - crosstheater:poland:fingerprint  (node_class: inbound_target)
  - tempo:poland:counts:{date}       (attack / attribution / amplification)
"""

import os
import re
import json
import time
import threading
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

TRACKER_VERSION = '1.0.0'

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')
NEWSAPI_KEY         = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY       = os.environ.get('BRAVE_API_KEY')

EUROPE_BACKEND = 'https://asifa-europe-backend.onrender.com'
ME_BACKEND     = os.environ.get('ME_BACKEND_URL', 'https://asifah-backend.onrender.com')

REDIS_KEY_LATEST  = 'rhetoric:poland:latest'
REDIS_KEY_HISTORY = 'rhetoric:poland:history'
CACHE_TTL         = 12 * 3600
SCAN_LOCK_KEY     = 'lock:poland:rhetoric:scan'

# ── Interpreter (soft import) ──
try:
    from poland_signal_interpreter import interpret_signals as _poland_interpret
    _INTERPRETER_AVAILABLE = True
    print('[Poland Rhetoric] ✅ Signal interpreter loaded')
except ImportError as e:
    _INTERPRETER_AVAILABLE = False
    _poland_interpret = None
    print(f'[Poland Rhetoric] ⚠️ Interpreter not available: {e}')

# ── Tempo baseline (soft import) ──
# mode='tape': Russia NEVER claims its hybrid operations in Poland. There is no
# claiming actor to fall silent, so "actor silence" would measure nothing. We
# measure the TAPE instead: attack tempo, Polish attribution tempo, and
# amplification tempo, each against its own baseline.
try:
    from tempo_baseline import emit_counts as _tempo_emit, read_baseline as _tempo_read
    TEMPO_AVAILABLE = True
except ImportError:
    TEMPO_AVAILABLE = False
    _tempo_emit = None
    _tempo_read = None

# ── Telegram / Bluesky (soft imports) ──
try:
    from telegram_signals_europe import fetch_poland_telegram_signals
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    fetch_poland_telegram_signals = None

try:
    from bluesky_signals_europe import fetch_bluesky_for_target
    BLUESKY_AVAILABLE = True
except ImportError:
    BLUESKY_AVAILABLE = False
    fetch_bluesky_for_target = None


# ════════════════════════════════════════════════════════════
# SOURCES
# ════════════════════════════════════════════════════════════

RSS_FEEDS = [
    ('https://notesfrompoland.com/feed/',                     'Notes from Poland',  0.95),
    ('https://www.polskieradio.pl/399/7975/Rss',              'Polskie Radio',      0.90),
    ('https://tvpworld.com/rss',                              'TVP World',          0.85),
    ('https://www.defence24.com/rss',                         'Defence24',          1.00),
    ('https://euractiv.com/sections/politics/feed/',          'Euractiv',           0.85),
    ('https://www.osw.waw.pl/en/rss.xml',                     'OSW (Centre for Eastern Studies)', 1.00),
    ('https://kyivindependent.com/feed/',                     'Kyiv Independent',   0.80),
    ('https://www.rferl.org/api/zrqiteuuir',                  'RFE/RL',             0.90),
    ('https://feeds.bbci.co.uk/news/world/europe/rss.xml',    'BBC Europe',         0.80),
]

# GDELT: pol = Polish (sourcelang code)
GDELT_QUERIES = [
    ('Poland sabotage Russia',            'eng'),
    ('Poland hybrid attack',              'eng'),
    ('Poland Ukraine tensions',           'eng'),
    ('Poland Belarus border',             'eng'),
    ('Polska sabota\u017c Rosja',         'pol'),
    ('Polska Ukraina napi\u0119cia',      'pol'),
    ('Rosja dywersja Polska',             'pol'),
]

REDDIT_SUBREDDITS = ['poland', 'europe', 'CredibleDefense', 'geopolitics', 'ukraine']


# ════════════════════════════════════════════════════════════
# ACTORS — 7
# ════════════════════════════════════════════════════════════

ACTORS = {
    'polish_government': {
        'name': 'Polish Government (Tusk)', 'flag': '\U0001f1f5\U0001f1f1', 'icon': '\U0001f3db\ufe0f',
        'color': '#0ea5e9', 'weight': 1.0,
        'role': 'Tusk cabinet, MFA (Sikorski), MoD, Siemoniak (special services)',
        'keywords': [
            'donald tusk', 'tusk government', 'polish prime minister',
            'radoslaw sikorski', 'sikorski', 'polish foreign ministry',
            'tomasz siemoniak', 'siemoniak', 'polish ministry of defence',
            'kosiniak-kamysz', 'polish cabinet', 'polish government says',
            'warsaw government', 'polish mfa',
        ],
    },
    'polish_presidency': {
        'name': 'Presidency (Nawrocki)', 'flag': '\U0001f1f5\U0001f1f1', 'icon': '\U0001f451',
        'color': '#f59e0b', 'weight': 1.0,
        'role': 'President Nawrocki — the cohabitation counterparty. THE OPENING.',
        'keywords': [
            'karol nawrocki', 'nawrocki', 'polish president', 'presidential veto poland',
            'president vetoes', 'presidential palace warsaw', 'nawrocki zelensky',
            'stripped honour zelensky', 'order of the white eagle',
            'prezydent nawrocki',
        ],
    },
    'security_services': {
        'name': 'Security Services (ABW/SKW)', 'flag': '\U0001f6e1\ufe0f', 'icon': '\U0001f575\ufe0f',
        'color': '#22c55e', 'weight': 1.1,
        'role': 'ABW, SKW, Border Guard — the ATTRIBUTION voice. Naming Russia in public is resilience, not damage.',
        'keywords': [
            'abw', 'internal security agency poland', 'polish counterintelligence',
            'skw', 'polish border guard', 'straz graniczna', 'jacek dobrzynski',
            'polish special services', 'polish intelligence', 'saboteur arrested poland',
            'detained on suspicion of espionage poland', 'spy ring poland',
            'agencja bezpiecze\u0144stwa wewn\u0119trznego',
        ],
    },
    'russian_pressure': {
        'name': 'Russian Pressure (inbound)', 'flag': '\U0001f1f7\U0001f1fa', 'icon': '\u2694\ufe0f',
        'color': '#ef4444', 'weight': 1.2,
        'role': 'The campaign itself — sabotage, cyber, disinformation. Never claimed.',
        'keywords': [
            'russian sabotage poland', 'kremlin poland', 'gru poland',
            'russian intelligence poland', 'commissioned by russian services',
            'russian disinformation poland', 'doppelganger', 'matryoshka operation',
            'disposable agents', 'russia hybrid war poland', 'moscow poland',
            'russian trolls poland', 'kremlin-linked poland',
        ],
    },
    'belarus_vector': {
        'name': 'Belarus Vector', 'flag': '\U0001f1e7\U0001f1fe', 'icon': '\U0001f6a7',
        'color': '#f97316', 'weight': 1.0,
        'role': 'Lukashenko border lever — instrumentalized migration. The flow IS the weapon.',
        'keywords': [
            'lukashenko', 'belarus border poland', 'belarusian border', 'minsk poland',
            'migrant crisis belarus', 'border tunnel belarus', 'belarusian intelligence',
            'weaponized migration', 'instrumentalized migration',
            'granica z bia\u0142orusi\u0105',
        ],
    },
    'ukraine_relations': {
        'name': 'Ukraine Relations', 'flag': '\U0001f1fa\U0001f1e6', 'icon': '\U0001fa78',
        'color': '#a855f7', 'weight': 1.1,
        'role': 'The wedge. Volhynia memory, grain, refugees — the fracture line Moscow found.',
        'keywords': [
            'poland ukraine relations', 'volhynia', 'wolyn', 'upa', 'bandera',
            'ukrainian grain poland', 'farmers protest poland', 'border blockade poland',
            'ukrainian refugees poland', 'refugee benefits poland', 'zelensky poland',
            'polish ukrainian tensions', 'exhumation ukraine poland',
            'wo\u0142y\u0144',
        ],
    },
    'nato_anchor': {
        'name': 'NATO Anchor', 'flag': '\U0001f6e1\ufe0f', 'icon': '\U0001f91d',
        'color': '#38bdf8', 'weight': 0.9,
        'role': 'Allied posture, US presence, Article 5 credibility. The thing that is NOT drifting.',
        'keywords': [
            'nato poland', 'us troops poland', 'article 5', 'article 4 poland',
            'nato eastern flank', 'allied posture poland', 'nato consultations poland',
            'us forces poland', 'patriot poland', 'nato summit poland',
            'east shield', 'tarcza wschod',
        ],
    },
}


# ════════════════════════════════════════════════════════════
# REDIS
# ════════════════════════════════════════════════════════════

def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=6)
        d = r.json()
        if d.get('result'):
            return json.loads(d['result'])
    except Exception as e:
        print(f'[Poland Rhetoric] Redis get error: {str(e)[:90]}')
    return None


def _redis_set(key, value, ttl=CACHE_TTL):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', key, json.dumps(value, default=str), 'EX', ttl], timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f'[Poland Rhetoric] Redis set error: {str(e)[:90]}')
        return False


def _redis_lpush_trim(key, value, keep=60):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return
    try:
        h = {'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}', 'Content-Type': 'application/json'}
        requests.post(UPSTASH_REDIS_URL, headers=h,
                      json=['LPUSH', key, json.dumps(value, default=str)], timeout=8)
        requests.post(UPSTASH_REDIS_URL, headers=h,
                      json=['LTRIM', key, 0, keep - 1], timeout=8)
    except Exception as e:
        print(f'[Poland Rhetoric] History push error: {str(e)[:90]}')


def _acquire_scan_lock(ttl=1800):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return True
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', SCAN_LOCK_KEY, datetime.now(timezone.utc).isoformat(),
                                'NX', 'EX', ttl], timeout=8)
        return (r.json() or {}).get('result') == 'OK'
    except Exception:
        return True


# ════════════════════════════════════════════════════════════
# FETCHERS
# ════════════════════════════════════════════════════════════

_UA = {'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')}

_POLAND_GATE = re.compile(
    r'\b(poland|polish|warsaw|polska|polski|rzeszow|nawrocki|tusk|wroclaw|krakow)\b', re.I)


def _fetch_rss(url, source, weight=0.85, max_items=20):
    out = []
    try:
        r = requests.get(url, timeout=12, headers=_UA)
        if r.status_code != 200:
            return out
        feed = feedparser.parse(r.content)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for e in feed.entries[:max_items]:
            title = (e.get('title') or '').strip()
            desc = (e.get('summary') or e.get('description') or '')[:600]
            if not title:
                continue
            # Gate broad feeds (BBC Europe, RFE/RL, Euractiv) to Poland content
            if source in ('BBC Europe', 'RFE/RL', 'Euractiv', 'Kyiv Independent'):
                if not _POLAND_GATE.search(title + ' ' + desc):
                    continue
            pub = None
            try:
                if e.get('published_parsed'):
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    if pub < cutoff:
                        continue
            except Exception:
                pass
            out.append({
                'title': title, 'description': desc, 'url': e.get('link', ''),
                'source': source, 'source_type': 'rss', 'weight': weight,
                'published': pub.isoformat() if pub else None,
            })
    except Exception as e:
        print(f'[Poland RSS] {source}: {str(e)[:70]}')
    return out


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    out = []
    try:
        r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc', params={
            'query': f'{query} sourcelang:{language}', 'mode': 'ArtList',
            'maxrecords': max_records, 'format': 'json',
            'timespan': f'{days * 24}h',
        }, timeout=(5, 15), headers=_UA)
        if r.status_code != 200:
            return out
        for a in (r.json().get('articles') or []):
            out.append({
                'title': a.get('title', ''), 'description': '',
                'url': a.get('url', ''), 'source': a.get('domain', 'GDELT'),
                'source_type': 'gdelt', 'weight': 0.75,
                'published': a.get('seendate'), 'lang': language,
            })
    except Exception as e:
        print(f'[Poland GDELT] {query[:28]} ({language}): {str(e)[:60]}')
    return out


def _fetch_reddit():
    out = []
    for sub in REDDIT_SUBREDDITS:
        try:
            r = requests.get(f'https://www.reddit.com/r/{sub}/new.json?limit=25',
                             timeout=10, headers=_UA)
            if r.status_code != 200:
                continue
            for c in (r.json().get('data', {}).get('children') or []):
                p = c.get('data', {})
                title = p.get('title', '')
                body = (p.get('selftext') or '')[:400]
                if sub != 'poland' and not _POLAND_GATE.search(title + ' ' + body):
                    continue
                out.append({
                    'title': title, 'text': title + ' ' + body,
                    'url': f"https://reddit.com{p.get('permalink', '')}",
                    'source': f'reddit-{sub}', 'source_type': 'reddit', 'weight': 0.4,
                    'score': p.get('score', 0),
                })
        except Exception:
            continue
    print(f'[Poland Reddit] {len(out)} posts across {len(REDDIT_SUBREDDITS)} subs')
    return out


# ════════════════════════════════════════════════════════════
# SERVER-SIDE READS (absence-honest, never blocking the scan)
# ════════════════════════════════════════════════════════════

def _read_refugee_data():
    """The wedge's AMMUNITION DIAL — not a humanitarian sensor on this page.

    ~1M Ukrainians have been hosted in Poland for four years without incident.
    The count itself is analytically inert. What matters is whether the RHETORIC
    ABOUT the count is heating up. The count is the dial; the rhetoric is the
    signal. The interpreter reads them together."""
    try:
        r = requests.get(f'{EUROPE_BACKEND}/api/europe/refugees/poland', timeout=12)
        if not r.ok:
            return None
        d = r.json() or {}
        total = d.get('total') or d.get('current_total') or d.get('refugees_total')
        if not total:
            return None
        return {
            'total': total,
            'trend': d.get('trend') or d.get('direction'),
            'stale': bool(d.get('stale')),
            'as_of': d.get('data_as_of') or d.get('last_updated'),
        }
    except Exception as e:
        print(f'[Poland Rhetoric] Refugee read failed (non-fatal): {str(e)[:70]}')
        return None


def _read_financial_data():
    """The attrition tile — debt-financed defence spending, priced live."""
    try:
        r = requests.get(f'{EUROPE_BACKEND}/api/europe/financial/poland', timeout=12)
        return r.json() if r.ok else None
    except Exception as e:
        print(f'[Poland Rhetoric] Financial read failed (non-fatal): {str(e)[:70]}')
        return None


def _read_commodity_data():
    """Grain-blockade convergence. Poland is the world's #2 silver producer and
    the primary overland grain-transit corridor out of the war zone -- and THAT
    is the point: Ukrainian grain transits Poland, Polish farmers blockade over
    it, and the blockade severs the corridor AND widens the Poland-Ukraine wedge
    in a single motion, at no cost to Moscow. The commodity IS the weapon."""
    try:
        r = requests.get(f'{EUROPE_BACKEND}/api/europe/commodity/poland', timeout=12)
        if not r.ok:
            return None
        d = r.json() or {}
        return {
            'present': True,
            'pressure': d.get('pressure_score') or d.get('pressure'),
            'alert': d.get('alert_level') or d.get('alert'),
            'commodities': [c.get('commodity') for c in (d.get('commodities') or [])][:6],
        }
    except Exception as e:
        print(f'[Poland Rhetoric] Commodity read failed (non-fatal): {str(e)[:70]}')
        return None


# ════════════════════════════════════════════════════════════
# CLASSIFY
# ════════════════════════════════════════════════════════════

def _classify(articles, telegram, bluesky, reddit):
    summaries = {}
    for aid, cfg in ACTORS.items():
        summaries[aid] = {
            'id': aid, 'name': cfg['name'], 'flag': cfg['flag'], 'icon': cfg['icon'],
            'color': cfg['color'], 'role': cfg['role'], 'weight': cfg['weight'],
            'statement_count': 0, 'level': 0, 'articles': [],
        }

    pool = []
    for a in articles:
        pool.append((a, (a.get('title', '') + ' ' + a.get('description', '')).lower()))
    for s in (telegram or []) + (bluesky or []) + (reddit or []):
        pool.append((s, (s.get('text') or s.get('title') or '').lower()))

    for item, text in pool:
        if not text:
            continue
        for aid, cfg in ACTORS.items():
            if any(kw in text for kw in cfg['keywords']):
                summaries[aid]['statement_count'] += 1
                if len(summaries[aid]['articles']) < 8:
                    summaries[aid]['articles'].append({
                        'title': item.get('title', '')[:180],
                        'url': item.get('url', ''),
                        'source': item.get('source', ''),
                    })

    # Actor level from statement volume — a SENSOR reading, not a judgment.
    for aid, s in summaries.items():
        n = s['statement_count']
        s['level'] = (5 if n >= 25 else 4 if n >= 15 else 3 if n >= 8
                      else 2 if n >= 4 else 1 if n >= 1 else 0)
    return summaries


# ════════════════════════════════════════════════════════════
# CROSS-THEATER FINGERPRINT — node_class: inbound_target
# Unlike Kazakhstan's China spoke (written-but-unread), the Russia wheel
# ALREADY has an inbound_target reader waiting for this.
# ════════════════════════════════════════════════════════════

def _write_crosstheater_fingerprint(result, interp):
    try:
        fp = interp.get('cross_theater_fingerprints') or {}
        consensus = fp.get('consensus_integrity') or {}
        hybrid    = fp.get('hybrid_tempo') or {}
        casualty  = fp.get('casualty_tripwire') or {}
        wedge     = fp.get('ukraine_wedge') or {}
        spine     = fp.get('logistics_spine') or {}
        migration = fp.get('instrumentalized_migration') or {}

        fingerprint = {
            'ts':         datetime.now(timezone.utc).isoformat(),
            'theatre':    'poland',
            'node_class': 'inbound_target',
            'level':      result.get('theatre_score', 0),
            'alert':      result.get('alert_level', 'normal'),

            # The instrument
            'consensus_integrity': consensus.get('integrity'),
            'consensus_state':     consensus.get('state'),

            # Domain-split hybrid campaign — kinetic/cyber/cognitive kept SEPARATE
            'hybrid_band':      hybrid.get('band'),
            'dominant_domain':  hybrid.get('dominant_domain'),
            'kinetic_rung':     hybrid.get('kinetic_rung'),
            'domains':          hybrid.get('domains', {}),

            # The Black Swan
            'casualty_tripwire': casualty.get('state'),
            'black_swan':        casualty.get('black_swan', False),

            # The vector Moscow is actively working
            'wedge_band':       wedge.get('band'),
            'wedge_axes':       wedge.get('axes', []),
            'wedge_multi_axis': wedge.get('multi_axis', False),

            # Corridor family members #3 and #4 (opposite polarity)
            'corridors': {
                'military_logistics': {
                    'name': spine.get('corridor_name'), 'stage': spine.get('stage'),
                    'threat_band': spine.get('threat_band'),
                    'blocker_actors': spine.get('blocker_actors', []),
                },
                'instrumentalized_migration': {
                    'name': migration.get('corridor_name'), 'polarity': 'inverted',
                    'band': migration.get('band'),
                },
            },

            'note': ('Poland is an INBOUND TARGET, not a drift spoke. Russia is not trying to '
                     'flip Poland -- it is trying to make Poland\'s support for Ukraine too '
                     'expensive to sustain. Read consensus_integrity, not alignment.'),
        }
        _redis_set('crosstheater:poland:fingerprint', fingerprint, ttl=30 * 3600)
        print(f"[Poland Rhetoric] ✅ Crosstheater fingerprint written "
              f"(inbound_target, consensus {consensus.get('integrity')}/100)")
    except Exception as e:
        print(f'[Poland Rhetoric] Fingerprint write error: {str(e)[:110]}')


# ════════════════════════════════════════════════════════════
# THE SCAN
# ════════════════════════════════════════════════════════════

def run_poland_rhetoric_scan(force=False):
    started = time.time()
    print('[Poland Rhetoric] Starting scan...')

    articles = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_fetch_rss, u, s, w) for u, s, w in RSS_FEEDS]
        futs += [ex.submit(_fetch_gdelt, q, lang) for q, lang in GDELT_QUERIES]
        for f in as_completed(futs):
            try:
                articles.extend(f.result() or [])
            except Exception:
                continue

    # Dedupe by URL
    seen, deduped = set(), []
    for a in articles:
        u = (a.get('url') or '').strip()
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        deduped.append(a)
    articles = deduped
    print(f'[Poland Rhetoric] Articles: {len(articles)}')

    telegram = []
    if TELEGRAM_AVAILABLE and fetch_poland_telegram_signals:
        try:
            telegram = fetch_poland_telegram_signals() or []
        except Exception as e:
            print(f'[Poland Rhetoric] Telegram failed: {str(e)[:70]}')

    bluesky = []
    if BLUESKY_AVAILABLE and fetch_bluesky_for_target:
        try:
            bluesky = fetch_bluesky_for_target('poland') or []
        except Exception as e:
            print(f'[Poland Rhetoric] Bluesky failed: {str(e)[:70]}')

    reddit = _fetch_reddit()
    print(f'[Poland Rhetoric] Telegram: {len(telegram)} · Bluesky: {len(bluesky)} · '
          f'Reddit: {len(reddit)}')

    # ── Server-side reads ──
    refugee_data   = _read_refugee_data()
    financial_data = _read_financial_data()
    commodity_data = _read_commodity_data()

    # ── Tempo baseline (mode='tape') ──
    # CORPUS HEALTH: the denominator that lets the engine tell "the tape went
    # quiet" apart from "our fetchers died." Without it we would hallucinate
    # menace from our own RSS outage.
    sources_live = len({a.get('source') for a in articles if a.get('source')})
    live_corpus = {'articles': len(articles), 'sources_live': sources_live,
                   'sources_total': len(RSS_FEEDS)}
    tempo_baseline = None
    if TEMPO_AVAILABLE and _tempo_read:
        try:
            tempo_baseline = _tempo_read('poland', live_corpus=live_corpus)
        except Exception as e:
            print(f'[Poland Rhetoric] Tempo read failed (non-fatal): {str(e)[:70]}')

    # ── Language buckets ──
    articles_en = [a for a in articles if a.get('lang') != 'pol']
    articles_pl = [a for a in articles if a.get('lang') == 'pol']

    actor_summaries = _classify(articles, telegram, bluesky, reddit)

    scan_data = {
        'articles_en': articles_en, 'articles_pl': articles_pl, 'articles_ru': [],
        'reddit_signals': reddit, 'telegram_messages': telegram,
        'bluesky_signals': bluesky, 'actor_summaries': actor_summaries,
        'refugee_data': refugee_data, 'financial_data': financial_data,
        'commodity_data': commodity_data, 'tempo_baseline': tempo_baseline,
    }

    interp = {}
    if _INTERPRETER_AVAILABLE and _poland_interpret:
        try:
            interp = _poland_interpret(scan_data) or {}
        except Exception as e:
            print(f'[Poland Rhetoric] Interpreter error: {str(e)[:110]}')

    # Score = consensus pressure. Lower integrity == higher pressure.
    consensus = interp.get('consensus_integrity') or {}
    score = interp.get('composite_modifier', 0)
    casualty = interp.get('casualty_tripwire') or {}

    if casualty.get('black_swan'):
        alert = 'critical'
    elif score >= 30 or consensus.get('state') in ('fracturing', 'contested'):
        alert = 'high'
    elif score >= 15 or consensus.get('state') == 'strained':
        alert = 'elevated'
    else:
        alert = 'normal'

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'poland',
        'flag':              '\U0001f1f5\U0001f1f1',
        'display_name':      'Poland',
        'theatre_score':     score,
        'alert_level':       alert,
        'pressure_score':    score,
        'tracker_version':   TRACKER_VERSION,
        'cached_at':         datetime.now(timezone.utc).isoformat(),
        'scan_duration_sec': elapsed,
        'cache_status':      'fresh',
        'total_articles':    len(articles),
        'articles_by_source': {
            'rss':   sum(1 for a in articles if a.get('source_type') == 'rss'),
            'gdelt': sum(1 for a in articles if a.get('source_type') == 'gdelt'),
        },
        'telegram_count':    len(telegram),
        'bluesky_count':     len(bluesky),
        'reddit_count':      len(reddit),
        'articles_en':       articles_en[:60],
        'articles_pl':       articles_pl[:40],
        'actor_summaries':   actor_summaries,

        # ── The instrument ──
        'consensus_integrity': consensus,

        # ── Vectors ──
        'hybrid_tempo':               interp.get('hybrid_tempo'),
        'casualty_tripwire':          casualty,
        'ukraine_wedge':              interp.get('ukraine_wedge'),
        'logistics_spine':            interp.get('logistics_spine'),
        'instrumentalized_migration': interp.get('instrumentalized_migration'),
        'cohabitation':               interp.get('cohabitation'),
        'defence_attrition':          interp.get('defence_attrition'),
        'election_clock':             interp.get('election_clock'),
        'volhynia_window':            interp.get('volhynia_window'),

        # ── Server-side reads (absence-honest) ──
        'refugee_snapshot':   refugee_data,
        'commodity_snapshot': commodity_data,
        'tempo_baseline':     tempo_baseline,
        'corpus_health':      live_corpus,

        'so_what':           interp.get('so_what'),
        'top_signals':       interp.get('top_signals') or [],
        'cross_theater_fingerprints': interp.get('cross_theater_fingerprints'),
        'composite_modifier': score,
        'interpreter_version': interp.get('interpreter_version'),
        'disclaimer': ('This composite is a CONVERGENCE indicator, NOT a probability of '
                       'action.'),
    }

    _redis_set(REDIS_KEY_LATEST, result)
    _write_crosstheater_fingerprint(result, interp)
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at': result['cached_at'], 'theatre_score': score,
        'alert_level': alert,
        'consensus_integrity': consensus.get('integrity'),
        'top_signals': result['top_signals'][:5],
    })

    # ── TEMPO EMITTER (mode='tape') ──
    # Three streams, because Russia never claims: attack tempo, Polish
    # attribution tempo, amplification tempo. Each carries the corpus denominator.
    if TEMPO_AVAILABLE and _tempo_emit:
        try:
            h = interp.get('hybrid_tempo') or {}
            doms = h.get('domains') or {}
            attack = ((doms.get('kinetic') or {}).get('signals', 0)
                      + (doms.get('cyber') or {}).get('signals', 0))
            amplification = ((doms.get('cognitive') or {}).get('signals', 0)
                             + ((interp.get('ukraine_wedge') or {}).get('amplification', 0)))
            _tempo_emit('poland',
                        streams={'attack': attack,
                                 'attribution': h.get('attribution_signals', 0),
                                 'amplification': amplification},
                        corpus=live_corpus)
        except Exception as e:
            print(f'[Poland Rhetoric] Tempo emit failed (non-fatal): {str(e)[:90]}')

    print(f"[Poland Rhetoric] ✅ Scan complete in {elapsed}s — "
          f"consensus {consensus.get('integrity', '--')}/100 "
          f"({consensus.get('state', '--')}), alert {alert}, "
          f"{len(result['top_signals'])} top_signals")
    return result


# ════════════════════════════════════════════════════════════
# BACKGROUND
# ════════════════════════════════════════════════════════════

def _bg_scan():
    time.sleep(150)
    while True:
        try:
            if _acquire_scan_lock():
                run_poland_rhetoric_scan()
            else:
                print('[Poland Rhetoric] Another worker owns the scan window — skipping')
        except Exception as e:
            print(f'[Poland Rhetoric] Background scan error: {str(e)[:110]}')
        time.sleep(12 * 3600)


def start_poland_rhetoric_scanner():
    threading.Thread(target=_bg_scan, daemon=True).start()
    print('[Poland Rhetoric] Background scanner started (12h, cross-worker lock)')


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

def register_poland_rhetoric_endpoints(app):
    from flask import jsonify, request

    @app.route('/api/rhetoric/poland', methods=['GET'])
    def api_rhetoric_poland():
        force = request.args.get('force', 'false').lower() == 'true'
        if not force:
            cached = _redis_get(REDIS_KEY_LATEST)
            if cached:
                cached['cache_status'] = 'cached'
                return jsonify(cached)
        return jsonify(run_poland_rhetoric_scan(force=True))

    @app.route('/api/rhetoric/poland/summary', methods=['GET'])
    def api_rhetoric_poland_summary():
        d = _redis_get(REDIS_KEY_LATEST) or {}
        c = d.get('consensus_integrity') or {}
        return jsonify({
            'theatre': 'poland', 'flag': '\U0001f1f5\U0001f1f1',
            'theatre_score': d.get('theatre_score', 0),
            'alert_level': d.get('alert_level', 'normal'),
            'consensus_integrity': c.get('integrity'),
            'consensus_state': c.get('state'),
            'casualty_tripwire': (d.get('casualty_tripwire') or {}).get('state'),
            'top_signals': (d.get('top_signals') or [])[:3],
            'cached_at': d.get('cached_at'),
        })

    @app.route('/api/rhetoric/poland/history', methods=['GET'])
    def api_rhetoric_poland_history():
        try:
            r = requests.get(f'{UPSTASH_REDIS_URL}/lrange/{REDIS_KEY_HISTORY}/0/59',
                             headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                             timeout=8)
            raw = (r.json() or {}).get('result') or []
            entries = []
            for item in raw:
                try:
                    e = json.loads(item)
                    entries.append({'date': e.get('cached_at'),
                                    'score': e.get('theatre_score', 0),
                                    'alert': e.get('alert_level'),
                                    'consensus_integrity': e.get('consensus_integrity')})
                except Exception:
                    continue
            entries.reverse()
            return jsonify({'theatre': 'poland', 'entries': entries})
        except Exception as e:
            return jsonify({'theatre': 'poland', 'entries': [], 'error': str(e)[:120]})

    @app.route('/debug/poland-rhetoric', methods=['GET'])
    def debug_poland_rhetoric():
        d = _redis_get(REDIS_KEY_LATEST) or {}
        return jsonify({
            'tracker_version':      TRACKER_VERSION,
            'interpreter_available': _INTERPRETER_AVAILABLE,
            'tempo_available':      TEMPO_AVAILABLE,
            'telegram_available':   TELEGRAM_AVAILABLE,
            'bluesky_available':    BLUESKY_AVAILABLE,
            'cached':               bool(d),
            'cached_at':            d.get('cached_at'),
            'total_articles':       d.get('total_articles'),
            'corpus_health':        d.get('corpus_health'),
            'consensus_integrity':  d.get('consensus_integrity'),
            'refugee_snapshot':     d.get('refugee_snapshot'),
            'commodity_snapshot':   d.get('commodity_snapshot'),
            'tempo_baseline_ready': (d.get('tempo_baseline') or {}).get('ready'),
            'top_signals_count':    len(d.get('top_signals') or []),
            'rss_feeds':            len(RSS_FEEDS),
            'actors':               list(ACTORS.keys()),
        })

    print('[Poland Rhetoric] ✅ Endpoints registered: /api/rhetoric/poland, '
          '/summary, /history, /debug/poland-rhetoric')
