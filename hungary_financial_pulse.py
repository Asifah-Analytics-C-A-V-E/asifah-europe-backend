"""
Asifah Analytics - Hungary Financial Pulse
==========================================
v1.0.0 -- Nov 3, 2026

Hungary's stability page had no backend of its own: everything on it came from
the rhetoric tracker, the article feed and the commodity proxy. This module
gives it the one thing those cannot -- what MONEY thinks of the reversal --
on the same canonical Financial Pulse Card the Russia / Azerbaijan / Greece
pages use.

FOUR TILES (each answers a different question):
  1. EURHUF  - EUR/HUF (EURHUF=X). The forint is the market's running verdict on
               the Magyar government and the EU-funds deal. INVERTED polarity:
               a rising EUR/HUF is a WEAKER forint.
  2. BUX     - Budapest Stock Exchange index (^BUX.BD). Domestic risk appetite.
  3. OTP     - OTP Bank (OTP.BD). Hungary's largest bank, with a large Russian /
               Ukrainian / regional footprint -- the sanctions-and-region read.
  4. MOL     - MOL Group (MOL.BD). The Druzhba refiner: Russian-crude exposure
               and the Adria / non-Russian switch live in its price.

Plus a plain-language `top_indicator` built from the four moves.

DATA SOURCE:  Yahoo Finance chart API (free, no key). Tickers are the public
              Yahoo symbols; if Yahoo stops serving one, the tile says
              "Unavailable" -- never a made-up number.
ENDPOINT:     GET /api/europe/hungary/financial-pulse   (?force=true, rate-limited)
CACHE:        Redis 'stability:hungary:financial_pulse', 12h refresh.
"""
import os
import json
import threading
import time
import requests
from datetime import datetime, timezone, timedelta
from flask import jsonify, request

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

PULSE_VERSION       = '1.0.0'
CACHE_KEY           = 'stability:hungary:financial_pulse'
SCAN_INTERVAL_HOURS = 12
FORCE_MIN_INTERVAL  = 600

_pulse_running = False
_pulse_lock    = threading.Lock()
_last_force    = {'ts': 0.0}

TILES = [
    # key,      ticker,     url-encoded,   name,                         inverted, note
    ('EURHUF', 'EURHUF=X', 'EURHUF%3DX', 'EUR/HUF',                     True,
     'INVERTED: rising EUR/HUF = weaker forint. The market\'s running verdict on Budapest.'),
    ('BUX',    '^BUX.BD',  '%5EBUX.BD',  'BUX (Budapest Stock Exchange)', False,
     'Domestic risk appetite.'),
    ('OTP',    'OTP.BD',   'OTP.BD',     'OTP Bank',                     False,
     'Largest bank; regional (incl. Russia / Ukraine) footprint -- the sanctions-and-region read.'),
    ('MOL',    'MOL.BD',   'MOL.BD',     'MOL Group',                    False,
     'The Druzhba refiner: Russian-crude exposure and the switch to Adria crude.'),
]


# ============================================
# REDIS (Upstash REST)
# ============================================
def _redis_get(key):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        r = requests.get(f"{UPSTASH_REDIS_URL}/get/{key}",
                         headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}"}, timeout=5)
        data = r.json()
        if data.get('result'):
            return json.loads(data['result'])
    except Exception as e:
        print(f"[Hungary Pulse] Redis GET error: {str(e)[:80]}")
    return None


def _redis_set(key, value):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return False
    try:
        requests.post(UPSTASH_REDIS_URL,
                      headers={"Authorization": f"Bearer {UPSTASH_REDIS_TOKEN}",
                               "Content-Type": "application/json"},
                      json=["SET", key, json.dumps(value, default=str)], timeout=5)
        return True
    except Exception as e:
        print(f"[Hungary Pulse] Redis SET error: {str(e)[:80]}")
    return False


# ============================================
# YAHOO (canonical sparkline helper)
# ============================================
def _fetch_yahoo_chart_with_sparkline(ticker, ticker_url_encoded=None):
    """Returns {price, change_pct, sparkline} or None. 24h delta from the last two
    sparkline closes (robust on weekends). Yahoo rejects bare scripts, so this
    keeps the browser-style User-Agent the other Financial Pulse modules use."""
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker_url_encoded or ticker}'
    try:
        r = requests.get(url, params={'interval': '1d', 'range': '1mo'}, timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0 (AsifahAnalytics/1.0)'})
        if r.status_code != 200:
            print(f'[Hungary Pulse] Yahoo {ticker}: HTTP {r.status_code}')
            return None
        result = (r.json().get('chart', {}).get('result') or [{}])[0]
        meta = result.get('meta', {})
        spark = []
        ts = result.get('timestamp', []) or []
        closes = (result.get('indicators', {}).get('quote') or [{}])[0].get('close', []) or []
        for i, t in enumerate(ts):
            if i < len(closes) and closes[i] is not None:
                spark.append({'time': datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                              'value': round(float(closes[i]), 4)})
        price = meta.get('regularMarketPrice')
        if price is None and spark:
            price = spark[-1]['value']
        prev = spark[-2]['value'] if len(spark) >= 2 else None
        if prev in (None, 0):
            prev = meta.get('previousClose') or meta.get('chartPreviousClose')
        if price is None or prev in (None, 0):
            return None
        return {'price': round(float(price), 4), 'change_pct': round((price - prev) / prev * 100, 3),
                'sparkline': spark}
    except Exception as e:
        print(f'[Hungary Pulse] Yahoo fetch error for {ticker}: {str(e)[:120]}')
        return None


# ============================================
# MARKET STATUS / TIERS
# ============================================
def _bse_market_status():
    """Budapest Stock Exchange: 09:00-17:00 Budapest time, Mon-Fri.
    Budapest is UTC+1 in winter, UTC+2 in summer (last Sunday Mar -> last Sunday Oct)."""
    now = datetime.now(timezone.utc)
    y = now.year

    def _last_sunday(month):
        d = datetime(y, month, 31 if month in (3, 10) else 30, tzinfo=timezone.utc)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    summer = _last_sunday(3).replace(hour=1) <= now < _last_sunday(10).replace(hour=1)
    local = now + timedelta(hours=2 if summer else 1)
    if local.weekday() >= 5:
        return 'closed'
    m = local.hour * 60 + local.minute
    if m < 8 * 60 + 15:
        return 'closed'
    if m < 9 * 60:
        return 'pre-market'
    if m < 17 * 60:
        return 'open'
    if m < 17 * 60 + 20:
        return 'after-hours'
    return 'closed'


def _fx_market_status():
    now = datetime.now(timezone.utc)
    if (now.weekday() == 5 and now.hour >= 22) or (now.weekday() == 6 and now.hour < 22):
        return 'closed'
    return 'open'


def _aggregate(statuses):
    if all(s == 'open' for s in statuses):
        return 'open'
    if all(s == 'closed' for s in statuses):
        return 'closed'
    return 'partial' if any(s == 'open' for s in statuses) else 'closed'


def _fp_tier(chg, inverted=False):
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


def _empty_tile(name, ticker, status, note):
    return {'name': name, 'ticker': ticker, 'value': None, 'change_pct_24h': 0, 'trend': 'unknown',
            'tier': 'stable', 'source': 'Unavailable', 'market_status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(), 'sparkline': [], 'note': note}


def _month_change(spark):
    if len(spark) >= 2 and spark[0]['value']:
        return round((spark[-1]['value'] - spark[0]['value']) / spark[0]['value'] * 100, 2)
    return None


# ============================================
# BUILD
# ============================================
def _top_indicator(tiles):
    """One plain sentence on what money is saying about Budapest this month."""
    fx = tiles.get('EURHUF') or {}
    bux = tiles.get('BUX') or {}
    mol = tiles.get('MOL') or {}
    live = [t for t in tiles.values() if t.get('value') is not None]
    if not live:
        return 'Markets unread this cycle -- the price feed did not answer (unread, not calm).'
    fx_m, bux_m, mol_m = fx.get('change_30d'), bux.get('change_30d'), mol.get('change_30d')
    parts = []
    if fx_m is not None:
        if fx_m <= -1.5:
            parts.append(f'the forint is firmer on the month (EUR/HUF {fx_m:+.1f}%)')
        elif fx_m >= 1.5:
            parts.append(f'the forint is weaker on the month (EUR/HUF {fx_m:+.1f}%)')
        else:
            parts.append(f'the forint is steady (EUR/HUF {fx_m:+.1f}% on the month)')
    if bux_m is not None:
        parts.append(f'Budapest equities {bux_m:+.1f}%')
    if mol_m is not None and abs(mol_m) >= 5:
        parts.append(f'MOL, the Druzhba refiner, {mol_m:+.1f}%')
    if not parts:
        return 'Markets partly read this cycle -- see the tiles.'
    stress = (fx_m or 0) >= 3 or (bux_m or 0) <= -7
    lead = 'Money is nervous about Budapest: ' if stress else 'Money is calm about Budapest: '
    return lead + ', '.join(parts) + '.'


def run_hungary_pulse_scan():
    fx_status, bse_status = _fx_market_status(), _bse_market_status()
    tiles = {}
    for key, ticker, enc, name, inverted, note in TILES:
        status = fx_status if key == 'EURHUF' else bse_status
        d = _fetch_yahoo_chart_with_sparkline(ticker, enc)
        if not d:
            tiles[key] = _empty_tile(name, ticker, status, note)
            continue
        chg = d['change_pct']
        tiles[key] = {
            'name': name, 'ticker': ticker, 'value': round(d['price'], 2), 'change_pct_24h': chg,
            'change_30d': _month_change(d['sparkline']),
            'trend': 'rising' if chg > 0.3 else ('falling' if chg < -0.3 else 'flat'),
            'tier': _fp_tier(chg, inverted=inverted), 'inverted': inverted,
            'source': 'Yahoo Finance', 'market_status': status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sparkline': d['sparkline'], 'note': note,
        }
    pulse = {
        'country': 'HU', 'card_label': 'Hungary Financial Pulse',
        'tiles': tiles, 'tile_order': [t[0] for t in TILES],
        'market_status': _aggregate([fx_status, bse_status]),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'disclaimer': 'Open-source market prices; estimative and convergence-framed -- not prediction.',
    }
    result = {'success': True, 'financial_pulse': pulse, 'top_indicator': _top_indicator(tiles),
              'tiles_live': sum(1 for t in tiles.values() if t.get('value') is not None),
              'scanned_at': datetime.now(timezone.utc).isoformat(), 'version': PULSE_VERSION}
    _redis_set(CACHE_KEY, result)
    print(f"[Hungary Pulse] Scan complete -- {result['tiles_live']}/4 tiles live")
    return result


def _background_loop():
    time.sleep(120)
    while True:
        try:
            run_hungary_pulse_scan()
        except Exception as e:
            print(f"[Hungary Pulse] Background refresh error: {str(e)[:80]}")
        time.sleep(SCAN_INTERVAL_HOURS * 3600)


def start_hungary_pulse_refresh():
    threading.Thread(target=_background_loop, daemon=True, name='HungaryPulse').start()
    print("[Hungary Pulse] Background refresh thread started")


def register_hungary_financial_endpoints(app):

    @app.route('/api/europe/hungary/financial-pulse', methods=['GET'])
    def hungary_financial_pulse():
        force = request.args.get('force', 'false').lower() in ('true', '1', 'yes')
        if force and time.time() - _last_force['ts'] < FORCE_MIN_INTERVAL:
            force = False
        if force:
            _last_force['ts'] = time.time()
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
            return jsonify(run_hungary_pulse_scan())
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500
        finally:
            with _pulse_lock:
                _pulse_running = False

    start_hungary_pulse_refresh()
    print("[Hungary Pulse] Endpoint registered: /api/europe/hungary/financial-pulse")
