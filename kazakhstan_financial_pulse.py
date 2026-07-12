"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — KAZAKHSTAN FINANCIAL PULSE
  v1.0.1 (Jul 12 2026) · Europe backend
  v1.0.1: URL-encode '=' in tickers (BZ=F -> BZ%3DF); per-ticker error registry
═══════════════════════════════════════════════════════════════════════

Canonical Financial Pulse card (Saudi/Nigeria/Russia Gold Standard),
Kazakhstan edition. Serves the shell already waiting on
kazakhstan-stability.html at /api/europe/financial/kazakhstan.

FOUR TILES — each answers a DIFFERENT analytical question. None redundant.

  1. BRENT (BZ=F)      Oil revenue baseline. CPC ROUTE-DEPENDENCY shown
                       inline. This is the Kazakh analog of Russia's Urals
                       discount, inverted: Russia's signature spread is a
                       PRICE discount (sanctions barometer); Kazakhstan's is
                       a ROUTE dependency (~80% of crude exports transit
                       Russian territory to Novorossiysk via the Caspian
                       Pipeline Consortium). Same slot on the card, opposite
                       logic. High Brent + route concentration = revenue
                       upside that Moscow can throttle at will. THAT is the
                       Kazakh story in one tile.

  2. USD/KZT (KZT=X)   Tenge FX stress. INVERTED polarity: rising USD/KZT =
                       weaker tenge. Carries oil-price transmission AND
                       Russian sanctions spillover.

  3. KAP.IL            Kazatomprom GDR (LSE International Order Book).
                       Kazakhstan is the world's #1 uranium producer (~40% of
                       global supply). This tile IS the nuclear-fuel
                       chokepoint, priced live. Failover: KAP.L.

  4. HSBK.IL           Halyk Bank GDR — domestic banking / capital-market
                       structural integrity. KASE publishes no free live
                       index feed, so this is an honest, sourced substitute
                       rather than an invented number. (Data-honesty
                       standard: never fabricate a number to fill a tile.)

DOCTRINE: this module is a SENSOR. It reports prices, deltas, and market
status with sources and timestamps. It does not interpret. The analyst layer
(rhetoric tracker / interpreter / BLUF / GPI) does the interpreting.

ENDPOINTS:
  GET /api/europe/financial/kazakhstan             (Redis-cached, 12h)
  GET /api/europe/financial/kazakhstan?force=true  (bypass cache)
  GET /debug/kazakhstan-financial                  (which tickers resolved)

USAGE FROM app.py:
    from kazakhstan_financial_pulse import register_kazakhstan_financial_endpoints
    register_kazakhstan_financial_endpoints(app)
"""

import os
import json
import time
import random
import threading
from datetime import datetime, timezone, timedelta

import requests
from flask import jsonify, request

VERSION = '1.0.2'

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')

REDIS_KEY      = 'europe:financial:kazakhstan'
CACHE_TTL_SEC  = 12 * 3600
REFRESH_SEC    = 12 * 3600
SCAN_LOCK_KEY  = 'lock:kz:financial:scan'

# ── CPC route-dependency reference (static, sourced, data_as_of) ──
# Data-honesty standard: static reference data always carries source +
# source_url + data_as_of. Never a bare number.
CPC_ROUTE_REFERENCE = {
    'share_pct':    80,
    'route':        'Caspian Pipeline Consortium (Tengiz → Novorossiysk, Russian territory)',
    'note':         'Roughly four-fifths of Kazakh crude exports transit Russian territory via CPC. '
                    'Moscow has previously suspended the terminal on maintenance and storm-damage '
                    'grounds during periods of political friction — the dependency is the leverage.',
    'source':       'Caspian Pipeline Consortium / KazMunayGas export disclosures',
    'source_url':   'https://www.cpc.ru/en',
    'data_as_of':   '2026-07',
}


# ════════════════════════════════════════════════════════════
# REDIS
# ════════════════════════════════════════════════════════════

def _redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                         timeout=5)
        d = r.json()
        if d.get('result'):
            return json.loads(d['result'])
    except Exception as e:
        print(f'[KZ Financial] Redis get error: {str(e)[:120]}')
    return None


def _redis_set(key, value):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', key, json.dumps(value, default=str)],
                          timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f'[KZ Financial] Redis set error: {str(e)[:120]}')
        return False


def _acquire_scan_lock(ttl_sec=600):
    """Cross-worker atomic lock — only the lock-owning worker runs the
    background refresh; the other sleeps and retries next cycle."""
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return True
    try:
        r = requests.post(UPSTASH_REDIS_URL,
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                                   'Content-Type': 'application/json'},
                          json=['SET', SCAN_LOCK_KEY,
                                datetime.now(timezone.utc).isoformat(), 'NX', 'EX', ttl_sec],
                          timeout=8)
        return (r.json() or {}).get('result') == 'OK'
    except Exception:
        return True


# ════════════════════════════════════════════════════════════
# YAHOO FETCHER (canonical v1.2.0 helper + query1→query2 failover)
# ════════════════════════════════════════════════════════════

# Per-ticker last-error registry — surfaced by /debug/kazakhstan-financial so a
# failed tile says WHY it failed instead of just showing N/A.
_LAST_ERRORS = {}

# ── YAHOO RATE-LIMIT DISCIPLINE (v1.0.2, Jul 12 2026) ────────────────────
# Poland's first deploy 429'd on ALL nine tickers; this module shares the same
# Render IP and the same Yahoo quota, so it was almost certainly being throttled
# too. A 429 IS NOT A MISSING TICKER -- it is a throttle signal, and a failover
# chain that sprints past it deepens the limit while learning nothing.
_YF_MIN_GAP_SEC = 2.0
_YF_MAX_429_RETRY = 2
_yf_last_call = [0.0]
_yf_gap_lock = threading.Lock()
_THROTTLED = set()


def _yf_throttle():
    with _yf_gap_lock:
        elapsed = time.time() - _yf_last_call[0]
        if elapsed < _YF_MIN_GAP_SEC:
            time.sleep(_YF_MIN_GAP_SEC - elapsed)
        _yf_last_call[0] = time.time()


_YF_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/124.0.0.0 Safari/537.36'),
    'Accept': 'application/json',
}


def _fetch_yahoo_chart_with_sparkline(ticker, ticker_url_encoded=None):
    """Canonical Yahoo helper. Returns dict with value / change_pct_24h /
    sparkline (30d) / source / timestamp, or None.

    SPARKLINE-DERIVED 24H MATH: previousClose can equal chartPreviousClose on
    weekends (both drift to chart-range-start), so the 24h delta comes from
    sparkline[-1] vs sparkline[-2] — always the last two trading days.

    query1 → query2 failover (canonical: query1 intermittently 401s).
    """
    # CRITICAL: '=' in a Yahoo ticker MUST be percent-encoded to %3D in the URL
    # path or Yahoo returns an error. BZ=F -> BZ%3DF, KZT=X -> KZT%3DX.
    # (Hard-won in russia_stability.py, which carries the same second parameter.)
    if ticker_url_encoded is None:
        ticker_url_encoded = ticker.replace('=', '%3D').replace('^', '%5E')
    _THROTTLED.discard(ticker)

    for attempt in range(_YF_MAX_429_RETRY + 1):
      saw_429 = False
      for host in ('query1', 'query2'):
        url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{ticker_url_encoded}'
        try:
            _yf_throttle()
            r = requests.get(url, params={'interval': '1d', 'range': '1mo'},
                             timeout=10, headers=_YF_HEADERS)
            if r.status_code == 429:
                saw_429 = True
                _LAST_ERRORS[ticker] = f'HTTP 429 (rate limited) via {host}'
                print(f'[KZ Financial] {ticker} via {host}: HTTP 429 -- backing off')
                continue
            _LAST_ERRORS[ticker] = f'HTTP {r.status_code} via {host}'
            if r.status_code != 200:
                print(f'[KZ Financial] {ticker} via {host}: HTTP {r.status_code} '
                      f'(url={url})')
                continue
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
                continue

            change_pct = ((float(price) - float(prev_close)) / float(prev_close)) * 100
            return {
                'value':          round(float(price), 4),
                'change_pct_24h': round(change_pct, 2),
                'sparkline':      sparkline[-30:],
                'source':         'Yahoo Finance',
                'ticker_used':    ticker,
                'timestamp':      datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            _LAST_ERRORS[ticker] = f'{type(e).__name__}: {str(e)[:80]}'
            print(f'[KZ Financial] {ticker} via {host}: {str(e)[:100]}')
            continue

      if saw_429 and attempt < _YF_MAX_429_RETRY:
          backoff = 5 * (2 ** attempt)
          print(f'[KZ Financial] {ticker}: rate-limited, sleeping {backoff}s '
                f'(retry {attempt + 1}/{_YF_MAX_429_RETRY})')
          time.sleep(backoff)
          continue
      if saw_429:
          _THROTTLED.add(ticker)
          _LAST_ERRORS[ticker] = 'HTTP 429 (rate limited, retries exhausted)'
          print(f'[KZ Financial] {ticker}: THROTTLED -- not a missing ticker.')
          return None
      break

    print(f'[KZ Financial] {ticker}: all hosts failed '
          f'(last: {_LAST_ERRORS.get(ticker, "unknown")})')
    return None


def _fetch_with_failover(primary, fallback=None):
    """Try primary, then fallback. ABSENCE-HONEST: returns None if both fail.

    THROTTLE-AWARE: if the primary was rate-limited (429) rather than genuinely
    missing, do NOT try the fallback -- a 429 says nothing about whether the
    fallback exists, and firing it deepens the limit for zero information."""
    out = _fetch_yahoo_chart_with_sparkline(primary)
    if out:
        return out
    if primary in _THROTTLED:
        print(f'[KZ Financial] {primary} THROTTLED -- skipping fallback {fallback}')
        return None
    if fallback:
        print(f'[KZ Financial] {primary} failed -- trying fallback {fallback}')
        return _fetch_yahoo_chart_with_sparkline(fallback)
    return None


# ════════════════════════════════════════════════════════════
# MARKET STATUS (canonical pill: open / closed / pre-market / after-hours)
# ════════════════════════════════════════════════════════════

def _kase_market_status():
    """Kazakhstan Stock Exchange (KASE). Main session 11:30-17:00 Almaty
    (UTC+5, no DST). Pre-market from 11:00."""
    almaty = datetime.now(timezone.utc) + timedelta(hours=5)
    if almaty.weekday() >= 5:
        return 'closed'
    minutes = almaty.hour * 60 + almaty.minute
    pre_open, open_min, close_min = 11 * 60, 11 * 60 + 30, 17 * 60
    if minutes < pre_open:
        return 'closed'
    if minutes < open_min:
        return 'pre-market'
    if minutes < close_min:
        return 'open'
    return 'after-hours'


def _lse_iob_market_status():
    """London Stock Exchange International Order Book (Kazatomprom + Halyk
    GDRs). Main session 08:00-16:30 London. UK DST approximated: BST from
    late Mar to late Oct (UTC+1), else UTC."""
    now = datetime.now(timezone.utc)
    bst = 3 <= now.month <= 10
    london = now + timedelta(hours=1 if bst else 0)
    if london.weekday() >= 5:
        return 'closed'
    minutes = london.hour * 60 + london.minute
    pre_open, open_min, close_min = 7 * 60, 8 * 60, 16 * 60 + 30
    if minutes < pre_open:
        return 'closed'
    if minutes < open_min:
        return 'pre-market'
    if minutes < close_min:
        return 'open'
    return 'after-hours'


def _brent_market_status():
    """Brent futures trade nearly 24h Sun evening - Fri evening (ICE)."""
    now = datetime.now(timezone.utc)
    wd = now.weekday()
    if wd == 5:
        return 'closed'
    if wd == 6 and now.hour < 23:
        return 'closed'
    return 'open'


def _fx_market_status():
    """FX is 24/5."""
    now = datetime.now(timezone.utc)
    wd = now.weekday()
    if wd == 5:
        return 'closed'
    if wd == 6 and now.hour < 21:
        return 'closed'
    if wd == 4 and now.hour >= 22:
        return 'closed'
    return 'open'


def _aggregate_market_status(statuses):
    if 'open' in statuses:
        return 'open'
    if 'pre-market' in statuses:
        return 'pre-market'
    if 'after-hours' in statuses:
        return 'after-hours'
    return 'closed'


# ════════════════════════════════════════════════════════════
# TIER LOGIC (polarity-aware)
# ════════════════════════════════════════════════════════════

def _fp_tier(chg, inverted=False):
    """Tile colour band.
      Standard polarity (Brent, KAP, HSBK): rising = good.
      Inverted polarity (USD/KZT):          rising = bad (weaker tenge).
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


def _trend(chg):
    v = chg or 0
    return 'rising' if v > 0.3 else ('falling' if v < -0.3 else 'flat')


def _empty_tile(name, ticker, market_status, note, chain=None):
    """Shell tile when a fetcher fails — keeps shape consistent and is
    ABSENCE-HONEST. We never invent a number to fill a tile."""
    _chain = chain or [ticker]
    throttled = any(tk in _THROTTLED for tk in _chain)
    return {
        'name':           name,
        'ticker':         ticker,
        'value':          None,
        'change_pct_24h': None,
        'trend':          'flat',
        'tier':           'stable',
        'source':         None,
        'market_status':  market_status,
        'timestamp':      None,
        'sparkline':      [],
        'note':           note,
        'unavailable':    True,
        'throttled':      throttled,
        'unavailable_reason': ('rate_limited' if throttled else 'no_data'),
    }


# ════════════════════════════════════════════════════════════
# BUILD THE CARD
# ════════════════════════════════════════════════════════════

def _build_financial_pulse(brent_full, kzt_full, kap_full, hsbk_full):
    brent_status = _brent_market_status()
    fx_status    = _fx_market_status()
    iob_status   = _lse_iob_market_status()

    tiles = {}

    # ── Tile 1: Brent + CPC route-dependency inline ──
    # The Kazakh signature signal. Russia's tile carries a PRICE discount;
    # Kazakhstan's carries a ROUTE dependency. Revenue upside that a
    # neighbour can throttle is a different kind of exposure entirely.
    if brent_full:
        tiles['BRENT'] = {
            'name':           'Brent Crude',
            'ticker':         'BZ=F',
            'value':          brent_full.get('value'),
            'change_pct_24h': brent_full.get('change_pct_24h'),
            'trend':          _trend(brent_full.get('change_pct_24h')),
            'tier':           _fp_tier(brent_full.get('change_pct_24h')),
            'source':         brent_full.get('source'),
            'market_status':  brent_status,
            'timestamp':      brent_full.get('timestamp'),
            'sparkline':      brent_full.get('sparkline', []),
            'note':           'Kazakh state oil revenue baseline (Tengiz · Kashagan · Karachaganak)',
            # Route-dependency inline (the Kazakh analog of the Urals discount)
            'route_share_pct':  CPC_ROUTE_REFERENCE['share_pct'],
            'route_name':       'CPC → Novorossiysk',
            'route_note':       f"~{CPC_ROUTE_REFERENCE['share_pct']}% of crude exports transit Russian "
                                f"territory via CPC · {CPC_ROUTE_REFERENCE['source']} · "
                                f"as of {CPC_ROUTE_REFERENCE['data_as_of']}",
            'route_reference':  CPC_ROUTE_REFERENCE,
        }
    else:
        tiles['BRENT'] = _empty_tile('Brent Crude', 'BZ=F', brent_status,
                                     'Kazakh state oil revenue baseline')

    # ── Tile 2: USD/KZT (INVERTED polarity) ──
    if kzt_full:
        tiles['KZTUSD'] = {
            'name':           'USD/KZT',
            'ticker':         'KZT=X',
            'value':          kzt_full.get('value'),
            'change_pct_24h': kzt_full.get('change_pct_24h'),
            'trend':          _trend(kzt_full.get('change_pct_24h')),
            'tier':           _fp_tier(kzt_full.get('change_pct_24h'), inverted=True),
            'source':         kzt_full.get('source'),
            'market_status':  fx_status,
            'timestamp':      kzt_full.get('timestamp'),
            'sparkline':      kzt_full.get('sparkline', []),
            'note':           'INVERTED polarity: rising USD/KZT = weaker tenge. Carries oil-price '
                              'transmission and Russian sanctions spillover.',
        }
    else:
        tiles['KZTUSD'] = _empty_tile('USD/KZT', 'KZT=X', fx_status, 'Tenge FX stress')

    # ── Tile 3: Kazatomprom (the uranium lever) ──
    if kap_full:
        tiles['KAZATOMPROM'] = {
            'name':           'Kazatomprom (Uranium)',
            'ticker':         kap_full.get('ticker_used', 'KAP.IL'),
            'value':          kap_full.get('value'),
            'change_pct_24h': kap_full.get('change_pct_24h'),
            'trend':          _trend(kap_full.get('change_pct_24h')),
            'tier':           _fp_tier(kap_full.get('change_pct_24h')),
            'source':         kap_full.get('source'),
            'market_status':  iob_status,
            'timestamp':      kap_full.get('timestamp'),
            'sparkline':      kap_full.get('sparkline', []),
            'note':           "World's largest uranium producer (~40% of global supply). The nuclear-fuel "
                              'chokepoint, priced live — GDR on the LSE International Order Book.',
        }
    else:
        tiles['KAZATOMPROM'] = _empty_tile('Kazatomprom (Uranium)', 'KAP.IL', iob_status,
                                           "World's largest uranium producer (~40% of global supply)")

    # ── Tile 4: Halyk Bank (domestic capital-market structural integrity) ──
    if hsbk_full:
        tiles['HALYK'] = {
            'name':           'Halyk Bank (Banking Sector)',
            'ticker':         hsbk_full.get('ticker_used', 'HSBK.IL'),
            'value':          hsbk_full.get('value'),
            'change_pct_24h': hsbk_full.get('change_pct_24h'),
            'trend':          _trend(hsbk_full.get('change_pct_24h')),
            'tier':           _fp_tier(hsbk_full.get('change_pct_24h')),
            'source':         hsbk_full.get('source'),
            'market_status':  iob_status,
            'timestamp':      hsbk_full.get('timestamp'),
            'sparkline':      hsbk_full.get('sparkline', []),
            'note':           'Domestic banking / capital-market structural integrity. Stands in for the '
                              'KASE index, which publishes no free live feed — sourced substitute, not an '
                              'invented number.',
        }
    else:
        tiles['HALYK'] = _empty_tile('Halyk Bank (Banking Sector)', 'HSBK.IL', iob_status,
                                     'Domestic banking / capital-market structural integrity')

    agg = _aggregate_market_status([brent_status, fx_status, iob_status, _kase_market_status()])

    return {
        'country':        'KZ',
        'card_label':     'Kazakhstan Financial Pulse',
        'version':        VERSION,
        'last_refreshed': datetime.now(timezone.utc).isoformat(),
        'market_status':  agg,
        'kase_status':    _kase_market_status(),
        'tiles':          tiles,
    }


def get_kazakhstan_financial(force=False):
    if not force:
        cached = _redis_get(REDIS_KEY)
        if cached and cached.get('last_refreshed'):
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(cached['last_refreshed'])).total_seconds()
                if age < CACHE_TTL_SEC:
                    cached['cache_status'] = 'hit'
                    return cached
            except Exception:
                pass

    print('[KZ Financial] Fetching fresh market data...')
    brent = _fetch_yahoo_chart_with_sparkline('BZ=F')
    kzt   = _fetch_yahoo_chart_with_sparkline('KZT=X')
    kap   = _fetch_with_failover('KAP.IL', 'KAP.L')
    hsbk  = _fetch_with_failover('HSBK.IL', 'HSBK.L')

    payload = _build_financial_pulse(brent, kzt, kap, hsbk)
    payload['cache_status'] = 'fresh'
    resolved = [k for k, v in payload['tiles'].items() if not v.get('unavailable')]
    print(f'[KZ Financial] Tiles resolved: {len(resolved)}/4 -> {resolved}')

    _redis_set(REDIS_KEY, payload)
    return payload


# ════════════════════════════════════════════════════════════
# BACKGROUND REFRESH (cross-worker lock)
# ════════════════════════════════════════════════════════════

def _background_refresh():
    # Jittered: the Poland pulse and russia_stability share this IP and quota.
    time.sleep(180 + random.randint(0, 180))
    while True:
        try:
            if _acquire_scan_lock(ttl_sec=600):
                get_kazakhstan_financial(force=True)
            else:
                print('[KZ Financial] Another worker owns the refresh window -- skipping')
        except Exception as e:
            print(f'[KZ Financial] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_SEC + random.randint(0, 600))


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[KZ Financial] Background refresh started (12h cycle, cross-worker lock)')


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

def register_kazakhstan_financial_endpoints(app):

    @app.route('/api/europe/financial/kazakhstan', methods=['GET'])
    def api_europe_financial_kazakhstan():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            return jsonify(get_kazakhstan_financial(force=force))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200],
                            'country': 'KZ', 'tiles': {}}), 500

    @app.route('/debug/kazakhstan-financial', methods=['GET'])
    def debug_kazakhstan_financial():
        """Which tickers actually resolved — first-deploy verification.
        (KAP.IL / HSBK.IL are the two to watch; both have .L failovers.)"""
        data = get_kazakhstan_financial(force=True)
        tiles = data.get('tiles', {})
        return jsonify({
            'version':        VERSION,
            'market_status':  data.get('market_status'),
            'kase_status':    data.get('kase_status'),
            'tickers': {
                k: {
                    'ticker':       v.get('ticker'),
                    'resolved':     not v.get('unavailable', False),
                    'value':        v.get('value'),
                    'change_24h':   v.get('change_pct_24h'),
                    'sparkline_pts': len(v.get('sparkline') or []),
                    'market_status': v.get('market_status'),
                } for k, v in tiles.items()
            },
            'resolved_count': sum(1 for v in tiles.values() if not v.get('unavailable')),
            'last_errors':     dict(_LAST_ERRORS),
            'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
        })

    print('[KZ Financial] Endpoints registered: /api/europe/financial/kazakhstan, /debug/kazakhstan-financial')
