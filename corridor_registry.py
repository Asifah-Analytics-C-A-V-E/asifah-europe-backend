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

__version__ = '1.0.0'

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
    _adapter_origin_spread,
    _adapter_throughput,
)


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

    print('ALL CORRIDOR REGISTRY TESTS PASSED')
