"""
Moldova Rhetoric Tracker (sensor) -- v1.0.0 -- July 16, 2026
Asifah Analytics -- Europe backend

THE NAMED QUESTION (drives the whole sensor):
  "Is Moldova being pulled out of the Western orbit faster than it is being
   anchored in -- and by what means?"

This is a CONTEST OF TEMPO, not a binary drift read. Russia will not invade
Moldova; it will try to CAPTURE IT FROM WITHIN before EU accession locks it in.
The tracker measures the race between Russian hybrid pressure (energy blackmail,
election interference, the Transnistria/Gagauzia frozen levers) and Western
integration momentum (EU accession). It is a TWO-SIDED tracker by design: the
eu_accession actor is a genuine de-escalatory / ANCHORING signal, not just a
pressure axis. The read is the BALANCE between capture-pressure and anchor.

Node class on the Russia wheel: INBOUND-TARGET (a place Russia acts UPON, same
taxonomy tier as Greenland/Arctic ring and the US influence slice). The spoke
measures "how hard is Russia pressing / is the target holding."

EMISSIONS (emit once, consume many):
  - rhetoric:moldova:latest / :history        (page + BLUF)
  - crosstheater:moldova:fingerprint          (Russia wheel reader; node_class=inbound_target)

Uses moldova_signal_interpreter.interpret_signals() for the analytical layer.

Absence-honesty throughout: per-feed soft-fail, commodity read is convergence-
gated (energy is structural, never scores alone), red-line band floors re-band
a genuine breach but never invent signal.
"""

import os
import json
import time
import threading
from datetime import datetime, timezone

import requests
import feedparser
from flask import request, jsonify

from moldova_signal_interpreter import interpret_signals

# Commodity proxy -- soft import so a missing proxy degrades the commodity
# vector to absence-honest rather than crashing the whole tracker.
try:
    from commodity_proxy_europe import get_commodity_data
    COMMODITY_PROXY_AVAILABLE = True
except ImportError:
    COMMODITY_PROXY_AVAILABLE = False
    print('[Moldova Tracker] Commodity proxy unavailable -- commodity vector '
          'will read absence-honest')

# Tempo baseline engine -- soft import (standing review rule: every new rhetoric
# tracker emits a corpus-health denominator so the engine suppresses quiet calls
# when a feed dies instead of hallucinating menace from its own outage).
try:
    from tempo_baseline import emit_tempo_sample
    TEMPO_AVAILABLE = True
except ImportError:
    TEMPO_AVAILABLE = False
    print('[Moldova Tracker] Tempo baseline unavailable -- skipping tempo emit')


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

REDIS_KEY_LATEST    = 'rhetoric:moldova:latest'
REDIS_KEY_HISTORY   = 'rhetoric:moldova:history'
SPOKE_KEY_CANONICAL = 'crosstheater:moldova:fingerprint'
SCAN_LOCK_KEY       = 'lock:rhetoric:moldova:scan'
REFRESH_INTERVAL_SEC = 6 * 3600

_scan_lock = threading.Lock()


# ============================================================
# ACTORS
# ============================================================
# Mode discipline (per the scoping note):
#   Russia/interference dimensions = deniable actors -> measure attack/
#   attribution/amplification TEMPO (tape-like). Transnistria/Gagauzia have
#   claiming actors -> silence is itself a signal (actor-like). eu_accession is
#   the ANCHOR (inverted polarity -- good news de-escalates). energy_complex is
#   DISPLAY-ONLY (structural; scores only through the interpreter convergence
#   gate, like Kazakhstan's commodity_complex).

ACTORS = {
    'moldovan_government': {
        'name': 'Moldovan Government',
        'flag': '\U0001f1f2\U0001f1e9',
        'icon': '\U0001f3db\ufe0f',
        'color': '#0ea5e9',
        'role': 'Sandu, PAS, MFA, the EU-accession drive',
        'description': (
            'President Maia Sandu and the pro-Western PAS government. The '
            'incumbent anchor of the Western trajectory -- pursuing EU accession '
            '(candidate since June 2022, negotiations opened 2024) while managing '
            'a pro-Russian opposition, a frozen conflict, and recurring energy '
            'shocks. Watch: government messaging discipline under pressure, '
            'coalition stability, reform-package cadence, MFA statements on '
            'Transnistria and Russia. This is the actor whose resilience the '
            'whole contest measures.'
        ),
        'keywords': [
            'maia sandu', 'sandu', 'moldova government', 'moldovan government',
            'pas party', 'action and solidarity', 'moldova president',
            'moldova mfa', 'moldova foreign ministry', 'recean', 'dorin recean',
            'moldova reform', 'moldova pro-western', 'moldova cabinet',
            '\u043c\u0430\u0439\u044f \u0441\u0430\u043d\u0434\u0443',
            '\u043f\u0440\u0430\u0432\u0438\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e \u043c\u043e\u043b\u0434\u043e\u0432\u044b',
            'guvernul moldovei', 'presedintele moldovei',
        ],
    },
    'russia_inbound': {
        'name': 'Russia (Inbound Levers)',
        'flag': '\U0001f1f7\U0001f1fa',
        'icon': '\U0001f43b',
        'color': '#ef4444',
        'role': 'Gazprom/Moldovagaz, FSB influence ops, hybrid pressure',
        'description': (
            'Moscow toward Chisinau, operating through DENIABLE levers rather than '
            'open force -- energy, money, information, and the frozen conflict. '
            'The dependency IS the leverage: the Cuciurgan plant in Transnistria '
            'ran on Russian gas and powered the pro-Western right bank until the '
            'Jan 1 2025 end of Ukraine transit. Add FSB-linked influence networks, '
            'Moldovagaz debt disputes, and coordinated disinformation. Tempo is '
            'measured in ATTACK / ATTRIBUTION / AMPLIFICATION -- the sensor never '
            'adjudicates a specific claim, it measures the tempo of the pressure.'
        ),
        'keywords': [
            'russia moldova', 'moscow chisinau', 'putin moldova', 'gazprom moldova',
            'moldovagaz', 'russian gas moldova', 'russia interference moldova',
            'russian influence moldova', 'fsb moldova', 'russia hybrid moldova',
            'kremlin moldova', 'russia destabilize moldova', 'russia pressure moldova',
            'moldova energy blackmail', 'russia disinformation moldova',
            '\u0440\u043e\u0441\u0441\u0438\u044f \u043c\u043e\u043b\u0434\u043e\u0432\u0430',
            '\u0432\u043c\u0435\u0448\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e \u0440\u043e\u0441\u0441\u0438\u0438',
            'ingerinta rusa', 'santaj energetic',
        ],
    },
    'transnistria': {
        'name': 'Transnistria (Frozen Lever)',
        'flag': '\U0001f7e5',
        'icon': '\u2744\ufe0f',
        'color': '#f97316',
        'role': 'OGRF garrison, Cobasna depot, left-bank gas, pretext watch',
        'description': (
            'The breakaway region east of the Dniester -- the frozen conflict that '
            'could unfreeze. Hosts the Russian Operational Group of Forces (~1,500 '
            'troops) and the Cobasna ammunition depot (~20,000 tons of Soviet-era '
            'munitions, 2km from Ukraine, ~40km from Odesa -- a standing flank '
            'threat to Ukraine\'s most important remaining port). This is the '
            'classic CONFLICT-TRACKER read: watch for escalation language, '
            '"peacekeeper" framing, left-bank gas status, troop-activity reports, '
            'and above all a MANUFACTURED PRETEXT. Silence here is itself a '
            'signal -- claiming actors go quiet before they move.'
        ),
        'keywords': [
            'transnistria', 'transdniestria', 'tiraspol', 'pridnestrovie',
            'operational group of russian forces', 'ogrf', 'cobasna', 'colbasna',
            'russian peacekeepers moldova', 'russian troops transnistria',
            'transnistria escalation', 'transnistria gas', 'cuciurgan', 'mgres',
            'transnistria mobilization', 'security zone dniester', 'dniester',
            '\u043f\u0440\u0438\u0434\u043d\u0435\u0441\u0442\u0440\u043e\u0432\u044c\u0435',
            '\u0442\u0438\u0440\u0430\u0441\u043f\u043e\u043b\u044c',
            '\u043a\u043e\u0431\u0430\u0441\u043d\u0430',
        ],
    },
    'gagauzia': {
        'name': 'Gagauzia (Second Front)',
        'flag': '\U0001f7e8',
        'icon': '\U0001f3f4',
        'color': '#eab308',
        'role': 'Comrat, Gutul, autonomy pressure, pro-Russian south',
        'description': (
            'The autonomous, pro-Russian, Turkic-Christian region in the south -- '
            'a second internal pressure point Moscow cultivates. Governor Evghenia '
            'Gutul (Shor-aligned) is a recurring flashpoint between Comrat and '
            'Chisinau. Watch: autonomy-expansion demands, Gutul legal/political '
            'moves, Comrat-Chisinau confrontation, pro-Russian mobilization framing. '
            'A live Gagauzia crisis lets Moscow open a second front without '
            'touching Transnistria.'
        ),
        'keywords': [
            'gagauzia', 'gagauz', 'comrat', 'evghenia gutul', 'gutul', 'gutsul',
            'gagauzia autonomy', 'gagauzia moldova', 'gagauz protest',
            'gagauzia russia', 'gagauzia referendum', 'bashkan',
            '\u0433\u0430\u0433\u0430\u0443\u0437\u0438\u044f',
            '\u043a\u043e\u043c\u0440\u0430\u0442', '\u0433\u0443\u0446\u0443\u043b',
        ],
    },
    'interference_shor': {
        'name': 'Interference (Shor Network)',
        'flag': '\U0001f5f3\ufe0f',
        'icon': '\U0001f4b0',
        'color': '#a855f7',
        'role': 'Shor network, vote-buying, disinformation, electoral capture',
        'description': (
            'The industrial-scale election-interference machine -- the frontline of '
            'capture-from-within. Fugitive oligarch Ilan Shor\'s network ran '
            'large-scale vote-buying and disinformation in the 2024 presidential '
            'race and EU referendum. This dimension measures INTERFERENCE TEMPO '
            'against the electoral/accession calendar: vote-buying reporting, '
            'disinformation surges, banned-party reconstitution, illicit-finance '
            'flows. Deniable actor -- the sensor measures the tempo of reported '
            'interference, never adjudicates a specific ballot.'
        ),
        'keywords': [
            'ilan shor', 'shor network', 'shor party', 'vote buying moldova',
            'moldova disinformation', 'moldova election interference',
            'moldova electoral fraud', 'victory bloc', 'pobeda moldova',
            'moldova vote rigging', 'moldova illicit finance', 'moldova propaganda',
            'moldova fake news', 'moldova influence operation',
            '\u0438\u043b\u0430\u043d \u0448\u043e\u0440', '\u0448\u043e\u0440',
            '\u043f\u043e\u0431\u0435\u0434\u0430',
            'cumparare voturi', 'dezinformare moldova',
        ],
    },
    'eu_accession': {
        'name': 'EU Accession (The Anchor)',
        'flag': '\U0001f1ea\U0001f1fa',
        'icon': '\u2693',
        'color': '#22c55e',
        'role': 'Accession milestones, EU support -- the anchoring green-line',
        'description': (
            'The ANCHORING side of the contest -- the one dimension where good news '
            'genuinely stabilizes. Moldova is an EU candidate (June 2022) with '
            'negotiations opened; each accession milestone is integration momentum '
            'that offsets capture-pressure, and each is also a trigger for Russian '
            'counter-pressure. INVERTED polarity: accession progress reads as '
            'DE-ESCALATION. Watch: cluster openings, EU financial/energy support, '
            'reform benchmarks met, membership-timeline signals, Romania/EU '
            'solidarity.'
        ),
        'keywords': [
            'moldova eu accession', 'moldova european union', 'moldova eu candidate',
            'moldova eu membership', 'moldova accession negotiations',
            'moldova eu reform', 'moldova eu support', 'moldova brussels',
            'moldova eu funding', 'moldova enlargement', 'moldova eu cluster',
            'moldova romania eu', 'moldova european integration',
            'aderare ue moldova', 'integrare europeana moldova',
            '\u0435\u0432\u0440\u043e\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f \u043c\u043e\u043b\u0434\u043e\u0432\u0430',
        ],
    },
    'energy_complex': {
        'name': 'Energy Complex (Display)',
        'flag': '\u26a1',
        'icon': '\U0001f6e2\ufe0f',
        'color': '#64748b',
        'role': 'Gas/electricity dependency -- DISPLAY-ONLY, convergence-gated',
        'description': (
            'The energy dependency that is Moldova\'s most reliable destabilizer -- '
            'the tariff->inflation->protest transmission belt. DISPLAY-ONLY here: '
            'like Kazakhstan\'s commodity complex, energy pressure is structural '
            '(Moldova is an acute importer every day of the year), so it never '
            'scores alone. Its analytical weight arrives through the interpreter\'s '
            'CONVERGENCE GATE -- energy stress counts only when it co-occurs with a '
            'live pressure vector (a Transnistria move, an interference spike, an '
            'accession milestone under attack).'
        ),
        'keywords': [
            'moldova energy', 'moldova gas', 'moldova electricity', 'moldova blackout',
            'moldova tariff', 'moldova power', 'moldova heating', 'moldova winter',
            'moldova energy crisis', 'moldova gas price', 'moldova energy security',
            'moldova romania electricity', 'moldova energy diversification',
            'criza energetica moldova', 'tarife moldova',
        ],
    },
}


# ============================================================
# GDELT QUERIES
# ============================================================

GDELT_QUERIES = {
    'eng': [
        '"moldova" AND ("sandu" OR "chisinau" OR "government")',
        '"moldova" AND ("russia" OR "gazprom" OR "interference")',
        '"moldova" AND ("transnistria" OR "tiraspol" OR "cobasna")',
        '"moldova" AND ("gagauzia" OR "comrat" OR "gutul")',
        '"moldova" AND ("shor" OR "vote buying" OR "disinformation")',
        '"moldova" AND ("eu accession" OR "european union" OR "candidate")',
        '"moldova" AND ("energy" OR "gas" OR "electricity" OR "blackout")',
        '"moldova" AND ("election" OR "referendum" OR "protest")',
    ],
    'rus': [
        '"\u043c\u043e\u043b\u0434\u043e\u0432\u0430" AND ("\u0441\u0430\u043d\u0434\u0443" OR "\u043a\u0438\u0448\u0438\u043d\u0451\u0432")',
        '"\u043c\u043e\u043b\u0434\u043e\u0432\u0430" AND ("\u043f\u0440\u0438\u0434\u043d\u0435\u0441\u0442\u0440\u043e\u0432\u044c\u0435" OR "\u0433\u0430\u0433\u0430\u0443\u0437\u0438\u044f")',
        '"\u043c\u043e\u043b\u0434\u043e\u0432\u0430" AND ("\u0440\u043e\u0441\u0441\u0438\u044f" OR "\u0448\u043e\u0440" OR "\u0433\u0430\u0437")',
    ],
    'ron': [
        '"moldova" AND ("sandu" OR "aderare" OR "transnistria")',
        '"moldova" AND ("ingerinta" OR "gagauzia" OR "energetic")',
    ],
}


# ============================================================
# TOPIC FILTER (Reddit gate)
# ============================================================

MOLDOVA_TOPIC_KEYWORDS = [
    'moldova', 'moldovan', 'chisinau', 'sandu', 'transnistria', 'tiraspol',
    'gagauzia', 'comrat', 'shor', 'gutul', 'cobasna', 'moldovagaz',
    'pridnestrovie', 'dniester', 'cuciurgan',
    '\u043c\u043e\u043b\u0434\u043e\u0432\u0430', '\u043a\u0438\u0448\u0438\u043d\u0451\u0432',
    '\u043f\u0440\u0438\u0434\u043d\u0435\u0441\u0442\u0440\u043e\u0432\u044c\u0435',
]


# ============================================================
# RSS FEEDS (per-feed soft-fail; verify in boot logs on first deploy)
# ============================================================
# VERIFY-IN-LOGS: any feed logging 0 items across two scans needs its URL fixed.

RSS_FEEDS = [
    {'url': 'https://www.intellinews.com/feed',          'name': 'bne IntelliNews',   'weight': 0.85},
    {'url': 'https://balkaninsight.com/feed/',           'name': 'Balkan Insight',    'weight': 0.85},
    {'url': 'https://emerging-europe.com/feed/',         'name': 'Emerging Europe',   'weight': 0.80},
    {'url': 'https://www.rferl.org/api/zrqiteuuir',      'name': 'RFE/RL Moldova',    'weight': 0.85},
    {'url': 'https://newsmaker.md/feed/',                'name': 'NewsMaker',         'weight': 0.80},
    {'url': 'https://www.zdg.md/feed/',                  'name': 'Ziarul de Garda',   'weight': 0.80},
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
        print(f'[Moldova Tracker] Redis get error: {str(e)[:120]}')
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
        print(f'[Moldova Tracker] Redis set error: {str(e)[:120]}')
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
        print(f'[Moldova Tracker] Redis lpush error: {str(e)[:120]}')
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
        print(f'[Moldova Tracker] Scan lock error (proceeding): {str(e)[:120]}')
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
        print(f'[Moldova RSS] {source_name}: {len(out)} items')
    except Exception as e:
        print(f'[Moldova RSS] {source_name}: {str(e)[:120]}')
    return out


def _fetch_gdelt(query, language='eng', days=7, max_records=25):
    params = {'query': query, 'mode': 'artlist', 'maxrecords': max_records,
              'format': 'json', 'sort': 'datedesc', 'timespan': f'{days*24}h',
              'sourcelang': language}
    try:
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=(5, 15))
        if resp.status_code == 429:
            print('[Moldova GDELT] Rate limited (429) -- backing off')
            return []
        if resp.status_code != 200:
            print(f'[Moldova GDELT] HTTP {resp.status_code}')
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
        print(f'[Moldova GDELT] {str(e)[:120]}')
        return []


def _fetch_newsapi(query='moldova', max_records=40):
    if not NEWSAPI_KEY:
        return []
    try:
        r = requests.get(NEWSAPI_BASE_URL,
                         params={'q': query, 'pageSize': max_records, 'language': 'en',
                                 'sortBy': 'publishedAt', 'apiKey': NEWSAPI_KEY},
                         timeout=10)
        if r.status_code != 200:
            print(f'[Moldova NewsAPI] HTTP {r.status_code}')
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
        print(f'[Moldova NewsAPI] {str(e)[:120]}')
        return []


def _fetch_brave(query='moldova russia transnistria', max_records=20):
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
        print(f'[Moldova Brave] {str(e)[:120]}')
        return []


def _fetch_reddit():
    """Browser-like UA -- generic UAs get silently 403'd by Reddit."""
    out = []
    subs = ['moldova', 'europe', 'geopolitics', 'worldnews', 'CredibleDefense']
    ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    total = 0
    for sub in subs:
        try:
            r = requests.get(f'https://www.reddit.com/r/{sub}/new.json?limit=25',
                             headers={'User-Agent': ua, 'Accept': 'application/json'},
                             timeout=8)
            if r.status_code != 200:
                print(f'[Moldova Reddit] r/{sub}: HTTP {r.status_code}')
                continue
            for child in (r.json().get('data', {}).get('children') or []):
                p = child.get('data', {})
                title = (p.get('title') or '').lower()
                if not any(kw in title for kw in MOLDOVA_TOPIC_KEYWORDS):
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
            print(f'[Moldova Reddit] r/{sub}: {str(e)[:120]}')
        time.sleep(0.3)
    print(f'[Moldova Reddit] Total: {total} posts across {len(subs)} subreddits')
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
        articles.extend(_fetch_newsapi('moldova', max_records=40))
    if len(articles) < 15:
        articles.extend(_fetch_brave('moldova russia transnistria', max_records=20))
    seen, unique = set(), []
    for a in articles:
        u = a.get('url')
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    return unique


# ============================================================
# COMMODITY READ (server-side, in-process -- never an HTTP self-call)
# ============================================================

def _read_commodity():
    """Read the commodity proxy IN-PROCESS. The proxy owns the absence-honest
    cascade; we inherit it. The interpreter CONVERGENCE-GATES this -- Moldova's
    energy pressure is structural (acute importer every day), so it never feeds
    the score alone, only when it co-occurs with a live pressure vector."""
    if not COMMODITY_PROXY_AVAILABLE:
        return None
    try:
        data = get_commodity_data('moldova')
        if not isinstance(data, dict):
            return None
        print(f"[Moldova Tracker] Commodity: pressure="
              f"{data.get('commodity_pressure', 0)} alert={data.get('alert_level')} "
              f"commodities={len(data.get('commodity_summaries') or [])} "
              f"stale={data.get('stale', False)}")
        return data
    except Exception as e:
        print(f'[Moldova Tracker] Commodity read failed: {str(e)[:120]}')
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
    """Baseline +8: an inbound-target state under sustained hybrid pressure, not
    a hot war theatre. energy_complex carries weight 0.0 -- DISPLAY-ONLY, scored
    only through the interpreter convergence gate (Moldova is an acute energy
    importer every day of the year; scoring it directly would pin the theatre
    permanently high). eu_accession is the ANCHOR: its articles are counted for
    visibility but weighted low -- accession momentum is measured as a
    de-escalatory read by the interpreter, not as theatre pressure."""
    BASELINE = 8
    actor_weights = {
        'moldovan_government': 0.60,
        'russia_inbound':      0.95,
        'transnistria':        1.00,   # the unfreeze risk carries the most weight
        'gagauzia':            0.70,
        'interference_shor':   0.90,
        'eu_accession':        0.30,   # anchor -- low theatre weight (de-esc read lives in interpreter)
        'energy_complex':      0.00,   # DISPLAY-ONLY -- see convergence gate
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
# SPOKE EMISSION
# ============================================================

_SPOKE_LEVEL_BY_ALERT = {'normal': 1, 'elevated': 2, 'high': 3, 'critical': 4}


def _write_canonical_spoke_fingerprint(result, fingerprints):
    """crosstheater:moldova:fingerprint -- the Russia wheel's reader is deployed
    and listening. node_class = inbound_target (Russia acts UPON Moldova; same
    taxonomy tier as Greenland/Arctic ring and the US influence slice).

    SURFACE-ONLY: node_class documents the taxonomy tier; no polarity is wired
    into any score. That remains a wheel scoping decision, not plumbing. The
    spoke carries the pressure-vs-anchor balance so the GPI Russia recompute can
    read Moldova as an inbound-target data point in the network read."""
    alert = result.get('alert_level', 'normal')
    fp = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'moldova',
        'node_class':  'inbound_target',
        'level':       _SPOKE_LEVEL_BY_ALERT.get(alert, 1),
        'score':       result.get('theatre_score', 0),
        'alert_level': alert,
        # Moldova-specific slices (the pressure-vs-anchor balance)
        'energy_lever':          fingerprints.get('energy_lever', {}),
        'interference_tempo':    fingerprints.get('interference_tempo', {}),
        'transnistria_watch':    fingerprints.get('transnistria_watch', {}),
        'gagauzia_watch':        fingerprints.get('gagauzia_watch', {}),
        'accession_momentum':    fingerprints.get('accession_momentum', {}),
        'commodity_convergence': fingerprints.get('commodity_convergence', {}),
    }
    try:
        _redis_set(SPOKE_KEY_CANONICAL, fp)
        print('[Moldova Tracker] Canonical spoke fingerprint written '
              '(crosstheater:moldova:fingerprint, node_class=inbound_target)')
    except Exception as e:
        print(f'[Moldova Tracker] Canonical fingerprint write failed: {e}')


# ============================================================
# MAIN SCAN
# ============================================================

def run_moldova_rhetoric_scan(force=False):
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

    print('[Moldova Tracker] Starting fresh scan...')
    started = time.time()

    articles = _fetch_all_articles()
    print(f'[Moldova Tracker] Articles: {len(articles)}')
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
            'display_only': key == 'energy_complex',
        }

    score = _compute_theatre_score(by_actor, articles)
    alert = _alert_level_from_score(score)

    articles_en = [a for a in articles if a.get('language', 'eng') in ('eng', None)]
    articles_ru = [a for a in articles if a.get('language') == 'rus']
    articles_ro = [a for a in articles if a.get('language') == 'ron']

    scan_data = {
        'articles_en':     articles_en,
        'articles_ru':     articles_ru,
        'articles_ro':     articles_ro,
        'reddit_signals':  reddit_signals,
        'by_actor':        by_actor,
        'actor_summaries': actor_summaries,
        'theatre_score':   score,
        'alert_level':     alert,
        'commodity_data':  commodity_data,
    }

    interpretation = interpret_signals(scan_data)

    # -- Structural-breach band floor. theatre_score is article VOLUME, so a
    #    BREACHED Transnistria/energy-cutoff/interference line can sit at
    #    'normal' on volume alone and get buried in the GPI rollup. Floor the
    #    band so a genuine breach reads at least 'high' ('critical' when two or
    #    more stack). Floors only, never lowers.
    _rl = (interpretation.get('red_lines') or {}).get('triggered') or []
    _structural = sum(1 for r in _rl if r.get('status') == 'BREACHED'
                      and r.get('id') in ('transnistria_mobilization', 'energy_cutoff',
                                          'election_capture', 'gagauzia_escalation'))
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
        print(f'[Moldova Tracker] Structural-breach floor applied: '
              f'{_structural} breach(es) -> band {alert}, score {score}')

    # -- Off-ramp / anchoring maturity (shared schema with Iran/Ukraine/Armenia/
    #    Kazakhstan). For Moldova the "green lines" are ACCESSION ANCHORING
    #    momentum -- the de-escalatory side of the contest.
    _green = interpretation.get('green_lines') or {}
    _green_active = _green.get('active_count', 0)
    _offramp = ('signed' if _green_active >= 3
                else 'framework' if _green_active >= 1 else 'none')

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'moldova',
        'flag':              '\U0001f1f2\U0001f1e9',
        'display_name':      'Moldova',
        'tracker_name':      'Moldova Capture-vs-Anchor Tracker',
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
        'articles_ru':     articles_ru,
        'articles_ro':     articles_ro,
        'actor_summaries': actor_summaries,
        'so_what':         interpretation.get('so_what'),
        'top_signals':     interpretation.get('top_signals') or [],
        'red_lines':       interpretation.get('red_lines'),
        'green_lines':     interpretation.get('green_lines'),
        # -- Moldova vector payloads --
        'energy_lever':          interpretation.get('energy_lever'),
        'interference_tempo':    interpretation.get('interference_tempo'),
        'transnistria_watch':    interpretation.get('transnistria_watch'),
        'gagauzia_watch':        interpretation.get('gagauzia_watch'),
        'accession_momentum':    interpretation.get('accession_momentum'),
        'capture_vs_anchor':     interpretation.get('capture_vs_anchor'),
        'commodity_convergence': interpretation.get('commodity_convergence'),
        'election_clock':        interpretation.get('election_clock'),
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

    # Tempo emit (corpus-health denominator so the engine suppresses quiet calls
    # when feeds die instead of hallucinating menace from an outage).
    if TEMPO_AVAILABLE:
        try:
            emit_tempo_sample('moldova', corpus_size=len(articles),
                              signal_count=len(result['top_signals']))
        except Exception as e:
            print(f'[Moldova Tracker] Tempo emit failed: {str(e)[:100]}')

    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Moldova Tracker] Scan complete: score={score}, alert={alert}, '
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
                    run_moldova_rhetoric_scan(force=True)
            else:
                print('[Moldova Tracker] Another worker owns the scan window -- skipping')
        except Exception as e:
            print(f'[Moldova Tracker] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Moldova Tracker] Background refresh thread started '
          '(6h cycle, cross-worker lock)')


# ============================================================
# ENDPOINTS
# ============================================================

def register_moldova_rhetoric_endpoints(app):

    @app.route('/api/rhetoric/moldova', methods=['GET'])
    def api_rhetoric_moldova():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            return jsonify(run_moldova_rhetoric_scan(force=force))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200],
                            'theatre': 'moldova'}), 500

    @app.route('/api/rhetoric/moldova/summary', methods=['GET'])
    def api_rhetoric_moldova_summary():
        try:
            d = run_moldova_rhetoric_scan(force=False)
            return jsonify({
                'success':          True,
                'theatre':          'moldova',
                'flag':             '\U0001f1f2\U0001f1e9',
                'display_name':     'Moldova',
                'theatre_score':    d.get('theatre_score', 0),
                'alert_level':      d.get('alert_level', 'normal'),
                'top_signals':      (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'capture_vs_anchor': (d.get('capture_vs_anchor') or {}).get('balance'),
                'cached_at':        d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/moldova/history', methods=['GET'])
    def api_rhetoric_moldova_history():
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
            return jsonify({'success': True, 'theatre': 'moldova',
                            'count': len(history), 'history': history})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500

    print('[Moldova Tracker] Endpoints registered: /api/rhetoric/moldova, '
          '/summary, /history')
