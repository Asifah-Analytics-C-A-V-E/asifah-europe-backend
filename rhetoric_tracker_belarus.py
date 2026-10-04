"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — BELARUS RHETORIC TRACKER
  v1.2.0 (Oct 4 2026)
═══════════════════════════════════════════════════════════════════════

v1.2.0 (Oct 4 2026) — FEED ROSTER REPAIR, against measured evidence

  Every feed below was probed from an INDEPENDENT NETWORK (not Render) on
  2026-10-04, which is the only way to tell "this host blocks datacenters"
  apart from "this feed is dead". Results:

    Nasha Niva (BE)   200, 53,430 bytes   -> ALIVE
    Zviazda (BE)      200, 225,358 bytes  -> ALIVE
    Radio Svaboda(BE) 200, 22,689 bytes   -> ALIVE
    RFE/RL BY         200, 11 BYTES       -> ZOMBIE (see below)
    Viasna            403                 -> blocked on BOTH networks
    Euroradio (BE)    403                 -> blocked on BOTH networks
    BelTA EN          404                 -> gone
    NEXTA             connection closed   -> gone (Render saw 404)

  TWO FINDINGS WORTH RECORDING:

  1. v1.1.0's claim that Nasha Niva and Zviazda return "malformed XML" was
     WRONG, and wrong in an instructive way. They serve 53KB and 225KB of
     perfectly good content. The old code called feedparser.parse(url),
     which fetches with feedparser's own User-Agent; the "not well-formed
     (invalid token): line 8" error is what you get when an HTML challenge
     page is handed to an XML parser. We were not reading a broken feed --
     we were reading a page that was not the feed at all. v1.1.0's switch to
     requests + a descriptive UA is expected to have fixed both without any
     URL change. Watch the next scan to confirm.

  2. RFE/RL's Belarus feed answers HTTP 200 with an ELEVEN BYTE body. That is
     the most dangerous failure shape on the roster -- worse than a 404,
     because a 200 reads as healthy at every layer and the resulting "0 items"
     is indistinguishable from a quiet news day in Belarus. A 404 at least
     announces itself. Hence the zombie guard in _fetch_rss.

  Four confirmed-dead feeds are now marked status='broken' and SKIPPED, but
  they are still listed, dated, and reported in sensing['rss']['known_broken'].
  Skipping a known-dead source is efficiency; forgetting it is how a roster
  quietly shrinks to nothing and nobody notices the country went dark.

  SOURCING-BIAS NOTE, which matters more than the weights suggest: BelTA is
  the REGIME voice. With it gone, the live roster reads Belarus almost
  entirely through opposition and exile outlets (Nasha Niva, Radio Svaboda),
  with Zviazda the only state-affiliated survivor. That is a one-sided
  corpus, and an analyst reading this tracker should know it. Replacing
  BelTA is worth more than its 0.65 weight implies.

v1.1.0 (Oct 4 2026) — SOURCE DISCIPLINE PASS
  1. GDELT routes through gdelt_gateway. This file was calling
     api.gdeltproject.org directly with a 5s read timeout and no circuit
     breaker; a live log shows twelve-plus consecutive "Read timed out"
     lines from it, in a process where the gateway already knew GDELT was
     unreachable.
  2. Reddit User-Agent is honest and failures are LOGGED. The old code sent
     'Asifah-Analytics/1.0' and did a bare `continue` on any non-200 -- no
     print, no counter. Reddit could have been refusing every request for
     months and this tracker would have reported "0 posts" indistinguishably
     from a quiet weekend.
  3. RSS failures are VISIBLE. feedparser.parse(url) swallows the transport
     layer: a 403, a 404 and a valid-but-empty feed all arrive as
     `entries == []`, so a dead feed read downstream as a quiet country.
     (The specific diagnosis written here in v1.1.0 -- "Nasha Niva and
     Zviazda returning malformed XML" -- was corrected by measurement in
     v1.2.0 above. The mechanism was right; the attribution was not.)
  4. Absence-honest sensing block in the result payload.

OPEN ITEM (Oct 4 2026): replacement URLs for the four dead feeds are NOT in
this file. They were not verifiable at authoring time, and guessing a feed
URL is how a tracker ends up silently reading nothing. Each failure is now
recorded with its status code and the date it was checked, so the repair is
a bounded errand against evidence rather than a search.

Multi-actor rhetoric tracker for Belarus. Aggregates signals across:
  - RSS (NEXTA, Meduza, RFE/RL Belarus, Viasna, BelTA, Reuters)
  - GDELT multi-language queries (English + Russian Cyrillic)
  - NewsAPI fallback
  - Brave Search tertiary fallback
  - Telegram channels (BELARUS_CHANNELS from telegram_signals_europe)
  - Bluesky (Tsikhanouskaya, NEXTA, opposition figures)
  - Reddit (/r/belarus, /r/europe, /r/credibledefense)

Calls belarus_signal_interpreter.interpret_signals() for analytical layer
(red lines, green lines, So What, top_signals, fingerprints).

Writes Redis cache key 'rhetoric:belarus:latest' for consumption by
europe_regional_bluf.py and the rhetoric-belarus.html frontend.

ENDPOINTS:
  GET /api/rhetoric/belarus          — full scan result
  GET /api/rhetoric/belarus/summary  — short-form for hub pages
  GET /api/rhetoric/belarus/history  — recent scans (paginated)

BACKGROUND REFRESH:
  Runs every 6 hours in a daemon thread (canonical pattern).
"""

import os
import json
import time
import threading
import requests
import feedparser
from datetime import datetime, timezone
from flask import jsonify, request

# Optional: telegram + bluesky integration (graceful if unavailable)
try:
    from telegram_signals_europe import fetch_belarus_telegram_signals
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print('[Belarus Rhetoric] Telegram signals not available')

try:
    from bluesky_signals_europe import fetch_belarus_bluesky_signals
    BLUESKY_AVAILABLE = True
except ImportError:
    BLUESKY_AVAILABLE = False
    print('[Belarus Rhetoric] Bluesky signals not available')

from belarus_signal_interpreter import interpret_signals

# ============================================================
# CONFIGURATION
# ============================================================

UPSTASH_REDIS_URL    = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN  = os.environ.get('UPSTASH_REDIS_TOKEN')
NEWSAPI_KEY          = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY        = os.environ.get('BRAVE_API_KEY')

GDELT_BASE_URL       = 'https://api.gdeltproject.org/api/v2/doc/doc'
NEWSAPI_BASE_URL     = 'https://newsapi.org/v2/everything'
BRAVE_BASE_URL       = 'https://api.search.brave.com/res/v1/news/search'

REDIS_KEY_LATEST     = 'rhetoric:belarus:latest'
REDIS_KEY_HISTORY    = 'rhetoric:belarus:history'
REFRESH_INTERVAL_SEC = 6 * 3600   # 6h

TRACKER_VERSION = '1.2.0'

TRACKER_USER_AGENT = (f'AsifahAnalytics-Europe-Belarus/{TRACKER_VERSION} '
                      f'(OSINT monitoring tool; +https://asifahanalytics.com)')
REDDIT_USER_AGENT = TRACKER_USER_AGENT

try:
    from gdelt_gateway import gdelt_fetch_probed as _gw_fetch_probed
    GDELT_GATEWAY = True
except ImportError:
    GDELT_GATEWAY = False
    print('[Belarus GDELT] gdelt_gateway unavailable -- direct calls (unpaced)')

_scan_lock = threading.Lock()


# ============================================================
# RSS FEEDS
# ============================================================
RSS_FEEDS = [
    # Independent / opposition (English)
    # BROKEN (verified 2026-10-04, independent network): connection closed
    # unexpectedly. Render reported HTTP 404 the same day. URL retained so the
    # roster records what we LOST, not a blank where a source used to be.
    {'name': 'NEXTA',                     'url': 'https://nexta.tv/en/rss',                                'weight': 0.95, 'language': 'eng', 'status': 'broken', 'checked': '2026-10-04', 'reason': 'connection closed / 404'},
    {'name': 'Meduza (English)',          'url': 'https://meduza.io/rss/en/all',                           'weight': 0.90, 'language': 'eng'},
    # ZOMBIE (verified 2026-10-04): HTTP 200 with an ELEVEN BYTE body. The most
    # dangerous failure shape here -- a 200 reads as healthy everywhere, and
    # "0 items" from a 200 is indistinguishable from a quiet news day.
    {'name': 'RFE/RL Belarus Service',    'url': 'https://www.rferl.org/api/zypppgmm-en',                  'weight': 0.95, 'language': 'eng', 'status': 'broken', 'checked': '2026-10-04', 'reason': 'HTTP 200, 11-byte empty body'},
    # BROKEN (verified 2026-10-04): HTTP 403 from BOTH a residential IP and the
    # Render host, so this is not a datacenter-IP block -- the path refuses us
    # outright. Viasna is the human-rights record for Belarus; worth replacing.
    {'name': 'Viasna Human Rights',       'url': 'https://spring96.org/en/rss',                            'weight': 0.95, 'language': 'eng', 'status': 'broken', 'checked': '2026-10-04', 'reason': 'HTTP 403 (residential + datacenter)'},
    # International coverage (English)
    {'name': 'Reuters Europe',            'url': 'https://www.reutersagency.com/feed/?best-regions=europe&post_type=best',  'weight': 0.90, 'language': 'eng'},
    {'name': 'Politico Europe',           'url': 'https://www.politico.eu/feed/',                          'weight': 0.85, 'language': 'eng'},
    {'name': 'Euractiv',                  'url': 'https://www.euractiv.com/feed/',                         'weight': 0.80, 'language': 'eng'},
    # State / regime English (counter-narrative)
    # BROKEN (verified 2026-10-04): HTTP 404. BelTA is the REGIME voice -- see
    # the sourcing-bias note in the module docstring. Its loss costs more than
    # its 0.65 weight: without it the roster reads Belarus from one side only.
    {'name': 'BelTA (state media, EN)',   'url': 'https://eng.belta.by/rss',                               'weight': 0.65, 'language': 'eng', 'status': 'broken', 'checked': '2026-10-04', 'reason': 'HTTP 404'},
    # ───── BELARUSIAN-LANGUAGE NATIVE FEEDS (be) ─────
    # Nasha Niva — primary Belarusian-language opposition outlet (in exile, est. 1906; "extremist" per regime)
    # VERIFIED ALIVE 2026-10-04: 200, 53,430 bytes. v1.1.0 called this feed
    # malformed; it was not -- feedparser's own fetch was getting something
    # other than the feed. See the v1.2.0 note in the module docstring.
    {'name': 'Nasha Niva (BE)',           'url': 'https://nashaniva.com/rss',                              'weight': 0.95, 'language': 'bel'},
    # Zviazda — oldest Belarusian-language publication (state-affiliated counter-narrative)
    # VERIFIED ALIVE 2026-10-04: 200, 225,358 bytes. Same correction as above.
    # Now the only state-affiliated voice left on the roster.
    {'name': 'Zviazda (BE)',              'url': 'https://zviazda.by/be/rss.xml',                          'weight': 0.65, 'language': 'bel'},
    # Euroradio Belarusian service — independent, Belarusian-language
    # BROKEN (verified 2026-10-04): HTTP 403 on both networks.
    {'name': 'Euroradio (BE)',            'url': 'https://euroradio.fm/be/rss',                            'weight': 0.90, 'language': 'bel', 'status': 'broken', 'checked': '2026-10-04', 'reason': 'HTTP 403 (residential + datacenter)'},
    # Radio Svaboda (RFE/RL Belarusian service) — Belarusian-language
    # VERIFIED ALIVE 2026-10-04: 200, 22,689 bytes. Note that RFE/RL's ENGLISH
    # Belarus feed above is the 11-byte zombie while this Belarusian-language
    # one is healthy -- same organisation, two very different feed endpoints.
    {'name': 'Radio Svaboda (BE)',        'url': 'https://www.svaboda.org/api/epiqq',                      'weight': 0.95, 'language': 'bel'},
]


# ============================================================
# ACTORS (7-actor framework per analytical plan)
# ============================================================
ACTORS = {
    'lukashenko_regime': {
        'name': 'Lukashenko Regime',
        'flag': '🇧🇾',
        'icon': '👤',
        'color': '#dc2626',
        'role': 'Domestic regime apparatus, KGB, propaganda, succession',
        'description': (
            'Lukashenko personally + presidential administration + KGB + '
            'security services. Watch for: succession signals, health '
            'language, opposition crackdown intensity, Article 130 cases, '
            'rhetoric tone shifts, propaganda lines.'
        ),
        'keywords': [
            'lukashenko', 'aleksandr lukashenko', 'alexander lukashenko',
            'belarusian president', 'pul_1', 'presidential administration belarus',
            'belarusian kgb', 'kgb belarus', 'belarusian security service',
            'minsk regime', 'belarusian propaganda',
            'лукашенко', 'президент беларуси',
            'health concerns', 'absent from public', 'medical leave',
            'transitional council', 'succession belarus',
        ],
    },
    'russian_forces_in_belarus': {
        'name': 'Russian Forces in Belarus',
        'flag': '🇷🇺',
        'icon': '⚔️',
        'color': '#7f1d1d',
        'role': 'Russian military deployments, nuclear systems, Ukraine staging',
        'description': (
            'Russian forces stationed in or operating from Belarusian '
            'territory. Watch for: Iskander movements, Asipovichy nuclear '
            'storage, joint exercises (Zapad), staging for Ukraine '
            'operations, S-400 deployments.'
        ),
        'keywords': [
            'russian forces belarus', 'russian troops belarus',
            'iskander belarus', 'asipovichy', 'nuclear storage belarus',
            'tactical nuclear belarus', 'warhead belarus',
            'zapad exercise', 'russian-belarusian exercise',
            's-400 belarus', 'air defense belarus', 'russian instructors belarus',
            'российские войска беларусь', 'искандер беларусь',
            'тактическое ядерное', 'учения запад',
        ],
    },
    'belarusian_opposition': {
        'name': 'Belarusian Opposition',
        'flag': '✊',
        'icon': '🟥⬜🟥',
        'color': '#16a34a',
        'role': 'Tsikhanouskaya, Coordination Council, Kalinouski Regiment, exiles',
        'description': (
            'Democratic opposition operating primarily from Vilnius/Warsaw/'
            'Berlin. Watch for: Tsikhanouskaya statements, United Transitional '
            'Cabinet decisions, prisoner releases, Kalinouski Regiment '
            'developments, NEXTA reporting.'
        ),
        'keywords': [
            'tsikhanouskaya', 'sviatlana tsikhanouskaya', 'svetlana tikhanovskaya',
            'united transitional cabinet', 'coordination council belarus',
            'kalinouski regiment', 'kalinouski battalion',
            'nexta', 'belsat', 'viasna', 'bialiatski', 'ales bialiatski',
            'belarusian opposition', 'belarusian dissidents',
            'political prisoners belarus', 'belarusian exiles',
            'тихановская', 'координационный совет',
        ],
    },
    'nato_border_states': {
        'name': 'NATO Border States',
        'flag': '🇵🇱🇱🇹🇱🇻',
        'icon': '🛡️',
        'color': '#3b82f6',
        'role': 'Poland + Lithuania + Latvia coordinated response',
        'description': (
            'NATO neighbors\' coordinated response — border closures, '
            'troop deployments, migrant pushback, EU/NATO advocacy. '
            'Treated as one actor because they coordinate so closely '
            '(joint declarations, EU sanction packages, NATO statements).'
        ),
        'keywords': [
            'poland border belarus', 'lithuania border belarus',
            'latvia border belarus', 'frontex', 'polish border guard',
            'lithuanian border', 'latvian border guard',
            'suwalki gap', 'suwałki', 'baltic land bridge',
            'nato eastern flank', 'nato forward presence',
            'polish-belarusian border', 'bialystok',
            'migrant pushback', 'border barrier belarus', 'border wall',
            'польша беларусь граница', 'литва беларусь',
        ],
    },
    'iran_belarus_axis': {
        'name': 'Iran-Belarus Axis',
        'flag': '🇮🇷🇧🇾',
        'icon': '🤝',
        'color': '#a16207',
        'role': 'SCO trilateral, defense cooperation, Apr 27 trilateral',
        'description': (
            'Defense and political cooperation between Tehran and Minsk, '
            'particularly via SCO framework. Watch for: Khrenin–Talaei-Nik '
            'meetings, drone technology transfer, joint exercise language, '
            'SCO trilateral signals.'
        ),
        'keywords': [
            'khrenin talaei', 'khrenin tehran', 'minsk tehran',
            'belarus iran cooperation', 'iran belarus defense',
            'iran belarus military', 'sco belarus iran',
            'shanghai cooperation belarus iran',
            'iranian defense minister belarus', 'belarus defense iran',
            'shahed belarus', 'iran drone belarus',
            'трехсторонний иран беларусь', 'иран беларусь оборона',
        ],
    },
    'china_belarus_axis': {
        'name': 'China-Belarus Axis',
        'flag': '🇨🇳🇧🇾',
        'icon': '🏗️',
        'color': '#7c3aed',
        'role': 'SCO membership, BRI rail, Great Stone industrial park',
        'description': (
            'Strategic anchor relationship — SCO full membership 2024, '
            'Great Stone industrial park, BRI rail (sanctions bypass for '
            'Belarusian potash/petroleum), PLA military cooperation MoUs.'
        ),
        'keywords': [
            'china belarus', 'beijing minsk', 'great stone industrial park',
            'belt and road belarus', 'bri rail belarus',
            'china-belarus military', 'pla belarus', 'plaaf belarus',
            'sco belarus full member', 'shanghai cooperation belarus china',
            'chinese investment belarus', 'china belarus partnership',
            'китай беларусь', 'великий камень',
        ],
    },
    'ukraine_border_signals': {
        'name': 'Ukraine Border Signals',
        'flag': '🇺🇦',
        'icon': '🚀',
        'color': '#0891b2',
        'role': 'Ukraine border drone attacks, missile staging visibility',
        'description': (
            'Activity along the 1,084 km Belarus–Ukraine border. Watch for: '
            'Ukrainian drone strikes on Belarusian airfields, Russian '
            'missile launches from Belarusian territory, Belarusian border '
            'troop movements, refugee/border crossing dynamics.'
        ),
        'keywords': [
            'belarus ukraine border', 'belarusian-ukrainian border',
            'machulishchy', 'baranavichy airbase', 'lida airbase',
            'ukrainian drone belarus', 'kyiv strike belarus airfield',
            'russian missile from belarus', 'cruise missile belarus',
            'ukrainian partisan belarus', 'belarus-ukraine frontier',
            'граница беларусь украина', 'удар беспилотник беларусь',
        ],
    },
}


# ============================================================
# GDELT QUERIES
# ============================================================
GDELT_QUERIES = {
    'eng': [
        '"belarus" AND ("lukashenko" OR "minsk")',
        '"belarus" AND ("nato" OR "poland" OR "lithuania")',
        '"belarus" AND ("iran" OR "sco" OR "khrenin")',
        '"belarus" AND ("nuclear" OR "iskander" OR "asipovichy")',
        '"belarus" AND ("opposition" OR "tsikhanouskaya" OR "viasna")',
        '"belarus" AND ("china" OR "great stone" OR "bri")',
        '"belarus border" AND ("ukraine" OR "drone" OR "strike")',
    ],
    'rus': [
        '"беларусь" AND ("лукашенко" OR "минск")',
        '"беларусь" AND ("нато" OR "польша" OR "литва")',
        '"беларусь" AND ("иран" OR "шос")',
        '"беларусь" AND ("ядерное" OR "искандер")',
    ],
    # Belarusian Cyrillic — uses native spellings (Лукашэнка vs Лукашенко, Беларусь same in both)
    'bel': [
        '"беларусь" AND ("лукашэнка" OR "мінск")',
        '"беларусь" AND ("нато" OR "польшча" OR "літва")',
        '"беларусь" AND ("апазіцыя" OR "ціханоўская" OR "вясна")',
        '"беларусь" AND ("ядзерны" OR "іскандэр")',
    ],
}


# ============================================================
# KEYWORDS FOR REDDIT / GENERAL FILTERING
# ============================================================
BELARUS_TOPIC_KEYWORDS = [
    'belarus', 'belarusian', 'lukashenko', 'minsk', 'nexta',
    'tsikhanouskaya', 'tikhanovskaya', 'belaruskali', 'asipovichy',
    'viasna', 'bialiatski', 'kalinouski', 'pul_1',
    'беларусь', 'белоруссия', 'лукашенко', 'минск',
]


# ============================================================
# REDIS HELPERS
# ============================================================

def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(
            f'{UPSTASH_REDIS_URL}/get/{key}',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=5
        )
        d = r.json()
        if d.get('result'):
            return json.loads(d['result'])
    except Exception as e:
        print(f'[Belarus Rhetoric] Redis get error: {str(e)[:120]}')
    return None


def _redis_set(key, value):
    # Canonical Upstash REST write: POST the BASE url with a command array
    # ["SET", key, value]. (The previous /set/{key} + {'value': body} form
    # wrapped the payload as {"value": "<json>"}, so nothing read back cleanly --
    # blank tracker, "Unavailable" BLUF, re-scan every visit.) No TTL: the key
    # persists until the next scan overwrites it, so there is ALWAYS something
    # for the interpreter, the regional BLUF, and the analyst to read.
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(
            UPSTASH_REDIS_URL,
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=['SET', key, json.dumps(value, default=str)],
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f'[Belarus Rhetoric] Redis set error: {str(e)[:120]}')
        return False


def _redis_lpush_trim(key, value, max_len=120):
    """Push to list head; trim to max_len. Used for history."""
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        requests.post(
            UPSTASH_REDIS_URL,
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=['LPUSH', key, json.dumps(value, default=str)],
            timeout=10
        )
        requests.post(
            UPSTASH_REDIS_URL,
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=['LTRIM', key, 0, max_len - 1],
            timeout=5
        )
        return True
    except Exception as e:
        print(f'[Belarus Rhetoric] Redis lpush error: {str(e)[:120]}')
        return False


# ============================================================
# FETCHERS
# ============================================================

def _parse_pub_date(pub_str):
    if not pub_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_str).isoformat()
    except Exception:
        return pub_str


def _fetch_rss(url, source_name, weight=0.85, max_items=20, language='eng'):
    """Fetch over requests FIRST so transport failures are visible.

    feedparser.parse(url) fetches internally and reports a 403, a 404, a
    dropped connection and a genuinely empty feed all the same way: zero
    entries. That is the absence-honesty problem in miniature -- six of this
    tracker's feeds were dead and the logs said nothing.
    """
    out = []
    try:
        r = requests.get(url, headers={'User-Agent': TRACKER_USER_AGENT}, timeout=12)
        if r.status_code != 200:
            print(f'[Belarus RSS] {source_name}: HTTP {r.status_code} -- feed not read')
            return out
        # ZOMBIE GUARD (v1.2.0, 2026-10-04): RFE/RL's Belarus feed answers 200
        # with an ELEVEN BYTE body. A 200 reads as healthy at every layer above
        # this one, and the resulting "0 items" is indistinguishable from a
        # quiet news day. A real RSS document cannot be this small.
        if len(r.content or b'') < 200:
            print(f'[Belarus RSS] {source_name}: HTTP 200 but only '
                  f'{len(r.content or b"")} bytes -- empty feed, NOT quiet news')
            return out
        feed = feedparser.parse(r.content)
        if getattr(feed, 'bozo', 0) and not (feed.entries or []):
            print(f'[Belarus RSS] {source_name}: unparseable feed '
                  f'({str(getattr(feed, "bozo_exception", ""))[:90]})')
            return out
        for entry in (feed.entries or [])[:max_items]:
            out.append({
                'title':       entry.get('title', '')[:300],
                'description': (entry.get('summary') or entry.get('description') or '')[:600],
                'url':         entry.get('link', ''),
                'published':   _parse_pub_date(entry.get('published') or entry.get('updated')),
                'source':      source_name,
                'source_type': 'rss',
                'weight':      weight,
                'language':    language,
            })
        print(f'[Belarus RSS] {source_name}: {len(out)} items')
    except Exception as e:
        print(f'[Belarus RSS] {source_name}: {type(e).__name__}: {str(e)[:110]}')
    return out


def _shape_gdelt(raw, language):
    """Gateway article dicts -> this tracker's article shape. Fields unchanged."""
    out = []
    for a in raw or []:
        out.append({
            'title':       (a.get('title') or '')[:300],
            'description': '',
            'url':         a.get('url', ''),
            'published':   a.get('published') or a.get('seendate'),
            'source':      a.get('source') or a.get('domain') or 'gdelt',
            'source_type': 'gdelt',
            'language':    language,
            'weight':      0.7,
        })
    return out


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    """Single GDELT query. Returns (articles, sensed).

    sensed=False means GDELT never answered -- the caller must not read the
    resulting empty list as an absence of Belarus news.
    """
    if GDELT_GATEWAY:
        raw, probe = _gw_fetch_probed(query, language=language,
                                      timespan=f'{days*24}h',
                                      maxrecords=max_records,
                                      label=f'belarus/{language}')
        return _shape_gdelt(raw, language), bool(probe.get('sensed'))

    params = {
        'query':        query,
        'mode':         'artlist',
        'maxrecords':   max_records,
        'format':       'json',
        'sort':         'datedesc',
        'timespan':     f'{days*24}h',
        'sourcelang':   language,
    }
    try:
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=(10, 25))
        if resp.status_code == 429:
            print('[Belarus GDELT] Rate limited (429) -- backing off')
            return [], False
        if resp.status_code != 200:
            print(f'[Belarus GDELT] HTTP {resp.status_code}')
            return [], False
        return _shape_gdelt(resp.json().get('articles') or [], language), True
    except Exception as e:
        print(f'[Belarus GDELT] Query error: {str(e)[:120]}')
        return [], False


def _fetch_newsapi(query='belarus', max_records=40):
    if not NEWSAPI_KEY:
        return []
    params = {
        'q':          query,
        'pageSize':   max_records,
        'language':   'en',
        'sortBy':     'publishedAt',
        'apiKey':     NEWSAPI_KEY,
    }
    try:
        r = requests.get(NEWSAPI_BASE_URL, params=params, timeout=10)
        if r.status_code != 200:
            print(f'[Belarus NewsAPI] HTTP {r.status_code}')
            return []
        out = []
        for a in (r.json().get('articles') or []):
            out.append({
                'title':       (a.get('title') or '')[:300],
                'description': (a.get('description') or '')[:600],
                'url':         a.get('url', ''),
                'published':   a.get('publishedAt'),
                'source':      (a.get('source') or {}).get('name', 'newsapi'),
                'source_type': 'newsapi',
                'weight':      0.85,
            })
        return out
    except Exception as e:
        print(f'[Belarus NewsAPI] {str(e)[:120]}')
        return []


def _fetch_brave(query='belarus politics', max_records=20):
    """Tertiary fallback for low-volume scans."""
    if not BRAVE_API_KEY:
        return []
    headers = {
        'Accept':              'application/json',
        'X-Subscription-Token': BRAVE_API_KEY,
    }
    params = {'q': query, 'count': max_records, 'freshness': 'pw'}
    try:
        r = requests.get(BRAVE_BASE_URL, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return []
        out = []
        for a in (r.json().get('results') or []):
            out.append({
                'title':       (a.get('title') or '')[:300],
                'description': (a.get('description') or '')[:600],
                'url':         a.get('url', ''),
                'published':   a.get('age'),
                'source':      (a.get('meta_url') or {}).get('hostname', 'brave'),
                'source_type': 'brave',
                'weight':      0.75,
            })
        return out
    except Exception as e:
        print(f'[Belarus Brave] {str(e)[:120]}')
        return []


def _fetch_reddit():
    """Belarus-relevant subreddits. Returns (posts, probe).

    The old version sent 'Asifah-Analytics/1.0' and swallowed every non-200
    with a bare `continue`. Reddit could have been refusing all six subreddits
    for months and the tracker would have reported "0 posts" -- the exact
    shape of a silence mistaken for calm.
    """
    out = []
    subs = ['belarus', 'europe', 'CredibleDefense', 'LessCredibleDefence',
            'geopolitics', 'ukraine']
    probe = {'attempted': 0, 'ok': 0, 'blocked': 0, 'status': {}}
    for sub in subs:
        probe['attempted'] += 1
        try:
            url = f'https://www.reddit.com/r/{sub}/new.json?limit=25'
            r = requests.get(
                url,
                headers={'User-Agent': REDDIT_USER_AGENT,
                         'Accept': 'application/json'},
                timeout=8
            )
            if r.status_code != 200:
                probe['blocked'] += 1
                probe['status'][sub] = r.status_code
                print(f'[Belarus Reddit] r/{sub}: HTTP {r.status_code}')
                continue
            probe['ok'] += 1
            for child in (r.json().get('data', {}).get('children') or []):
                p = child.get('data', {})
                title = (p.get('title') or '').lower()
                # Filter: must mention Belarus topic
                if not any(kw in title for kw in BELARUS_TOPIC_KEYWORDS):
                    continue
                out.append({
                    'title':       p.get('title', '')[:300],
                    'description': (p.get('selftext') or '')[:400],
                    'url':         f"https://reddit.com{p.get('permalink', '')}",
                    'published':   datetime.fromtimestamp(
                        p.get('created_utc', 0), tz=timezone.utc
                    ).isoformat() if p.get('created_utc') else None,
                    'source':      f'reddit-{sub}',
                    'source_type': 'reddit',
                    'score':       p.get('score', 0),
                    'comments':    p.get('num_comments', 0),
                    'weight':      0.65,
                })
        except Exception as e:
            probe['blocked'] += 1
            probe['status'][sub] = type(e).__name__
            print(f'[Belarus Reddit] r/{sub}: {str(e)[:120]}')
        time.sleep(0.3)  # rate-limit politeness
    if probe['ok'] == 0:
        print(f'[Belarus Reddit] NOT SENSED -- 0 of {probe["attempted"]} subreddits '
              f'answered ({probe["status"]}). Missing data, not an absent conversation.')
    else:
        print(f'[Belarus Reddit] {len(out)} posts from '
              f'{probe["ok"]}/{probe["attempted"]} subreddits')
    return out, probe


def _fetch_all_articles():
    """Run all article fetchers, dedupe by URL. Returns (articles, sensing)."""
    articles = []
    sensing = {
        'rss':     {'attempted': 0, 'ok': 0, 'empty': [], 'known_broken': []},
        'gdelt':   {'attempted': 0, 'sensed': 0},
        'newsapi': {'attempted': 0, 'ok': 0},
        'brave':   {'attempted': 0, 'ok': 0},
    }

    # RSS -- per-feed, so a dead feed is named rather than averaged away.
    # Feeds marked status='broken' are NOT fetched (four confirmed-dead URLs
    # cost ~12s of every scan and filled the log with the same four errors),
    # but they ARE still counted and named in sensing. Skipping a known-dead
    # source is efficiency; forgetting it is how a roster quietly shrinks.
    for feed in RSS_FEEDS:
        if feed.get('status') == 'broken':
            sensing['rss']['known_broken'].append(
                f"{feed['name']} ({feed.get('reason', 'unverified')})")
            continue
        sensing['rss']['attempted'] += 1
        got = _fetch_rss(feed['url'], feed['name'], feed['weight'],
                         language=feed.get('language', 'eng'))
        if got:
            sensing['rss']['ok'] += 1
        else:
            sensing['rss']['empty'].append(feed['name'])
        articles.extend(got)

    # GDELT -- no local sleep: the gateway paces process-wide.
    for lang, queries in GDELT_QUERIES.items():
        for q in queries:
            sensing['gdelt']['attempted'] += 1
            got, sensed = _fetch_gdelt(q, language=lang, days=7)
            if sensed:
                sensing['gdelt']['sensed'] += 1
            articles.extend(got)

    # NewsAPI fallback (only if RSS+GDELT thin)
    if len(articles) < 30:
        sensing['newsapi']['attempted'] += 1
        got = _fetch_newsapi('belarus', max_records=40)
        if got:
            sensing['newsapi']['ok'] += 1
        articles.extend(got)

    # Brave tertiary fallback (only if still thin)
    if len(articles) < 15:
        sensing['brave']['attempted'] += 1
        got = _fetch_brave('belarus lukashenko', max_records=20)
        if got:
            sensing['brave']['ok'] += 1
        articles.extend(got)

    # Dedupe by URL
    seen = set()
    unique = []
    for a in articles:
        u = a.get('url')
        if u and u not in seen:
            seen.add(u)
            unique.append(a)

    sensing['any_sensed'] = bool(
        sensing['rss']['ok'] or sensing['gdelt']['sensed']
        or sensing['newsapi']['ok'] or sensing['brave']['ok'])
    sensing['degraded'] = (
        sensing['gdelt']['attempted'] > 0
        and sensing['gdelt']['sensed'] == 0) or not sensing['any_sensed']
    return unique, sensing


# ============================================================
# ACTOR CLASSIFICATION
# ============================================================

def _score_article_for_actor(article, actor_def):
    """How strongly does this article relate to a given actor?"""
    text = ' '.join([
        (article.get('title') or '').lower(),
        (article.get('description') or '').lower(),
    ])
    if not text.strip():
        return 0
    matches = 0
    for kw in actor_def.get('keywords', []):
        if kw.lower() in text:
            matches += 1
    return matches


def _classify_articles(articles):
    """Assign each article to one or more actors. Returns dict actor→articles."""
    by_actor = {k: [] for k in ACTORS}
    for art in articles:
        best_actor, best_score = None, 0
        for actor_key, actor_def in ACTORS.items():
            s = _score_article_for_actor(art, actor_def)
            if s > best_score:
                best_score, best_actor = s, actor_key
        if best_actor and best_score >= 1:
            art_copy = dict(art)
            art_copy['actor_score'] = best_score
            by_actor[best_actor].append(art_copy)
    return by_actor


# ============================================================
# THEATRE SCORE
# ============================================================

def _compute_theatre_score(by_actor, articles):
    """
    Derive a 0-100 'pressure' score for the theatre.
    Belarus baseline +9 per project memory (high-pressure tuning).

    ABSENCE CAVEAT (v1.1.0): this is a volume metric. A blind scan scores
    BASELINE and bands as 'normal' -- indistinguishable from a quiet Belarus.
    The math is UNCHANGED so historical series stay comparable; the scan
    records result['sensing'] instead. Wiring blindness into the score is a
    scoring decision for the GPI rollup, not part of a plumbing fix.
    """
    BASELINE = 9
    actor_weights = {
        'lukashenko_regime':         0.85,
        'russian_forces_in_belarus': 1.10,
        'belarusian_opposition':     0.55,
        'nato_border_states':        0.95,
        'iran_belarus_axis':         1.05,
        'china_belarus_axis':        0.80,
        'ukraine_border_signals':    0.95,
    }
    score = BASELINE
    for actor_key, articles_list in by_actor.items():
        weight = actor_weights.get(actor_key, 0.7)
        # Each article above weight 0.5 adds proportionally; cap per-actor at 25
        actor_contribution = min(25, sum(a.get('weight', 0.7) for a in articles_list) * weight)
        score += actor_contribution
    return max(0, min(100, int(score)))


def _alert_level_from_score(score):
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'elevated'
    else:
        return 'normal'


# ============================================================
# CROSS-THEATER FINGERPRINT WRITE
# ============================================================

def _write_cross_theater_fingerprints(fingerprints):
    """Write fingerprint flags to Redis for downstream tracker reads."""
    for key, val in (fingerprints or {}).items():
        try:
            _redis_set(f'fingerprint:belarus:{key}', val)
        except Exception:
            pass


# ============================================================
# CANONICAL SPOKE FINGERPRINT (Rim Emission Pass -- Jul 2026)
# Writes crosstheater:belarus:fingerprint so the Russia wheel's
# _read_spoke_fingerprints() reads Belarus. node_class = aligned_multiplier.
# SURFACE-ONLY: no polarity wired into any score (Belarus escalating is an
# AMPLIFIER, but that read is a wheel scoping decision, not plumbing).
# ============================================================

# Belarus alert enum -> canonical 0-5 level. Belarus is an ALIGNED MULTIPLIER,
# not a combatant -- NO war floor (unlike Ukraine). Reads 'normal' when quiet
# and caps at L4 (Incident): a force multiplier never reaches L5 strategic
# escalation on its own -- that is principal-actor territory.
_SPOKE_LEVEL_BY_ALERT = {
    'normal':   0,   # Baseline -- aligned but quiet
    'elevated': 2,   # Warning -- pressure building (troop movement, rhetoric)
    'high':     3,   # Direct Threat -- Suwalki pressure / mobilization / nuclear-host activity
    'critical': 4,   # Incident -- Belarus directly implicated
}

def _write_canonical_spoke_fingerprint(result):
    """Emit crosstheater:belarus:fingerprint (hub-agnostic per-country schema).

    Read by the Russia wheel (_read_spoke_fingerprints), the Europe BLUF, and
    future Russia-wheel recompute narratives. Runs ALONGSIDE the legacy
    fingerprint:belarus:* writes (emit once, consume many)."""
    alert = result.get('alert_level', 'normal')
    level = _SPOKE_LEVEL_BY_ALERT.get(alert, 0)
    ctf = result.get('cross_theater_fingerprints') or {}
    fingerprint = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'belarus',
        'node_class':  'aligned_multiplier',   # Russia force multiplier / Suwalki Gap
        'level':       level,
        'score':       result.get('theatre_score', 0),
        'alert_level': alert,

        # -- Multiplier slice: what makes Belarus matter to the Russia wheel --
        #    Suwalki/NATO perimeter, Russian force staging, nuclear host posture.
        'multiplier': {
            'russia_axis':             ctf.get('belarus_russia_axis', True),
            'nato_perimeter_pressure': ctf.get('nato_perimeter_pressure', False),
            'wagner_active':           ctf.get('wagner_active_belarus', False),
            'succession_watch':        ctf.get('lukashenko_succession_watch', False),
        },
    }
    try:
        _redis_set('crosstheater:belarus:fingerprint', fingerprint)
        print('[Belarus Rhetoric] Canonical spoke fingerprint written (crosstheater:belarus:fingerprint)')
    except Exception as e:
        print(f'[Belarus Rhetoric] Canonical fingerprint write failed: {e}')


# ============================================================
# MAIN SCAN
# ============================================================

def run_belarus_rhetoric_scan(force=False):
    """
    Full scan orchestrator. Aggregates all sources, classifies by actor,
    runs interpreter, writes Redis cache + history.
    Returns the scan result dict.
    """
    if not force:
        cached = _redis_get(REDIS_KEY_LATEST)
        if cached and cached.get('cached_at'):
            # Serve cached data ALWAYS -- fresh or stale. Never block a page load
            # on a 5-minute scan; the background thread refreshes on schedule and
            # the "Refresh Scan" button (force=true) forces a fresh run. Stale is
            # flagged so the UI / BLUF can show freshness, but it is still served
            # so the analyst always has a read. Only a true cold start (no cache)
            # falls through to the one-time synchronous scan below.
            try:
                cached_at = datetime.fromisoformat(cached['cached_at'])
                age = (datetime.now(timezone.utc) - cached_at).total_seconds()
                cached['cache_status'] = 'hit' if age < REFRESH_INTERVAL_SEC else 'stale'
                cached['cache_age_sec'] = int(age)
            except Exception:
                cached['cache_status'] = 'hit'
            return cached

    print('[Belarus Rhetoric] Starting fresh scan...')
    started = time.time()

    # Articles
    articles, sensing = _fetch_all_articles()
    print(f'[Belarus Rhetoric] Articles: {len(articles)} '
          f'(RSS {sensing["rss"]["ok"]}/{sensing["rss"]["attempted"]}, '
          f'GDELT {sensing["gdelt"]["sensed"]}/{sensing["gdelt"]["attempted"]} sensed)')
    if sensing['rss']['known_broken']:
        print(f'[Belarus Rhetoric] Skipped {len(sensing["rss"]["known_broken"])} '
              f'known-broken feed(s): {"; ".join(sensing["rss"]["known_broken"])}')
    if sensing['rss']['empty']:
        print(f'[Belarus Rhetoric] Live feeds returning nothing: '
              f'{", ".join(sensing["rss"]["empty"])}')
    if not sensing['any_sensed']:
        print('[Belarus Rhetoric] BLIND -- no source family answered. The score '
              'below is the BASELINE FLOOR, not a measurement of a quiet Belarus.')
    elif sensing['degraded']:
        print('[Belarus Rhetoric] DEGRADED -- GDELT contributed nothing this scan.')

    # Telegram
    telegram_messages = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_messages = fetch_belarus_telegram_signals() or []
            print(f'[Belarus Rhetoric] Telegram: {len(telegram_messages)} messages')
        except Exception as e:
            print(f'[Belarus Rhetoric] Telegram fetch error: {str(e)[:120]}')

    # Bluesky
    bluesky_signals = []
    if BLUESKY_AVAILABLE:
        try:
            bluesky_signals = fetch_belarus_bluesky_signals() or []
            print(f'[Belarus Rhetoric] Bluesky: {len(bluesky_signals)} posts')
        except Exception as e:
            print(f'[Belarus Rhetoric] Bluesky fetch error: {str(e)[:120]}')

    # Reddit
    reddit_signals, reddit_probe = _fetch_reddit()
    print(f'[Belarus Rhetoric] Reddit: {len(reddit_signals)} posts')
    sensing['reddit'] = reddit_probe

    # Classify articles by actor
    by_actor = _classify_articles(articles)
    actor_summaries = {}
    for actor_key, actor_articles in by_actor.items():
        actor_def = ACTORS[actor_key]
        actor_summaries[actor_key] = {
            'name':           actor_def['name'],
            'flag':           actor_def['flag'],
            'icon':           actor_def['icon'],
            'color':          actor_def['color'],
            'role':           actor_def['role'],
            'description':    actor_def['description'],
            'article_count':  len(actor_articles),
            'top_articles':   actor_articles[:5],
        }

    # Theatre score
    score = _compute_theatre_score(by_actor, articles)
    alert = _alert_level_from_score(score)

    # Articles by language for interpreter
    articles_en = [a for a in articles if a.get('language', 'eng') in ('eng', 'en', None)]
    articles_ru = [a for a in articles if a.get('language') in ('rus', 'ru')]
    articles_be = [a for a in articles if a.get('language') in ('bel', 'be')]

    # Build scan_data for interpreter
    scan_data = {
        'articles_en':        articles_en,
        'articles_ru':        articles_ru,
        'articles_be':        articles_be,
        'telegram_messages':  telegram_messages,
        'bluesky_signals':    bluesky_signals,
        'reddit_signals':     reddit_signals,
        'by_actor':           by_actor,
        'actor_summaries':    actor_summaries,
        'theatre_score':      score,
        'alert_level':        alert,
    }

    # Run analytical layer
    interpretation = interpret_signals(scan_data)

    # Write cross-theater fingerprints to Redis
    _write_cross_theater_fingerprints(
        interpretation.get('cross_theater_fingerprints') or {}
    )

    # Compose final result
    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'belarus',
        'flag':              '🇧🇾',
        'display_name':      'Belarus',
        'theatre_score':     score,
        'alert_level':       alert,
        'pressure_score':    score,
        'tracker_version':   TRACKER_VERSION,
        # Absence-honest sensing record. Read this before reading the score:
        # any_sensed=False means nothing answered, and theatre_score is then
        # the baseline floor rather than an observation.
        'sensing':           sensing,
        'sensing_degraded':  bool(sensing.get('degraded')),
        'any_source_sensed': bool(sensing.get('any_sensed')),
        'cached_at':         datetime.now(timezone.utc).isoformat(),
        'scan_duration_sec': elapsed,
        'cache_status':      'fresh',
        # Article metadata
        'total_articles':    len(articles),
        'articles_by_source': {
            'rss':     sum(1 for a in articles if a.get('source_type') == 'rss'),
            'gdelt':   sum(1 for a in articles if a.get('source_type') == 'gdelt'),
            'newsapi': sum(1 for a in articles if a.get('source_type') == 'newsapi'),
            'brave':   sum(1 for a in articles if a.get('source_type') == 'brave'),
        },
        'telegram_count':  len(telegram_messages),
        'bluesky_count':   len(bluesky_signals),
        'reddit_count':    len(reddit_signals),
        'articles_en':     articles_en,
        'articles_ru':     articles_ru,
        'articles_be':     articles_be,
        # Full social signal arrays (capped to keep payload manageable)
        'telegram_signals': telegram_messages[:30],
        'bluesky_signals':  bluesky_signals[:30],
        'reddit_signals':   reddit_signals[:30],
        # Actor breakdown
        'actor_summaries': actor_summaries,
        # Interpretation (canonical schema)
        'so_what':         interpretation.get('so_what'),
        'top_signals':     interpretation.get('top_signals') or [],
        'red_lines':       interpretation.get('red_lines'),
        'green_lines':     interpretation.get('green_lines'),
        'diplomatic_track': interpretation.get('diplomatic_track'),
        'commodity_signal': interpretation.get('commodity_signal'),
        'cross_theater_fingerprints': interpretation.get('cross_theater_fingerprints'),
        'composite_modifier': interpretation.get('composite_modifier', 0),
        'interpreter_version': interpretation.get('interpreter_version'),
    }

    # Persist
    _redis_set(REDIS_KEY_LATEST, result)
    _write_canonical_spoke_fingerprint(result)   # Rim Emission Pass -- feed the Russia wheel
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Belarus Rhetoric] Scan complete: score={score}, alert={alert}, '
          f'articles={len(articles)}, elapsed={elapsed}s')
    return result


# ============================================================
# BACKGROUND REFRESH
# ============================================================

def _background_refresh():
    """Daemon: scan every 6 hours."""
    time.sleep(120)  # boot stabilization
    while True:
        try:
            with _scan_lock:
                run_belarus_rhetoric_scan(force=True)
        except Exception as e:
            print(f'[Belarus Rhetoric] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Belarus Rhetoric] Background refresh thread started (6h cycle)')


# ============================================================
# ENDPOINT REGISTRATION
# ============================================================

def register_belarus_rhetoric_endpoints(app):
    """Register Flask endpoints. Call from Europe app.py."""

    @app.route('/api/rhetoric/belarus', methods=['GET'])
    def api_rhetoric_belarus():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            data = run_belarus_rhetoric_scan(force=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error':   str(e)[:200],
                'theatre': 'belarus',
            }), 500

    @app.route('/api/rhetoric/belarus/summary', methods=['GET'])
    def api_rhetoric_belarus_summary():
        """Compact form for hub pages."""
        try:
            d = run_belarus_rhetoric_scan(force=False)
            return jsonify({
                'theatre':         'belarus',
                'flag':            '🇧🇾',
                'display_name':    'Belarus',
                'theatre_score':   d.get('theatre_score', 0),
                'alert_level':     d.get('alert_level', 'normal'),
                'top_signals':     (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'cached_at':       d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/belarus/history', methods=['GET'])
    def api_rhetoric_belarus_history():
        """Recent scan snapshots from Redis list."""
        if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
            return jsonify({'success': False, 'error': 'Redis not configured', 'history': []})
        try:
            limit = min(int(request.args.get('limit', 30)), 120)
            r = requests.get(
                f'{UPSTASH_REDIS_URL}/lrange/{REDIS_KEY_HISTORY}/0/{limit-1}',
                headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                timeout=8
            )
            raw = (r.json().get('result') or []) if r.status_code == 200 else []
            history = []
            for item in raw:
                try:
                    history.append(json.loads(item))
                except Exception:
                    pass
            return jsonify({
                'success': True,
                'theatre': 'belarus',
                'count':   len(history),
                'history': history,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500

    print('[Belarus Rhetoric] Endpoints registered: /api/rhetoric/belarus, /summary, /history')
