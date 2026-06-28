"""
Asifah Analytics - Cyprus Division Pressure Rhetoric Tracker (Dial 2)
v1.0.0 - June 2026

ANALYTICAL FRAME - Inverted threat model:
The Republic of Cyprus (Greek-Cypriot south, EU member) is the status-quo /
sovereignty-defense actor and is NOT the source of pressure. Its internal
governance is the calm Dial 1, anchored separately. The threat LANGUAGE
originates externally and inbound: Turkey (Ankara) is the primary pressure
actor, the Turkish-Cypriot north (TRNC) the secondary, and the frozen division
generates the live pressure on the island's status quo. The reader reads
INBOUND pressure ON Cyprus, not Cypriot posturing outward. This module is
Dial 2 - the live division / inbound-Turkey gauge.

VECTORS (issue-axes, not an actor roster):
  turkey_posture    - Ankara stance: two-state framing, troop posture, drilling
                      authorizations, Blue Homeland claims. PRIMARY inbound
                      driver; also feeds the Turkey hub-and-spoke layer.
  trnc_politics     - Turkish-Cypriot north: Tatar, elections, settler moves,
                      Varosha, Ankara's grip on the north.
  green_line        - Buffer-zone / UNFICYP / crossing incidents, military
                      movement along the ceasefire line.
  eez_maritime      - Gas / EEZ / drillship disputes, delimitation friction,
                      NAVTEX standoffs with Turkey.
  settlement_track  - Settlement-track FRICTION (deadlock, two-state push,
                      collapse, walkouts) - collapse-biased, not progress.

ESCALATION MODEL (inverted):
  Level 0 - Baseline:      Normal diplomatic noise, no division pressure
  Level 1 - Rhetoric:      Turkish / TRNC statements (two-state, EEZ) - no operational signals
  Level 2 - Pressure:      Active Turkish coercion - drillship deployment, troop signaling
  Level 3 - Crisis:        RoC / Greece / EU protests, UNFICYP incident, drillship standoff, talks collapse
  Level 4 - Confrontation: Military incident in buffer zone / EEZ, unilateral TRNC move, Greece-Turkey spillover
  Level 5 - Rupture:       Armed clash, forced-partition move, abrogation of buffer-zone arrangements

REDIS KEYS:
  Cache:    rhetoric:cyprus:latest
  History:  rhetoric:cyprus:history
  Spoke:    spoke:turkey:cyprus  (turkey_posture fingerprint for the hub-and-spoke)

ENDPOINTS:
  GET /api/rhetoric/cyprus
  GET /api/rhetoric/cyprus/summary
  GET /api/rhetoric/cyprus/history

CHANGELOG:
  v1.0.0 (2026-06-25): Initial build - inverted, vectored Dial-2 tracker (5 issue-vectors)

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import json
import threading
import time
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from flask import jsonify, request

# ============================================
# CONFIG
# ============================================
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

try:
    from telegram_signals_europe import fetch_cyprus_telegram_signals
    TELEGRAM_AVAILABLE = True
    print("[Cyprus Rhetoric] ✅ Telegram signals available")
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[Cyprus Rhetoric] ⚠️ Telegram signals not available — RSS/GDELT only")

try:
    from cyprus_signal_interpreter import interpret_signals as cyprus_interpret_signals
    INTERPRETER_AVAILABLE = True
    print("[Cyprus Rhetoric] ✅ Signal interpreter loaded")
except ImportError:
    INTERPRETER_AVAILABLE = False
    print("[Cyprus Rhetoric] ⚠️ Signal interpreter not available")

RHETORIC_CACHE_KEY  = 'rhetoric:cyprus:latest'
HISTORY_KEY         = 'rhetoric:cyprus:history'
BASELINE_KEY        = 'rhetoric_baseline:cyprus'

RHETORIC_CACHE_TTL  = 6 * 3600   # 6 hours
SCAN_INTERVAL_HOURS = 6
HISTORY_MAX_ENTRIES = 120

_rhetoric_running = False
_rhetoric_lock    = threading.Lock()


# ============================================
# ESCALATION LEVELS
# ============================================
ESCALATION_LEVELS = {
    0: {'label': 'Baseline',       'color': '#6b7280', 'description': 'Normal diplomatic noise - no division pressure'},
    1: {'label': 'Rhetoric',       'color': '#3b82f6', 'description': 'Turkish / TRNC public statements (two-state, EEZ claims) - no operational signals'},
    2: {'label': 'Pressure',       'color': '#f59e0b', 'description': 'Active Turkish coercion - drillship deployment, troop signaling, settlement hardening'},
    3: {'label': 'Crisis',         'color': '#f97316', 'description': 'RoC / Greece / EU formal protests, UNFICYP incident, drillship standoff, talks collapse'},
    4: {'label': 'Confrontation',  'color': '#ef4444', 'description': 'Military incident in buffer zone / EEZ, unilateral TRNC move (Varosha), Greece-Turkey spillover'},
    5: {'label': 'Rupture',        'color': '#b91c1c', 'description': 'Armed clash, forced-partition move, abrogation of buffer-zone arrangements'},
}


# ============================================
# ACTORS
# ============================================
ACTORS = {

    'turkey_posture': {
        'name': 'Turkey Posture (Ankara)',
        'flag': '🇹🇷', 'icon': '🇹🇷',
        'color': '#dc2626',
        'role': 'Primary Pressure Actor - Inbound',
        'description': 'Ankara stance toward Cyprus: two-state framing, troop posture, drilling authorizations, Blue Homeland claims',
        'keywords': [
            'turkey cyprus', 'ankara cyprus', 'erdogan cyprus',
            'turkey two-state cyprus', 'turkish cyprus sovereignty',
            'turkey troops cyprus', 'turkish military cyprus',
            'turkey northern cyprus', 'erdogan northern cyprus',
            'turkey drilling cyprus', 'turkey eez cyprus',
            'turkish warship cyprus', 'turkey gas cyprus',
            'blue homeland', 'mavi vatan', 'turkey mediterranean claim',
            'turkey cyprus airspace', 'turkish navtex cyprus',
            'turkey cyprus ultimatum', 'ankara two-state',
            'turkey recognizes trnc', 'turkey cyprus base',
            'turkish drillship', 'turkey hydrocarbon cyprus',
            'turkey cyprus warning', 'turkey cyprus settlers',
            'turkey defends trnc', 'turkey cyprus provocation',
        ],
        'baseline_statements_per_week': 10,
        'weight': 1.4,   # primary inbound driver - overweighted
    },

    'trnc_politics': {
        'name': 'Turkish-Cypriot North (TRNC)',
        'flag': '🟧', 'icon': '🏛️',
        'color': '#f59e0b',
        'role': 'Secondary Pressure - North',
        'description': 'Turkish-Cypriot north: Tatar, elections, settler moves, Varosha, Ankara grip',
        'keywords': [
            'trnc', 'northern cyprus', 'turkish republic northern cyprus',
            'ersin tatar', 'tatar cyprus', 'turkish cypriot leader',
            'north cyprus election', 'turkish cypriot election',
            'varosha', 'maras cyprus', 'varosha reopening',
            'settlers northern cyprus', 'turkish settlers cyprus',
            'north cyprus politics', 'turkish cypriot parliament',
            'north cyprus president', 'two-state cyprus north',
            'trnc declaration', 'north cyprus annexation',
            'turkish cypriot opposition', 'north cyprus economy turkey',
        ],
        'baseline_statements_per_week': 7,
        'weight': 1.1,
    },

    'green_line': {
        'name': 'Green Line / Buffer Zone (UNFICYP)',
        'flag': '🚧', 'icon': '🚧',
        'color': '#3b82f6',
        'role': 'Division Line - Buffer / UNFICYP',
        'description': 'Buffer-zone / UNFICYP / crossing incidents, military movement along the ceasefire line',
        'keywords': [
            'green line cyprus', 'buffer zone cyprus', 'unficyp',
            'un buffer zone cyprus', 'ledra crossing', 'crossing points cyprus',
            'green line incident', 'buffer zone incident',
            'cyprus ceasefire line', 'national guard cyprus buffer',
            'turkish forces buffer zone', 'pyla cyprus', 'pyla incident',
            'unficyp mandate', 'un peacekeepers cyprus',
            'green line violation', 'buffer zone construction',
            'cyprus demarcation', 'ledra palace',
        ],
        'baseline_statements_per_week': 6,
        'weight': 1.0,
    },

    'eez_maritime': {
        'name': 'EEZ / Maritime & Gas',
        'flag': '🛢️', 'icon': '🛢️',
        'color': '#0ea5e9',
        'role': 'Maritime / EEZ Friction',
        'description': 'Gas / EEZ / drillship disputes, delimitation friction, NAVTEX standoffs with Turkey',
        'keywords': [
            'cyprus eez', 'cyprus exclusive economic zone', 'cyprus gas',
            'aphrodite gas', 'calypso cyprus', 'glaucus cyprus',
            'cyprus drilling', 'cyprus drillship', 'cyprus offshore gas',
            'cyprus hydrocarbon', 'cyprus turkey maritime',
            'cyprus continental shelf', 'eastern mediterranean gas cyprus',
            'cyprus exploration block', 'cyprus navtex', 'exxonmobil cyprus',
            'eni cyprus', 'total cyprus', 'cyprus gas dispute',
            'cyprus maritime delimitation', 'cyprus seismic survey',
            'cyprus turkey drilling standoff',
        ],
        'baseline_statements_per_week': 7,
        'weight': 1.2,
    },

    'settlement_track': {
        'name': 'Settlement-Track Friction',
        'flag': '🕊️', 'icon': '🕊️',
        'color': '#8b5cf6',
        'role': 'Settlement-Track Friction (collapse-biased)',
        'description': 'Settlement-track friction: deadlock, two-state push, collapse, walkouts - NOT progress',
        'keywords': [
            'cyprus settlement talks', 'cyprus reunification', 'cyprus peace talks',
            'cyprus negotiations', 'bizonal bicommunal', 'cyprus federal solution',
            'cyprus two-state', 'crans-montana cyprus', 'cyprus un talks',
            'cyprus settlement collapse', 'cyprus talks deadlock',
            'cyprus talks fail', 'cyprus negotiations stall',
            'cyprus two-state push', 'cyprus confidence building',
            'cyprus guterres', 'un cyprus envoy', 'cyprus comprehensive settlement',
            'cyprus talks walkout', 'cyprus reunification deadlock',
            'cyprus informal talks', 'cyprus 5+1',
        ],
        'baseline_statements_per_week': 6,
        'weight': 0.9,
    },

}


# ============================================
# RSS FEEDS
# ============================================
RSS_FEEDS = [
    # Local source (reliable)
    'https://cyprus-mail.com/feed/',
    # Google News - per vector
    'https://news.google.com/rss/search?q=cyprus+turkey+OR+cyprus+eez+OR+cyprus+drilling&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=cyprus+green+line+OR+unficyp+OR+buffer+zone+cyprus&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=northern+cyprus+OR+trnc+OR+ersin+tatar+OR+varosha&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=cyprus+settlement+talks+OR+cyprus+reunification+OR+cyprus+two-state&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=cyprus+gas+OR+aphrodite+OR+cyprus+maritime+turkey&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=erdogan+cyprus+OR+ankara+cyprus+OR+turkey+northern+cyprus&hl=en&gl=US&ceid=US:en',
]

# ============================================
# NITTER FEEDS — Primary source Twitter/X accounts
# Mirror fallback: if mirror 1 fails, try mirror 2, etc.
# No API key required — public RSS.
# ============================================
NITTER_MIRRORS = [
    "nitter.poast.org",
    "nitter.privacydev.net",
    "nitter.woodland.cafe",
]

# Account list: (username, weight, description)
# Weight > 1.0 = primary source (direct government statement)
NITTER_ACCOUNTS = [
    # Cyprus Dial-2 runs on RSS + GDELT. Nitter instances are unreliable, so no
    # accounts are wired here; add high-confidence handles later if they stabilize.
]


def _fetch_nitter(username, weight=1.0, timeout=8):
    """
    Fetch RSS for a Twitter/X account via Nitter mirror fallback.
    Tries each mirror in order until one succeeds.
    Returns list of articles with source tagged as 'Nitter @{username}'.
    """
    articles = []
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; AsifahAnalytics/1.0)'}

    for mirror in NITTER_MIRRORS:
        url = f'https://{mirror}/{username}/rss'
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall('.//item')[:20]:
                title_el   = item.find('title')
                link_el    = item.find('link')
                pubdate_el = item.find('pubDate')
                desc_el    = item.find('description')
                if title_el is None:
                    continue
                title = title_el.text or ''
                link  = link_el.text if link_el is not None else ''
                pub   = ''
                if pubdate_el is not None and pubdate_el.text:
                    try:
                        pub = parsedate_to_datetime(pubdate_el.text).isoformat()
                    except Exception:
                        pub = pubdate_el.text or ''
                desc = ''
                if desc_el is not None and desc_el.text:
                    # Strip HTML tags from Nitter descriptions
                    import re
                    desc = re.sub(r'<[^>]+>', '', desc_el.text)[:300]
                articles.append({
                    'title':     title,
                    'url':       link,
                    'published': pub,
                    'source':    f'Nitter @{username}',
                    'body':      f'{title} {desc}'.lower(),
                    'nitter_weight': weight,
                })
            if articles:
                print(f'[Cyprus Rhetoric/Nitter] @{username}: {len(articles)} posts via {mirror}')
                return articles  # Success — don't try other mirrors
        except Exception as e:
            print(f'[Cyprus Rhetoric/Nitter] @{username} mirror {mirror} failed: {str(e)[:60]}')
            continue

    if not articles:
        print(f'[Cyprus Rhetoric/Nitter] @{username}: all mirrors failed')
    return articles


def _fetch_all_nitter(days=5):
    """Fetch from all Nitter accounts and filter by recency."""
    import re
    all_posts = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for username, weight, desc in NITTER_ACCOUNTS:
        posts = _fetch_nitter(username, weight=weight)
        for p in posts:
            # Filter to recency window
            if p.get('published'):
                try:
                    pub_dt = datetime.fromisoformat(p['published'].replace('Z', '+00:00'))
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass
            all_posts.append(p)
        time.sleep(0.4)

    print(f'[Cyprus Rhetoric/Nitter] Total posts: {len(all_posts)}')
    return all_posts


GDELT_QUERIES = [
    # English - per vector
    ('cyprus turkey two-state sovereignty', 'eng'),
    ('cyprus eez gas drilling turkey', 'eng'),
    ('cyprus green line unficyp buffer zone', 'eng'),
    ('northern cyprus trnc tatar varosha', 'eng'),
    ('cyprus settlement talks reunification', 'eng'),
    ('erdogan cyprus ankara mediterranean', 'eng'),
    # Turkish-language - strengthens the turkey_posture / TRNC read
    ('kibris turkiye eez', 'tur'),
]


# ============================================
# REDIS HELPERS
# ============================================
def _redis_get(key):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        resp = requests.get(
            f'{UPSTASH_REDIS_URL}/get/{key}',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=5
        )
        result = resp.json().get('result')
        return json.loads(result) if result else None
    except Exception as e:
        print(f'[Cyprus Rhetoric] Redis GET error ({key}): {e}')
        return None


def _redis_set(key, value, ttl=None):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return False
    try:
        payload = json.dumps(value, default=str)
        params = {'EX': ttl} if ttl else {}
        resp = requests.post(
            f'{UPSTASH_REDIS_URL}/set/{key}',
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json'
            },
            data=payload,
            params=params,
            timeout=5
        )
        return resp.json().get('result') == 'OK'
    except Exception as e:
        print(f'[Cyprus Rhetoric] Redis SET error ({key}): {e}')
        return False


def _redis_lpush(key, value, max_len=HISTORY_MAX_ENTRIES):
    """Push to Redis list with trim."""
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return
    try:
        payload = json.dumps(value, default=str)
        requests.post(
            f'{UPSTASH_REDIS_URL}/lpush/{key}',
            headers={
                'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                'Content-Type': 'application/json'
            },
            data=json.dumps([payload]),
            timeout=5
        )
        requests.post(
            f'{UPSTASH_REDIS_URL}/ltrim/{key}/0/{max_len - 1}',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=5
        )
    except Exception as e:
        print(f'[Cyprus Rhetoric] Redis LPUSH error: {e}')


# ============================================
# ARTICLE FETCHING
# ============================================
def _fetch_rss(url, timeout=10):
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AsifahAnalytics/1.0)'}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return articles
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item')[:15]:
            title_el   = item.find('title')
            link_el    = item.find('link')
            pubdate_el = item.find('pubDate')
            desc_el    = item.find('description')
            if title_el is None:
                continue
            title = title_el.text or ''
            link  = link_el.text  if link_el  is not None else ''
            pub   = ''
            if pubdate_el is not None and pubdate_el.text:
                try:
                    pub = parsedate_to_datetime(pubdate_el.text).isoformat()
                except Exception:
                    pub = pubdate_el.text or ''
            desc = desc_el.text[:300] if desc_el is not None and desc_el.text else ''
            articles.append({
                'title':     title,
                'url':       link,
                'published': pub,
                'source':    url,
                'body':      f'{title} {desc}'.lower(),
            })
    except Exception as e:
        print(f'[Cyprus Rhetoric] RSS error ({url[:60]}): {str(e)[:80]}')
    return articles


def _fetch_gdelt(query, lang='eng', days=5, timeout=15):
    """Fetch articles from GDELT v2 doc API."""
    articles = []
    try:
        params = {
            'query':      query,
            'mode':       'artlist',
            'maxrecords': 50,
            'timespan':   f'{days}d',
            'sourcelang': lang,
            'format':     'json',
        }
        url = 'https://api.gdeltproject.org/api/v2/doc/doc'
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code != 200:
            return articles
        data = resp.json()
        for art in data.get('articles', []):
            articles.append({
                'title':     art.get('title', ''),
                'url':       art.get('url', ''),
                'published': art.get('seendate', ''),
                'source':    art.get('domain', ''),
                'body':      f"{art.get('title', '')} {art.get('url', '')}".lower(),
            })
    except Exception as e:
        print(f'[Cyprus Rhetoric] GDELT error ({query[:40]}): {str(e)[:80]}')
    return articles


def _fetch_all_articles(days=5):
    """Fetch from all RSS feeds and GDELT queries."""
    all_articles = []
    seen_urls = set()

    print(f'[Cyprus Rhetoric] Fetching RSS feeds ({len(RSS_FEEDS)} feeds)...')
    for feed_url in RSS_FEEDS:
        arts = _fetch_rss(feed_url)
        for a in arts:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)
        time.sleep(0.3)

    print(f'[Cyprus Rhetoric] Fetching GDELT ({len(GDELT_QUERIES)} queries)...')
    for query, lang in GDELT_QUERIES:
        arts = _fetch_gdelt(query, lang=lang, days=days)
        for a in arts:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)
        time.sleep(0.5)

    # Nitter — primary source Twitter/X accounts
    print(f'[Cyprus Rhetoric] Fetching Nitter ({len(NITTER_ACCOUNTS)} accounts)...')
    nitter_posts = _fetch_all_nitter(days=days)
    for p in nitter_posts:
        if p['url'] not in seen_urls:
            seen_urls.add(p['url'])
            all_articles.append(p)

    print(f'[Cyprus Rhetoric] Total articles after dedup: {len(all_articles)}')
    return all_articles


# ============================================
# SCORING ENGINE
# ============================================
def _score_actor(actor_id, actor_cfg, articles, telegram_msgs):
    """Score a single actor across all articles and Telegram messages."""
    keywords  = [kw.lower() for kw in actor_cfg['keywords']]
    hits      = []
    hit_count = 0

    for art in articles:
        body = art.get('body', '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            hit_count += len(matched)
            hits.append({
                'title':    art.get('title', '')[:150],
                'url':      art.get('url', ''),
                'source':   art.get('source', ''),
                'published': art.get('published', ''),
                'matched_keywords': matched[:5],
            })

    # Add Telegram signals
    tg_hits = 0
    for msg in telegram_msgs:
        body = msg.get('title', '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            tg_hits += len(matched)
            hit_count += len(matched)

    # Baseline normalization
    baseline = actor_cfg.get('baseline_statements_per_week', 8)
    weight   = actor_cfg.get('weight', 1.0)
    raw_score = min(100, int((hit_count / max(baseline, 1)) * 25 * weight))

    # Map to 0–5 escalation level
    if raw_score >= 85:   level = 5
    elif raw_score >= 65: level = 4
    elif raw_score >= 45: level = 3
    elif raw_score >= 28: level = 2
    elif raw_score >= 12: level = 1
    else:                 level = 0

    level_info = ESCALATION_LEVELS[level]
    return {
        'actor':          actor_id,
        'name':           actor_cfg['name'],
        'flag':           actor_cfg['flag'],
        'icon':           actor_cfg['icon'],
        'color':          actor_cfg['color'],
        'role':           actor_cfg['role'],
        'raw_score':      raw_score,
        'level':          level,
        'label':          level_info['label'],
        'escalation_color': level_info['color'],
        'description':    level_info['description'],
        'article_hits':   len(hits),
        'keyword_hits':   hit_count,
        'telegram_hits':  tg_hits,
        'top_articles':   hits[:5],
    }


def _compute_composite(actor_scores):
    """
    Dial-2 composite division-pressure score for Cyprus (inverted model).
    Turkey posture is the primary inbound driver; EEZ + Green Line are the live
    friction axes; TRNC politics and settlement-track friction are context. The
    Republic of Cyprus's internal governance (Dial 1) is NOT scored here.
    """
    tp = actor_scores.get('turkey_posture',   {})
    tr = actor_scores.get('trnc_politics',    {})
    gl = actor_scores.get('green_line',       {})
    ez = actor_scores.get('eez_maritime',     {})
    st = actor_scores.get('settlement_track', {})

    tp_raw = tp.get('raw_score', 0)
    tr_raw = tr.get('raw_score', 0)
    gl_raw = gl.get('raw_score', 0)
    ez_raw = ez.get('raw_score', 0)
    st_raw = st.get('raw_score', 0)

    # Composite weighting (sums to 1.0): Turkey posture is the primary inbound
    # pressure; EEZ + Green Line are the live friction axes.
    composite = (
        tp_raw * 0.35 +
        ez_raw * 0.20 +
        gl_raw * 0.18 +
        tr_raw * 0.15 +
        st_raw * 0.12
    )
    composite = min(100, int(composite))

    if composite >= 85:   theatre_level = 5
    elif composite >= 65: theatre_level = 4
    elif composite >= 45: theatre_level = 3
    elif composite >= 28: theatre_level = 2
    elif composite >= 12: theatre_level = 1
    else:                 theatre_level = 0

    level_info = ESCALATION_LEVELS[theatre_level]

    # Per-vector levels (frontend Dial-2 breakdown + summary)
    turkey_posture_level = tp.get('level', 0)
    trnc_level           = tr.get('level', 0)
    green_line_level     = gl.get('level', 0)
    eez_level            = ez.get('level', 0)
    settlement_level     = st.get('level', 0)

    # Convergence read (estimative; absence stays honest)
    convergence_signal = ''
    if turkey_posture_level >= 3 and (eez_level >= 2 or green_line_level >= 2):
        convergence_signal = '⚠️ High Turkish posture converging with maritime / buffer-zone friction'
    elif turkey_posture_level >= 4:
        convergence_signal = '🚨 Turkish two-state / coercion pressure at crisis level'
    elif eez_level >= 3 and turkey_posture_level >= 2:
        convergence_signal = '🛢️ Active EEZ standoff under Turkish pressure'
    elif green_line_level >= 3:
        convergence_signal = '🚧 Elevated buffer-zone / Green Line friction'
    elif settlement_level >= 3:
        convergence_signal = '🕊️ Settlement track hardening toward deadlock / two-state framing'
    elif turkey_posture_level >= 2:
        convergence_signal = '📡 Elevated Turkish posture toward Cyprus'

    # Spoke fingerprint for the Turkey hub-and-spoke layer. Canonical hub-agnostic
    # schema so the future Turkey hub aggregator reads every spoke the same way.
    # 'direction' + 'ts' are stamped at write time in _bg_scan.
    spoke_fingerprint = {
        'spoke':        'cyprus',
        'hub':          'turkey',
        'vector':       'turkey_posture',
        'relationship': 'friction',   # Cyprus is pressured BY Turkey (inverted model)
        'level':        turkey_posture_level,
        'score':        tp_raw,
        'direction':    'steady',
        'top_signal':   convergence_signal or f'Turkey posture toward Cyprus at L{turkey_posture_level}',
        # --- back-compat (legacy hub-reader fields) ---
        'turkey_posture_score':  tp_raw,
        'turkey_posture_level':  turkey_posture_level,
        'composite_score':       composite,
        'composite_level':       theatre_level,
    }

    return {
        'theatre_score':            composite,
        'theatre_level':            theatre_level,
        'theatre_escalation_level': theatre_level,
        'theatre_escalation_label': level_info['label'],
        'theatre_escalation_color': level_info['color'],
        'theatre_label':            level_info['label'],
        'theatre_color':            level_info['color'],
        'convergence_signal':       convergence_signal,
        'turkey_posture_level':     turkey_posture_level,
        'trnc_level':               trnc_level,
        'green_line_level':         green_line_level,
        'eez_level':                eez_level,
        'settlement_level':         settlement_level,
        'spoke_fingerprint':        spoke_fingerprint,
    }


# ============================================
# MAIN SCAN
# ============================================
def run_cyprus_rhetoric_scan(days=5):
    """Full scan: fetch articles, score all actors, return structured result."""
    print(f'[Cyprus Rhetoric] Starting scan (days={days})...')
    start_time = time.time()

    # Fetch articles
    articles = _fetch_all_articles(days=days)

    # Fetch Telegram
    telegram_msgs = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_msgs = fetch_cyprus_telegram_signals(hours_back=days * 24) or []
            print(f'[Cyprus Rhetoric] Telegram: {len(telegram_msgs)} messages')
        except Exception as e:
            print(f'[Cyprus Rhetoric] Telegram error: {e}')

    # Score each actor
    actor_scores = {}
    for actor_id, actor_cfg in ACTORS.items():
        actor_scores[actor_id] = _score_actor(actor_id, actor_cfg, articles, telegram_msgs)
        print(f'[Cyprus Rhetoric] {actor_cfg["name"]}: L{actor_scores[actor_id]["level"]} ({actor_scores[actor_id]["raw_score"]}/100)')

    # Composite theatre score
    composite = _compute_composite(actor_scores)

    elapsed = round(time.time() - start_time, 1)
    now = datetime.now(timezone.utc).isoformat()

    # Top articles across all actors (deduplicated, sorted by hit count)
    all_top = []
    seen = set()
    for scores in actor_scores.values():
        for art in scores.get('top_articles', []):
            if art['url'] not in seen:
                seen.add(art['url'])
                all_top.append(art)
    all_top = all_top[:20]

    result = {
        'success':              True,
        'theatre':              'Cyprus',
        'version':              '1.0.0',
        'timestamp':            now,
        'scanned_at':           now,
        'scan_duration_seconds': elapsed,
        'total_articles':       len(articles),
        'telegram_messages':    len(telegram_msgs),
        # Composite
        **composite,
        # Per-actor
        'actors':               actor_scores,
        # Top articles
        'top_articles':         all_top,
        # Legacy fields for summary endpoint
        'theatre_score':        composite['theatre_score'],
        'is_strike_actor':      False,   # Inverted model — no strike actor
        'is_sovereignty_crisis': composite['theatre_level'] >= 3,
    }

    # Signal interpretation -- So What, Red Lines, Historical Patterns
    if INTERPRETER_AVAILABLE:
        try:
            # Attach raw corpus for the RUMINT read, then pop it after so the
            # cached payload is not bloated. Cyprus articles carry a pre-
            # lowercased 'body' (title+desc); telegram msgs carry 'title'.
            result['rumint_articles'] = articles
            result['rumint_telegram'] = telegram_msgs
            result['rumint_reddit']   = []   # reddit not yet wired for Cyprus
            result['interpretation'] = cyprus_interpret_signals(result)
            for _k in ('rumint_articles', 'rumint_telegram', 'rumint_reddit'):
                result.pop(_k, None)
            # Hand the RUMINT read up to the top level for the frontend pill.
            result['rumint'] = (result['interpretation'] or {}).get('rumint')
            breached = result['interpretation']['red_lines']['breached_count']
            scenario = result['interpretation']['so_what'].get('scenario', 'N/A')
            print(f'[Cyprus Rhetoric] Interpreter: {breached} red lines breached | {scenario}')
        except Exception as ie:
            print(f'[Cyprus Rhetoric] Interpreter error: {str(ie)[:100]}')

    # v2.0: Build top_signals[] for BLUF/GPI consumption
    if INTERPRETER_AVAILABLE:
        try:
            from cyprus_signal_interpreter import build_top_signals
            result['top_signals'] = build_top_signals(result)
            print(f'[Cyprus Rhetoric] top_signals: {len(result["top_signals"])} emitted')
        except Exception as e:
            print(f'[Cyprus Rhetoric] build_top_signals error: {str(e)[:120]}')
            result['top_signals'] = []

    print(f'[Cyprus Rhetoric] Scan complete in {elapsed}s | Theatre L{composite["theatre_level"]} ({composite["theatre_score"]}/100) | {composite["convergence_signal"] or "No convergence signal"}')
    return result


# ============================================
# BACKGROUND SCAN
# ============================================
def _bg_scan():
    """Run scan and write to Redis cache + history."""
    global _rhetoric_running
    try:
        result = run_cyprus_rhetoric_scan()
        _redis_set(RHETORIC_CACHE_KEY, result, ttl=RHETORIC_CACHE_TTL)
        # Append to history
        history_entry = {
            'timestamp':            result['timestamp'],
            'theatre_score':        result['theatre_score'],
            'theatre_level':        result['theatre_level'],
            'theatre_label':        result['theatre_label'],
            'turkey_posture_level': result['turkey_posture_level'],
            'eez_level':            result['eez_level'],
            'green_line_level':     result['green_line_level'],
            'trnc_level':           result['trnc_level'],
            'settlement_level':     result['settlement_level'],
            'convergence_signal':   result['convergence_signal'],
        }
        _redis_lpush(HISTORY_KEY, history_entry)
        # Spoke-and-wheel: write the canonical Turkey-posture fingerprint (180d TTL).
        # 'direction' compares to the prior history entry (now at lindex 1, since
        # this scan's entry was just lpushed to index 0).
        try:
            _fp = dict(result.get('spoke_fingerprint', {}))
            _cur = _fp.get('level', 0)
            _prior_tp = None
            try:
                if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                    _r = requests.get(
                        f'{UPSTASH_REDIS_URL}/lindex/{HISTORY_KEY}/1',
                        headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                        timeout=5
                    )
                    _raw = _r.json().get('result')
                    if _raw:
                        _prior_tp = json.loads(_raw).get('turkey_posture_level')
            except Exception:
                _prior_tp = None
            if _prior_tp is None:    _fp['direction'] = 'steady'
            elif _cur > _prior_tp:   _fp['direction'] = 'rising'
            elif _cur < _prior_tp:   _fp['direction'] = 'falling'
            else:                    _fp['direction'] = 'steady'
            _fp['ts'] = datetime.now(timezone.utc).isoformat()
            _redis_set('spoke:turkey:cyprus', _fp, ttl=180 * 24 * 3600)
        except Exception as _se:
            print(f'[Cyprus Rhetoric] spoke fingerprint write skipped: {_se}')
        print(f'[Cyprus Rhetoric] ✅ Cache + history written')
    except Exception as e:
        print(f'[Cyprus Rhetoric] ❌ Background scan error: {e}')
    finally:
        with _rhetoric_lock:
            _rhetoric_running = False


# ============================================
# FLASK ROUTE REGISTRATION
# ============================================
def register_cyprus_rhetoric_endpoints(app):

    def _periodic():
        time.sleep(180)   # 3-minute stagger after boot
        print('[Cyprus Rhetoric] Starting initial scan...')
        _bg_scan()
        while True:
            print(f'[Cyprus Rhetoric] Sleeping {SCAN_INTERVAL_HOURS}h...')
            time.sleep(SCAN_INTERVAL_HOURS * 3600)
            _bg_scan()

    threading.Thread(target=_periodic, daemon=True).start()
    print(f'[Cyprus Rhetoric] ✅ Periodic scan thread started ({SCAN_INTERVAL_HOURS}h cycle)')

    @app.route('/api/rhetoric/cyprus', methods=['GET'])
    def cyprus_rhetoric():
        force = request.args.get('force', '').lower() in ('true', '1', 'yes')
        days  = int(request.args.get('days', 5))

        if force:
            try:
                return jsonify(run_cyprus_rhetoric_scan(days=days))
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)[:200]}), 500

        cached = _redis_get(RHETORIC_CACHE_KEY)
        if cached:
            cached['cached'] = True
            return jsonify(cached)

        global _rhetoric_running
        with _rhetoric_lock:
            if not _rhetoric_running:
                _rhetoric_running = True
                threading.Thread(target=_bg_scan, daemon=True).start()

        return jsonify({
            'success':                  True,
            'awaiting_scan':            True,
            'theatre':                  'Cyprus',
            'theatre_score':            0,
            'theatre_escalation_level': 0,
            'theatre_escalation_label': 'Scanning...',
            'theatre_escalation_color': '#6b7280',
            'message':                  'First scan in progress — fetching Cyprus / Eastern-Mediterranean sources...',
            'version':                  '1.0.0',
        })

    @app.route('/api/rhetoric/cyprus/summary', methods=['GET'])
    def cyprus_rhetoric_summary():
        cached = _redis_get(RHETORIC_CACHE_KEY)
        if cached:
            actors = cached.get('actors', {})
            return jsonify({
                'success':                  True,
                'theatre':                  'Cyprus',
                # Composite
                'theatre_score':            cached.get('theatre_score', 0),
                'theatre_level':            cached.get('theatre_level', 0),
                'theatre_escalation_level': cached.get('theatre_escalation_level', 0),
                'theatre_escalation_label': cached.get('theatre_escalation_label', 'Baseline'),
                'theatre_escalation_color': cached.get('theatre_escalation_color', '#6b7280'),
                'theatre_label':            cached.get('theatre_label', 'Baseline'),
                'theatre_color':            cached.get('theatre_color', '#6b7280'),
                # Key signals (per-vector)
                'turkey_posture_level':     cached.get('turkey_posture_level', 0),
                'eez_level':                cached.get('eez_level', 0),
                'green_line_level':         cached.get('green_line_level', 0),
                'trnc_level':               cached.get('trnc_level', 0),
                'settlement_level':         cached.get('settlement_level', 0),
                'convergence_signal':       cached.get('convergence_signal', ''),
                'is_sovereignty_crisis':    cached.get('is_sovereignty_crisis', False),
                'spoke_fingerprint':        cached.get('spoke_fingerprint', {}),
                # Per-actor quick view
                'actor_levels': {
                    aid: {
                        'level': adat.get('level', 0),
                        'label': adat.get('label', 'Baseline'),
                        'color': adat.get('escalation_color', '#6b7280'),
                        'score': adat.get('raw_score', 0),
                    }
                    for aid, adat in actors.items()
                },
                'total_articles':   cached.get('total_articles', 0),
                'scanned_at':       cached.get('scanned_at', ''),
                'cached':           True,
            })
        return jsonify({
            'success':       False,
            'awaiting_scan': True,
            'theatre':       'Cyprus',
            'message':       'No cached data — scan in progress',
        })

    @app.route('/api/rhetoric/cyprus/history', methods=['GET'])
    def cyprus_rhetoric_history():
        try:
            limit = max(1, min(int(request.args.get('limit', 120)), 120))
            entries = []
            if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
                resp = requests.get(
                    f'{UPSTASH_REDIS_URL}/lrange/{HISTORY_KEY}/0/{limit - 1}',
                    headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                    timeout=5
                )
                for item in resp.json().get('result', []):
                    try:
                        entries.append(json.loads(item))
                    except Exception:
                        pass
            entries.reverse()
            return jsonify({
                'success': True,
                'theatre': 'Cyprus',
                'count':   len(entries),
                'entries': entries,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    print('[Cyprus Rhetoric] ✅ Routes registered: '
          '/api/rhetoric/cyprus, /api/rhetoric/cyprus/summary, '
          '/api/rhetoric/cyprus/history')
