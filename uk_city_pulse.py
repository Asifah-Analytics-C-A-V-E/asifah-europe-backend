"""
Asifah Analytics -- United Kingdom: City of London & Financial Pulse
====================================================================
v1.0.0 -- Nov 4, 2026  (Europe backend)
v1.0.1 -- Nov 4, 2026 (eve): the first live read put three lenses at L3 on
          routine copy -- an LME daily price wrap ("plunged"), a jailed claims
          handler plus an annual premiums total (Lloyd's), and investor
          commentary (tax). Event terms are now STRUCTURAL (a JWC listing, a
          trading halt, a ban, an official figure), price words are gone, and
          each lane can demand a second subject term ('requires_also') so a
          Saudi tourism minister in London is not "Gulf money".

The UK is a pressure state, not a conflict state. Its stability story runs
through money, so this module reads money three ways:

  LENS A -- OTHER PEOPLE'S MONEY IN LONDON
      The City as the place others' influence runs through: Russian money and
      sanctions evasion, Gulf sovereign wealth, Chinese money, and the
      enforcement side (OFSI, NCA, unexplained wealth orders).

  LENS B -- LONDON PRICES THE WORLD'S RISK
      Why the City matters far beyond Britain: Lloyd's of London and its Joint
      War Committee decide what it costs to sail a war zone; the London Metal
      Exchange sets the world's metal prices; the shadow fleet lives or dies on
      who will insure it.

  LENS C -- WHAT THE CITY MEANS TO BRITAIN
      Market tiles (pound, 10-year gilt, FTSE 100, FTSE 250, Lloyd's
      underwriters, copper) plus the FISCAL-STRESS ACTOR: tax, talent and the
      gilt market -- does Britain still pull money and people, and does the
      bond market still trust the Treasury?

TWO READS WORTH THE PAGE:
  * The credibility check. Normally higher gilt yields pull the pound UP
    (better returns attract money). When yields jump AND the pound falls at the
    same time, markets are not pricing growth -- they are pricing the
    government. That was September 2022 (the mini-budget). Flagged as
    'credibility_stress'.
  * Home vs world. The FTSE 100 earns mostly abroad; the FTSE 250 is domestic
    Britain. A wide gap says the market is marking down the UK economy, not
    UK plc.

EVIDENCE RULES (platform doctrine):
  * News lanes: volume alone caps at L2. L3 needs an event term (sanctioned,
    seized, takeover, sell-off...) in headlines from 2+ separate outlets.
    News never reaches L4/L5 here.
  * A feed that did not answer is 'unread' -- never 'quiet'.
  * Market tiles never invent a number; a substitute instrument is labelled.

SOURCES (all free, keyless):
  * Prices: market_fetch.py (Yahoo via curl_cffi -> Stooq). The 10-year gilt
    has a third fallback: the Bank of England's own statistical database.
  * News: Google News RSS (en-GB), ten narrow queries per scan.

COST: no paid APIs, no Claude calls. ?force is rate-limited (10 min).

ENDPOINTS:
  GET /api/europe/uk/city-pulse          cached payload (never scans on a page load
                                          unless the cache is empty)
  GET /api/europe/uk/city-pulse?force=1   rescan (rate-limited)
  GET /api/europe/uk/city-pulse/debug     ticker + feed diagnostics

REDIS: 'stability:uk:city_pulse' (read by europe_regional_bluf.py and the ME
       market detector's analog lens for the gilt read).

VERIFY-IN-LOGS on first deploy: the Yahoo gilt symbol (^TMBMKGB-10Y), the
FTSE 250 symbol (^FTMC) and the Stooq fallbacks. /debug shows which resolved.
"""
import os
import io
import csv
import json
import re
import time
import threading
import html as _html
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests
from flask import jsonify, request

VERSION             = '1.0.1'   # Nov 4 eve: tighter event terms + a money/subject test per lane (first live read over-fired)
CACHE_KEY           = 'stability:uk:city_pulse'
SCAN_INTERVAL_HOURS = 6
FORCE_MIN_INTERVAL  = 600
LOG                 = '[UK City Pulse]'

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

# ── shared market fetcher (soft import: the module still works without it) ──
try:
    import market_fetch as _mf
    _mf.STOOQ_MAP.update({            # UK instruments -> Stooq symbols (fallback layer)
        'GBPUSD=X':     'gbpusd',
        '^FTSE':        '^ukx',
        '^TMBMKGB-10Y': '10ukyt.b',   # UK 10-year gilt yield
        'HG=F':         'hg.f',       # COMEX copper
    })
    MARKET_FETCH = True
except Exception as _e:               # pragma: no cover
    _mf = None
    MARKET_FETCH = False
    print(f'{LOG} market_fetch not available ({_e}) -- plain Yahoo fallback only')

_scan_running = False
_scan_lock    = threading.Lock()
_last_force   = {'ts': 0.0}
_feed_status  = {}

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


# ════════════════════════════════════════════════════════════
# REDIS
# ════════════════════════════════════════════════════════════
def _redis_get(key):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=5)
        res = r.json().get('result')
        return json.loads(res) if res else None
    except Exception as e:
        print(f'{LOG} Redis GET error: {str(e)[:80]}')
        return None


def _redis_set(key, value):
    if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
        return False
    try:
        requests.post(UPSTASH_REDIS_URL,
                      headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                               'Content-Type': 'application/json'},
                      json=['SET', key, json.dumps(value, default=str), 'EX', 7 * 24 * 3600], timeout=5)
        return True
    except Exception as e:
        print(f'{LOG} Redis SET error: {str(e)[:80]}')
        return False


# ════════════════════════════════════════════════════════════
# MARKET DATA
# ════════════════════════════════════════════════════════════
def _plain_yahoo(ticker):
    """Last-resort fetch if market_fetch is missing. Same canonical shape."""
    enc = ticker.replace('=', '%3D').replace('^', '%5E')
    try:
        r = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{enc}',
                         params={'interval': '1d', 'range': '1mo'}, timeout=10,
                         headers={'User-Agent': UA})
        if r.status_code != 200:
            return None
        res = (r.json().get('chart', {}).get('result') or [{}])[0]
        ts = res.get('timestamp') or []
        closes = ((res.get('indicators', {}).get('quote') or [{}])[0].get('close') or [])
        spark = [{'time': datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                  'value': round(float(c), 4)} for t, c in zip(ts, closes) if c is not None]
        if len(spark) < 2:
            return None
        return {'value': spark[-1]['value'], 'sparkline': spark, 'source': 'Yahoo Finance',
                'ticker_used': ticker, 'is_substitute': False,
                'change_pct_24h': round((spark[-1]['value'] - spark[-2]['value']) / spark[-2]['value'] * 100, 2)}
    except Exception:
        return None


def _fetch(candidates):
    if MARKET_FETCH:
        return _mf.fetch_chain(candidates, LOG)
    for i, tk in enumerate(candidates):
        out = _plain_yahoo(tk)
        if out:
            out['is_substitute'] = i > 0
            return out
    return None


def _boe_gilt_10y():
    """Bank of England statistical database: 10-year nominal zero-coupon gilt
    yield (series IUDMNZC), daily, about one working day behind. Official,
    free, keyless -- the third fallback for the gilt tile."""
    start = (datetime.now(timezone.utc) - timedelta(days=45)).strftime('%d/%b/%Y')
    url = ('https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp'
           f'?csv.x=yes&Datefrom={start}&Dateto=now&SeriesCodes=IUDMNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N')
    try:
        getter = requests.get
        kw = {'timeout': 12, 'headers': {'User-Agent': UA}}
        if MARKET_FETCH and getattr(_mf, 'CURL_CFFI_AVAILABLE', False):
            getter = _mf.cffi_requests.get
            kw['impersonate'] = 'chrome'
        r = getter(url, **kw)
        if r.status_code != 200 or 'DATE' not in r.text[:200].upper():
            _feed_status['boe_gilt'] = f'HTTP {r.status_code} / unparseable'
            return None
        spark = []
        for row in csv.reader(io.StringIO(r.text)):
            if len(row) < 2 or row[0].strip().upper() == 'DATE':
                continue
            try:
                d = datetime.strptime(row[0].strip(), '%d %b %Y').date().isoformat()
                spark.append({'time': d, 'value': round(float(row[1]), 4)})
            except ValueError:
                continue
        if len(spark) < 2:
            _feed_status['boe_gilt'] = 'fewer than 2 rows'
            return None
        _feed_status['boe_gilt'] = 'ok'
        return {'value': spark[-1]['value'], 'sparkline': spark[-30:], 'source': 'Bank of England (IADB)',
                'ticker_used': 'IUDMNZC', 'is_substitute': True,
                'change_pct_24h': round((spark[-1]['value'] - spark[-2]['value']) / spark[-2]['value'] * 100, 2)}
    except Exception as e:
        _feed_status['boe_gilt'] = f'{type(e).__name__}: {str(e)[:60]}'
        return None


def _lse_status():
    """London Stock Exchange: 08:00-16:30 London time, Mon-Fri.
    London = UTC in winter, UTC+1 from the last Sunday of March to the last Sunday of October."""
    now = datetime.now(timezone.utc)

    def last_sunday(month):
        d = datetime(now.year, month, 31, 1, tzinfo=timezone.utc)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    local = now + timedelta(hours=1 if last_sunday(3) <= now < last_sunday(10) else 0)
    if local.weekday() >= 5:
        return 'closed'
    m = local.hour * 60 + local.minute
    if m < 7 * 60 + 50:
        return 'closed'
    if m < 8 * 60:
        return 'pre-market'
    if m < 16 * 60 + 30:
        return 'open'
    if m < 16 * 60 + 45:
        return 'after-hours'
    return 'closed'


def _fx_status():
    now = datetime.now(timezone.utc)
    if (now.weekday() == 5 and now.hour >= 22) or (now.weekday() == 6 and now.hour < 22) or \
       (now.weekday() == 4 and now.hour >= 22):
        return 'closed'
    return 'open'


def _pct_30d(spark):
    if len(spark) >= 2 and spark[0]['value']:
        return round((spark[-1]['value'] - spark[0]['value']) / spark[0]['value'] * 100, 2)
    return None


def _tier_pct(chg):
    if chg is None:
        return 'stable'
    if chg <= -2:
        return 'stress'
    if chg <= -1:
        return 'warning'
    if chg >= 2:
        return 'rally'
    return 'stable'


def _tier_bp(bp):
    """Gilt yield: RISING is the stress direction."""
    if bp is None:
        return 'stable'
    if bp >= 15:
        return 'stress'
    if bp >= 8:
        return 'warning'
    if bp <= -10:
        return 'rally'
    return 'stable'


def _empty(name, ticker, status, note):
    return {'name': name, 'ticker': ticker, 'value': None, 'change_pct_24h': None, 'change_pct_30d': None,
            'trend': 'unknown', 'tier': 'stable', 'source': 'Unavailable', 'market_status': status,
            'sparkline': [], 'note': note, 'unread': True,
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _tile(name, d, status, note, kind='pct'):
    spark = d.get('sparkline') or []
    t = {'name': name, 'ticker': d.get('ticker_used'), 'value': round(float(d['value']), 4 if kind == 'fx' else 2),
         'source': d.get('source'), 'market_status': status, 'sparkline': spark, 'note': note,
         'is_substitute': bool(d.get('is_substitute')), 'timestamp': datetime.now(timezone.utc).isoformat()}
    if kind == 'yield':
        bp1 = round((spark[-1]['value'] - spark[-2]['value']) * 100, 1) if len(spark) >= 2 else None
        bp30 = round((spark[-1]['value'] - spark[0]['value']) * 100, 1) if len(spark) >= 2 else None
        t.update({'unit': '%', 'change_bp_24h': bp1, 'change_bp_30d': bp30,
                  'change_pct_24h': d.get('change_pct_24h'), 'change_pct_30d': _pct_30d(spark),
                  'tier': _tier_bp(bp1), 'inverted': True,
                  'trend': 'rising' if (bp1 or 0) > 2 else ('falling' if (bp1 or 0) < -2 else 'flat')})
    else:
        chg = d.get('change_pct_24h')
        t.update({'change_pct_24h': chg, 'change_pct_30d': _pct_30d(spark), 'tier': _tier_pct(chg),
                  'trend': 'rising' if (chg or 0) > 0.3 else ('falling' if (chg or 0) < -0.3 else 'flat')})
    return t


LLOYDS_MEMBERS = [('BEZ.L', 'Beazley'), ('HSX.L', 'Hiscox'), ('LRE.L', 'Lancashire')]


def _lloyds_basket(status):
    """Lloyd's of London is a market, not a company -- it has no share price.
    Three London-listed specialty insurers that write much of their business
    at Lloyd's stand in for it, averaged after rebasing each to 100."""
    note = ("Lloyd's itself is not listed. Average of three London-listed insurers that write at Lloyd's "
            "(Beazley, Hiscox, Lancashire), each rebased to 100. War, marine and political-risk cover is their trade.")
    members, series = [], []
    for tk, nm in LLOYDS_MEMBERS:
        d = _fetch([tk])
        if not d or len(d.get('sparkline') or []) < 2:
            continue
        sp = d['sparkline']
        base = sp[0]['value'] or None
        if not base:
            continue
        series.append({p['time']: p['value'] / base * 100 for p in sp})
        members.append({'name': nm, 'ticker': tk, 'change_pct_24h': d.get('change_pct_24h'),
                        'change_pct_30d': _pct_30d(sp)})
    name = "Lloyd's underwriters (basket)"
    if not members:
        return _empty(name, 'BEZ.L/HSX.L/LRE.L', status, note)
    dates = sorted(set.intersection(*[set(s) for s in series])) if len(series) > 1 else sorted(series[0])
    spark = [{'time': dt, 'value': round(sum(s[dt] for s in series) / len(series), 2)} for dt in dates]
    chg = [m['change_pct_24h'] for m in members if m['change_pct_24h'] is not None]
    d = {'value': spark[-1]['value'] if spark else 100.0, 'sparkline': spark, 'source': 'Yahoo Finance / Stooq',
         'ticker_used': '+'.join(m['ticker'] for m in members), 'is_substitute': True,
         'change_pct_24h': round(sum(chg) / len(chg), 2) if chg else None}
    t = _tile(name, d, status, note)
    t['members'] = members
    t['members_read'] = f'{len(members)} of {len(LLOYDS_MEMBERS)}'
    return t


def _scan_markets():
    lse, fx = _lse_status(), _fx_status()
    tiles = {}
    d = _fetch(['GBPUSD=X'])
    tiles['GBPUSD'] = _tile('Pound (GBP/USD)', d, fx, 'Dollars per pound. Falling = a weaker pound.', 'fx') if d \
        else _empty('Pound (GBP/USD)', 'GBPUSD=X', fx, 'Dollars per pound.')
    d = _fetch(['^TMBMKGB-10Y']) or _boe_gilt_10y()
    tiles['GILT10'] = _tile('10-year gilt yield', d, lse,
                            "What the UK government pays to borrow for 10 years. RISING = more expensive = the stress direction.",
                            'yield') if d else _empty('10-year gilt yield', '^TMBMKGB-10Y', lse, 'UK 10-year borrowing cost.')
    d = _fetch(['^FTSE'])
    tiles['FTSE100'] = _tile('FTSE 100', d, lse, 'Mostly global companies that happen to list in London (most earnings abroad).') if d \
        else _empty('FTSE 100', '^FTSE', lse, 'Global earners listed in London.')
    d = _fetch(['^FTMC', 'MIDD.L'])
    tiles['FTSE250'] = _tile('FTSE 250', d, lse, 'Mid-sized, mostly domestic companies: the better read on the British economy.'
                             + (' (Substitute: iShares FTSE 250 ETF.)' if d and d.get('is_substitute') else '')) if d \
        else _empty('FTSE 250', '^FTMC', lse, 'Domestic Britain.')
    tiles['LLOYDS'] = _lloyds_basket(lse)
    d = _fetch(['HG=F'])
    tiles['COPPER'] = _tile('Copper (COMEX)', d, fx, "The LME sets the world's metal prices but its data is paywalled; "
                            "COMEX copper tracks it closely. Labelled as a proxy, never as the LME price.") if d \
        else _empty('Copper (COMEX)', 'HG=F', fx, 'LME proxy.')
    statuses = [lse, fx]
    agg = 'open' if all(s == 'open' for s in statuses) else ('closed' if all(s == 'closed' for s in statuses) else 'partial')
    return tiles, agg


# ════════════════════════════════════════════════════════════
# THE TWO READS
# ════════════════════════════════════════════════════════════
def _credibility_check(tiles):
    g, p = tiles.get('GILT10') or {}, tiles.get('GBPUSD') or {}
    bp30, bp1 = g.get('change_bp_30d'), g.get('change_bp_24h')
    gbp30, gbp1 = p.get('change_pct_30d'), p.get('change_pct_24h')
    base = {'gilt_bp_30d': bp30, 'gilt_bp_24h': bp1, 'gbp_pct_30d': gbp30, 'gbp_pct_24h': gbp1,
            'analog': 'UK gilt / mini-budget crisis, Sep 2022'}
    if bp30 is None or gbp30 is None:
        return dict(base, state='unread', level=0,
                    text='Credibility check unread this cycle -- the gilt or the pound did not report. Unread, not calm.')
    if (bp1 is not None and gbp1 is not None and bp1 >= 12 and gbp1 <= -0.8):
        return dict(base, state='credibility_stress', level=3, window='today',
                    text=(f'Today gilt yields jumped {bp1:+.0f}bp while the pound fell {gbp1:.1f}%. That pairing -- '
                          'borrowing costs up and the currency down together -- is how markets price a government '
                          'rather than an economy. It was the September 2022 signature.'))
    if bp30 >= 30 and gbp30 <= -2.0:
        return dict(base, state='credibility_stress', level=3, window='30d',
                    text=(f'Over the month 10-year gilt yields are up {bp30:.0f}bp and the pound is down {abs(gbp30):.1f}%. '
                          'Higher yields would normally lift the pound; both moving against Britain at once means '
                          'money is questioning the Treasury, not just pricing interest rates. That was the September 2022 shape.'))
    if bp30 >= 30:
        return dict(base, state='rates_rising', level=2, window='30d',
                    text=(f'Gilt yields are up {bp30:.0f}bp on the month but the pound is holding ({gbp30:+.1f}%). '
                          'That reads as markets pricing interest rates or inflation, not doubting the government -- '
                          'expensive for the Treasury, not yet a credibility problem.'))
    return dict(base, state='normal', level=1 if abs(bp30) >= 15 else 0, window='30d',
                text=(f'No credibility signal: gilts {bp30:+.0f}bp and the pound {gbp30:+.1f}% on the month. '
                      'The bond market is not sending Westminster a message.'))


def _home_vs_world(tiles):
    a, b = (tiles.get('FTSE250') or {}).get('change_pct_30d'), (tiles.get('FTSE100') or {}).get('change_pct_30d')
    if a is None or b is None:
        return {'state': 'unread', 'gap_pts': None,
                'text': 'Home-vs-world read unavailable this cycle (one index did not report).'}
    gap = round(a - b, 1)
    if gap <= -4:
        st, txt = 'home_lagging', (f'Domestic Britain (FTSE 250, {a:+.1f}%) is trailing the global earners (FTSE 100, {b:+.1f}%) '
                                   f'by {abs(gap):.1f} points this month: money is marking down the UK economy, not UK plc.')
    elif gap >= 4:
        st, txt = 'home_leading', (f'Domestic Britain (FTSE 250, {a:+.1f}%) is outrunning the global earners (FTSE 100, {b:+.1f}%) '
                                   f'by {gap:.1f} points: a vote of confidence in the home economy.')
    else:
        st, txt = 'in_step', (f'The FTSE 250 ({a:+.1f}%) and FTSE 100 ({b:+.1f}%) are moving together: '
                              'no special verdict on the British economy this month.')
    return {'state': st, 'gap_pts': gap, 'text': txt}


# ════════════════════════════════════════════════════════════
# NEWS LANES (Google News RSS, en-GB)
# ════════════════════════════════════════════════════════════
UK_CTX = ['london', 'uk', 'u.k.', 'britain', 'british', 'city of', 'england', 'scotland', 'ofsi', 'westminster']

LANES = [
    # ── Lens A: other people's money in London ──
    {'id': 'russia_money', 'lens': 'foreign_money', 'label': 'Russian money & sanctions',
     'q': '(oligarch OR "Russian money" OR "sanctions evasion" OR Londongrad OR OFSI) (London OR UK OR Britain)',
     'requires_any': ['russia', 'russian', 'oligarch', 'ofsi', 'londongrad', 'kremlin'],
     'requires_also': ['money', 'sanction', 'asset', 'freeze', 'frozen', 'launder', 'property', 'mansion', 'wealth',
                       'evasion', 'ofsi', 'seized', 'yacht', 'bank'],
     'context': UK_CTX,
     'events': ['sanctioned', 'sanctions on', 'frozen', 'freeze', 'seized', 'charged', 'fined', 'raid', 'arrested',
                'convicted', 'breach', 'designated', 'asset freeze']},
    {'id': 'gulf_money', 'lens': 'foreign_money', 'label': 'Gulf money',
     'q': '("Qatar Investment Authority" OR "Abu Dhabi" OR "Saudi" OR Mubadala OR ADIA OR "Gulf investors" OR "sovereign wealth fund") (London OR UK OR Britain)',
     'requires_any': ['qatar', 'abu dhabi', 'saudi', 'mubadala', 'adia', 'gulf', 'emirati', 'uae', 'kuwait', 'pif'],
     'requires_also': ['invest', 'fund', 'stake', 'takeover', 'buys', 'bought', 'acquir', 'billion', 'property',
                       'sovereign', 'bid ', 'owner', 'deal'],
     'context': UK_CTX,
     'events': ['takeover', 'stake in', 'acquires', 'acquisition', 'bid for', 'blocked', 'national security',
                'billion deal', 'investment of', 'buys stake', 'agrees to buy']},
    {'id': 'china_money', 'lens': 'foreign_money', 'label': 'Chinese money & presence',
     'q': '("Chinese embassy" OR "Chinese investment" OR "China spy" OR "Chinese ownership") (London OR UK OR Britain)',
     'requires_any': ['china', 'chinese', 'beijing'],
     'requires_also': ['invest', 'embassy', 'spy', 'espionage', 'takeover', 'stake', 'security', 'ownership', 'acquir',
                       'sanction', 'steel', 'nuclear', 'port', 'interference'],
     'context': UK_CTX,
     'events': ['approved', 'blocked', 'charged', 'arrested', 'expelled', 'takeover', 'national security', 'banned']},
    {'id': 'enforcement', 'lens': 'foreign_money', 'label': 'Enforcement & dirty money',
     'q': '("unexplained wealth order" OR "National Crime Agency" OR "Companies House" OR "money laundering" OR "Serious Fraud Office" OR "FCA fine") UK',
     'requires_any': ['unexplained wealth', 'national crime agency', 'nca', 'companies house', 'laundering',
                      'serious fraud office', 'sfo', 'fca', 'dirty money', 'kleptocra'],
     'context': UK_CTX,
     'events': ['charged', 'fined', 'raid', 'arrested', 'convicted', 'seized', 'frozen', 'order granted', 'struck off']},
    # ── Lens B: London prices the world's risk ──
    {'id': 'lloyds', 'lens': 'world_desk', 'label': "Lloyd's & war-risk insurance",
     'q': '("Lloyd\'s of London" OR "Joint War Committee" OR "war risk" OR "war-risk premium" OR "marine insurance") shipping',
     'requires_any': ["lloyd's", 'lloyds', 'joint war committee', 'war risk', 'war-risk', 'marine insur', 'insurer', 'insurance'],
     'context': None,
     'requires_also': ['war', 'risk', 'shipping', 'marine', 'vessel', 'tanker', 'sea', 'strait', 'conflict'],
     'events': ['listed area', 'listed areas', 'joint war committee', 'war risk premium', 'war-risk premium',
                'additional premium', 'cancel cover', 'cancels cover', 'withdraw cover', 'withdraws cover',
                'suspend cover', 'notice of cancellation', 'war risk cover', 'war-risk cover', 'insurers pull',
                'uninsurable', 'refuse to insure', 'no longer insure']},
    {'id': 'lme', 'lens': 'world_desk', 'label': 'London Metal Exchange',
     'q': '"London Metal Exchange" OR (LME nickel OR LME aluminium OR LME copper OR "LME warehouse" OR "Russian metal")',
     'requires_any': ['london metal exchange', 'lme'],
     'context': None,
     'events': ['suspends', 'suspended trading', 'halts', 'halted', 'trading halt', 'bans', 'banned', 'ban on',
                'cancelled trades', 'cancels trades', 'short squeeze', 'squeeze', 'sanction', 'delist', 'position limit',
                'rule change', 'russian metal']},
    {'id': 'shadow_fleet', 'lens': 'world_desk', 'label': 'Shadow fleet & who insures it',
     'q': '"shadow fleet" (insurance OR "P&I" OR sanctions OR tanker) (UK OR Britain OR Channel OR Baltic)',
     'requires_any': ['shadow fleet', 'dark fleet'],
     'context': None,
     'events': ['sanctioned', 'detained', 'boarded', 'seized', 'stopped', 'banned', 'designated', 'uninsured']},
    # ── Lens C: what the City means to Britain (the fiscal-stress actor) ──
    {'id': 'fiscal', 'lens': 'home_economy', 'label': 'Gilts, borrowing & the fiscal rules',
     'q': '(gilts OR "gilt yields" OR "UK borrowing" OR "fiscal rules" OR "Office for Budget Responsibility" OR "black hole") (Healey OR Treasury)',
     'requires_any': ['gilt', 'borrowing', 'fiscal', 'obr', 'budget responsibility', 'black hole', 'debt'],
     'context': UK_CTX + ['healey', 'treasury', 'gilt'],
     'events': ['sell-off', 'selloff', 'surge', 'soar', 'jump', 'highest since', 'record high', 'emergency',
                'downgrade', 'breach', 'u-turn', 'rout']},
    {'id': 'tax_talent', 'lens': 'home_economy', 'label': 'Tax, wealth & talent flight',
     'q': '("non-dom" OR "wealth tax" OR "millionaire exodus" OR "leaving the UK" OR "capital gains tax" OR "exit tax") UK',
     'requires_any': ['non-dom', 'wealth tax', 'millionaire', 'exodus', 'leaving the uk', 'leave the uk', 'capital gains',
                      'exit tax', 'tax rise', 'tax raid', 'emigrat'],
     'context': UK_CTX,
     'events': ['record number', 'official figures', 'hmrc figures', 'hmrc data', 'figures show', 'data shows',
                'u-turn', 'abolish', 'scrapped', 'confirmed in the budget', 'will introduce', 'to introduce']},
    {'id': 'listings', 'lens': 'home_economy', 'label': 'Listings & the City\'s pull',
     'q': '"London Stock Exchange" (delisting OR "moves listing" OR "New York listing" OR "primary listing") OR "London listing"',
     'requires_any': ['london stock exchange', 'lse', 'listing', 'delist', 'ftse'],
     'context': None,
     'events': ['delist', 'moves listing', 'move its listing', 'switch', 'abandon', 'quits london', 'leaves london',
                'new york', 'blow to london']},
]

LENSES = {
    'foreign_money': {
        'title': "Other people's money in London",
        'so_what': ("London is where a lot of other countries' influence is banked. When Russian, Gulf or Chinese money "
                    "moves in or out -- or when Britain finally enforces against it -- that is foreign policy happening "
                    "through property, football clubs, newspapers and law firms. Watch enforcement, not speeches."),
    },
    'world_desk': {
        'title': "London prices the world's risk",
        'so_what': ("Most of the world's war-risk shipping cover is written in London, and the LME sets the price of the "
                    "metals in every battery and cable. When Lloyd's underwriters list a sea as a war zone, ships reroute "
                    "before any navy moves. This is Britain's quiet global reach -- and an early warning for every chokepoint."),
    },
    'home_economy': {
        'title': 'What the City means to Britain',
        'so_what': ("Financial services are roughly a tenth of the UK economy and a large share of its tax. A bond market "
                    "that stops trusting the Treasury can end a government in weeks (2022); a slow drain of companies, "
                    "money and people does the same damage over years."),
    },
}

_TAG_RE = re.compile(r'<[^>]+>')
_WORD_CACHE = {}


def _has_any(text, terms):
    """Substring match, except short terms (<=4 chars, e.g. 'uk', 'lme', 'lse',
    'nca') must sit on word boundaries -- 'uk' is inside 'ukraine', 'lse' inside 'else'."""
    for t in terms:
        if len(t) <= 4:
            rx = _WORD_CACHE.get(t)
            if rx is None:
                rx = _WORD_CACHE[t] = re.compile(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])')
            if rx.search(text):
                return True
        elif t in text:
            return True
    return False


def _fetch_lane(lane):
    url = ('https://news.google.com/rss/search?q=' + quote_plus(lane['q'] + ' when:7d')
           + '&hl=en-GB&gl=GB&ceid=GB:en')
    try:
        r = requests.get(url, timeout=12, headers={'User-Agent': UA})
        if r.status_code != 200:
            _feed_status[lane['id']] = f'HTTP {r.status_code}'
            return None
        root = ET.fromstring(r.content)
    except Exception as e:
        _feed_status[lane['id']] = f'{type(e).__name__}: {str(e)[:60]}'
        return None
    items, seen = [], set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for it in root.iter('item'):
        title = _html.unescape((it.findtext('title') or '').strip())
        src_el = it.find('source')
        outlet = (src_el.text or '').strip() if src_el is not None and src_el.text else ''
        if outlet and title.endswith(' - ' + outlet):
            title = title[: -len(' - ' + outlet)]
        desc = _TAG_RE.sub(' ', _html.unescape(it.findtext('description') or ''))
        try:
            pub = parsedate_to_datetime(it.findtext('pubDate') or '')
        except Exception:
            pub = None
        if pub and pub < cutoff:
            continue
        text = (title + ' ' + desc).lower()
        if not _has_any(text, lane['requires_any']):
            continue
        if lane.get('requires_also') and not _has_any(text, lane['requires_also']):
            continue
        if lane.get('context') and not _has_any(text, lane['context']):
            continue
        key = re.sub(r'\W+', ' ', title.lower()).strip()[:90]
        if key in seen:
            continue
        seen.add(key)
        items.append({'title': title, 'url': (it.findtext('link') or '').strip(), 'outlet': outlet or 'Google News',
                      'published': pub.isoformat() if pub else None,
                      'event': _has_any(title.lower(), lane['events'])})
    _feed_status[lane['id']] = f'ok ({len(items)} items)'
    return items


def _grade_lane(lane, items):
    base = {'id': lane['id'], 'label': lane['label'], 'lens': lane['lens']}
    if items is None:
        return dict(base, level=0, state='unread', lane='none', count=0, outlets=[], items=[],
                    sentence=f"{lane['label']}: feed did not answer this cycle -- unread, not quiet.")
    outlets = sorted({i['outlet'] for i in items})
    ev = [i for i in items if i['event']]
    ev_outlets = sorted({i['outlet'] for i in ev})
    n = len(items)
    if len(ev_outlets) >= 2:
        level, tag = 3, 'corroborated'
    elif n >= 5:
        level, tag = 2, 'volume'
    elif ev_outlets:
        level, tag = 1, 'single_source'
    elif n:
        level, tag = 1, 'routine'
    else:
        level, tag = 0, 'none'
    if tag == 'corroborated':
        s = f"{lane['label']}: a concrete development reported by {len(ev_outlets)} outlets ({', '.join(ev_outlets[:3])}) -- \"{ev[0]['title']}\"."
    elif tag == 'volume':
        s = f"{lane['label']}: busier than usual -- {n} stories from {len(outlets)} outlets this week, no single corroborated event."
    elif tag == 'single_source':
        s = f"{lane['label']}: one outlet reports a concrete development, not yet corroborated -- \"{ev[0]['title']}\" ({ev[0]['outlet']})."
    elif tag == 'routine':
        s = f"{lane['label']}: routine coverage ({n} {'story' if n == 1 else 'stories'} this week)."
    else:
        s = f"{lane['label']}: nothing in the past week."
    # corroborated events first, then newest
    items = sorted(items, key=lambda i: i.get('published') or '', reverse=True)
    items = sorted(items, key=lambda i: not i['event'])      # stable: events first, newest first within
    return dict(base, level=level, state='read', lane=tag, count=n, outlets=outlets[:8],
                event_outlets=ev_outlets, items=items[:6], sentence=s)


def _scan_lanes():
    out = {}
    for lane in LANES:
        out[lane['id']] = _grade_lane(lane, _fetch_lane(lane))
        time.sleep(1.0)
    return out


def _build_lenses(lanes):
    lenses = {}
    for lid, meta in LENSES.items():
        ls = [l for l in lanes.values() if l['lens'] == lid]
        read = [l for l in ls if l['state'] == 'read']
        lvl = max([l['level'] for l in read] or [0])
        top = sorted(read, key=lambda l: (-l['level'], -l['count']))
        if not read:
            sent = 'Not read this cycle -- every feed in this lens failed. Unread, not calm.'
        elif lvl == 0:
            sent = 'Quiet in the coverage this week.'
        else:
            sent = top[0]['sentence']
        lenses[lid] = {'id': lid, 'title': meta['title'], 'so_what': meta['so_what'], 'level': lvl,
                       'sentence': sent, 'lanes': [l['id'] for l in ls],
                       'unread_lanes': [l['id'] for l in ls if l['state'] != 'read']}
    return lenses


def _fiscal_actor(cred, lanes, tiles):
    """The fiscal-stress actor: tax, talent and the gilt market. Two honest
    readings are carried side by side -- the platform does not pick a tax policy."""
    f, t, li = lanes.get('fiscal', {}), lanes.get('tax_talent', {}), lanes.get('listings', {})
    lvl = max(cred.get('level', 0), f.get('level', 0), t.get('level', 0), li.get('level', 0))
    g = tiles.get('GILT10') or {}
    parts = []
    if g.get('value') is not None:
        parts.append(f"10-year gilt at {g['value']:.2f}%"
                     + (f" ({g['change_bp_30d']:+.0f}bp on the month)" if g.get('change_bp_30d') is not None else ''))
    for l in (f, t, li):
        if l.get('state') == 'read' and l.get('level', 0) >= 2:
            parts.append(l['sentence'])
    return {
        'name': 'Fiscal stress -- tax, talent & the gilt market', 'level': lvl,
        'reading': ' · '.join(parts) if parts else 'Nothing beyond routine fiscal coverage this week.',
        'credibility_state': cred.get('state'),
        'two_readings': [
            ("Tax-and-talent: Britain's pull on money and people is its edge. Higher taxes on wealth, non-doms and "
             "capital push the mobile rich and fast-growing companies to Milan, Dubai, Zurich or New York, and the "
             "base erodes. Watch: non-dom departures, listings leaving London, the millionaire-migration counts."),
            ("Fill-the-hole: the gap has to be closed somewhere, and the gilt market punished unfunded promises far "
             "harder than tax rises (2022). On this reading the real danger is not taxes but a budget the bond market "
             "stops believing. Watch: gilt yields against the pound -- the credibility check above."),
        ],
        'why_it_matters': ("Both readings agree on the test: if money and people keep choosing London and the gilt market "
                           "stays calm, the City's relevance holds. If both move against Britain at once, the country "
                           "loses room to act abroad -- defence, Ukraine, AUKUS all cost money."),
    }


# ════════════════════════════════════════════════════════════
# BUILD
# ════════════════════════════════════════════════════════════
def _top_indicator(tiles, cred, hvw, lenses):
    live = [t for t in tiles.values() if t.get('value') is not None]
    if not live:
        return 'UK markets unread this cycle -- the price feeds did not answer (unread, not calm).'
    if cred['state'] == 'credibility_stress':
        return 'Money is questioning the Treasury: ' + cred['text']
    hot = [l for l in lenses.values() if l['level'] >= 3]
    if hot:
        return f"{hot[0]['title']}: {hot[0]['sentence']}"
    g, p = tiles.get('GILT10') or {}, tiles.get('GBPUSD') or {}
    bits = []
    if p.get('change_pct_30d') is not None:
        bits.append(f"the pound {p['change_pct_30d']:+.1f}% on the month")
    if g.get('change_bp_30d') is not None:
        bits.append(f"10-year gilts {g['change_bp_30d']:+.0f}bp")
    if hvw.get('gap_pts') is not None:
        bits.append('domestic shares ' + {'home_lagging': 'trailing the global earners',
                                          'home_leading': 'beating the global earners',
                                          'in_step': 'in step with the global earners'}[hvw['state']])
    lead = 'Money is nervous about Britain: ' if cred['state'] == 'rates_rising' else 'Money is calm about Britain: '
    return lead + ', '.join(bits) + '.' if bits else 'UK markets partly read this cycle -- see the tiles.'


def run_uk_city_scan():
    t0 = time.time()
    tiles, agg = _scan_markets()
    cred = _credibility_check(tiles)
    hvw = _home_vs_world(tiles)
    lanes = _scan_lanes()
    lenses = _build_lenses(lanes)
    actor = _fiscal_actor(cred, lanes, tiles)
    g = tiles.get('GILT10') or {}
    bp30 = g.get('change_bp_30d')
    result = {
        'success': True, 'country': 'uk', 'version': VERSION,
        'financial_pulse': {
            'country': 'GB', 'card_label': 'United Kingdom Financial Pulse',
            'tiles': tiles, 'tile_order': ['GBPUSD', 'GILT10', 'FTSE100', 'FTSE250', 'LLOYDS', 'COPPER'],
            'market_status': agg, 'updated_at': datetime.now(timezone.utc).isoformat(),
            'disclaimer': 'Open-source market prices; convergence-framed, not prediction, not investment advice.',
        },
        'top_indicator': _top_indicator(tiles, cred, hvw, lenses),
        'credibility_check': cred,
        'home_vs_world': hvw,
        'lenses': lenses,
        'lanes': lanes,
        'fiscal_actor': actor,
        # Compact read for the ME market detector's analog lens (uk_gilt_2022).
        'gilt_read': {'gilt_10y': g.get('value'), 'gilt_bp_30d': bp30,
                      'gilt_jump': (bp30 >= 40) if bp30 is not None else None,
                      'source': g.get('source'), 'as_of': datetime.now(timezone.utc).date().isoformat()},
        'tiles_live': sum(1 for t in tiles.values() if t.get('value') is not None),
        'lanes_read': sum(1 for l in lanes.values() if l['state'] == 'read'),
        'scan_seconds': round(time.time() - t0, 1),
        'scanned_at': datetime.now(timezone.utc).isoformat(),
    }
    _redis_set(CACHE_KEY, result)
    print(f"{LOG} Scan complete -- {result['tiles_live']}/6 tiles, {result['lanes_read']}/{len(LANES)} lanes, "
          f"credibility={cred['state']} ({result['scan_seconds']}s)")
    return result


def _background_loop():
    time.sleep(150)
    while True:
        try:
            run_uk_city_scan()
        except Exception as e:
            print(f'{LOG} Background refresh error: {str(e)[:120]}')
        time.sleep(SCAN_INTERVAL_HOURS * 3600)


def start_uk_city_refresh():
    threading.Thread(target=_background_loop, daemon=True, name='UKCityPulse').start()
    print(f'{LOG} Background refresh thread started ({SCAN_INTERVAL_HOURS}h)')


def register_uk_city_endpoints(app, start_background=True):

    @app.route('/api/europe/uk/city-pulse', methods=['GET'])
    def uk_city_pulse():
        global _scan_running
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
        with _scan_lock:
            if _scan_running:
                cached = _redis_get(CACHE_KEY)
                if cached:
                    cached.update({'from_cache': True, 'scan_in_progress': True})
                    return jsonify(cached)
                return jsonify({'success': False, 'error': 'Scan in progress'}), 202
            _scan_running = True
        try:
            return jsonify(run_uk_city_scan())
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500
        finally:
            with _scan_lock:
                _scan_running = False

    @app.route('/api/europe/uk/city-pulse/debug', methods=['GET'])
    def uk_city_pulse_debug():
        cached = _redis_get(CACHE_KEY) or {}
        tiles = ((cached.get('financial_pulse') or {}).get('tiles') or {})
        return jsonify({
            'version': VERSION, 'market_fetch_loaded': MARKET_FETCH,
            'market_fetch': _mf.diagnostics() if MARKET_FETCH else None,
            'feed_status_this_process': dict(_feed_status),
            'cached_scanned_at': cached.get('scanned_at'),
            'tiles': {k: {'source': v.get('source'), 'ticker': v.get('ticker'), 'value': v.get('value'),
                          'substitute': v.get('is_substitute')} for k, v in tiles.items()},
            'lanes': {k: {'state': v.get('state'), 'level': v.get('level'), 'count': v.get('count')}
                      for k, v in (cached.get('lanes') or {}).items()},
        })

    if start_background:
        start_uk_city_refresh()
    print('[UK City Pulse] Endpoints registered: /api/europe/uk/city-pulse (+ /debug)')
