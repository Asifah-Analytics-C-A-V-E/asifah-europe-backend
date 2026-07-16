"""
Moldova Refugee Tracker (sensor) -- v1.0.0 -- July 16, 2026
Asifah Analytics -- Europe backend

DUAL-READ migration sensor for Moldova. Unlike Poland (a one-way absorber of
Ukrainian refugees), Moldova's migration story is bidirectional and BOTH
directions are stability facts:

  INFLOW  -- Ukrainians in Moldova (the war-driven absorption load). Moldova was
             the highest PER-CAPITA refugee host in Europe at the war's outset;
             ~100-120k remain in a country of ~2.5M. A Transnistria unfreeze
             would add displacement.
  OUTFLOW -- Moldova's own emigration (the structural drain). Roughly a third of
             the working-age population lives abroad; remittances run ~15% of
             GDP. The drain is a demographic-stability fact AND the remittance
             dependency is an economic-leverage surface.

This matches the platform's bidirectional migration model (canonical for
Syria / Lebanon / Sudan / Cuba): out-migration = escalatory/structural-stress,
return = de-escalatory. Moldova joins that family.

Sources (per-field attribution, data-honesty standard):
  INFLOW
    1. UNHCR Refugee Data Finder  (coo=UKR, coa=MDA) -- annual stock
    2. Eurostat migr_asytpsm       (geo=MD, citizen=UA) -- monthly TPD, fresher
  OUTFLOW
    3. UNHCR Refugee Data Finder  (coo=MDA) -- Moldovan emigration stock proxy
       (refugees + asylum-seekers of Moldovan origin worldwide; a FLOOR, not the
       full labor-diaspora, which UNHCR does not count -- flagged in the note).
    4. World Bank WDI  (BX.TRF.PWKR.DT.GD.ZS) -- personal remittances, % of GDP,
       annual. The economic-dependency dial.

Absence-honesty: Redis key persists WITHOUT TTL. Freshness is a logical 24h
window checked against fetched_at. On refresh failure the last known value is
served with stale: true. Never zero, never invented. Each of the four sources
fails soft and independently -- the payload succeeds if ANY inflow source OR
any outflow source lands, and says exactly which ones did.

VERIFY-IN-LOGS (first deploy): hit /debug/moldova-refugees and confirm
  - unhcr_inflow_rows > 0     (UKR->MDA series present)
  - unhcr_outflow_rows > 0    (MDA-origin series present)
  - eurostat present or a clean error (geo=MD may lag; soft-fail is fine)
  - worldbank_remittance present or a clean error
Any source that logs an error string across two scans needs its params checked.

Endpoint: /api/europe/refugees/moldova   (?force=true to bypass freshness)
Debug:    /debug/moldova-refugees
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

REDIS_KEY = 'europe:refugees:moldova'         # persists, no TTL (absence-honest)
FRESHNESS_SECONDS = 24 * 3600                 # logical 24h freshness window

HEADERS = {'User-Agent': 'AsifahAnalytics/1.0 (OSINT research; asifahanalytics.com)'}

# ---- INFLOW: Ukrainians in Moldova ----
UNHCR_URL = 'https://api.unhcr.org/population/v1/population/'
UNHCR_INFLOW_PARAMS = {
    'coo': 'UKR',
    'coa': 'MDA',
    'cf_type': 'ISO',
    'yearFrom': 2021,
    'limit': 20,
}
UNHCR_INFLOW_SOURCE_URL = 'https://api.unhcr.org/population/v1/population/?coo=UKR&coa=MDA&cf_type=ISO&yearFrom=2021'

EUROSTAT_URL = (
    'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
    'migr_asytpsm'
)
EUROSTAT_PARAMS = {
    'format': 'JSON',
    'lang': 'EN',
    'geo': 'MD',
    'citizen': 'UA',
    'sex': 'T',
    'age': 'TOTAL',
    'unit': 'PER',
}
EUROSTAT_SOURCE_URL = 'https://ec.europa.eu/eurostat/databrowser/view/migr_asytpsm/default/table'

# ---- OUTFLOW: Moldovan emigration + remittance dependency ----
UNHCR_OUTFLOW_PARAMS = {
    'coo': 'MDA',          # Moldovan origin, all destinations
    'cf_type': 'ISO',
    'yearFrom': 2018,
    'limit': 40,
}
UNHCR_OUTFLOW_SOURCE_URL = 'https://api.unhcr.org/population/v1/population/?coo=MDA&cf_type=ISO&yearFrom=2018'

# World Bank WDI -- personal remittances received, % of GDP
WORLDBANK_REMITTANCE_URL = (
    'https://api.worldbank.org/v2/country/MDA/indicator/BX.TRF.PWKR.DT.GD.ZS'
)
WORLDBANK_REMITTANCE_PARAMS = {'format': 'json', 'per_page': 60}
WORLDBANK_REMITTANCE_SOURCE_URL = (
    'https://data.worldbank.org/indicator/BX.TRF.PWKR.DT.GD.ZS?locations=MD'
)


# ========================================
# REDIS HELPERS (no-TTL persist pattern)
# ========================================

def _redis_load():
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        resp = requests.get(
            f"{UPSTASH_REDIS_URL}/get/{REDIS_KEY}",
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            timeout=10,
        )
        if resp.status_code == 200:
            raw = resp.json().get('result')
            if raw:
                return json.loads(raw)
    except Exception as e:
        print(f"[Moldova Refugees] Redis load error: {e}")
    return None


def _redis_save(payload):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return
    try:
        resp = requests.post(
            f"{UPSTASH_REDIS_URL}/set/{REDIS_KEY}",
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
            data=json.dumps(payload),
            timeout=10,
        )
        if resp.status_code == 200:
            print("[Moldova Refugees] ✅ Saved to Redis")
    except Exception as e:
        print(f"[Moldova Refugees] Redis save error: {e}")


# ========================================
# INFLOW SOURCE 1 -- UNHCR annual (Ukrainians in Moldova)
# ========================================

def fetch_unhcr_inflow_series():
    """Annual stock of Ukrainians in Moldova. Returns (series, error)."""
    try:
        resp = requests.get(UNHCR_URL, params=UNHCR_INFLOW_PARAMS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"UNHCR inflow HTTP {resp.status_code}"
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
            return None, "UNHCR inflow returned no rows"
        series.sort(key=lambda r: r['year'])
        return series, None
    except Exception as e:
        return None, f"UNHCR inflow fetch failed: {e}"


# ========================================
# INFLOW SOURCE 2 -- Eurostat monthly TPD (fresher, best-effort)
# ========================================

def fetch_eurostat_monthly():
    """Latest + previous monthly Ukrainian TPD beneficiaries in Moldova.
    JSON-stat 2.0, fully defensive. Returns (dict or None, error).
    NOTE: geo='MD' coverage in migr_asytpsm can lag or be absent (Moldova is
    non-EU); a clean 'no data' here is expected-acceptable, UNHCR carries it."""
    try:
        resp = requests.get(EUROSTAT_URL, params=EUROSTAT_PARAMS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"Eurostat HTTP {resp.status_code}"
        data = resp.json()
        values = data.get('value') or {}
        time_idx = (((data.get('dimension') or {}).get('time') or {})
                    .get('category') or {}).get('index') or {}
        if not values or not time_idx:
            return None, "Eurostat response missing value/time structure (geo=MD may be uncovered)"
        month_by_pos = {int(pos): month for month, pos in time_idx.items()}
        present = sorted(pos for pos in month_by_pos if str(pos) in values)
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
# OUTFLOW SOURCE 3 -- UNHCR Moldovan-origin stock (emigration proxy floor)
# ========================================

def fetch_unhcr_outflow_series():
    """Annual stock of Moldovan-origin refugees + asylum-seekers worldwide.
    This is a FLOOR proxy for emigration pressure -- it captures forced/asylum
    outflow, NOT the far larger economic labor diaspora (UNHCR doesn't count
    that). Rising asylum-origin numbers still read as intensifying outflow
    pressure. Returns (series, error)."""
    try:
        resp = requests.get(UNHCR_URL, params=UNHCR_OUTFLOW_PARAMS, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"UNHCR outflow HTTP {resp.status_code}"
        data = resp.json()
        items = data.get('items') or []
        by_year = {}
        for row in items:
            try:
                year = int(row.get('year'))
            except (TypeError, ValueError):
                continue
            refugees = int(row.get('refugees') or 0)
            asylum = int(row.get('asylum_seekers') or 0)
            oip = int(row.get('oip') or 0)
            # sum across all destination countries for a given year
            b = by_year.setdefault(year, {'year': year, 'refugees': 0,
                                          'asylum_seekers': 0, 'oip': 0})
            b['refugees'] += refugees
            b['asylum_seekers'] += asylum
            b['oip'] += oip
        series = []
        for year in sorted(by_year):
            b = by_year[year]
            b['total'] = b['refugees'] + b['asylum_seekers'] + b['oip']
            series.append(b)
        if not series:
            return None, "UNHCR outflow returned no rows"
        return series, None
    except Exception as e:
        return None, f"UNHCR outflow fetch failed: {e}"


# ========================================
# OUTFLOW SOURCE 4 -- World Bank remittances (% of GDP)
# ========================================

def fetch_worldbank_remittances():
    """Personal remittances received, % of GDP (annual). The economic-
    dependency dial. Returns (dict or None, error).
    dict: {latest_year, latest_pct, previous_year, previous_pct}"""
    try:
        resp = requests.get(WORLDBANK_REMITTANCE_URL, params=WORLDBANK_REMITTANCE_PARAMS,
                            headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, f"World Bank HTTP {resp.status_code}"
        data = resp.json()
        # WB shape: [meta, [ {date, value}, ... ]]
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return None, "World Bank response empty/unexpected"
        rows = [r for r in data[1] if r.get('value') is not None]
        if not rows:
            return None, "World Bank returned no populated years"
        rows.sort(key=lambda r: int(r['date']))  # ascending
        latest = rows[-1]
        result = {
            'latest_year': int(latest['date']),
            'latest_pct': round(float(latest['value']), 1),
            'previous_year': None,
            'previous_pct': None,
        }
        if len(rows) >= 2:
            prev = rows[-2]
            result['previous_year'] = int(prev['date'])
            result['previous_pct'] = round(float(prev['value']), 1)
        return result, None
    except Exception as e:
        return None, f"World Bank fetch failed: {e}"


# ========================================
# TREND HELPER (shared by both directions)
# ========================================

def _series_trend(series, monthly=None, monthly_gate=1.0, annual_gate=2.0):
    """Build a trend dict from a monthly pair (preferred) or annual series."""
    trend = {'direction': 'flat', 'delta': None, 'delta_pct': None,
             'basis': None, 'compare_label': None}
    if monthly and monthly.get('previous_value'):
        delta = monthly['latest_value'] - monthly['previous_value']
        trend['basis'] = 'month-over-month (Eurostat)'
        trend['compare_label'] = monthly['previous_month']
        trend['delta'] = delta
        if monthly['previous_value'] > 0:
            trend['delta_pct'] = round(100.0 * delta / monthly['previous_value'], 1)
        if trend['delta_pct'] is not None and abs(trend['delta_pct']) >= monthly_gate:
            trend['direction'] = 'rising' if delta > 0 else 'falling'
    elif series and len(series) >= 2:
        latest, prev = series[-1], series[-2]
        delta = latest['total'] - prev['total']
        trend['basis'] = 'year-over-year (UNHCR)'
        trend['compare_label'] = str(prev['year'])
        trend['delta'] = delta
        if prev['total'] > 0:
            trend['delta_pct'] = round(100.0 * delta / prev['total'], 1)
        if trend['delta_pct'] is not None and abs(trend['delta_pct']) >= annual_gate:
            trend['direction'] = 'rising' if delta > 0 else 'falling'
    return trend


# ========================================
# SO-WHAT (sensor altitude -- names each dial + its driver)
# ========================================

def _build_so_what(inflow_dir, outflow_dir, remittance_pct):
    """Two estimative lines -- one per direction. Sensor voice, no synthesis."""
    inflow_base = ("Inflow stock measures Moldova's absorption load -- Ukrainian "
                   "displacement against a small host population (highest per-capita "
                   "in Europe at the war's outset).")
    if inflow_dir == 'rising':
        inflow_line = (inflow_base + " A rising count is consistent with renewed "
                       "displacement pressure -- historically preceding strain on "
                       "housing, services, and (in Moldova's case) the Transnistria "
                       "security calculus.")
    elif inflow_dir == 'falling':
        inflow_line = (inflow_base + " A declining count is consistent with returns "
                       "or onward movement into the EU, easing absorption load.")
    else:
        inflow_line = inflow_base + " A stable count indicates steady-state load."

    rem = f"~{remittance_pct}% of GDP" if remittance_pct is not None else "a large share of GDP"
    outflow_base = (f"Outflow measures Moldova's structural drain -- with remittances at "
                    f"{rem}, emigration is simultaneously a demographic-stability risk and "
                    f"an economic-dependency surface an external actor can pressure.")
    if outflow_dir == 'rising':
        outflow_line = (outflow_base + " Rising asylum-origin outflow is consistent with "
                        "intensifying push pressure (economic shock, political stress).")
    elif outflow_dir == 'falling':
        outflow_line = (outflow_base + " Falling outflow is consistent with easing push "
                        "pressure or improved domestic conditions.")
    else:
        outflow_line = outflow_base + " A stable outflow indicates steady-state drain."
    return {'inflow': inflow_line, 'outflow': outflow_line}


# ========================================
# PAYLOAD BUILDER (dual-read)
# ========================================

def build_payload():
    """Fetch all four sources, assemble a dual-read payload with per-field
    attribution. Succeeds if AT LEAST one inflow source OR one outflow source
    lands. Returns (payload or None, errors)."""
    errors = []

    inflow_series, e1 = fetch_unhcr_inflow_series()
    if e1: errors.append(e1)
    eurostat, e2 = fetch_eurostat_monthly()
    if e2: errors.append(e2)
    outflow_series, e3 = fetch_unhcr_outflow_series()
    if e3: errors.append(e3)
    remittances, e4 = fetch_worldbank_remittances()
    if e4: errors.append(e4)

    got_inflow = bool(inflow_series or eurostat)
    got_outflow = bool(outflow_series or remittances)
    if not got_inflow and not got_outflow:
        return None, errors  # total failure -> caller serves stale

    # ---- INFLOW block ----
    inflow = None
    if got_inflow:
        if eurostat:
            head_val, head_as_of = eurostat['latest_value'], eurostat['latest_month']
            head_src = 'Eurostat migr_asytpsm (temporary protection beneficiaries, end of month)'
            head_url = EUROSTAT_SOURCE_URL
        else:
            latest = inflow_series[-1]
            head_val, head_as_of = latest['total'], str(latest['year'])
            head_src = "UNHCR Refugee Data Finder (refugees + asylum-seekers + OIP, end of year)"
            head_url = UNHCR_INFLOW_SOURCE_URL
        inflow = {
            'headline': {'value': head_val, 'data_as_of': head_as_of,
                         'source': head_src, 'source_url': head_url},
            'trend': _series_trend(inflow_series, eurostat),
            'annual_series': inflow_series or [],
            'annual_series_source_url': UNHCR_INFLOW_SOURCE_URL if inflow_series else None,
            'monthly': eurostat,
        }

    # ---- OUTFLOW block ----
    outflow = None
    if got_outflow:
        outflow = {
            'emigration_series': outflow_series or [],
            'emigration_source': "UNHCR Refugee Data Finder (Moldovan-origin, asylum floor)" if outflow_series else None,
            'emigration_source_url': UNHCR_OUTFLOW_SOURCE_URL if outflow_series else None,
            'emigration_trend': _series_trend(outflow_series) if outflow_series else None,
            'remittances': remittances,
            'remittances_source': "World Bank WDI BX.TRF.PWKR.DT.GD.ZS (personal remittances, % of GDP)" if remittances else None,
            'remittances_source_url': WORLDBANK_REMITTANCE_SOURCE_URL if remittances else None,
        }

    inflow_dir = inflow['trend']['direction'] if inflow else 'flat'
    outflow_dir = (outflow['emigration_trend']['direction']
                   if outflow and outflow.get('emigration_trend') else 'flat')
    remittance_pct = remittances['latest_pct'] if remittances else None

    payload = {
        'country': 'moldova',
        'situation': 'dual_read',          # inflow (Ukraine) + outflow (emigration)
        'inflow': inflow,
        'outflow': outflow,
        'so_what': _build_so_what(inflow_dir, outflow_dir, remittance_pct),
        'source_errors': errors,           # partial failures stay visible
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


def get_moldova_refugees(force=False):
    """Main entry. Always returns a payload dict (or an honest empty-state)."""
    cached = _redis_load()
    if cached and not force and _is_fresh(cached):
        cached['from_cache'] = True
        return cached

    fresh, errors = build_payload()
    if fresh:
        _redis_save(fresh)
        fresh['from_cache'] = False
        return fresh

    if cached:
        cached['stale'] = True
        cached['from_cache'] = True
        cached['stale_reason'] = '; '.join(errors) if errors else 'refresh failed'
        print(f"[Moldova Refugees] ⚠️ Serving STALE (refresh failed: {errors})")
        return cached

    return {
        'country': 'moldova',
        'situation': 'dual_read',
        'inflow': None,
        'outflow': None,
        'status': 'unavailable',
        'stale': True,
        'stale_reason': '; '.join(errors) if errors else 'no data and no cache',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }


# ========================================
# FLASK REGISTRATION
# ========================================

def register_moldova_refugee_endpoints(app):
    """Wire /api/europe/refugees/moldova into the Europe backend."""

    @app.route('/api/europe/refugees/moldova')
    def moldova_refugees():
        force = request.args.get('force', '').lower() == 'true'
        return jsonify(get_moldova_refugees(force=force))

    @app.route('/debug/moldova-refugees')
    def moldova_refugees_debug():
        """Raw per-source statuses for deploy verification (VERIFY-IN-LOGS)."""
        inflow_series, e1 = fetch_unhcr_inflow_series()
        eurostat, e2 = fetch_eurostat_monthly()
        outflow_series, e3 = fetch_unhcr_outflow_series()
        remittances, e4 = fetch_worldbank_remittances()
        return jsonify({
            'unhcr_inflow_rows': len(inflow_series) if inflow_series else 0,
            'unhcr_inflow_latest': inflow_series[-1] if inflow_series else None,
            'unhcr_inflow_error': e1,
            'eurostat': eurostat,
            'eurostat_error': e2,
            'unhcr_outflow_rows': len(outflow_series) if outflow_series else 0,
            'unhcr_outflow_latest': outflow_series[-1] if outflow_series else None,
            'unhcr_outflow_error': e3,
            'worldbank_remittances': remittances,
            'worldbank_error': e4,
            'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
            'redis_key': REDIS_KEY,
        })

    print("[Moldova Refugees] Routes registered: /api/europe/refugees/moldova, /debug/moldova-refugees")
