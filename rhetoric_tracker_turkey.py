"""
=======================================================================
  ASIFAH ANALYTICS -- TURKEY RHETORIC TRACKER
  v1.0.0 (Jun 11 2026)
=======================================================================

The platform's first SWING-STATE tracker. Multi-actor rhetoric tracker
for Turkey, aggregating signals across:
  - RSS: Turkish state-adjacent press AS ACTOR SOURCES (Daily Sabah,
    Hurriyet DN, TRT World, Anadolu), opposition (Duvar English), and
    inbound/analyst layer (JPost, Times of Israel, Al-Monitor, MEE)
  - GDELT multi-language queries (English + Turkish + Russian)
  - NewsAPI fallback, Brave Search tertiary fallback
  - Telegram (Turkey subset of Europe channels -- ClashReport is
    Turkish-origin OSINT, already in the roster)
  - Bluesky (generic per-target fetch; handles tagged 'turkey' or '*')
  - Reddit (/r/Turkey, /r/lebanon, /r/syriancivilwar, /r/Israel,
    /r/geopolitics) -- the Lebanon vector surfaces in r/lebanon before
    it makes wire copy

Calls turkey_signal_interpreter.interpret_signals() for the analytical
layer: dual alignment indices (NATO-anchor vs strategic-autonomy),
Lebanon-vector playbook ladder, mirror-imaging friction index,
constitutional-clock multiplier.

Writes Redis cache key 'rhetoric:turkey:latest'.
Writes cross-theater fingerprints fingerprint:turkey:* (shared Redis,
read by Lebanon / Israel / Syria trackers on the ME backend + both
ME and Europe regional BLUFs -- Hungary dual-theater precedent).

ACTOR FRAMEWORK (7 actors):
  - turkish_presidency           (Erdogan, palace, comms directorate)
  - turkish_mfa_defense          (Fidan/MFA + MSB/TSK)
  - turkish_state_media          (TRT/Anadolu/Sabah -- the actor's voice)
  - turkish_opposition           (CHP/Imamoglu, domestic pressure)
  - israel_on_turkey             (INBOUND -- mirror-imaging input)
  - nato_western_track           (Alliance cooperation signals)
  - east_alignment_track         (Russia/Iran/SCO coordination signals)

ENDPOINTS:
  GET /api/rhetoric/turkey
  GET /api/rhetoric/turkey/summary
  GET /api/rhetoric/turkey/history
=======================================================================
"""

import os
import json
import time
import threading
import requests
import feedparser
from datetime import datetime, timezone
from flask import jsonify, request

try:
    from telegram_signals_europe import fetch_turkey_telegram_signals
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print('[Turkey Rhetoric] Telegram signals not available')

try:
    from bluesky_signals_europe import fetch_bluesky_for_target
    BLUESKY_AVAILABLE = True
except ImportError:
    BLUESKY_AVAILABLE = False
    print('[Turkey Rhetoric] Bluesky signals not available')

from turkey_signal_interpreter import interpret_signals

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

REDIS_KEY_LATEST     = 'rhetoric:turkey:latest'
REDIS_KEY_HISTORY    = 'rhetoric:turkey:history'
REFRESH_INTERVAL_SEC = 6 * 3600

_scan_lock = threading.Lock()

# ============================================================
# RSS FEEDS
# Verify on first deploy via articles_by_source counts (the Badil
# lesson): any feed returning zero gets its URL researched, not trusted.
# ============================================================

RSS_FEEDS = [
    # -- Turkish state-adjacent press: ACTOR SOURCES, not just coverage --
    {'name': 'Daily Sabah',            'url': 'https://www.dailysabah.com/rss/homepage',                 'weight': 0.90},
    {'name': 'Hurriyet Daily News',    'url': 'https://www.hurriyetdailynews.com/rss',                   'weight': 0.85},
    {'name': 'TRT World',              'url': 'https://www.trtworld.com/rss',                            'weight': 0.85},
    {'name': 'Anadolu Agency',         'url': 'https://www.aa.com.tr/en/rss/default?cat=guncel',         'weight': 0.90},
    # -- Turkish opposition / independent --
    {'name': 'Duvar English',          'url': 'https://www.duvarenglish.com/rss',                        'weight': 0.80},
    # -- Inbound (Israeli) + analyst layer --
    {'name': 'Jerusalem Post ME',      'url': 'https://www.jpost.com/rss/rssfeedsmiddleeastnews.aspx',   'weight': 0.85},
    {'name': 'Times of Israel',        'url': 'https://www.timesofisrael.com/feed/',                     'weight': 0.85},
    {'name': 'Al-Monitor',             'url': 'https://www.al-monitor.com/rss',                          'weight': 0.90},
    {'name': 'Middle East Eye',        'url': 'https://www.middleeasteye.net/rss',                       'weight': 0.75},
]

# ============================================================
# ACTORS
# ============================================================

ACTORS = {
    'turkish_presidency': {
        'name': 'Turkish Presidency',
        'flag': '\U0001f1f9\U0001f1f7',
        'icon': '\U0001f3db\ufe0f',
        'color': '#e11d48',
        'role': 'Erdogan, Presidential Palace, Communications Directorate',
        'description': (
            'Erdogan statements, palace communiques, Altun/Communications '
            'Directorate framing, Kalin-successor NSC voice. Watch for: '
            'threat-perimeter extension ("threatens Turkey too"), '
            'Ottoman-heritage framing, protector-of-Sunnis/Jerusalem '
            'language, constitutional-clock signals, jawboning of CBRT.'
        ),
        'keywords': [
            'erdogan', 'recep tayyip erdogan', 'turkish president',
            'turkish presidency', 'presidential palace ankara',
            'erdogan says', 'erdogan warns', 'erdogan statement',
            'erdogan speech', 'fahrettin altun', 'communications directorate',
            'erdogan announces', 'erdogan threatens', 'erdogan vows',
            # threat-perimeter / Levant framing
            'threaten turkey too', 'threatens turkey too',
            'erdogan israel', 'erdogan lebanon', 'erdogan syria',
            'erdogan jerusalem', 'erdogan muslim world', 'erdogan ummah',
            # domestic clock
            'erdogan constitution', 'erdogan 2028', 'erdogan re-election',
            # Turkish-language
            'cumhurbaskani erdogan', 'erdogan aciklama',
        ],
    },
    'turkish_mfa_defense': {
        'name': 'Turkish MFA & Defense',
        'flag': '\U0001f1f9\U0001f1f7',
        'icon': '\u2694\ufe0f',
        'color': '#b91c1c',
        'role': 'Fidan/MFA, MSB (Defense Ministry), TSK General Staff',
        'description': (
            'Hakan Fidan MFA statements, MSB/Guler defense communiques, '
            'TSK operational language. Watch for: "buffer zone"/"safe '
            'zone" framing (the signature pre-operation tell), operation '
            'naming patterns, SDF ultimatums, deconfliction language re '
            'Israel in Syria, Montreux/straits signaling.'
        ),
        'keywords': [
            'hakan fidan', 'turkish foreign minister', 'turkish mfa',
            'turkey foreign ministry', 'yasar guler', 'turkish defense minister',
            'turkish defense ministry', 'msb', 'turkish armed forces',
            'tsk', 'turkish general staff', 'turkish military',
            'turkish operation', 'turkish forces', 'turkish troops',
            'buffer zone', 'safe zone', 'guvenli bolge', 'tampon bolge',
            'turkey montreux', 'turkish straits', 'bosphorus transit',
            'turkey deconfliction', 'fidan says', 'fidan warns',
            'disisleri bakanligi', 'milli savunma bakanligi',
        ],
    },
    'turkish_state_media': {
        'name': 'Turkish State Media',
        'flag': '\U0001f4fa',
        'icon': '\U0001f4e1',
        'color': '#f97316',
        'role': 'TRT, Anadolu Agency, Daily Sabah editorial line',
        'description': (
            'State-adjacent editorial framing -- the regime voice between '
            'official statements. Watch for: escalation-language drift, '
            'narrative pivots (solidarity -> deterrence -> inevitability), '
            'anti-Israel campaign intensity, neo-Ottoman heritage content, '
            'synchronized framing with Iranian/Russian state media.'
        ),
        'keywords': [
            'trt world', 'anadolu agency', 'daily sabah', 'sabah editorial',
            'turkish state media', 'trt report', 'anadolu reports',
            'aksam', 'yeni safak', 'star gazetesi', 'turkish press',
            'turkish media campaign', 'sabah column',
        ],
    },
    'turkish_opposition': {
        'name': 'Turkish Opposition & Domestic',
        'flag': '\U0001f5f3\ufe0f',
        'icon': '\u2696\ufe0f',
        'color': '#0ea5e9',
        'role': 'CHP, Imamoglu case, protest movements, lira/economy stress',
        'description': (
            'CHP leadership, Imamoglu legal saga, DEM/Kurdish politics, '
            'street mobilization, lira and CBRT stress. Watch for: mass '
            'protest waves, opposition leadership arrests, early-election '
            'maneuvering, capital-flight signals. Domestic pressure '
            'transmits to foreign-policy risk appetite in both directions.'
        ),
        'keywords': [
            'imamoglu', 'ekrem imamoglu', 'chp', 'republican peoples party',
            'ozgur ozel', 'turkish opposition', 'istanbul mayor',
            'turkey protests', 'protests istanbul', 'protests ankara',
            'turkish lira', 'lira crisis', 'cbrt', 'turkish central bank',
            'turkey inflation', 'dem party', 'turkey early elections',
            'turkey snap election', 'turkish election', 'turkey detains',
            'turkey arrests opposition', 'turkish journalists arrested',
        ],
    },
    'israel_on_turkey': {
        'name': 'Israel on Turkey (Inbound)',
        'flag': '\U0001f1ee\U0001f1f1',
        'icon': '\U0001f50d',
        'color': '#3b82f6',
        'role': 'Israeli government/military/analyst claims about Turkey',
        'description': (
            'INBOUND vector -- the mirror-imaging input. Israeli official '
            'statements, IDF assessments, and Israeli-press analysis '
            'framing Turkey as expansionist threat ("Turkish takeover of '
            'Lebanon," neo-Ottoman warnings, Hamas-hosting accusations). '
            'Tracked with attribution, scored against Turkey-claims-'
            'Israel for the friction index. Both directions read; the '
            'reader completes the inference.'
        ),
        'keywords': [
            'israel warns turkey', 'israel turkey threat', 'israeli officials turkey',
            'netanyahu turkey', 'netanyahu erdogan', 'idf turkey',
            'turkish takeover', 'turkey takeover lebanon', 'israel accuses turkey',
            'israel turkey lebanon', 'israel turkey syria', 'mossad turkey',
            'israeli intelligence turkey', 'turkey hamas israel',
            'israel neo-ottoman', 'katz turkey', 'israeli minister turkey',
            'jerusalem post turkey', 'israel concerned turkey',
        ],
    },
    'nato_western_track': {
        'name': 'NATO / Western Track',
        'flag': '\U0001f6e1\ufe0f',
        'icon': '\u2693',
        'color': '#10b981',
        'role': 'Alliance cooperation: NATO, US, EU defense relationship',
        'description': (
            'The NATO-anchor index feed: exercises, F-35/F-16 program '
            'movement, EU SAFE participation, Incirlik status, CAATSA '
            'relief talks, Sweden-accession-style bargains, Article 5 '
            'language. Volume here holds the anchor index up against '
            'autonomy drift.'
        ),
        'keywords': [
            'turkey nato', 'nato turkey', 'turkey f-35', 'turkey f-16',
            'incirlik', 'turkey us relations', 'turkey pentagon',
            'turkey eu defense', 'turkey safe program', 'caatsa turkey',
            'turkey nato exercise', 'turkey patriot', 'stoltenberg turkey',
            'rutte turkey', 'turkey washington', 'turkey state department',
            'turkey arms ukraine', 'bayraktar ukraine',
        ],
    },
    'east_alignment_track': {
        'name': 'East Alignment Track',
        'flag': '\U0001f9ed',
        'icon': '\U0001f0cf',
        'color': '#9333ea',
        'role': 'Russia/Iran/SCO-BRICS coordination signals',
        'description': (
            'The strategic-autonomy index feed: Putin-Erdogan channel, '
            'TurkStream/Akkuyu energy entanglement, S-400 file, Iran '
            'coordination, SCO/BRICS courtship, sanctions-defiance '
            'posture, Hamas hosting. Volume here against a falling '
            'NATO-track is the decoupling signal.'
        ),
        'keywords': [
            'erdogan putin', 'turkey russia', 'turkstream', 'akkuyu',
            'turkey rosatom', 's-400', 'turkey iran', 'ankara tehran',
            'turkey sco', 'turkey brics', 'turkey china', 'erdogan xi',
            'turkey sanctions defiance', 'turkey russia trade',
            'turkey russia gas', 'turkey hosts hamas', 'erdogan hamas',
            'turkey gazprom', 'putin ankara', 'lavrov turkey',
        ],
    },
}

# ============================================================
# GDELT QUERIES (multi-language)
# ============================================================

GDELT_QUERIES = [
    {'query': 'Turkey Erdogan',           'language': 'eng'},
    {'query': 'Turkey Lebanon influence', 'language': 'eng'},
    {'query': 'Turkey Israel',            'language': 'eng'},
    {'query': 'Turkey Syria operation',   'language': 'eng'},
    {'query': 'Turkey NATO',              'language': 'eng'},
    {'query': 'Erdogan Lubnan',           'language': 'tur'},
    {'query': 'Turkiye Suriye',           'language': 'tur'},
    {'query': 'Turtsiya Erdogan',         'language': 'rus'},
]

# Topic gate: NewsAPI/Brave noise filter -- an article must touch Turkey
TURKEY_TOPIC_KEYWORDS = [
    'turkey', 'turkish', 'turkiye', 'erdogan', 'ankara', 'istanbul',
    'bosphorus', 'incirlik', 'fidan', 'tsk', 'anatolia', 'anatolian',
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
            timeout=8
        )
        if r.status_code == 200:
            result = r.json().get('result')
            if result:
                return json.loads(result)
    except Exception as e:
        print(f'[Turkey Rhetoric] Redis GET error: {str(e)[:80]}')
    return None


def _redis_set(key, value):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(
            UPSTASH_REDIS_URL,
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            json=['SET', key, json.dumps(value)],
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f'[Turkey Rhetoric] Redis SET error: {str(e)[:80]}')
        return False


def _redis_lpush_trim(key, value, max_len=120):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        headers = {'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}
        requests.post(UPSTASH_REDIS_URL, headers=headers,
                      json=['LPUSH', key, json.dumps(value)], timeout=10)
        requests.post(UPSTASH_REDIS_URL, headers=headers,
                      json=['LTRIM', key, '0', str(max_len - 1)], timeout=10)
        return True
    except Exception as e:
        print(f'[Turkey Rhetoric] Redis LPUSH error: {str(e)[:80]}')
        return False


# ============================================================
# ARTICLE FETCHERS
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
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_items]:
            articles.append({
                'title':       entry.get('title', ''),
                'description': entry.get('summary', '')[:400],
                'url':         entry.get('link', ''),
                'source':      source_name,
                'source_type': 'rss',
                'weight':      weight,
                'language':    'eng',
                'published':   _parse_pub_date(entry.get('published')),
            })
    except Exception as e:
        print(f'[Turkey Rhetoric] RSS error ({source_name}): {str(e)[:80]}')
    return articles


# GDELT circuit breaker (canonical pattern): after the first failure,
# short-circuit all remaining GDELT queries for 10 minutes. Eight
# consecutive read-timeouts cost ~40s of scan time for zero articles.
_GDELT_BREAKER = {'tripped_at': 0.0}
_GDELT_BREAKER_COOLDOWN_SEC = 600


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    articles = []
    if time.time() - _GDELT_BREAKER['tripped_at'] < _GDELT_BREAKER_COOLDOWN_SEC:
        return articles  # breaker open -- skip silently
    try:
        params = {
            'query':         f'{query} sourcelang:{language}',
            'mode':          'artlist',
            'maxrecords':    max_records,
            'timespan':      f'{days}d',
            'format':        'json',
            'sort':          'datedesc',
        }
        r = requests.get(GDELT_BASE_URL, params=params, timeout=(5, 8))
        if r.status_code == 200:
            for item in (r.json().get('articles') or []):
                articles.append({
                    'title':       item.get('title', ''),
                    'description': '',
                    'url':         item.get('url', ''),
                    'source':      item.get('domain', 'GDELT'),
                    'source_type': 'gdelt',
                    'weight':      0.75,
                    'language':    language,
                    'published':   item.get('seendate'),
                })
    except Exception as e:
        _GDELT_BREAKER['tripped_at'] = time.time()
        print(f'[Turkey Rhetoric] GDELT error ({query}): {str(e)[:80]} '
              f'-- breaker OPEN, skipping remaining GDELT queries for 10 min')
    return articles


def _fetch_newsapi(query='turkey erdogan', max_records=40):
    if not NEWSAPI_KEY:
        return []
    articles = []
    try:
        params = {
            'q':        query,
            'language': 'en',
            'sortBy':   'publishedAt',
            'pageSize': max_records,
            'apiKey':   NEWSAPI_KEY,
        }
        r = requests.get(NEWSAPI_BASE_URL, params=params, timeout=12)
        if r.status_code == 200:
            for item in (r.json().get('articles') or []):
                title = (item.get('title') or '').lower()
                desc = (item.get('description') or '').lower()
                if not any(kw in title or kw in desc for kw in TURKEY_TOPIC_KEYWORDS):
                    continue
                articles.append({
                    'title':       item.get('title', ''),
                    'description': (item.get('description') or '')[:400],
                    'url':         item.get('url', ''),
                    'source':      (item.get('source') or {}).get('name', 'NewsAPI'),
                    'source_type': 'newsapi',
                    'weight':      0.80,
                    'language':    'eng',
                    'published':   item.get('publishedAt'),
                })
    except Exception as e:
        print(f'[Turkey Rhetoric] NewsAPI error: {str(e)[:80]}')
    return articles


def _fetch_brave(query='turkey erdogan lebanon israel', max_records=20):
    if not BRAVE_API_KEY:
        return []
    articles = []
    try:
        r = requests.get(
            BRAVE_BASE_URL,
            headers={'X-Subscription-Token': BRAVE_API_KEY, 'Accept': 'application/json'},
            params={'q': query, 'count': max_records},
            timeout=12
        )
        if r.status_code == 200:
            for item in (r.json().get('results') or []):
                title = (item.get('title') or '').lower()
                desc = (item.get('description') or '').lower()
                if not any(kw in title or kw in desc for kw in TURKEY_TOPIC_KEYWORDS):
                    continue
                articles.append({
                    'title':       item.get('title', ''),
                    'description': (item.get('description') or '')[:400],
                    'url':         item.get('url', ''),
                    'source':      (item.get('meta_url') or {}).get('hostname', 'Brave'),
                    'source_type': 'brave',
                    'weight':      0.70,
                    'language':    'eng',
                    'published':   item.get('age'),
                })
    except Exception as e:
        print(f'[Turkey Rhetoric] Brave error: {str(e)[:80]}')
    return articles


def _fetch_reddit():
    """Reddit signals. The Lebanon vector surfaces in r/lebanon before
    it makes wire copy (the RUMINT lesson: r/forbiddenbromance surfaced
    the South Lebanon economic zone six months early)."""
    # r/Turkey is the HOME sub: posts there are about Turkey by
    # definition and rarely say "turkey" in the title -- exempt from the
    # topic gate. Cross-subs (r/lebanon etc.) keep the keyword filter.
    subs = [('Turkey', False), ('lebanon', True), ('syriancivilwar', True),
            ('Israel', True), ('geopolitics', True)]
    signals = []
    headers = {'User-Agent': 'AsifahAnalytics/1.0'}
    for sub, gate in subs:
        try:
            r = requests.get(
                f'https://www.reddit.com/r/{sub}/hot.json?limit=20',
                headers=headers, timeout=10
            )
            if r.status_code != 200:
                print(f'[Turkey Rhetoric] Reddit r/{sub} HTTP {r.status_code}')
                continue
            for child in (r.json().get('data', {}).get('children') or []):
                post = child.get('data', {})
                title = (post.get('title') or '').lower()
                if gate and not any(kw in title for kw in TURKEY_TOPIC_KEYWORDS):
                    continue
                signals.append({
                    'title':     post.get('title', ''),
                    'text':      post.get('title', ''),
                    'url':       f"https://reddit.com{post.get('permalink', '')}",
                    'source':    f'r/{sub}',
                    'score':     post.get('score', 0),
                    'created':   post.get('created_utc'),
                })
        except Exception as e:
            print(f'[Turkey Rhetoric] Reddit error (r/{sub}): {str(e)[:80]}')
    return signals


def _fetch_all_articles():
    articles = []
    for feed in RSS_FEEDS:
        articles.extend(_fetch_rss(feed['url'], feed['name'], feed['weight']))
    for gq in GDELT_QUERIES:
        articles.extend(_fetch_gdelt(gq['query'], gq['language']))
    articles.extend(_fetch_newsapi())
    articles.extend(_fetch_brave())

    # De-duplicate by URL
    seen, unique = set(), []
    for a in articles:
        url = a.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(a)
    return unique


# ============================================================
# CLASSIFICATION & SCORING
# ============================================================

def _score_article_for_actor(article, actor_def):
    text = ' '.join([
        (article.get('title') or '').lower(),
        (article.get('description') or '').lower(),
        (article.get('url') or '').lower().replace('-', ' ').replace('_', ' '),
    ])
    hits = sum(1 for kw in actor_def['keywords'] if kw.lower() in text)
    return hits


def _classify_articles(articles):
    by_actor = {key: [] for key in ACTORS}
    for article in articles:
        best_actor, best_hits = None, 0
        for actor_key, actor_def in ACTORS.items():
            hits = _score_article_for_actor(article, actor_def)
            if hits > best_hits:
                best_actor, best_hits = actor_key, hits
        if best_actor and best_hits > 0:
            by_actor[best_actor].append(article)
    for actor_key in by_actor:
        by_actor[actor_key].sort(
            key=lambda a: a.get('published') or '', reverse=True)
    return by_actor


def _compute_theatre_score(by_actor, articles):
    """Turkey baseline +8: a swing state under standing tension, not at
    war (Ukraine runs +12). The inbound and east-track actors weigh
    heaviest -- they are where the swing shows first."""
    BASELINE = 8
    actor_weights = {
        'turkish_presidency':    1.00,
        'turkish_mfa_defense':   1.05,
        'turkish_state_media':   0.70,
        'turkish_opposition':    0.75,
        'israel_on_turkey':      1.00,
        'nato_western_track':    0.80,
        'east_alignment_track':  0.95,
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
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'elevated'
    else:
        return 'normal'


def _write_cross_theater_fingerprints(fingerprints):
    for key, val in (fingerprints or {}).items():
        try:
            _redis_set(f'fingerprint:turkey:{key}', val)
        except Exception:
            pass


# ============================================================
# MAIN SCAN
# ============================================================

def run_turkey_rhetoric_scan(force=False):
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

    print('[Turkey Rhetoric] Starting fresh scan...')
    started = time.time()

    articles = _fetch_all_articles()
    print(f'[Turkey Rhetoric] Articles: {len(articles)}')

    telegram_messages = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_messages = fetch_turkey_telegram_signals() or []
            print(f'[Turkey Rhetoric] Telegram: {len(telegram_messages)} messages')
        except Exception as e:
            print(f'[Turkey Rhetoric] Telegram fetch error: {str(e)[:120]}')

    bluesky_signals = []
    if BLUESKY_AVAILABLE:
        try:
            bluesky_signals = fetch_bluesky_for_target('turkey') or []
            print(f'[Turkey Rhetoric] Bluesky: {len(bluesky_signals)} posts')
        except Exception as e:
            print(f'[Turkey Rhetoric] Bluesky fetch error: {str(e)[:120]}')

    reddit_signals = _fetch_reddit()
    print(f'[Turkey Rhetoric] Reddit: {len(reddit_signals)} posts')

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
        }

    score = _compute_theatre_score(by_actor, articles)
    alert = _alert_level_from_score(score)

    articles_en = [a for a in articles if a.get('language', 'eng') in ('eng', None)]
    articles_tr = [a for a in articles if a.get('language') == 'tur']
    articles_other = [a for a in articles
                      if a.get('language') not in ('eng', 'tur', None)]

    scan_data = {
        'articles_en':       articles_en,
        'articles_tr':       articles_tr,
        'articles_other':    articles_other,
        'telegram_messages': telegram_messages,
        'bluesky_signals':   bluesky_signals,
        'reddit_signals':    reddit_signals,
        'by_actor':          by_actor,
        'actor_summaries':   actor_summaries,
        'theatre_score':     score,
        'alert_level':       alert,
    }

    interpretation = interpret_signals(scan_data)
    _write_cross_theater_fingerprints(
        interpretation.get('cross_theater_fingerprints') or {}
    )

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'turkey',
        'flag':              '\U0001f1f9\U0001f1f7',
        'display_name':      'Turkey',
        'theatre_score':     score,
        'alert_level':       alert,
        'pressure_score':    score,
        'tracker_version':   '1.0.0',
        'tracker_class':     'swing_state',
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
        'telegram_count':    len(telegram_messages),
        'bluesky_count':     len(bluesky_signals),
        'reddit_count':      len(reddit_signals),
        'articles_en':       articles_en,
        'articles_tr':       articles_tr,
        'articles_other':    articles_other,
        'actor_summaries':   actor_summaries,
        'so_what':           interpretation.get('so_what'),
        'top_signals':       interpretation.get('top_signals') or [],
        'red_lines':         interpretation.get('red_lines'),
        'green_lines':       interpretation.get('green_lines'),
        'diplomatic_track':  interpretation.get('diplomatic_track'),
        'alignment':         interpretation.get('alignment'),
        'lebanon_vector':    interpretation.get('lebanon_vector'),
        'mirror_friction':   interpretation.get('mirror_friction'),
        'election_clock':    interpretation.get('election_clock'),
        'cross_theater_fingerprints': interpretation.get('cross_theater_fingerprints'),
        'composite_modifier': interpretation.get('composite_modifier', 0),
        'interpreter_version': interpretation.get('interpreter_version'),
        'disclaimer':        interpretation.get('disclaimer'),
    }

    _redis_set(REDIS_KEY_LATEST, result)
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'alignment': {
            'nato_anchor_index':        (result.get('alignment') or {}).get('nato_anchor_index'),
            'strategic_autonomy_index': (result.get('alignment') or {}).get('strategic_autonomy_index'),
            'divergence':               (result.get('alignment') or {}).get('divergence'),
        },
        'lebanon_vector_stage': (result.get('lebanon_vector') or {}).get('stage'),
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Turkey Rhetoric] Scan complete: score={score}, alert={alert}, '
          f'articles={len(articles)}, elapsed={elapsed}s')
    return result


# ============================================================
# BACKGROUND REFRESH
# ============================================================

def _background_refresh():
    time.sleep(150)
    while True:
        try:
            with _scan_lock:
                run_turkey_rhetoric_scan(force=True)
        except Exception as e:
            print(f'[Turkey Rhetoric] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Turkey Rhetoric] Background refresh thread started (6h cycle)')


# ============================================================
# ENDPOINT REGISTRATION
# ============================================================

def register_turkey_rhetoric_endpoints(app):
    @app.route('/api/rhetoric/turkey', methods=['GET'])
    def api_rhetoric_turkey():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            data = run_turkey_rhetoric_scan(force=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error':   str(e)[:200],
                'theatre': 'turkey',
            }), 500

    @app.route('/api/rhetoric/turkey/summary', methods=['GET'])
    def api_rhetoric_turkey_summary():
        try:
            d = run_turkey_rhetoric_scan(force=False)
            return jsonify({
                'theatre':         'turkey',
                'flag':            '\U0001f1f9\U0001f1f7',
                'display_name':    'Turkey',
                'theatre_score':   d.get('theatre_score', 0),
                'alert_level':     d.get('alert_level', 'normal'),
                'tracker_class':   'swing_state',
                'alignment':       d.get('alignment'),
                'lebanon_vector_stage': (d.get('lebanon_vector') or {}).get('stage'),
                'top_signals':     (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'cached_at':       d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/turkey/history', methods=['GET'])
    def api_rhetoric_turkey_history():
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
                'theatre': 'turkey',
                'count':   len(history),
                'history': history,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500
