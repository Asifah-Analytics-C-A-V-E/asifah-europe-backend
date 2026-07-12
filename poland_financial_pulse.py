"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — POLAND FINANCIAL PULSE
  v1.0.0 (Jul 12 2026) · Europe backend
═══════════════════════════════════════════════════════════════════════

Canonical Financial Pulse card (Saudi/Nigeria/Russia/Kazakhstan Gold Standard),
Poland edition. Serves /api/europe/financial/poland.

DOCTRINE (Rachel, Jul 12 2026): "The financial pulse on stability is just dry
info -- interpretation belongs to the rhetoric page." This module is a SENSOR.
It reports prices, deltas, market status, sources and timestamps. It does not
interpret. The analyst layer (rhetoric tracker / interpreter / BLUF / GPI) does.

FOUR TILES — each answers a DIFFERENT question. None redundant.

  1. WIG20            Warsaw blue-chip index. Domestic equity / risk appetite.
                      Failover chain: WIG20.WA -> ^WIG20 -> EPOL (the US-listed
                      MSCI Poland ETF, i.e. foreign capital's view of Poland).
                      If we end up on EPOL the tile SAYS so -- a substitute is
                      labelled, never disguised.

  2. USD/PLN          Zloty FX stress. INVERTED polarity: rising = weaker zloty.

  3. THE ATTRITION TILE ***
                      Poland's 2026 defence budget is 200bn zloty (~$55bn) =
                      4.83% of GDP -- nearly triple NATO's minimum and above the
                      US -- and the deficit runs at 6.3% of GDP, well past the
                      EU's 3% limit. Tusk: "We won't defend the Polish border
                      with a small deficit." That spending is DEBT-FINANCED.

                      So the market's price on the armament spiral IS the
                      analytical object. Russia's hybrid strategy is cost
                      imposition without firing a shot; this tile is where you
                      watch the bill arrive.

                      Preferred instrument: Polish 10Y sovereign yield.
                      Yahoo's coverage of PL sovereigns is unreliable, so we try
                      a candidate chain and FAIL HONESTLY to EUAD (European
                      aerospace & defence sector) -- the market's price on
                      European rearmament. Whichever resolves, the tile reports
                      WHICH, and the debug endpoint reports why the others died.

  4. ORLEN (PKN.WA)   Poland's state energy champion. Post-2022, Poland cut
                      Russian gas and rebuilt supply via Baltic Pipe (Norway) +
                      LNG at Swinoujscie. Energy independence was ACHIEVED, and
                      it was PAID FOR. This tile is the price tag.

ENDPOINTS:
  GET /api/europe/financial/poland             (Redis-cached, 12h)
  GET /api/europe/financial/poland?force=true  (bypass cache)
  GET /debug/poland-financial                  (which tickers resolved + why not)

USAGE FROM app.py:
    from poland_financial_pulse import register_poland_financial_endpoints
    register_poland_financial_endpoints(app)
"""

import os
import json
import time
import threading
from datetime import datetime, timezone, timedelta

import requests
from flask import jsonify, request

VERSION = '1.0.0'

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')

REDIS_KEY     = 'europe:financial:poland'
CACHE_TTL_SEC = 12 * 3600
REFRESH_SEC   = 12 * 3600
SCAN_LOCK_KEY = 'lock:pl:financial:scan'

# Per-ticker last-error registry — surfaced by /debug/poland-financial so a
# failed tile says WHY it failed instead of just showing N/A. (KAP.IL lesson.)
_LAST_ERRORS = {}

# ── Defence-attrition reference (static, sourced, data_as_of) ──
# Data-honesty standard: static reference data always carries source +
# source_url + data_as_of. Never a bare number.
DEFENCE_ATTRITION_REFERENCE = {
    'defence_budget_pln_bn': 200,
    'defence_pct_gdp':       4.83,
    'deficit_pct_gdp':       6.3,
    'eu_deficit_limit_pct':  3.0,
    'nato_minimum_pct':      2.0,
    'note': ('Poland fields the largest army in Europe and spends 4.83% of GDP on defence '
             '-- nearly triple the NATO minimum and above the United States -- financed '
             'largely by debt, with the 2026 deficit at 6.3% of GDP against an EU limit of '
             '3%. The armament spiral is a cost imposed on Poland whether or not a shot is '
             'ever fired.'),
    'source':     'Polish 2026 budget / NATO defence-expenditure reporting',
    'source_url': 'https://www.nato.int/cps/en/natohq/topics_49198.htm',
    'data_as_of': '2026-02',
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
        print(f'[PL Financial] Redis get error: {str(e)[:120]}')
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
        print(f'[PL Financial] Redis set error: {str(e)[:120]}')
        return False


def _acquire_scan_lock(ttl_sec=600):
    """Cross-worker atomic lock — only the lock-owning worker runs the refresh."""
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
# YAHOO FETCHER (canonical helper + query1→query2 failover)
# ════════════════════════════════════════════════════════════

_YF_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/124.0.0.0 Safari/537.36'),
    'Accept': 'application/json',
}


def _fetch_yahoo_chart_with_sparkline(ticker, ticker_url_encoded=None):
    """Canonical Yahoo helper. Returns dict with value / change_pct_24h /
    sparkline (30d) / source / ticker_used / timestamp, or None.

    CRITICAL: '=' and '^' in a Yahoo ticker must be percent-encoded in the URL
    path (PLN=X -> PLN%3DX, ^WIG20 -> %5EWIG20) or Yahoo errors out.
    (Hard-won in russia_stability.py and again in kazakhstan_financial_pulse.py.)

    SPARKLINE-DERIVED 24H MATH: previousClose can equal chartPreviousClose on
    weekends, so the delta comes from sparkline[-1] vs sparkline[-2].
    """
    if ticker_url_encoded is None:
        ticker_url_encoded = ticker.replace('=', '%3D').replace('^', '%5E')
    for host in ('query1', 'query2'):
        url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{ticker_url_encoded}'
        try:
            r = requests.get(url, params={'interval': '1d', 'range': '1mo'},
                             timeout=10, headers=_YF_HEADERS)
            _LAST_ERRORS[ticker] = f'HTTP {r.status_code} via {host}'
            if r.status_code != 200:
                print(f'[PL Financial] {ticker} via {host}: HTTP {r.status_code} (url={url})')
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
                _LAST_ERRORS[ticker] = 'resolved but no usable price/prev_close'
                continue

            change_pct = ((float(price) - float(prev_close)) / float(prev_close)) * 100
            _LAST_ERRORS.pop(ticker, None)
            return {
                'value':          round(float(price), 4),
                'change_pct_24h': round(change_pct, 2),
                'sparkline':      sparkline[-30:],
                'source':         'Yahoo Finance',
                'ticker_used':    ticker,
                'currency':       meta.get('currency'),
                'timestamp':      datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            _LAST_ERRORS[ticker] = f'{type(e).__name__}: {str(e)[:80]}'
            print(f'[PL Financial] {ticker} via {host}: {str(e)[:100]}')
            continue
    print(f'[PL Financial] {ticker}: all hosts failed '
          f'(last: {_LAST_ERRORS.get(ticker, "unknown")})')
    return None


def _fetch_chain(candidates):
    """Try each ticker in order; return the first that resolves, tagged with
    which one won. ABSENCE-HONEST: returns None if the whole chain fails, and
    every failure is recorded in _LAST_ERRORS for the debug endpoint.

    A substitute instrument is LABELLED, never disguised as the original."""
    for i, tk in enumerate(candidates):
        out = _fetch_yahoo_chart_with_sparkline(tk)
        if out:
            out['is_substitute'] = (i > 0)
            out['chain_position'] = i
            if i > 0:
                print(f'[PL Financial] {candidates[0]} unavailable -- '
                      f'resolved via substitute {tk}')
            return out
    return None


# ════════════════════════════════════════════════════════════
# MARKET STATUS
# ════════════════════════════════════════════════════════════

def _gpw_market_status():
    """Warsaw Stock Exchange (GPW). Continuous 09:00-17:00 CET, closing auction
    to 17:05. CET/CEST approximated: CEST (UTC+2) late Mar-late Oct."""
    now = datetime.now(timezone.utc)
    cest = 3 <= now.month <= 10
    warsaw = now + timedelta(hours=2 if cest else 1)
    if warsaw.weekday() >= 5:
        return 'closed'
    minutes = warsaw.hour * 60 + warsaw.minute
    pre_open, open_min, close_min = 8 * 60 + 30, 9 * 60, 17 * 60 + 5
    if minutes < pre_open:
        return 'closed'
    if minutes < open_min:
        return 'pre-market'
    if minutes < close_min:
        return 'open'
    return 'after-hours'


def _us_market_status():
    """NYSE/NASDAQ (for EPOL / EUAD substitutes). 09:30-16:00 ET."""
    now = datetime.now(timezone.utc)
    edt = 3 <= now.month <= 11
    et = now - timedelta(hours=4 if edt else 5)
    if et.weekday() >= 5:
        return 'closed'
    minutes = et.hour * 60 + et.minute
    if minutes < 4 * 60:
        return 'closed'
    if minutes < 9 * 60 + 30:
        return 'pre-market'
    if minutes < 16 * 60:
        return 'open'
    if minutes < 20 * 60:
        return 'after-hours'
    return 'closed'


def _fx_market_status():
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
    for s in ('open', 'pre-market', 'after-hours'):
        if s in statuses:
            return s
    return 'closed'


# ════════════════════════════════════════════════════════════
# TIER LOGIC (polarity-aware)
# ════════════════════════════════════════════════════════════

def _fp_tier(chg, inverted=False):
    """Tile colour band.
      Standard polarity (WIG20, Orlen): rising = good.
      Inverted polarity (USD/PLN, and a YIELD): rising = bad.
        - USD/PLN rising  = weaker zloty.
        - Bond yield rising = borrowing costs more = the armament spiral is
          getting more expensive. (If the attrition tile falls back to EUAD --
          a defence EQUITY -- polarity flips back to standard, because a rising
          defence sector is not itself a stress signal. Handled at call site.)
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


def _empty_tile(name, ticker, market_status, note):
    """Shell tile when a fetcher fails — ABSENCE-HONEST. We never invent a
    number to fill a tile."""
    return {
        'name': name, 'ticker': ticker, 'value': None, 'change_pct_24h': None,
        'trend': 'flat', 'tier': 'stable', 'source': None,
        'market_status': market_status, 'timestamp': None, 'sparkline': [],
        'note': note, 'unavailable': True,
    }


# ════════════════════════════════════════════════════════════
# BUILD THE CARD
# ════════════════════════════════════════════════════════════

# Candidate chains. First entry is the instrument we WANT; the rest are
# labelled substitutes.
WIG20_CHAIN     = ['WIG20.WA', '^WIG20', 'EPOL']
PLN_CHAIN       = ['PLN=X']
# Polish 10Y sovereign yield: Yahoo's PL sovereign coverage is unreliable, so we
# try the plausible symbols and then fail honestly to the European defence
# sector -- a different instrument answering an adjacent question, and LABELLED.
ATTRITION_CHAIN = ['PL10YT=RR', '^PL10Y', 'EUAD']
ORLEN_CHAIN     = ['PKN.WA', 'PKN.PW']


def _build_financial_pulse(wig_full, pln_full, attr_full, orlen_full):
    gpw_status = _gpw_market_status()
    fx_status  = _fx_market_status()
    us_status  = _us_market_status()

    tiles = {}

    # ── Tile 1: WIG20 (or labelled substitute) ──
    if wig_full:
        sub = wig_full.get('is_substitute')
        tk = wig_full.get('ticker_used', 'WIG20.WA')
        is_epol = (tk == 'EPOL')
        tiles['WIG20'] = {
            'name':           'MSCI Poland ETF' if is_epol else 'WIG20 (Warsaw)',
            'ticker':         tk,
            'value':          wig_full.get('value'),
            'change_pct_24h': wig_full.get('change_pct_24h'),
            'trend':          _trend(wig_full.get('change_pct_24h')),
            'tier':           _fp_tier(wig_full.get('change_pct_24h')),
            'source':         wig_full.get('source'),
            'market_status':  us_status if is_epol else gpw_status,
            'timestamp':      wig_full.get('timestamp'),
            'sparkline':      wig_full.get('sparkline', []),
            'is_substitute':  bool(sub),
            'note': ('SUBSTITUTE: WIG20 unavailable -- showing the US-listed MSCI Poland ETF '
                     "(foreign capital's view of Poland)." if is_epol
                     else 'Warsaw blue-chip index -- domestic equity sentiment and risk appetite.'),
        }
    else:
        tiles['WIG20'] = _empty_tile('WIG20 (Warsaw)', 'WIG20.WA', gpw_status,
                                     'Warsaw blue-chip index -- domestic risk appetite')

    # ── Tile 2: USD/PLN (INVERTED) ──
    if pln_full:
        tiles['PLNUSD'] = {
            'name':           'USD/PLN',
            'ticker':         'PLN=X',
            'value':          pln_full.get('value'),
            'change_pct_24h': pln_full.get('change_pct_24h'),
            'trend':          _trend(pln_full.get('change_pct_24h')),
            'tier':           _fp_tier(pln_full.get('change_pct_24h'), inverted=True),
            'source':         pln_full.get('source'),
            'market_status':  fx_status,
            'timestamp':      pln_full.get('timestamp'),
            'sparkline':      pln_full.get('sparkline', []),
            'note':           'INVERTED polarity: rising USD/PLN = weaker zloty.',
        }
    else:
        tiles['PLNUSD'] = _empty_tile('USD/PLN', 'PLN=X', fx_status, 'Zloty FX stress')

    # ── Tile 3: THE ATTRITION TILE ──
    # Poland's defence spend is debt-financed. This tile is where the bill shows
    # up. If we get the sovereign yield, polarity is INVERTED (rising yield =
    # borrowing costs more = the spiral is getting more expensive). If we fall
    # back to the defence-sector ETF, polarity is STANDARD -- a rising defence
    # sector is not itself a stress reading, and pretending otherwise would be
    # dishonest.
    if attr_full:
        tk = attr_full.get('ticker_used', '')
        is_yield = tk in ('PL10YT=RR', '^PL10Y')
        tiles['ATTRITION'] = {
            'name':           'Poland 10Y Yield' if is_yield else 'Europe Defence Sector',
            'ticker':         tk,
            'value':          attr_full.get('value'),
            'change_pct_24h': attr_full.get('change_pct_24h'),
            'trend':          _trend(attr_full.get('change_pct_24h')),
            'tier':           _fp_tier(attr_full.get('change_pct_24h'), inverted=is_yield),
            'source':         attr_full.get('source'),
            'market_status':  gpw_status if is_yield else us_status,
            'timestamp':      attr_full.get('timestamp'),
            'sparkline':      attr_full.get('sparkline', []),
            'is_substitute':  bool(attr_full.get('is_substitute')),
            'is_yield':       is_yield,
            'note': ('INVERTED polarity: a rising yield means Poland borrows more expensively -- '
                     'the armament spiral getting dearer. Defence spend is debt-financed.'
                     if is_yield else
                     'SUBSTITUTE: Polish 10Y sovereign yield unavailable from the feed -- showing '
                     "the European aerospace & defence sector, the market's price on European "
                     'rearmament.'),
            # The defence-attrition context rides inline (the Poland analog of
            # Russia's Urals discount and Kazakhstan's CPC route dependency).
            'defence_pct_gdp':  DEFENCE_ATTRITION_REFERENCE['defence_pct_gdp'],
            'deficit_pct_gdp':  DEFENCE_ATTRITION_REFERENCE['deficit_pct_gdp'],
            'attrition_note':   (f"Defence {DEFENCE_ATTRITION_REFERENCE['defence_pct_gdp']}% of GDP "
                                 f"(NATO min {DEFENCE_ATTRITION_REFERENCE['nato_minimum_pct']}%) · "
                                 f"deficit {DEFENCE_ATTRITION_REFERENCE['deficit_pct_gdp']}% "
                                 f"(EU limit {DEFENCE_ATTRITION_REFERENCE['eu_deficit_limit_pct']}%)"),
            'attrition_reference': DEFENCE_ATTRITION_REFERENCE,
        }
    else:
        tiles['ATTRITION'] = _empty_tile('Poland 10Y Yield', 'PL10YT=RR', gpw_status,
                                         'Cost of the armament spiral -- debt-financed defence')
        tiles['ATTRITION']['attrition_reference'] = DEFENCE_ATTRITION_REFERENCE
        tiles['ATTRITION']['attrition_note'] = (
            f"Defence {DEFENCE_ATTRITION_REFERENCE['defence_pct_gdp']}% of GDP · "
            f"deficit {DEFENCE_ATTRITION_REFERENCE['deficit_pct_gdp']}%")

    # ── Tile 4: Orlen (energy security, bought and paid for) ──
    if orlen_full:
        tiles['ORLEN'] = {
            'name':           'Orlen (Energy)',
            'ticker':         orlen_full.get('ticker_used', 'PKN.WA'),
            'value':          orlen_full.get('value'),
            'change_pct_24h': orlen_full.get('change_pct_24h'),
            'trend':          _trend(orlen_full.get('change_pct_24h')),
            'tier':           _fp_tier(orlen_full.get('change_pct_24h')),
            'source':         orlen_full.get('source'),
            'market_status':  gpw_status,
            'timestamp':      orlen_full.get('timestamp'),
            'sparkline':      orlen_full.get('sparkline', []),
            'is_substitute':  bool(orlen_full.get('is_substitute')),
            'note': ('State energy champion. Poland cut Russian gas after 2022 and rebuilt supply '
                     'via Baltic Pipe (Norway) and LNG at Swinoujscie -- independence achieved, '
                     'and paid for.'),
        }
    else:
        tiles['ORLEN'] = _empty_tile('Orlen (Energy)', 'PKN.WA', gpw_status,
                                     'State energy champion -- post-Russian-gas supply security')

    agg = _aggregate_market_status([gpw_status, fx_status, us_status])

    return {
        'country':        'PL',
        'card_label':     'Poland Financial Pulse',
        'version':        VERSION,
        'last_refreshed': datetime.now(timezone.utc).isoformat(),
        'market_status':  agg,
        'gpw_status':     gpw_status,
        'tiles':          tiles,
    }


def get_poland_financial(force=False):
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

    print('[PL Financial] Fetching fresh market data...')
    wig   = _fetch_chain(WIG20_CHAIN)
    pln   = _fetch_chain(PLN_CHAIN)
    attr  = _fetch_chain(ATTRITION_CHAIN)
    orlen = _fetch_chain(ORLEN_CHAIN)

    payload = _build_financial_pulse(wig, pln, attr, orlen)
    payload['cache_status'] = 'fresh'
    resolved = [k for k, v in payload['tiles'].items() if not v.get('unavailable')]
    subs = [k for k, v in payload['tiles'].items() if v.get('is_substitute')]
    print(f'[PL Financial] Tiles resolved: {len(resolved)}/4 -> {resolved}'
          + (f' | substitutes in use: {subs}' if subs else ''))

    _redis_set(REDIS_KEY, payload)
    return payload


# ════════════════════════════════════════════════════════════
# BACKGROUND REFRESH
# ════════════════════════════════════════════════════════════

def _background_refresh():
    time.sleep(240)
    while True:
        try:
            if _acquire_scan_lock(ttl_sec=600):
                get_poland_financial(force=True)
            else:
                print('[PL Financial] Another worker owns the refresh window -- skipping')
        except Exception as e:
            print(f'[PL Financial] Background error: {str(e)[:120]}')
        time.sleep(REFRESH_SEC)


def start_background_refresh():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()
    print('[PL Financial] Background refresh started (12h cycle, cross-worker lock)')


# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

def register_poland_financial_endpoints(app):

    @app.route('/api/europe/financial/poland', methods=['GET'])
    def api_europe_financial_poland():
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            return jsonify(get_poland_financial(force=force))
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200],
                            'country': 'PL', 'tiles': {}}), 500

    @app.route('/debug/poland-financial', methods=['GET'])
    def debug_poland_financial():
        """Which tickers resolved, which substituted, and WHY the others died.
        WIG20.WA and the PL10Y chain are the two to watch on first deploy."""
        data = get_poland_financial(force=True)
        tiles = data.get('tiles', {})
        return jsonify({
            'version':       VERSION,
            'market_status': data.get('market_status'),
            'gpw_status':    data.get('gpw_status'),
            'chains': {
                'WIG20': WIG20_CHAIN, 'PLNUSD': PLN_CHAIN,
                'ATTRITION': ATTRITION_CHAIN, 'ORLEN': ORLEN_CHAIN,
            },
            'tickers': {
                k: {
                    'ticker':        v.get('ticker'),
                    'resolved':      not v.get('unavailable', False),
                    'is_substitute': v.get('is_substitute', False),
                    'value':         v.get('value'),
                    'change_24h':    v.get('change_pct_24h'),
                    'sparkline_pts': len(v.get('sparkline') or []),
                    'market_status': v.get('market_status'),
                } for k, v in tiles.items()
            },
            'resolved_count':   sum(1 for v in tiles.values() if not v.get('unavailable')),
            'substitutes_used': [k for k, v in tiles.items() if v.get('is_substitute')],
            'last_errors':      dict(_LAST_ERRORS),
            'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
        })

    print('[PL Financial] Endpoints registered: /api/europe/financial/poland, '
          '/debug/poland-financial')
