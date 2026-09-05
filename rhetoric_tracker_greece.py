"""
Asifah Analytics - Greece Rhetoric & Pressure Tracker
v1.0.0 - June 2026  |  Europe backend (asifa-europe-backend.onrender.com)

ARCHETYPE: anchored frontline state. Greece sits at the intersection of a
primary Turkey axis (currently in managed detente, disputes frozen not
resolved), backed by EU + NATO/US anchoring, with migration-frontline exposure
and internal political pressure. Unlike Cyprus (pure inbound-pressure victim),
Greece is a PEER-RIVAL with agency -- so the Turkey vector is bidirectional and
runs ALONGSIDE a live diplomatic off-ramp (the High-Level Cooperation Council
detente). Greece writes spoke:turkey:greece (second Turkey-spoke after Cyprus).

SIX VECTORS, two panels:
  PRESSURES (external + internal strain)
    turkey_axis         - Aegean/EEZ/casus belli/Blue Homeland/East Med energy
    migration_frontline - Libya->Crete corridor, Aegean route, Evros, asylum
    domestic_pressure   - Tempi/Karystianou, Predator wiretapping, cost of living
  ANCHORS & STANDING (what backs Greece / its regional weight)
    eu_anchor           - RRF/recovery, EU solidarity, rule-of-law strain
    nato_us             - Souda Bay, Alexandroupoli, MDCA, F-35, Vertical Corridor
    regional_alignment  - 3+1 (Greece-Cyprus-Israel-US), Egypt EEZ, IMEC, UNSC seat

CROSS-TRACKER CORROBORATION (proxy-not-clone; absence-honest):
  * military:turkey:posture + military:greece:posture  (written by the ME-backend
    military tracker, shared Upstash Redis) -- operational corroboration for the
    Turkey axis. Rhetoric + drillship/Aegean posture = a live read, not declaratory.
  * greece:migration:latest  (written by the Greece migration sensor, same backend)
    -- corroborates the migration_frontline vector against actual arrivals.

DIPLOMATIC TRACK: the Greece-Turkey detente (High-Level Cooperation Council,
confidence-building measures, positive agenda) -- the first Europe tracker to
light up the dormant diplomatic card. Scenario-driven, estimative, absence-honest.

DOCTRINE: convergence, not prediction. Sensors below, analyst above. The tracker
emits raw vector levels + composite + peak; the interpreter does the estimative
read. No probabilities, no dates, no "will".

ENDPOINTS:
  GET /api/rhetoric/greece            (cache-first)
  GET /api/rhetoric/greece?force=true (bypass cache, re-scan)
  GET /api/rhetoric/greece/summary    (lightweight; banner-safe numeric levels)
  GET /api/rhetoric/greece/history     (snapshot history for the trend chart)

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import re
import json
import threading
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from flask import jsonify, request

# ============================================
# CONFIG
# ============================================
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

# Optional Telegram layer (Greek/Turkish channels can be wired later -- absence-honest).
try:
    from telegram_signals_europe import fetch_greece_telegram_signals
    TELEGRAM_AVAILABLE = True
    print("[Greece Rhetoric] Telegram signals available")
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[Greece Rhetoric] Telegram signals not available - RSS/GDELT only")

# Signal interpreter (analyst layer)
try:
    from greece_signal_interpreter import interpret_signals as greece_interpret_signals
    INTERPRETER_AVAILABLE = True
    print("[Greece Rhetoric] Signal interpreter loaded")
except ImportError:
    INTERPRETER_AVAILABLE = False
    print("[Greece Rhetoric] Signal interpreter not available")

RHETORIC_CACHE_KEY  = 'rhetoric:greece:latest'
RHETORIC_CACHE_TTL  = 12 * 3600
SCAN_INTERVAL_HOURS = 6
HISTORY_MAX_ENTRIES = 120

# Shared cross-tracker fingerprints (written by other backends, same Redis)
MILITARY_TURKEY_KEY = 'military:turkey:posture'
MILITARY_GREECE_KEY = 'military:greece:posture'
MIGRATION_KEY       = 'greece:migration:latest'

# Spoke fingerprint: Greece is a Turkey-relationship spoke (peer-rivalry, not victim)
SPOKE_FINGERPRINT_KEY = 'spoke:turkey:greece'
SPOKE_FINGERPRINT_TTL = 180 * 24 * 3600   # 180 days

_rhetoric_running = False
_rhetoric_lock    = threading.Lock()

# Aegean-relevant military signal keywords -- used to decide whether a posture
# fingerprint corroborates the Turkey axis (vs. unrelated theatre noise).
AEGEAN_MIL_KEYWORDS = [
    'aegean', 'drillship', 'navtex', 'eez', 'overflight', 'airspace', 'naval',
    'frigate', 'corvette', 'f-16', 'f16', 'east med', 'eastern mediterranean',
    'crete', 'kastellorizo', 'greece', 'greek', 'turkish navy', 'oruc reis',
    'blue homeland', 'mavi vatan', 'territorial waters', 'continental shelf',
]


# ============================================
# ESCALATION LEVELS (intensity ladder)
# ============================================
ESCALATION_LEVELS = {
    0: {'label': 'Baseline',      'color': '#6b7280', 'description': 'Routine diplomatic noise - no active friction'},
    1: {'label': 'Rhetoric',      'color': '#3b82f6', 'description': 'Statements, declarations, framing - no concrete moves'},
    2: {'label': 'Pressure',      'color': '#f59e0b', 'description': 'Concrete moves - drills, NAVTEX, deals, deportations, protests'},
    3: {'label': 'Crisis',        'color': '#f97316', 'description': 'Significant escalation - formal protest, incident, talks strain'},
    4: {'label': 'Confrontation', 'color': '#ef4444', 'description': 'Crisis-level - militarized incident, recall, casus belli activation'},
    5: {'label': 'Rupture',       'color': '#b91c1c', 'description': 'Maximal - kinetic, detente collapse, ambassadorial recall'},
}


# ============================================
# ACTORS (six vectors -- 3 PRESSURES + 3 ANCHORS)
# ============================================
PRESSURE_VECTORS = ['turkey_axis', 'migration_frontline', 'domestic_pressure']
ANCHOR_VECTORS   = ['eu_anchor', 'nato_us', 'regional_alignment']

ACTORS = {

    # ---------------- PRESSURES ----------------
    'turkey_axis': {
        'name': 'Turkey Axis (Ankara)',
        'flag': '\U0001F1F9\U0001F1F7', 'icon': '\U0001F1F9\U0001F1F7',
        'color': '#dc2626',
        'role': 'Primary Axis - Peer Rivalry (bidirectional)',
        'description': 'Aegean / EEZ delimitation, casus belli, Blue Homeland (Mavi Vatan), East Med energy (Chevron south of Crete), airspace/overflights, island militarization, Western Thrace minority, Cyprus linkage',
        'keywords': [
            'greece turkey', 'turkey greece', 'greek turkish', 'aegean', 'aegean sea',
            'casus belli', 'territorial waters', '12 nautical miles', 'twelve nautical miles',
            'continental shelf', 'greece eez', 'turkey eez', 'exclusive economic zone',
            'maritime delimitation', 'blue homeland', 'mavi vatan', 'oruc reis', 'navtex',
            'aegean airspace', 'airspace violation', 'overflight', 'greek airspace',
            'island militarization', 'demilitarization', 'lausanne treaty', 'western thrace',
            'muslim minority thrace', 'turkish minority greece', 'east med', 'eastern mediterranean',
            'chevron crete', 'south of crete', 'greece offshore blocks', 'greece turkey dispute',
            'greece turkey tension', 'greece turkey maritime', 'erdogan mitsotakis',
            'mitsotakis erdogan', 'greece turkey delimitation', 'kastellorizo', 'imia',
            'greece turkey drillship', 'aegean dispute', 'fidan greece', 'dendias turkey',
            # Greek
            '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03c4\u03bf\u03c5\u03c1\u03ba\u03af\u03b1', '\u03b1\u03b9\u03b3\u03b1\u03af\u03bf', '\u03b3\u03b1\u03bb\u03ac\u03b6\u03b9\u03b1 \u03c0\u03b1\u03c4\u03c1\u03af\u03b4\u03b1',
            '\u03b1\u03c0\u03bf\u03ba\u03bb\u03b5\u03b9\u03c3\u03c4\u03b9\u03ba\u03ae \u03bf\u03b9\u03ba\u03bf\u03bd\u03bf\u03bc\u03b9\u03ba\u03ae \u03b6\u03ce\u03bd\u03b7', '\u03c5\u03c6\u03b1\u03bb\u03bf\u03ba\u03c1\u03b7\u03c0\u03af\u03b4\u03b1',
            '\u03c7\u03c9\u03c1\u03b9\u03ba\u03ac \u03cd\u03b4\u03b1\u03c4\u03b1', '\u03b5\u03bb\u03bb\u03b7\u03bd\u03bf\u03c4\u03bf\u03c5\u03c1\u03ba\u03b9\u03ba\u03ac', '\u03b4\u03c5\u03c4\u03b9\u03ba\u03ae \u03b8\u03c1\u03ac\u03ba\u03b7',
            # Turkish
            'yunanistan turkiye', 'ege', 'mavi vatan', 'kita sahanligi', 'bati trakya',
            'yunanistan turkiye gerginlik',
        ],
        'baseline_statements_per_week': 14,
        'weight': 1.4,   # the big one -- overweighted
    },

    'migration_frontline': {
        'name': 'Migration Frontline',
        'flag': '\U0001F6DF', 'icon': '\U0001F6DF',
        'color': '#0ea5e9',
        'role': 'External Pressure - EU External Border',
        'description': 'Libya->Crete/Gavdos corridor (surging) vs the Turkey-cooperative Aegean route (down ~60%), Evros land border, asylum suspension, return hubs, pushback allegations, Frontex, EU-pact leverage',
        'keywords': [
            'greece migration', 'greece migrants', 'greece refugees', 'crete migrants',
            'gavdos', 'libya crete', 'libya greece migrants', 'aegean crossing',
            'greek islands migrants', 'lesbos migrants', 'chios migrants', 'samos migrants',
            'evros', 'greece turkey border migrants', 'greece asylum suspension',
            'greece pushback', 'greece pushbacks', 'frontex greece', 'greece coast guard migrants',
            'greece deportation', 'return hubs', 'greece asylum', 'eu migration pact greece',
            'greece smuggling', 'migrant boat greece', 'greece north africa migrants',
            'greece shipwreck', 'greece migrant deaths', 'greece detention migrants',
            # Greek
            '\u03bc\u03b5\u03c4\u03b1\u03bd\u03ac\u03c3\u03c4\u03b5\u03c2 \u03b5\u03bb\u03bb\u03ac\u03b4\u03b1', '\u03c0\u03c1\u03bf\u03c3\u03c6\u03c5\u03b3\u03b9\u03ba\u03cc', '\u03ba\u03c1\u03ae\u03c4\u03b7 \u03bc\u03b5\u03c4\u03b1\u03bd\u03ac\u03c3\u03c4\u03b5\u03c2',
            '\u03ad\u03b2\u03c1\u03bf\u03c2', '\u03ac\u03c3\u03c5\u03bb\u03bf', '\u03b1\u03c0\u03b5\u03bb\u03ac\u03c3\u03b5\u03b9\u03c2',
        ],
        'baseline_statements_per_week': 12,
        'weight': 1.0,
    },

    'domestic_pressure': {
        'name': 'Domestic Pressure',
        'flag': '\U0001F3DB\uFE0F', 'icon': '\U0001F3DB\uFE0F',
        'color': '#a78bfa',
        'role': 'Internal Pressure - Government Stability',
        'description': 'Tempi rail-disaster fallout & Karystianou movement, Predator/EYP wiretapping scandal, press-freedom strain, cost-of-living & pensioner protests, ND polling slide, opposition vacuum, constitutional reform',
        'keywords': [
            'mitsotakis', 'new democracy greece', 'greece tempi', 'tempi disaster',
            'tempi train', 'tempi crash', 'karystianou', 'tempi protest', 'greece protest',
            'predator spyware', 'greece wiretapping', 'greece surveillance', 'eyp greece',
            'greece press freedom', 'greece corruption', 'novartis greece', 'opekepe',
            'greece farm subsidy', 'greece cost of living', 'greece pensioners',
            'greece strike', 'greece inflation', 'greece housing crisis', 'golden visa greece',
            'syriza', 'pasok', 'tsipras', 'greece constitutional reform', 'greece opposition',
            'greece election', 'greece snap election', 'greece government', 'androulakis',
            # Greek
            '\u03bc\u03b7\u03c4\u03c3\u03bf\u03c4\u03ac\u03ba\u03b7\u03c2', '\u03c4\u03ad\u03bc\u03c0\u03b7', '\u03ba\u03b1\u03c1\u03c5\u03c3\u03c4\u03b9\u03b1\u03bd\u03bf\u03cd', '\u03c5\u03c0\u03bf\u03ba\u03bb\u03bf\u03c0\u03ad\u03c2',
            'predator', '\u03bd\u03ad\u03b1 \u03b4\u03b7\u03bc\u03bf\u03ba\u03c1\u03b1\u03c4\u03af\u03b1', '\u03b1\u03c0\u03b5\u03c1\u03b3\u03af\u03b1', '\u03b1\u03ba\u03c1\u03af\u03b2\u03b5\u03b9\u03b1', '\u03c3\u03c5\u03c1\u03b9\u03b6\u03b1',
        ],
        'baseline_statements_per_week': 14,
        'weight': 0.9,
    },

    # ---------------- ANCHORS & STANDING ----------------
    'eu_anchor': {
        'name': 'EU Anchor',
        'flag': '\U0001F1EA\U0001F1FA', 'icon': '\U0001F1EA\U0001F1FA',
        'color': '#3b82f6',
        'role': 'Anchor - EU Embedding & Standing',
        'description': 'Post-bailout fiscal recovery, RRF wind-down "cliff", removal from EU macroeconomic-imbalances list, EU solidarity vs Turkey, EU migration-pact leverage -- set against EU rule-of-law / press-freedom scrutiny',
        'keywords': [
            'greece eu', 'greece european union', 'greece rrf', 'greece recovery resilience',
            'greece recovery fund', 'greece macroeconomic imbalances', 'greece eu funds',
            'greece brussels', 'greece eu solidarity', 'greece eu migration pact',
            'greece rule of law', 'greece eu press freedom', 'greece eu commission',
            'greece eurozone', 'greece debt', 'greece investment grade', 'greece bailout',
            'greece fiscal', 'greece european parliament', 'greece eu rebuke', 'greece bonds',
            'greece credit rating', 'greece eu funding',
            # Greek
            '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03b5\u03c5\u03c1\u03c9\u03c0\u03b1\u03ca\u03ba\u03ae \u03ad\u03bd\u03c9\u03c3\u03b7',  # ellada evropaiki enosi
            '\u03c4\u03b1\u03bc\u03b5\u03af\u03bf \u03b1\u03bd\u03ac\u03ba\u03b1\u03bc\u03c8\u03b7\u03c2', '\u03ba\u03bf\u03bc\u03b9\u03c3\u03b9\u03cc\u03bd', '\u03b2\u03c1\u03c5\u03be\u03ad\u03bb\u03bb\u03b5\u03c2',
        ],
        'baseline_statements_per_week': 10,
        'weight': 1.0,
    },

    'nato_us': {
        'name': 'NATO / US Posture',
        'flag': '\U0001F6E1\uFE0F', 'icon': '\U0001F6E1\uFE0F',
        'color': '#22c55e',
        'role': 'Anchor - Western Defense Alignment',
        'description': 'Souda Bay + Alexandroupoli basing, US-Greece Mutual Defense Cooperation Agreement, F-35 acquisition, Black Sea-Aegean Vertical Corridor eroding Turkish transit leverage, Greece as reliable NATO anchor',
        'keywords': [
            'greece nato', 'greece united states', 'greece us defense', 'souda bay',
            'alexandroupoli', 'greece us base', 'mutual defense cooperation', 'mdca greece',
            'greece f-35', 'greece f35', 'greece rafale', 'greece us military',
            'greece pentagon', 'greece arms deal', 'greece defense spending', 'greece frigate',
            'black sea aegean corridor', 'vertical corridor', 'greece bulgaria romania rail',
            'greece ukraine resupply', 'greece nato flank', 'greece dendias', 'greece belharra',
            'greece defense minister', 'greece us partnership',
            # Greek
            '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03bd\u03b1\u03c4\u03bf', '\u03c3\u03bf\u03cd\u03b4\u03b1', '\u03b1\u03bb\u03b5\u03be\u03b1\u03bd\u03b4\u03c1\u03bf\u03cd\u03c0\u03bf\u03bb\u03b7', '\u03b5\u03be\u03bf\u03c0\u03bb\u03b9\u03c3\u03bc\u03bf\u03af',
        ],
        'baseline_statements_per_week': 9,
        'weight': 1.0,
    },

    'regional_alignment': {
        'name': 'Regional Alignment',
        'flag': '\U0001F91D', 'icon': '\U0001F91D',
        'color': '#14b8a6',
        'role': 'Anchor - Mediterranean Power Projection',
        'description': 'East Med "3+1" (Greece-Cyprus-Israel + US), Greece-Egypt EEZ deal countering the Turkey-Libya memorandum, IMEC, UN Security Council seat (2025-26), East Med energy diplomacy',
        'keywords': [
            'greece israel', 'greece cyprus israel', '3+1', 'three plus one', 'greece egypt',
            'greece egypt eez', 'eastmed pipeline', 'east med pipeline', 'greece israel defense',
            'greece cyprus', 'imec corridor', 'greece un security council', 'greece unsc',
            'greece mediterranean', 'greece energy diplomacy', 'chevron greece', 'exxonmobil greece',
            'greece gas exploration', 'greece netanyahu', 'mitsotakis netanyahu',
            'greece libya memorandum', 'turkey libya memorandum', 'greece saudi', 'greece india imec',
            'greece egypt military', 'greece cyprus israel summit',
            # Greek
            '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03b9\u03c3\u03c1\u03b1\u03ae\u03bb', '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03b1\u03af\u03b3\u03c5\u03c0\u03c4\u03bf\u03c2', '\u03b5\u03bb\u03bb\u03ac\u03b4\u03b1 \u03ba\u03cd\u03c0\u03c1\u03bf\u03c2',
        ],
        'baseline_statements_per_week': 9,
        'weight': 0.9,
    },
}

# Composite weighting (sums to ~1.0): Turkey axis dominates by design.
COMPOSITE_WEIGHTS = {
    'turkey_axis':         0.30,
    'migration_frontline': 0.16,
    'domestic_pressure':   0.14,
    'eu_anchor':           0.14,
    'nato_us':             0.14,
    'regional_alignment':  0.12,
}

# Diplomatic-track (detente) detection keywords
DIPLOMATIC_KEYWORDS = [
    'high-level cooperation council', 'high level cooperation council',
    'confidence-building', 'confidence building measures', 'positive agenda',
    'calm waters', 'good neighborly', 'greece turkey trade', 'greece turkey agreement',
    'greece turkey memorandum', 'greece turkey dialogue', 'greece turkey rapprochement',
    'greece turkey detente', 'aegean confidence', 'greece turkey cooperation',
    'mitsotakis erdogan', 'erdogan mitsotakis', 'greece turkey friendship',
    'greece turkey thaw', 'athens ankara dialogue',
]


# ============================================
# RSS FEEDS + GDELT QUERIES
# ============================================
RSS_FEEDS = [
    # Direct regional / Greek-English
    'https://www.ekathimerini.com/feed/',
    'https://greekreporter.com/feed/',
    'https://www.naftemporiki.gr/feed/',
    # Google News -- per vector (EN)
    'https://news.google.com/rss/search?q=greece+turkey+aegean+OR+casus+belli+OR+eez+OR+blue+homeland&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=greece+migration+OR+crete+migrants+OR+evros+OR+greece+asylum&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=mitsotakis+OR+greece+tempi+OR+greece+wiretapping+OR+karystianou&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=greece+eu+OR+greece+rrf+OR+greece+brussels+OR+greece+recovery+fund&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=greece+nato+OR+souda+bay+OR+alexandroupoli+OR+greece+f-35&hl=en&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=greece+israel+OR+greece+egypt+OR+east+med+OR+greece+cyprus+israel&hl=en&gl=US&ceid=US:en',
    # Google News -- Greek-language (broad Greece-Turkey + domestic)
    'https://news.google.com/rss/search?q=%CE%B5%CE%BB%CE%BB%CE%AC%CE%B4%CE%B1+%CF%84%CE%BF%CF%85%CF%81%CE%BA%CE%AF%CE%B1+%CE%B1%CE%B9%CE%B3%CE%B1%CE%AF%CE%BF&hl=el&gl=GR&ceid=GR:el',
]

GDELT_QUERIES = [
    # English -- per vector
    ('greece turkey aegean eez casus belli', 'eng'),
    ('greece migration crete evros asylum', 'eng'),
    ('greece mitsotakis tempi wiretapping protest', 'eng'),
    ('greece eu recovery fund brussels', 'eng'),
    ('greece nato souda alexandroupoli defense', 'eng'),
    ('greece israel egypt east med cyprus', 'eng'),
    # Turkish -- strengthens the turkey_axis read
    ('yunanistan ege mavi vatan', 'tur'),
]


# ============================================
# REDIS HELPERS
# ============================================
def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f"{UPSTASH_REDIS_URL}/get/{key}",
                         headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                         timeout=8)
        if r.status_code == 200:
            val = r.json().get('result')
            if val:
                return json.loads(val)
    except Exception as e:
        print(f"[Greece Rhetoric] Redis GET error ({key}): {str(e)[:80]}")
    return None


def _redis_set(key, value, ttl=None):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        encoded = json.dumps(value)
        if ttl:
            url = f"{UPSTASH_REDIS_URL}/setex/{key}/{int(ttl)}"
        else:
            url = f"{UPSTASH_REDIS_URL}/set/{key}"
        r = requests.post(url, headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                          data=encoded.encode('utf-8'), timeout=8)
        return r.status_code == 200
    except Exception as e:
        print(f"[Greece Rhetoric] Redis SET error ({key}): {str(e)[:80]}")
        return False


def _redis_lpush(key, value, max_len=HISTORY_MAX_ENTRIES):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        encoded = json.dumps(value)
        hdr = {"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}
        requests.post(f"{UPSTASH_REDIS_URL}/lpush/{key}/{requests.utils.quote(encoded, safe='')}",
                      headers=hdr, timeout=8)
        requests.post(f"{UPSTASH_REDIS_URL}/ltrim/{key}/0/{max_len - 1}", headers=hdr, timeout=8)
        return True
    except Exception as e:
        print(f"[Greece Rhetoric] Redis LPUSH error ({key}): {str(e)[:80]}")
        return False


def _redis_lrange(key, count=HISTORY_MAX_ENTRIES):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return []
    try:
        r = requests.get(f"{UPSTASH_REDIS_URL}/lrange/{key}/0/{count - 1}",
                         headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}, timeout=8)
        if r.status_code == 200:
            out = []
            for item in (r.json().get('result') or []):
                try:
                    out.append(json.loads(item))
                except Exception:
                    pass
            return out
    except Exception as e:
        print(f"[Greece Rhetoric] Redis LRANGE error ({key}): {str(e)[:80]}")
    return []


# ============================================
# ARTICLE FETCH (RSS + GDELT)
# ============================================
def _fetch_rss(url, timeout=10):
    out = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AsifahAnalytics/1.0)'}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return out
        root = ET.fromstring(r.content)
        for item in root.iter('item'):
            title = (item.findtext('title') or '').strip()
            link  = (item.findtext('link') or '').strip()
            desc  = (item.findtext('description') or '').strip()
            pub   = (item.findtext('pubDate') or '').strip()
            src   = ''
            src_el = item.find('source')
            if src_el is not None:
                src = (src_el.text or '').strip()
            published_iso = ''
            if pub:
                try:
                    published_iso = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
                except Exception:
                    published_iso = ''
            out.append({
                'title': title, 'url': link, 'source': src or 'RSS',
                'published': published_iso, 'body': f"{title} {desc}",
            })
    except Exception as e:
        print(f"[Greece Rhetoric] RSS error ({url[:50]}): {str(e)[:60]}")
    return out


def _fetch_gdelt(query, lang='eng', days=5, timeout=15):
    out = []
    try:
        url = ('https://api.gdeltproject.org/api/v2/doc/doc'
               f'?query={requests.utils.quote(query)}%20sourcelang:{lang}'
               f'&mode=ArtList&maxrecords=40&format=json&timespan={days}d')
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AsifahAnalytics/1.0)'}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return out
        for art in (r.json().get('articles') or []):
            title = art.get('title', '')
            out.append({
                'title': title,
                'url': art.get('url', ''),
                'source': art.get('domain', 'GDELT'),
                'published': art.get('seendate', ''),
                'body': title,
            })
    except Exception as e:
        print(f"[Greece Rhetoric] GDELT error ({query[:30]}): {str(e)[:60]}")
    return out


def _fetch_all_articles(days=5):
    articles = []
    seen = set()

    for feed in RSS_FEEDS:
        for art in _fetch_rss(feed):
            u = art.get('url')
            if u and u not in seen:
                seen.add(u)
                articles.append(art)

    for query, lang in GDELT_QUERIES:
        for art in _fetch_gdelt(query, lang=lang, days=days):
            u = art.get('url')
            if u and u not in seen:
                seen.add(u)
                articles.append(art)
        time.sleep(0.5)   # be gentle with GDELT between sequential calls

    print(f"[Greece Rhetoric] Fetched {len(articles)} unique articles")
    return articles


# ============================================
# ACTOR SCORING
# ============================================
# Short single-token keywords (<=4 chars, e.g. "ege" = Aegean in Turkish) must match on
# WORD BOUNDARIES, not as substrings -- otherwise "ege" matches "lEGEndary", "aEGEan",
# slugs, etc., and silently inflates a vector to a false high. Multi-word / hyphenated /
# longer keywords stay on fast substring matching (they are specific enough).
_WB_CACHE = {}
def _kw_in_body(kw, body):
    if (' ' in kw) or ('-' in kw) or ('+' in kw) or len(kw) > 4:
        return kw in body
    pat = _WB_CACHE.get(kw)
    if pat is None:
        pat = re.compile(r'(?<![a-z0-9])' + re.escape(kw) + r'(?![a-z0-9])')
        _WB_CACHE[kw] = pat
    return pat.search(body) is not None


def _score_actor(actor_id, actor_cfg, articles, telegram_msgs):
    keywords  = [kw.lower() for kw in actor_cfg['keywords']]
    hits      = []
    hit_count = 0

    for art in articles:
        body = art.get('body', '').lower()
        matched = [kw for kw in keywords if _kw_in_body(kw, body)]
        if matched:
            hit_count += len(matched)
            hits.append({
                'title':     art.get('title', '')[:150],
                'url':       art.get('url', ''),
                'source':    art.get('source', ''),
                'published': art.get('published', ''),
                'matched_keywords': matched[:5],
            })

    # ── RANK THE EVIDENCE (Sep 2026) ────────────────────────────────────
    # `hits` is built in FEED ORDER, and top_articles[:5] took the first five.
    # So the article displayed as evidence for a signal was whichever one
    # happened to arrive first -- not the strongest match. On 5 Sep the Greece
    # turkey_axis vector sat at L5 while its displayed evidence was a Greek
    # WEATHER FORECAST ("Sunshine today, mercury up to 36 degrees") that had
    # clipped a single keyword. The level was carried by aggregate hit_count
    # across all articles; the prose was carried by an arbitrary one.
    #
    # Ranking by match COUNT then by SPECIFICITY (longer, multi-word keywords
    # are the discriminating ones -- 'greece turkey delimitation' means
    # something, 'aegean' alone does not) puts the article that actually
    # justifies the reading in front of the reader.
    #
    # This does not change any LEVEL. It changes which article is shown as the
    # basis for one -- the same auditability gap as the nuclear trigger phrase.
    def _evidence_rank(h):
        kws = h.get('matched_keywords') or []
        return (-len(kws), -max((len(k) for k in kws), default=0))

    hits.sort(key=_evidence_rank)

    tg_hits = 0
    for msg in telegram_msgs:
        body = (msg.get('title', '') or msg.get('body', '')).lower()
        matched = [kw for kw in keywords if _kw_in_body(kw, body)]
        if matched:
            tg_hits += len(matched)
            hit_count += len(matched)

    baseline  = actor_cfg.get('baseline_statements_per_week', 10)
    weight    = actor_cfg.get('weight', 1.0)
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


# ============================================
# CROSS-TRACKER CORROBORATION (proxy-not-clone; absence-honest)
# ============================================
_MIL_ALERT_LEVEL = {'normal': 0, 'elevated': 1, 'high': 2, 'critical': 4}


def _posture_aegean_relevant(posture):
    """Does this military posture fingerprint actually bear on the Aegean / Greece-Turkey
    theatre (vs. unrelated noise)? Checks alert level + top-signal text."""
    if not isinstance(posture, dict):
        return False, 0
    alert = str(posture.get('alert_level', 'normal')).lower()
    lvl = _MIL_ALERT_LEVEL.get(alert, 0)
    aegean_hit = False
    for sig in (posture.get('top_signals', []) or [])[:3]:
        text = (sig if isinstance(sig, str) else (sig.get('title', '') or sig.get('text', ''))).lower()
        if any(k in text for k in AEGEAN_MIL_KEYWORDS):
            aegean_hit = True
            break
    return (lvl >= 1 or aegean_hit), lvl


def _read_military_corroboration():
    """Read the ME-backend military tracker's posture fingerprints for Turkey + Greece.
    Returns an absence-honest corroboration dict. Never raises -- best-effort metadata."""
    out = {'active': False, 'level': 0, 'turkey': None, 'greece': None, 'note': ''}
    try:
        tk = _redis_get(MILITARY_TURKEY_KEY)
        gr = _redis_get(MILITARY_GREECE_KEY)
        tk_rel, tk_lvl = _posture_aegean_relevant(tk) if tk else (False, 0)
        gr_rel, gr_lvl = _posture_aegean_relevant(gr) if gr else (False, 0)
        if tk:
            out['turkey'] = {'alert_level': tk.get('alert_level', 'normal'),
                             'score': tk.get('score', 0),
                             'scanned_at': tk.get('scanned_at', ''),
                             'aegean_relevant': tk_rel}
        if gr:
            out['greece'] = {'alert_level': gr.get('alert_level', 'normal'),
                             'score': gr.get('score', 0),
                             'scanned_at': gr.get('scanned_at', ''),
                             'aegean_relevant': gr_rel}
        out['active'] = bool(tk_rel or gr_rel)
        out['level']  = max(tk_lvl, gr_lvl)
        if out['active']:
            out['note'] = ('Military posture in the Aegean/East-Med theatre is elevated; '
                           'consistent with operational backing of the rhetoric, not declaratory only.')
    except Exception as e:
        print(f"[Greece Rhetoric] military corroboration read error: {str(e)[:80]}")
    return out


def _read_migration_corroboration():
    """Read the Greece migration sensor (same backend). Absence-honest. Surfaces whether
    the live arrivals picture corroborates migration-frontline rhetoric."""
    out = {'active': False, 'total': None, 'route': '', 'data_as_of': '', 'note': ''}
    try:
        mig = _redis_get(MIGRATION_KEY)
        if not mig:
            return out
        # Defensive read -- the sensor's exact shape may evolve. Look for common fields.
        total = (mig.get('total_arrivals') or mig.get('total') or
                 mig.get('sea_arrivals') or mig.get('arrivals'))
        out['total']      = total
        out['route']      = mig.get('dominant_route') or mig.get('route') or ''
        out['data_as_of'] = mig.get('data_as_of') or mig.get('scanned_at') or ''
        band = str(mig.get('band') or mig.get('trend') or mig.get('alert_level') or '').lower()
        # Active if the sensor flags elevation, or simply if it is reporting live arrivals.
        out['active'] = bool(band in ('elevated', 'high', 'surge', 'rising') or total)
        if out['active']:
            out['note'] = ('Live arrivals sensor is reporting flow; migration rhetoric is '
                           'tracking an actual pressure, not an abstract one.')
    except Exception as e:
        print(f"[Greece Rhetoric] migration corroboration read error: {str(e)[:80]}")
    return out


def _detect_diplomatic_track(articles):
    """Detect the Greece-Turkey detente track (High-Level Cooperation Council, CBMs,
    positive agenda). Scenario-driven, like the off-ramp spine. Absence-honest."""
    hits = []
    seen = set()
    for art in articles:
        body = art.get('body', '').lower()
        matched = [kw for kw in DIPLOMATIC_KEYWORDS if kw in body]
        if matched and art.get('url') not in seen:
            seen.add(art.get('url'))
            hits.append({'title': art.get('title', '')[:140], 'url': art.get('url', ''),
                         'source': art.get('source', ''), 'matched': matched[:3]})
    count = len(hits)
    if count >= 4:
        scenario, framework = 'Active Detente Track', True
    elif count >= 2:
        scenario, framework = 'Confidence-Building Signals', True
    elif count >= 1:
        scenario, framework = 'Limited Dialogue Indicators', False
    else:
        scenario, framework = 'No Active Track', False
    return {
        'scenario':         scenario,
        'framework_active': framework,
        'score':            count,
        'top_signals':      hits[:4],
    }


# ============================================
# COMPOSITE
# ============================================
def _spoke_top_signal(level):
    if level >= 4:
        return 'Aegean/EEZ confrontation -- crisis-level Greece-Turkey friction'
    if level >= 3:
        return 'Significant Greece-Turkey friction -- formal protest / incident territory'
    if level >= 2:
        return 'Concrete Turkish pressure moves on the Aegean / East-Med file'
    if level >= 1:
        return 'Greece-Turkey rhetoric active -- declaratory, no concrete moves'
    return 'Greece-Turkey axis quiet -- managed-calm baseline'


def _compute_composite(actor_scores, military, migration, diplomatic):
    levels = {aid: actor_scores.get(aid, {}).get('level', 0) for aid in ACTORS}
    raws   = {aid: actor_scores.get(aid, {}).get('raw_score', 0) for aid in ACTORS}

    composite = sum(raws[aid] * COMPOSITE_WEIGHTS.get(aid, 0) for aid in ACTORS)
    composite = min(100, int(composite))

    if composite >= 85:   theatre_level = 5
    elif composite >= 65: theatre_level = 4
    elif composite >= 45: theatre_level = 3
    elif composite >= 28: theatre_level = 2
    elif composite >= 12: theatre_level = 1
    else:                 theatre_level = 0

    level_info = ESCALATION_LEVELS[theatre_level]

    # Hottest single vector -- so the regional rollup does not under-read breadth
    # (the Azerbaijan composite-dilution lesson, baked in from day one).
    peak_vector_level = max(levels.values()) if levels else 0
    peak_vector = max(levels, key=lambda k: levels[k]) if levels else None

    # Active pressure / anchor stacking
    active_pressures = [v for v in PRESSURE_VECTORS if levels[v] >= 2]
    active_anchors   = [v for v in ANCHOR_VECTORS if levels[v] >= 2]

    # ---- Convergence read (estimative, absence-honest) ----
    convergence_signal = ''
    tk = levels['turkey_axis']
    mig_lvl = levels['migration_frontline']

    if tk >= 1 and military.get('active'):
        convergence_signal = ('\U0001F3AF Aegean rhetoric corroborated by elevated Turkish/Greek '
                              'military posture -- the dispute reads operationally live, not declaratory.')
    elif mig_lvl >= 1 and migration.get('active'):
        convergence_signal = ('\U0001F6DF Migration rhetoric is tracking the live Libya-to-Crete '
                              'arrivals picture -- a real pressure, not an abstract one.')
    elif tk >= 3:
        convergence_signal = '\U0001F1F9\U0001F1F7 Greece-Turkey friction at crisis intensity on the Aegean / EEZ file.'
    elif len(active_pressures) >= 2:
        convergence_signal = ('\U0001F4E1 Pressure stacking across ' +
                              ', '.join(ACTORS[v]['name'] for v in active_pressures))
    elif diplomatic.get('framework_active') and tk <= 1:
        convergence_signal = ('\U0001F54A\uFE0F Managed detente holding -- active diplomatic track with '
                              'Turkey friction contained at declaratory levels.')

    # ---- Spoke fingerprint (Greece -> Turkey hub; peer-rivalry) ----
    spoke_fingerprint = {
        'spoke':        'greece',
        'hub':          'turkey',
        'vector':       'turkey_axis',
        'relationship': 'peer_rivalry',
        'level':        tk,
        'score':        raws['turkey_axis'],
        'direction':    'steady',     # stamped from prior history at write time
        'top_signal':   _spoke_top_signal(tk),
        'detente_active': bool(diplomatic.get('framework_active')),
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
        'turkey_axis_level':        levels['turkey_axis'],
        'migration_frontline_level': levels['migration_frontline'],
        'domestic_pressure_level':  levels['domestic_pressure'],
        'eu_anchor_level':          levels['eu_anchor'],
        'nato_us_level':            levels['nato_us'],
        'regional_alignment_level': levels['regional_alignment'],
        # Hottest single vector -- regional rollup reads this when composite dilutes
        'peak_vector_level':        peak_vector_level,
        'peak_vector':              peak_vector,
        # Panel stacking
        'active_pressures':         active_pressures,
        'active_anchors':           active_anchors,
        # Cross-tracker corroboration + diplomatic off-ramp
        'military_corroboration':   military,
        'migration_corroboration':  migration,
        'diplomatic_track':         diplomatic,
        'spoke_fingerprint':        spoke_fingerprint,
    }


def _write_spoke_fingerprint(spoke_fingerprint):
    """Write spoke:turkey:greece with a freshly-stamped ts + direction from prior level."""
    try:
        prior = _redis_get(SPOKE_FINGERPRINT_KEY)
        direction = 'steady'
        if isinstance(prior, dict):
            pl = prior.get('level', spoke_fingerprint['level'])
            if spoke_fingerprint['level'] > pl:
                direction = 'rising'
            elif spoke_fingerprint['level'] < pl:
                direction = 'easing'
        payload = dict(spoke_fingerprint)
        payload['direction'] = direction
        payload['ts'] = datetime.now(timezone.utc).isoformat()
        payload['source'] = 'rhetoric_tracker_greece_v1.0'
        _redis_set(SPOKE_FINGERPRINT_KEY, payload, ttl=SPOKE_FINGERPRINT_TTL)
    except Exception as e:
        print(f"[Greece Rhetoric] spoke fingerprint write error: {str(e)[:80]}")


# ============================================
# FULL SCAN
# ============================================
def run_greece_rhetoric_scan(days=5):
    print(f'[Greece Rhetoric] Starting scan (days={days})...')
    start_time = time.time()

    articles = _fetch_all_articles(days=days)

    telegram_msgs = []
    if TELEGRAM_AVAILABLE:
        try:
            telegram_msgs = fetch_greece_telegram_signals(hours_back=days * 24) or []
            print(f'[Greece Rhetoric] Telegram: {len(telegram_msgs)} messages')
        except Exception as e:
            print(f'[Greece Rhetoric] Telegram error: {str(e)[:80]}')

    actor_scores = {}
    for actor_id, actor_cfg in ACTORS.items():
        actor_scores[actor_id] = _score_actor(actor_id, actor_cfg, articles, telegram_msgs)
        s = actor_scores[actor_id]
        print(f'[Greece Rhetoric] {actor_cfg["name"]}: L{s["level"]} ({s["raw_score"]}/100)')

    # Cross-tracker corroboration + diplomatic off-ramp
    military   = _read_military_corroboration()
    migration  = _read_migration_corroboration()
    diplomatic = _detect_diplomatic_track(articles)

    composite = _compute_composite(actor_scores, military, migration, diplomatic)

    # Persist the spoke fingerprint for the (future) Turkey hub aggregator
    _write_spoke_fingerprint(composite['spoke_fingerprint'])

    elapsed = round(time.time() - start_time, 1)
    now = datetime.now(timezone.utc).isoformat()

    all_top = []
    seen = set()
    for scores in actor_scores.values():
        for art in scores.get('top_articles', []):
            if art['url'] and art['url'] not in seen:
                seen.add(art['url'])
                all_top.append(art)
    all_top = all_top[:20]

    result = {
        'success':               True,
        'theatre':               'Greece',
        'version':               '1.0.0',
        'timestamp':             now,
        'scanned_at':            now,
        'scan_duration_seconds': elapsed,
        'total_articles':        len(articles),
        'telegram_messages':     len(telegram_msgs),
        **composite,
        'actors':                actor_scores,
        'pressure_vectors':      PRESSURE_VECTORS,
        'anchor_vectors':        ANCHOR_VECTORS,
        'top_articles':          all_top,
        'is_strike_actor':       False,
    }

    # Signal interpretation -- So What, BLUF, diplomatic read (analyst layer)
    if INTERPRETER_AVAILABLE:
        try:
            result['interpretation'] = greece_interpret_signals(result)
        except Exception as ie:
            print(f'[Greece Rhetoric] Interpreter error: {str(ie)[:100]}')
        try:
            from greece_signal_interpreter import build_top_signals
            result['top_signals'] = build_top_signals(result)
            print(f'[Greece Rhetoric] top_signals: {len(result["top_signals"])} emitted')
        except Exception as e:
            print(f'[Greece Rhetoric] build_top_signals error: {str(e)[:120]}')
            result['top_signals'] = []

    print(f'[Greece Rhetoric] Scan complete in {elapsed}s | '
          f'Theatre L{composite["theatre_level"]} ({composite["theatre_score"]}/100) | '
          f'peak L{composite["peak_vector_level"]} | '
          f'detente={diplomatic["scenario"]} | '
          f'{composite["convergence_signal"] or "No convergence signal"}')
    return result


# ============================================
# BACKGROUND SCAN
# ============================================
def _bg_scan():
    global _rhetoric_running
    if not _rhetoric_lock.acquire(blocking=False):
        print('[Greece Rhetoric] Scan already running -- skipping')
        return
    try:
        _rhetoric_running = True
        result = run_greece_rhetoric_scan()
        _redis_set(RHETORIC_CACHE_KEY, result, ttl=RHETORIC_CACHE_TTL)
        snap = {
            'timestamp':     result['scanned_at'],
            'scanned_at':    result['scanned_at'],
            'theatre_score': result['theatre_score'],
            'theatre_level': result['theatre_level'],
            'peak_vector_level': result['peak_vector_level'],
        }
        _redis_lpush('rhetoric:greece:history', snap)
        print('[Greece Rhetoric] Background scan cached + snapshotted')
    except Exception as e:
        print(f'[Greece Rhetoric] Background scan error: {str(e)[:120]}')
    finally:
        _rhetoric_running = False
        _rhetoric_lock.release()


def _start_background_loop():
    def loop():
        time.sleep(90)   # boot delay
        while True:
            try:
                cached = _redis_get(RHETORIC_CACHE_KEY)
                if not cached:
                    _bg_scan()
            except Exception as e:
                print(f'[Greece Rhetoric] loop error: {str(e)[:80]}')
            time.sleep(SCAN_INTERVAL_HOURS * 3600)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print('[Greece Rhetoric] Background scan loop started')


# ============================================
# ENDPOINTS
# ============================================
def register_greece_rhetoric_endpoints(app):

    @app.route('/api/rhetoric/greece', methods=['GET'])
    def greece_rhetoric():
        force = request.args.get('force', '').lower() == 'true'
        if not force:
            cached = _redis_get(RHETORIC_CACHE_KEY)
            if cached:
                return jsonify(cached)
        try:
            result = run_greece_rhetoric_scan()
            _redis_set(RHETORIC_CACHE_KEY, result, ttl=RHETORIC_CACHE_TTL)
            snap = {
                'timestamp': result['scanned_at'], 'scanned_at': result['scanned_at'],
                'theatre_score': result['theatre_score'], 'theatre_level': result['theatre_level'],
                'peak_vector_level': result['peak_vector_level'],
            }
            _redis_lpush('rhetoric:greece:history', snap)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False, 'theatre': 'Greece',
                'error': str(e)[:200],
                'theatre_score': 0, 'theatre_level': 0,
                'theatre_escalation_level': 0,
                'theatre_escalation_label': 'Scanning...',
                'theatre_escalation_color': '#6b7280',
            }), 200

    @app.route('/api/rhetoric/greece/summary', methods=['GET'])
    def greece_rhetoric_summary():
        cached = _redis_get(RHETORIC_CACHE_KEY)
        if cached:
            dip = cached.get('diplomatic_track', {}) or {}
            return jsonify({
                'success':                  True,
                'theatre':                  'Greece',
                'theatre_score':            cached.get('theatre_score', 0),
                'theatre_level':            cached.get('theatre_level', 0),
                'theatre_escalation_level': cached.get('theatre_escalation_level', 0),
                'theatre_escalation_label': cached.get('theatre_escalation_label', 'Baseline'),
                'theatre_escalation_color': cached.get('theatre_escalation_color', '#6b7280'),
                'theatre_label':            cached.get('theatre_label', 'Baseline'),
                'theatre_color':            cached.get('theatre_color', '#6b7280'),
                # Per-vector levels
                'turkey_axis_level':         cached.get('turkey_axis_level', 0),
                'migration_frontline_level': cached.get('migration_frontline_level', 0),
                'domestic_pressure_level':   cached.get('domestic_pressure_level', 0),
                'eu_anchor_level':           cached.get('eu_anchor_level', 0),
                'nato_us_level':             cached.get('nato_us_level', 0),
                'regional_alignment_level':  cached.get('regional_alignment_level', 0),
                # Hottest single vector -- regional rollup reads this when the composite dilutes
                'peak_vector_level':         cached.get('peak_vector_level', 0),
                # Diplomatic off-ramp scenario
                'diplomatic_scenario':       dip.get('scenario', 'No Active Track'),
                'detente_active':            bool(dip.get('framework_active')),
                'convergence_signal':        cached.get('convergence_signal', ''),
                'scanned_at':                cached.get('scanned_at', ''),
                'total_articles':            cached.get('total_articles', 0),
            })
        return jsonify({
            'success': False, 'theatre': 'Greece',
            'theatre_score': 0, 'theatre_level': 0,
            'theatre_escalation_level': 0, 'theatre_escalation_label': 'Scanning...',
            'theatre_escalation_color': '#6b7280',
        }), 200

    @app.route('/api/rhetoric/greece/history', methods=['GET'])
    def greece_rhetoric_history():
        limit = min(int(request.args.get('limit', 120)), HISTORY_MAX_ENTRIES)
        entries = _redis_lrange('rhetoric:greece:history', count=limit)
        return jsonify({'success': True, 'theatre': 'Greece',
                        'count': len(entries), 'entries': entries})

    print('[Greece Rhetoric] Endpoints registered: '
          '/api/rhetoric/greece, /api/rhetoric/greece/summary, /api/rhetoric/greece/history')
    _start_background_loop()
