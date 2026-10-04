"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — UKRAINE RHETORIC TRACKER
  v1.1.0 (Oct 4 2026)
═══════════════════════════════════════════════════════════════════════

v1.1.0 (Oct 4 2026) — SOURCE DISCIPLINE PASS
  1. GDELT now routes through gdelt_gateway. This tracker was calling
     api.gdeltproject.org directly with a 5s read timeout and no circuit
     breaker, alongside five other trackers doing the same from the same
     process on the same IP. A live log showed FOURTEEN consecutive
     "Read timed out (read timeout=5)" lines from this file alone -- 70
     seconds spent retrieving nothing, while the gateway sitting in the
     same process already knew GDELT was unreachable.
  2. Reddit User-Agent is now honest. The previous string impersonated
     Chrome 124 on macOS. In the same log, every one of seven subreddits
     returned 403 to this file, while app.py -- which carries a truthful
     AsifahAnalytics UA -- got 429s and real posts from the same IP in the
     same minute. The spoof was not helping; it was the thing being caught.
  3. Absence-honest sensing. A scan that retrieves nothing now says so in
     result['sensing'] instead of returning a baseline score that reads as
     a quiet war. NOTE: the score itself still floors at BASELINE when
     blind -- see the comment on _compute_theatre_score.

Multi-actor rhetoric tracker for Ukraine. Aggregates signals across:
  - RSS (Kyiv Independent, Ukrainska Pravda EN, Ukrinform, ISW, Kiel)
  - GDELT multi-language queries (English + Ukrainian + Russian)
  - NewsAPI fallback
  - Brave Search tertiary fallback
  - Telegram channels (Ukraine-specific subset of Europe channels)
  - Bluesky (Zelensky, Ukraine MFA, OSINT defenders, Wartranslated)
  - Reddit (/r/ukraine, /r/credibledefense, /r/europe, /r/ukrainewarvideoreport)

Calls ukraine_signal_interpreter.interpret_signals() for analytical layer.

Writes Redis cache key 'rhetoric:ukraine:latest'.

ACTOR FRAMEWORK (7 actors):
  - ukrainian_government
  - ukrainian_armed_forces
  - russian_forces_in_ukraine
  - us_government                  (own actor — aid pipeline decisive)
  - nato_western_support           (Europe + UK + non-US Western)
  - defense_industrial_base        (drone advisor exports SUB-VECTOR)
  - occupied_territories_signals

ENDPOINTS:
  GET /api/rhetoric/ukraine
  GET /api/rhetoric/ukraine/summary
  GET /api/rhetoric/ukraine/history
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
    from telegram_signals_europe import fetch_ukraine_telegram_signals
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print('[Ukraine Rhetoric] Telegram signals not available')

try:
    from bluesky_signals_europe import fetch_ukraine_bluesky_signals
    BLUESKY_AVAILABLE = True
except ImportError:
    BLUESKY_AVAILABLE = False
    print('[Ukraine Rhetoric] Bluesky signals not available')

from ukraine_signal_interpreter import interpret_signals

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

REDIS_KEY_LATEST     = 'rhetoric:ukraine:latest'
REDIS_KEY_HISTORY    = 'rhetoric:ukraine:history'
REFRESH_INTERVAL_SEC = 6 * 3600

TRACKER_VERSION = '1.1.0'

# Honest identification. See v1.1.0 note 2 in the module docstring: the
# browser impersonation this replaces was earning 403s, not avoiding them.
TRACKER_USER_AGENT = (f'AsifahAnalytics-Europe-Ukraine/{TRACKER_VERSION} '
                      f'(OSINT monitoring tool; +https://asifahanalytics.com)')
REDDIT_USER_AGENT = TRACKER_USER_AGENT

# GDELT goes through the shared gateway: one semaphore, paced, escalating
# backoff, circuit breaker. Soft import so a backend without the module
# degrades to the direct path instead of failing to start.
try:
    from gdelt_gateway import gdelt_fetch_probed as _gw_fetch_probed
    GDELT_GATEWAY = True
except ImportError:
    GDELT_GATEWAY = False
    print('[Ukraine GDELT] gdelt_gateway unavailable -- direct calls (unpaced)')

_scan_lock = threading.Lock()


# ============================================================
# RSS FEEDS
# ============================================================
RSS_FEEDS = [
    # Ukrainian press
    {'name': 'Kyiv Independent',         'url': 'https://kyivindependent.com/feed/',           'weight': 0.95},
    {'name': 'Ukrainska Pravda (EN)',    'url': 'https://www.pravda.com.ua/eng/rss/view_news/', 'weight': 0.90},
    {'name': 'Ukrinform',                'url': 'https://www.ukrinform.net/rss/block-lastnews', 'weight': 0.90},
    # Defense / OSINT
    {'name': 'ISW',                      'url': 'https://www.understandingwar.org/rss.xml',     'weight': 0.95},
    {'name': 'War on the Rocks',         'url': 'https://warontherocks.com/feed/',              'weight': 0.85},
    {'name': 'USNI News',                'url': 'https://news.usni.org/feed',                   'weight': 0.85},
    # Investigative / Russia-focused
    {'name': 'Meduza (English)',         'url': 'https://meduza.io/rss/en/all',                 'weight': 0.90},
    {'name': 'Bellingcat',               'url': 'https://www.bellingcat.com/feed/',             'weight': 0.95},
    # International
    {'name': 'Reuters World',            'url': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',  'weight': 0.90},
    {'name': 'Politico Europe',          'url': 'https://www.politico.eu/feed/',                'weight': 0.85},
]


# ============================================================
# ACTORS (7 actors per analytical plan)
# ============================================================
ACTORS = {
    'ukrainian_government': {
        'name': 'Ukrainian Government',
        'flag': '🇺🇦',
        'icon': '🏛️',
        'color': '#0ea5e9',
        'role': 'Office of the President, MFA, Cabinet, Verkhovna Rada',
        'description': (
            'Zelensky office, Yermak (chief of staff), Kuleba/MFA, Cabinet '
            'of Ministers, Verkhovna Rada (parliament). Watch for: '
            'diplomatic posture, ceasefire signals, mobilization legislation, '
            'sanctions advocacy, reconstruction frameworks.'
        ),
        'keywords': [
            'zelensky', 'volodymyr zelensky', 'zelenskyy',
            'office of the president ukraine',
            'yermak', 'andriy yermak', 'ukrainian mfa', 'kuleba',
            'sybiha', 'andrii sybiha', 'ukrainian government',
            'cabinet of ministers ukraine', 'verkhovna rada',
            'shmyhal', 'denys shmyhal',
            'kyiv government', 'ukrainian presidency',
            # ── v1.1 (May 24 2026) — Pre-strike warning / intel signaling ──
            # Pattern: Zelensky receives intel from US/UK partners about
            # imminent Russian missile strike, publicly warns Ukrainian
            # citizens hours before. Most recent: May 23 2026 Oreshnik
            # warning followed by mass strike on Kyiv overnight.
            'zelensky warns', 'zelensky warning', 'zelensky intelligence',
            'zelensky predicts', 'zelensky pre-strike',
            'ukrainian intelligence indicates russia preparing',
            'ukraine intel russia preparing', 'kyiv warns of strike',
            'ukraine air defense preparing', 'ukraine readiness alert',
            'kyiv pre-strike warning', 'us embassy kyiv security alert',
            'embassy kyiv shelter alert', 'embassy kyiv warns',
            'значущий повітряний удар', 'попередження про обстріл',
            # ── v1.1 — Ceasefire / diplomatic trending (early signals) ──
            'zelensky open to talks', 'zelensky negotiations',
            'zelensky ceasefire', 'zelensky peace deal',
            'zelensky willing to negotiate', 'kyiv open to talks',
            'ukraine willing negotiations', 'ukraine accepts talks',
            'ukraine peace proposal', 'ukraine ceasefire proposal',
            'ukraine 14-point plan', 'ukraine peace plan',
            'zelensky envoy', 'ukrainian envoy talks',
            'офис президента', 'верховная рада',
        ],
    },
    'ukrainian_armed_forces': {
        'name': 'Ukrainian Armed Forces',
        'flag': '🪖',
        'icon': '⚔️',
        'color': '#0891b2',
        'role': 'AFU General Staff, theatre commands, GUR, SBU operations',
        'description': (
            'Armed Forces of Ukraine General Staff, Syrskyi (Cmdr-in-Chief), '
            'theatre commands, GUR (military intelligence) operations, SBU '
            'sabotage. Watch for: counter-offensive language, salient defense, '
            'GUR strikes deep in Russia, ATACMS / Storm Shadow employment.'
        ),
        'keywords': [
            'syrskyi', 'oleksandr syrskyi', 'afu general staff',
            'ukrainian armed forces', 'ukrainian military',
            'ukrainian army', 'ukrainian forces',
            'gur', 'ukrainian military intelligence', 'budanov',
            'kyrylo budanov', 'sbu', 'ukrainian special forces',
            'ukrainian counter-offensive', 'ukrainian operation',
            'atacms strike', 'storm shadow ukraine',
            # -- Ukrainian deep-strike / long-range campaign (Jun 2026) --
            # The offensive tempo: drone/missile strikes on Russian energy,
            # Crimea, and Black Sea targets -- headline war activity the
            # AFU-command keywords alone were missing.
            'ukrainian drone strike', 'ukraine deep strike',
            'ukraine long-range strike', 'ukraine strikes russian',
            'ukrainian drones russia', 'ukraine targets russian energy',
            'russian refinery strike', 'russian oil depot',
            'russian energy strike', 'crimea strike', 'crimea bridge',
            'kerch bridge', 'ukraine hits crimea', 'ukraine strikes crimea',
            'black sea fleet', 'naval drone', 'sea drone', 'magura',
            'novorossiysk', 'temryuk', 'ukraine sabotage russia',
            'drone strike russia', 'ukrainian long-range drones',
            # -- v1.2 (Jun 18 2026): Ukraine -> Russia OUTBOUND (Moscow / capital / refineries) --
            # Mirror of the inbound Kyiv coverage. Strike-directional only (NOT bare
            # 'moscow') so diplomatic 'Moscow says...' stories don't mis-credit the AFU.
            'barrage on moscow', 'drone barrage on moscow', 'drone attack on moscow',
            'attack on moscow', 'strike on moscow', 'strikes on moscow',
            'drones on moscow', 'moscow drone attack', 'moscow under attack',
            'attack on the russian capital', 'strike on the russian capital',
            'on the russian capital', 'russian capital attack', 'drones russian capital',
            'ukraine strikes moscow', 'ukrainian drones moscow', 'ukrainian drone barrage',
            'largest drone attack', 'biggest drone attack', 'record drone attack',
            'moscow refinery', 'moscow oil refinery', 'russian refinery ablaze',
            'russian refinery fire', 'struck russian refinery', 'moscow airports closed',
            'moscow airport closed', 'airports closed moscow',
            'всу', 'генштаб украины', 'буданов',
        ],
    },
    'russian_forces_in_ukraine': {
        'name': 'Russian Forces in Ukraine',
        'flag': '🇷🇺',
        'icon': '💥',
        'color': '#dc2626',
        'role': 'Russian theatre forces, MoD operations, Shahed/missile campaigns',
        'description': (
            'Russian forces operating in / against Ukraine. Watch for: '
            'Shahed swarms, cruise missile salvos, frontline advances, '
            'glide bomb employment, infrastructure strike campaigns, '
            'Tornado-S deployment.'
        ),
        'keywords': [
            'russian forces ukraine', 'russian troops ukraine',
            'russian advance', 'russian offensive ukraine',
            'shahed', 'shahed swarm', 'iranian-made drones',
            # v1.2.0 HEBREW -- NARROW SCOPE (Aug 2026). abualiexpress was added
            # to UKRAINE_CHANNELS for exactly one signal: the Iranian materiel
            # track into Russia, which Israeli sources often report first.
            # These terms are scoped to that axis and nothing else. Hebrew is
            # not a primary language of Ukraine-war reporting and broadening
            # this would bleed ME content into the Ukraine score.
            'שאהד',                     # Shahed
            'רחפנים איראניים',           # "Iranian drones"
            'רחפנים איראניים לרוסיה',    # "Iranian drones to Russia"
            'טילים איראניים לרוסיה',     # "Iranian missiles to Russia"
            'איראן מספקת לרוסיה',        # "Iran supplies Russia"
            'סיוע איראני לרוסיה',        # "Iranian assistance to Russia"
            'kalibr strike', 'kalibr missile', 'kinzhal strike',
            'tornado-s', 'glide bomb', 'fab-1500',
            'russian missile strike ukraine', 'russian shelling',
            # ── v1.1 (May 24 2026) — Oreshnik / hypersonic / IRBM coverage ──
            # Zelensky warned May 23 2026 of imminent Oreshnik strike;
            # massive combined missile + drone attack hit Kyiv overnight.
            'oreshnik', 'oreshnik missile', 'oreshnik hypersonic',
            'oreshnik strike', 'russia oreshnik launch',
            'hypersonic missile ukraine', 'hypersonic ballistic missile',
            'medium-range ballistic missile', 'irbm russia',
            'intermediate-range missile russia', 'russia new missile',
            'russia new ballistic missile', 'russia novel weapon',
            'russia experimental missile', 'kedr missile',
            # Combined / mass strike patterns
            'mass missile attack ukraine', 'combined missile drone attack',
            'massive russian strike', 'combined strike ukraine',
            'wave of missiles ukraine', 'salvo attack ukraine',
            'mass strike kyiv', '700 drones ukraine', 'drone barrage',
            'overnight strike kyiv', 'russia largest attack',
            'russia largest strike',
            # Polish/allied air defense scramble (signals scale)
            'polish jets scramble', 'nato jets scramble',
            'allied fighters scrambled', 'polish air force scramble',
            'российские войска украина', 'шахед',
            'орешник', 'гиперзвуковая ракета',
            'новая ракета россия',
        ],
    },
    'us_government': {
        'name': 'United States Government',
        'flag': '🇺🇸',
        'icon': '🏛️',
        'color': '#1e40af',
        'role': 'Trump admin, State Dept, DoD, Congress — aid pipeline',
        'description': (
            'US government posture toward Ukraine — Trump administration '
            'position, State Department signals, DoD weapons authorizations, '
            'Congressional aid debate. The decisive variable for Ukrainian '
            'war sustainability.'
        ),
        'keywords': [
            'trump ukraine', 'trump zelensky', 'witkoff',
            'kushner', 'jared kushner', 'us envoys', 'us envoys ukraine',
            'peace efforts', 'positive call', 'zelensky us envoys',
            'us aid ukraine', 'us military aid ukraine',
            'congressional aid ukraine', 'state department ukraine',
            'pentagon ukraine', 'us weapons ukraine',
            'patriot ukraine', 'atacms ukraine authorization',
            'us ukraine policy', 'biden ukraine', 'rubio ukraine',
            'us secretary of state ukraine', 'us defense secretary ukraine',
            'трамп украина', 'сша украина помощь',
        ],
    },
    'nato_western_support': {
        'name': 'NATO / Western Support',
        'flag': '🇪🇺',
        'icon': '🛡️',
        'color': '#3b82f6',
        'role': 'EU, UK, Germany, France, Poland, Nordics — non-US Western',
        'description': (
            'Western support outside the US — EU peace facility, UK weapons '
            'aid, German Leopard/Patriot deliveries, French SCALP, Polish '
            'logistics hub, Nordic ammunition surge. Backfill capacity for '
            'US gaps + independent commitment trajectory.'
        ),
        'keywords': [
            'nato ukraine', 'eu ukraine aid', 'european aid ukraine',
            'germany ukraine aid', 'leopard ukraine', 'patriot delivery germany',
            'uk ukraine', 'storm shadow uk', 'british aid ukraine',
            'france ukraine', 'scalp delivery', 'macron ukraine',
            'poland ukraine', 'polish aid ukraine',
            'finland ukraine', 'sweden ukraine', 'norway ukraine',
            'eu peace facility', 'eu summit ukraine',
            'rheinmetall expansion', 'european defense fund',
        ],
    },
    'defense_industrial_base': {
        'name': 'Defense Industrial Base',
        'flag': '🏭',
        'icon': '🚁',
        'color': '#a16207',
        'role': 'Ukrainian DIB + drone advisor exports to GCC (sub-vector)',
        'description': (
            'Ukrainian defense industrial base — domestic drone production '
            '(Bayraktar localization, Magura, Bober, Punisher), missile '
            'programs, Western weapons integration, AND drone advisor exports '
            'to GCC (UAE, Saudi Arabia, Israel during Iran war). Unique '
            'leverage vector — defense knowledge as strategic export.'
        ),
        'keywords': [
            # Ukrainian DIB
            'ukrainian defense industry', 'ukroboronprom',
            'magura', 'magura naval drone', 'bober drone', 'punisher drone',
            'ukrainian drone production', 'ukrainian missile program',
            'neptune missile', 'long neptune',
            'shahed knockoff ukraine', 'rampage ukraine',
            # Drone advisor exports (the unique vector)
            'ukrainian drone advisors', 'ukrainian drone instructors',
            'ukraine drone training abroad', 'ukrainian advisors uae',
            'ukrainian advisors saudi', 'kyiv drone diplomacy',
            'ukraine drone export', 'ukrainian drone partnership gcc',
            'ukraine israel drone', 'ukraine drone gcc',
            # Western integration
            'f-16 ukraine', 'mirage 2000 ukraine', 'leopard ukraine',
            'himars ukraine',
        ],
    },
    'occupied_territories_signals': {
        'name': 'Occupied Territories Signals',
        'flag': '🏚️',
        'icon': '⚖️',
        'color': '#7c2d12',
        'role': 'Mariupol/Crimea/Donbas: atrocity, deportation, partisan',
        'description': (
            'Russian-occupied territories — atrocity disclosures, mass '
            'deportation events, filtration camp expansion, Russification '
            'campaigns, partisan activity, ICC indictments. Drives Western '
            'political pressure dynamics.'
        ),
        'keywords': [
            'mariupol', 'azovstal', 'occupied territories ukraine',
            'occupied donbas', 'occupied crimea', 'occupied kherson',
            'filtration camp', 'forced deportation ukrainian',
            'children deported ukraine', 'forced russification',
            'ukrainian partisan', 'crimea partisan',
            'icc warrant putin', 'icc warrant lvova-belova',
            'mass grave ukraine', 'atrocity ukraine',
            'оккупированная территория украины', 'фильтрационный лагерь',
            # ── v1.3 (Jul 20 2026) — Crimea posture / Black Sea Fleet displacement ──
            # RUMINT sub-vector: Ukrainian-sourced reports (Atesh partisan recon,
            # leaked Russian garrison orders) of BSF command + military-family
            # relocation OUT of Sevastopol under the sustained strike campaign.
            # Consistent with sea-denial success; NOT a Russian concession signal.
            # Flagged UNVERIFIED in the crimea_posture scan block (interested sources).
            'black sea fleet evacuation', 'black sea fleet relocation',
            'sevastopol evacuation', 'crimea evacuation', 'evacuate crimea',
            'fleet command novorossiysk', 'fleet relocation novorossiysk',
            'bsf withdrawal', 'black sea fleet withdrawal', 'pinchuk sevastopol',
            'atesh', 'void group', 'crimea military families',
            'эвакуация севастополь', 'эвакуация крым', 'флот новороссийск',
            'евакуація крим', 'чорноморський флот евакуація',
            # ── v1.4 (Jul 21 2026) — occupied-Crimea-under-strain frame ──
            # The actor was blind to the strangulation/logistics story: the
            # strike campaign isolating occupied Crimea (fuel/power collapse),
            # grain extraction from occupied ports, and named occupied
            # geographies. These are occupied-territory PRESSURE signals — the
            # broad sensor read — distinct from the narrow BSF-displacement
            # RUMINT tripwire above (v1.3) and the crimea_posture scan block.
            # Occupied-Crimea distress reads as pressure on Russian control,
            # convergence-framed (not a prediction of collapse).
            'crimea fuel', 'crimea fuel crisis', 'crimea fuel shortage',
            'crimea power outage', 'crimea blackout', 'crimea energy crisis',
            'crimea isolated', 'crimea cut off', 'crimea supply',
            'crimea economy', 'occupied crimea economy',
            'feodosia', 'dzhankoi', 'saky', 'sevastopol occupied',
            'kerch', 'kerch strait', 'crimean bridge',
            'occupied port', 'occupied ukrainian port',
            'stolen grain', 'grain smuggling occupied', 'looted grain',
            'grain theft crimea', 'russian shadow fleet grain',
            'occupied melitopol', 'occupied berdiansk', 'occupied enerhodar',
            'zaporizhzhia nuclear plant occupied', 'znpp occupied',
            'оккупированный крым', 'крым топливо', 'крым блэкаут',
        ],
    },
}


# ============================================================
# GDELT QUERIES
# ============================================================
GDELT_QUERIES = {
    'eng': [
        '"ukraine" AND ("zelensky" OR "kyiv")',
        '"ukraine" AND ("frontline" OR "offensive" OR "advance")',
        '"ukraine" AND ("nato" OR "eu" OR "western aid")',
        '"ukraine" AND ("trump" OR "us aid" OR "congressional")',
        '"ukraine" AND ("drone" OR "shahed" OR "magura")',
        '"ukraine" AND ("ceasefire" OR "negotiation" OR "diplomatic")',
        '"ukrainian advisors" OR "ukrainian drone training"',
        # -- v1.2 (Jun 18 2026): OUTBOUND lane -- Ukraine striking Russia/Moscow --
        '"moscow" AND ("drone" OR "strike" OR "refinery" OR "attack")',
        '"ukraine" AND ("moscow" OR "russian refinery" OR "russian capital")',
        '"russian refinery" OR "moscow drone attack" OR "strike on moscow"',
    ],
    'ukr': [
        '"україна" AND ("зеленський" OR "київ")',
        '"україна" AND ("фронт" OR "наступ")',
    ],
    'rus': [
        '"украина" AND ("зеленский" OR "киев")',
        '"украина" AND ("сво" OR "наступление")',
    ],
}


# ============================================================
# TOPIC FILTER
# ============================================================
UKRAINE_TOPIC_KEYWORDS = [
    'ukraine', 'ukrainian', 'kyiv', 'kiev', 'zelensky', 'zelenskyy',
    'kharkiv', 'odesa', 'odessa', 'donbas', 'mariupol', 'crimea',
    'kherson', 'sumy', 'zaporizhzhia',
    # -- v1.2 (Jun 18 2026): outbound targets (specific; watch for noise) --
    'moscow', 'russian capital', 'russian refinery',
    'україна', 'украина', 'киев', 'київ',
]


# ============================================================
# REDIS HELPERS (canonical pattern, same as Belarus)
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
        print(f'[Ukraine Rhetoric] Redis get error: {str(e)[:120]}')
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
        print(f'[Ukraine Rhetoric] Redis set error: {str(e)[:120]}')
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
        print(f'[Ukraine Rhetoric] Redis lpush error: {str(e)[:120]}')
        return False


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
    """Fetch over requests FIRST so transport failures are visible.

    feedparser.parse(url) reports a 403, a 404, a dropped connection and a
    genuinely empty feed identically: zero entries. A dead feed then reads
    downstream as a quiet source.
    """
    out = []
    try:
        r = requests.get(url, headers={'User-Agent': TRACKER_USER_AGENT}, timeout=12)
        if r.status_code != 200:
            print(f'[Ukraine RSS] {source_name}: HTTP {r.status_code} -- feed not read')
            return out
        feed = feedparser.parse(r.content)
        if getattr(feed, 'bozo', 0) and not (feed.entries or []):
            print(f'[Ukraine RSS] {source_name}: unparseable feed '
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
            })
        print(f'[Ukraine RSS] {source_name}: {len(out)} items')
    except Exception as e:
        print(f'[Ukraine RSS] {source_name}: {type(e).__name__}: {str(e)[:110]}')
    return out


def _shape_gdelt(raw, language):
    """Gateway article dicts -> this tracker's article shape. Unchanged fields."""
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
    """
    Returns (articles, sensed).

    `sensed` is the absence-honest half: True only when GDELT actually
    answered. An empty list with sensed=True is a real zero; an empty list
    with sensed=False means we never got to look, and the caller must not
    score it as quiet.
    """
    if GDELT_GATEWAY:
        raw, probe = _gw_fetch_probed(query, language=language,
                                      timespan=f'{days*24}h',
                                      maxrecords=max_records,
                                      label=f'ukraine/{language}')
        return _shape_gdelt(raw, language), bool(probe.get('sensed'))

    # Fallback only: no gateway on this backend. Timeout raised from 5s --
    # GDELT routinely takes 10-20s under load, and a 5s ceiling guaranteed
    # failure exactly when the service was busiest.
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
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=(10, 25))
        if resp.status_code == 429:
            print('[Ukraine GDELT] Rate limited (429) -- backing off')
            return [], False
        if resp.status_code != 200:
            print(f'[Ukraine GDELT] HTTP {resp.status_code}')
            return [], False
        return _shape_gdelt(resp.json().get('articles') or [], language), True
    except Exception as e:
        print(f'[Ukraine GDELT] Query error: {str(e)[:120]}')
        return [], False


def _fetch_newsapi(query='ukraine', max_records=40):
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
            print(f'[Ukraine NewsAPI] HTTP {r.status_code}')
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
        print(f'[Ukraine NewsAPI] {str(e)[:120]}')
        return []


def _fetch_brave(query='ukraine war', max_records=20):
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
                'weight':      0.75,
            })
        return out
    except Exception as e:
        print(f'[Ukraine Brave] {str(e)[:120]}')
        return []


def _fetch_reddit():
    """
    Fetch Reddit posts for Ukraine topics. Returns (posts, probe).

    v1.1.0 (Oct 4 2026): the browser-impersonating UA is gone.

    The May 2026 note that justified it -- "Reddit blocks generic/scripted
    user agents" -- was a reasonable inference at the time and the October 4
    log contradicts it. Every one of these seven subreddits returned 403 to
    the spoofed UA, while app.py's REDDIT_USER_AGENT (a truthful
    AsifahAnalytics string) drew 429s and real posts from the same IP in the
    same scan cycle. Reddit now detects fake browser UAs from datacenter
    ranges; a request that lies badly fares worse than one that does not lie.

    If Reddit access matters enough to pay for, the real fix is a registered
    OAuth app with the canonical 'platform:app_id:version (by /u/<name>)'
    UA -- not a better disguise.
    """
    out = []
    subs = ['ukraine', 'CredibleDefense', 'LessCredibleDefence',
            'UkrainianConflict', 'ukrainewarvideoreport',
            'europe', 'geopolitics']
    ua = REDDIT_USER_AGENT
    probe = {'attempted': 0, 'ok': 0, 'blocked': 0, 'status': {}}
    found_total = 0
    for sub in subs:
        probe['attempted'] += 1
        try:
            url = f'https://www.reddit.com/r/{sub}/new.json?limit=25'
            r = requests.get(
                url,
                headers={'User-Agent': ua, 'Accept': 'application/json'},
                timeout=8
            )
            if r.status_code != 200:
                probe['blocked'] += 1
                probe['status'][sub] = r.status_code
                print(f'[Ukraine Reddit] r/{sub}: HTTP {r.status_code}')
                continue
            probe['ok'] += 1
            sub_count = 0
            for child in (r.json().get('data', {}).get('children') or []):
                p = child.get('data', {})
                title = (p.get('title') or '').lower()
                if not any(kw in title for kw in UKRAINE_TOPIC_KEYWORDS):
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
                sub_count += 1
            found_total += sub_count
            print(f'[Ukraine Reddit] r/{sub}: {sub_count} matching posts '
                  f'({len(r.json().get("data", {}).get("children") or [])} scanned)')
        except Exception as e:
            probe['blocked'] += 1
            probe['status'][sub] = type(e).__name__
            print(f'[Ukraine Reddit] r/{sub}: {str(e)[:120]}')
        time.sleep(0.3)
    if probe['ok'] == 0:
        print(f'[Ukraine Reddit] NOT SENSED -- 0 of {probe["attempted"]} subreddits '
              f'answered ({probe["status"]}). Missing data, not an absent conversation.')
    else:
        print(f'[Ukraine Reddit] Total: {found_total} posts from '
              f'{probe["ok"]}/{probe["attempted"]} subreddits')
    return out, probe


def _fetch_all_articles():
    """Returns (unique_articles, sensing).

    `sensing` records which source families actually answered, so a caller can
    tell an empty corpus from an unreachable one.
    """
    articles = []
    sensing = {
        'rss':     {'attempted': 0, 'ok': 0, 'empty': []},
        'gdelt':   {'attempted': 0, 'sensed': 0},
        'newsapi': {'attempted': 0, 'ok': 0},
        'brave':   {'attempted': 0, 'ok': 0},
    }

    for feed in RSS_FEEDS:
        sensing['rss']['attempted'] += 1
        got = _fetch_rss(feed['url'], feed['name'], feed['weight'])
        if got:
            sensing['rss']['ok'] += 1
        else:
            sensing['rss']['empty'].append(feed['name'])
        articles.extend(got)

    # No sleep here any more: the gateway serialises and paces every GDELT
    # call process-wide. A second delay on top of it was paying the toll twice.
    for lang, queries in GDELT_QUERIES.items():
        for q in queries:
            sensing['gdelt']['attempted'] += 1
            got, sensed = _fetch_gdelt(q, language=lang, days=7)
            if sensed:
                sensing['gdelt']['sensed'] += 1
            articles.extend(got)

    if len(articles) < 30:
        sensing['newsapi']['attempted'] += 1
        got = _fetch_newsapi('ukraine', max_records=40)
        if got:
            sensing['newsapi']['ok'] += 1
        articles.extend(got)

    if len(articles) < 15:
        sensing['brave']['attempted'] += 1
        got = _fetch_brave('ukraine war', max_records=20)
        if got:
            sensing['brave']['ok'] += 1
        articles.extend(got)

    seen, unique = set(), []
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
    # v1.1 (Jun 2026): also scan content + URL slug. Slugs encode the full
    # headline (hyphens -> spaces) -- critical for GDELT articles, which carry
    # an empty description.
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
    # v1.1 (Jun 2026): multi-actor co-crediting. Winner-take-all swallowed
    # cross-actor stories -- e.g. "Zelensky positive call with US envoys" went
    # 100% to ukrainian_government and the US Government card showed nothing.
    # Now: the best-match actor gets PRIMARY credit (counts toward theatre
    # score); any OTHER actor matching >= 2 keywords gets a CO-CREDIT copy
    # (visible on its card, flagged co_credit=True, EXCLUDED from theatre
    # score so nothing double-counts).
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
# THEATRE SCORE
# ============================================================

def _compute_theatre_score(by_actor, articles):
    """Ukraine baseline +12 (active war, higher than Belarus).

    ABSENCE CAVEAT (v1.1.0): this is a volume metric. A scan that retrieves
    nothing scores BASELINE and bands as 'elevated' -- indistinguishable from
    a genuinely quiet day on the war floor. The score math is deliberately
    UNCHANGED here so historical series stay comparable; instead the scan
    records result['sensing'], and a consumer that treats a blind scan as an
    observation is making the error, not this function. Wiring blindness into
    the score itself is a scoring decision, taken once, with the GPI rollup
    in view -- not smuggled in as part of a plumbing fix.
    """
    BASELINE = 12
    actor_weights = {
        'ukrainian_government':       0.85,
        'ukrainian_armed_forces':     0.95,
        'russian_forces_in_ukraine':  1.10,
        'us_government':              1.10,
        'nato_western_support':       0.85,
        'defense_industrial_base':    0.85,
        'occupied_territories_signals': 0.75,
    }
    score = BASELINE
    for actor_key, articles_list in by_actor.items():
        weight = actor_weights.get(actor_key, 0.7)
        # Co-credit copies are display-only -- exclude from score (v1.1).
        actor_contribution = min(25, sum(
            a.get('weight', 0.7) for a in articles_list
            if not a.get('co_credit')) * weight)
        score += actor_contribution
    return max(0, min(100, int(score)))


def _alert_level_from_score(score):
    """Active-war theatre: war is the FLOOR. Baseline never reads 'normal' --
    the analytical question is escalation ABOVE the hot floor, not the
    presence/absence of conflict. Enum (elevated/high/critical) preserved so
    the Europe BLUF + GPI rollup stay schema-compatible (and Ukraine stops
    under-weighting the GPI as a false 'normal')."""
    if score >= 70:
        return 'critical'   # major escalation (mass strikes / red-line breach)
    elif score >= 50:
        return 'high'       # escalating above the war floor
    else:
        return 'elevated'   # WAR FLOOR -- sustained active-war tempo


def _write_cross_theater_fingerprints(fingerprints):
    for key, val in (fingerprints or {}).items():
        try:
            _redis_set(f'fingerprint:ukraine:{key}', val)
        except Exception:
            pass


# ============================================================
# CANONICAL SPOKE FINGERPRINT (Rim Emission Pass -- Jul 2026)
# Writes crosstheater:ukraine:fingerprint so the Russia wheel's
# _read_spoke_fingerprints() can finally read Ukraine. Clones the Russia
# template; adapted to Ukraine's score/alert model. node_class = adversary.
# SURFACE-ONLY: no polarity wired into any score -- that is a wheel scoping
# decision, made once the rim is live, not smuggled in as plumbing.
# ============================================================

# Ukraine's alert enum -> canonical 0-5 level, honoring its own war-floor
# doctrine (see _alert_level_from_score). Mirrors Russia Option B: L4 is the
# active-war band, L5 is reserved for strategic escalation.
_SPOKE_LEVEL_BY_ALERT = {
    'elevated': 4,   # WAR FLOOR -- Active Conflict (matches Russia)
    'high':     4,   # active war, elevated tempo
    'critical': 5,   # Strategic Escalation -- major escalation / red-line breach
}

def _write_canonical_spoke_fingerprint(result):
    """Emit crosstheater:ukraine:fingerprint (hub-agnostic per-country schema).

    Consumed by the Russia wheel (_read_spoke_fingerprints), the Europe BLUF,
    and future Russia-wheel recompute narratives. Runs ALONGSIDE the legacy
    fingerprint:ukraine:* writes (emit once, consume many)."""
    alert = result.get('alert_level', 'elevated')
    level = _SPOKE_LEVEL_BY_ALERT.get(alert, 4)   # default to war floor, never below
    green = result.get('green_lines') or {}
    fingerprint = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'ukraine',
        'node_class':  'adversary',   # adversary of Russia in the Russia wheel
        'level':       level,
        'score':       result.get('theatre_score', 0),
        'alert_level': alert,

        # -- Diplomatic slice: Ukraine is the adversary AND the loudest
        #    off-ramp voice. The wheel reads "adversary active WHILE an
        #    off-ramp is present" -- the dual signal, convergence-framed.
        'diplomatic': {
            'off_ramp_maturity':    result.get('de_escalation_maturity', 'none'),
            'green_lines_active':   green.get('active_count', 0),
            'contradiction_active': result.get('contradiction_active', False),
            'diplomatic_max_raw':   result.get('diplomatic_max_raw', 0),
        },
    }
    try:
        _redis_set('crosstheater:ukraine:fingerprint', fingerprint)
        print('[Ukraine Rhetoric] Canonical spoke fingerprint written (crosstheater:ukraine:fingerprint)')
    except Exception as e:
        print(f'[Ukraine Rhetoric] Canonical fingerprint write failed: {e}')


# ============================================================
# MAIN SCAN
# ============================================================

def run_ukraine_rhetoric_scan(force=False):
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

    print('[Ukraine Rhetoric] Starting fresh scan...')
    started = time.time()

    articles, sensing = _fetch_all_articles()
    print(f'[Ukraine Rhetoric] Articles: {len(articles)} '
          f'(RSS {sensing["rss"]["ok"]}/{sensing["rss"]["attempted"]}, '
          f'GDELT {sensing["gdelt"]["sensed"]}/{sensing["gdelt"]["attempted"]} sensed)')
    if not sensing['any_sensed']:
        print('[Ukraine Rhetoric] BLIND -- no source family answered. The score '
              'below is the BASELINE FLOOR, not a measurement of a quiet war.')
    elif sensing['degraded']:
        print('[Ukraine Rhetoric] DEGRADED -- GDELT contributed nothing this scan.')

    telegram_messages = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_messages = fetch_ukraine_telegram_signals() or []
            print(f'[Ukraine Rhetoric] Telegram: {len(telegram_messages)} messages')
        except Exception as e:
            print(f'[Ukraine Rhetoric] Telegram fetch error: {str(e)[:120]}')

    bluesky_signals = []
    if BLUESKY_AVAILABLE:
        try:
            bluesky_signals = fetch_ukraine_bluesky_signals() or []
            print(f'[Ukraine Rhetoric] Bluesky: {len(bluesky_signals)} posts')
        except Exception as e:
            print(f'[Ukraine Rhetoric] Bluesky fetch error: {str(e)[:120]}')

    reddit_signals, reddit_probe = _fetch_reddit()
    print(f'[Ukraine Rhetoric] Reddit: {len(reddit_signals)} posts')
    sensing['reddit'] = reddit_probe

    by_actor = _classify_articles(articles)

    # ── v1.3 (Jul 20 2026): Crimea posture RUMINT sub-read ──────────────────
    # Counts occupied-territories articles that name the BSF-displacement
    # cluster, tags the SOURCE class (partisan/leaked/confirmed-strike), and
    # returns an explicitly-UNVERIFIED structured block. Sensor-only: this does
    # NOT feed the theatre score (partisan/interested sourcing must never
    # inflate a confirmed-fact metric). The analyst layer frames the meaning.
    _crimea_displacement_kw = [
        'black sea fleet evacuation', 'black sea fleet relocation',
        'sevastopol evacuation', 'crimea evacuation', 'evacuate crimea',
        'fleet command novorossiysk', 'fleet relocation novorossiysk',
        'bsf withdrawal', 'black sea fleet withdrawal', 'pinchuk sevastopol',
        'crimea military families', 'эвакуация севастополь', 'эвакуация крым',
        'евакуація крим',
    ]
    _rumint_sources = ['atesh', 'void group', 'leaked', 'telegram attributed',
                       'partisan', 'reconnaissance group', 'could not verify',
                       'could not independently verify', 'unverified']
    _crimea_hits, _crimea_src_tags, _crimea_examples = 0, set(), []
    for _a in articles:
        _txt = ' '.join([
            (_a.get('title') or '').lower(),
            (_a.get('description') or '').lower(),
            (_a.get('url') or '').lower().replace('-', ' ').replace('/', ' '),
        ])
        if any(_kw in _txt for _kw in _crimea_displacement_kw):
            _crimea_hits += 1
            if any(_s in _txt for _s in _rumint_sources):
                _crimea_src_tags.add('partisan/leaked (unverified)')
            if any(_s in _txt for _s in ('strike', 'drone', 'storm shadow',
                                         'atacms', 'magura', 'destroyed', 'hit')):
                _crimea_src_tags.add('strike-corroborated')
            if len(_crimea_examples) < 4:
                _crimea_examples.append({
                    'title':  (_a.get('title') or '')[:180],
                    'url':    _a.get('url', ''),
                    'source': _a.get('source', ''),
                })
    # Level 0-3, deliberately capped at 3: this is a RUMINT read, never a
    # confirmed 4/5. 1-2 reports = L1, 3-4 = L2, 5+ = L3.
    if _crimea_hits >= 5:
        _crimea_level = 3
    elif _crimea_hits >= 3:
        _crimea_level = 2
    elif _crimea_hits >= 1:
        _crimea_level = 1
    else:
        _crimea_level = 0
    crimea_posture = {
        'level':      _crimea_level,
        'report_count': _crimea_hits,
        'verified':   False,   # ALWAYS false — partisan/leaked/interested sources
        'rumint':     True,
        'source_classes': sorted(_crimea_src_tags),
        'examples':   _crimea_examples,
        'reading': ('Reports of Black Sea Fleet command / military-family '
                    'displacement from Sevastopol toward Novorossiysk. '
                    'Consistent with sustained Ukrainian sea-denial pressure on '
                    'occupied Crimea. UNVERIFIED — sourced to Ukrainian partisan '
                    'reconnaissance (Atesh) and leaked garrison orders. A '
                    'contingency-planning / logistics-strain read, NOT a Russian '
                    'decision to concede Crimea and NOT a shift in stated war aims.'),
    }
    if _crimea_hits:
        print(f'[Ukraine Rhetoric] Crimea posture RUMINT: {_crimea_hits} report(s), '
              f'L{_crimea_level}, sources={sorted(_crimea_src_tags) or ["unclassified"]}')

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
    articles_uk = [a for a in articles if a.get('language') == 'ukr']
    articles_ru = [a for a in articles if a.get('language') == 'rus']

    scan_data = {
        'articles_en':       articles_en,
        'articles_uk':       articles_uk,
        'articles_ru':       articles_ru,
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

    # -- v1.2 (Jun 18 2026): strategic-strike BREACH band floor -----------------
    # A record strike is a record strike -- on the BAND, not just the signal.
    # theatre_score is pure article volume, so a BREACHED Strategic-Strike red
    # line (the record Moscow attack, or a major strike on Kyiv) can sit on the
    # war-floor 'elevated' band on volume alone -- which buries it in the GPI
    # priority rollup (the GPI ranks signals by their region's ambient level).
    # Floor the band so a genuine strategic-strike breach reads at least 'high'
    # (and 'critical' when two or more stack). Convergence-safe: re-bands an
    # ALREADY-breached red line; invents no signal. Floors only, never lowers.
    _rl_triggered = (interpretation.get('red_lines') or {}).get('triggered') or []
    _strategic_breaches = sum(
        1 for _rl in _rl_triggered
        if _rl.get('status') == 'BREACHED'
        and _rl.get('category') == 'Strategic Strike'
        and _rl.get('severity', 0) >= 4
    )
    _BAND_RANK = {'normal': 0, 'elevated': 1, 'high': 2, 'critical': 3}
    if _strategic_breaches >= 2:
        score = max(score, 70)
        if _BAND_RANK['critical'] > _BAND_RANK.get(alert, 0):
            alert = 'critical'
    elif _strategic_breaches >= 1:
        score = max(score, 55)
        if _BAND_RANK['high'] > _BAND_RANK.get(alert, 0):
            alert = 'high'
    if _strategic_breaches >= 1:
        print(f'[Ukraine Rhetoric] Strategic-strike BREACH floor applied: '
              f'{_strategic_breaches} breach(es) -> band {alert}, score {score}')

    # -- Off-ramp fingerprint (Slice 4, Jun 18 2026) --
    # Translate the interpreter's gated diplomatic-track scenario into the Iran
    # off-ramp schema (de_escalation_maturity / contradiction_active /
    # diplomatic_max_raw) so the conflict-repricing detector and the GPI read
    # Ukraine the same way they read Iran. Convergence framing: reports that an
    # off-ramp is present and how mature it is -- never predicts the war ends.
    _dt = interpretation.get('diplomatic_track') or {}
    _scenario = _dt.get('scenario', 'No Active Track')
    _MATURITY_BY_SCENARIO = {
        'No Active Track':                  'none',
        'Limited De-escalation Indicators': 'none',
        'Tentative Diplomatic Signals':     'framework',   # talk, not terms
        'Active Ceasefire Track':           'signed',      # terms, not talk
    }
    _offramp_maturity = _MATURITY_BY_SCENARIO.get(_scenario, 'none')
    _negator_hits = _dt.get('negator_hits', 0)
    # Contradiction: an off-ramp is present AND the tape is fighting it -- either
    # an explicit ceasefire rejection (negators) or a live strategic-strike
    # breach (e.g. the record Moscow strike) continuing through the track.
    _contradiction_flags = []
    if _offramp_maturity != 'none':
        if _strategic_breaches >= 1:
            _contradiction_flags.append('active_strategic_strikes')
        if _negator_hits >= 1:
            _contradiction_flags.append('ceasefire_rejected')
    _contradiction_active = bool(_contradiction_flags)

    elapsed = round(time.time() - started, 1)
    result = {
        'theatre':           'ukraine',
        'flag':              '🇺🇦',
        'display_name':      'Ukraine',
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
        'articles_uk':       articles_uk,
        'articles_ru':       articles_ru,
        'actor_summaries':   actor_summaries,
        'so_what':           interpretation.get('so_what'),
        'top_signals':       interpretation.get('top_signals') or [],
        'red_lines':         interpretation.get('red_lines'),
        'green_lines':       interpretation.get('green_lines'),
        'diplomatic_track':  interpretation.get('diplomatic_track'),
        # Off-ramp fingerprint (Slice 4) -- read by conflict_repricing_detector
        'de_escalation_maturity': _offramp_maturity,
        'contradiction_active':   _contradiction_active,
        'contradiction_flags':    _contradiction_flags,
        'diplomatic_max_raw':     _dt.get('score', 0),
        'crimea_posture':    crimea_posture,   # v1.3 RUMINT sub-read (unverified, score-neutral)
        'commodity_signal':  interpretation.get('commodity_signal'),
        'cross_theater_fingerprints': interpretation.get('cross_theater_fingerprints'),
        'composite_modifier': interpretation.get('composite_modifier', 0),
        'interpreter_version': interpretation.get('interpreter_version'),
    }

    _redis_set(REDIS_KEY_LATEST, result)
    _write_canonical_spoke_fingerprint(result)   # Rim Emission Pass -- feed the Russia wheel
    _redis_lpush_trim(REDIS_KEY_HISTORY, {
        'cached_at':     result['cached_at'],
        'theatre_score': result['theatre_score'],
        'alert_level':   result['alert_level'],
        'top_signals':   result['top_signals'][:5],
    })

    print(f'[Ukraine Rhetoric] Scan complete: score={score}, alert={alert}, '
          f'articles={len(articles)}, elapsed={elapsed}s')
    return result


# ============================================================
# BACKGROUND REFRESH
# ============================================================

def _background_refresh():
    time.sleep(120)
    while True:
        try:
            with _scan_lock:
                run_ukraine_rhetoric_scan(force=True)
        except Exception as e:
            print(f'[Ukraine Rhetoric] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_INTERVAL_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[Ukraine Rhetoric] Background refresh thread started (6h cycle)')


# ============================================================
# ENDPOINT REGISTRATION
# ============================================================

def register_ukraine_rhetoric_endpoints(app):
    @app.route('/api/rhetoric/ukraine', methods=['GET'])
    def api_rhetoric_ukraine():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            data = run_ukraine_rhetoric_scan(force=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error':   str(e)[:200],
                'theatre': 'ukraine',
            }), 500

    @app.route('/api/rhetoric/ukraine/summary', methods=['GET'])
    def api_rhetoric_ukraine_summary():
        try:
            d = run_ukraine_rhetoric_scan(force=False)
            return jsonify({
                'theatre':         'ukraine',
                'flag':            '🇺🇦',
                'display_name':    'Ukraine',
                'theatre_score':   d.get('theatre_score', 0),
                'alert_level':     d.get('alert_level', 'normal'),
                'top_signals':     (d.get('top_signals') or [])[:3],
                'so_what_scenario': (d.get('so_what') or {}).get('scenario'),
                'cached_at':       d.get('cached_at'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/rhetoric/ukraine/history', methods=['GET'])
    def api_rhetoric_ukraine_history():
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
                'theatre': 'ukraine',
                'count':   len(history),
                'history': history,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200], 'history': []}), 500

    print('[Ukraine Rhetoric] Endpoints registered: /api/rhetoric/ukraine, /summary, /history')
