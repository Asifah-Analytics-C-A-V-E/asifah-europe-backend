"""
Asifah Analytics - Greece Migration Pressure (Sensor)
v1.0.0 - June 2026  |  Europe backend

SENSOR module (doctrine: stability pages are dials, not analysts). Emits RAW
arrival figures for Greece - sea + land, route split, top nationalities - with
honest sourcing and data_as_of. The analyst meaning (why the flows shifted, the
EU-pact leverage, the Libya-departure-hub linkage) lives in the rhetoric / BLUF
layer, NOT here.

THE LIVE STORY (2025-2026): the classic Aegean route (Turkey -> Greek islands)
has gone quiet; the Libya -> Crete / Gavdos corridor is now dominant. This module
surfaces that split so the page reads the real picture.

DATA SOURCES:
  * Live   - UNHCR Operational Data Portal, Greece sea arrivals (location 24489,
             situation 'europe-sea-arrivals'). Monthly cadence. Best-effort pull;
             VERIFY the population endpoint on first deploy (Badil-RSS pattern).
  * Static - manually-maintained baseline (latest published UNHCR/coast-guard
             figures) so the card ALWAYS renders even if the live pull misses.

REDIS:
  Cache: greece:migration:latest  (12h TTL)

ENDPOINTS:
  GET /api/greece/migration            (cache-first)
  GET /api/greece/migration?force=true (bypass cache, re-fetch)
  GET /debug/greece-migration

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import json
import time
import threading
from datetime import datetime, timezone

import requests

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL', '')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN', '')

CACHE_KEY = 'greece:migration:latest'
CACHE_TTL = 12 * 3600   # 12 hours

# UNHCR Operational Data Portal - Greece sea arrivals
UNHCR_LOCATION_ID = 24489
UNHCR_SITUATION   = 'europe-sea-arrivals'
UNHCR_PAGE_URL    = 'https://data.unhcr.org/en/situations/europe-sea-arrivals/location/24489'
# Best-effort machine-readable population endpoint (verify on first deploy).
UNHCR_POP_API     = 'https://data.unhcr.org/population/'

_migration_lock = threading.Lock()

# ------------------------------------------------------------------
# STATIC BASELINE  (always-present fallback; update as new dashboards publish)
# Sourced from UNHCR ODP Greece Sea Arrivals + Hellenic Coast Guard reporting.
# ------------------------------------------------------------------
STATIC_BASELINE = {
    'data_as_of':    '2026-05-03',
    'ytd_total':     7589,     # overall arrivals YTD 2026
    'sea_arrivals':  5615,
    'land_arrivals': 1974,
    'routes': {
        'crete_gavdos':   3184,   # Libya -> southern Greece (now the dominant route)
        'aegean_islands': 2431,   # Turkey -> eastern Aegean (down sharply YoY)
        'evros_land':     1974,   # Greece-Turkey land border
    },
    'top_nationalities': [
        {'name': 'Afghanistan', 'count': None},
        {'name': 'Sudan',       'count': None},
        {'name': 'Egypt',       'count': None},
        {'name': 'Bangladesh',  'count': None},
    ],
    'prior_year': {
        'year':            2025,
        'crete_gavdos':    19948,   # mainly Egypt, Sudan, Bangladesh
        'crete_share_pct': 47,      # 47% of 2025 arrivals landed in the Crete region
        'top_nationalities_2025': [
            {'name': 'Afghanistan', 'count': 10156},
            {'name': 'Sudan',       'count': 9104},
            {'name': 'Egypt',       'count': 8149},
        ],
    },
    # Sensor-level factual note (route picture), NOT analysis.
    'route_note': ('Route shift in progress: the Libya -> Crete / Gavdos corridor is now the '
                   'dominant entry point, while eastern-Aegean arrivals from Turkey have fallen '
                   'sharply year-on-year. Most departures originate from Tobruk in eastern Libya.'),
    'sources': [
        {'name': 'UNHCR Operational Data Portal - Greece Sea Arrivals',
         'url':  'https://data.unhcr.org/en/situations/europe-sea-arrivals/location/24489'},
        {'name': 'Hellenic Coast Guard', 'url': 'https://www.hcg.gr/'},
        {'name': 'IOM Missing Migrants Project (Mediterranean)',
         'url':  'https://missingmigrants.iom.int/region/mediterranean'},
    ],
}


# ------------------------------------------------------------------
# Redis helpers (Upstash REST)
# ------------------------------------------------------------------
def _redis_get(key):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        r = requests.get(
            '%s/get/%s' % (UPSTASH_REDIS_URL, key),
            headers={'Authorization': 'Bearer %s' % UPSTASH_REDIS_TOKEN},
            timeout=8,
        )
        if r.status_code == 200:
            val = r.json().get('result')
            if val:
                return json.loads(val)
    except Exception as e:
        print('[Greece Migration] redis get error: %s' % str(e)[:120])
    return None


def _redis_set(key, value, ttl=CACHE_TTL):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return
    try:
        requests.post(
            UPSTASH_REDIS_URL,
            headers={'Authorization': 'Bearer %s' % UPSTASH_REDIS_TOKEN},
            json=['SET', key, json.dumps(value), 'EX', str(ttl)],
            timeout=8,
        )
    except Exception as e:
        print('[Greece Migration] redis set error: %s' % str(e)[:120])


# ------------------------------------------------------------------
# UNHCR live pull (best-effort; falls back to static on any miss)
# ------------------------------------------------------------------
def _fetch_unhcr_arrivals():
    """
    Best-effort pull of Greece sea-arrival totals from the UNHCR ODP.
    Returns a dict of live fields, or None if the pull fails / shape is
    unexpected (the caller then keeps the static baseline). Conservative by
    design: we only override static fields we can actually parse.
    VERIFY/TUNE the params on first deploy against the live portal.
    """
    try:
        params = {
            'widget_id':        686755,           # "Total arrivals in 2026" widget
            'sv_id':            100,               # europe-sea-arrivals situation
            'population_group': '0;4797,0;4798,0;5634',
            'forcesvid':        1,
            'fromDate':         '%d-01-01' % datetime.now(timezone.utc).year,
        }
        r = requests.get(
            UNHCR_POP_API, params=params,
            headers={'User-Agent': 'AsifahAnalytics/1.0 (OSINT research)'},
            timeout=10,
        )
        if r.status_code != 200:
            print('[Greece Migration] UNHCR pull HTTP %s - using static baseline' % r.status_code)
            return None
        data = r.json()
        # ODP shapes vary; only accept a parseable numeric total.
        total = None
        if isinstance(data, dict):
            for k in ('data', 'population', 'result'):
                node = data.get(k)
                if isinstance(node, list) and node:
                    cand = node[-1]
                    if isinstance(cand, dict):
                        for vk in ('individuals', 'value', 'count', 'total'):
                            if isinstance(cand.get(vk), (int, float)):
                                total = int(cand[vk])
                                break
                if total is not None:
                    break
        if total is None or total <= 0:
            print('[Greece Migration] UNHCR pull: no parseable total - using static baseline')
            return None
        return {
            'ytd_total_live': total,
            'live_source':    'UNHCR ODP (europe-sea-arrivals, loc 24489)',
            'live_fetched_at': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print('[Greece Migration] UNHCR pull error: %s - using static baseline' % str(e)[:120])
        return None


# ------------------------------------------------------------------
# Payload assembly
# ------------------------------------------------------------------
def build_migration_payload(force=False):
    if not force:
        cached = _redis_get(CACHE_KEY)
        if cached:
            cached['cached'] = True
            return cached

    payload = json.loads(json.dumps(STATIC_BASELINE))  # deep copy
    payload['theatre'] = 'Greece'
    payload['module']  = 'greece_migration'
    payload['version'] = '1.0.0'
    payload['live']    = False
    payload['cached']  = False
    payload['generated_at'] = datetime.now(timezone.utc).isoformat()

    live = _fetch_unhcr_arrivals()
    if live and live.get('ytd_total_live'):
        payload['ytd_total']    = live['ytd_total_live']
        payload['live']         = True
        payload['live_source']  = live.get('live_source', '')
        payload['data_as_of']   = live.get('live_fetched_at', payload['data_as_of'])

    _redis_set(CACHE_KEY, payload)
    return payload


# ------------------------------------------------------------------
# Endpoint registration
# ------------------------------------------------------------------
def register_greece_migration_endpoints(app):
    from flask import request, jsonify

    @app.route('/api/greece/migration', methods=['GET'])
    def greece_migration():
        force = request.args.get('force', '').lower() in ('true', '1', 'yes')
        try:
            return jsonify(build_migration_payload(force=force))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200],
                            'fallback': STATIC_BASELINE}), 500

    @app.route('/debug/greece-migration', methods=['GET'])
    def debug_greece_migration():
        return jsonify({
            'module':        'greece_migration v1.0.0',
            'cache_key':     CACHE_KEY,
            'unhcr_page':    UNHCR_PAGE_URL,
            'redis_wired':   bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
            'static_as_of':  STATIC_BASELINE['data_as_of'],
        })

    print('[Europe Backend] \u2705 Greece migration endpoints registered')
