"""
Asifah Analytics - Azerbaijan Financial Pulse
==============================================
Focused backend module serving the canonical Financial Pulse Card for the
azerbaijan-stability.html page. Mirrors the Saudi / Nigeria / Russia
"_fetch_yahoo_chart_with_sparkline" Gold Standard, trimmed to Azerbaijan's
hydrocarbon-driven economy.

THREE TILES (each answers a different question, none redundant):
  1. BRENT   - Brent Crude (BZ=F), global oil-revenue baseline, with the
               Azeri Light premium shown INLINE. Azeri Light is a light, sweet
               crude that trades OVER Brent; the premium is the market-access
               signal (the elegant inverse of Russia's Urals *discount*).
               Premium is a hardcoded synthetic estimate - the live differential
               is not freely available on Yahoo.
  2. GAS     - European gas TTF (TTF=F) PRIMARY, Henry Hub (NG=F) FALLBACK.
               Shah Deniz -> Southern Gas Corridor export benchmark.
  3. AZNUSD  - USD/AZN (AZN=X), manat peg-watch (~1.70, managed). INVERTED
               polarity: a flat peg is the story; movement is the devaluation
               / crisis signal.

DATA SOURCE:  Yahoo Finance chart API (free, no key).
ENDPOINT:     GET /api/europe/azerbaijan/financial-pulse  (?force=true)
CACHE:        Redis key 'stability:azerbaijan:financial_pulse' (Upstash REST), 12h.
REFRESH:      Background thread, 90s boot delay, then every 12h.

NOTE on Azeri Light premium: hardcoded estimate, last reviewed 2026-06-25.
Surfaced with an asterisk note on the tile. Update AZERI_LIGHT_PREMIUM here.
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

CACHE_KEY           = 'stability:azerbaijan:financial_pulse'
SCAN_INTERVAL_HOURS = 12

# Azeri Light synthetic premium over Brent (light sweet crude trades over Brent).
# Hardcoded estimate - the live differential is not free on Yahoo. Update + bump
# the as-of date when re-reviewed; the tile shows the as-of with an asterisk.
AZERI_LIGHT_PREMIUM       = 2.0
AZERI_LIGHT_PREMIUM_AS_OF = '2026-06-25'

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
        print(f"[Azerbaijan Pulse] Redis GET error: {str(e)[:80]}")
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
        print(f"[Azerbaijan Pulse] Redis SET error: {str(e)[:80]}")
    return False


# ============================================
# YAHOO FETCHER (canonical Saudi/Nigeria/Russia helper)
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
        print(f'[Azerbaijan Pulse] Yahoo fetch error for {ticker}: {str(e)[:120]}')
        return None


# ============================================
# MARKET STATUS HELPERS
# ============================================
def _commodity_market_status():
    """ICE Brent / TTF trade Mon-Fri effectively 24/5 (Sun 22:00 UTC -> Sat 22:00 UTC)."""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    h = now.hour
    if weekday == 5 and h >= 22:   # Sat 22:00+ = closed
        return 'closed'
    if weekday == 6 and h < 22:    # Sun before 22:00 UTC = closed
        return 'closed'
    return 'open'


def _fx_market_status():
    """USD/AZN FX - effectively 24/5 like the commodity desks."""
    return _commodity_market_status()


def _aggregate_market_status(statuses):
    """Combine per-tile statuses into a single card-level status."""
    if all(s == 'open' for s in statuses):
        return 'open'
    if all(s == 'closed' for s in statuses):
        return 'closed'
    if any(s == 'open' for s in statuses):
        return 'partial'
    return 'closed'


# ============================================
# TIER LOGIC (polarity-aware tile color band)
# ============================================
def _fp_tier(chg, inverted=False):
    """
    Financial Pulse tile tier - color band.
      Standard polarity (Brent, TTF): rising = good (rally)
      Inverted polarity (USD/AZN):    rising = bad  (weaker manat)
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
def _fetch_brent_full():
    """Brent crude (Yahoo BZ=F)."""
    try:
        data = _fetch_yahoo_chart_with_sparkline('BZ=F', 'BZ%3DF')
        if data is None:
            return None
        return {
            'value':          round(data['price'], 2),
            'change_pct_24h': data['change_pct'],
            'sparkline':      data['sparkline'],
            'source':         'Yahoo Finance (ICE Brent)',
            'timestamp':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[Azerbaijan Pulse] Brent full fetch error: {str(e)[:80]}")
        return None


def _fetch_azn_full():
    """USD/AZN (Yahoo AZN=X) - manat peg-watch."""
    try:
        data = _fetch_yahoo_chart_with_sparkline('AZN=X', 'AZN%3DX')
        if data is None:
            return None
        return {
            'value':          round(data['price'], 4),
            'change_pct_24h': data['change_pct'],
            'sparkline':      data['sparkline'],
            'source':         'Yahoo Finance',
            'timestamp':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[Azerbaijan Pulse] USD/AZN full fetch error: {str(e)[:80]}")
        return None


def _fetch_gas_full():
    """
    European gas TTF (Yahoo TTF=F) PRIMARY -> Henry Hub (NG=F) FALLBACK.

    TTF is the correct benchmark for Azerbaijani gas (it sells into Europe via
    the Southern Gas Corridor). If Yahoo does not serve TTF=F, fall back to
    Henry Hub as a directional global-gas proxy and label the tile honestly.
    """
    # Primary: Dutch TTF (European hub, EUR/MWh)
    try:
        data = _fetch_yahoo_chart_with_sparkline('TTF=F', 'TTF%3DF')
        if data is not None:
            return {
                'value':          round(data['price'], 3),
                'change_pct_24h': data['change_pct'],
                'sparkline':      data['sparkline'],
                'source':         'Yahoo Finance (Dutch TTF, EUR/MWh)',
                'benchmark':      'TTF',
                'tile_name':      'European Gas (TTF)',
                'timestamp':      datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        print(f"[Azerbaijan Pulse] TTF fetch error: {str(e)[:80]}")

    # Fallback: Henry Hub (US benchmark, USD/MMBtu) - directional proxy only
    try:
        data = _fetch_yahoo_chart_with_sparkline('NG=F', 'NG%3DF')
        if data is not None:
            return {
                'value':          round(data['price'], 3),
                'change_pct_24h': data['change_pct'],
                'sparkline':      data['sparkline'],
                'source':         'Yahoo Finance (Henry Hub - TTF unavailable, US proxy)',
                'benchmark':      'HENRY_HUB',
                'tile_name':      'Natural Gas (Henry Hub)*',
                'timestamp':      datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        print(f"[Azerbaijan Pulse] Henry Hub fallback fetch error: {str(e)[:80]}")

    return None


# ============================================
# FINANCIAL PULSE CARD ASSEMBLY (3 tiles)
# ============================================
def _build_financial_pulse(brent_full, gas_full, azn_full):
    """Assemble the canonical 3-tile Financial Pulse payload for Azerbaijan."""
    brent_status = _commodity_market_status()
    gas_status   = _commodity_market_status()
    fx_status    = _fx_market_status()

    tiles = {}

    # -- Tile 1: Brent Crude + Azeri Light premium inline --
    if brent_full:
        brent_price = brent_full.get('value')
        azeri_est = round(brent_price + AZERI_LIGHT_PREMIUM, 2) if brent_price is not None else None
        chg = brent_full.get('change_pct_24h')
        tiles['BRENT'] = {
            'name':                'Brent Crude',
            'ticker':              'BZ=F',
            'value':               brent_price,
            'change_pct_24h':      chg,
            'trend':               'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat'),
            'tier':                _fp_tier(chg),
            'source':              brent_full.get('source'),
            'market_status':       brent_status,
            'timestamp':           brent_full.get('timestamp'),
            'sparkline':           brent_full.get('sparkline', []),
            'note':                'Global oil-revenue baseline - hydrocarbons drive the economy',
            # Azeri Light premium inline (synthetic est.) - Azerbaijan signature signal
            'azeri_light_est':     azeri_est,
            'azeri_light_premium': AZERI_LIGHT_PREMIUM,
            'azeri_light_as_of':   AZERI_LIGHT_PREMIUM_AS_OF,
            'azeri_light_note':    f'Azeri Light ~ Brent + ${AZERI_LIGHT_PREMIUM:.2f}/bbl (synthetic est.) * last updated {AZERI_LIGHT_PREMIUM_AS_OF}',
        }
    else:
        tiles['BRENT'] = _empty_tile('Brent Crude', 'BZ=F', brent_status, 'Global oil-revenue baseline')

    # -- Tile 2: European Gas (TTF primary / Henry Hub fallback) --
    if gas_full:
        chg = gas_full.get('change_pct_24h')
        ticker = 'TTF=F' if gas_full.get('benchmark') == 'TTF' else 'NG=F'
        tiles['GAS'] = {
            'name':           gas_full.get('tile_name', 'European Gas (TTF)'),
            'ticker':         ticker,
            'value':          gas_full.get('value'),
            'change_pct_24h': chg,
            'trend':          'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat'),
            'tier':           _fp_tier(chg),
            'source':         gas_full.get('source'),
            'benchmark':      gas_full.get('benchmark'),
            'market_status':  gas_status,
            'timestamp':      gas_full.get('timestamp'),
            'sparkline':      gas_full.get('sparkline', []),
            'note':           'Shah Deniz -> Southern Gas Corridor export benchmark',
        }
    else:
        tiles['GAS'] = _empty_tile('European Gas (TTF)', 'TTF=F', gas_status, 'SGC gas export benchmark')

    # -- Tile 3: USD/AZN manat peg-watch (INVERTED polarity) --
    if azn_full:
        chg = azn_full.get('change_pct_24h')
        tiles['AZNUSD'] = {
            'name':           'USD/AZN',
            'ticker':         'AZN=X',
            'value':          azn_full.get('value'),
            'change_pct_24h': chg,
            'trend':          'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat'),
            'tier':           _fp_tier(chg, inverted=True),
            'source':         azn_full.get('source'),
            'market_status':  fx_status,
            'timestamp':      azn_full.get('timestamp'),
            'sparkline':      azn_full.get('sparkline', []),
            'note':           'Manat peg-watch (~1.70, managed). INVERTED: a flat peg is the story; movement = devaluation signal',
        }
    else:
        tiles['AZNUSD'] = _empty_tile('USD/AZN', 'AZN=X', fx_status, 'Manat peg-watch (INVERTED polarity)')

    card_status = _aggregate_market_status([brent_status, gas_status, fx_status])

    return {
        'tiles':         tiles,
        'tile_order':    ['BRENT', 'GAS', 'AZNUSD'],
        'market_status': card_status,
        'updated_at':    datetime.now(timezone.utc).isoformat(),
        'disclaimer':    'Open-source market signals, estimative and convergence-framed - not prediction. Azeri Light premium is a synthetic estimate.',
    }


# ============================================
# SCAN + CACHE
# ============================================
def run_azerbaijan_pulse_scan():
    """Fetch all three tiles, assemble, cache, return the full payload."""
    brent_full = _fetch_brent_full()
    gas_full   = _fetch_gas_full()
    azn_full   = _fetch_azn_full()

    pulse = _build_financial_pulse(brent_full, gas_full, azn_full)
    result = {
        'success':         True,
        'financial_pulse': pulse,
        'scanned_at':      datetime.now(timezone.utc).isoformat(),
        'version':         '1.0.0-azerbaijan-financial-pulse',
    }
    _redis_set(CACHE_KEY, result)
    print(f"[Azerbaijan Pulse] Scan complete - card status: {pulse['market_status']} | "
          f"gas benchmark: {pulse['tiles'].get('GAS', {}).get('benchmark')}")
    return result


# ============================================
# BACKGROUND REFRESH
# ============================================
def _background_loop():
    """Boot delay, then refresh every SCAN_INTERVAL_HOURS."""
    time.sleep(90)  # let other modules initialize first
    while True:
        try:
            print("[Azerbaijan Pulse] Background refresh starting...")
            run_azerbaijan_pulse_scan()
        except Exception as e:
            print(f"[Azerbaijan Pulse] Background refresh error: {str(e)[:80]}")
        time.sleep(SCAN_INTERVAL_HOURS * 3600)


def start_azerbaijan_pulse_refresh():
    t = threading.Thread(target=_background_loop, daemon=True)
    t.start()
    print("[Azerbaijan Pulse] Background refresh thread started")


# ============================================
# FLASK ENDPOINTS
# ============================================
def register_azerbaijan_financial_endpoints(app):

    @app.route('/api/europe/azerbaijan/financial-pulse', methods=['GET'])
    def azerbaijan_financial_pulse():
        """
        Azerbaijan Financial Pulse - 3 tiles (Brent+Azeri Light, Gas TTF/HH, USD/AZN).
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
            result = run_azerbaijan_pulse_scan()
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500
        finally:
            with _pulse_lock:
                _pulse_running = False

    # Start background refresh thread
    start_azerbaijan_pulse_refresh()

    print("[Azerbaijan Pulse] Endpoint registered: /api/europe/azerbaijan/financial-pulse")
