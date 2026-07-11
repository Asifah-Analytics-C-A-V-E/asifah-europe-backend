"""
rhetoric_tracker_hungary.py
Asifah Analytics -- Europe Backend Module
v1.0.0 -- May 17, 2026

HUNGARY RHETORIC TRACKER

Tracks Hungary's diplomatic + political + economic rhetoric across 5 actor
dimensions, with primary analytical focus on AXIS REVERSAL: the structural
shift in Hungarian foreign policy following the April 2026 Tisza landslide
victory over Orban/Fidesz.

KEY ANALYTICAL FRAMING:
  Hungary is the first documented "Russia-axis-dependent" Eurasian country
  to undergo a democratic axis reversal that Asifah can track in real-time.
  Concrete symptoms observed:
    - $82M cash + 9kg gold returned to Ukraine (May 6, 2026)
    - 90B EUR EU loan veto LIFTED (post-election)
    - Druzhba pipeline flow resumption
    - Pre-electoral anti-Ukraine rhetoric reversed
  This tracker watches for: (a) durability of reversal, (b) Orban/Fidesz
  comeback signals, (c) Russia counter-pressure on Hungary.

ACTORS (5):
  1. hungary_government       -- Tisza-led govt (post-April 2026 election)
  2. hungary_opposition       -- Orban/Fidesz (now in opposition)
  3. hungary_eu_track         -- Hungary <-> Brussels relationship
  4. hungary_russia_axis      -- Russia ties being unwound (oil/gas/Paks II)
  5. hungary_ukraine_track    -- Hungary <-> Kyiv bilateral

SIGNAL SOURCES:
  - GDELT (English + Hungarian + Russian queries)
  - NewsAPI (English)
  - RSS feeds (Hungarian state + opposition + EU + Reuters/AP)
  - Brave Search API (tertiary fallback when GDELT + NewsAPI < 10 articles)
  - Bluesky (via bluesky_signals_europe.fetch_hungary_bluesky_signals)
  - Telegram (via telegram_signals_europe.fetch_hungary_telegram_signals)

EMITS:
  - Cross-theater fingerprint: 'hungary_axis_reversal_active' (boolean)
  - Cross-theater fingerprint: 'hungary_orban_revival_signal' (boolean)
  - Cross-theater fingerprint: 'druzhba_pipeline_status' (string enum)

ENDPOINTS:
  GET /api/rhetoric/hungary               -- Full scan output (cached)
  GET /api/rhetoric/hungary?force=true    -- Force fresh scan
  GET /api/rhetoric/hungary/summary       -- Lightweight summary for cards
  GET /api/rhetoric/hungary/history       -- Last N scans history

Author: RCGG / Asifah Analytics
"""
import os
import json
import time
import re
import threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import feedparser

# ============================================================
# OPTIONAL IMPORTS (graceful fallback)
# ============================================================
try:
    from telegram_signals_europe import fetch_hungary_telegram_signals
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    def fetch_hungary_telegram_signals(hours_back=120):
        return []

try:
    from bluesky_signals_europe import fetch_hungary_bluesky_signals
    BLUESKY_AVAILABLE = True
except ImportError:
    BLUESKY_AVAILABLE = False
    def fetch_hungary_bluesky_signals(days=7, max_posts_per_account=20):
        return []

# ============================================================
# CONFIGURATION
# ============================================================
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')
NEWSAPI_KEY         = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY       = os.environ.get('BRAVE_API_KEY', '')
GDELT_BASE_URL      = 'https://api.gdeltproject.org/api/v2/doc/doc'

RHETORIC_CACHE_KEY  = 'rhetoric:hungary:latest'
HISTORY_KEY         = 'rhetoric:hungary:history'
SUMMARY_KEY         = 'rhetoric:hungary:summary'
CROSSTHEATER_KEY    = 'rhetoric:crosstheater:fingerprints'

RHETORIC_CACHE_TTL  = 12 * 3600
SCAN_INTERVAL_HOURS = 12
HISTORY_RETENTION   = 30
SCAN_LOCK_KEY       = 'rhetoric:hungary:scan_lock'
SCAN_LOCK_TTL       = 600

RSS_TIMEOUT         = 12
GDELT_TIMEOUT       = 15
NEWSAPI_TIMEOUT     = 15
BRAVE_TIMEOUT       = 12

BRAVE_FALLBACK_MIN_ARTICLES = 10

VERSION = '1.0.0'

# ============================================================
# ESCALATION LEVELS
# ============================================================
ESCALATION_LEVELS = {
    0: {'label': 'BASELINE',     'color': '#6b7280', 'icon': '⚪'},
    1: {'label': 'WATCH',        'color': '#3b82f6', 'icon': '🔵'},
    2: {'label': 'ELEVATED',     'color': '#22c55e', 'icon': '🟢'},
    3: {'label': 'TENSION',      'color': '#f59e0b', 'icon': '🟡'},
    4: {'label': 'CONFRONTATION','color': '#f97316', 'icon': '🟠'},
    5: {'label': 'CRISIS',       'color': '#dc2626', 'icon': '🔴'},
}

# ============================================================
# ACTORS
# ============================================================
# ============================================================
# SEVERITY LEXICONS (v1.1 calibration -- intensity, not volume)
# ------------------------------------------------------------
# Actor 'keywords' answer "is this article about this actor?" (relevance).
# These lexicons answer "how hot is the language?" (intensity).
# Multi-word phrases are used on purpose to avoid naive-substring false
# positives (e.g. 'coup' inside 'couple', 'riot' inside 'patriot').
#
#   HIGH   = genuine unrest / violence           -> enables L4-L5
#   MEDIUM = coercion / confrontation / rupture  -> enables L3-L4
#   (neither present = ordinary politics         -> caps at L2)
# ============================================================
SEVERITY_HIGH = [
    'civil war', 'martial law', 'state of emergency', 'military coup',
    'coup attempt', 'coup d', 'violent clashes', 'deadly clashes',
    'violent unrest', 'armed clashes', 'troops deployed', 'tanks deployed',
    'opened fire', 'live fire', 'mass casualties', 'people killed',
    'protesters killed', 'rioting', 'storming of parliament',
    'stormed parliament', 'insurrection', 'assassination',
]

SEVERITY_MEDIUM = [
    'constitutional crisis', 'political crisis', 'government collapse',
    'cabinet collapse', 'vote of no confidence', 'no-confidence motion',
    'no confidence motion', 'snap election', 'impeachment', 'ultimatum',
    'recall ambassador', 'ambassador recalled', 'expels diplomats',
    'expelled diplomats', 'sever ties', 'severs ties', 'cuts ties',
    'suspends cooperation', 'emergency session', 'mass protest',
    'mass demonstration', 'general strike', 'crackdown', 'standoff',
    'closes border', 'border closure',
]


ACTORS = {

    # ── 1. HUNGARY GOVERNMENT (Tisza-led, post-April 2026) ────────
    'hungary_government': {
        'name': 'Hungary Government (Tisza-led)',
        'flag': '🇭🇺',
        'icon': '🏛️',
        'color': '#22c55e',
        'role': 'Post-April-2026 government -- pro-EU realignment posture',
        'description': (
            'Tisza-led Hungarian government following April 2026 landslide '
            'two-thirds parliamentary majority. PM Peter Magyar + cabinet '
            'pursuing reversal of Orban-era axis-dependent policies. '
            'Watch for: EU loan unlock, Druzhba pipeline statements, '
            'Russia-contract reviews, Ukraine support language.'
        ),
        'keywords': [
            # Core government identity
            'tisza party', 'tisza government', 'peter magyar', 'magyar peter',
            'hungarian government tisza', 'hungarian pm magyar', 'hungary prime minister tisza',
            'hungary cabinet tisza', 'hungarian foreign minister tisza',
            'budapest government tisza', 'hungary parliament tisza',
            'magyar cabinet', 'magyar government',
            # Pro-EU realignment signals
            'hungary lifts veto', 'hungary unlocks eu loan',
            'hungary supports ukraine', 'hungary supports kyiv',
            'hungary pro-eu', 'hungary back to eu',
            'hungary rule of law', 'hungary article 7',
            'hungary eu cooperation', 'hungary brussels cooperation',
            # Axis-reversal symptoms
            'hungary returns ukraine assets', 'hungary returns gold',
            'hungary returns cash', 'hungary returns seized',
            'hungary druzhba resumed', 'hungary druzhba flow',
            'hungary russia gas review', 'paks ii review',
            'hungary rosatom review', 'hungary nuclear contract review',
            # Hungarian (Magyar)
            'tisza párt', 'magyar péter', 'magyar kormány',
            'magyar miniszterelnök', 'magyar kabinet',
            'magyar uniós hitel', 'magyar vétó feloldás',
        ],
        'baseline_statements_per_week': 8,
        'tripwires': [
            'hungary unlocks eu loan',
            'hungary returns ukraine assets',
            'paks ii rosatom cancel',
            'hungary druzhba resumed',
        ],
    },

    # ── 2. HUNGARY OPPOSITION (Orban / Fidesz, post-defeat) ───────
    'hungary_opposition': {
        'name': 'Hungary Opposition (Orban / Fidesz)',
        'flag': '🇭🇺',
        'icon': '⚠️',
        'color': '#f97316',
        'role': 'Former ruling party -- now opposition; axis-revival watch',
        'description': (
            'Viktor Orban and Fidesz now in opposition following April 2026 '
            'electoral defeat. Still influential -- ~33% of parliament. Watch '
            'for: Orban international diplomacy (Putin/Trump direct lines), '
            'anti-Ukraine messaging revival, anti-EU rhetoric, Fidesz mass '
            'rallies, attempts to obstruct Tisza policy.'
        ),
        'keywords': [
            # Core identity
            'viktor orban', 'orban', 'fidesz', 'fidesz party',
            'hungarian opposition', 'orban statement', 'fidesz statement',
            'orban speech', 'orban rally', 'fidesz rally',
            'orban interview', 'orban presser', 'orban tucker',
            'hungarian far-right', 'hungarian nationalist',
            # Russia-axis-revival signals
            'orban moscow', 'orban putin', 'orban russia visit',
            'orban kremlin', 'orban russian gas', 'orban druzhba',
            'orban russia peace plan', 'fidesz russia',
            'fidesz pro russia', 'orban anti-ukraine',
            # Anti-EU / anti-Brussels signals
            'orban brussels', 'orban eu sovereignty', 'orban hungexit',
            'orban anti-eu', 'fidesz anti-brussels',
            'orban article 7', 'orban rule of law dispute',
            'orban migration crisis', 'orban gender',
            # Trump alignment
            'orban trump', 'orban mar-a-lago', 'orban cpac',
            'orban heritage foundation', 'orban tucker carlson',
            # Hungarian (Magyar)
            'orbán viktor', 'fidesz párt', 'orbán beszéd',
            'orbán interjú', 'orbán moszkva', 'orbán putyin',
        ],
        'baseline_statements_per_week': 12,
        'tripwires': [
            'orban moscow visit',
            'orban putin meeting',
            'fidesz mass rally',
            'orban tucker carlson interview',
        ],
    },

    # ── 3. HUNGARY <-> EU TRACK ────────────────────────────────────
    'hungary_eu_track': {
        'name': 'Hungary <-> EU Relations',
        'flag': '🇪🇺',
        'icon': '🤝',
        'color': '#3b82f6',
        'role': 'Hungary-Brussels bilateral track -- normalization vs friction',
        'description': (
            'Hungary-EU relationship dynamics. Includes: 90B EUR Ukraine loan '
            'status, Article 7 rule-of-law proceedings, Cohesion Funds release, '
            'EU sanctions on Russia compliance, joint EU statements. Post-Tisza '
            'election, EU has signaled willingness to release frozen funds + '
            'close Article 7 proceedings if Hungary continues reform path.'
        ),
        'keywords': [
            # EU institutional engagement
            'european commission hungary', 'ec hungary',
            'eu council hungary', 'european council hungary',
            'von der leyen hungary', 'metsola hungary',
            'european parliament hungary', 'ep hungary debate',
            'eu summit hungary', 'eu hungary loan',
            # Loan / Cohesion Funds dynamics
            'hungary eu loan', '90 billion euro ukraine',
            'eu loan ukraine hungary veto', 'hungary lifts loan veto',
            'hungary cohesion funds', 'hungary frozen eu funds',
            'hungary eu funds released', 'rrf hungary',
            'hungary recovery plan eu',
            # Rule of law track
            'hungary article 7', 'hungary rule of law',
            'eu article 7 hungary', 'hungary judicial reform',
            'hungary cjeu', 'hungary court of justice',
            'hungary infringement procedure',
            # Sanctions cooperation
            'hungary russia sanctions', 'hungary sanctions vote',
            'hungary 19th sanctions package', 'hungary blocks sanctions',
            'hungary unblocks sanctions',
            # Hungarian / EU languages
            'magyar uniós hitel', 'magyar uniós források',
            'magyarország 7 cikk', 'magyar jogállamiság',
        ],
        'baseline_statements_per_week': 10,
        'tripwires': [
            'hungary lifts loan veto',
            'hungary eu funds released',
            'hungary article 7 closed',
            'hungary blocks sanctions',
        ],
    },

    # ── 4. HUNGARY RUSSIA AXIS (reversing) ─────────────────────────
    'hungary_russia_axis': {
        'name': 'Hungary <-> Russia Axis (Reversing)',
        'flag': '🇷🇺',
        'icon': '🛢️',
        'color': '#dc2626',
        'role': 'Russia-Hungary ties under structural reversal post-election',
        'description': (
            'Russia-Hungary structural ties under reversal. Watch: Druzhba '
            'pipeline status, Russian gas contracts (MVM-Gazprom), Paks II '
            'nuclear plant Rosatom contract, Putin-Orban dynamics (now '
            'opposition-channel), Russia counter-pressure on Hungary. '
            'Druzhba pipeline transit Russia -> Ukraine -> Hungary -> Slovakia '
            'is the structural leverage point; was the trigger for Orban EU '
            'loan veto pre-election.'
        ),
        'keywords': [
            # Druzhba pipeline
            'druzhba pipeline', 'druzhba flow', 'druzhba damage',
            'druzhba repair', 'druzhba resumed', 'druzhba halted',
            'russia drone druzhba', 'ukraine druzhba damage',
            'mol hungary druzhba', 'mol szazhalombatta',
            'tisza refinery hungary', 'hungary oil pipeline russia',
            # Russian gas dependency
            'gazprom hungary', 'mvm hungary gas', 'mvm gazprom',
            'turkstream hungary', 'turkstream gas hungary',
            'hungary russian gas contract', 'hungary gas dependency',
            'hungary lng diversification', 'krk croatia hungary',
            'baltic pipe hungary', 'hungary lng terminal',
            # Paks II nuclear
            'paks nuclear plant', 'paks ii', 'paks ii rosatom',
            'paks ii expansion', 'rosatom hungary',
            'paks ii financing', 'paks ii sanctions',
            'paks ii construction', 'paks ii contract review',
            # Putin-Orban / Russia influence
            'putin orban', 'orban putin call', 'putin orban meeting',
            'russia hungary cooperation', 'kremlin hungary',
            'lavrov hungary', 'russia hungary peace plan',
            'russia counter pressure hungary',
            # Russian (Cyrillic)
            'венгрия россия', 'венгерская россия',
            'венгрия дружба', 'венгрия газпром',
            'венгрия паксAES', 'орбан путин',
        ],
        'baseline_statements_per_week': 8,
        'tripwires': [
            'paks ii rosatom cancel',
            'hungary terminates gazprom contract',
            'druzhba resumed',
            'putin orban call',
            'russia counter pressure hungary',
        ],
    },

    # ── 5. HUNGARY <-> UKRAINE TRACK ──────────────────────────────
    'hungary_ukraine_track': {
        'name': 'Hungary <-> Ukraine Relations',
        'flag': '🇺🇦',
        'icon': '🕊️',
        'color': '#22c55e',
        'role': 'Hungary-Kyiv bilateral track -- post-election normalization',
        'description': (
            'Hungary-Ukraine bilateral relationship. Most directly affected '
            'by April 2026 election outcome. Watch: returned-assets goodwill, '
            'border + minority rights (Ukrainian Hungarians in Transcarpathia), '
            'arms transit, Ukrainian refugees in Hungary, Zelenskyy-Magyar '
            'dynamics, Druzhba-related disputes resolving.'
        ),
        'keywords': [
            # Bilateral diplomacy
            'zelensky hungary', 'zelenskyy hungary', 'zelensky magyar',
            'zelensky orban', 'zelenskyy budapest', 'magyar zelensky',
            'hungary ukraine summit', 'hungary ukraine talks',
            'kuleba hungary', 'sybiha hungary',
            'hungary ukraine relations',
            # The asset return event (May 6, 2026)
            'hungary returns ukraine 82 million', 'hungary returns 80 million',
            'hungary returns oschadbank', 'oschadbank hungary',
            'hungary returns ukrainian gold', 'hungary returns cash gold',
            'hungary seized ukraine cash', 'hungary armored car ukraine',
            'hungarian counter terrorism ukrainian cash',
            'hungary returns ukrainian valuables',
            # Refugees / Hungarian minority
            'ukrainian refugees hungary', 'hungary border ukraine',
            'transcarpathia hungarians', 'hungarians ukraine minority',
            'beregszasz hungarians', 'zakarpattia hungarians',
            'hungary ukrainian schools', 'hungary minority rights ukraine',
            # Anti-Ukraine campaign (Orban-era residue)
            'orban anti-ukraine campaign', 'anti-ukraine referendum hungary',
            'hungary ukraine accession veto', 'hungary blocks ukraine eu',
            # Hungarian / Ukrainian
            'magyar ukrán', 'magyar zelenszkij', 'magyar ukrajna',
            'угорщина повертає україні', 'угорщина ощадбанк',
        ],
        'baseline_statements_per_week': 10,
        'tripwires': [
            'hungary lifts ukraine accession veto',
            'zelensky magyar summit',
            'hungary returns ukraine assets',
        ],
    },
}


# ============================================================
# AXIS REVERSAL TRIGGERS (cross-theater fingerprint emission)
# ============================================================
AXIS_REVERSAL_TRIGGERS = [
    # Each is a substring-match against article titles + descriptions.
    # Co-occurrence of 3+ across articles -> axis_reversal_active fingerprint.
    'hungary returns ukraine assets',
    'hungary returns gold ukraine',
    'hungary lifts loan veto',
    'hungary unlocks eu loan',
    'hungary eu funds released',
    'druzhba flow resumed',
    'hungary article 7 closed',
    'hungary returns oschadbank',
    'tisza government supports ukraine',
    'paks ii rosatom review',
    'hungary blocks fewer russia sanctions',
]

ORBAN_REVIVAL_TRIGGERS = [
    'orban moscow visit', 'orban putin meeting',
    'fidesz mass rally', 'orban tucker carlson',
    'orban comeback', 'fidesz resurgence',
    'orban anti-ukraine campaign revival',
    'orban hungexit', 'orban article 7 defiance',
]


# ============================================================
# RSS SOURCES (Hungary-specific)
# ============================================================
RSS_SOURCES = {
    # Hungarian state media
    'hu_mti': {
        'url': 'https://magyarnemzet.hu/feed/',
        'name': 'Magyar Nemzet',
        'weight': 0.95,
        'language': 'hu',
    },
    'hu_telex': {
        'url': 'https://telex.hu/rss',
        'name': 'Telex (independent)',
        'weight': 1.0,
        'language': 'hu',
    },
    'hu_index': {
        'url': 'https://index.hu/24ora/rss/',
        'name': 'Index.hu',
        'weight': 0.95,
        'language': 'hu',
    },
    'hu_hvg': {
        'url': 'https://hvg.hu/rss',
        'name': 'HVG',
        'weight': 0.95,
        'language': 'hu',
    },
    # EU / international Hungary coverage
    'reuters_hungary': {
        'url': 'https://www.reuters.com/arc/outboundfeeds/v3/category/world/europe/?outputType=xml',
        'name': 'Reuters Europe',
        'weight': 1.0,
        'language': 'en',
    },
    'politico_eu': {
        'url': 'https://www.politico.eu/feed/',
        'name': 'POLITICO Europe',
        'weight': 1.0,
        'language': 'en',
    },
    'euractiv': {
        'url': 'https://www.euractiv.com/feed/',
        'name': 'EURACTIV',
        'weight': 0.95,
        'language': 'en',
    },
    'euobserver': {
        'url': 'https://euobserver.com/rss.xml',
        'name': 'EUObserver',
        'weight': 0.9,
        'language': 'en',
    },
    'ap_world': {
        'url': 'https://feeds.apnews.com/rss/topic/europe',
        'name': 'AP Europe',
        'weight': 1.0,
        'language': 'en',
    },
}


# ============================================================
# GDELT QUERIES
# ============================================================
GDELT_QUERIES = {
    'en': [
        '"Hungary" AND ("Tisza" OR "Magyar" OR "Orban")',
        '"Hungary" AND ("EU loan" OR "Article 7" OR "rule of law")',
        '"Hungary" AND ("Druzhba" OR "Paks" OR "Rosatom" OR "Gazprom")',
        '"Hungary" AND ("Ukraine" OR "Zelensky" OR "Oschadbank")',
        '"Orban" AND ("Putin" OR "Moscow" OR "Tucker" OR "Mar-a-Lago")',
    ],
    'hu': [
        '"Magyarország" AND ("Tisza" OR "Magyar Péter")',
        '"Magyarország" AND ("uniós hitel" OR "jogállamiság")',
        '"Magyarország" AND ("Druzsba" OR "Paks" OR "Roszatom")',
        '"Magyarország" AND ("Ukrajna" OR "Zelenszkij")',
        '"Orbán" AND ("Putyin" OR "Moszkva")',
    ],
    'ru': [
        '"Венгрия" AND ("Орбан" OR "Тиса")',
        '"Венгрия" AND ("Дружба" OR "Газпром" OR "Пакш")',
        '"Венгрия" AND ("Украина" OR "Зеленский")',
    ],
}


# ============================================================
# REDIS HELPERS
# ============================================================
def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        resp = requests.get(
            f'{UPSTASH_REDIS_URL}/get/{key}',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get('result')
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
        return None
    except Exception as e:
        print(f'[Hungary Redis] get error: {str(e)[:80]}')
        return None


def _redis_set(key, value, ttl=None):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        body = json.dumps(value) if not isinstance(value, str) else value
        url = f'{UPSTASH_REDIS_URL}/set/{key}'
        if ttl:
            url = f'{UPSTASH_REDIS_URL}/setex/{key}/{ttl}'
        resp = requests.post(
            url,
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                     'Content-Type': 'text/plain'},
            data=body,
            timeout=8,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f'[Hungary Redis] set error: {str(e)[:80]}')
        return False


# ============================================================
# CANONICAL SPOKE FINGERPRINT (Rim Emission Pass -- Jul 2026)
# Writes crosstheater:hungary:fingerprint for the Russia wheel's
# _read_spoke_fingerprints(). node_class = axis_reversal_watch: Hungary is
# an EU/NATO member whose Russia posture FLIPPED post-April-2026 (Tisza/
# Magyar reversal of the Orban era). The wheel watches for reversal
# durability vs Orban-revival drift back toward Moscow.
# SURFACE-ONLY: no polarity wired into any score -- wheel scoping decision.
# NOTE: requires 'hungary' added to SPOKE_READ_KEYS in
# rhetoric_tracker_russia.py -- the reader does not listen for Hungary
# by default (unlike ukraine/belarus).
# ============================================================

def _write_canonical_spoke_fingerprint(result):
    """Emit crosstheater:hungary:fingerprint (hub-agnostic per-country schema).

    Hungary emits its NATIVE 0-5 theatre_level (no enum translation --
    unlike Ukraine/Belarus, this tracker computes the canonical level
    directly). Runs ALONGSIDE the legacy collective crosstheater writes
    (emit once, consume many)."""
    ct = result.get('cross_theater') or {}
    fingerprint = {
        'ts':          datetime.now(timezone.utc).isoformat(),
        'country':     'hungary',
        'node_class':  'axis_reversal_watch',   # EU/NATO member, post-Orban reversal
        'level':       result.get('theatre_level', 0),
        'score':       result.get('theatre_score', 0),
        'alert_level': result.get('theatre_label', ''),

        # -- Reversal slice: the read the wheel actually wants from Hungary.
        #    reversal_active = drifting AWAY from Moscow (de-tensioning);
        #    orban_revival   = drift BACK toward Moscow (the watch signal).
        'reversal': {
            'axis_reversal_active': ct.get('axis_reversal_active', False),
            'orban_revival_signal': ct.get('orban_revival_signal', False),
            'reversal_hits':        len(ct.get('axis_reversal_hits', []) or []),
            'revival_hits':         len(ct.get('orban_revival_hits', []) or []),
        },
    }
    try:
        _redis_set('crosstheater:hungary:fingerprint', fingerprint)
        print('[Hungary Rhetoric] Canonical spoke fingerprint written (crosstheater:hungary:fingerprint)')
    except Exception as e:
        print(f'[Hungary Rhetoric] Canonical fingerprint write failed: {e}')


def _crossteater_update(key, value):
    """Update a single field in the cross-theater fingerprint blob."""
    try:
        existing = _redis_get(CROSSTHEATER_KEY) or {}
        if not isinstance(existing, dict):
            existing = {}
        existing[key] = value
        existing['_updated_at'] = datetime.now(timezone.utc).isoformat()
        _redis_set(CROSSTHEATER_KEY, existing, ttl=86400 * 7)
    except Exception as e:
        print(f'[Hungary Crossteater] update error: {str(e)[:80]}')


# ============================================================
# FETCH HELPERS
# ============================================================
def _fetch_rss(url, name, weight=1.0):
    try:
        resp = requests.get(url, timeout=RSS_TIMEOUT,
                            headers={'User-Agent': 'AsifahAnalytics/1.0'})
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.content)
        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for entry in (feed.entries or [])[:30]:
            title = (entry.get('title') or '').strip()
            desc = (entry.get('summary') or entry.get('description') or '')[:500]
            url_a = entry.get('link') or ''
            pub_raw = entry.get('published') or entry.get('updated') or ''
            try:
                # Try parsing the publication date
                if entry.get('published_parsed'):
                    pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if pub < cutoff:
                        continue
            except Exception:
                pass
            if not title:
                continue
            articles.append({
                'title':       title[:300],
                'description': desc,
                'url':         url_a,
                'publishedAt': pub_raw,
                'source':      {'name': name},
                'content':     desc,
                'language':    'auto',
                'feed_type':   'rss',
                'source_weight_override': weight,
            })
        if articles:
            print(f'[Hungary RSS] {name}: {len(articles)} articles')
        return articles
    except Exception as e:
        print(f'[Hungary RSS] {name} error: {str(e)[:80]}')
        return []


def _fetch_gdelt(query, language='en', timespan='7d'):
    try:
        # Language code mapping for GDELT
        lang_param = {'en': 'eng', 'hu': 'hun', 'ru': 'rus'}.get(language, 'eng')
        params = {
            'query':        f'{query} sourcelang:{lang_param}',
            'mode':         'ArtList',
            'maxrecords':   30,
            'format':       'json',
            'timespan':     timespan,
            'sort':         'datedesc',
        }
        headers = {'User-Agent': 'AsifahAnalytics/1.0'}
        resp = requests.get(GDELT_BASE_URL, params=params,
                            headers=headers, timeout=GDELT_TIMEOUT)
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        articles = []
        for item in (data.get('articles') or [])[:30]:
            title = item.get('title', '').strip()
            url_a = item.get('url', '')
            domain = item.get('domain', '')
            if not title:
                continue
            articles.append({
                'title':       title[:300],
                'description': title[:400],
                'url':         url_a,
                'publishedAt': item.get('seendate', ''),
                'source':      {'name': domain or 'GDELT'},
                'content':     title,
                'language':    language,
                'feed_type':   'gdelt',
            })
        return articles
    except Exception as e:
        print(f'[Hungary GDELT] {language} error: {str(e)[:80]}')
        return []


def _fetch_newsapi(query, language='en'):
    if not NEWSAPI_KEY:
        return []
    try:
        params = {
            'q':         query,
            'apiKey':    NEWSAPI_KEY,
            'pageSize':  30,
            'sortBy':    'publishedAt',
            'language':  language,
        }
        resp = requests.get('https://newsapi.org/v2/everything',
                            params=params, timeout=NEWSAPI_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        articles = []
        for item in (data.get('articles') or [])[:30]:
            title = (item.get('title') or '').strip()
            if not title:
                continue
            articles.append({
                'title':       title[:300],
                'description': (item.get('description') or '')[:500],
                'url':         item.get('url', ''),
                'publishedAt': item.get('publishedAt', ''),
                'source':      item.get('source', {'name': 'NewsAPI'}),
                'content':     (item.get('content') or '')[:500],
                'language':    language,
                'feed_type':   'newsapi',
            })
        return articles
    except Exception as e:
        print(f'[Hungary NewsAPI] error: {str(e)[:80]}')
        return []


def _fetch_brave(query, days=7):
    """Brave Search tertiary fallback. Same pattern as Japan tracker."""
    if not BRAVE_API_KEY:
        return []
    try:
        resp = requests.get(
            'https://api.search.brave.com/res/v1/news/search',
            headers={
                'Accept':              'application/json',
                'Accept-Encoding':     'gzip',
                'X-Subscription-Token': BRAVE_API_KEY,
            },
            params={
                'q':          query,
                'count':      20,
                'freshness':  'pw' if days <= 7 else 'pm',
                'spellcheck': 'false',
            },
            timeout=BRAVE_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        articles = []
        for r in (data.get('results') or []):
            articles.append({
                'title':       (r.get('title') or '')[:300],
                'description': (r.get('description') or '')[:500],
                'url':         r.get('url') or '',
                'publishedAt': r.get('age') or r.get('page_age') or '',
                'source':      {'name': (r.get('meta_url', {}) or {}).get('hostname', 'Brave')},
                'content':     (r.get('description') or '')[:500],
                'language':    'en',
                'feed_type':   'brave',
            })
        return articles
    except Exception:
        return []


def _fetch_all_brave():
    """Brave fallback query bundle for Hungary."""
    if not BRAVE_API_KEY:
        return []
    queries = [
        'Hungary Tisza government Orban',
        'Hungary EU loan Ukraine veto',
        'Hungary Druzhba pipeline Russian oil',
        'Hungary Paks II Rosatom nuclear',
        'Hungary Ukraine gold cash return',
    ]
    all_articles = []
    for q in queries:
        all_articles.extend(_fetch_brave(q))
        time.sleep(1.0)
    if all_articles:
        print(f'[Hungary Brave] Total: {len(all_articles)} articles')
    return all_articles


# ============================================================
# CORE FETCH + SCORE
# ============================================================
def _gather_articles():
    """Pull articles from all sources. Returns deduplicated list."""
    all_articles = []
    seen_urls = set()

    def _add(arts):
        for a in (arts or []):
            url = a.get('url', '')
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            all_articles.append(a)

    # ── Telegram (168h window for slow-moving European diplomatic signals) ──
    if TELEGRAM_AVAILABLE:
        try:
            tg_messages = fetch_hungary_telegram_signals(hours_back=168)
            for msg in tg_messages:
                all_articles.append({
                    'title':       msg.get('title', '')[:300],
                    'description': msg.get('title', '')[:400],
                    'url':         msg.get('url', ''),
                    'publishedAt': msg.get('published', ''),
                    'source':      {'name': msg.get('source', 'Telegram')},
                    'content':     msg.get('title', '')[:500],
                    'language':    'auto',
                    'feed_type':   'telegram',
                })
            print(f'[Hungary] Telegram: {len(tg_messages)} messages ingested')
        except Exception as e:
            print(f'[Hungary] Telegram error: {str(e)[:80]}')

    # ── Bluesky ──
    if BLUESKY_AVAILABLE:
        try:
            bs_posts = fetch_hungary_bluesky_signals(days=7)
            for p in bs_posts:
                _add([p])
            print(f'[Hungary] Bluesky: {len(bs_posts)} posts ingested')
        except Exception as e:
            print(f'[Hungary] Bluesky error: {str(e)[:80]}')

    # ── RSS feeds ──
    for key, src in RSS_SOURCES.items():
        try:
            _add(_fetch_rss(src['url'], src['name'], src.get('weight', 0.95)))
        except Exception as e:
            print(f'[Hungary RSS] {key} error: {str(e)[:80]}')

    # ── GDELT (multi-language) ──
    gdelt_count = 0
    for lang, queries in GDELT_QUERIES.items():
        for q in queries:
            try:
                fetched = _fetch_gdelt(q, language=lang)
                _add(fetched)
                gdelt_count += len(fetched)
            except Exception as e:
                print(f'[Hungary GDELT] {lang} error: {str(e)[:80]}')
    print(f'[Hungary GDELT] Total: {gdelt_count} articles')

    # ── NewsAPI ──
    if NEWSAPI_KEY:
        for q in ['Hungary Tisza', 'Orban Fidesz', 'Hungary Druzhba',
                  'Hungary EU loan Ukraine', 'Hungary Paks Rosatom']:
            try:
                _add(_fetch_newsapi(q))
            except Exception as e:
                print(f'[Hungary NewsAPI] error: {str(e)[:80]}')

    # ── Brave fallback (when primary sources thin) ──
    if len(all_articles) < BRAVE_FALLBACK_MIN_ARTICLES and BRAVE_API_KEY:
        print(f'[Hungary] Triggering Brave fallback: only {len(all_articles)} articles so far')
        try:
            _add(_fetch_all_brave())
        except Exception as e:
            print(f'[Hungary Brave] error: {str(e)[:80]}')

    print(f'[Hungary] Total deduplicated articles: {len(all_articles)}')
    return all_articles


def _score_actor(actor_key, actor_cfg, articles):
    """
    Score a single actor against the article pool.
    Returns dict with statement_count, escalation_level, top_articles, etc.
    """
    keywords = actor_cfg.get('keywords', [])
    tripwires = actor_cfg.get('tripwires', [])
    baseline = actor_cfg.get('baseline_statements_per_week', 5)

    matched_articles = []
    matched_keywords_seen = set()
    tripwire_hits = []

    for art in articles:
        title = (art.get('title') or '').lower()
        desc  = (art.get('description') or '').lower()
        text  = title + ' ' + desc
        if not text.strip():
            continue

        kw_hits = [kw for kw in keywords if kw.lower() in text]
        if not kw_hits:
            continue

        tw_hits = [tw for tw in tripwires if tw.lower() in text]
        if tw_hits:
            tripwire_hits.extend(tw_hits)

        # Intensity tags (severity, not volume) + source class
        sev_high = any(term in text for term in SEVERITY_HIGH)
        sev_med  = (not sev_high) and any(term in text for term in SEVERITY_MEDIUM)
        feed_type = (art.get('feed_type') or '').lower()
        src_name  = ((art.get('source') or {}).get('name') or '').lower()
        is_social = (feed_type in ('telegram', 'bluesky')
                     or 'telegram' in src_name or 'bluesky' in src_name)

        matched_keywords_seen.update(kw_hits)
        matched_articles.append({
            **art,
            '_matched_keywords': kw_hits[:5],
            '_tripwire_hits':    tw_hits[:3],
            '_sev_high':         sev_high,
            '_sev_med':          sev_med,
            '_is_social':        is_social,
        })

    statement_count = len(matched_articles)

    # --- Severity-driven escalation level (v1.1 calibration) ---
    # Language intensity sets the tier; article volume only moves the level
    # WITHIN the ordinary-politics band (cap L2). Social-only signals
    # (Telegram / Bluesky) can flag early warning but cap at L2 unless a
    # non-social source corroborates.
    high_all       = [a for a in matched_articles if a.get('_sev_high')]
    med_all        = [a for a in matched_articles if a.get('_sev_med')]
    high_nonsocial = [a for a in high_all if not a.get('_is_social')]
    med_nonsocial  = [a for a in med_all  if not a.get('_is_social')]

    if statement_count == 0:
        level = 0
    elif high_all:                       # genuine unrest / violence
        if not high_nonsocial:
            level = 2                    # social-only early warning
        elif len(high_nonsocial) >= 2:
            level = 5                    # multiple corroborated reports
        else:
            level = 4                    # single corroborated report
    elif med_all:                        # coercion / confrontation
        if not med_nonsocial:
            level = 2                    # social-only early warning
        elif len(med_nonsocial) >= 3:
            level = 4
        else:
            level = 3
    else:                                # ordinary politics -> cap L2
        if statement_count <= max(1, baseline * 0.5):
            level = 1
        else:
            level = 2

    # Tripwires are surfaced as event flags only (see tripwire_hits in the
    # return); they no longer auto-raise the level. Many Hungary tripwires
    # are de-escalatory realignment events, so the old +1 bump inflated the
    # score. Directionality is handled by the signal interpreter.

    # Sort + top_articles for surface
    matched_articles.sort(
        key=lambda a: (len(a.get('_matched_keywords', [])),
                       len(a.get('_tripwire_hits', []))),
        reverse=True,
    )
    top_articles = matched_articles[:10]

    return {
        'name':              actor_cfg['name'],
        'flag':              actor_cfg.get('flag', ''),
        'icon':              actor_cfg.get('icon', '⚪'),
        'color':             actor_cfg.get('color', '#6b7280'),
        'role':              actor_cfg.get('role', ''),
        'description':       actor_cfg.get('description', ''),
        'statement_count':   statement_count,
        'escalation_level':  level,
        'escalation_label':  ESCALATION_LEVELS[level]['label'],
        'escalation_color':  ESCALATION_LEVELS[level]['color'],
        'escalation_icon':   ESCALATION_LEVELS[level]['icon'],
        'top_articles':      top_articles,
        'matched_keywords':  sorted(matched_keywords_seen)[:30],
        'tripwire_hits':     list(set(tripwire_hits))[:10],
        'baseline':          baseline,
    }


def _detect_cross_theater_signals(articles, actor_results):
    """
    Detect axis-reversal + Orban-revival patterns; emit fingerprints.
    """
    text_blob = ''
    for art in articles:
        text_blob += ' ' + (art.get('title') or '').lower()
        text_blob += ' ' + (art.get('description') or '').lower()

    # Count axis-reversal triggers present
    reversal_hits = [t for t in AXIS_REVERSAL_TRIGGERS if t in text_blob]
    revival_hits  = [t for t in ORBAN_REVIVAL_TRIGGERS  if t in text_blob]

    axis_reversal_active = len(reversal_hits) >= 3
    orban_revival_signal = len(revival_hits) >= 2

    # Druzhba status enum
    druzhba_status = 'unknown'
    if 'druzhba resumed' in text_blob or 'druzhba flow' in text_blob:
        druzhba_status = 'flowing'
    elif 'druzhba damage' in text_blob or 'druzhba halted' in text_blob:
        druzhba_status = 'disrupted'
    elif 'druzhba repair' in text_blob:
        druzhba_status = 'repairing'

    # Emit cross-theater fingerprints (best-effort, non-blocking)
    # Group A: pattern-level signals (booleans + enum)
    # Group B: per-actor escalation levels (read by Russia + Ukraine + GPI)
    try:
        # Group A -- pattern signals
        _crossteater_update('hungary_axis_reversal_active', axis_reversal_active)
        _crossteater_update('hungary_orban_revival_signal', orban_revival_signal)
        _crossteater_update('druzhba_pipeline_status', druzhba_status)

        # Group B -- per-actor escalation levels (0-5 scale)
        # Added May 18 2026 -- enables Russia + Ukraine cross-theater reads
        _crossteater_update(
            'hungary_government_level',
            actor_results.get('hungary_government', {}).get('escalation_level', 0)
        )
        _crossteater_update(
            'hungary_opposition_level',
            actor_results.get('hungary_opposition', {}).get('escalation_level', 0)
        )
        _crossteater_update(
            'hungary_eu_track_level',
            actor_results.get('hungary_eu_track', {}).get('escalation_level', 0)
        )
        _crossteater_update(
            'hungary_russia_axis_level',
            actor_results.get('hungary_russia_axis', {}).get('escalation_level', 0)
        )
        _crossteater_update(
            'hungary_ukraine_track_level',
            actor_results.get('hungary_ukraine_track', {}).get('escalation_level', 0)
        )
    except Exception as e:
        print(f'[Hungary Crossteater] emission error: {str(e)[:80]}')

    return {
        'axis_reversal_active':  axis_reversal_active,
        'axis_reversal_hits':    reversal_hits,
        'orban_revival_signal':  orban_revival_signal,
        'orban_revival_hits':    revival_hits,
        'druzhba_pipeline_status': druzhba_status,
    }


def _compute_theatre_score(actor_results, cross_theater):
    """
    Composite Hungary 'theatre' score:
      - Weighted sum of actor escalation levels
      - Penalized by axis_reversal_active (lower theatre tension when reversal active)
      - Boosted by orban_revival_signal (rising opposition pressure)
    """
    level_sum = sum(a.get('escalation_level', 0) for a in actor_results.values())
    avg_level = level_sum / max(len(actor_results), 1)

    score = int(avg_level * 20)  # 0-100 scale

    if cross_theater.get('axis_reversal_active'):
        score = max(0, score - 15)  # De-tensioning event
    if cross_theater.get('orban_revival_signal'):
        score = min(100, score + 15)  # Counter-revival pressure

    # Map to canonical level
    if score >= 80:    level = 5
    elif score >= 65:  level = 4
    elif score >= 50:  level = 3
    elif score >= 30:  level = 2
    elif score >= 15:  level = 1
    else:              level = 0

    return {
        'theatre_score':  score,
        'theatre_level':  level,
        'theatre_label':  ESCALATION_LEVELS[level]['label'],
        'theatre_color':  ESCALATION_LEVELS[level]['color'],
        'theatre_icon':   ESCALATION_LEVELS[level]['icon'],
    }


# ============================================================
# MAIN SCAN ENTRY POINT
# ============================================================
def run_hungary_scan():
    """
    Run a full Hungary rhetoric scan.
    Returns dict ready for caching + JSON serialization.
    """
    start = time.time()

    articles = _gather_articles()
    total_articles = len(articles)

    actor_results = {}
    for actor_key, actor_cfg in ACTORS.items():
        actor_results[actor_key] = _score_actor(actor_key, actor_cfg, articles)

    cross_theater = _detect_cross_theater_signals(articles, actor_results)
    theatre = _compute_theatre_score(actor_results, cross_theater)

    # Try interpreter (may not be available; graceful)
    interpretation = {}
    try:
        from hungary_signal_interpreter import interpret_signals
        scan_data = {
            'actors': actor_results,
            'theatre_score': theatre['theatre_score'],
            'theatre_level': theatre['theatre_level'],
            'cross_theater':  cross_theater,
        }
        interpretation = interpret_signals(scan_data) or {}
    except ImportError:
        interpretation = {'note': 'hungary_signal_interpreter not yet deployed'}
    except Exception as e:
        interpretation = {'error': str(e)[:200]}

    elapsed = round(time.time() - start, 2)

    result = {
        'success':         True,
        'target':          'hungary',
        'version':         VERSION,
        'actors':          actor_results,
        'total_articles':  total_articles,
        'cross_theater':   cross_theater,
        'interpretation':  interpretation,
        **theatre,
        'scanned_at':      datetime.now(timezone.utc).isoformat(),
        'scan_duration_s': elapsed,
        'from_cache':      False,
    }

    # Cache + history
    _redis_set(RHETORIC_CACHE_KEY, result, ttl=RHETORIC_CACHE_TTL)
    _write_canonical_spoke_fingerprint(result)   # Rim Emission Pass -- feed the Russia wheel

    # Update history
    try:
        history = _redis_get(HISTORY_KEY) or []
        if not isinstance(history, list):
            history = []
        history.append({
            'scanned_at':     result['scanned_at'],
            'theatre_score':  result['theatre_score'],
            'theatre_level':  result['theatre_level'],
            'total_articles': result['total_articles'],
            'axis_reversal_active': cross_theater.get('axis_reversal_active', False),
            'orban_revival_signal': cross_theater.get('orban_revival_signal', False),
        })
        history = history[-HISTORY_RETENTION:]
        _redis_set(HISTORY_KEY, history, ttl=86400 * 90)
    except Exception as e:
        print(f'[Hungary] history write error: {str(e)[:80]}')

    print(f'[Hungary] Scan complete in {elapsed}s; theatre L{theatre["theatre_level"]} '
          f'({theatre["theatre_label"]}); articles={total_articles}')
    return result


# ============================================================
# FLASK ROUTE REGISTRATION
# ============================================================
def register_hungary_rhetoric_endpoints(app):
    """Register Hungary rhetoric tracker endpoints on Flask app.

    Naming convention matches existing Europe backend trackers
    (Russia/Belarus/Ukraine all use _endpoints).
    """
    from flask import jsonify, request

    @app.route('/api/rhetoric/hungary', methods=['GET'])
    def hungary_rhetoric():
        force = request.args.get('force', '').lower() in ('true', '1', 'yes')

        if not force:
            cached = _redis_get(RHETORIC_CACHE_KEY)
            if cached:
                cached['from_cache'] = True
                return jsonify(cached)

        # Force-scan path (or no cache)
        try:
            # Light locking to prevent thundering herd
            lock = _redis_get(SCAN_LOCK_KEY)
            if lock and not force:
                # Another scan is running; serve cached
                cached = _redis_get(RHETORIC_CACHE_KEY)
                if cached:
                    cached['from_cache'] = True
                    cached['scan_locked'] = True
                    return jsonify(cached)

            _redis_set(SCAN_LOCK_KEY, 'locked', ttl=SCAN_LOCK_TTL)
            try:
                result = run_hungary_scan()
            finally:
                # Clear lock by setting short TTL
                _redis_set(SCAN_LOCK_KEY, '', ttl=1)

            return jsonify(result)
        except Exception as e:
            print(f'[Hungary] scan error: {e}')
            cached = _redis_get(RHETORIC_CACHE_KEY)
            if cached:
                cached['from_cache'] = True
                cached['scan_error'] = str(e)[:200]
                return jsonify(cached)
            return jsonify({'success': False, 'error': str(e)[:200]}), 503

    @app.route('/api/rhetoric/hungary/summary', methods=['GET'])
    def hungary_rhetoric_summary():
        cached = _redis_get(RHETORIC_CACHE_KEY)
        if not cached:
            return jsonify({'success': False, 'error': 'No data yet -- trigger a scan first'}), 404

        actors = cached.get('actors', {})
        interp = cached.get('interpretation', {}) or {}
        so_what = interp.get('so_what', {}) or {}
        red_lines = interp.get('red_lines', {}) or {}
        cross_theater = cached.get('cross_theater', {}) or {}
        top_red_lines = (red_lines.get('triggered') or [])[:3]

        return jsonify({
            'success':         True,
            'theatre_score':   cached.get('theatre_score', 0),
            'theatre_level':   cached.get('theatre_level', 0),
            'theatre_label':   cached.get('theatre_label', ''),
            'theatre_color':   cached.get('theatre_color', '#6b7280'),
            'hungary_government_level':  actors.get('hungary_government', {}).get('escalation_level', 0),
            'hungary_opposition_level':  actors.get('hungary_opposition', {}).get('escalation_level', 0),
            'hungary_eu_track_level':    actors.get('hungary_eu_track', {}).get('escalation_level', 0),
            'hungary_russia_axis_level': actors.get('hungary_russia_axis', {}).get('escalation_level', 0),
            'hungary_ukraine_track_level': actors.get('hungary_ukraine_track', {}).get('escalation_level', 0),
            'total_articles':            cached.get('total_articles', 0),
            # Cross-theater fingerprints
            'axis_reversal_active':      cross_theater.get('axis_reversal_active', False),
            'orban_revival_signal':      cross_theater.get('orban_revival_signal', False),
            'druzhba_pipeline_status':   cross_theater.get('druzhba_pipeline_status', 'unknown'),
            # So-What
            'so_what_scenario':          so_what.get('scenario', ''),
            'so_what_scenario_color':    so_what.get('scenario_color', '#6b7280'),
            'so_what_scenario_icon':     so_what.get('scenario_icon', '⚪'),
            'so_what_situation':         so_what.get('situation', ''),
            'so_what_assessment':        so_what.get('assessment', ''),
            'so_what_watch_list':        so_what.get('watch_list', [])[:5],
            # Red Lines
            'red_lines_breached':        red_lines.get('breached_count', 0),
            'red_lines_approaching':     red_lines.get('approaching_count', 0),
            'top_red_lines':             top_red_lines,
            'scanned_at':                cached.get('scanned_at', ''),
            'from_cache':                True,
        })

    @app.route('/api/rhetoric/hungary/history', methods=['GET'])
    def hungary_rhetoric_history():
        history = _redis_get(HISTORY_KEY) or []
        return jsonify({'success': True, 'history': history, 'count': len(history)})

    print('[Hungary Rhetoric] Endpoints registered: /api/rhetoric/hungary, /summary, /history')


# ============================================================
# BACKGROUND REFRESH (mirrors Russia/Belarus/Ukraine pattern)
# ============================================================
# 12-hour cadence background scanner that keeps Hungary tracker
# data fresh without depending on /force=true calls from the
# stability page or other consumers.

_REFRESH_INTERVAL_SECONDS = 12 * 3600  # 12 hours
_refresh_thread = None
_refresh_stop_event = None


def _background_refresh_loop():
    """Daemon loop -- runs run_hungary_scan() every 12 hours."""
    global _refresh_stop_event
    import time as _time
    while _refresh_stop_event is not None and not _refresh_stop_event.is_set():
        try:
            print('[Hungary Background] Starting scheduled scan...')
            result = run_hungary_scan()
            print(f'[Hungary Background] Scan complete: '
                  f'L{result.get("theatre_level", "?")} '
                  f'({result.get("theatre_label", "?")}), '
                  f'{result.get("total_articles", 0)} articles')
        except Exception as e:
            print(f'[Hungary Background] Scan error: {str(e)[:120]}')
        # Sleep in 60s chunks so the daemon can respond to stop signal
        for _ in range(_REFRESH_INTERVAL_SECONDS // 60):
            if _refresh_stop_event.is_set():
                return
            _time.sleep(60)


def start_background_refresh():
    """Start the 12hr background refresh thread (idempotent).

    Called once from app.py during Flask init. Mirrors the pattern
    used by rhetoric_tracker_russia / _belarus / _ukraine.
    """
    global _refresh_thread, _refresh_stop_event
    if _refresh_thread and _refresh_thread.is_alive():
        print('[Hungary Background] Refresh thread already running')
        return
    _refresh_stop_event = threading.Event()
    _refresh_thread = threading.Thread(
        target=_background_refresh_loop,
        daemon=True,
        name='HungaryRhetoricRefresh',
    )
    _refresh_thread.start()
    print('[Hungary Background] 12hr refresh thread started')


def stop_background_refresh():
    """Stop the background refresh thread (called on shutdown)."""
    global _refresh_stop_event
    if _refresh_stop_event is not None:
        _refresh_stop_event.set()
        print('[Hungary Background] Refresh thread signaled to stop')


# ============================================================
# MODULE METADATA
# ============================================================
__version__ = VERSION
__module_id__ = 'rhetoric_tracker_hungary'
print(f'[Hungary Rhetoric] Module loaded -- v{VERSION}')
