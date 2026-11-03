"""
Asifah Analytics -- Europe Actor Matrix v1.1.0
November 3, 2026   (v1.0.0 same day)

v1.1.0 -- reads the Ukraine v1.2 / Moldova v1.2 trackers:
  * US -> Ukraine (patron) from Ukraine's us_vector: aid AND who Washington leans on
  * Ukraine -> the Russia-Iran axis: drone defence in the Gulf, the Caspian supply line
  * Russia -> Moldova and drone incursions read Moldova's new airspace red line
  * Russia -> Ukraine also reads Ukraine's evidence-based russia_pressure
  * a tracker's own `thin_read` (corpus too small) wins over `sensing_degraded`
    (GDELT absent) -- a 300-article scan without GDELT is not blind

The Europe sibling of the ME, Africa and Asia actor matrices. A READER, NOT A
SCANNER: every cell comes from a tracker that already runs -- the Europe
rhetoric trackers (europe_regional_bluf TRACKER_KEYS) and the ME military
tracker's shared cache (`military_tracker_cache`).

THE QUESTION THIS BOARD ANSWERS
  The war in Ukraine is the floor, not the finding: Russia -> Ukraine reads hot
  every day. The question is:
  BEYOND THE WAR, IS MOSCOW PRESSING ONE NATO-FACING FRONT OR SEVERAL AT ONCE?
  Poland (sabotage, the cohabitation gap), Moldova (Transnistria, interference,
  energy), drones crossing into countries NOT at war, the Black Sea (passage,
  mines, shipping) and the hybrid campaign across the eastern flank -- read side
  by side. Simultaneous pressure is a different situation from one probe at a
  time, and no single-country card can show which one this is.
  Rachel's priorities (Nov 2 2026), in order: Russia <-> Ukraine, Russia -> Poland,
  Russia -> Moldova, drone incursions wherever they occur, the Black Sea.

KINDS
  pressure   who is pressing whom
  space      contested spaces -- not one country's tracker (drone incursions, the Black Sea)
  patron     who is backing whom
  dyad       rivalries where the tracker cannot split the two directions

HOW A CELL IS READ  (source kinds)
  ('actor',    tracker, id)          actors[id] / actor_summaries[id] -> level | escalation_level
  ('path',     tracker, 'a.b', map)  a named field in the payload, through a mapper:
                 int5    integer, may assert L5 (kinetic war ladder only)
                 int4    integer, capped at L4 (everything else -- the L5 assertion rule)
                 native5 a tracker's own six-rung ladder (Greece): rung 5 -> L4
                 band    quiet 0 / simmering 1 / elevated 2 / high 3 / critical 4
                 status  INACTIVE/DORMANT 0, WATCHING/SIGNALED/ACTIVE 2, APPROACHING 3, BREACHED 4
                 rung    Poland's kinetic rung: nuisance 2, infrastructure 3, casualty 4
                 swan    a black-swan flag: True -> 4
  ('redline',  tracker, id)          red_lines.triggered[id].status through `status`
  ('military', 'actor', id)          ME military tracker actor_summaries[id].alert_level:
                                     normal 0 / elevated 2 / high 3 / surge 3 (volume -> capped L3)
  ('chokepoint', 'military', id)     ME military tracker chokepoint: open 0 / monitored 2 /
                                     contested 3 / disrupted 4
  The cell takes the HIGHEST source. Nothing but an int5 source asserts L5.

ABSENCE-HONEST
  No tracker -> 'unread'. Tracker read but the field absent -> 'not sensed'.
  Tracker read on a DEGRADED scan (sensing_degraded) and nothing above L0 ->
  'under-read', shown as a gap. Older than 48h -> 'stale', a gap. None of these
  is ever L0.

ENDPOINTS
  /api/europe/actor-matrix                    all pairs + headline + So What lines
  /api/europe/actor-matrix?actor=poland       pairs touching one card
  /api/europe/actor-matrix/debug              per tracker: what was read, what each pair uses

Cost: Redis reads only (~14 keys), cached 15 min. No external fetch, ever.
"""

import os
import json
import time
from datetime import datetime, timezone

import requests

MATRIX_VERSION = '1.1.0'
CACHE_KEY = 'actor_matrix:europe:latest'
PREV_KEY = 'actor_matrix:europe:previous_levels'
CACHE_SEC = 15 * 60
STALE_HOURS = 48
MILITARY_KEY = 'military_tracker_cache'

UPSTASH_REDIS_URL = os.environ.get('UPSTASH_REDIS_URL') or os.environ.get('UPSTASH_REDIS_REST_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN') or os.environ.get('UPSTASH_REDIS_REST_TOKEN')

LADDER = {0: 'Monitoring', 1: 'Rhetoric', 2: 'Warning', 3: 'Confrontation',
          4: 'Coercion', 5: 'Active Conflict', 6: 'Red Line Breached'}
KIND_LABELS = {'pressure': 'Who is pressing whom',
               'space': 'Contested spaces (not one country)',
               'patron': 'Who is backing whom',
               'dyad': 'Rivalries (both directions)'}

DEFAULT_TRACKER_KEYS = {
    'russia': 'rhetoric:russia:latest', 'ukraine': 'rhetoric:ukraine:latest',
    'poland': 'rhetoric:poland:latest', 'moldova': 'rhetoric:moldova:latest',
    'belarus': 'rhetoric:belarus:latest', 'greenland': 'rhetoric:greenland:latest',
    'hungary': 'rhetoric:hungary:latest', 'turkey': 'rhetoric:turkey:latest',
    'azerbaijan': 'rhetoric:azerbaijan:latest', 'cyprus': 'rhetoric:cyprus:latest',
    'greece': 'rhetoric:greece:latest', 'armenia': 'rhetoric:armenia:latest',
    'kazakhstan': 'rhetoric:kazakhstan:latest',
}

BANDS = {'quiet': 0, 'baseline': 0, 'normal': 0, 'low': 0, 'simmering': 1, 'watch': 1,
         'elevated': 2, 'active': 2, 'high': 3, 'critical': 4, 'surge': 3}
STATUS = {'INACTIVE': 0, 'DORMANT': 0, 'QUIET': 0, 'CLEAR': 0, 'WATCHING': 2, 'SIGNALED': 2,
          'ACTIVE': 2, 'ELEVATED': 2, 'APPROACHING': 3, 'BREACHED': 4, 'TRIGGERED': 4}
MIL = {'normal': 0, 'elevated': 2, 'high': 3, 'surge': 3}
CHOKE = {'open': 0, 'monitored': 2, 'contested': 3, 'disrupted': 4}
RUNG = {0: 0, 1: 2, 2: 3, 3: 4}

RU, UA, PL, MD, BY, KZ, TR, GR, CY, AZ, AM, US, GL, HU, IR = (
    '🇷🇺', '🇺🇦', '🇵🇱', '🇲🇩', '🇧🇾', '🇰🇿', '🇹🇷', '🇬🇷', '🇨🇾', '🇦🇿', '🇦🇲', '🇺🇸', '🇬🇱', '🇭🇺', '🇮🇷')
NATO, SEA, SKY = '🛡️', '🌊', '🛸'


def _P(pid, kind, actor, a_flag, target, t_flag, keys, sources, theatre, note=''):
    return {'id': pid, 'kind': kind, 'actor': actor, 'actor_flag': a_flag, 'target': target,
            'target_flag': t_flag, 'keys': keys, 'sources': sources, 'theatre': theatre, 'note': note}


# The NATO-facing fronts: the core question counts how many are hot at once.
# Russia -> Ukraine is deliberately NOT in this list -- the war is the floor.
MOSCOW_FRONTS = ['russia>poland', 'russia>moldova', 'drones>nonbelligerents', 'black_sea',
                 'russia>flank', 'russia>kazakhstan']
FRONT_LABELS = {'russia>poland': 'Poland', 'russia>moldova': 'Moldova',
                'drones>nonbelligerents': 'drone incursions', 'black_sea': 'the Black Sea',
                'russia>flank': 'the eastern-flank hybrid campaign', 'russia>kazakhstan': 'Kazakhstan'}

PAIRS = [
    # ---------------- THE WAR (both directions) ----------------
    _P('russia>ukraine', 'pressure', 'Russia', RU, 'Ukraine (the war)', UA, ['russia', 'ukraine'],
       [('path', 'russia', 'ground_ops_level', 'int5'), ('path', 'ukraine', 'russia_pressure.level', 'int5'),
        ('redline', 'ukraine', 'kyiv_strike_significant'),
        ('redline', 'ukraine', 'energy_grid_collapse'), ('military', 'actor', 'russia')], 'russia',
       note='The war is the floor, not the finding: corroborated ground operations read L5 Active Conflict '
            'every day. The only row allowed to assert L5.'),
    _P('ukraine>russia', 'pressure', 'Ukraine', UA, 'Russia (deep strikes · sea denial)', RU, ['ukraine', 'russia'],
       [('redline', 'ukraine', 'ukraine_strike_russia_significant'), ('actor', 'russia', 'ukraine'),
        ('military', 'actor', 'ukraine')], 'ukraine',
       note='Escalation runs both ways: refinery and airbase strikes inside Russia, sea drones against the Black Sea Fleet.'),

    # ---------------- MOSCOW'S NATO-FACING FRONTS (the core question) ----------------
    _P('russia>poland', 'pressure', 'Russia (hybrid campaign)', RU, 'Poland', PL, ['russia', 'poland'],
       [('path', 'poland', 'hybrid_tempo.band', 'band'), ('path', 'poland', 'hybrid_tempo.kinetic_rung', 'rung'),
        ('path', 'poland', 'casualty_tripwire.black_swan', 'swan')], 'poland',
       note='Sabotage, arson, cyber and influence below the threshold of war. The aim is cost, not alignment.'),
    _P('russia>moldova', 'pressure', 'Russia (Transnistria · interference · energy)', RU, 'Moldova', MD,
       ['russia', 'moldova'],
       [('path', 'moldova', 'interference_tempo.status', 'status'), ('path', 'moldova', 'transnistria_watch.status', 'status'),
        ('path', 'moldova', 'energy_lever.status', 'status'), ('redline', 'moldova', 'transnistria_mobilization'),
        ('redline', 'moldova', 'energy_cutoff'), ('redline', 'moldova', 'election_capture'),
        ('path', 'moldova', 'russia_pressure.level', 'int4'), ('actor', 'moldova', 'russia_inbound'),
        ('military', 'actor', 'moldova')], 'moldova'),
    _P('drones>nonbelligerents', 'space', 'Russian drones', SKY,
       'Countries not at war (Poland · Romania · Moldova · Baltics)', NATO,
       ['russia', 'poland', 'moldova'],
       [('path', 'russia', 'drone_incursion_level', 'int4'), ('redline', 'moldova', 'airspace_violation')], 'russia',
       note='Drones INTO a country not at war. Battlefield strikes inside Ukraine never count here.'),
    _P('black_sea', 'space', 'Russia ↔ Ukraine at sea', SEA, 'The Black Sea (passage · mines · shipping)', SEA,
       ['russia', 'ukraine', 'turkey'],
       [('path', 'russia', 'black_sea_level', 'int4'), ('redline', 'ukraine', 'grain_corridor_disruption'),
        ('redline', 'ukraine', 'crimea_bsf_displacement'), ('chokepoint', 'military', 'black_sea'),
        ('chokepoint', 'military', 'bosporus')], 'russia',
       note='Read from the Russia tracker\'s Black Sea vector, Ukraine\'s grain-corridor and Black Sea Fleet red lines, and the military tracker\'s Black Sea and Bosphorus chokepoints.'),
    _P('russia>flank', 'pressure', 'Russia (hybrid · airspace)', RU, 'NATO eastern flank', NATO,
       ['russia', 'poland'],
       [('path', 'russia', 'hybrid_level', 'int4'), ('path', 'russia', 'nato_flank_level', 'int4')], 'russia'),
    _P('russia>kazakhstan', 'pressure', 'Russia', RU, 'Kazakhstan (levers · irredentism)', KZ, ['russia', 'kazakhstan'],
       [('actor', 'kazakhstan', 'russia_inbound')], 'kazakhstan'),

    # ---------------- OTHER PRESSURE ----------------
    _P('russia>nuclear', 'pressure', 'Russia (nuclear signalling)', RU, 'NATO & Ukraine', NATO, ['russia', 'ukraine'],
       [('path', 'russia', 'nuclear_level', 'int4')], 'russia',
       note='Doctrine language and threats -- signalling, never use. Use would sit on the war row.'),
    _P('belarus>poland', 'pressure', 'Belarus (with Russia)', BY, 'Poland & the Baltics (weaponised migration)', PL,
       ['belarus', 'poland'],
       [('path', 'poland', 'instrumentalized_migration.band', 'band'), ('military', 'actor', 'belarus')], 'poland',
       note='Inverted corridor: progress on the Belarus border is bad news -- the flow is the weapon.'),
    _P('turkey>cyprus', 'pressure', 'Turkey', TR, 'Cyprus (EEZ · Green Line · TRNC)', CY, ['turkey', 'cyprus'],
       [('path', 'cyprus', 'turkey_posture_level', 'int4'), ('path', 'cyprus', 'trnc_level', 'int4'),
        ('path', 'cyprus', 'eez_level', 'int4')], 'cyprus'),
    _P('azerbaijan>armenia', 'pressure', 'Azerbaijan', AZ, 'Armenia (peace implementation)', AM, ['azerbaijan', 'armenia'],
       [('path', 'azerbaijan', 'armenia_corridor_level', 'int4')], 'azerbaijan'),
    _P('us>greenland', 'pressure', 'United States', US, 'Greenland (sovereignty)', GL, ['greenland'],
       [('path', 'greenland', 'us_pressure_level', 'int4')], 'greenland'),

    # ---------------- RIVALRIES ----------------
    _P('turkey<>greece', 'dyad', 'Turkey', TR, 'Greece (Aegean · EEZ)', GR, ['turkey', 'greece'],
       [('path', 'greece', 'turkey_axis_level', 'native5')], 'greece',
       note='Greece runs its own six-rung ladder; its rung 5 (detente rupture) maps to platform L4.'),

    # ---------------- PATRONS / BACKERS ----------------
    _P('us>ukraine', 'patron', 'United States', US, 'Ukraine (aid · and who Washington leans on)', UA,
       ['ukraine'],
       [('path', 'ukraine', 'us_vector.level', 'int4'), ('actor', 'ukraine', 'us_government'),
        ('actor', 'russia', 'united_states')], 'ukraine',
       note=('Read both ways: the aid pipeline AND public pressure on Kyiv vs on Moscow. A guarantor leaning on '
             'the side it arms is a different signal from one leaning on the aggressor -- see the Ukraine page.')),
    _P('nato>ukraine', 'patron', 'Europe & NATO allies', NATO, 'Ukraine (aid · air defence · guarantees)', UA,
       ['ukraine'],
       [('actor', 'ukraine', 'nato_western_support'), ('path', 'ukraine', 'nato_track.level', 'int4'),
        ('actor', 'russia', 'nato_alliance')], 'ukraine'),
    _P('ukraine>iran_axis', 'pressure', 'Ukraine', UA, 'The Russia–Iran axis (Gulf drone defence · Caspian supply)',
       IR, ['ukraine'],
       [('path', 'ukraine', 'drone_diplomacy.level', 'int4')], 'ukraine',
       note=('Kyiv fights the same Shahed design at both ends: over its cities, and as an exporter of '
             'counter-drone expertise to the Gulf. Capped L3 -- a vector, not a front.')),
    _P('russia>belarus', 'patron', 'Russia', RU, 'Belarus (forces · nuclear basing)', BY, ['belarus', 'russia'],
       [('actor', 'russia', 'belarus')], 'russia'),
    _P('russia>hungary', 'patron', 'Russia', RU, 'Hungary (energy · the EU veto)', HU, ['hungary', 'russia'],
       [('path', 'hungary', 'hungary_russia_axis_level', 'int4')], 'hungary'),
    _P('iran<>russia', 'patron', 'Iran ↔ Russia', IR, 'Drones · missiles · diplomatic cover', RU, ['russia'],
       [('actor', 'russia', 'russia_iran_axis')], 'russia',
       note='The Europe-to-Middle-East bridge: what Tehran supplies Moscow, and what Moscow gives back.'),
]

COVERAGE_GAPS = [
    'No tracker yet for Romania, the Baltic states or Finland: drone incursions there are read from the Russia '
    'tracker\'s corpus and the military tracker, not from their own trackers.',
    'Belarus -> Poland reads Poland\'s border corridor; Belarus\'s own tracker reads regime pressure, not outbound pressure.',
]

CARD_ALIASES = {}


# ----------------------------------------------------------------------------
# REDIS
# ----------------------------------------------------------------------------
def _rget(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=6)
        res = r.json().get('result')
        return json.loads(res) if res else None
    except Exception as e:
        print(f'[Europe Matrix] Redis get {key}: {str(e)[:100]}')
        return None


def _rset(key, value, ttl=7 * 86400):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(UPSTASH_REDIS_URL, headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                          json=['SET', key, json.dumps(value, default=str), 'EX', str(ttl)], timeout=8)
        return r.status_code == 200
    except Exception as e:
        print(f'[Europe Matrix] Redis set {key}: {str(e)[:100]}')
        return False


def _tracker_keys():
    try:
        import europe_regional_bluf as b
        keys = dict(b.TRACKER_KEYS)
        for k, v in DEFAULT_TRACKER_KEYS.items():
            keys.setdefault(k, v)
        return keys
    except Exception:
        return dict(DEFAULT_TRACKER_KEYS)


# ----------------------------------------------------------------------------
# READING
# ----------------------------------------------------------------------------
def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return max(0, min(6, int(v)))
    if isinstance(v, str):
        s = v.strip()
        if s.lstrip('-').isdigit():
            return max(0, min(6, int(s)))
        if s.lower() in BANDS:
            return BANDS[s.lower()]
    return None


def _path(raw, dotted):
    cur = raw
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _map(value, mapper):
    """-> (level or None, may_assert_l5)."""
    if value is None:
        return None, False
    if mapper == 'int5':
        return _num(value), True
    if mapper in ('int4', 'native5'):
        n = _num(value)
        return (None if n is None else min(4, n)), False
    if mapper == 'band':
        return (BANDS.get(str(value).strip().lower()) if isinstance(value, str) else _num(value)), False
    if mapper == 'status':
        return STATUS.get(str(value).strip().upper()), False
    if mapper == 'rung':
        n = _num(value)
        return (None if n is None else RUNG.get(min(3, n), 0)), False
    if mapper == 'swan':
        return (4 if value is True else 0) if isinstance(value, bool) else None, False
    return _num(value), False


def _age_hours(ts):
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return None


def read_trackers(redis_get=None):
    """{tracker: {'raw', 'scanned_at', 'freshness', 'degraded'}}, plus the military cache under 'military'."""
    rget = redis_get or _rget
    out, missing = {}, []
    for th, key in _tracker_keys().items():
        raw = rget(key)
        if isinstance(raw, dict) and raw:
            ts = raw.get('scanned_at') or raw.get('cached_at') or raw.get('timestamp') or raw.get('updated_at') or ''
            age = _age_hours(ts)
            degraded = raw.get('thin_read') if 'thin_read' in raw else raw.get('sensing_degraded')
            out[th] = {'raw': raw, 'scanned_at': ts,
                       'freshness': 'stale' if (age is not None and age > STALE_HOURS) else 'live',
                       'degraded': bool(degraded)}
        else:
            missing.append(th)
    mil = rget(MILITARY_KEY)
    if isinstance(mil, dict) and mil:
        ts = mil.get('cached_at') or mil.get('last_updated') or ''
        age = _age_hours(ts)
        out['military'] = {'raw': mil, 'scanned_at': ts, 'degraded': False,
                           'freshness': 'stale' if (age is not None and age > STALE_HOURS) else 'live'}
    else:
        missing.append('military')
    return out, missing


def _read_source(src, trackers):
    """-> (state, level, may_l5, tracker, detail). state: read | absent | unread | stale."""
    kind = src[0]
    th = 'military' if kind in ('military', 'chokepoint') else src[1]
    t = trackers.get(th)
    if not t:
        return 'unread', None, False, th, ''
    if t['freshness'] == 'stale':
        return 'stale', None, False, th, ''
    raw = t['raw']
    if kind == 'actor':
        sid = src[2]
        rec = None
        for block in ('actors', 'actor_summaries'):
            b = raw.get(block)
            if isinstance(b, dict) and isinstance(b.get(sid), dict):
                rec = b[sid]
                break
        if rec is None:
            return 'absent', None, False, th, sid
        lv = _num(rec.get('level'))
        if lv is None:
            lv = _num(rec.get('escalation_level'))
        if lv is None:
            return 'absent', None, False, th, sid
        return 'read', min(4, lv), False, th, f'actor:{sid}'
    if kind == 'path':
        lv, l5 = _map(_path(raw, src[2]), src[3])
        if lv is None:
            return 'absent', None, False, th, src[2]
        return 'read', lv, l5, th, src[2]
    if kind == 'redline':
        rl = raw.get('red_lines')
        trig = rl.get('triggered') if isinstance(rl, dict) else rl
        for r in trig or []:
            if isinstance(r, dict) and r.get('id') == src[2]:
                lv = STATUS.get(str(r.get('status') or '').upper())
                if lv is None:
                    return 'absent', None, False, th, src[2]
                return 'read', lv, False, th, f'red line {src[2]} ({r.get("status")})'
        return 'absent', None, False, th, src[2]
    if kind == 'military':
        rec = (raw.get('actor_summaries') or {}).get(src[2])
        if not isinstance(rec, dict):
            return 'absent', None, False, th, src[2]
        lv = MIL.get(str(rec.get('alert_level') or '').lower())
        if lv is None:
            return 'absent', None, False, th, src[2]
        return 'read', lv, False, th, f'military {src[2]} {rec.get("alert_level")} ({rec.get("signal_count", 0)} signals)'
    if kind == 'chokepoint':
        rec = (raw.get('chokepoint_postures') or {}).get(src[2])
        if not isinstance(rec, dict):
            return 'absent', None, False, th, src[2]
        lv = CHOKE.get(str(rec.get('alert_level') or '').lower())
        if lv is None:
            return 'absent', None, False, th, src[2]
        return 'read', lv, False, th, f'chokepoint {src[2]} {rec.get("alert_level")}'
    return 'absent', None, False, th, ''


def read_pair(pair, trackers):
    best, states, degraded_hit = None, [], False
    for src in pair['sources']:
        state, lv, l5, th, detail = _read_source(src, trackers)
        states.append((state, th))
        if state != 'read':
            continue
        if trackers.get(th, {}).get('degraded'):
            degraded_hit = True
        lv = lv if l5 else min(4, lv)
        cand = {'level': lv, 'tracker': th, 'detail': detail,
                'degraded_scan': bool(trackers.get(th, {}).get('degraded'))}
        if best is None or cand['level'] > best['level']:
            best = cand
    cell = {k: pair[k] for k in ('id', 'kind', 'actor', 'actor_flag', 'target', 'target_flag', 'keys', 'theatre', 'note')}
    cell['kind_label'] = KIND_LABELS[pair['kind']]
    read_from = sorted({th for s, th in states if s == 'read'})
    clean_read = any(s == 'read' and not trackers.get(th, {}).get('degraded') for s, th in states)
    if best and (best['level'] > 0 or clean_read):
        cell.update(state='read', level=best['level'], word=LADDER[best['level']], source=best,
                    under_read=best['degraded_scan'])
    elif best:
        # Read only on degraded scans and nothing above L0: that is a blind sensor, not calm.
        cell.update(state='under_read', level=None, word='Under-read', under_read=True,
                    source={'trackers_read': read_from, 'reason': 'sources degraded this cycle and nothing sensed'})
    elif any(s == 'absent' for s, _ in states):
        cell.update(state='not_sensed', level=None, word='Not sensed', under_read=False,
                    source={'trackers_read': sorted({th for s, th in states if s == 'absent'}),
                            'reason': 'tracker read; this field absent'})
    elif any(s == 'stale' for s, _ in states):
        cell.update(state='stale', level=None, word='Stale', under_read=False,
                    source={'trackers_stale': sorted({th for s, th in states if s == 'stale'})})
    else:
        cell.update(state='unread', level=None, word='Unread', under_read=False,
                    source={'trackers_missing': sorted({th for s, th in states if s == 'unread'})})
    return cell


# ----------------------------------------------------------------------------
# SO WHAT
# ----------------------------------------------------------------------------
def _name(c):
    return f"{c['actor']} → {c['target']}"


def build_lines(cells, prev, trackers=None):
    lines = []
    by = {c['id']: c for c in cells}
    read = [c for c in cells if c['state'] == 'read']

    # THE CORE QUESTION: beyond the war, how many NATO-facing fronts are hot at once?
    fronts = [by[i] for i in MOSCOW_FRONTS if i in by and by[i]['state'] == 'read']
    hot = [c for c in fronts if c['level'] >= 3]
    blind = [by[i] for i in MOSCOW_FRONTS if i in by and by[i]['state'] != 'read']
    if len(fronts) * 2 < len(MOSCOW_FRONTS):
        lines.append(f"Only {len(fronts)} of {len(MOSCOW_FRONTS)} NATO-facing fronts were read this cycle -- too few to say "
                     "whether Moscow is pressing one front or several. Read the gaps below as blind spots, not calm."
                     + (f" Of those read, hot (L3+): " + ', '.join(f"{FRONT_LABELS[c['id']]} L{c['level']}" for c in hot)
                        if hot else ''))
    elif len(hot) >= 2:
        lines.append(f"Beyond the war in Ukraine, Moscow is pressing on {len(hot)} NATO-facing fronts at once ("
                     + ', '.join(f"{FRONT_LABELS[c['id']]} L{c['level']}" for c in hot)
                     + ") -- simultaneous pressure tests allied attention and cohesion, not just one border.")
    elif len(hot) == 1:
        h = hot[0]
        lines.append(f"Beyond the war, Moscow's pressure is concentrated on {FRONT_LABELS[h['id']]} (L{h['level']}); "
                     "the other NATO-facing fronts read at L2 or below -- one probe at a time.")
    elif fronts:
        lines.append('Beyond the war, no NATO-facing front above L2 this cycle -- '
                     + ', '.join(f"{FRONT_LABELS[c['id']]} L{c['level']}" for c in fronts) + '.')
    if blind:
        lines.append('Not read this cycle: ' + ', '.join(f"{FRONT_LABELS[c['id']]} ({c['word'].lower()})" for c in blind)
                     + ' -- a gap in the sensor, not a quiet front.')

    # The war, both directions
    ru, ua = by.get('russia>ukraine'), by.get('ukraine>russia')
    if ru and ru['state'] == 'read' and ua and ua['state'] == 'read' and ua['level'] >= 3:
        lines.append(f"Escalation is running both ways: Russia's war on Ukraine at L{ru['level']}, Ukraine carrying it "
                     f"into Russia at L{ua['level']} (deep strikes, sea denial).")
    elif ru and ru['state'] != 'read':
        lines.append(f"The war row itself is {ru['word'].lower()} this cycle -- the Russia tracker did not deliver "
                     "a ground-operations read. A gap, not a ceasefire.")

    # The war's edges touching non-belligerents
    dr, bs = by.get('drones>nonbelligerents'), by.get('black_sea')
    if dr and bs and dr['state'] == bs['state'] == 'read' and dr['level'] >= 3 and bs['level'] >= 3:
        lines.append(f"Drones are crossing into countries not at war (L{dr['level']}) while the Black Sea is contested "
                     f"(L{bs['level']}) -- the war's edges are touching NATO territory and shipping in the same window.")
    elif dr and dr['state'] == 'read' and dr['level'] >= 3:
        lines.append(f"Drone incursions into countries not at war at L{dr['level']} -- each one is a test of how "
                     "NATO answers below the Article 5 line.")
    elif bs and bs['state'] == 'read' and bs['level'] >= 3:
        lines.append(f"The Black Sea is contested (L{bs['level']}): shipping, ports and passage are under pressure -- "
                     "grain and energy exporters feel it first.")

    # The US spoke, read both ways (Ukraine tracker us_vector)
    usv = (((trackers or {}).get('ukraine') or {}).get('raw') or {}).get('us_vector') or {}
    if usv.get('posture') == 'pressing_kyiv' and (usv.get('pressure_on_kyiv') or 0) >= 2:
        lines.append(f"Washington's public pressure is running toward Kyiv (L{usv.get('pressure_on_kyiv')}) more than "
                     f"Moscow (L{usv.get('pressure_on_moscow') or 0}), aid pipeline {str(usv.get('aid_pipeline') or '').replace('_', ' ')} "
                     "-- the mediator leaning on the side it arms moves the terms toward the other side.")
    ia = by.get('ukraine>iran_axis')
    if ia and ia['state'] == 'read' and ia['level'] >= 2:
        lines.append(f"Ukraine is active against the Russia-Iran axis beyond its borders (L{ia['level']}): Gulf drone "
                     "defence and the Caspian supply line tie this war to the Middle East.")

    # Poland's two-sided read: pressure from Moscow, and the cohabitation gap it works through
    pl = by.get('russia>poland')
    if pl and pl['state'] == 'read' and pl['level'] >= 3:
        lines.append(f"Russia's hybrid campaign against Poland at L{pl['level']} -- the aim is to make support for Ukraine "
                     "too expensive to sustain, not to flip Poland.")

    if read:
        top = max(c['level'] for c in read)
        tops = [c for c in read if c['level'] == top and c['id'] != 'russia>ukraine']
        if top >= 3 and tops:
            lines.append(f"Highest pressure off the war row: {'; '.join(_name(c) for c in tops[:3])} at L{top} {LADDER[top]}.")

    moved = [f"{_name(x)} (L{prev[x['id']]}→L{x['level']})" for x in read
             if isinstance((prev or {}).get(x['id']), int) and x['level'] - prev[x['id']] >= 2]
    if moved:
        lines.append('Sharp moves since the last read: ' + '; '.join(moved[:3]) + '.')
    under = [x for x in cells if x.get('under_read')]
    gaps = [x for x in cells if x['state'] != 'read']
    if gaps or under:
        lines.append(f"{len(gaps)} of {len(cells)} pairs not read this cycle"
                     + (f"; {len(under)} read on degraded sources" if under else '')
                     + ' -- shown as gaps, not as calm.')
    return lines[:7]


def build_matrix(redis_get, redis_set, trackers=None, missing=None):
    if trackers is None:
        trackers, missing = read_trackers(redis_get)
    cells = [read_pair(p, trackers) for p in PAIRS]
    prev = redis_get(PREV_KEY) or {}
    if not isinstance(prev, dict):
        prev = {}
    for c in cells:
        p = prev.get(c['id'])
        c['previous_level'] = p if isinstance(p, int) else None
        c['delta'] = (c['level'] - p) if (c['state'] == 'read' and isinstance(p, int)) else None
    read = [c for c in cells if c['state'] == 'read']
    off_war = [c for c in read if c['id'] != 'russia>ukraine']
    head = max(off_war, key=lambda c: c['level']) if off_war else (max(read, key=lambda c: c['level']) if read else None)
    fronts = [c for c in cells if c['id'] in MOSCOW_FRONTS and c['state'] == 'read']
    payload = {
        'success': True, 'version': MATRIX_VERSION, 'region': 'europe',
        'built_at': datetime.now(timezone.utc).isoformat(),
        'question': 'Beyond the war in Ukraine, is Moscow pressing one NATO-facing front or several at once?',
        'headline': ({'pair': _name(head), 'level': head['level'], 'word': head['word'], 'kind': head['kind']}
                     if head else None),
        'moscow_fronts': {'read': len(fronts), 'hot': sum(1 for c in fronts if c['level'] >= 3),
                          'levels': {c['id']: c['level'] for c in fronts},
                          'not_read': [i for i in MOSCOW_FRONTS if i not in {c['id'] for c in fronts}]},
        'pairs': cells,
        'kinds': KIND_LABELS,
        'lines': build_lines(cells, prev, trackers),
        'trackers_read': sorted(trackers), 'trackers_missing': sorted(missing or []),
        'trackers_degraded': sorted(t for t, v in trackers.items() if v.get('degraded')),
        'coverage': {'tracked_countries': sorted(_tracker_keys()), 'gaps': COVERAGE_GAPS},
        'method': ('Each pair reads the trackers that watch it -- the Europe rhetoric trackers and the military '
                   'tracker -- and takes the highest reading. Only the war row (Russia -> Ukraine ground '
                   'operations) may assert L5; every other source caps at L4, and military volume reads at L3. '
                   'Nothing here is scanned separately. Unread, stale, not-sensed and under-read pairs are gaps, '
                   'never L0.'),
    }
    if read:
        redis_set(PREV_KEY, {c['id']: c['level'] for c in read})
    return payload


def filter_for_actor(payload, actor):
    a = CARD_ALIASES.get(actor, actor)
    pairs = [c for c in payload.get('pairs', []) if a in c['keys']]
    out = dict(payload)
    out['pairs'], out['actor'] = pairs, a
    read = [c for c in pairs if c['state'] == 'read']
    head = max(read, key=lambda c: c['level']) if read else None
    out['headline'] = ({'pair': _name(head), 'level': head['level'], 'word': head['word'], 'kind': head['kind']}
                       if head else None)
    out['lines'] = build_lines(pairs, {c['id']: c.get('previous_level') for c in pairs}) if pairs else []
    return out


# ----------------------------------------------------------------------------
# FLASK
# ----------------------------------------------------------------------------
def register_europe_actor_matrix(app):
    from flask import jsonify, request
    _mem = {'payload': None, 'at': 0}

    def current():
        if _mem['payload'] and time.time() - _mem['at'] < CACHE_SEC:
            return _mem['payload']
        cached = _rget(CACHE_KEY)
        if isinstance(cached, dict) and time.time() - cached.get('_at', 0) < CACHE_SEC:
            _mem.update(payload=cached, at=cached['_at'])
            return cached
        payload = build_matrix(_rget, _rset)
        payload['_at'] = time.time()
        _rset(CACHE_KEY, payload, ttl=CACHE_SEC * 4)
        _mem.update(payload=payload, at=time.time())
        return payload

    def api_matrix():
        try:
            data = current()
            actor = (request.args.get('actor') or '').strip().lower()
            return jsonify(filter_for_actor(data, actor) if actor else data)
        except Exception as e:
            return jsonify({'success': False, 'version': MATRIX_VERSION, 'state': 'unread',
                            'error': f'{type(e).__name__}: {str(e)[:200]}', 'pairs': []}), 200

    def api_debug():
        try:
            trackers, missing = read_trackers()
        except Exception as e:
            return jsonify({'error': f'{type(e).__name__}: {e}'}), 200
        rows = {}
        for th, t in trackers.items():
            used = [f"{s[0]}:{s[2] if len(s) > 2 else ''}" for p in PAIRS for s in p['sources']
                    if (('military' if s[0] in ('military', 'chokepoint') else s[1]) == th)]
            absent = []
            for p in PAIRS:
                for s in p['sources']:
                    owner = 'military' if s[0] in ('military', 'chokepoint') else s[1]
                    if owner == th and _read_source(s, trackers)[0] == 'absent':
                        absent.append(f"{p['id']} <- {s[0]}:{s[2]}")
            rows[th] = {'scanned_at': t['scanned_at'], 'freshness': t['freshness'], 'degraded': t['degraded'],
                        'fields_used': sorted(set(used)), 'expected_but_absent': absent}
        return jsonify({'version': MATRIX_VERSION, 'trackers': rows, 'missing': missing,
                        'pairs_by_source': {p['id']: [':'.join(str(x) for x in s if x is not None) for s in p['sources']]
                                            for p in PAIRS}})

    app.add_url_rule('/api/europe/actor-matrix', 'europe_actor_matrix', api_matrix, methods=['GET'])
    app.add_url_rule('/api/europe/actor-matrix/debug', 'europe_actor_matrix_debug', api_debug, methods=['GET'])
    print(f"[Europe Matrix] ✅ /api/europe/actor-matrix (+ /debug) -- {len(PAIRS)} pairs, reader only")
