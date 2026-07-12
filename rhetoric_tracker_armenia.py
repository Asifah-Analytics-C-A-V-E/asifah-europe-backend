"""
Armenia Rhetoric Tracker v1.0.0 (Jul 12 2026)
==============================================
Multi-vector hybrid tracker (Ukraine model): inbound pressure from three
directions (Russia, Iran, Azerbaijan-dyad) plus a domestic contest, layered
over a peace-implementation diplomatic track and the TRIPP corridor vector.

Calls armenia_signal_interpreter.interpret_signals() for the analytical layer.

EMISSIONS (emit once, consume many):
  rhetoric:armenia:latest              own payload (Europe BLUF, both pages)
  rhetoric:armenia:history             lpush trim 120
  crosstheater:armenia:fingerprint     canonical per-country spoke key --
                                       the Russia wheel's reader is already
                                       deployed and listening for this key.
                                       node_class = friction_drift (the
                                       "Friction / drift-away" taxonomy tier).
                                       SURFACE-ONLY: no polarity wired into
                                       any score. That is a wheel scoping
                                       decision, not plumbing.
  spoke:turkey:armenia                 Turkey-wheel periphery spoke. Schema
                                       from the GPI reader: level /
                                       relationship / top_signal. Polarity is
                                       DYNAMIC: friction baseline, alignment
                                       when the normalization vector warms.

READS (never re-scan):
  crosstheater:azerbaijan:fingerprint  the dyad read. Aliyev rhetoric is
                                       scored by the Azerbaijan tracker; here
                                       it is only READ (absence-honest), and
                                       the azerbaijan_counterparty actor card
                                       is weight 0.0 display-only so nothing
                                       double-counts into the Europe BLUF.

Iran-facing slice rides INSIDE the canonical fingerprint (conditional-buffer
posture + TRIPP flip meter); a shared-dict write is deferred until the Iran
friction-tier reader defines its schema.

Doctrine: convergence, not prediction. Sensors below, analyst above.
"""

import os
import json
import time
import threading
from datetime import datetime, timezone

import requests
import feedparser
from flask import request, jsonify

from armenia_signal_interpreter import interpret_signals

# ============================================================
# CONFIG
# ============================================================

UPSTASH_REDIS_URL    = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN  = os.environ.get('UPSTASH_REDIS_TOKEN')
NEWSAPI_KEY          = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY        = os.environ.get('BRAVE_API_KEY')

GDELT_BASE_URL       = 'https://api.gdeltproject.org/api/v2/doc/doc'
NEWSAPI_BASE_URL     = 'https://newsapi.org/v2/everything'
BRAVE_BASE_URL       = 'https://api.search.brave.com/res/v1/news/search'

REDIS_KEY_LATEST     = 'rhetoric:armenia:latest'
REDIS_KEY_HISTORY    = 'rhetoric:armenia:history'
SPOKE_KEY_CANONICAL  = 'crosstheater:armenia:fingerprint'
SPOKE_KEY_TURKEY     = 'spoke:turkey:armenia'
AZ_FINGERPRINT_KEY   = 'crosstheater:azerbaijan:fingerprint'
SCAN_LOCK_KEY        = 'lock:rhetoric:armenia:scan'
REFRESH_INTERVAL_SEC = 6 * 3600

_scan_lock = threading.Lock()


# ============================================================
# ACTORS
# azerbaijan_counterparty is DISPLAY-ONLY (score weight 0.0): the dyad is
# scored by the Azerbaijan tracker; double-scoring Aliyev into the Europe
# BLUF is the double-count trap. The card exists because Armenia-page
# readers need the counterparty read in one place.
# ============================================================

ACTORS = {
    'armenian_government': {
        'name': 'Armenian Government',
        'flag': '\U0001f1e6\U0001f1f2',
        'icon': '\U0001f3db\ufe0f',
        'color': '#0ea5e9',
        'role': 'Pashinyan office, Civil Contract, MFA, National Assembly',
        'description': (
            'Pashinyan (third term, Jun 2026), Civil Contract majority (64 of '
            '105 -- short of the two-thirds needed to call the constitutional '
            'referendum from parliament), MFA (Mirzoyan), National Assembly. '
            'Watch for: referendum scheduling language, treaty-signature '
            'signals, "Real Armenia" framing, EU-accession milestones, '
            'prosecution of opposition figures.'
        ),
        'keywords': [
            'pashinyan', 'nikol pashinyan', 'civil contract', 'armenian government',
            'armenian mfa', 'mirzoyan', 'ararat mirzoyan', 'national assembly armenia',
            'armenian parliament', 'yerevan government', 'armenian presidency',
            'real armenia', 'pashinyan referendum', 'pashinyan treaty',
            'pashinyan constitution', 'armenia constitutional amendment',
            'пашинян', 'гражданский договор', 'правительство армении',
            '\u0583\u0561\u0577\u056b\u0576\u0575\u0561\u0576',  # Pashinyan (hy)
        ],
    },
    'opposition_bloc': {
        'name': 'Opposition Bloc',
        'flag': '\u2694\ufe0f',
        'icon': '\U0001f5f3\ufe0f',
        'color': '#f97316',
        'role': 'Karapetyan Strong Armenia, Kocharyan alliance, Tsarukyan, Dashnaks',
        'description': (
            'The pro-Russian parliamentary opposition after Jun 2026: Strong '
            'Armenia (Karapetyan, 23.3 percent), Armenia Alliance (Kocharyan), '
            'Prosperous Armenia (Tsarukyan), plus Dashnaktsutyun street '
            'presence. Watch for: "resistance" language, referendum-blocking '
            'posture, street mobilization calls, Moscow-alignment framing, '
            'contestation of the election result.'
        ),
        'keywords': [
            'karapetyan', 'samvel karapetyan', 'strong armenia', 'mother armenia',
            'kocharyan', 'robert kocharyan', 'armenia alliance', 'tsarukyan',
            'prosperous armenia', 'dashnak', 'dashnaktsutyun', 'arf armenia',
            'armenian opposition', 'opposition armenia protest',
            'political resistance armenia', 'contest election armenia',
            'кочарян', 'карапетян', 'армянская оппозиция', 'дашнакцутюн',
        ],
    },
    'church_state_axis': {
        'name': 'Church-State Axis',
        'flag': '\u26ea',
        'icon': '\U0001f54a\ufe0f',
        'color': '#a855f7',
        'role': 'Etchmiadzin, Catholicos Karekin II, politically active clergy',
        'description': (
            'The Armenian Apostolic Church as a political actor: Catholicos '
            'Karekin II, Etchmiadzin, archbishops with movement followings '
            '(Bagrat Galstanyan class), clergy arrests and coup-plot '
            'reporting. The church is a named channel in documented Russian '
            'influence work -- coverage tempo here is a meddling-adjacent '
            'sensor. Sensor, not referee.'
        ),
        'keywords': [
            'karekin', 'catholicos', 'etchmiadzin', 'echmiadzin',
            'armenian apostolic church', 'armenian church protest',
            'bagrat galstanyan', 'archbishop armenia', 'clergy arrested armenia',
            'church state conflict armenia', 'holy see armenia pashinyan',
            'католикос', 'эчмиадзин', 'армянская церковь',
        ],
    },
    'azerbaijan_counterparty': {
        'name': 'Azerbaijan (Treaty Counterparty)',
        'flag': '\U0001f1e6\U0001f1ff',
        'icon': '\U0001f91d',
        'color': '#22c55e',
        'role': 'Aliyev treaty-language vs threat-language, DISPLAY-ONLY card',
        'description': (
            'Baku as the peace counterparty: Aliyev treaty language ("learning '
            'to live in peace"), confidence-building steps (fuel shipments, '
            'transit, prisoner releases) versus any revival of corridor-by-'
            'force framing. DISPLAY-ONLY: this card carries zero weight in the '
            'Armenia theatre score -- Azerbaijan is scored by its own tracker, '
            'and the dyad read arrives via its cross-theater fingerprint.'
        ),
        'keywords': [
            'aliyev armenia', 'aliyev peace', 'azerbaijan armenia treaty',
            'baku yerevan', 'aliyev corridor', 'azerbaijan peace agreement',
            'aliyev pashinyan', 'azerbaijan transit armenia', 'baku fuel armenia',
            'azerbaijan prisoners armenia', 'aliyev zangezur',
            'алиев армения', 'баку ереван',
        ],
    },
    'russia_inbound': {
        'name': 'Russia (Inbound Pressure)',
        'flag': '\U0001f1f7\U0001f1fa',
        'icon': '\U0001f43b',
        'color': '#ef4444',
        'role': 'Kremlin statements on Armenia, interference reporting, levers',
        'description': (
            'Moscow toward Yerevan: Kremlin/MFA statements on Armenia, '
            'documented interference reporting (Kiriyenko portfolio, disinfo, '
            'imported voters), and the hard-lever inventory -- 102nd base '
            'Gyumri, FSB border guards, Russian Railways operating the '
            'network, Gazprom Armenia, Rosatom/Metsamor fuel. Reporting tempo '
            'is measured both directions; the sensor never adjudicates.'
        ),
        'keywords': [
            'russia armenia', 'kremlin armenia', 'lavrov armenia', 'peskov armenia',
            'kiriyenko armenia', 'russian interference armenia', 'moscow yerevan',
            'gyumri base', '102nd base', 'russian border guards armenia',
            'russian railways armenia', 'gazprom armenia', 'metsamor', 'rosatom armenia',
            'csto armenia', 'russia armenia relations',
            'россия армения', 'кремль армения', 'одкб армения', 'база в гюмри',
        ],
    },
    'iran_inbound': {
        'name': 'Iran (Conditional Buffer)',
        'flag': '\U0001f1ee\U0001f1f7',
        'icon': '\u2696\ufe0f',
        'color': '#eab308',
        'role': 'Tehran statements on Armenia, corridor redlines, cooperation',
        'description': (
            'Iran backed Armenia for years because Armenia blocked the pan-'
            'Turkic land bridge. TRIPP breaks that logic: a US consortium on '
            'the Iranian border, transit that bypasses both Russia and Iran. '
            'The slice is a CONDITIONAL BUFFER -- Iranian rhetoric intensity '
            'on Zangezur/TRIPP is itself the flip-meter from buffer toward '
            'friction. Cooperation channels: gas-for-electricity swap, '
            'North-South corridor, Meghri FTZ.'
        ),
        'keywords': [
            'iran armenia', 'tehran yerevan', 'iran zangezur', 'irgc armenia',
            'iran corridor armenia', 'iran trump route', 'araghchi armenia',
            'iran armenia gas', 'iran armenia trade', 'meghri', 'aras exercise',
            'iran red line corridor', 'iran syunik',
            'иран армения', 'тегеран ереван',
        ],
    },
    'turkey_normalization': {
        'name': 'Turkiye Normalization Track',
        'flag': '\U0001f1f9\U0001f1f7',
        'icon': '\U0001f54a\ufe0f',
        'color': '#38bdf8',
        'role': 'Border opening, visa steps, flights, Kars rail -- treaty-chained',
        'description': (
            'Normalization is explicitly chained to the Azerbaijan treaty: '
            'visa facilitation live since Jan 1 2026, Turkish Airlines Yerevan '
            'routes, Kars-Dilucu rail under construction to meet TRIPP. Border '
            'opening would be Armenia\'s biggest economic event since '
            'independence and a Russia-leverage reducer. Feeds the '
            'spoke:turkey:armenia relationship polarity.'
        ),
        'keywords': [
            'turkey armenia', 'armenia turkey normalization', 'ankara yerevan',
            'turkey armenia border', 'margara', 'alican', 'kars gyumri',
            'kars dilucu', 'turkish airlines yerevan', 'erdogan armenia',
            'fidan armenia', 'turkey armenia visa', 'special envoy armenia turkey',
            'турция армения', 'анкара ереван',
        ],
    },
    'us_eu_anchor': {
        'name': 'US / EU Anchor',
        'flag': '\U0001f1fa\U0001f1f8',
        'icon': '\u2693',
        'color': '#93c5fd',
        'role': 'TRIPP/TIF milestones, EU accession, EUMA, strategic partnership',
        'description': (
            'The western anchor: TRIPP Development Company milestones (74/26, '
            'Jan 2026 framework), US strategic partnership follow-through, EU '
            'accession process stages, EUMA monitoring mission, visa '
            'liberalization track. Progress here is the drift axis\'s hard '
            'evidence.'
        ),
        'keywords': [
            'tripp', 'trump route', 'tripp development company', 'us armenia',
            'state department armenia', 'us armenia strategic partnership',
            'eu armenia', 'eu accession armenia', 'eu membership armenia',
            'euma', 'eu monitoring mission armenia', 'visa liberalization armenia',
            'brussels yerevan', 'washington yerevan',
            'сша армения', 'ес армения',
        ],
    },
}


# ============================================================
# GDELT QUERIES (sourcelang codes VERIFIED against the live
# LOOKUP-LANGUAGES.TXT on Jul 12 2026: hye = Armenian, rus = Russian)
# ============================================================

GDELT_QUERIES = {
    'eng': [
        '"armenia" AND ("pashinyan" OR "yerevan")',
        '"armenia" AND ("peace treaty" OR "peace agreement" OR "referendum")',
        '"armenia" AND ("tripp" OR "trump route" OR "zangezur" OR "corridor")',
        '"armenia" AND ("russia" OR "kremlin" OR "csto" OR "gyumri")',
        '"armenia" AND ("iran" OR "tehran" OR "irgc")',
        '"armenia" AND ("turkey" OR "border opening" OR "normalization")',
        '"armenia" AND ("eu" OR "european union" OR "accession")',
        '"armenia" AND ("opposition" OR "protest" OR "church")',
    ],
    'hye': [
        '"\u0570\u0561\u0575\u0561\u057d\u057f\u0561\u0576"',
        '"\u0583\u0561\u0577\u056b\u0576\u0575\u0561\u0576" OR "\u0566\u0561\u0576\u0563\u0565\u0566\u0578\u0582\u0580"',
    ],
    'rus': [
        '"\u0430\u0440\u043c\u0435\u043d\u0438\u044f" AND ("\u043f\u0430\u0448\u0438\u043d\u044f\u043d" OR "\u0435\u0440\u0435\u0432\u0430\u043d")',
        '"\u0430\u0440\u043c\u0435\u043d\u0438\u044f" AND ("\u043a\u043e\u0440\u0438\u0434\u043e\u0440" OR "\u0440\u0435\u0444\u0435\u0440\u0435\u043d\u0434\u0443\u043c")',
    ],
}


# ============================================================
# TOPIC FILTER (Reddit gate)
# ============================================================

ARMENIA_TOPIC_KEYWORDS = [
    'armenia', 'armenian', 'yerevan', 'pashinyan', 'zangezur', 'syunik',
    'karabakh', 'nagorno', 'tripp', 'trump route', 'gyumri', 'etchmiadzin',
    'karapetyan', 'kocharyan', 'aliyev', 'caucasus',
    '\u0430\u0440\u043c\u0435\u043d\u0438\u044f', '\u0435\u0440\u0435\u0432\u0430\u043d',
    '\u0570\u0561\u0575\u0561\u057d\u057f\u0561\u0576',
]


# ============================================================
# RSS FEEDS (Badil precedent: per-feed soft-fail; verify in boot logs
# on first deploy and swap any dead URL)
# ============================================================

RSS_FEEDS = [
    {'url': 'https://oc-media.org/feed/',            'name': 'OC Media',        'weight': 0.90},
    {'url': 'https://eurasianet.org/rss',            'name': 'Eurasianet',      'weight': 0.90},
    {'url': 'https://evnreport.com/feed/',           'name': 'EVN Report',      'weight': 0.85},
    {'url': 'https://www.civilnet.am/en/feed/',      'name': 'CivilNet EN',     'weight': 0.85},
    {'url': 'https://armenpress.am/en/rss',          'name': 'Armenpress EN',   'weight': 0.80},
]


# ============================================================
# REDIS HELPERS (canonical pattern)
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
        print(f'[Armenia Rhetoric] Redis get error: {str(e)[:120]}')
    return None


def _redis_set(key, value):
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
        print(f'[Armenia Rhetoric] Redis set error: {str(e)[:120]}')
        return False


def _redis_lpush_trim(key, value, max_len=120):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        body = json.dumps(value, default=str)
        requests.post(
            f'{UPSTASH_REDIS_URL}/lpush/{key}',
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json={'value': body},
            timeout=10
        )
        requests.post(
            f'{UPSTASH_REDIS_URL}/ltrim/{key}/0/{max_len-1}',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=5
        )
        return True
    except Exception as e:
        print(f'[Armenia Rhetoric] Redis lpush error: {str(e)[:120]}')
        return False


def _acquire_scan_lock(ttl_sec=900):
    """Cross-worker atomic lock (SET NX EX) for the BACKGROUND loop only.
    Request-driven force scans are not gated -- the operator is the operator.
    Returns True if this worker owns the scan window."""
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return True   # no Redis: single-worker fallback behavior
    try:
        r = requests.post(
            UPSTASH_REDIS_URL,
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=['SET', SCAN_LOCK_KEY,
                  datetime.now(timezone.utc).isoformat(), 'NX', 'EX', ttl_sec],
            timeout=8
        )
        return (r.json() or {}).get('result') == 'OK'
    except Exception as e:
        print(f'[Armenia Rhetoric] Scan lock error (proceeding): {str(e)[:120]}')
        return True


# ============================================================
# FETCHERS (canonical pattern)
# ============================================================

def _parse_pub_date(pub_str):
    if not pub_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_str).isoformat()
    except Exception:
        return pub_str


def _fetch_rss(url, source_name, weight=0.85, max_items=20):
    out = []
    try:
        feed = feedparser.parse(url)
        for entry in (feed.entries or [])[:max_items]:
            out.append({
                'title':       entry.get('title', '')[:300],
                'description': (entry.get('summary') or entry.get('description') or '')[:600],
                'url':         entry.get('link', ''),
                'published':   _parse_pub_date(entry.get('published') or entry.get('updated')),
                'source':      source_name,
                'source_type': 'rss',
                'language':    'eng',
                'weight':      weight,
            })
    except Exception as e:
        print(f'[Armenia RSS] {source_name}: {str(e)[:120]}')
    return out


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    params = {
        'query':      query,
        'mode':       'artlist',
        'maxrecords': max_records,
        'format':     'json',
        'sort':       'datedesc',
        'timespan':   f'{days*24}h',
        'sourcelang': language,
    }
    try:
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=(5, 15))
        if resp.status_code == 429:
            print('[Armenia GDELT] Rate limited (429) -- backing off')
            return []
        if resp.status_code != 200:
            print(f'[Armenia GDELT] HTTP {resp.status_code}')
            return []
        out = []
        for a in (resp.json().get('articles') or []):
            out.append({
                'title':       (a.get('title') or '')[:300],
                'description': '',
                'url':         a.get('url', ''),
                'published':   a.get('seendate'),
                'source':      a.get('domain', 'gdelt'),
                'source_type': 'gdelt',
                'language':    language,
                'weight':      0.80,
            })
        return out
    except Exception as e:
        print(f'[Armenia GDELT] {str(e)[:120]}')
        return []


def _fetch_newsapi(query='armenia', max_records=40):
    if not NEWSAPI_KEY:
        return []
    params = {
        'q':        query,
        'pageSize': max_records,
        'language': 'en',
        'sortBy':   'publishedAt',
        'apiKey':   NEWSAPI_KEY,
    }
    try:
        r = requests.get(NEWSAPI_BASE_URL, params=params, timeout=10)
        if r.status_code != 200:
            print(f'[Armenia NewsAPI] HTTP {r.status_code}')
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
                'language':    'eng',
                'weight':      0.85,
            })
        return out
    except Exception as e:
        print(f'[Armenia NewsAPI] {str(e)[:120]}')
        return []


def _fetch_brave(query='armenia azerbaijan peace', max_records=20):
    if not BRAVE_API_KEY:
        return []
    headers = {
        'Accept': 'application/json',
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
                'language':    'eng',
                'weight':      0.75,
            })
        return out
    except Exception as e:
        print(f'[Armenia Brave] {str(e)[:120]}')
        return []


def _fetch_reddit():
    """Browser-like UA (the Ukraine v1.2 lesson: generic UAs get silently
    403'd by Reddit; every non-200 is logged so blocks are visible)."""
    out = []
    subs = ['armenia', 'geopolitics', 'europe', 'CredibleDefense']
    ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
          'AppleWebKit/537.36 (KHTML, like Gecko) '
          'Chrome/124.0.0.0 Safari/537.36')
    found_total = 0
    for sub in subs:
        try:
            url = f'https://www.reddit.com/r/{sub}/new.json?limit=25'
            r = requests.get(
                url,
                headers={'User-Agent': ua, 'Accept': 'application/json'},
                timeout=8
            )
            if r.status_code != 200:
                print(f'[Armenia Reddit] r/{sub}: HTTP {r.status_code}')
                continue
            sub_count = 0
            for child in (r.json().get('data', {}).get('children') or []):
                p = child.get('data', {})
                title = (p.get('title') or '').lower()
                if not any(kw in title for kw in ARMENIA_TOPIC_KEYWORDS):
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
                    'language':    'eng',
                    'score':       p.get('score', 0),
                    'comments':    p.get('num_comments', 0),
                    'weight':      0.65,
                })
                sub_count += 1
            found_total += sub_count
        except Exception as e:
            print(f'[Armenia Reddit] r/{sub}: {str(e)[:120]}')
        time.sleep(0.3)
    print(f'[Armenia Reddit] Total: {found_total} posts across {len(subs)} subreddits')
    return out


def _fetch_all_articles():
    articles = []
    for feed in RSS_FEEDS:
        articles.extend(_fetch_rss(feed['url'], feed['name'], feed['weight']))
    for lang, queries in GDELT_QUERIES.items():
        for q in queries:
            articles.extend(_fetch_gdelt(q, language=lang, days=7))
            time.sleep(0.5)
    if len(articles) < 30:
        articles.extend(_fetch_newsapi('armenia', max_records=40))
    if len(articles) < 15:
        articles.extend(_fetch_brave('armenia azerbaijan peace', max_records=20))
    seen, unique = set(), []
    for a in articles:
        u = a.get('url')
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    return unique


# ============================================================
# CLASSIFICATION (co-crediting clone -- the Ukraine v1.1 lesson)
# ============================================================

def _score_article_for_actor(article, actor_def):
    _url = (article.get('url') or article.get('link') or '').lower()
    text = ' '.join([
        (article.get('title') or '').lower(),
        (article.get('description') or '').lower(),
        (article.get('content') or '').lower(),
        _url.replace('-', ' ').replace('_', ' ').replace('/', ' '),
    ])
    if not text.strip():
        return 0
    matches = 0
    for kw in actor_def.get('keywords', []):
        if kw.lower() in text:
            matches += 1
    return matches


def _classify_articles(articles):
    """Multi-actor co-crediting: best-match actor gets PRIMARY credit
    (counts toward theatre score); any other actor matching >= 2 keywords
    gets a co-credit copy (visible on its card, excluded from score)."""
    CO_CREDIT_MIN = 2
    by_actor = {k: [] for k in ACTORS}
    for art in articles:
        scores = {}
        for actor_key, actor_def in ACTORS.items():
            s = _score_article_for_actor(art, actor_def)
            if s >= 1:
                scores[actor_key] = s
        if not scores:
            continue
        best_actor = max(scores, key=lambda k: scores[k])
        art_copy = dict(art)
        art_copy['actor_score'] = scores[best_actor]
        by_actor[best_actor].append(art_copy)
        for actor_key, s in scores.items():
            if actor_key != best_actor and s >= CO_CREDIT_MIN:
                cc = dict(art)
                cc['actor_score'] = s
                cc['co_credit'] = True
                by_actor[actor_key].append(cc)
    return by_actor


# ============================================================
# THEATRE SCORE + ALERT BANDS
# ============================================================

def _compute_theatre_score(by_actor, articles):
    """Armenia baseline +8: contested post-war implementation period --
    ambient pressure without a war floor. azerbaijan_counterparty carries
    weight 0.0 (display-only; the dyad is the Azerbaijan tracker's score)."""
    BASELINE = 8
    actor_weights = {
        'armenian_government':     0.85,
        'opposition_bloc':         0.90,
        'church_state_axis':       0.75,
        'azerbaijan_counterparty': 0.00,   # DISPLAY-ONLY, never scores
        'russia_inbound':          1.00,
        'iran_inbound':            0.90,
        'turkey_normalization':    0.70,
        'us_eu_anchor':            0.75,
    }
    score = BASELINE
    for actor_key, articles_list in by_actor.items():
        weight = actor_weights.get(actor_key, 0.7)
        actor_contribution = min(25, sum(
            a.get('weight', 0.7) for a in articles_list
            if not a.get('co_credit')) * weight)
        score += actor_contribution
    return max(0, min(100, int(score)))


def _alert_level_from_score(score):
    """No war floor: Armenia reads the standard four-band enum."""
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'elevated'
    else:
        return 'normal'


# ============================================================
# DYAD READ (read, never re-scan)
# ============================================================

def _read_azerbaijan_dyad():
    """Absence-honest read of crosstheater:azerbaijan:fingerprint.
    24h freshness gate. Never invents a dyad read from a cold key."""
    fp = _redis_get(AZ_FINGERPRINT_KEY)
    if not isinstance(fp, dict):
        return {'present': False, 'note': 'Azerbaijan fingerprint not present in Redis'}
    try:
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(fp['ts'])).total_seconds() / 3600.0
        if age_h > 24:
            return {'present': False,
                    'note': f'Azerbaijan fingerprint stale ({age_h:.0f}h old)'}
    except Exception:
        return {'present': False, 'note': 'Azerbaijan fingerprint missing timestamp'}
    return {
        'present':     True,
        'level':       fp.get('level', 0),
        'alert_level': fp.get('alert_level', 'unknown'),
        'node_class':  fp.get('node_class', ''),
        'ts':          fp.get('ts'),
        'note':        'Dyad read via Azerbaijan tracker fingerprint (never re-scanned here)',
    }


# ============================================================
# CANONICAL SPOKE EMISSIONS
# ============================================================

# Armenia alert enum -> canonical 0-5 level. No war floor: a contested
# post-war state at baseline reads L1 (ambient contest, not silence).
_SPOKE_LEVEL_BY_ALERT = {
    'normal':   1,
    'elevated': 2,
    'high':     3,
    'critical': 4,
}


def _write_canonical_spoke_fingerprint(result, fingerprints):
    """Emit crosstheater:armenia:fingerprint (hub-agnostic per-country
    schema). Consumed by the Russia wheel's _read_spoke_fingerprints (already
    deployed and listening -- this write is the rim's tenth spoke), the
    Europe BLUF, and future recompute narratives.

    SURFACE-ONLY: no polarity wired into any score. node_class documents the
    taxonomy tier; wiring polarity into scores is a wheel scoping decision.
    Harmonize the node_class string with Azerbaijan's emission if they
    differ (one-line change)."""
    alert = result.get('alert_level', 'normal')
    level = _SPOKE_LEVEL_BY_ALERT.get(alert, 1)
    dt = result.get('diplomatic_track') or {}
    fingerprint = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'armenia',
        'node_class':  'friction_drift',   # Russia-wheel taxonomy: Friction / drift-away tier
        'level':       level,
        'score':       result.get('theatre_score', 0),
        'alert_level': alert,

        # -- Diplomatic slice (Ukraine off-ramp schema, treaty edition) --
        'diplomatic': {
            'off_ramp_maturity':    result.get('de_escalation_maturity', 'none'),
            'green_lines_active':   (result.get('green_lines') or {}).get('active_count', 0),
            'contradiction_active': result.get('contradiction_active', False),
            'diplomatic_max_raw':   dt.get('score', 0),
        },

        # -- Armenia-specific slices (interpreter-supplied) --
        'westward_drift': fingerprints.get('westward_drift', {}),
        'tripp_corridor': fingerprints.get('tripp_corridor', {}),
        'iran_facing':    fingerprints.get('iran_facing', {}),
        'russia_pressure': fingerprints.get('russia_pressure', {}),
    }
    try:
        _redis_set(SPOKE_KEY_CANONICAL, fingerprint)
        print('[Armenia Rhetoric] Canonical spoke fingerprint written '
              '(crosstheater:armenia:fingerprint) -- the rim gains its tenth spoke')
    except Exception as e:
        print(f'[Armenia Rhetoric] Canonical fingerprint write failed: {e}')


def _write_turkey_spoke(fingerprints):
    """Emit spoke:turkey:armenia for the Turkey wheel's GPI recompute.
    Schema from the reader: level / relationship / top_signal. The
    relationship polarity is DYNAMIC (friction baseline, alignment when the
    normalization vector warms) -- the read lives in the polarity."""
    ts = fingerprints.get('turkey_spoke') or {}
    if not ts:
        return
    payload = {
        'ts':           datetime.now(timezone.utc).isoformat(),
        'country':      'armenia',
        'level':        ts.get('level', 0),
        'relationship': ts.get('relationship', 'friction'),
        'top_signal':   ts.get('top_signal', ''),
    }
    try:
        _redis_set(SPOKE_KEY_TURKEY, payload)
        print(f"[Armenia Rhetoric] Turkey spoke written (spoke:turkey:armenia, "
              f"relationship={payload['relationship']})")
    except Exception as e:
        print(f'[Armenia Rhetoric] Turkey spoke write failed: {e}')


# ============================================================
# MAIN SCAN
# ============================================================

def run_armenia_rhetoric_scan(force=False):
    if not force:
        cached = _redis_get(REDIS_KEY_LATEST)
        if cached and cached.get('cached_at'):
            try:
                cached_at = datetime.fromisoformat(cached['cached_at'])
                age = (datetime.now(timezone.utc) - cached_at).total_seconds()
                if age < REFRESH_INTERVAL_SEC:
                    cached['cache_status'] = 'hit'
                    return cached
            except Exception:
                pass

    print('[Armenia Rhetoric] Starting fresh scan...')
    started = time.time()

    articles = _fetch_all_articles()
    print(f'[Armenia Rhetoric] Articles: {len(articles)}')

    reddit_signals = _fetch_reddit()

    by_actor = _classify_articles(articles)
    actor_summaries = {}
    for actor_key, actor_articles in by_actor.items():
        actor_def = ACTORS[actor_key]
        actor_summaries[actor_key] = {
            'name':          actor_def['name'],
            'flag':          actor_def['flag'],
            'icon':          actor_def['icon'],
            'color':         actor_def['color'],
            'role':          actor_def['role'],
            'description':   actor_def['description'],
            'article_count': len(actor_articles),
            'top_articles':  actor_articles[:5],
            'display_only':  actor_key == 'azerbaijan_counterparty',
        }

    score = _compute_theatre_score(by_actor, articles)
    alert = _alert_level_from_score(score)

    articles_en = [a for a in articles if a.get('language', 'eng') in ('eng', None)]
    articles_hy = [a for a in articles if a.get('language') == 'hye']
    articles_ru = [a for a in articles if a.get('language') == 'rus']

    scan_data = {
        'articles_en':    articles_en,
        'articles_hy':    articles_hy,
        'articles_ru':    articles_ru,
        'reddit_signals': reddit_signals,
        'by_actor':       by_actor,
        'actor_summaries': actor_summaries,
        'theatre_score':  score,
        'alert_level':    alert,
    }

    interpretation = interpret_signals(scan_data)

    # -- Constitutional-crisis band floor (port of the Ukraine strategic-
    #    strike floor, Jun 18 2026 pattern). theatre_score is pure article
    #    volume, so a BREACHED Treaty Collapse or Constitutional Crisis red
    #    line can sit at 'normal' on volume alone -- which buries it in the
    #    GPI rollup. Floor the band so a genuine breach reads at least
    #    'high' ('critical' when two or more stack). Floors only, never
    #    lowers. Convergence-safe: re-bands an already-breached red line,
    #    invents no signal.
    _rl_triggered = (interpretation.get('red_lines') or {}).get('triggered') or []
    _structural_breaches = sum(
        1 for _rl in _rl_triggered
        if _rl.get('status') == 'BREACHED'
        and _rl.get('id') in ('treaty_collapse', 'constitutional_crisis',
                              'corridor_by_force')
    )
    _BAND_RANK = {'normal': 0, 'elevated': 1, 'high': 2, 'critical': 3}
    if _structural_breaches >= 2:
        score = max(score, 70)
        if _BAND_RANK['critical'] > _BAND_RANK.get(alert, 0):
            alert = 'critical'
    elif _structural_breaches >= 1:
        score = max(score, 55)
        if _BAND_RANK['high'] > _BAND_RANK.get(alert, 0):
            alert = 'high'
    if _structural_breaches >= 1:
        print(f'[Armenia Rhetoric] Structural-breach floor applied: '
              f'{_structural_breaches} breach(es) -> band {alert}, score {score}')

    # -- Off-ramp maturity (Ukraine Slice-4 schema, treaty edition) so the
    #    conflict-repricing detector and the GPI read Armenia the same way
    #    they read Iran and Ukraine. Convergence framing: reports that a
    #    treaty track is present and how mature -- never predicts signature.
    _dt = interpretation.get('diplomatic_track') or {}
    _scenario = _dt.get('scenario', 'No Active Track')
    _MATURITY_BY_SCENARIO = {
        'No Active Track':             'none',
        'Track Contested':             'none',
        'Tentative Treaty Signals':    'framework',
        'Active Treaty Track':         'framework',
        'Signature Window Conditions': 'signed',
    }
    _offramp_maturity = _MATURITY_BY_SCENARIO.get(_scenario, 'none')
    _negator_hits = _dt.get('negator_hits', 0)
    _contradiction_flags = []
    if _offramp_maturity != 'none':
        if _structural_breaches >= 1:
            _contradiction_flags.append('structural_breach_during_track')
        if _negator_hits >= 1:
            _contradiction_flags.append('treaty_rejected_language')
    _contradiction_active = bool(_contradiction_flags)

    dyad_read = _read_azerbaijan_dyad()

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'armenia',
        'flag':              '\U0001f1e6\U0001f1f2',
        'display_name':      'Armenia',
        'theatre_score':     score,
        'alert_level':       alert,
        'pressure_score':    score,
        'tracker_version':   '1.0.0',
        'cached_at':         datetime.now(timezone.utc).isoformat(),
        'scan_duration_sec': elapsed,
        'cache_status':      'fresh',
        'total_articles':    len(articles),
        'articles_by_source': {
            'rss':     sum(1 for a in articles if a.get('source_type') == 'rss'),
            'gdelt':   sum(1 for a in articles if a.get('source_type') == 'gdelt'),
            'newsapi': sum(1 for a in articles if a.get('source_type') == 'newsapi'),
            'brave':   sum(1 for a in articles if a.get('source_type') == 'brave'),
        },
        'reddit_count':      len(reddit_signals),
        'articles_en':       articles_en,
        'articles_hy':       articles_hy,
        'articles_ru':       articles_ru,
        'actor_summaries':   actor_summaries,
        'so_what':           interpretation.get('so_what'),
        'top_signals':       interpretation.get('top_signals') or [],
        'red_lines':         interpretation.get('red_lines'),
        'green_lines':       interpretation.get('green_lines'),
        'diplomatic_track':  interpretation.get('diplomatic_track'),
        # -- Armenia vector payloads --
        'tripp_corridor':       interpretation.get('tripp_corridor'),
        'russia_pressure':      interpretation.get('russia_pressure'),
        'westward_drift':       interpretation.get('westward_drift'),
        'iran_buffer':          interpretation.get('iran_buffer'),
        'turkey_normalization': interpretation.get('turkey_normalization'),
        'referendum_clock':     interpretation.get('referendum_clock'),
        'rumint':               interpretation.get('rumint'),
        'dyad_read':            dyad_read,
        # -- Off-ramp fingerprint (Iran/Ukraine schema) --
        'de_escalation_maturity': _offramp_maturity,
        'contradiction_active':   _contradiction_active,
        'contradiction_flags':    _contradiction_flags,
        'diplomatic_max_raw':     _dt.get('score', 0),
        'cross_theater_fingerprints': interpretation.get('cross_theater_fingerprints'),
        'composite_modifier':  interpretation.get('composite_modifier', 0),
        'interpreter_version': interpretation.get('interpreter_version'),
        'disclaimer':          interpretation.get('disclaimer'),
    }

    _redis_set(REDIS_KEY_LATEST, result)
    fps = interpretation.get('cross_theater_fingerprints') or {}
    _write_canonical_spoke_fingerprint(result, fps)   # Russia wheel: tenth spoke
    _write_turkey_spoke(fps)                          # Turkey wheel: periphery join
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Armenia Rhetoric] Scan complete: score={score}, alert={alert}, '
          f'articles={len(articles)}, elapsed={elapsed}s')
    return result


# ============================================================
# BACKGROUND REFRESH (cross-worker Redis lock: only the lock-owning
# worker scans; the other sleeps and retries next cycle)
# ============================================================

def _background_refresh():
    time.sleep(150)
    while True:
        try:
            if _acquire_scan_lock(ttl_sec=900):
                with _scan_lock:
                    run_armenia_rhetoric_scan(force=True)
            else:
                print('[Armenia Rhetoric] Another worker owns the scan window -- skipping')
        except Exception as e:
            print(f'[Armenia Rhetoric] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Armenia Rhetoric] Background refresh thread started (6h cycle, cross-worker lock)')


# ============================================================
# ENDPOINT REGISTRATION
# ============================================================

def register_armenia_rhetoric_endpoints(app):
    @app.route('/api/rhetoric/armenia', methods=['GET'])
    def api_rhetoric_armenia():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            data = run_armenia_rhetoric_scan(force=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error':   str(e)[:200],
                'theatre': 'armenia',
            }), 500

    @app.route('/api/rhetoric/armenia/summary', methods=['GET'])
    def api_rhetoric_armenia_summary():
        try:
            d = run_armenia_rhetoric_scan(force=False)
            return jsonify({
                'theatre':          'armenia',
                'flag':             '\U0001f1e6\U0001f1f2',
                'display_name':     'Armenia',
                'theatre_score':    d.get('theatre_score', 0),
                'alert_level':      d.get('alert_level', 'normal'),
                'top_signals':      (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'cached_at':        d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/armenia/history', methods=['GET'])
    def api_rhetoric_armenia_history():
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
                'theatre': 'armenia',
                'count':   len(history),
                'history': history,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500

    print('[Armenia Rhetoric] Endpoints registered: /api/rhetoric/armenia, /summary, /history')
