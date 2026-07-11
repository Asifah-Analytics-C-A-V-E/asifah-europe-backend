"""
Poland Refugee Tracker (sensor) -- v1.0.0 -- July 11, 2026
Asifah Analytics -- Europe backend

Ukraine-situation refugee figures for Poland. Dynamic data only, no
hand-updated statics. Sensor voice: the dial, not the diagnosis.

Sources (per-field attribution, data-honesty standard):
  1. UNHCR Refugee Data Finder API (documented, annual stock figures)
     https://api.unhcr.org/population/v1/population/
     Headline population = refugees + asylum_seekers + oip
     (Ukrainians under EU temporary protection are counted as OIP --
     "other people in need of international protection" -- NOT refugees.)
  2. Eurostat monthly temporary-protection beneficiaries (migr_asytpsm)
     Fresher monthly figure when available; best-effort, soft-fail.

Absence-honesty: Redis key persists WITHOUT TTL. Freshness is a logical
24h window checked against fetched_at. On refresh failure, the last
known value is served with stale: true. Never zero, never invented.

Endpoint: /api/europe/refugees/poland   (?force=true to bypass freshness)
Debug:    /debug/poland-refugees
"""

import json
import os
import time
from datetime import datetime, timezone

import requests
from flask import jsonify, request

# ========================================
# CONFIG
# ========================================

UPSTASH_REDIS_URL = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

REDIS_KEY = 'europe:refugees:poland'          # persists, no TTL (absence-honest)
FRESHNESS_SECONDS = 24 * 3600                 # logical 24h freshness window

UNHCR_URL = 'https://api.unhcr.org/population/v1/population/'
UNHCR_PARAMS = {
    'coo': 'UKR',
    'coa': 'POL',
    'cf_type': 'ISO',      # use ISO3 codes, not UNHCR internal codes
    'yearFrom': 2021,
    'limit': 20,
}
UNHCR_SOURCE_URL = 'https://api.unhcr.org/population/v1/population/?coo=UKR&coa=POL&cf_type=ISO&yearFrom=2021'

# Eurostat: beneficiaries of temporary protection at end of month (monthly)
EUROSTAT_URL = (
    'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
    'migr_asytpsm'
)
EUROSTAT_PARAMS = {
    'format': 'JSON',
    'lang': 'EN',
    'geo': 'PL',
    'citizen': 'UA',
    'sex': 'T',
    'age': 'TOTAL',
    'unit': 'PER',
}
EUROSTAT_SOURCE_URL = 'https://ec.europa.eu/eurostat/databrowser/view/migr_asytpsm/default/table'

HEADERS = {'User-Agent': 'AsifahAnalytics/1.0 (OSINT research; asifahanalytics.com)'}


# ========================================
# REDIS HELPERS (no-TTL persist pattern)
# ========================================

def _redis_load():
    """Load last-known payload from Upstash Redis. Returns dict or None."""
    if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
        try:
            resp = requests.get(
                f"{UPSTASH_REDIS_URL}/get/{REDIS_KEY}",
                headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
                timeout=5
            )
            data = resp.json()
            if data.get("result"):
                return json.loads(data["result"])
        except Exception as e:
            print(f"[Poland Refugees] Redis load error: {e}")
    return None


def _redis_save(payload):
    """Persist payload to Upstash Redis WITHOUT TTL (absence-honest)."""
    if UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN:
        try:
            resp = requests.post(
                f"{UPSTASH_REDIS_URL}/set/{REDIS_KEY}",
                headers={
                    "Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={"value": json.dumps(payload, default=str)},
                timeout=10
            )
            if resp.status_code == 200:
                print("[Poland Refugees] ✅ Saved to Redis")
        except Exception as e:
            print(f"[Poland Refugees] Redis save error: {e}")


# ========================================
# SOURCE 1 -- UNHCR Refugee Data Finder (annual, authoritative)
# ========================================

def fetch_unhcr_series():
    """
    Annual stock series of Ukrainians in Poland.
    Returns (series list, error string or None).
    Each series row: {year, total, refugees, asylum_seekers, oip}
    total = refugees + asylum_seekers + oip (temp-protection lives in oip).
    """
    try:
        resp = requests.get(UNHCR_URL, params=UNHCR_PARAMS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"UNHCR HTTP {resp.status_code}"
        data = resp.json()
        items = data.get('items') or []
        series = []
        for row in items:
            try:
                year = int(row.get('year'))
            except (TypeError, ValueError):
                continue
            refugees = int(row.get('refugees') or 0)
            asylum = int(row.get('asylum_seekers') or 0)
            oip = int(row.get('oip') or 0)
            series.append({
                'year': year,
                'refugees': refugees,
                'asylum_seekers': asylum,
                'oip': oip,
                'total': refugees + asylum + oip,
            })
        if not series:
            return None, "UNHCR returned no rows"
        series.sort(key=lambda r: r['year'])
        return series, None
    except Exception as e:
        return None, f"UNHCR fetch failed: {e}"


# ========================================
# SOURCE 2 -- Eurostat monthly TPD beneficiaries (fresher, best-effort)
# ========================================

def fetch_eurostat_monthly():
    """
    Latest + previous monthly count of Ukrainian temporary-protection
    beneficiaries in Poland. JSON-stat 2.0 parsing, fully defensive.
    Returns (dict or None, error string or None).
    dict: {latest_month, latest_value, previous_month, previous_value}
    """
    try:
        resp = requests.get(EUROSTAT_URL, params=EUROSTAT_PARAMS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"Eurostat HTTP {resp.status_code}"
        data = resp.json()
        values = data.get('value') or {}
        time_idx = (((data.get('dimension') or {}).get('time') or {})
                    .get('category') or {}).get('index') or {}
        if not values or not time_idx:
            return None, "Eurostat response missing value/time structure"
        # time_idx maps "2026-05" -> position; values keys are positions as strings
        # Keep only months that actually have a value, sorted chronologically.
        month_by_pos = {int(pos): month for month, pos in time_idx.items()}
        present = sorted(
            (pos for pos in month_by_pos if str(pos) in values),
        )
        if not present:
            return None, "Eurostat returned no populated months"
        latest_pos = present[-1]
        result = {
            'latest_month': month_by_pos[latest_pos],
            'latest_value': int(values[str(latest_pos)]),
            'previous_month': None,
            'previous_value': None,
        }
        if len(present) >= 2:
            prev_pos = present[-2]
            result['previous_month'] = month_by_pos[prev_pos]
            result['previous_value'] = int(values[str(prev_pos)])
        return result, None
    except Exception as e:
        return None, f"Eurostat fetch failed: {e}"


# ========================================
# SO-WHAT (sensor altitude: name what the dial measures + the driver)
# ========================================

def _build_so_what(trend_direction):
    """One estimative line. Sensor voice -- no deep synthesis here."""
    base = ("Refugee stock measures Poland's absorption load -- a standing "
            "pressure valve on labor supply, housing stock, and coalition politics.")
    if trend_direction == 'rising':
        return (base + " A rising count is consistent with renewed eastward "
                "displacement pressure and historically precedes tightening "
                "in host-country service and housing capacity.")
    if trend_direction == 'falling':
        return (base + " A declining count is consistent with returns or "
                "onward movement within the EU, easing absorption pressure "
                "while the war-driven baseline remains elevated.")
    return (base + " A stable count indicates absorbed, steady-state load "
            "rather than active inflow pressure.")


# ========================================
# PAYLOAD BUILDER
# ========================================

def build_payload():
    """
    Fetch both sources, assemble payload with per-field attribution.
    Returns (payload dict or None, list of source errors).
    Succeeds if AT LEAST the UNHCR annual series lands; Eurostat is enrichment.
    """
    errors = []
    unhcr_series, unhcr_err = fetch_unhcr_series()
    if unhcr_err:
        errors.append(unhcr_err)
    eurostat, euro_err = fetch_eurostat_monthly()
    if euro_err:
        errors.append(euro_err)

    if not unhcr_series and not eurostat:
        return None, errors  # total failure -> caller serves stale

    # --- headline: prefer Eurostat monthly (fresher), fallback UNHCR annual
    if eurostat:
        headline_value = eurostat['latest_value']
        headline_as_of = eurostat['latest_month']
        headline_source = 'Eurostat migr_asytpsm (temporary protection beneficiaries, end of month)'
        headline_source_url = EUROSTAT_SOURCE_URL
    else:
        latest = unhcr_series[-1]
        headline_value = latest['total']
        headline_as_of = str(latest['year'])
        headline_source = "UNHCR Refugee Data Finder (refugees + asylum-seekers + OIP, end of year)"
        headline_source_url = UNHCR_SOURCE_URL

    # --- trend: month-over-month if Eurostat has 2 points, else year-over-year
    trend = {'direction': 'flat', 'delta': None, 'delta_pct': None,
             'basis': None, 'compare_label': None}
    if eurostat and eurostat.get('previous_value'):
        delta = eurostat['latest_value'] - eurostat['previous_value']
        trend['basis'] = 'month-over-month (Eurostat)'
        trend['compare_label'] = eurostat['previous_month']
        trend['delta'] = delta
        if eurostat['previous_value'] > 0:
            trend['delta_pct'] = round(100.0 * delta / eurostat['previous_value'], 1)
        # monthly noise gate: under 1% counts as flat
        if trend['delta_pct'] is not None and abs(trend['delta_pct']) >= 1.0:
            trend['direction'] = 'rising' if delta > 0 else 'falling'
    elif unhcr_series and len(unhcr_series) >= 2:
        latest, prev = unhcr_series[-1], unhcr_series[-2]
        delta = latest['total'] - prev['total']
        trend['basis'] = 'year-over-year (UNHCR)'
        trend['compare_label'] = str(prev['year'])
        trend['delta'] = delta
        if prev['total'] > 0:
            trend['delta_pct'] = round(100.0 * delta / prev['total'], 1)
        if trend['delta_pct'] is not None and abs(trend['delta_pct']) >= 2.0:
            trend['direction'] = 'rising' if delta > 0 else 'falling'

    payload = {
        'country': 'poland',
        'situation': 'ukraine',
        'headline': {
            'value': headline_value,
            'data_as_of': headline_as_of,
            'source': headline_source,
            'source_url': headline_source_url,
        },
        'trend': trend,
        'annual_series': unhcr_series or [],
        'annual_series_source': "UNHCR Refugee Data Finder" if unhcr_series else None,
        'annual_series_source_url': UNHCR_SOURCE_URL if unhcr_series else None,
        'monthly': eurostat,
        'so_what': _build_so_what(trend['direction']),
        'source_errors': errors,       # partial failures stay visible
        'stale': False,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }
    return payload, errors


# ========================================
# CACHE ORCHESTRATION (fresh -> serve; stale -> refetch; fail -> stale-serve)
# ========================================

def _is_fresh(payload):
    try:
        fetched = datetime.fromisoformat(payload['fetched_at'])
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        return age < FRESHNESS_SECONDS
    except Exception:
        return False


def get_poland_refugees(force=False):
    """Main entry. Returns a payload dict, always (or an honest empty-state)."""
    cached = _redis_load()

    if cached and not force and _is_fresh(cached):
        cached['from_cache'] = True
        return cached

    fresh, errors = build_payload()
    if fresh:
        _redis_save(fresh)
        fresh['from_cache'] = False
        return fresh

    # total fetch failure -> absence-honest stale serve
    if cached:
        cached['stale'] = True
        cached['from_cache'] = True
        cached['stale_reason'] = '; '.join(errors) if errors else 'refresh failed'
        print(f"[Poland Refugees] ⚠️ Serving STALE (refresh failed: {errors})")
        return cached

    # nothing cached, nothing fetched -- say so, never invent
    return {
        'country': 'poland',
        'situation': 'ukraine',
        'headline': None,
        'status': 'unavailable',
        'stale': True,
        'stale_reason': '; '.join(errors) if errors else 'no data and no cache',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }


# ========================================
# FLASK REGISTRATION
# ========================================

def register_poland_refugee_endpoints(app):
    """Wire /api/europe/refugees/poland into the Europe backend."""

    @app.route('/api/europe/refugees/poland')
    def poland_refugees():
        force = request.args.get('force', '').lower() == 'true'
        return jsonify(get_poland_refugees(force=force))

    @app.route('/debug/poland-refugees')
    def poland_refugees_debug():
        """Raw source statuses for deploy verification."""
        unhcr_series, unhcr_err = fetch_unhcr_series()
        eurostat, euro_err = fetch_eurostat_monthly()
        return jsonify({
            'unhcr_rows': len(unhcr_series) if unhcr_series else 0,
            'unhcr_latest': unhcr_series[-1] if unhcr_series else None,
            'unhcr_error': unhcr_err,
            'eurostat': eurostat,
            'eurostat_error': euro_err,
            'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
            'redis_key': REDIS_KEY,
        })

    print("[Poland Refugees] Routes registered: /api/europe/refugees/poland, /debug/poland-refugees")
