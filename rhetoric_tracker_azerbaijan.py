"""
Asifah Analytics - Azerbaijan Four-Wheel Rhetoric Tracker
v1.0.0 - June 2026

ANALYTICAL FRAME - Outbound, agent model (NOT inverted):
Azerbaijan is an active balancer, not a passive recipient of pressure. Baku
plays its patrons against each other: leaning toward Ankara, rupturing with
Moscow, sparring with Tehran, and running a quiet axis with Jerusalem - all at
once, on purpose. This tracker reads Baku as an AGENT working four wheels
simultaneously, and is the platform's first true four-wheel spoke: it writes a
spoke fingerprint to Turkey, Russia, Iran, AND Israel, plus a cross-theater
slice so the resistance-axis trackers can read Baku.

SIX VECTORS (issue-axes, each a bilateral relationship with its own polarity):
  turkey_axis        - Ankara alignment: "one nation two states", Shusha
                       Declaration, OST, defense co-production, corridor
                       patronage. Polarity: ALIGNMENT (reinforcing).
  russia_rupture     - Moscow decoupling: AZAL-crash fallout, Ekaterinburg,
                       embassy strikes, CSTO drift, transport severing.
                       Polarity: RUPTURE (the live wire).
  iran_friction      - Tehran adversarial: border drills, Israeli-platform
                       accusations, South-Azerbaijan question, Zangezur threat.
                       Polarity: FRICTION.
  israel_axis        - Jerusalem axis: oil exports, drone / air-defense buys,
                       intel-platform framing. Polarity: AXIS (Iran-facing).
  armenia_corridor   - The convergence object: TRIPP / Zangezur, peace-treaty
                       track, Syunik, delimitation, "Western Azerbaijan". Where
                       all four wheels collide.
  domestic_legitimacy- Baseline: Aliyev consolidation, elections, crackdown,
                       COP29 aftermath, revanchist framing.

ESCALATION MODEL (intensity ladder - how ACTIVE a vector is, not its polarity;
polarity lives in each spoke fingerprint's 'relationship' field):
  Level 0 - Baseline:      Routine diplomatic noise
  Level 1 - Rhetoric:      Statements, declarations, framing
  Level 2 - Maneuvering:   Concrete moves - deals, visits, drills, signings
  Level 3 - Friction:      Significant escalation / intensification
  Level 4 - Confrontation: Crisis-level activity - recalls, incidents, major pacts
  Level 5 - Rupture:       Maximal - rupture, kinetic, treaty, ambassadorial recall

SPOKE-AND-WHEEL (canonical spoke fingerprint schema, hub-agnostic):
  Writes spoke:turkey:azerbaijan, spoke:russia:azerbaijan,
         spoke:iran:azerbaijan, spoke:israel:azerbaijan  (180d TTL)
  Each: {spoke, hub, vector, relationship, level, score, direction, top_signal, ts}
  Plus a cross-theater slice fingerprints['azerbaijan'] in the shared registry
  so Iran / Israel (resistance-axis readers) can see Baku.

REDIS KEYS:
  Cache:        rhetoric:azerbaijan:latest
  History:      rhetoric:azerbaijan:history
  Cross-theater: rhetoric:crosstheater:fingerprints  (WRITES azerbaijan slice)
  Spokes:       spoke:{turkey,russia,iran,israel}:azerbaijan

ENDPOINTS:
  GET /api/rhetoric/azerbaijan
  GET /api/rhetoric/azerbaijan/summary
  GET /api/rhetoric/azerbaijan/history

CHANGELOG:
  v1.0.0 (2026-06-28): Initial build - four-wheel agent tracker (6 vectors,
                       4 spoke fingerprints + cross-theater slice)

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import json
import threading
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from flask import jsonify, request

# ============================================
# CONFIG
# ============================================
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

try:
    from telegram_signals_europe import fetch_azerbaijan_telegram_signals
    TELEGRAM_AVAILABLE = True
    print("[Azerbaijan Rhetoric] Telegram signals available")
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[Azerbaijan Rhetoric] Telegram signals not available - RSS/GDELT only")

try:
    from azerbaijan_signal_interpreter import interpret_signals as azerbaijan_interpret_signals
    INTERPRETER_AVAILABLE = True
    print("[Azerbaijan Rhetoric] Signal interpreter loaded")
except ImportError:
    INTERPRETER_AVAILABLE = False
    print("[Azerbaijan Rhetoric] Signal interpreter not available")

RHETORIC_CACHE_KEY  = 'rhetoric:azerbaijan:latest'
HISTORY_KEY         = 'rhetoric:azerbaijan:history'
BASELINE_KEY        = 'rhetoric_baseline:azerbaijan'
CROSSTHEATER_KEY    = 'rhetoric:crosstheater:fingerprints'

RHETORIC_CACHE_TTL  = 6 * 3600   # 6 hours
SCAN_INTERVAL_HOURS = 6
HISTORY_MAX_ENTRIES = 120
SPOKE_TTL           = 180 * 24 * 3600   # 180 days

# The four wheels and the polarity of Baku's relationship with each.
WHEEL_VECTORS = {
    'turkey': {'vector': 'turkey_axis',     'relationship': 'alignment'},
    'russia': {'vector': 'russia_rupture',  'relationship': 'rupture'},
    'iran':   {'vector': 'iran_friction',   'relationship': 'friction'},
    'israel': {'vector': 'israel_axis',     'relationship': 'axis'},
}

_rhetoric_running = False
_rhetoric_lock    = threading.Lock()


# ============================================
# ESCALATION LEVELS (intensity ladder)
# ============================================
ESCALATION_LEVELS = {
    0: {'label': 'Baseline',       'color': '#6b7280', 'description': 'Routine diplomatic noise'},
    1: {'label': 'Rhetoric',       'color': '#3b82f6', 'description': 'Statements, declarations, framing - no concrete moves'},
    2: {'label': 'Maneuvering',    'color': '#f59e0b', 'description': 'Concrete moves - deals, visits, drills, signings'},
    3: {'label': 'Friction',       'color': '#f97316', 'description': 'Significant escalation / intensification of the relationship'},
    4: {'label': 'Confrontation',  'color': '#ef4444', 'description': 'Crisis-level activity - recalls, incidents, major pacts'},
    5: {'label': 'Rupture',        'color': '#b91c1c', 'description': 'Maximal - rupture, kinetic, treaty, ambassadorial recall'},
}


# ============================================
# ACTORS (six bilateral vectors)
# ============================================
ACTORS = {

    'turkey_axis': {
        'name': 'Turkey Axis (Ankara)',
        'flag': '🇹🇷', 'icon': '🤝',
        'color': '#dc2626',
        'role': 'Patron Alignment - "One Nation, Two States"',
        'description': 'Ankara-Baku alignment: Shusha Declaration, Organization of Turkic States, defense co-production, corridor patronage',
        'keywords': [
            'azerbaijan turkey', 'baku ankara', 'turkey azerbaijan',
            'one nation two states', 'two states one nation',
            'shusha declaration', 'organization of turkic states',
            'turkic states summit', 'azerbaijan turkey defense',
            'azerbaijan turkey military', 'azerbaijan turkey alliance',
            'erdogan aliyev', 'aliyev erdogan', 'azerbaijan turkey gas',
            'azerbaijan turkey corridor', 'turkey azerbaijan drone',
            'azerbaijan bayraktar', 'azerbaijan turkey pipeline',
            'tanap', 'azerbaijan turkey trade', 'azerbaijan turkey pact',
            'azerbaijan turkey joint', 'azerbaijan turkey brotherhood',
            # Azerbaijani / Turkish
            'azərbaycan türkiyə', 'bir millət iki dövlət', 'şuşa bəyannaməsi',
            'azerbaycan türkiye', 'iki devlet tek millet', 'türk dövlətləri',
        ],
        'baseline_statements_per_week': 11,
        'weight': 1.1,
    },

    'russia_rupture': {
        'name': 'Russia Rupture (Moscow)',
        'flag': '🇷🇺', 'icon': '⚡',
        'color': '#b91c1c',
        'role': 'Decoupling Patron - The Live Wire',
        'description': 'Moscow-Baku decoupling: AZAL-crash fallout, Ekaterinburg, embassy strikes, CSTO drift, transport severing',
        'keywords': [
            'azerbaijan russia', 'baku moscow', 'russia azerbaijan',
            'azerbaijan airlines crash', 'azal crash', 'azal plane',
            'azerbaijan plane shot', 'ekaterinburg azerbaijani',
            'azerbaijan russia tension', 'azerbaijan russia embassy',
            'russia azerbaijan strike', 'azerbaijan russia row',
            'azerbaijan russia diplomatic', 'azerbaijan csto',
            'sputnik azerbaijan', 'russian house baku', 'rossotrudnichestvo baku',
            'azerbaijan russia detain', 'azerbaijan russia arrest',
            'azerbaijan russia compensation', 'azerbaijan russia apology',
            'azerbaijan russia border', 'azerbaijan russia transit',
            'azerbaijan russia gas', 'azerbaijan ukraine cooperation',
            'aliyev putin', 'putin aliyev',
            # Russian / Azerbaijani
            'азербайджан россия', 'баку москва', 'крушение azal',
            'azərbaycan rusiya', 'rusiya azərbaycan',
        ],
        'baseline_statements_per_week': 9,
        'weight': 1.3,
    },

    'iran_friction': {
        'name': 'Iran Friction (Tehran)',
        'flag': '🇮🇷', 'icon': '⚔️',
        'color': '#f97316',
        'role': 'Adversarial Neighbor',
        'description': 'Tehran friction: border drills, Israeli-platform accusations, South-Azerbaijan question, Zangezur threat to Iran',
        'keywords': [
            'azerbaijan iran', 'baku tehran', 'iran azerbaijan',
            'iran azerbaijan border', 'iran azerbaijan drill',
            'iran military exercise azerbaijan', 'iran azerbaijan tension',
            'iran azerbaijan israel', 'azerbaijan israel iran',
            'south azerbaijan', 'iranian azeris', 'iranian azerbaijanis',
            'iran zangezur', 'iran armenia border', 'iran azerbaijan embassy',
            'iran azerbaijan attack', 'azerbaijan iran spy',
            'iran azerbaijan mossad', 'iran azerbaijan accusation',
            'iran azerbaijan warning', 'iran azerbaijan threat',
            'iran azerbaijan corridor', 'iran caspian azerbaijan',
            # Farsi / Azerbaijani
            'ایران آذربایجان', 'آذربایجان اسرائیل', 'azərbaycan iran',
            'güney azərbaycan', 'iran azərbaycan',
        ],
        'baseline_statements_per_week': 7,
        'weight': 1.15,
    },

    'israel_axis': {
        'name': 'Israel Axis (Jerusalem)',
        'flag': '🇮🇱', 'icon': '🛰️',
        'color': '#0ea5e9',
        'role': 'Quiet Axis - Iran-Facing',
        'description': 'Jerusalem axis: oil exports (~40% of Israeli supply), drone / air-defense procurement, intel-platform framing',
        'keywords': [
            'azerbaijan israel', 'baku tel aviv', 'israel azerbaijan',
            'azerbaijan israel oil', 'azerbaijan oil israel',
            'azerbaijan israel drone', 'azerbaijan israeli weapons',
            'azerbaijan harop', 'azerbaijan barak', 'azerbaijan israel defense',
            'socar israel', 'azerbaijan israel embassy', 'azerbaijan israel ties',
            'azerbaijan israel trade', 'azerbaijan israel intelligence',
            'azerbaijan israel platform', 'azerbaijan israel base',
            'azerbaijan israel cooperation', 'azerbaijan israel arms',
            'azerbaijan israel energy', 'baku jerusalem',
            # Azerbaijani / Hebrew
            'azərbaycan israil', 'israil azərbaycan', 'אזרבייג׳ן ישראל',
        ],
        'baseline_statements_per_week': 6,
        'weight': 1.0,
    },

    'armenia_corridor': {
        'name': 'Armenia / Corridor (TRIPP)',
        'flag': '🇦🇲', 'icon': '🛣️',
        'color': '#8b5cf6',
        'role': 'The Convergence Object',
        'description': 'Where all four wheels collide: TRIPP / Zangezur corridor, peace-treaty track, Syunik, delimitation, "Western Azerbaijan"',
        'keywords': [
            'azerbaijan armenia', 'armenia azerbaijan', 'zangezur corridor',
            'zangezur', 'syunik', 'tripp', 'trump route', 'trump corridor',
            'armenia azerbaijan peace', 'azerbaijan armenia treaty',
            'azerbaijan armenia border', 'border delimitation armenia',
            'nagorno-karabakh', 'nagorno karabakh', 'karabakh',
            'nakhchivan corridor', 'western azerbaijan', 'aliyev armenia',
            'pashinyan aliyev', 'aliyev pashinyan', 'armenia azerbaijan deal',
            'azerbaijan armenia summit', 'lachin', 'armenia azerbaijan talks',
            'azerbaijan armenia delimitation', 'crossroads of peace',
            # Azerbaijani / Armenian
            'azərbaycan ermənistan', 'zəngəzur dəhlizi', 'qarabağ',
            'ermənistan azərbaycan',
        ],
        'baseline_statements_per_week': 10,
        'weight': 1.2,
    },

    'domestic_legitimacy': {
        'name': 'Domestic Legitimacy (Baku)',
        'flag': '🇦🇿', 'icon': '🏛️',
        'color': '#3b82f6',
        'role': 'Regime Baseline',
        'description': 'Aliyev consolidation, elections, crackdown on press / civil society, COP29 aftermath, revanchist framing',
        'keywords': [
            'aliyev', 'ilham aliyev', 'azerbaijan election',
            'azerbaijan opposition', 'azerbaijan crackdown',
            'azerbaijan journalist arrest', 'azerbaijan press freedom',
            'azerbaijan human rights', 'azerbaijan political prisoners',
            'mehriban aliyeva', 'azerbaijan constitution', 'cop29 baku',
            'azerbaijan corruption', 'azerbaijan protest', 'azerbaijan dissent',
            'azerbaijan civil society', 'azerbaijan referendum',
            'azerbaijan parliament', 'azerbaijan reform', 'azerbaijan succession',
            # Azerbaijani
            'əliyev', 'azərbaycan seçki', 'azərbaycan müxalifət',
        ],
        'baseline_statements_per_week': 13,
        'weight': 0.85,
    },

}


# ============================================
# RSS FEEDS
# ============================================
RSS_FEEDS = [
    # Independent / regional (friction, Armenia, domestic)
    'https://eurasianet.org/rss.xml',
    'https://oc-media.org/feed/',
    # Google News - per vector
    'https://news.google.com/rss/search?q=azerbaijan+turkey+OR+baku+ankara+OR+turkic+states&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=azerbaijan+russia+OR+baku+moscow+OR+azal+crash&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=azerbaijan+iran+OR+baku+tehran+OR+south+azerbaijan&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=azerbaijan+israel+OR+azerbaijan+oil+israel+OR+azerbaijan+drones&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=azerbaijan+armenia+OR+zangezur+corridor+OR+tripp+OR+peace+treaty&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=aliyev+azerbaijan+OR+azerbaijan+opposition+OR+western+azerbaijan&hl=en&gl=US&ceid=US:en',
]

GDELT_QUERIES = [
    # English - per vector
    ('azerbaijan turkey alliance corridor', 'eng'),
    ('azerbaijan russia tension crash embassy', 'eng'),
    ('azerbaijan iran border israel tehran', 'eng'),
    ('azerbaijan israel oil drones defense', 'eng'),
    ('azerbaijan armenia peace zangezur tripp', 'eng'),
    ('aliyev azerbaijan opposition western azerbaijan', 'eng'),
    # Russian - strengthens the russia_rupture read
    ('азербайджан россия', 'rus'),
    # Turkish - strengthens the turkey_axis read
    ('azerbaycan turkiye', 'tur'),
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
        print(f'[Azerbaijan Rhetoric] Redis GET error ({key}): {e}')
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
        print(f'[Azerbaijan Rhetoric] Redis SET error ({key}): {e}')
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
        print(f'[Azerbaijan Rhetoric] Redis LPUSH error: {e}')


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
        print(f'[Azerbaijan Rhetoric] RSS error ({url[:60]}): {str(e)[:80]}')
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
        print(f'[Azerbaijan Rhetoric] GDELT error ({query[:40]}): {str(e)[:80]}')
    return articles


def _fetch_all_articles(days=5):
    """Fetch from all RSS feeds and GDELT queries, deduplicated by URL."""
    all_articles = []
    seen_urls = set()

    print(f'[Azerbaijan Rhetoric] Fetching RSS feeds ({len(RSS_FEEDS)} feeds)...')
    for feed_url in RSS_FEEDS:
        arts = _fetch_rss(feed_url)
        for a in arts:
            if a['url'] and a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)
        time.sleep(0.3)

    print(f'[Azerbaijan Rhetoric] Fetching GDELT ({len(GDELT_QUERIES)} queries)...')
    for query, lang in GDELT_QUERIES:
        arts = _fetch_gdelt(query, lang=lang, days=days)
        for a in arts:
            if a['url'] and a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)
        time.sleep(0.5)

    print(f'[Azerbaijan Rhetoric] Total articles after dedup: {len(all_articles)}')
    return all_articles


# ============================================
# SCORING ENGINE
# ============================================
def _score_actor(actor_id, actor_cfg, articles, telegram_msgs):
    """Score a single vector across all articles and Telegram messages."""
    keywords  = [kw.lower() for kw in actor_cfg['keywords']]
    hits      = []
    hit_count = 0

    for art in articles:
        body = art.get('body', '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            hit_count += len(matched)
            hits.append({
                'title':     art.get('title', '')[:150],
                'url':       art.get('url', ''),
                'source':    art.get('source', ''),
                'published': art.get('published', ''),
                'matched_keywords': matched[:5],
            })

    tg_hits = 0
    for msg in telegram_msgs:
        body = msg.get('title', '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            tg_hits += len(matched)
            hit_count += len(matched)

    baseline = actor_cfg.get('baseline_statements_per_week', 8)
    weight   = actor_cfg.get('weight', 1.0)
    raw_score = min(100, int((hit_count / max(baseline, 1)) * 25 * weight))

    if raw_score >= 85:   level = 5
    elif raw_score >= 65: level = 4
    elif raw_score >= 45: level = 3
    elif raw_score >= 28: level = 2
    elif raw_score >= 12: level = 1
    else:                 level = 0

    level_info = ESCALATION_LEVELS[level]
    return {
        'actor':            actor_id,
        'name':             actor_cfg['name'],
        'flag':             actor_cfg['flag'],
        'icon':             actor_cfg['icon'],
        'color':            actor_cfg['color'],
        'role':             actor_cfg['role'],
        'raw_score':        raw_score,
        'level':            level,
        'label':            level_info['label'],
        'escalation_color': level_info['color'],
        'description':      level_info['description'],
        'article_hits':     len(hits),
        'keyword_hits':     hit_count,
        'telegram_hits':    tg_hits,
        'top_articles':     hits[:5],
    }


def _wheel_top_signal(hub, relationship, level):
    """Templated estimative one-liner for a spoke fingerprint, by wheel + intensity."""
    band = {
        'turkey': {
            4: 'Ankara-Baku axis at acute intensity - major pact or defense signal',
            3: 'Turkey-Azerbaijan alignment intensifying',
            2: 'Active Turkey-Azerbaijan coordination',
            1: 'Routine Turkey-Azerbaijan alignment rhetoric',
            0: 'Turkey-Azerbaijan axis quiet',
        },
        'russia': {
            4: 'Baku-Moscow rupture at crisis pitch - recalls / strikes / detentions',
            3: 'Russia-Azerbaijan decoupling deepening',
            2: 'Active Russia-Azerbaijan friction - concrete moves',
            1: 'Russia-Azerbaijan strain in rhetoric',
            0: 'Russia-Azerbaijan channel quiet',
        },
        'iran': {
            4: 'Tehran-Baku friction at confrontation level - drills / accusations',
            3: 'Iran-Azerbaijan friction escalating',
            2: 'Active Iran-Azerbaijan friction',
            1: 'Iran-Azerbaijan friction in rhetoric',
            0: 'Iran-Azerbaijan friction dormant',
        },
        'israel': {
            4: 'Baku-Jerusalem axis at acute activity - major arms / energy signal',
            3: 'Israel-Azerbaijan axis intensifying',
            2: 'Active Israel-Azerbaijan axis - arms / oil',
            1: 'Israel-Azerbaijan axis in routine activity',
            0: 'Israel-Azerbaijan axis quiet',
        },
    }
    return band.get(hub, {}).get(level, f'{hub} {relationship} L{level}')


def _compute_composite(actor_scores):
    """
    Four-wheel agent composite for Azerbaijan. Russia (rupture) and the Armenia
    corridor (convergence object) are the live drivers; Iran, Turkey, and Israel
    are the other wheels; domestic legitimacy is baseline context. Builds the
    per-wheel spoke fingerprints and the cross-theater slice.
    """
    tk = actor_scores.get('turkey_axis',         {})
    ru = actor_scores.get('russia_rupture',      {})
    ir = actor_scores.get('iran_friction',       {})
    il = actor_scores.get('israel_axis',         {})
    am = actor_scores.get('armenia_corridor',    {})
    dm = actor_scores.get('domestic_legitimacy', {})

    tk_raw = tk.get('raw_score', 0); tk_lvl = tk.get('level', 0)
    ru_raw = ru.get('raw_score', 0); ru_lvl = ru.get('level', 0)
    ir_raw = ir.get('raw_score', 0); ir_lvl = ir.get('level', 0)
    il_raw = il.get('raw_score', 0); il_lvl = il.get('level', 0)
    am_raw = am.get('raw_score', 0); am_lvl = am.get('level', 0)
    dm_raw = dm.get('raw_score', 0); dm_lvl = dm.get('level', 0)

    # Composite weighting (sums to 1.0): Russia rupture + Armenia corridor lead.
    composite = (
        ru_raw * 0.22 +
        am_raw * 0.20 +
        ir_raw * 0.18 +
        tk_raw * 0.16 +
        il_raw * 0.14 +
        dm_raw * 0.10
    )
    composite = min(100, int(composite))

    if composite >= 85:   theatre_level = 5
    elif composite >= 65: theatre_level = 4
    elif composite >= 45: theatre_level = 3
    elif composite >= 28: theatre_level = 2
    elif composite >= 12: theatre_level = 1
    else:                 theatre_level = 0

    level_info = ESCALATION_LEVELS[theatre_level]

    # Contested-node read: how many wheels are simultaneously active (>= L2)
    wheel_levels = {'turkey': tk_lvl, 'russia': ru_lvl, 'iran': ir_lvl, 'israel': il_lvl}
    active_wheels = [w for w, lv in wheel_levels.items() if lv >= 2]
    contested_node_score = len(active_wheels)
    is_contested_node = contested_node_score >= 3

    # Convergence read (spoke-side: multiple wheels on Baku; estimative, absence-honest)
    convergence_signal = ''
    if is_contested_node:
        convergence_signal = ('🎯 Four-wheel contested node: ' +
                              ', '.join(w.title() for w in active_wheels) +
                              ' simultaneously active on Baku')
    elif ru_lvl >= 3 and tk_lvl >= 2:
        convergence_signal = '⚡ Russia rupture deepening as Ankara patronage firms - Baku rebalancing west'
    elif ir_lvl >= 3 and il_lvl >= 2:
        convergence_signal = '⚔️ Iran friction tracking Israel-axis intensity - the Baku triangle is live'
    elif am_lvl >= 3:
        convergence_signal = '🛣️ Zangezur / TRIPP corridor activity elevated - the four-wheel convergence object is hot'
    elif ru_lvl >= 3:
        convergence_signal = '⚡ Baku-Moscow rupture at elevated intensity'
    elif tk_lvl >= 3:
        convergence_signal = '🤝 Turkey-Azerbaijan axis intensifying'
    elif contested_node_score >= 2:
        convergence_signal = ('📡 Two wheels active on Baku: ' +
                              ', '.join(w.title() for w in active_wheels))

    # Per-wheel spoke fingerprints (canonical schema; direction + ts stamped at write time)
    spoke_fingerprints = {}
    raw_by_hub = {'turkey': tk_raw, 'russia': ru_raw, 'iran': ir_raw, 'israel': il_raw}
    for hub, meta in WHEEL_VECTORS.items():
        lvl = wheel_levels[hub]
        spoke_fingerprints[hub] = {
            'spoke':        'azerbaijan',
            'hub':          hub,
            'vector':       meta['vector'],
            'relationship': meta['relationship'],
            'level':        lvl,
            'score':        raw_by_hub[hub],
            'direction':    'steady',   # stamped from prior history at write time
            'top_signal':   _wheel_top_signal(hub, meta['relationship'], lvl),
            # 'ts' stamped at write time
        }

    # Cross-theater slice (read by the resistance-axis trackers via the shared registry)
    crosstheater_slice = {
        'theatre':                'azerbaijan',
        'composite_score':        composite,
        'composite_level':        theatre_level,
        'turkey_axis_level':      tk_lvl,
        'russia_rupture_level':   ru_lvl,
        'iran_friction_level':    ir_lvl,
        'israel_axis_level':      il_lvl,
        'armenia_corridor_level': am_lvl,
        'is_contested_node':      is_contested_node,
        'contested_node_score':   contested_node_score,
        # 'ts' stamped at write time
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
        # Per-vector levels (frontend breakdown + summary)
        'turkey_axis_level':        tk_lvl,
        'russia_rupture_level':     ru_lvl,
        'iran_friction_level':      ir_lvl,
        'israel_axis_level':        il_lvl,
        'armenia_corridor_level':   am_lvl,
        'domestic_legitimacy_level': dm_lvl,
        # Highest single-wheel intensity (drives the frontend Intensity Ladder).
        # Distinct from theatre_level, which is the weighted composite.
        'peak_wheel_level':         max(tk_lvl, ru_lvl, ir_lvl, il_lvl, am_lvl, dm_lvl),
        # Contested-node read
        'active_wheels':            active_wheels,
        'contested_node_score':     contested_node_score,
        'is_contested_node':        is_contested_node,
        # Fingerprints
        'spoke_fingerprints':       spoke_fingerprints,
        'crosstheater_slice':       crosstheater_slice,
    }


def _write_crosstheater_fingerprint(crosstheater_slice):
    """Merge Azerbaijan's slice into the shared cross-theater registry."""
    try:
        existing = _redis_get(CROSSTHEATER_KEY) or {}
        slice_copy = dict(crosstheater_slice)
        slice_copy['ts'] = datetime.now(timezone.utc).isoformat()
        existing['azerbaijan'] = slice_copy
        _redis_set(CROSSTHEATER_KEY, existing)
        print('[Azerbaijan Rhetoric] Cross-theater slice written to shared registry')
    except Exception as e:
        print(f'[Azerbaijan Rhetoric] Cross-theater write error: {str(e)[:100]}')


def _prior_wheel_levels():
    """Read the most recent history entry's per-wheel levels (for direction)."""
    try:
        if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
            return {}
        resp = requests.get(
            f'{UPSTASH_REDIS_URL}/lindex/{HISTORY_KEY}/0',
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=5
        )
        raw = resp.json().get('result')
        if not raw:
            return {}
        prev = json.loads(raw)
        return {
            'turkey': prev.get('turkey_axis_level', 0),
            'russia': prev.get('russia_rupture_level', 0),
            'iran':   prev.get('iran_friction_level', 0),
            'israel': prev.get('israel_axis_level', 0),
        }
    except Exception:
        return {}


# ============================================
# MAIN SCAN
# ============================================
def run_azerbaijan_rhetoric_scan(days=5):
    """Full scan: fetch articles, score all six vectors, return structured result."""
    print(f'[Azerbaijan Rhetoric] Starting scan (days={days})...')
    start_time = time.time()

    articles = _fetch_all_articles(days=days)

    telegram_msgs = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_msgs = fetch_azerbaijan_telegram_signals(hours_back=days * 24) or []
            print(f'[Azerbaijan Rhetoric] Telegram: {len(telegram_msgs)} messages')
        except Exception as e:
            print(f'[Azerbaijan Rhetoric] Telegram error: {e}')

    actor_scores = {}
    for actor_id, actor_cfg in ACTORS.items():
        actor_scores[actor_id] = _score_actor(actor_id, actor_cfg, articles, telegram_msgs)
        print(f'[Azerbaijan Rhetoric] {actor_cfg["name"]}: L{actor_scores[actor_id]["level"]} ({actor_scores[actor_id]["raw_score"]}/100)')

    composite = _compute_composite(actor_scores)

    elapsed = round(time.time() - start_time, 1)
    now = datetime.now(timezone.utc).isoformat()

    all_top = []
    seen = set()
    for scores in actor_scores.values():
        for art in scores.get('top_articles', []):
            if art['url'] not in seen:
                seen.add(art['url'])
                all_top.append(art)
    all_top = all_top[:20]

    result = {
        'success':               True,
        'theatre':               'Azerbaijan',
        'version':               '1.0.0',
        'timestamp':             now,
        'scanned_at':            now,
        'scan_duration_seconds': elapsed,
        'total_articles':        len(articles),
        'telegram_messages':     len(telegram_msgs),
        **composite,
        'actors':                actor_scores,
        'top_articles':          all_top,
        'theatre_score':         composite['theatre_score'],
        'is_strike_actor':       False,
        'is_contested_node':     composite['is_contested_node'],
    }

    # Signal interpretation -- So What, Red Lines, Historical (Slice 2)
    if INTERPRETER_AVAILABLE:
        try:
            result['rumint_articles'] = articles
            result['rumint_telegram'] = telegram_msgs
            result['rumint_reddit']   = []
            result['interpretation'] = azerbaijan_interpret_signals(result)
            for _k in ('rumint_articles', 'rumint_telegram', 'rumint_reddit'):
                result.pop(_k, None)
            result['rumint'] = (result['interpretation'] or {}).get('rumint')
        except Exception as ie:
            print(f'[Azerbaijan Rhetoric] Interpreter error: {str(ie)[:100]}')

        try:
            from azerbaijan_signal_interpreter import build_top_signals
            result['top_signals'] = build_top_signals(result)
            print(f'[Azerbaijan Rhetoric] top_signals: {len(result["top_signals"])} emitted')
        except Exception as e:
            print(f'[Azerbaijan Rhetoric] build_top_signals error: {str(e)[:120]}')
            result['top_signals'] = []

    print(f'[Azerbaijan Rhetoric] Scan complete in {elapsed}s | '
          f'Theatre L{composite["theatre_level"]} ({composite["theatre_score"]}/100) | '
          f'contested={composite["contested_node_score"]}/4 | '
          f'{composite["convergence_signal"] or "No convergence signal"}')
    return result


# ============================================
# BACKGROUND SCAN
# ============================================
def _bg_scan():
    """Run scan and write to Redis cache + history + spoke fingerprints."""
    global _rhetoric_running
    try:
        result = run_azerbaijan_rhetoric_scan()

        # Direction per wheel (compare to prior history entry BEFORE we lpush)
        prior = _prior_wheel_levels()

        _redis_set(RHETORIC_CACHE_KEY, result, ttl=RHETORIC_CACHE_TTL)

        history_entry = {
            'timestamp':                 result['timestamp'],
            'theatre_score':             result['theatre_score'],
            'theatre_level':             result['theatre_level'],
            'theatre_label':             result['theatre_label'],
            'turkey_axis_level':         result['turkey_axis_level'],
            'russia_rupture_level':      result['russia_rupture_level'],
            'iran_friction_level':       result['iran_friction_level'],
            'israel_axis_level':         result['israel_axis_level'],
            'armenia_corridor_level':    result['armenia_corridor_level'],
            'domestic_legitimacy_level': result['domestic_legitimacy_level'],
            'contested_node_score':      result['contested_node_score'],
            'convergence_signal':        result['convergence_signal'],
        }
        _redis_lpush(HISTORY_KEY, history_entry)

        # Spoke-and-wheel: write the four canonical spoke fingerprints (180d TTL).
        now_iso = datetime.now(timezone.utc).isoformat()
        spokes = result.get('spoke_fingerprints', {})
        for hub, fp in spokes.items():
            try:
                prev_lvl = prior.get(hub)
                cur_lvl  = fp.get('level', 0)
                if prev_lvl is None:
                    fp['direction'] = 'steady'
                elif cur_lvl > prev_lvl:
                    fp['direction'] = 'rising'
                elif cur_lvl < prev_lvl:
                    fp['direction'] = 'falling'
                else:
                    fp['direction'] = 'steady'
                fp['ts'] = now_iso
                _redis_set(f'spoke:{hub}:azerbaijan', fp, ttl=SPOKE_TTL)
            except Exception as _se:
                print(f'[Azerbaijan Rhetoric] spoke:{hub}:azerbaijan write skipped: {_se}')

        # Cross-theater slice for the resistance-axis readers
        _write_crosstheater_fingerprint(result.get('crosstheater_slice', {}))

        print('[Azerbaijan Rhetoric] Cache + history + 4 spoke fingerprints written')
    except Exception as e:
        print(f'[Azerbaijan Rhetoric] Background scan error: {e}')
    finally:
        with _rhetoric_lock:
            _rhetoric_running = False


# ============================================
# FLASK ROUTE REGISTRATION
# ============================================
def register_azerbaijan_rhetoric_endpoints(app):

    def _periodic():
        time.sleep(180)   # 3-minute stagger after boot
        print('[Azerbaijan Rhetoric] Starting initial scan...')
        _bg_scan()
        while True:
            print(f'[Azerbaijan Rhetoric] Sleeping {SCAN_INTERVAL_HOURS}h...')
            time.sleep(SCAN_INTERVAL_HOURS * 3600)
            _bg_scan()

    threading.Thread(target=_periodic, daemon=True).start()
    print(f'[Azerbaijan Rhetoric] Periodic scan thread started ({SCAN_INTERVAL_HOURS}h cycle)')

    @app.route('/api/rhetoric/azerbaijan', methods=['GET'])
    def azerbaijan_rhetoric():
        force = request.args.get('force', '').lower() in ('true', '1', 'yes')
        days  = int(request.args.get('days', 5))

        if force:
            try:
                return jsonify(run_azerbaijan_rhetoric_scan(days=days))
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
            'theatre':                  'Azerbaijan',
            'theatre_score':            0,
            'theatre_escalation_level': 0,
            'theatre_escalation_label': 'Scanning...',
            'theatre_escalation_color': '#6b7280',
            'message':                  'First scan in progress - fetching Azerbaijan / South-Caucasus sources...',
            'version':                  '1.0.0',
        })

    @app.route('/api/rhetoric/azerbaijan/summary', methods=['GET'])
    def azerbaijan_rhetoric_summary():
        cached = _redis_get(RHETORIC_CACHE_KEY)
        if cached:
            actors = cached.get('actors', {})
            return jsonify({
                'success':                  True,
                'theatre':                  'Azerbaijan',
                'theatre_score':            cached.get('theatre_score', 0),
                'theatre_level':            cached.get('theatre_level', 0),
                'theatre_escalation_level': cached.get('theatre_escalation_level', 0),
                'theatre_escalation_label': cached.get('theatre_escalation_label', 'Baseline'),
                'theatre_escalation_color': cached.get('theatre_escalation_color', '#6b7280'),
                'theatre_label':            cached.get('theatre_label', 'Baseline'),
                'theatre_color':            cached.get('theatre_color', '#6b7280'),
                # Per-wheel levels
                'turkey_axis_level':        cached.get('turkey_axis_level', 0),
                'russia_rupture_level':     cached.get('russia_rupture_level', 0),
                'iran_friction_level':      cached.get('iran_friction_level', 0),
                'israel_axis_level':        cached.get('israel_axis_level', 0),
                'armenia_corridor_level':   cached.get('armenia_corridor_level', 0),
                'domestic_legitimacy_level': cached.get('domestic_legitimacy_level', 0),
                # Contested-node read
                'active_wheels':            cached.get('active_wheels', []),
                'contested_node_score':     cached.get('contested_node_score', 0),
                'is_contested_node':        cached.get('is_contested_node', False),
                'convergence_signal':       cached.get('convergence_signal', ''),
                'spoke_fingerprints':       cached.get('spoke_fingerprints', {}),
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
            'theatre':       'Azerbaijan',
            'message':       'No cached data - scan in progress',
        })

    @app.route('/api/rhetoric/azerbaijan/history', methods=['GET'])
    def azerbaijan_rhetoric_history():
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
                'theatre': 'Azerbaijan',
                'count':   len(entries),
                'entries': entries,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    print('[Azerbaijan Rhetoric] Routes registered: '
          '/api/rhetoric/azerbaijan, /api/rhetoric/azerbaijan/summary, '
          '/api/rhetoric/azerbaijan/history')
