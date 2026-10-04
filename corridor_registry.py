"""
corridor_registry.py  --  Asifah Analytics  (Europe backend)
================================================================
ROUTE INTEGRITY AS A STATE.

WHY THIS EXISTS
  The platform wrote "Watch: Black Sea grain corridor status" at least THREE
  times across five months -- in convergence_registry.wheat_lebanon (May 3),
  in commodity_tracker's russia.fertilizer note, and in its poland.wheat note
  (Jul) -- and never built the sensor. Europe's app.py carries 'grain corridor'
  and 'port closure' as rhetoric KEYWORDS. The vocabulary was everywhere; the
  state was nowhere.

  Without it the platform reads "Ukrainian production stable" and reports calm
  while the grain cannot move. It measures the silo and calls it the supply.

THE EDGE/NODE PROBLEM (why this is its own module)
  convergence_detector.py joins four axes PER COUNTRY. Every axis answers
  "what is happening IN country X."

  A corridor is an EDGE, not a node. Black Sea closure does not happen IN
  Ukraine, Russia or Turkey -- it is the link between them and Lebanon, Egypt,
  Gaza, Syria. Filed under Ukraine it is mislabelled; filed under Lebanon it is
  unsourced.

      corridor state (EDGE)
        x  country corridor-dependence (MAPPING, phase 2, ME backend)
        =  per-country logistics reading (NODE)

  Lebanon gets a Black Sea reading not because Lebanon is in the Black Sea, but
  because Lebanon's wheat arrives through it.

WHY THE EUROPE BACKEND
  The corridor is physically in Europe's theatre (Odesa, Pivdennyi,
  Novorossiysk, Constanta, Gdansk/Gdynia); Europe owns the Russia and Ukraine
  trackers; ME is already 88 files on two Render instances. ONE writer, many
  readers -- the platform's existing cross-theater fingerprint pattern. Three
  parallel implementations in three backends is how five version strings and
  two Israeli feed sets happened.

BASELINE vs LIVE  -- the central honesty rule of this module
  A STRUCTURAL instrument (the Lloyd's JWC listed-area circulars) tells you the
  insurance market's standing assessment. It is revised about three times a
  year: JWLA-030 Apr 2022, 031 Apr 2023, 033 Mar 2026, 034 Jul 2026, 035 Sep
  2026. It tells you the risk TIER. It does NOT tell you whether grain moved
  this week, and this module must never let it pretend otherwise.

  So a corridor carries TWO readings:
      baseline_tier  -- from structural instruments (slow, sourced, dated)
      live_state     -- from leading instruments (fast); 'unknown' until one
                        is wired

  A corridor we cannot read and a corridor that is open MUST NOT produce the
  same output. 'unknown' is a state, never a silence.

LAUNCH POSTURE (v1.0.0)
  No leading instrument is confirmed wired. The Black Sea FOB index that would
  be ideal (Investing.com WHFOB) prohibits automated access in its terms; the
  candidate replacement (Euronext MATIF milling wheat, spread against CBOT) is
  not yet confirmed reachable through the platform's existing fetch path.

  Therefore every corridor launches with live_state='unknown' and a real,
  dated, sourced baseline_tier. This is the Lane D pattern from the Palestinian
  financial access work: evidence-only at launch BY DECISION, not by oversight.
  Reporting 'open' because we cannot see is the one failure mode this platform
  exists to prevent.

SCOPE
  Corridors only. Kerem Shalom is a TERMINAL (crossing status, throughput,
  covered_storage) and belongs to LOGISTICS_NODES in a later phase -- its id is
  reserved here so the two tables cannot collide.

ID VOCABULARY
  Adopted from commodity_tracker.py's 'cascade_upstream_chokepoints', which
  already uses structured snake_case ids ('strait_of_hormuz', used 4x). The
  free-text 'chokepoints' lists in that file stay as display strings.

WRITES   corridor:<id>:latest        (Upstash, TTL 24h)
         corridor:index:latest       (all corridors, one blob, for cheap reads)
READS    nothing. This module is a WRITER.

SCOPING NOTE  claude/CORRIDOR_SENSOR_SCOPING.md
COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import json
import requests
from datetime import datetime, timezone

__version__ = '1.1.0'

CORRIDOR_REGISTRY_VERSION = __version__
CORRIDOR_USER_AGENT = (f'AsifahAnalytics-EU-Corridor/{CORRIDOR_REGISTRY_VERSION} '
                       f'(OSINT monitoring tool; +https://asifahanalytics.com)')

UPSTASH_REDIS_URL   = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')

CORRIDOR_KEY_PREFIX = 'corridor:'
CORRIDOR_INDEX_KEY  = 'corridor:index:latest'
CORRIDOR_TTL_SEC    = 24 * 3600


# ======================================================================
# THE STATE LADDER
# ======================================================================
# DELIBERATELY NOT L0-L5. That ladder describes what an ACTOR is doing, and a
# corridor has no actor -- nobody is "signalling" or "escalating" a waterway.
# Borrowing it would have made 'L3 standoff hardening' a sentence about a
# shipping lane, which is the kind of false precision the theatre_state module
# was written to stop.
CORRIDOR_STATES = {
    'open':      'normal traffic, no reported impairment',
    'strained':  'cost or risk rising; one route of several impaired',
    'impaired':  'a named route unusable; traffic rerouting at cost',
    'blocked':   'no commercial transit',
    'unknown':   'not currently sensed -- this is missing data, not calm',
}

# Ordering for "take the worst reading". 'unknown' sits OUTSIDE this ordering
# on purpose: it is not a severity, it is an absence, and max() over severities
# must never silently swallow it.
STATE_SEVERITY = {'open': 0, 'strained': 1, 'impaired': 2, 'blocked': 3}

# How much an instrument is allowed to claim.
#   structural   -- slow standing assessment. Sets baseline_tier. NEVER sets
#                   live_state: a war-risk listing from September cannot tell
#                   you whether a ship sailed this morning.
#   leading      -- moves before throughput does. May set live_state.
#   corroborating-- confirms a reading. May RAISE an existing live_state but
#                   may never create one from nothing: a keyword match is not
#                   a measurement.
CONFIDENCE_CLASSES = ('structural', 'leading', 'corroborating')


# ======================================================================
# THE CORRIDORS
# ======================================================================
# Facts here are STRUCTURAL and slow-moving. Anything that changes week to week
# belongs in an instrument, not in this table.
#
# 'jwc_baseline' is hand-entered from the Lloyd's Joint War Committee circular
# named in 'source'. It is dated because it WILL go stale -- the circulars are
# irregular and there is no feed to poll (the public LMA index lists only the
# 2005/2020/2022 circulars; current ones sit at unpredictable upload paths
# behind no RSS, with the archive behind member login). Trade press reports new
# circulars within days; that is the realistic refresh path, by hand.
CORRIDORS = {
    'black_sea_grain_corridor': {
        'name':        'Black Sea grain corridor',
        'icon':        '\U0001f6a2',          # ship
        'kind':        'maritime',
        'commodities': ['wheat', 'corn', 'sunflower_oil', 'barley', 'fertilizer'],
        'origin':      ['ukraine', 'russia'],
        'ports':       ['odesa', 'pivdennyi', 'chornomorsk', 'mykolaiv',
                        'novorossiysk'],
        'exits_via':   ['bosphorus'],
        'description': (
            'The primary export route for Ukrainian and Russian grain. Mined '
            'water, drone and USV attacks on port infrastructure, and war-risk '
            'underwriting are the binding constraints -- not production. The '
            'grain exists and is in silos; this is the stage at which it stops.'
        ),
        'jwc_baseline': {
            'tier':      'listed',
            'as_of':     '2026-09-16',
            'circular':  'JWLA-035',
            'wording':   ('Black Sea excluding territorial waters of adjoining '
                          'countries other than Russia and Ukraine'),
            'source':    'https://lmalloyds.com/wp-content/uploads/2026/09/'
                         'JWLA-035-Black-Sea.pdf',
            'note':      ('The WHOLE sea is a listed area as of this circular. '
                          'Verified Oct 4 2026. Re-check on the next JWLA.'),
        },
        'watch': ['war-risk hull rates', 'port strike reporting',
                  'insurer withdrawal of cover', 'convoy programmes',
                  'Odesa / Pivdennyi throughput'],
    },
    'bosphorus': {
        'name':        'Turkish Straits (Bosphorus / Dardanelles)',
        'icon':        '\U0001f309',          # bridge
        'kind':        'maritime',
        'commodities': ['wheat', 'corn', 'oil', 'natural_gas', 'fertilizer'],
        'origin':      ['ukraine', 'russia'],
        'ports':       [],
        'exits_via':   [],
        'description': (
            'Every tonne leaving the Black Sea passes here. Governed by the '
            'Montreux Convention, which makes Turkish transit policy a '
            'structural variable rather than a commercial one. A Bosphorus '
            'event is upstream of every Black Sea corridor reading.'
        ),
        'jwc_baseline': None,          # not separately listed; see black_sea
        'watch': ['Montreux interpretation disputes', 'transit suspensions',
                  'tanker queue length', 'Turkish straits closures'],
    },
    'danube_river': {
        'name':        'Danube river route',
        'icon':        '\U0001f6a4',          # speedboat
        'kind':        'river',
        'commodities': ['wheat', 'corn', 'sunflower_oil'],
        'origin':      ['ukraine'],
        'ports':       ['izmail', 'reni'],
        'exits_via':   ['constanta'],
        'description': (
            'The substitution route when the sea route is impaired -- barge to '
            'Izmail/Reni, then Constanta. Lower capacity and higher cost, so a '
            'rising Danube share is itself evidence the sea route is degraded. '
            'USDA: Danube share fell 13%% (2024) to 4%% (2025) as maritime '
            'recovered 91%% to 95%% -- substitution is observable in the shares.'
        ),
        'jwc_baseline': None,
        'watch': ['Izmail / Reni strike reporting', 'Constanta congestion',
                  'barge availability', 'Danube water levels'],
    },
    'poland_overland': {
        'name':        'Poland overland corridor',
        'icon':        '\U0001f682',          # locomotive
        'kind':        'overland',
        'commodities': ['wheat', 'corn'],
        'origin':      ['ukraine'],
        'ports':       ['gdansk', 'gdynia'],
        'exits_via':   [],
        'description': (
            'Rail transshipment to the Baltic. FLOW, NOT STOCK. Already '
            'modelled in commodity_tracker as poland.wheat role=transit with '
            'the note: a Polish border closure is a food-corridor event with '
            'Ukraine-solidarity and EU-cohesion spillovers. The binding '
            'constraint here is POLITICAL (farmer blockades, import bans), not '
            'kinetic -- the only corridor on this list where that is true.'
        ),
        'jwc_baseline': None,
        'watch': ['Dorohusk / Medyka crossing status', 'Polish farmer-union actions',
                  'EU import-quota decisions', 'Baltic port grain volumes'],
    },
}

# RESERVED -- terminals, not corridors. Declared so the two tables cannot
# collide when LOGISTICS_NODES lands. A terminal has covered storage, opening
# hours and a throughput ceiling; a corridor has none of those.
RESERVED_TERMINAL_IDS = ('kerem_shalom',)

# Already defined elsewhere. Do NOT redefine here -- commodity_tracker uses
# this id in cascade_upstream_chokepoints.
EXTERNALLY_OWNED_IDS = ('strait_of_hormuz',)


# ======================================================================
# REDIS (write side)
# ======================================================================
def _redis_set(key, value, ttl=CORRIDOR_TTL_SEC):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(
            f"{UPSTASH_REDIS_URL}/set/{key}",
            headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}',
                     'Content-Type': 'application/json',
                     'User-Agent': CORRIDOR_USER_AGENT},
            params={'EX': ttl} if ttl else {},
            data=json.dumps(value),
            timeout=8,
        )
        return r.ok
    except Exception as e:
        print(f"[Corridor] Redis SET error ({key}): {str(e)[:90]}")
        return False


# ======================================================================
# INSTRUMENT ADAPTERS
# ======================================================================
# Contract: an adapter takes a corridor dict and returns either None (nothing
# to say -- which is a legitimate and common answer) or:
#
#   {
#     'instrument':  'jwc_listed_area',
#     'confidence':  'structural' | 'leading' | 'corroborating',
#     'state_hint':  one of CORRIDOR_STATES (omit for structural-only),
#     'tier':        free-text tier label (structural instruments),
#     'evidence':    one human sentence,
#     'as_of':       ISO date of the underlying fact,
#     'source':      url or named source,
#   }
#
# Adapters MUST NOT raise. A broken instrument degrades the reading to
# 'unknown'; it never takes the module down and never invents a state.

# ======================================================================
# ROUTE EVENTS -- the leading instrument  (v1.1.0, Oct 4 2026)
# ======================================================================
# WHY THIS IS 'LEADING' AND KEYWORDS ARE NOT
#   v1.0.0 said news can only ever be CORROBORATING because "a keyword match
#   is not a measurement." That is right for CHATTER -- 'grain corridor' in an
#   op-ed tells you nothing about the water. It is wrong for a NAMED EVENT ON
#   THE ROUTE. "Odesa grain terminal struck overnight" is not sentiment about
#   shipping; it is a report that the thing we are trying to measure has
#   changed. An event on the route IS a measurement of the route.
#
#   So the split is not news-vs-market. It is NAMED EVENT vs AMBIENT TALK, and
#   this adapter is built to separate them and to fail toward silence.
#
# WHAT THIS INSTRUMENT IS, HONESTLY
#   Lagging-to-coincident, NOT leading-in-time. It reports that the corridor
#   closed, not that it is closing. The price instrument that would have moved
#   first (Black Sea FOB) is unavailable: Investing.com's WHFOB forbids
#   automated access, and Yahoo's EBM=F is NOT Euronext milling wheat (it
#   returned 75005 EUR against a real MATIF price of EUR 241.50/t on Oct 2
#   2026 -- a ~310x discrepancy; see the scoping note). Labelled for what it
#   is rather than sold as what we wanted.
#
# FOUR GUARDS, because an event sensor built on news fails in four ways:
#   1. ANCHOR      -- the article must name THIS corridor's ports or waters.
#                     'port closure' anywhere on earth must not move the Black
#                     Sea. This is the single most important guard.
#   2. COMMENTARY  -- think-tank and op-ed writing ABOUT corridor risk is
#                     counted and never promoted. Cloned from the Palestinian
#                     financial-access lane, where the same trap was live.
#   3. CORROBORATION -- impaired/blocked need >= MIN_SOURCES distinct outlets.
#                     One wire story is a claim; three are a condition.
#   4. RECENCY     -- handled by the gateway timespan. A 2023 strike must
#                     never set today's state.
try:
    from gdelt_gateway import gdelt_fetch as _gw_gdelt
    _GDELT_GATEWAY = True
except ImportError:
    _gw_gdelt = None
    _GDELT_GATEWAY = False

# Event classes, most severe first. Matching stops at the first class that
# clears every guard, so 'blocked' language outranks 'strained' language in
# the same article.
ROUTE_EVENT_CLASSES = (
    ('blocked', (
        'exports halted', 'exports suspended', 'port closed', 'ports closed',
        'shipping suspended', 'sailings suspended', 'corridor suspended',
        'corridor closed', 'traffic halted', 'no vessels', 'grain deal collapsed',
        'blockade',
    )),
    ('impaired', (
        'port struck', 'terminal struck', 'port hit', 'terminal damaged',
        'grain terminal', 'struck the port', 'attack on the port',
        'drone attack on', 'missile struck', 'vessel struck', 'ship struck',
        'hit by a drone', 'sea mine', 'struck a mine', 'cover withdrawn',
        'withdrew cover', 'insurers withdraw', 'underwriters decline',
        'declared unsafe', 'crossing blockaded', 'border crossing closed',
    )),
    ('strained', (
        'war risk premium', 'war-risk premium', 'premiums rise',
        'premiums rising', 'insurance costs rise', 'rerouting', 're-routing',
        'convoy', 'queue of vessels', 'vessels waiting', 'congestion',
        'shipping costs surge',
    )),
)

# Recovery language. Present without any impairment class, this is evidence of
# 'open' -- the one way this module may ever assert open, and it still needs
# the anchor and the corroboration count.
ROUTE_RECOVERY_TERMS = (
    'exports resumed', 'shipping resumed', 'port reopened', 'reopened the port',
    'sailings resumed', 'corridor reopened', 'cover restored', 'traffic normalised',
    'traffic normalized',
)

# Guard 2. Writing ABOUT the risk, not reporting an event.
ROUTE_COMMENTARY_MARKERS = (
    'analysis:', 'opinion:', 'commentary:', 'explainer', 'what to know',
    'could disrupt', 'may disrupt', 'risks to', 'threatens to', 'warns that',
    'fears of', 'experts say', 'analysts say', 'scenario', 'outlook',
    'five things', 'what happens if', 'why the', 'how the',
)

MIN_SOURCES_FOR_IMPAIRMENT = 2
ROUTE_EVENT_TIMESPAN = '7d'
ROUTE_EVENT_MAXRECORDS = 60


def _route_anchor_terms(corridor):
    """Guard 1. Terms that tie an article to THIS corridor specifically."""
    terms = set()
    for p in corridor.get('ports', []) or []:
        terms.add(p.replace('_', ' ').lower())
    for e in corridor.get('exits_via', []) or []:
        terms.add(e.replace('_', ' ').lower())
    name = (corridor.get('name') or '').lower()
    if name:
        terms.add(name)
    # the distinctive half of the name, so 'Black Sea grain corridor' also
    # anchors on 'black sea' -- but never on a word as generic as 'corridor'
    for frag in ('black sea', 'bosphorus', 'dardanelles', 'turkish straits',
                 'danube', 'dorohusk', 'medyka'):
        if frag in name or frag.split()[0] in name:
            terms.add(frag)
    return tuple(t for t in terms if len(t) >= 4)


def _route_is_commentary(text):
    """Guard 2."""
    return any(m in text for m in ROUTE_COMMENTARY_MARKERS)


def _route_query(corridor):
    """GDELT query. Narrow on purpose -- this is an event sensor, not a sweep."""
    anchors = [a for a in _route_anchor_terms(corridor)][:4]
    if not anchors:
        return None
    ors = ' OR '.join(f'"{a}"' for a in anchors)
    return f'({ors}) AND (port OR grain OR shipping OR vessel OR corridor)'


def _adapter_route_events(corridor):
    """LEADING (coincident). Named events on THIS route.

    Returns None -- not a state -- whenever the gateway is absent, the query
    cannot be built, nothing matches, or corroboration falls short. Every one
    of those is a legitimate 'we cannot say', and the composer turns that into
    'unknown' rather than 'open'.
    """
    if not (_GDELT_GATEWAY and _gw_gdelt):
        return None
    query = _route_query(corridor)
    if not query:
        return None

    try:
        raw = _gw_gdelt(query, language='eng', timespan=ROUTE_EVENT_TIMESPAN,
                        maxrecords=ROUTE_EVENT_MAXRECORDS,
                        label=f"corridor/{corridor.get('name', '?')[:20]}") or []
    except Exception as e:
        print(f"[Corridor] GDELT error: {str(e)[:90]}")
        return None

    anchors = _route_anchor_terms(corridor)
    hits = {}              # state -> {source: headline}
    recovery = {}
    commentary_count = 0

    for art in raw:
        title = (art.get('title') or '').lower()
        if not title:
            continue
        if not any(a in title for a in anchors):       # GUARD 1
            continue
        if _route_is_commentary(title):                # GUARD 2
            commentary_count += 1
            continue
        src = (art.get('source') or 'unknown')
        for state, terms in ROUTE_EVENT_CLASSES:
            if any(t in title for t in terms):
                hits.setdefault(state, {}).setdefault(src, art.get('title'))
                break
        else:
            if any(t in title for t in ROUTE_RECOVERY_TERMS):
                recovery.setdefault(src, art.get('title'))

    # GUARD 3 -- severity order, first class with enough distinct sources wins.
    # A STRONGER class that failed corroboration is not discarded: it is
    # carried as 'under_corroborated' so the analyst sees that one outlet is
    # reporting closure while two report strain. Dropping it silently would
    # hide the most important sentence in the corpus.
    under = []
    for state, _ in ROUTE_EVENT_CLASSES:
        sources = hits.get(state, {})
        needed = MIN_SOURCES_FOR_IMPAIRMENT if state in ('impaired', 'blocked') else 1
        if 0 < len(sources) < needed:
            under.append({'state': state, 'source_count': len(sources),
                          'headlines': list(sources.values())[:2]})
            continue
        if len(sources) >= needed:
            heads = list(sources.values())[:3]
            ev = (f'{len(sources)} distinct source(s) reporting '
                  f'{state}-class route events in the last '
                  f'{ROUTE_EVENT_TIMESPAN}: ' + ' | '.join(heads))
            if under:
                u = under[0]
                ev += (f" -- NOTE: {u['source_count']} source(s) report the "
                       f"stronger '{u['state']}' class but fall short of the "
                       f"{MIN_SOURCES_FOR_IMPAIRMENT}-source bar: "
                       + ' | '.join(u['headlines']))
            return {
                'instrument': 'route_events',
                'confidence': 'leading',
                'state_hint': state,
                'evidence':   ev,
                'source_count':     len(sources),
                'under_corroborated': under,
                'commentary_filtered': commentary_count,
                'as_of':      datetime.now(timezone.utc).date().isoformat(),
                'source':     'GDELT via shared gateway',
            }

    if len(recovery) >= MIN_SOURCES_FOR_IMPAIRMENT:
        return {
            'instrument': 'route_events',
            'confidence': 'leading',
            'state_hint': 'open',
            'evidence':   (f'{len(recovery)} distinct source(s) reporting route '
                           f'reopening/resumption and no impairment-class event '
                           f'in the last {ROUTE_EVENT_TIMESPAN}: '
                           + ' | '.join(list(recovery.values())[:3])),
            'source_count':     len(recovery),
            'commentary_filtered': commentary_count,
            'as_of':      datetime.now(timezone.utc).date().isoformat(),
            'source':     'GDELT via shared gateway',
        }

    # Matched nothing that cleared the guards. NOT 'open' -- silence.
    return None


def _adapter_jwc_baseline(corridor):
    """STRUCTURAL. The Lloyd's JWC listed-area standing assessment.

    Sets baseline_tier only. Deliberately returns NO state_hint: a war-risk
    listing dated September cannot tell you whether a ship sailed this morning,
    and the first draft of the scoping note was wrong to imply it could.
    """
    base = corridor.get('jwc_baseline')
    if not base:
        return None
    return {
        'instrument': 'jwc_listed_area',
        'confidence': 'structural',
        'tier':       base.get('tier'),
        'evidence':   (f"Lloyd's Joint War Committee {base.get('circular')} "
                       f"({base.get('as_of')}): \"{base.get('wording')}\""),
        'as_of':      base.get('as_of'),
        'source':     base.get('source'),
    }


def _adapter_origin_spread(corridor):
    """LEADING. Black Sea-origin wheat decoupling from the world benchmark.

    NOT WIRED (v1.0.0). Returns None, honestly, rather than a fabricated read.

    The intended measurement is a SPREAD, not a level: flat wheat price is a
    global story that moves on Kansas drought. The corridor signal is
    origin-specific price separating from the benchmark.

    Investing.com's WHFOB (Wheat Index FOB Black Sea) is exactly the right
    series and its terms prohibit automated access -- ruled out, not deferred.
    The candidate replacement is Euronext MATIF milling wheat spread against
    CBOT (ZW=F, which commodity_tracker already fetches), pending confirmation
    that MATIF resolves through the existing Yahoo path. Candidate tickers:
    EBM=F, ML=F; comparators KE=F, MW=F.

    When wired, this adapter returns a leading state_hint and nothing else in
    this module changes -- which is the entire point of the adapter contract.
    """
    return None


def _adapter_throughput(corridor):
    """LEADING. Port throughput against its own trailing baseline.

    NOT WIRED (v1.0.0). The USDA AMS Ukraine Grain Transportation report
    carries corridor MODAL SHARES and is machine-readable -- but it is ANNUAL
    (the filename's month is the publication month, not the coverage period),
    so it calibrates the dependence map in phase 2 and cannot serve as a live
    throughput sensor.
    """
    return None


# Order matters only for readability; composition is explicit below.
ADAPTERS = (
    _adapter_jwc_baseline,
    _adapter_route_events,
    _adapter_origin_spread,
    _adapter_throughput,
)


# ======================================================================
# GLOBAL FREIGHT CONTEXT  (v1.1.0)
# ======================================================================
# BDRY is deliberately NOT an adapter, and that is the whole point.
#
# It is a dry-bulk freight ETF: a real, verified, free daily price (NYSE Arca,
# USD 14.20 on Oct 4 2026). It is also GLOBAL. It moves on Chinese iron ore
# demand, Panama Canal draft, scrapping cycles and a dozen things that have
# nothing to do with Odesa. Wiring it as an adapter would let a worldwide
# freight move set a Black Sea corridor state -- which is the shared_global
# trap from the scoping note running backwards: a diffuse signal masquerading
# as a specific one.
#
# So it rides on the PAYLOAD as context, never on a corridor's state. An
# analyst reading "Black Sea impaired, and global dry bulk is also elevated"
# learns something real. A machine scoring the second as evidence of the first
# does not.
FREIGHT_CONTEXT_TICKER = 'BDRY'
_YF_CHART = 'https://query1.finance.yahoo.com/v8/finance/chart/'


def freight_context():
    """Global dry-bulk freight. Context only -- never moves a corridor state."""
    out = {
        'ticker':      FREIGHT_CONTEXT_TICKER,
        'name':        'Breakwave Dry Bulk Shipping ETF',
        'scope':       'GLOBAL -- not corridor-specific',
        'affects_corridor_state': False,
        'why_not': ('Global dry-bulk rates move on Chinese demand, canal draft '
                    'and scrapping cycles. Treating that as evidence about a '
                    'named corridor would be a diffuse signal masquerading as '
                    'a specific one.'),
        'available':   False,
    }
    try:
        r = requests.get(
            f'{_YF_CHART}{FREIGHT_CONTEXT_TICKER}?range=1mo&interval=1d',
            headers={'User-Agent': CORRIDOR_USER_AGENT}, timeout=10)
        if not r.ok:
            out['note'] = f'HTTP {r.status_code}'
            return out
        res = (r.json().get('chart') or {}).get('result') or []
        if not res:
            out['note'] = 'no result'
            return out
        closes = [c for c in
                  (res[0].get('indicators', {}).get('quote', [{}])[0].get('close') or [])
                  if c is not None]
        if not closes:
            out['note'] = 'no closes'
            return out
        last, first = closes[-1], closes[0]
        out.update({
            'available':  True,
            'last':       round(last, 2),
            'currency':   res[0].get('meta', {}).get('currency'),
            'change_1mo_pct': round(((last - first) / first) * 100, 1) if first else None,
            'as_of':      datetime.now(timezone.utc).date().isoformat(),
        })
    except Exception as e:
        out['note'] = f'{type(e).__name__}: {str(e)[:60]}'
    return out


# ======================================================================
# COMPOSITION
# ======================================================================
def _worst(states):
    """Most severe of a list of states, ignoring 'unknown'. None if empty."""
    real = [s for s in states if s in STATE_SEVERITY]
    if not real:
        return None
    return max(real, key=lambda s: STATE_SEVERITY[s])


def read_corridor(corridor_id):
    """Compose one corridor's reading from every adapter. Never raises."""
    corridor = CORRIDORS.get(corridor_id)
    if not corridor:
        return None

    readings, errors = [], []
    for adapter in ADAPTERS:
        try:
            out = adapter(corridor)
        except Exception as e:                       # an instrument may fail;
            errors.append(f'{adapter.__name__}: {type(e).__name__}')
            continue                                 # the corridor may not
        if out:
            readings.append(out)

    structural = [r for r in readings if r.get('confidence') == 'structural']
    leading    = [r for r in readings if r.get('confidence') == 'leading']
    corrob     = [r for r in readings if r.get('confidence') == 'corroborating']

    # LIVE STATE -- only a leading instrument may create one.
    live_state = _worst([r.get('state_hint') for r in leading])

    # Corroborating instruments may RAISE an existing reading, never create
    # one. A keyword match is not a measurement; if the only thing we have is
    # chatter, the honest answer is still 'unknown'.
    if live_state is not None and corrob:
        raised = _worst([live_state] + [r.get('state_hint') for r in corrob])
        if raised:
            live_state = raised

    sensed = live_state is not None
    if not sensed:
        live_state = 'unknown'

    baseline_tier = structural[0].get('tier') if structural else None

    return {
        'corridor_id':    corridor_id,
        'name':           corridor['name'],
        'icon':           corridor.get('icon', ''),
        'kind':           corridor.get('kind'),
        'commodities':    corridor.get('commodities', []),
        'origin':         corridor.get('origin', []),
        'ports':          corridor.get('ports', []),
        'exits_via':      corridor.get('exits_via', []),
        'description':    corridor.get('description', ''),

        'live_state':     live_state,
        'live_state_meaning': CORRIDOR_STATES[live_state],
        'sensed':         sensed,
        'baseline_tier':  baseline_tier,

        'readings':       readings,
        'instrument_errors': errors,
        'watch':          corridor.get('watch', []),
        'read':           _prose(corridor, live_state, sensed,
                                 baseline_tier, structural),
        'version':        CORRIDOR_REGISTRY_VERSION,
        'generated_at':   datetime.now(timezone.utc).isoformat(),
    }


def _prose(corridor, live_state, sensed, baseline_tier, structural):
    """One estimative sentence. No probabilities, no dates, no 'will'."""
    name = corridor['name']
    if not sensed:
        base = (f"{name}: route state NOT SENSED this cycle. No leading "
                f"instrument is wired, so this is missing data and not a "
                f"finding of calm.")
        if structural:
            s = structural[0]
            base += (f" Standing structural assessment: {s.get('evidence')} "
                     f"That is a risk tier, not a reading of current traffic.")
        else:
            base += " No structural baseline on file for this corridor either."
        return base

    phrase = CORRIDOR_STATES[live_state]
    out = f"{name} -- {live_state}: {phrase}."
    if baseline_tier:
        out += f" Structural baseline: {baseline_tier}."
    return out


def read_all_corridors():
    """Every corridor plus an honest summary."""
    records = [read_corridor(cid) for cid in sorted(CORRIDORS)]
    records = [r for r in records if r]

    sensed = [r for r in records if r['sensed']]
    worst = _worst([r['live_state'] for r in sensed])

    if not sensed:
        summary = (f"{len(records)} corridors registered, NONE sensed. "
                   f"No leading instrument is wired yet (v{__version__}); "
                   f"structural baselines are attached where they exist. "
                   f"Absence here is missing data, not calm.")
    else:
        summary = (f"{len(sensed)} of {len(records)} corridors sensed; "
                   f"most impaired: {worst}.")

    return {
        'version':      CORRIDOR_REGISTRY_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'corridor_count': len(records),
        'sensed_count':   len(sensed),
        'any_sensed':     bool(sensed),
        'worst_state':    worst or 'unknown',
        'summary':        summary,
        'states_legend':  CORRIDOR_STATES,
        'freight_context': freight_context(),
        'corridors':      records,
        'reserved_terminal_ids':  list(RESERVED_TERMINAL_IDS),
        'externally_owned_ids':   list(EXTERNALLY_OWNED_IDS),
        'disclaimer': (
            'CORRIDOR STATE is a route-integrity indicator, NOT a forecast of '
            'supply disruption. It reports whether a route is passable and at '
            'what cost. It does not predict whether or when shortage, price '
            'movement or political consequence will follow. A corridor in '
            "'unknown' state is one we cannot currently read."
        ),
    }


def publish_corridors():
    """Write every corridor to Redis plus one index blob. Returns a report."""
    payload = read_all_corridors()
    written, failed = [], []
    for rec in payload['corridors']:
        key = f"{CORRIDOR_KEY_PREFIX}{rec['corridor_id']}:latest"
        (written if _redis_set(key, rec) else failed).append(rec['corridor_id'])
    index_ok = _redis_set(CORRIDOR_INDEX_KEY, payload)
    print(f"[Corridor] published {len(written)}/{len(payload['corridors'])} "
          f"corridors (index={'ok' if index_ok else 'FAILED'})")
    return {'written': written, 'failed': failed, 'index_written': index_ok,
            'summary': payload['summary']}


# ======================================================================
# FLASK (canonical Asifah pattern)
# ======================================================================
def register_corridor_endpoints(app):
    """Register corridor endpoints on the Europe Flask app."""
    from flask import jsonify, request

    @app.route('/api/corridors', methods=['GET', 'OPTIONS'])
    def corridors_all():
        if request.method == 'OPTIONS':
            return ('', 204)
        try:
            return jsonify(read_all_corridors()), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)[:200]}), 500

    @app.route('/api/corridors/<corridor_id>', methods=['GET', 'OPTIONS'])
    def corridor_one(corridor_id):
        if request.method == 'OPTIONS':
            return ('', 204)
        rec = read_corridor((corridor_id or '').strip().lower())
        if not rec:
            return jsonify({'success': False,
                            'error': f"unknown corridor '{corridor_id}'",
                            'known': sorted(CORRIDORS)}), 404
        return jsonify(rec), 200

    @app.route('/api/corridors/health', methods=['GET'])
    def corridors_health():
        payload = read_all_corridors()
        # Which adapters actually returned anything -- derived from the
        # composed records, NOT by calling adapters again here. An earlier
        # draft re-invoked them inline, which put an un-guarded adapter call
        # in the one endpoint whose job is to work when things are broken.
        wired = sorted({r.get('instrument')
                        for rec in payload['corridors']
                        for r in rec.get('readings', [])
                        if r.get('instrument')})
        return jsonify({
            'ok':              True,
            'version':         CORRIDOR_REGISTRY_VERSION,
            'corridor_count':  payload['corridor_count'],
            'sensed_count':    payload['sensed_count'],
            'any_sensed':      payload['any_sensed'],
            'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
            'adapters':        [a.__name__ for a in ADAPTERS],
            'adapters_reporting': wired,
            'instrument_errors': {rec['corridor_id']: rec['instrument_errors']
                                  for rec in payload['corridors']
                                  if rec.get('instrument_errors')},
            'note': ('sensed_count 0 is EXPECTED at v1.0.0 -- no leading '
                     'instrument is wired yet. See '
                     'claude/CORRIDOR_SENSOR_SCOPING.md section 4.'),
        }), 200

    print('[Corridor] endpoints registered (/api/corridors)')


# ======================================================================
# SELF-TEST
# ======================================================================
if __name__ == '__main__':
    print(f'Corridor Registry v{__version__} -- self-test\n')

    print('TEST 1 -- every corridor composes without raising')
    for cid in CORRIDORS:
        rec = read_corridor(cid)
        assert rec is not None, cid
        assert rec['live_state'] in CORRIDOR_STATES, (cid, rec['live_state'])
        assert not rec['instrument_errors'], (cid, rec['instrument_errors'])
    print(f'  {len(CORRIDORS)} corridors composed, 0 instrument errors\n')

    print('TEST 2 -- THE CENTRAL RULE: no leading instrument => unknown')
    for cid in CORRIDORS:
        rec = read_corridor(cid)
        assert rec['live_state'] == 'unknown', (cid, 'must not claim a state')
        assert rec['sensed'] is False, cid
    print('  all corridors unknown + sensed=False at v1.0.0 (correct)\n')

    print('TEST 3 -- a structural instrument NEVER sets live_state')
    bs = read_corridor('black_sea_grain_corridor')
    assert bs['baseline_tier'] == 'listed', bs['baseline_tier']
    assert bs['live_state'] == 'unknown', 'JWC listing must not imply traffic'
    assert any(r['instrument'] == 'jwc_listed_area' for r in bs['readings'])
    print(f"  baseline_tier={bs['baseline_tier']} while live_state="
          f"{bs['live_state']} -- the September circular does not claim to "
          f"know this morning\n")

    print('TEST 4 -- severity ordering ignores unknown')
    assert _worst(['open', 'impaired', 'strained']) == 'impaired'
    assert _worst(['unknown', 'open']) == 'open'
    assert _worst(['unknown']) is None
    assert _worst([]) is None
    print('  _worst() never returns unknown as a severity\n')

    print('TEST 5 -- prose says missing data, never calm')
    for cid in CORRIDORS:
        txt = read_corridor(cid)['read']
        assert 'NOT SENSED' in txt, cid
        assert 'calm' in txt.lower(), cid     # it says "not a finding of calm"
    print(f'  {len(CORRIDORS)}/{len(CORRIDORS)} corridor prose refuses to '
          f'report calm\n')

    print('TEST 6 -- id hygiene: no collision with reserved/external ids')
    for rid in RESERVED_TERMINAL_IDS + EXTERNALLY_OWNED_IDS:
        assert rid not in CORRIDORS, f'{rid} must not be a corridor'
    print(f'  {len(RESERVED_TERMINAL_IDS + EXTERNALLY_OWNED_IDS)} reserved ids '
          f'kept out of CORRIDORS\n')

    print('TEST 7 -- payload summary is honest about zero sensing')
    payload = read_all_corridors()
    assert payload['any_sensed'] is False
    assert payload['worst_state'] == 'unknown'
    assert 'not calm' in payload['summary']
    print(f"  {payload['summary']}\n")

    print('TEST 8 -- adapters never raise on a malformed corridor')
    junk = {'name': 'junk'}
    for a in ADAPTERS:
        a(junk)
    print('  3 adapters survived a corridor with no fields\n')

    print('TEST 9 -- THE CONTRACT: a wired leading instrument changes the read')
    # Proves the module is honest-by-design, not honest-by-being-empty. If this
    # fails, v1.0.0's silence is a bug wearing a doctrine costume.
    def _fake_leading(corridor):
        if corridor.get('name', '').startswith('Black Sea'):
            return {'instrument': 'fake_spread', 'confidence': 'leading',
                    'state_hint': 'impaired', 'evidence': 'test',
                    'as_of': '2026-10-04', 'source': 'test'}
        return None

    def _fake_corroborating(corridor):
        return {'instrument': 'fake_chatter', 'confidence': 'corroborating',
                'state_hint': 'blocked', 'evidence': 'test', 'as_of': '2026-10-04',
                'source': 'test'}

    _orig = ADAPTERS
    try:
        globals()['ADAPTERS'] = _orig + (_fake_leading,)
        bs2 = read_corridor('black_sea_grain_corridor')
        assert bs2['live_state'] == 'impaired', bs2['live_state']
        assert bs2['sensed'] is True
        assert bs2['baseline_tier'] == 'listed', 'baseline must survive'
        assert 'NOT SENSED' not in bs2['read']
        print(f"  leading instrument wired -> live_state={bs2['live_state']}, "
              f"baseline still {bs2['baseline_tier']}")

        # a corroborating instrument may RAISE a reading...
        globals()['ADAPTERS'] = _orig + (_fake_leading, _fake_corroborating)
        bs3 = read_corridor('black_sea_grain_corridor')
        assert bs3['live_state'] == 'blocked', bs3['live_state']
        print(f"  corroborating raised impaired -> {bs3['live_state']}")

        # ...but must NEVER create one from nothing. This is the guard that
        # stops a keyword match from becoming a measurement.
        globals()['ADAPTERS'] = _orig + (_fake_corroborating,)
        dn = read_corridor('danube_river')
        assert dn['live_state'] == 'unknown', (
            'corroborating-only must NOT create a state, got ' + dn['live_state'])
        assert dn['sensed'] is False
        print('  corroborating alone -> still unknown (chatter is not a sensor)')
    finally:
        globals()['ADAPTERS'] = _orig

    # and the module is back where it started
    assert read_corridor('black_sea_grain_corridor')['live_state'] == 'unknown'
    print('  adapters restored; module back to honest-empty\n')

    print('TEST 10 -- ROUTE EVENT GUARDS (the safety-critical ones)')
    # These exercise the instrument with synthetic corpora. Without them the
    # earlier tests only prove the adapter is silent when GDELT is absent,
    # which is not the same as proving it is correct when it is present.
    bs_corr = CORRIDORS['black_sea_grain_corridor']

    def _with_corpus(titles, fn):
        """Run _adapter_route_events against a fake gateway.

        Patches THIS module's globals() directly. An earlier version did
        `import corridor_registry as _self` and patched that -- but running
        this file as a script makes it __main__, so the import created a
        SECOND module object and the patch landed on the wrong copy. The
        adapter stayed blind and the first two guard tests passed because the
        result was None for the wrong reason. False green, caught by 10c.
        """
        def _fake(query, language=None, timespan=None, maxrecords=None, label=None):
            return [{'title': t, 'source': src} for t, src in titles]
        g = globals()
        og, oa = g['_gw_gdelt'], g['_GDELT_GATEWAY']
        g['_gw_gdelt'], g['_GDELT_GATEWAY'] = _fake, True
        try:
            return fn()
        finally:
            g['_gw_gdelt'], g['_GDELT_GATEWAY'] = og, oa

    # The harness must be able to produce a POSITIVE before any negative
    # result from it can be believed. This is the check the first version
    # lacked.
    _canary = _with_corpus([('Odesa port closed, exports halted', 'reuters'),
                            ('Black Sea corridor suspended', 'ap')],
                           lambda: _adapter_route_events(bs_corr))
    assert _canary is not None, 'HARNESS DEAD: fake gateway not reaching adapter'
    print('  10-canary     : harness proven live (produces a positive)')

    # 10a ANCHOR -- an unrelated port closure must NOT move the Black Sea
    r = _with_corpus([('Shanghai port closed after typhoon', 'reuters'),
                      ('Port closed in Chile amid strike', 'ap'),
                      ('Exports halted at Durban container terminal', 'bbc')],
                     lambda: _adapter_route_events(bs_corr))
    assert r is None, f'ANCHOR LEAK: unrelated ports moved the corridor -> {r}'
    print('  10a anchor   : 3 unrelated port closures -> None  (no leak)')

    # 10b COMMENTARY -- op-ed about closure must not fire
    r = _with_corpus([('Analysis: Black Sea closure could disrupt global wheat', 'ft'),
                      ('Opinion: why the Odesa corridor threatens to collapse', 'economist'),
                      ('Explainer: what happens if Black Sea exports halted', 'vox')],
                     lambda: _adapter_route_events(bs_corr))
    assert r is None, f'COMMENTARY LEAK: op-eds set a state -> {r}'
    print('  10b commentary: 3 anchored op-eds -> None  (counted, not promoted)')

    # 10c CORROBORATION -- one source is a claim, two are a condition
    one = _with_corpus([('Odesa grain terminal struck overnight', 'reuters')],
                       lambda: _adapter_route_events(bs_corr))
    assert one is None, f'one source should not set impaired -> {one}'
    two = _with_corpus([('Odesa grain terminal struck overnight', 'reuters'),
                        ('Drone attack on Odesa port infrastructure', 'ap')],
                       lambda: _adapter_route_events(bs_corr))
    assert two and two['state_hint'] == 'impaired', two
    assert two['source_count'] == 2
    print('  10c corrobor. : 1 source -> None | 2 sources -> impaired')

    # 10d SAME SOURCE TWICE is still one source
    dup = _with_corpus([('Odesa grain terminal struck overnight', 'reuters'),
                        ('Odesa port hit again, says official', 'reuters')],
                       lambda: _adapter_route_events(bs_corr))
    assert dup is None, f'same outlet twice must not corroborate itself -> {dup}'
    print('  10d dedupe    : same outlet twice -> None  (not self-corroborating)')

    # 10e SEVERITY -- blocked outranks strained when BOTH are corroborated
    sev = _with_corpus([('Black Sea exports halted as corridor suspended', 'reuters'),
                        ('Odesa port closed to commercial traffic', 'bbc'),
                        ('War risk premium rises for Odesa calls', 'lloydslist'),
                        ('Convoy programme announced for Black Sea', 'ap')],
                       lambda: _adapter_route_events(bs_corr))
    assert sev and sev['state_hint'] == 'blocked', sev
    print(f"  10e severity  : both classes corroborated -> {sev['state_hint']}")

    # 10e2 FALL-THROUGH -- an UNDER-corroborated stronger class must not set
    # the state, but must not vanish either. One outlet claiming closure while
    # two report strain is the single most decision-relevant thing in the
    # corpus, and burying it would be the quiet kind of dishonesty.
    ft = _with_corpus([('Black Sea exports halted as corridor suspended', 'reuters'),
                       ('War risk premium rises for Odesa calls', 'lloydslist'),
                       ('Convoy programme announced for Black Sea', 'ap')],
                      lambda: _adapter_route_events(bs_corr))
    assert ft and ft['state_hint'] == 'strained', ft
    assert ft['under_corroborated'], 'stronger claim was silently dropped'
    assert ft['under_corroborated'][0]['state'] == 'blocked'
    assert 'fall short' in ft['evidence']
    print('  10e2 fallthru : 1-source blocked -> state stays strained, but the '
          'claim is carried in evidence')

    # 10f RECOVERY -- the only path to 'open', and it still needs 2 sources
    rec = _with_corpus([('Black Sea exports resumed after pause', 'reuters'),
                        ('Odesa port reopened to commercial traffic', 'ap')],
                       lambda: _adapter_route_events(bs_corr))
    assert rec and rec['state_hint'] == 'open', rec
    rec1 = _with_corpus([('Black Sea exports resumed after pause', 'reuters')],
                        lambda: _adapter_route_events(bs_corr))
    assert rec1 is None, 'one source must not assert open'
    print('  10f recovery  : 2 sources -> open | 1 source -> None')

    # 10g SILENCE -- an anchored but eventless corpus is NOT 'open'
    sil = _with_corpus([('Odesa hosts grain export conference', 'reuters'),
                        ('Black Sea shipping volumes discussed at summit', 'ap')],
                       lambda: _adapter_route_events(bs_corr))
    assert sil is None, f'eventless corpus must not assert anything -> {sil}'
    print('  10g silence   : anchored but eventless -> None  (never defaults open)')

    # 10h END TO END -- a real impairment reaches the composed record
    def _impair(corridor):
        return ({'instrument': 'route_events', 'confidence': 'leading',
                 'state_hint': 'impaired', 'evidence': 'test',
                 'as_of': '2026-10-04', 'source': 'test'}
                if corridor.get('name', '').startswith('Black Sea') else None)
    _o = ADAPTERS
    try:
        globals()['ADAPTERS'] = (_adapter_jwc_baseline, _impair)
        full = read_all_corridors()
        bsr = [c for c in full['corridors']
               if c['corridor_id'] == 'black_sea_grain_corridor'][0]
        assert bsr['live_state'] == 'impaired' and bsr['sensed'] is True
        assert full['any_sensed'] is True and full['worst_state'] == 'impaired'
        assert 'NOT SENSED' not in bsr['read']
        others = [c for c in full['corridors'] if c['corridor_id'] != 'black_sea_grain_corridor']
        assert all(c['live_state'] == 'unknown' for c in others), (
            'one impaired corridor must not infect the others')
        print(f"  10h end-to-end: payload worst_state={full['worst_state']}, "
              f"other 3 corridors still unknown (no contagion)")
    finally:
        globals()['ADAPTERS'] = _o
    print()

    print('TEST 11 -- freight context is CONTEXT, not a sensor')
    fc = freight_context()
    assert fc['affects_corridor_state'] is False
    assert fc['scope'].startswith('GLOBAL')
    # and it must never appear as an adapter
    assert 'freight' not in ' '.join(a.__name__ for a in ADAPTERS)
    # a payload with freight context present must still read unsensed
    pl = read_all_corridors()
    assert 'freight_context' in pl and pl['any_sensed'] is False
    print(f"  BDRY available={fc['available']}, affects_state=False, "
          f"not in ADAPTERS, payload still unsensed\n")

    print('ALL CORRIDOR REGISTRY TESTS PASSED')
