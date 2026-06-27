"""
Asifah Analytics - Greece Financial Pulse
=========================================
Focused backend module serving the canonical Financial Pulse Card for the
greece-stability.html page. Mirrors the Azerbaijan / Saudi / Nigeria / Russia
"_fetch_yahoo_chart_with_sparkline" Gold Standard, retooled for Greece's
deleveraging-and-recovery story rather than a hydrocarbon economy.

THREE TILES (each answers a different question, none redundant):
  1. ATHEX           - Athens Exchange General (Composite) Index (GD.AT),
                       Yahoo Finance. Domestic equity benchmark, standard
                       polarity (rising = good). Athens trading hours.
  2. GREK            - Global X MSCI Greece ETF (GREK), Yahoo Finance. The
                       foreign-investor-confidence proxy; ~30% Greek banks
                       (Piraeus / Alpha / NBG / Eurobank), so it tracks the
                       deleveraging / bank-recovery theme. Standard polarity.
                       NYSE Arca trading hours.
  3. GR_BUND_SPREAD  - Greek 10Y minus German Bund 10Y, in basis points, from
                       the ECB Data Portal (free, no key, MONTHLY). The market's
                       verdict on Greek solvency. INVERTED polarity: a TIGHTER
                       spread = deleveraged / recovered (good); a WIDER spread =
                       solvency stress (bad). Monthly cadence, so no live
                       "market status" - labelled 'monthly'.

DATA SOURCES: Yahoo Finance chart API (free, no key) for the two equity tiles;
              ECB Data Portal API (free, no key) for the bond spread.
ENDPOINT:     GET /api/europe/greece/financial-pulse  (?force=true)
CACHE:        Redis key 'stability:greece:financial_pulse' (Upstash REST), 12h.
REFRESH:      Background thread, 90s boot delay, then every 12h.

NOTE on the spread static fallback: the ECB series updates monthly (~8th working
day). If the live pull fails, the tile shows an approximate static fallback with
an explicit as-of date and a 'live: false' flag so absence stays honest - the
card never renders empty.
"""

import os
import json
import threading
import time
import requests
from datetime import datetime, timezone
from flask import jsonify, request

# ============================================
# CONFIG
# ============================================
UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

CACHE_KEY           = 'stability:greece:financial_pulse'
SCAN_INTERVAL_HOURS = 12

# ECB Data Portal - long-term government bond yields, monthly, EUR (free, no key).
# Series: IRS  M.{GR,DE}.L.L40.CI.0000.EUR.N.Z  (dataflow IRS is in the URL path).
ECB_BASE = 'https://data-api.ecb.europa.eu/service/data/IRS'
ECB_KEY  = 'M.GR+DE.L.L40.CI.0000.EUR.N.Z'

# Approximate static fallback for the Greek-Bund spread, used ONLY when the live
# ECB monthly pull fails. Update + bump data_as_of when re-reviewed. The tile
# surfaces 'live: false' and the as-of so it never reads as a live number.
STATIC_SPREAD = {
    'spread_bps': 93.0,
    'change_bps': None,
    'gr_yield':   3.53,
    'de_yield':   2.60,
    'period':     '2026-06',
    'source':     'Static fallback (approx; live ECB pull pending)',
    'data_as_of': '2026-06-26',
}

_pulse_running = False
_pulse_lock    = threading.Lock()


# ============================================
# REDIS HELPERS (Upstash REST)
# ============================================
def _redis_get(key):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        resp = requests.get(
            f"{UPSTASH_REDIS_URL}/get/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"},
            timeout=5
        )
        data = resp.json()
        if data.get('result'):
            return json.loads(data['result'])
    except Exception as e:
        print(f"[Greece Pulse] Redis GET error: {str(e)[:80]}")
    return None


def _redis_set(key, value):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return False
    try:
        requests.post(
            UPSTASH_REDIS_URL,
            headers={
                "Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}",
                "Content-Type": "application/json"
            },
            json=["SET", key, json.dumps(value, default=str)],
            timeout=5
        )
        return True
    except Exception as e:
        print(f"[Greece Pulse] Redis SET error: {str(e)[:80]}")
    return False


# ============================================
# YAHOO FETCHER (canonical Saudi/Nigeria/Russia/Azerbaijan helper)
# ============================================
def _fetch_yahoo_chart_with_sparkline(ticker, ticker_url_encoded=None):
    """
    Canonical Yahoo helper. Returns {price, change_pct, sparkline} or None.

    SPARKLINE-DERIVED 24H MATH: previousClose can equal chartPreviousClose on
    weekends (both drift to chart-range-start). We use sparkline[-1] vs
    sparkline[-2] for the 24h delta - always the last two trading days.
    """
    if ticker_url_encoded is None:
        ticker_url_encoded = ticker
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker_url_encoded}'
    try:
        r = requests.get(
            url,
            params={'interval': '1d', 'range': '1mo'},
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (AsifahAnalytics/1.0)'},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        result = (data.get('chart', {}).get('result') or [{}])[0]
        meta = result.get('meta', {})

        sparkline = []
        try:
            timestamps = result.get('timestamp', []) or []
            closes = (result.get('indicators', {}).get('quote') or [{}])[0].get('close', []) or []
            for i, ts in enumerate(timestamps):
                if i < len(closes) and closes[i] is not None:
                    sparkline.append({
                        'time':  datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                        'value': round(float(closes[i]), 4),
                    })
        except Exception:
            pass

        price = meta.get('regularMarketPrice')
        if price is None and sparkline:
            price = sparkline[-1]['value']

        prev_close = None
        if len(sparkline) >= 2:
            prev_close = sparkline[-2]['value']
        if prev_close in (None, 0):
            prev_close = meta.get('previousClose') or meta.get('chartPreviousClose')

        if price is None or prev_close in (None, 0):
            return None
        change_pct = ((price - prev_close) / prev_close) * 100

        return {
            'price':      round(float(price), 4),
            'change_pct': round(change_pct, 3),
            'sparkline':  sparkline,
        }
    except Exception as e:
        print(f'[Greece Pulse] Yahoo fetch error for {ticker}: {str(e)[:120]}')
        return None


# ============================================
# ECB FETCHER (Greek 10Y - German Bund 10Y spread, monthly)
# ============================================
def _fetch_ecb_spread():
    """
    Greek 10Y minus German Bund 10Y, MONTHLY, from the ECB Data Portal (free, no
    key). Returns {spread_bps, change_bps, gr_yield, de_yield, period, source}
    or None on any failure (caller falls back to STATIC_SPREAD).

    The csvdata format yields a header row plus one row per observation. We find
    the REF_AREA / TIME_PERIOD / OBS_VALUE columns by name (defensive), group by
    area, take each area's latest observation for the current spread, and the
    prior observation for the month-over-month change.
    """
    url = f'{ECB_BASE}/{ECB_KEY}'
    try:
        r = requests.get(
            url,
            params={'lastNObservations': 2, 'format': 'csvdata'},
            timeout=12,
            headers={'User-Agent': 'Mozilla/5.0 (AsifahAnalytics/1.0)'},
        )
        if r.status_code != 200:
            return None
        lines = [ln for ln in r.text.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None
        header = [h.strip().upper() for h in lines[0].split(',')]

        def col(name):
            for i, h in enumerate(header):
                if h == name:
                    return i
            return None

        i_area = col('REF_AREA')
        i_time = col('TIME_PERIOD')
        i_val  = col('OBS_VALUE')
        if i_area is None or i_time is None or i_val is None:
            return None

        series = {'GR': [], 'DE': []}
        max_i = max(i_area, i_time, i_val)
        for ln in lines[1:]:
            parts = ln.split(',')
            if len(parts) <= max_i:
                continue
            area = parts[i_area].strip().strip('"')
            period = parts[i_time].strip().strip('"')
            raw = parts[i_val].strip().strip('"')
            try:
                val = float(raw)
            except ValueError:
                continue
            if area in series:
                series[area].append((period, val))

        if not series['GR'] or not series['DE']:
            return None

        for k in series:
            series[k].sort(key=lambda x: x[0])

        gr_latest = series['GR'][-1]
        de_latest = series['DE'][-1]
        spread_now = (gr_latest[1] - de_latest[1]) * 100.0  # percentage points -> bps

        change_bps = None
        if len(series['GR']) >= 2 and len(series['DE']) >= 2:
            spread_prev = (series['GR'][-2][1] - series['DE'][-2][1]) * 100.0
            change_bps = spread_now - spread_prev

        return {
            'spread_bps': round(spread_now, 1),
            'change_bps': round(change_bps, 1) if change_bps is not None else None,
            'gr_yield':   round(gr_latest[1], 3),
            'de_yield':   round(de_latest[1], 3),
            'period':     gr_latest[0],
            'source':     'ECB Data Portal (monthly)',
        }
    except Exception as e:
        print(f'[Greece Pulse] ECB spread fetch error: {str(e)[:120]}')
        return None


# ============================================
# MARKET STATUS HELPERS
# ============================================
def _equity_market_status(open_min, close_min, pre_min=None, post_min=None):
    """
    Generic equity market status from UTC minutes-since-midnight bands.
    Weekends are closed. Bands are approximate (summer DST) - the pill is
    informational, not trading-critical.
    """
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:           # Sat / Sun
        return 'closed'
    m = now.hour * 60 + now.minute
    if open_min <= m < close_min:
        return 'open'
    if pre_min is not None and pre_min <= m < open_min:
        return 'premarket'
    if post_min is not None and close_min <= m < post_min:
        return 'afterhours'
    return 'closed'


def _athens_market_status():
    """Athens Exchange ~10:00-17:20 EEST (summer, UTC+3) = ~07:00-14:20 UTC."""
    return _equity_market_status(7 * 60, 14 * 60 + 20)


def _nyse_market_status():
    """NYSE 09:30-16:00 EDT (summer, UTC-4) = 13:30-20:00 UTC; pre 08:00, after to 24:00."""
    return _equity_market_status(13 * 60 + 30, 20 * 60, pre_min=8 * 60, post_min=24 * 60)


def _aggregate_market_status(statuses):
    """Combine per-tile statuses into a single card-level status (live equity tiles only)."""
    if all(s == 'open' for s in statuses):
        return 'open'
    if any(s == 'open' for s in statuses):
        return 'partial'
    if any(s in ('premarket', 'afterhours') for s in statuses):
        return 'partial'
    return 'closed'


# ============================================
# TIER LOGIC (polarity-aware tile color band)
# ============================================
def _fp_tier(chg, inverted=False):
    """
    Financial Pulse tile tier - color band (percent-change scale).
      Standard polarity (ATHEX, GREK): rising = good (rally)
    Tiers: rally / stable / warning / stress
    """
    if chg is None:
        return 'stable'
    c = -chg if inverted else chg
    if c <= -2:
        return 'stress'
    if c <= -1:
        return 'warning'
    if c >= 2:
        return 'rally'
    return 'stable'


def _spread_tier(change_bps):
    """
    Bond-spread tier (basis-point scale, INVERTED polarity).
    Widening (positive change) = solvency stress; tightening = recovery.
    """
    if change_bps is None:
        return 'stable'
    if change_bps >= 20:
        return 'stress'
    if change_bps >= 8:
        return 'warning'
    if change_bps <= -20:
        return 'rally'
    return 'stable'


def _empty_tile(name, ticker, market_status, note):
    """Shell tile when fetcher fails - keeps shape consistent."""
    return {
        'name':           name,
        'ticker':         ticker,
        'value':          None,
        'change_pct_24h': 0,
        'trend':          'unknown',
        'tier':           'stable',
        'source':         'Unavailable',
        'market_status':  market_status,
        'timestamp':      datetime.now(timezone.utc).isoformat(),
        'sparkline':      [],
        'note':           note,
    }


# ============================================
# *_full FETCHERS (wrap raw fetcher into tile-payload shape)
# ============================================
def _fetch_athex_full():
    try:
        data = _fetch_yahoo_chart_with_sparkline('GD.AT', 'GD.AT')
        if not data:
            return None
        return {
            'value':          data['price'],
            'change_pct_24h': data['change_pct'],
            'source':         'Yahoo Finance',
            'timestamp':      datetime.now(timezone.utc).isoformat(),
            'sparkline':      data.get('sparkline', []),
        }
    except Exception as e:
        print(f'[Greece Pulse] ATHEX fetch error: {str(e)[:100]}')
        return None


def _fetch_grek_full():
    try:
        data = _fetch_yahoo_chart_with_sparkline('GREK', 'GREK')
        if not data:
            return None
        return {
            'value':          data['price'],
            'change_pct_24h': data['change_pct'],
            'source':         'Yahoo Finance',
            'timestamp':      datetime.now(timezone.utc).isoformat(),
            'sparkline':      data.get('sparkline', []),
        }
    except Exception as e:
        print(f'[Greece Pulse] GREK fetch error: {str(e)[:100]}')
        return None


def _fetch_spread_full():
    """Live ECB spread if available, else the static fallback. Always returns a dict."""
    live = _fetch_ecb_spread()
    if live:
        live['live'] = True
        return live
    fb = dict(STATIC_SPREAD)
    fb['live'] = False
    return fb


# ============================================
# BUILD PAYLOAD
# ============================================
def _build_financial_pulse(athex_full, grek_full, spread_full):
    """Assemble the canonical 3-tile Financial Pulse payload for Greece."""
    athens_status = _athens_market_status()
    nyse_status   = _nyse_market_status()
    spread_status = 'monthly'

    tiles = {}

    # -- Tile 1: ATHEX General Index (domestic equity benchmark) --
    if athex_full:
        chg = athex_full.get('change_pct_24h')
        tiles['ATHEX'] = {
            'name':           'ATHEX General Index',
            'ticker':         'GD.AT',
            'value':          athex_full.get('value'),
            'change_pct_24h': chg,
            'trend':          'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat'),
            'tier':           _fp_tier(chg),
            'source':         athex_full.get('source'),
            'market_status':  athens_status,
            'timestamp':      athex_full.get('timestamp'),
            'sparkline':      athex_full.get('sparkline', []),
            'note':           'Athens Exchange General (Composite) Index - the domestic equity benchmark.',
        }
    else:
        tiles['ATHEX'] = _empty_tile('ATHEX General Index', 'GD.AT', athens_status,
                                     'Athens Exchange domestic equity benchmark')

    # -- Tile 2: GREK ETF (foreign-investor confidence / bank-recovery proxy) --
    if grek_full:
        chg = grek_full.get('change_pct_24h')
        tiles['GREK'] = {
            'name':           'Global X MSCI Greece ETF',
            'ticker':         'GREK',
            'value':          grek_full.get('value'),
            'change_pct_24h': chg,
            'trend':          'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat'),
            'tier':           _fp_tier(chg),
            'source':         grek_full.get('source'),
            'market_status':  nyse_status,
            'timestamp':      grek_full.get('timestamp'),
            'sparkline':      grek_full.get('sparkline', []),
            'note':           'Foreign-investor confidence proxy. ~30% Greek banks (Piraeus / Alpha / NBG / Eurobank) - the deleveraging / bank-recovery read.',
        }
    else:
        tiles['GREK'] = _empty_tile('Global X MSCI Greece ETF', 'GREK', nyse_status,
                                    'Foreign-investor confidence; ~30% Greek banks')

    # -- Tile 3: Greek 10Y - German Bund spread (ECB, monthly, INVERTED) --
    sp = spread_full or {}
    chg_bps = sp.get('change_bps')
    tiles['GR_BUND_SPREAD'] = {
        'name':           'Greek 10Y - Bund Spread',
        'ticker':         'GR10Y-DE10Y',
        'value':          sp.get('spread_bps'),
        'unit':           'bps',
        'change_pct_24h': None,                  # monthly series; 24h delta not applicable
        'change_bps':     chg_bps,
        'trend':          'rising' if (chg_bps or 0) > 1 else ('falling' if (chg_bps or 0) < -1 else 'flat'),
        'tier':           _spread_tier(chg_bps),
        'source':         sp.get('source'),
        'market_status':  spread_status,
        'timestamp':      datetime.now(timezone.utc).isoformat(),
        'sparkline':      [],
        'gr_yield':       sp.get('gr_yield'),
        'de_yield':       sp.get('de_yield'),
        'period':         sp.get('period'),
        'live':           sp.get('live', False),
        'data_as_of':     sp.get('data_as_of'),
        'note':           'Greek 10Y minus German Bund (ECB, monthly). INVERTED: tighter = deleveraged / recovered, wider = solvency stress. The market verdict on Greece.',
    }

    # Card status reflects the LIVE equity tiles only (the spread is monthly reference data).
    card_status = _aggregate_market_status([athens_status, nyse_status])

    return {
        'tiles':         tiles,
        'tile_order':    ['ATHEX', 'GREK', 'GR_BUND_SPREAD'],
        'market_status': card_status,
        'updated_at':    datetime.now(timezone.utc).isoformat(),
        'disclaimer':    'Open-source market signals, estimative and convergence-framed - not prediction. The Greek-Bund spread is monthly ECB data; the equity tiles are daily.',
    }


# ============================================
# SCAN + CACHE
# ============================================
def run_greece_pulse_scan():
    """Fetch all three tiles, assemble, cache, return the full payload."""
    athex_full  = _fetch_athex_full()
    grek_full   = _fetch_grek_full()
    spread_full = _fetch_spread_full()

    pulse = _build_financial_pulse(athex_full, grek_full, spread_full)
    result = {
        'success':         True,
        'financial_pulse': pulse,
        'scanned_at':      datetime.now(timezone.utc).isoformat(),
        'version':         '1.0.0-greece-financial-pulse',
    }
    _redis_set(CACHE_KEY, result)
    sp = pulse['tiles'].get('GR_BUND_SPREAD', {})
    print(f"[Greece Pulse] Scan complete - card status: {pulse['market_status']} | "
          f"spread: {sp.get('value')}bps live={sp.get('live')}")
    return result


# ============================================
# BACKGROUND REFRESH
# ============================================
def _background_loop():
    """Boot delay, then refresh every SCAN_INTERVAL_HOURS."""
    time.sleep(90)  # let other modules initialize first
    while True:
        try:
            print("[Greece Pulse] Background refresh starting...")
            run_greece_pulse_scan()
        except Exception as e:
            print(f"[Greece Pulse] Background refresh error: {str(e)[:80]}")
        time.sleep(SCAN_INTERVAL_HOURS * 3600)


def start_greece_pulse_refresh():
    t = threading.Thread(target=_background_loop, daemon=True)
    t.start()
    print("[Greece Pulse] Background refresh thread started")


# ============================================
# FLASK ENDPOINTS
# ============================================
def register_greece_financial_endpoints(app):

    @app.route('/api/europe/greece/financial-pulse', methods=['GET'])
    def greece_financial_pulse():
        """
        Greece Financial Pulse - 3 tiles (ATHEX GD.AT, GREK ETF, Greek-Bund spread).
        ?force=true bypasses cache and runs a fresh scan (60-90s).
        """
        force = request.args.get('force', 'false').lower() in ('true', '1', 'yes')

        if not force:
            cached = _redis_get(CACHE_KEY)
            if cached:
                cached['from_cache'] = True
                return jsonify(cached)

        global _pulse_running
        with _pulse_lock:
            if _pulse_running:
                cached = _redis_get(CACHE_KEY)
                if cached:
                    cached['from_cache'] = True
                    cached['scan_in_progress'] = True
                    return jsonify(cached)
                return jsonify({'success': False, 'error': 'Scan in progress'}), 202
            _pulse_running = True

        try:
            result = run_greece_pulse_scan()
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500
        finally:
            with _pulse_lock:
                _pulse_running = False

    # Start background refresh thread
    start_greece_pulse_refresh()

    print("[Greece Pulse] Endpoint registered: /api/europe/greece/financial-pulse")
