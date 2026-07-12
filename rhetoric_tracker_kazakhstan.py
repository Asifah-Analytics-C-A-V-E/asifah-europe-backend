"""
Kazakhstan Multi-Vector Tracker v1.0.0 (Jul 12 2026)
=====================================================
Central Asia's hedging-integrity sensor. Calls
kazakhstan_signal_interpreter.interpret_signals() for the analytical layer.

WHY "MULTI-VECTOR" AND NOT "PRESSURE": multi-vector hedging IS Kazakh state
doctrine. Astana sells stability to Moscow, Beijing and Washington at the same
time, and the product is mostly real. So the instrument does not ask which way
the country is drifting (that is the Armenia question) -- it asks whether the
HEDGE IS HOLDING, and treats divergence from three-pole equilibrium as the
signal, whichever pole is pulling.

EMISSIONS (emit once, consume many):
  rhetoric:kazakhstan:latest          own payload (Europe BLUF, both pages)
  rhetoric:kazakhstan:history         lpush trim 120
  crosstheater:kazakhstan:fingerprint canonical per-country spoke -- the Russia
                                      wheel's reader is deployed and listening.
                                      node_class = friction_drift (same taxonomy
                                      tier as Armenia). SURFACE-ONLY: no polarity
                                      wired into any score.
  spoke:china:kazakhstan              *** THE FIRST CHINA-WHEEL SPOKE ***
                                      Schema mirrors spoke:turkey:<c> exactly
                                      (level / relationship / top_signal) so a
                                      future China wheel reads its rim with the
                                      same reader the Turkey wheel already uses.
                                      Relationship vocabulary is the Turkey
                                      wheel's (alignment / friction) by decision.
                                      Polarity is DYNAMIC and carries the dual-
                                      track read: elite pull vs street friction.

READS (never re-scan, never re-clone):
  commodity_proxy_europe.get_commodity_data('kazakhstan')
      Server-side, in-process. The proxy owns the three-layer cascade
      (Europe Redis -> ME backend -> stale-flagged -> placeholder). Reading it
      HERE rather than in the browser is the whole point: the commodity read
      reaches top_signals -> Europe BLUF -> GPI, instead of being decorative
      on one page.

      CONVERGENCE-GATED in the interpreter: Kazakhstan's commodity pressure is
      STRUCTURAL (#1 uranium producer every day of the year), so it never feeds
      the score alone. It fires only when it co-occurs with a live pressure
      vector -- a chokepoint being SQUEEZED, not a chokepoint merely existing.

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

from kazakhstan_signal_interpreter import interpret_signals

# Commodity proxy — soft import so a missing proxy degrades the commodity
# vector to absence-honest rather than crashing the whole tracker.
try:
    from commodity_proxy_europe import get_commodity_data
    COMMODITY_PROXY_AVAILABLE = True
except ImportError:
    COMMODITY_PROXY_AVAILABLE = False
    print('[Kazakhstan Tracker] Commodity proxy unavailable -- commodity vector '
          'will read absence-honest')


# ============================================================
# CONFIG
# ============================================================

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')
NEWSAPI_KEY         = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY       = os.environ.get('BRAVE_API_KEY')

GDELT_BASE_URL   = 'https://api.gdeltproject.org/api/v2/doc/doc'
NEWSAPI_BASE_URL = 'https://newsapi.org/v2/everything'
BRAVE_BASE_URL   = 'https://api.search.brave.com/res/v1/news/search'

REDIS_KEY_LATEST    = 'rhetoric:kazakhstan:latest'
REDIS_KEY_HISTORY   = 'rhetoric:kazakhstan:history'
SPOKE_KEY_CANONICAL = 'crosstheater:kazakhstan:fingerprint'
SPOKE_KEY_CHINA     = 'spoke:china:kazakhstan'      # <-- first China-wheel spoke
SCAN_LOCK_KEY       = 'lock:rhetoric:kazakhstan:scan'
REFRESH_INTERVAL_SEC = 6 * 3600

_scan_lock = threading.Lock()


# ============================================================
# ACTORS
# ============================================================

ACTORS = {
    'kazakh_government': {
        'name': 'Kazakh Government',
        'flag': '\U0001f1f0\U0001f1ff',
        'icon': '\U0001f3db\ufe0f',
        'color': '#0ea5e9',
        'role': 'Tokayev, Akorda, MFA, Kurultai',
        'description': (
            'Tokayev and the Akorda. The July 1 2026 constitution rewrote roughly '
            'four-fifths of the 1995 text: bicameral parliament replaced by a '
            'unicameral Kurultai (party-lists only, no independents), a '
            'PRESIDENTIALLY APPOINTED vice presidency created, a People\'s Council '
            'with legislative initiative added. On July 7 2026 the Constitutional '
            'Court ruled his current term does not count -- the "single seven-year '
            'term" survives on paper while the clock resets. Watch: the VP '
            'appointment (it names the heir), snap-election signals, "Just '
            'Kazakhstan" framing, multi-vector doctrine restatements.'
        ),
        'keywords': [
            'tokayev', 'kassym-jomart tokayev', 'akorda', 'kazakh government',
            'kazakhstan president', 'kurultai', 'kazakh parliament', 'astana government',
            'kazakh mfa', 'just kazakhstan', 'new kazakhstan', 'kazakh constitution',
            'vice president kazakhstan', 'multi-vector foreign policy',
            '\u0442\u043e\u043a\u0430\u0435\u0432', '\u0430\u043a\u043e\u0440\u0434\u0430',
            '\u043a\u0443\u0440\u0443\u043b\u0442\u0430\u0439',
        ],
    },
    'domestic_pressure': {
        'name': 'Domestic Pressure (Jan-2022 Class)',
        'flag': '\u270a',
        'icon': '\U0001f525',
        'color': '#f97316',
        'role': 'Labour, protest, fuel/utility tariffs, Mangystau oil belt',
        'description': (
            'The precursor chain that produced Bloody January: a fuel-price change '
            'on January 1 2022 became a national uprising within roughly seventy-two '
            'hours, leaving ~238 dead and CSTO troops on Kazakh soil. The chain is '
            'documented and repeatable -- price trigger, then Mangystau/Zhanaozen '
            'labour action (Zhanaozen 2011 is the deep precedent), then metastasis. '
            'PATTERN MEMORY, not prophecy: the tracker reports where the chain '
            'stands, never that it will complete.'
        ),
        'keywords': [
            'protest kazakhstan', 'strike kazakhstan', 'zhanaozen', 'mangystau',
            'mangistau', 'oil workers strike', 'fuel price kazakhstan', 'lpg price',
            'utility tariff kazakhstan', 'rally kazakhstan', 'labour dispute kazakhstan',
            'activist arrested kazakhstan', 'crackdown kazakhstan', 'bloody january',
            'qandy qantar', 'aktau protest', 'almaty unrest',
            '\u043f\u0440\u043e\u0442\u0435\u0441\u0442\u044b \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
            '\u0437\u0430\u0431\u0430\u0441\u0442\u043e\u0432\u043a\u0430',
            '\u0436\u0430\u043d\u0430\u043e\u0437\u0435\u043d',
        ],
    },
    'russia_inbound': {
        'name': 'Russia (Inbound Levers)',
        'flag': '\U0001f1f7\U0001f1fa',
        'icon': '\U0001f43b',
        'color': '#ef4444',
        'role': 'CPC chokehold, irredentist rhetoric, EAEU, Baikonur, sanctions corridor',
        'description': (
            'Moscow toward Astana, and the levers are physical. The CPC pipeline '
            '(Tengiz to Novorossiysk) carries roughly four-fifths of Kazakh crude '
            'exports through Russian territory, and Moscow has suspended the terminal '
            'on maintenance and storm-damage grounds during periods of friction -- the '
            'dependency IS the leverage. Add: northern-Kazakhstan irredentist rhetoric '
            '(post-Ukraine, Astana reads this as existential), the EAEU, Baikonur to '
            '2050, Rosatom, and the sanctions-rerouting corridor that is simultaneously '
            'a revenue lifeline and an OFAC liability. Tokayev refused to recognise the '
            'breakaway republics while sitting beside Putin at SPIEF 2022. Tempo is '
            'measured BOTH directions; the sensor never adjudicates.'
        ),
        'keywords': [
            'russia kazakhstan', 'moscow astana', 'putin tokayev', 'cpc pipeline',
            'caspian pipeline consortium', 'novorossiysk', 'eaeu kazakhstan',
            'eurasian economic union', 'csto kazakhstan', 'baikonur', 'rosatom kazakhstan',
            'gazprom kazakhstan', 'russian language kazakhstan', 'northern kazakhstan',
            'sanctions evasion kazakhstan', 'parallel imports kazakhstan',
            '\u0440\u043e\u0441\u0441\u0438\u044f \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
            '\u043a\u0442\u043a', '\u0431\u0430\u0439\u043a\u043e\u043d\u0443\u0440',
        ],
    },
    'china_inbound': {
        'name': 'China (Dual Track)',
        'flag': '\U0001f1e8\U0001f1f3',
        'icon': '\U0001f409',
        'color': '#eab308',
        'role': 'Elite pull (BRI, trade, energy) vs street friction (Sinophobia, water, Xinjiang)',
        'description': (
            'China is not one signal here, it is two with opposite polarity. ELITE '
            'PULL: top trade partner, the Belt and Road was announced in Astana in '
            '2013, Khorgos dry port, pipelines east, uranium to Chinese reactors. '
            'STREET FRICTION: recurring Sinophobia (land-lease protests, debt '
            'anxiety), the Xinjiang ethnic-Kazakh grievance Astana suppresses, and '
            'transboundary water -- Beijing controls the Ili and Irtysh headwaters, '
            'and Lake Balkhash is the slow-motion story. A government leaning in '
            'while the street pushes back is the NORMAL Kazakh condition; the read '
            'is in how far the two tracks diverge. This actor feeds the FIRST China '
            'spoke on the platform.'
        ),
        'keywords': [
            'china kazakhstan', 'beijing astana', 'belt and road kazakhstan', 'bri kazakhstan',
            'xi jinping kazakhstan', 'khorgos', 'sco summit', 'china central asia',
            'chinese investment kazakhstan', 'anti-china protest', 'sinophobia',
            'xinjiang kazakhs', 'atajurt', 'ili river', 'irtysh', 'lake balkhash',
            'land lease china', 'chinese loan kazakhstan',
            '\u043a\u0438\u0442\u0430\u0439 \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
            '\u0441\u0438\u043d\u044c\u0446\u0437\u044f\u043d',
        ],
    },
    'corridor_logistics': {
        'name': 'Middle Corridor / TITR',
        'flag': '\U0001f6a2',
        'icon': '\U0001f5fa\ufe0f',
        'color': '#38bdf8',
        'role': 'Trans-Caspian route, Aktau/Kuryk ports, the hedge against route dependency',
        'description': (
            'The escape route. Kazakh crude exits via Russia and Kazakh uranium '
            'transits Russia; chromium rides Chinese rail east. The Middle Corridor '
            '(Trans-Caspian International Transport Route) is Astana\'s attempt to own '
            'a way out -- Aktau and Kuryk ports, Caspian shipping, rail to Baku and on '
            'to Europe, EU Global Gateway money. Corridor-vector family member #2 '
            '(TRIPP was #1, and TRIPP is designed to plug into this). Watch: volume '
            'records, port capacity, investment, and the constraint reporting that '
            'rises when a bypass matures fast enough to matter to the states it '
            'bypasses.'
        ),
        'keywords': [
            'middle corridor', 'trans-caspian', 'titr', 'aktau port', 'kuryk port',
            'caspian shipping', 'trans caspian international transport route',
            'global gateway kazakhstan', 'container train china europe',
            'rail freight kazakhstan europe', 'kazakhstan transit route',
            'export diversification kazakhstan', 'btc pipeline kazakh',
            '\u0441\u0440\u0435\u0434\u043d\u0438\u0439 \u043a\u043e\u0440\u0438\u0434\u043e\u0440',
            '\u0430\u043a\u0442\u0430\u0443 \u043f\u043e\u0440\u0442',
        ],
    },
    'west_anchor': {
        'name': 'West / Minerals Anchor',
        'flag': '\U0001f1fa\U0001f1f8',
        'icon': '\u2693',
        'color': '#93c5fd',
        'role': 'C5+1, critical minerals, TCO/Kashagan, EU Global Gateway',
        'description': (
            'The third pole. Chevron\'s Tengizchevroil and the Kashagan consortium are '
            'the largest Western investments in Central Asia; the C5+1 format, the '
            'US/EU critical-minerals courtship, and EU Global Gateway money for the '
            'Middle Corridor are the diplomatic scaffolding. Kazakhstan joined the '
            'Abraham Accords in November 2025 -- largely symbolic, but a legible '
            'West-pole data point. Progress here is what keeps the hedge three-sided.'
        ),
        'keywords': [
            'us kazakhstan', 'eu kazakhstan', 'c5+1', 'chevron kazakhstan',
            'tengizchevroil', 'kashagan', 'critical minerals kazakhstan',
            'rare earths kazakhstan', 'western investment kazakhstan',
            'abraham accords kazakhstan', 'eu global gateway', 'brussels astana',
            'washington astana', 'exxonmobil kazakhstan',
            '\u0441\u0448\u0430 \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
            '\u0435\u0441 \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
        ],
    },
    'turkic_axis': {
        'name': 'Turkic Axis (OTS)',
        'flag': '\U0001f1f9\U0001f1f7',
        'icon': '\U0001f91d',
        'color': '#a855f7',
        'role': 'Organization of Turkic States, Ankara defence-industrial ties',
        'description': (
            'The fourth, lighter pole -- the one Astana uses to dilute the big-three '
            'hedge. Organization of Turkic States summits, the Turkic Investment Fund, '
            'and Ankara\'s defence-industrial offer (drones, joint production). Small '
            'in volume, but it is the pole that costs Astana least to lean on, which '
            'is precisely why leaning on it is informative.'
        ),
        'keywords': [
            'organization of turkic states', 'turkic states summit', 'turkic council',
            'turkey kazakhstan', 'ankara astana', 'turkish drone kazakhstan',
            'anka kazakhstan', 'baykar kazakhstan', 'turkic investment fund',
            'turkey kazakhstan defence', 'erdogan tokayev',
            '\u0442\u0443\u0440\u0446\u0438\u044f \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
        ],
    },
    'commodity_complex': {
        'name': 'Commodity Complex',
        'flag': '\u2622\ufe0f',
        'icon': '\U0001f6e2\ufe0f',
        'color': '#22c55e',
        'role': 'Uranium (#1 globally), oil, chromium, gas, wheat -- and the routes they take',
        'description': (
            'Kazakhstan supplies roughly forty percent of the world\'s uranium '
            '(Kazatomprom, #1 globally) and is a top-tier oil exporter (Tengiz, '
            'Kashagan, Karachaganak). It is also #2 in chromium. But the read is not '
            'the volume -- it is the ROUTE: crude exits via CPC through Russia, '
            'uranium transits Russia, chromium rides Chinese rail east. The commodity '
            'POWER is real and the commodity ROUTES belong to the two neighbours being '
            'hedged against. This card is display-and-context; the scoring lives in the '
            'interpreter\'s CONVERGENCE GATE, which fires only when commodity pressure '
            'co-occurs with a live pressure vector.'
        ),
        'keywords': [
            'kazatomprom', 'uranium kazakhstan', 'kazakh oil', 'tengiz', 'kashagan',
            'karachaganak', 'kazmunaygas', 'chromium kazakhstan', 'ferrochrome',
            'kazakh wheat', 'kazakh gas export', 'uranium price', 'oil export kazakhstan',
            'nuclear fuel kazakhstan',
            '\u043a\u0430\u0437\u0430\u0442\u043e\u043c\u043f\u0440\u043e\u043c',
            '\u0443\u0440\u0430\u043d \u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d',
        ],
    },
}


# ============================================================
# GDELT QUERIES
# sourcelang codes verified against the live LOOKUP-LANGUAGES table
# during the Armenia build: kaz = Kazakh, rus = Russian.
# ============================================================

GDELT_QUERIES = {
    'eng': [
        '"kazakhstan" AND ("tokayev" OR "astana")',
        '"kazakhstan" AND ("protest" OR "strike" OR "unrest")',
        '"kazakhstan" AND ("russia" OR "cpc" OR "pipeline")',
        '"kazakhstan" AND ("china" OR "belt and road" OR "khorgos")',
        '"kazakhstan" AND ("middle corridor" OR "trans-caspian" OR "aktau")',
        '"kazakhstan" AND ("uranium" OR "kazatomprom" OR "oil export")',
        '"kazakhstan" AND ("sanctions" OR "re-export" OR "parallel import")',
        '"kazakhstan" AND ("election" OR "constitution" OR "kurultai")',
    ],
    'kaz': [
        '"\u049b\u0430\u0437\u0430\u049b\u0441\u0442\u0430\u043d"',
        '"\u0442\u043e\u049b\u0430\u0435\u0432" OR "\u0430\u0441\u0442\u0430\u043d\u0430"',
    ],
    'rus': [
        '"\u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d" AND ("\u0442\u043e\u043a\u0430\u0435\u0432" OR "\u0430\u0441\u0442\u0430\u043d\u0430")',
        '"\u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d" AND ("\u043f\u0440\u043e\u0442\u0435\u0441\u0442" OR "\u043a\u0442\u043a" OR "\u0441\u0430\u043d\u043a\u0446\u0438\u0438")',
    ],
}


# ============================================================
# TOPIC FILTER (Reddit gate)
# ============================================================

KAZAKHSTAN_TOPIC_KEYWORDS = [
    'kazakhstan', 'kazakh', 'astana', 'almaty', 'tokayev', 'nazarbayev',
    'kazatomprom', 'zhanaozen', 'mangystau', 'aktau', 'khorgos', 'baikonur',
    'middle corridor', 'central asia', 'tengiz', 'kashagan',
    '\u043a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d', '\u0430\u0441\u0442\u0430\u043d\u0430',
    '\u049b\u0430\u0437\u0430\u049b\u0441\u0442\u0430\u043d',
]


# ============================================================
# RSS FEEDS (per-feed soft-fail; verify in boot logs on first deploy)
# ============================================================

RSS_FEEDS = [
    {'url': 'https://eurasianet.org/rss',                'name': 'Eurasianet',     'weight': 0.90},
    {'url': 'https://astanatimes.com/feed/',             'name': 'Astana Times',   'weight': 0.85},
    {'url': 'https://www.intellinews.com/feed',          'name': 'bne IntelliNews','weight': 0.85},
    {'url': 'https://cabar.asia/en/feed',                'name': 'CABAR.asia',     'weight': 0.80},
    {'url': 'https://thediplomat.com/regions/centralasia/feed/', 'name': 'The Diplomat CA', 'weight': 0.85},
]


# ============================================================
# REDIS HELPERS
# ============================================================

def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                         timeout=5)
        d = r.json()
        if d.get('result'):
            return json.loads(d['result'])
    except Exception as e:
        print(f'[Kazakhstan Tracker] Redis get error: {str(e)[:120]}')
    return None


def _redis_set(key, value):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', key, json.dumps(value, default=str)],
                          timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f'[Kazakhstan Tracker] Redis set error: {str(e)[:120]}')
        return False


def _redis_lpush_trim(key, value, max_len=120):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        requests.post(f'{UPSTASH_REDIS_URL}/lpush/{key}',
                      headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                               'Content-Type': 'application/json'},
                      json={'value': json.dumps(value, default=str)}, timeout=10)
        requests.post(f'{UPSTASH_REDIS_URL}/ltrim/{key}/0/{max_len-1}',
                      headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=5)
        return True
    except Exception as e:
        print(f'[Kazakhstan Tracker] Redis lpush error: {str(e)[:120]}')
        return False


def _acquire_scan_lock(ttl_sec=900):
    """Cross-worker atomic lock (SET NX EX) for the BACKGROUND loop only."""
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return True
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', SCAN_LOCK_KEY,
                                datetime.now(timezone.utc).isoformat(), 'NX', 'EX', ttl_sec],
                          timeout=8)
        return (r.json() or {}).get('result') == 'OK'
    except Exception as e:
        print(f'[Kazakhstan Tracker] Scan lock error (proceeding): {str(e)[:120]}')
        return True


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
        print(f'[Kazakhstan RSS] {source_name}: {len(out)} items')
    except Exception as e:
        print(f'[Kazakhstan RSS] {source_name}: {str(e)[:120]}')
    return out


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    params = {'query': query, 'mode': 'artlist', 'maxrecords': max_records,
              'format': 'json', 'sort': 'datedesc', 'timespan': f'{days*24}h',
              'sourcelang': language}
    try:
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=(5, 15))
        if resp.status_code == 429:
            print('[Kazakhstan GDELT] Rate limited (429) -- backing off')
            return []
        if resp.status_code != 200:
            print(f'[Kazakhstan GDELT] HTTP {resp.status_code}')
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
        print(f'[Kazakhstan GDELT] {str(e)[:120]}')
        return []


def _fetch_newsapi(query='kazakhstan', max_records=40):
    if not NEWSAPI_KEY:
        return []
    try:
        r = requests.get(NEWSAPI_BASE_URL,
                         params={'q': query, 'pageSize': max_records, 'language': 'en',
                                 'sortBy': 'publishedAt', 'apiKey': NEWSAPI_KEY},
                         timeout=10)
        if r.status_code != 200:
            print(f'[Kazakhstan NewsAPI] HTTP {r.status_code}')
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
        print(f'[Kazakhstan NewsAPI] {str(e)[:120]}')
        return []


def _fetch_brave(query='kazakhstan russia china', max_records=20):
    if not BRAVE_API_KEY:
        return []
    try:
        r = requests.get(BRAVE_BASE_URL,
                         headers={'Accept': 'application/json',
                                  'X-Subscription-Token': BRAVE_API_KEY},
                         params={'q': query, 'count': max_records, 'freshness': 'pw'},
                         timeout=10)
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
        print(f'[Kazakhstan Brave] {str(e)[:120]}')
        return []


def _fetch_reddit():
    """Browser-like UA -- generic UAs get silently 403'd by Reddit."""
    out = []
    subs = ['Kazakhstan', 'CentralAsia', 'geopolitics', 'worldnews', 'CredibleDefense']
    ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    total = 0
    for sub in subs:
        try:
            r = requests.get(f'https://www.reddit.com/r/{sub}/new.json?limit=25',
                             headers={'User-Agent': ua, 'Accept': 'application/json'},
                             timeout=8)
            if r.status_code != 200:
                print(f'[Kazakhstan Reddit] r/{sub}: HTTP {r.status_code}')
                continue
            for child in (r.json().get('data', {}).get('children') or []):
                p = child.get('data', {})
                title = (p.get('title') or '').lower()
                if not any(kw in title for kw in KAZAKHSTAN_TOPIC_KEYWORDS):
                    continue
                out.append({
                    'title':       p.get('title', '')[:300],
                    'description': (p.get('selftext') or '')[:400],
                    'url':         f"https://reddit.com{p.get('permalink', '')}",
                    'published':   datetime.fromtimestamp(
                        p.get('created_utc', 0), tz=timezone.utc).isoformat()
                        if p.get('created_utc') else None,
                    'source':      f'reddit-{sub}',
                    'source_type': 'reddit',
                    'language':    'eng',
                    'score':       p.get('score', 0),
                    'comments':    p.get('num_comments', 0),
                    'weight':      0.65,
                })
                total += 1
        except Exception as e:
            print(f'[Kazakhstan Reddit] r/{sub}: {str(e)[:120]}')
        time.sleep(0.3)
    print(f'[Kazakhstan Reddit] Total: {total} posts across {len(subs)} subreddits')
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
        articles.extend(_fetch_newsapi('kazakhstan', max_records=40))
    if len(articles) < 15:
        articles.extend(_fetch_brave('kazakhstan russia china', max_records=20))
    seen, unique = set(), []
    for a in articles:
        u = a.get('url')
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    return unique


# ============================================================
# COMMODITY READ (server-side, in-process — never an HTTP self-call)
# ============================================================

def _read_commodity():
    """Read the commodity proxy IN-PROCESS. The proxy owns the three-layer
    cascade (Europe Redis -> ME backend -> stale-flagged -> placeholder), so we
    inherit its absence-honesty for free.

    Reading it HERE rather than in the browser is the architectural point: the
    commodity read reaches top_signals -> Europe BLUF -> GPI. A frontend fetch
    would be decorative.

    NOTE: the interpreter CONVERGENCE-GATES this. Kazakhstan's commodity
    pressure is structural (world's #1 uranium producer every day of the year),
    so it never feeds the score alone -- only when it co-occurs with a live
    pressure vector."""
    if not COMMODITY_PROXY_AVAILABLE:
        return None
    try:
        data = get_commodity_data('kazakhstan')
        if not isinstance(data, dict):
            return None
        print(f"[Kazakhstan Tracker] Commodity: pressure="
              f"{data.get('commodity_pressure', 0)} alert={data.get('alert_level')} "
              f"commodities={len(data.get('commodity_summaries') or [])} "
              f"stale={data.get('stale', False)}")
        return data
    except Exception as e:
        print(f'[Kazakhstan Tracker] Commodity read failed: {str(e)[:120]}')
        return None


# ============================================================
# CLASSIFICATION (co-crediting)
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
    return sum(1 for kw in actor_def.get('keywords', []) if kw.lower() in text)


def _classify_articles(articles):
    """Best-match actor gets PRIMARY credit (counts toward score); any other
    actor matching >= 2 keywords gets a co-credit copy (visible, not scored)."""
    CO_CREDIT_MIN = 2
    by_actor = {k: [] for k in ACTORS}
    for art in articles:
        scores = {}
        for key, defn in ACTORS.items():
            s = _score_article_for_actor(art, defn)
            if s >= 1:
                scores[key] = s
        if not scores:
            continue
        best = max(scores, key=lambda k: scores[k])
        cp = dict(art)
        cp['actor_score'] = scores[best]
        by_actor[best].append(cp)
        for key, s in scores.items():
            if key != best and s >= CO_CREDIT_MIN:
                cc = dict(art)
                cc['actor_score'] = s
                cc['co_credit'] = True
                by_actor[key].append(cc)
    return by_actor


# ============================================================
# THEATRE SCORE + BANDS
# ============================================================

def _compute_theatre_score(by_actor, articles):
    """Baseline +6: a functioning managed-authoritarian state with real
    stability, not a conflict theatre. commodity_complex carries weight 0.0 --
    it is DISPLAY-ONLY here because scoring it directly would pin Kazakhstan at
    'surge' permanently (it is the #1 uranium producer every day of the year).
    Its analytical weight arrives through the interpreter's CONVERGENCE GATE."""
    BASELINE = 6
    actor_weights = {
        'kazakh_government':  0.75,
        'domestic_pressure':  1.00,   # the Jan-2022 class carries the most weight
        'russia_inbound':     0.95,
        'china_inbound':      0.85,
        'corridor_logistics': 0.60,
        'west_anchor':        0.60,
        'turkic_axis':        0.50,
        'commodity_complex':  0.00,   # DISPLAY-ONLY — see convergence gate
    }
    score = BASELINE
    for key, arts in by_actor.items():
        w = actor_weights.get(key, 0.7)
        score += min(25, sum(a.get('weight', 0.7) for a in arts
                             if not a.get('co_credit')) * w)
    return max(0, min(100, int(score)))


def _alert_level_from_score(score):
    if score >= 80:
        return 'critical'
    if score >= 60:
        return 'high'
    if score >= 40:
        return 'elevated'
    return 'normal'


# ============================================================
# SPOKE EMISSIONS
# ============================================================

_SPOKE_LEVEL_BY_ALERT = {'normal': 1, 'elevated': 2, 'high': 3, 'critical': 4}


def _write_canonical_spoke_fingerprint(result, fingerprints):
    """crosstheater:kazakhstan:fingerprint — the Russia wheel's reader is
    deployed and listening. node_class = friction_drift, the same taxonomy tier
    as Armenia (Azerbaijan/Armenia/Kazakhstan-Central Asia).

    SURFACE-ONLY: node_class documents the taxonomy tier; no polarity is wired
    into any score. That remains a wheel scoping decision, not plumbing."""
    alert = result.get('alert_level', 'normal')
    fp = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'kazakhstan',
        'node_class':  'friction_drift',
        'level':       _SPOKE_LEVEL_BY_ALERT.get(alert, 1),
        'score':       result.get('theatre_score', 0),
        'alert_level': alert,
        # Kazakhstan-specific slices
        'hedging_integrity':     fingerprints.get('hedging_integrity', {}),
        'middle_corridor':       fingerprints.get('middle_corridor', {}),
        'russia_levers':         fingerprints.get('russia_levers', {}),
        'china_spoke':           fingerprints.get('china_spoke', {}),
        'domestic_tripwire':     fingerprints.get('domestic_tripwire', {}),
        'commodity_convergence': fingerprints.get('commodity_convergence', {}),
    }
    try:
        _redis_set(SPOKE_KEY_CANONICAL, fp)
        print('[Kazakhstan Tracker] Canonical spoke fingerprint written '
              '(crosstheater:kazakhstan:fingerprint)')
    except Exception as e:
        print(f'[Kazakhstan Tracker] Canonical fingerprint write failed: {e}')


def _write_china_spoke(fingerprints):
    """*** spoke:china:kazakhstan -- THE FIRST CHINA-WHEEL SPOKE ***

    Schema mirrors spoke:turkey:<c> EXACTLY (level / relationship / top_signal)
    so that when a China wheel is built, it reads its rim with the same reader
    shape the Turkey wheel already uses. Relationship vocabulary is the Turkey
    wheel's (alignment / friction) by decision -- consistency beats creativity.

    The polarity is DYNAMIC and carries the dual-track read: elite pull vs
    street friction. A government leaning into Beijing while the street pushes
    back is the normal Kazakh condition, and the spoke says so."""
    cs = fingerprints.get('china_spoke') or {}
    if not cs:
        return
    payload = {
        'ts':           datetime.now(timezone.utc).isoformat(),
        'country':      'kazakhstan',
        'level':        cs.get('level', 0),
        'relationship': cs.get('relationship', 'alignment'),
        'top_signal':   cs.get('top_signal', ''),
        # dual-track extras (a future China wheel can use or ignore these)
        'track':          cs.get('track'),
        'elite_signals':  cs.get('elite_signals', 0),
        'street_signals': cs.get('street_signals', 0),
    }
    try:
        _redis_set(SPOKE_KEY_CHINA, payload)
        print(f"[Kazakhstan Tracker] *** CHINA SPOKE WRITTEN *** "
              f"(spoke:china:kazakhstan, relationship={payload['relationship']}, "
              f"track={payload['track']}) -- first writer of the China rim")
    except Exception as e:
        print(f'[Kazakhstan Tracker] China spoke write failed: {e}')


# ============================================================
# MAIN SCAN
# ============================================================

def run_kazakhstan_rhetoric_scan(force=False):
    if not force:
        cached = _redis_get(REDIS_KEY_LATEST)
        if cached and cached.get('cached_at'):
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(cached['cached_at'])).total_seconds()
                if age < REFRESH_INTERVAL_SEC:
                    cached['cache_status'] = 'hit'
                    return cached
            except Exception:
                pass

    print('[Kazakhstan Tracker] Starting fresh scan...')
    started = time.time()

    articles = _fetch_all_articles()
    print(f'[Kazakhstan Tracker] Articles: {len(articles)}')
    reddit_signals = _fetch_reddit()
    commodity_data = _read_commodity()

    by_actor = _classify_articles(articles)
    actor_summaries = {}
    for key, arts in by_actor.items():
        d = ACTORS[key]
        actor_summaries[key] = {
            'name': d['name'], 'flag': d['flag'], 'icon': d['icon'],
            'color': d['color'], 'role': d['role'], 'description': d['description'],
            'article_count': len(arts), 'top_articles': arts[:5],
            'display_only': key == 'commodity_complex',
        }

    score = _compute_theatre_score(by_actor, articles)
    alert = _alert_level_from_score(score)

    articles_en = [a for a in articles if a.get('language', 'eng') in ('eng', None)]
    articles_kk = [a for a in articles if a.get('language') == 'kaz']
    articles_ru = [a for a in articles if a.get('language') == 'rus']

    scan_data = {
        'articles_en':     articles_en,
        'articles_kk':     articles_kk,
        'articles_ru':     articles_ru,
        'reddit_signals':  reddit_signals,
        'by_actor':        by_actor,
        'actor_summaries': actor_summaries,
        'theatre_score':   score,
        'alert_level':     alert,
        'commodity_data':  commodity_data,   # <-- server-side, convergence-gated
    }

    interpretation = interpret_signals(scan_data)

    # -- Structural-breach band floor. theatre_score is article VOLUME, so a
    #    BREACHED mass-unrest or CPC-disruption line can sit at 'normal' on
    #    volume alone and get buried in the GPI rollup. Floor the band so a
    #    genuine breach reads at least 'high' ('critical' when two or more
    #    stack). Floors only, never lowers. Re-bands an already-breached red
    #    line; invents no signal.
    _rl = (interpretation.get('red_lines') or {}).get('triggered') or []
    _structural = sum(1 for r in _rl if r.get('status') == 'BREACHED'
                      and r.get('id') in ('mass_unrest', 'fuel_price_unrest',
                                          'cpc_disruption', 'russian_irredentist'))
    _RANK = {'normal': 0, 'elevated': 1, 'high': 2, 'critical': 3}
    if _structural >= 2:
        score = max(score, 70)
        if _RANK['critical'] > _RANK.get(alert, 0):
            alert = 'critical'
    elif _structural >= 1:
        score = max(score, 55)
        if _RANK['high'] > _RANK.get(alert, 0):
            alert = 'high'
    if _structural:
        print(f'[Kazakhstan Tracker] Structural-breach floor applied: '
              f'{_structural} breach(es) -> band {alert}, score {score}')

    # -- Off-ramp maturity (shared schema with Iran/Ukraine/Armenia so the GPI
    #    and the repricing detector read Kazakhstan the same way).
    _green = interpretation.get('green_lines') or {}
    _green_active = _green.get('active_count', 0)
    _offramp = ('signed' if _green_active >= 3
                else 'framework' if _green_active >= 1 else 'none')

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'kazakhstan',
        'flag':              '\U0001f1f0\U0001f1ff',
        'display_name':      'Kazakhstan',
        'tracker_name':      'Kazakhstan Multi-Vector Tracker',
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
        'reddit_count':    len(reddit_signals),
        'articles_en':     articles_en,
        'articles_kk':     articles_kk,
        'articles_ru':     articles_ru,
        'actor_summaries': actor_summaries,
        'so_what':         interpretation.get('so_what'),
        'top_signals':     interpretation.get('top_signals') or [],
        'red_lines':       interpretation.get('red_lines'),
        'green_lines':     interpretation.get('green_lines'),
        # -- Kazakhstan vector payloads --
        'middle_corridor':       interpretation.get('middle_corridor'),
        'russia_levers':         interpretation.get('russia_levers'),
        'china_dual_track':      interpretation.get('china_dual_track'),
        'domestic_tripwire':     interpretation.get('domestic_tripwire'),
        'hedging_integrity':     interpretation.get('hedging_integrity'),
        'succession':            interpretation.get('succession'),
        'turkic_integration':    interpretation.get('turkic_integration'),
        'commodity_convergence': interpretation.get('commodity_convergence'),
        'election_clock':        interpretation.get('election_clock'),
        'winter_calendar':       interpretation.get('winter_calendar'),
        # -- commodity passthrough for the page card (display) --
        'commodity_snapshot': ({
            'pressure':    (commodity_data or {}).get('commodity_pressure', 0),
            'alert':       (commodity_data or {}).get('alert_level'),
            'commodities': [(c.get('commodity') or c.get('name'))
                            for c in ((commodity_data or {}).get('commodity_summaries') or [])][:6],
            'stale':       (commodity_data or {}).get('stale', False),
            'present':     commodity_data is not None,
        }),
        'de_escalation_maturity': _offramp,
        'cross_theater_fingerprints': interpretation.get('cross_theater_fingerprints'),
        'composite_modifier':  interpretation.get('composite_modifier', 0),
        'interpreter_version': interpretation.get('interpreter_version'),
        'disclaimer':          interpretation.get('disclaimer'),
    }

    _redis_set(REDIS_KEY_LATEST, result)
    fps = interpretation.get('cross_theater_fingerprints') or {}
    _write_canonical_spoke_fingerprint(result, fps)   # Russia wheel
    _write_china_spoke(fps)                           # *** FIRST CHINA SPOKE ***
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Kazakhstan Tracker] Scan complete: score={score}, alert={alert}, '
          f'articles={len(articles)}, elapsed={elapsed}s')
    return result


# ============================================================
# BACKGROUND REFRESH
# ============================================================

def _background_refresh():
    time.sleep(210)
    while True:
        try:
            if _acquire_scan_lock(ttl_sec=900):
                with _scan_lock:
                    run_kazakhstan_rhetoric_scan(force=True)
            else:
                print('[Kazakhstan Tracker] Another worker owns the scan window -- skipping')
        except Exception as e:
            print(f'[Kazakhstan Tracker] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Kazakhstan Tracker] Background refresh thread started '
          '(6h cycle, cross-worker lock)')


# ============================================================
# ENDPOINTS
# ============================================================

def register_kazakhstan_rhetoric_endpoints(app):

    @app.route('/api/rhetoric/kazakhstan', methods=['GET'])
    def api_rhetoric_kazakhstan():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            return jsonify(run_kazakhstan_rhetoric_scan(force=force))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200],
                            'theatre': 'kazakhstan'}), 500

    @app.route('/api/rhetoric/kazakhstan/summary', methods=['GET'])
    def api_rhetoric_kazakhstan_summary():
        try:
            d = run_kazakhstan_rhetoric_scan(force=False)
            return jsonify({
                'theatre':          'kazakhstan',
                'flag':             '\U0001f1f0\U0001f1ff',
                'display_name':     'Kazakhstan',
                'theatre_score':    d.get('theatre_score', 0),
                'alert_level':      d.get('alert_level', 'normal'),
                'top_signals':      (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'hedge_integrity':  (d.get('hedging_integrity') or {}).get('integrity'),
                'cached_at':        d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/kazakhstan/history', methods=['GET'])
    def api_rhetoric_kazakhstan_history():
        if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
            return jsonify({'success': False, 'error': 'Redis not configured', 'history': []})
        try:
            limit = min(int(request.args.get('limit', 30)), 120)
            r = requests.get(
                f'{UPSTASH_REDIS_URL}/lrange/{REDIS_KEY_HISTORY}/0/{limit-1}',
                headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=8)
            raw = (r.json().get('result') or []) if r.status_code == 200 else []
            history = []
            for item in raw:
                try:
                    history.append(json.loads(item))
                except Exception:
                    pass
            return jsonify({'success': True, 'theatre': 'kazakhstan',
                            'count': len(history), 'history': history})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500

    print('[Kazakhstan Tracker] Endpoints registered: /api/rhetoric/kazakhstan, '
          '/summary, /history')
