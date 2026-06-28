"""
Asifah Analytics - Azerbaijan Signal Interpreter (analyst layer)
v1.0.0 - June 2026

Consumes the four-wheel scan_data from rhetoric_tracker_azerbaijan.py and
produces the analyst-altitude read. Two public entry points (same contract the
heavy interpreters use, so callers do not branch):

  * interpret_signals(scan_data) -> estimative So-What, plus REAL red-line
                                    detection and historical-precedent matching
                                    (Azerbaijan's four-wheel story is too rich
                                    to stub), and a forward-compatible rumint
                                    stub (RUMINT module is a later build).
  * build_top_signals(scan_data) -> canonical top_signals[] for BLUF / GPI /
                                    Gold Standard card consumption.

DOCTRINE: convergence, not prediction. Estimative voice only - "consistent
with / historically precedes / likely indicates", precedent-anchored. No
probabilities, no dates, no "will". The reader completes the inference.

The four wheels (Baku as active balancer / agent):
  turkey_axis      (alignment)  iran_friction    (friction)
  russia_rupture   (rupture)    israel_axis      (axis, Iran-facing)
  armenia_corridor (the convergence object)
  domestic_legitimacy (baseline)

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

from datetime import datetime, timezone

# Flag + icons (unicode escape -> ASCII-safe source, emoji at runtime)
AZ_FLAG       = '\U0001f1e6\U0001f1ff'   # AZ
ICON_RUSSIA   = '\u26a1'                  # high voltage (rupture / live wire)
ICON_IRAN     = '\u2694\ufe0f'            # crossed swords (friction)
ICON_CORRIDOR = '\U0001f6e3\ufe0f'        # motorway (Zangezur / TRIPP)
ICON_ISRAEL   = '\U0001f6f0\ufe0f'        # satellite (Iran-facing axis)
ICON_TURKEY   = '\U0001f91d'              # handshake (alignment)
ICON_NODE     = '\U0001f3af'              # target (contested node)
ICON_SIREN    = '\U0001f6a8'              # siren (breach)
ICON_RED      = '\U0001f534'              # red circle (theatre-high)
ICON_ORANGE   = '\U0001f7e0'              # orange circle (approaching / pressure)
ICON_ANTENNA  = '\U0001f4e1'              # antenna (convergence flag)

WHEEL_LABEL = {
    'turkey_axis':         'Turkey axis',
    'russia_rupture':      'Russia rupture',
    'iran_friction':       'Iran friction',
    'israel_axis':         'Israel axis',
    'armenia_corridor':    'Armenia / corridor',
    'domestic_legitimacy': 'Domestic legitimacy',
}


# ============================================
# RED LINES (Azerbaijan-specific, precedent-anchored)
# Each: key vector, breach/approach thresholds (intensity ladder), severity,
# icon, and the precedent the estimative read anchors to. Red line #4 is a
# COMPOUND read (Israel axis overt AND Iran friction live).
# ============================================
RED_LINES = [
    {
        'id':        'russia_kinetic',
        'label':     'Baku-Moscow rupture goes kinetic / ambassadorial recall',
        'vector':    'russia_rupture',
        'breach':    5, 'approach': 4, 'severity': 5,
        'icon':      ICON_RUSSIA,
        'precedent': 'Consistent with the trajectory since the Dec 2024 AZAL downing and the Jun 2025 Ekaterinburg deaths.',
    },
    {
        'id':        'iran_border',
        'label':     'Iran-Azerbaijan border kinetic / major drills',
        'vector':    'iran_friction',
        'breach':    4, 'approach': 3, 'severity': 4,
        'icon':      ICON_IRAN,
        'precedent': 'Historically precedes the pattern of Iranian border exercises (2021, 2022-23) framed against the Baku-Jerusalem axis.',
    },
    {
        'id':        'corridor_forcing',
        'label':     'Zangezur / TRIPP corridor forcing or armed-clash resumption',
        'vector':    'armenia_corridor',
        'breach':    4, 'approach': 3, 'severity': 5,
        'icon':      ICON_CORRIDOR,
        'precedent': 'Anchored to the 2020 war, the Sep 2023 Karabakh takeover, and Tehran\'s standing "no border change" red line over Syunik.',
    },
    {
        'id':        'israel_overt',
        'label':     'Israel platform / basing made overt (Iran casus belli)',
        'vector':    'israel_axis',
        'breach':    4, 'approach': 3, 'severity': 4,
        'icon':      ICON_ISRAEL,
        'compound_vector': 'iran_friction',   # only fires when Iran friction is also live (>=3)
        'compound_min':    3,
        'precedent': 'Consistent with recurring Iranian accusations that Baku hosts an Israeli intelligence / strike platform.',
    },
]


# ============================================
# HISTORICAL PRECEDENTS (matched when the relevant wheel is elevated)
# ============================================
HISTORICAL_PRECEDENTS = [
    {
        'label':     'Black January (1990)',
        'vectors':   ['russia_rupture', 'domestic_legitimacy'],
        'min_level': 4,
        'note':      'Soviet crackdown on Baku - the historical floor of Azerbaijani distrust of Moscow.',
    },
    {
        'label':     'Second Karabakh War (2020)',
        'vectors':   ['armenia_corridor'],
        'min_level': 3,
        'note':      '44-day war that reset the South-Caucasus balance in Baku\'s favor and put the corridor on the table.',
    },
    {
        'label':     'Karabakh takeover + Armenian exodus (Sep 2023)',
        'vectors':   ['armenia_corridor'],
        'min_level': 4,
        'note':      'One-day operation ending the enclave; the precedent for a fait-accompli forcing move.',
    },
    {
        'label':     'AZAL downing (Dec 2024)',
        'vectors':   ['russia_rupture'],
        'min_level': 3,
        'note':      'The rupture trigger - Russian fire downed the airliner; Moscow acknowledged responsibility in Apr 2026.',
    },
    {
        'label':     'TRIPP / "Trump Route" (Aug 2025)',
        'vectors':   ['armenia_corridor', 'russia_rupture', 'iran_friction'],
        'min_level': 3,
        'note':      'Western corridor insertion through Syunik - displaces Russia and Iran simultaneously; the four-wheel convergence object.',
    },
]


def _wheel_levels(scan_data):
    return {
        'turkey_axis':         scan_data.get('turkey_axis_level', 0) or 0,
        'russia_rupture':      scan_data.get('russia_rupture_level', 0) or 0,
        'iran_friction':       scan_data.get('iran_friction_level', 0) or 0,
        'israel_axis':         scan_data.get('israel_axis_level', 0) or 0,
        'armenia_corridor':    scan_data.get('armenia_corridor_level', 0) or 0,
        'domestic_legitimacy': scan_data.get('domestic_legitimacy_level', 0) or 0,
    }


# ============================================
# SO WHAT (estimative; built from the four-wheel composite)
# ============================================
def _build_so_what(scan_data):
    theatre_level = scan_data.get('theatre_level', 0) or 0
    theatre_score = scan_data.get('theatre_score', 0) or 0
    convergence   = scan_data.get('convergence_signal', '') or ''
    contested     = scan_data.get('contested_node_score', 0) or 0
    is_node       = scan_data.get('is_contested_node', False)
    active        = scan_data.get('active_wheels', []) or []

    v = _wheel_levels(scan_data)
    dominant, dom_level = max(v.items(), key=lambda kv: kv[1])
    ru, ir, am, tk, il = (v['russia_rupture'], v['iran_friction'],
                          v['armenia_corridor'], v['turkey_axis'], v['israel_axis'])

    # Baseline / quiet: absence stays honest.
    if theatre_level <= 1 and dom_level <= 1:
        return {
            'scenario':   'Baseline balancing posture',
            'assessment': ('Baku is running its four patron relationships at routine intensity this cycle; '
                           'no wheel is converging. Azerbaijan remains in active-balancer equilibrium. '
                           'Watch the russia_rupture and armenia_corridor wheels for first movement.'),
            'theatre_level':   theatre_level,
            'theatre_score':   theatre_score,
            'dominant_vector': dominant,
            'dominant_level':  dom_level,
        }

    if is_node:
        names = ', '.join(WHEEL_LABEL.get('%s' % w if w in WHEEL_LABEL else w,
                                          w.title()) for w in active)
        # active_wheels are short hub names (turkey/russia/iran/israel)
        names = ', '.join(w.title() for w in active)
        scenario   = 'Four-wheel contested node'
        assessment = ('Baku is working %d patron relationships at once (%s) - the active-balancer '
                      'signature under stress. When the wheels move together rather than in sequence, the '
                      'compound pattern is consistent with periods when Azerbaijan is hedging hard across all '
                      'fronts. Independent vectors stacking on the same window; the reader completes the inference.'
                      % (contested, names))
    elif ru >= 4:
        scenario   = 'Acute Baku-Moscow rupture'
        assessment = ('The Russia wheel is at crisis pitch - recall, strike, or detention signaling - consistent '
                      'with the post-AZAL trajectory of calculated insulation rather than realignment. Turkey-axis '
                      'and Ukraine-cooperation reads are the lead corroborants.')
    elif ru >= 3 and tk >= 2:
        scenario   = 'Russia rupture as Ankara patronage firms'
        assessment = ('Moscow decoupling is deepening while the Turkey axis is active - the pattern consistent with '
                      'Baku rebalancing west under Ankara cover. Watch whether the Ukraine-cooperation track tracks alongside.')
    elif ir >= 3 and il >= 2:
        scenario   = 'The Baku triangle is live'
        assessment = ('Iran friction is tracking Israel-axis intensity - drills, platform accusations, or arms/energy '
                      'signaling - the compound that historically precedes Iranian border posturing framed against the '
                      'Baku-Jerusalem relationship.')
    elif am >= 4:
        scenario   = 'Corridor forcing / clash risk'
        assessment = ('The Armenia / corridor wheel is at confrontation level - unilateral Zangezur forcing or '
                      'armed-clash signaling, consistent with the 2020 and Sep-2023 fait-accompli precedents and '
                      'Tehran\'s standing red line over Syunik.')
    elif am >= 3:
        scenario   = 'Corridor track elevated'
        assessment = ('Zangezur / TRIPP corridor activity is elevated - the four-wheel convergence object is warm. '
                      'Corridor moves displace Russia and Iran simultaneously, so this wheel tends to pull the others.')
    elif tk >= 3:
        scenario   = 'Turkey axis intensifying'
        assessment = ('The Ankara-Baku alignment wheel is intensifying - pact, defense, or corridor-patronage signaling '
                      'consistent with the "one nation, two states" tempo. Read alongside the Russia wheel for the rebalancing vector.')
    else:
        scenario   = 'Elevated four-wheel activity'
        assessment = ('Baku\'s balancing activity is elevated, led by the %s wheel. No multi-wheel convergence yet; '
                      'watch for russia_rupture or armenia_corridor to stack with a second wheel.' % WHEEL_LABEL.get(dominant, dominant))

    if convergence:
        assessment = assessment + ' Convergence read: ' + convergence

    return {
        'scenario':        scenario,
        'assessment':      assessment,
        'theatre_level':   theatre_level,
        'theatre_score':   theatre_score,
        'dominant_vector': dominant,
        'dominant_level':  dom_level,
    }


# ============================================
# RED LINES + HISTORICAL
# ============================================
def _check_red_lines(scan_data):
    v = _wheel_levels(scan_data)
    triggered = []
    for rl in RED_LINES:
        lvl = v.get(rl['vector'], 0)
        # Compound red lines require a second wheel to be live.
        if rl.get('compound_vector'):
            if v.get(rl['compound_vector'], 0) < rl.get('compound_min', 99):
                continue
        status = None
        if lvl >= rl['breach']:
            status = 'BREACHED'
        elif lvl >= rl['approach']:
            status = 'APPROACHING'
        if status:
            triggered.append({
                'id':        rl['id'],
                'label':     rl['label'],
                'status':    status,
                'severity':  rl['severity'],
                'vector':    rl['vector'],
                'level':     lvl,
                'icon':      rl['icon'],
                'precedent': rl['precedent'],
            })
    breached    = [t for t in triggered if t['status'] == 'BREACHED']
    approaching = [t for t in triggered if t['status'] == 'APPROACHING']
    highest = max([t['severity'] for t in breached], default=0)
    return {
        'triggered':         triggered,
        'breached_count':    len(breached),
        'approaching_count': len(approaching),
        'highest_severity':  highest,
    }


def _match_historical(scan_data):
    v = _wheel_levels(scan_data)
    matches = []
    for p in HISTORICAL_PRECEDENTS:
        if any(v.get(vec, 0) >= p['min_level'] for vec in p['vectors']):
            matches.append({'label': p['label'], 'note': p['note'], 'vectors': p['vectors']})
    return matches[:4]


# ============================================
# MAIN ENTRY
# ============================================
def interpret_signals(scan_data):
    """Main entry. Returns the heavy-interpreter contract: so_what + real
    red_lines + historical_matches + a forward-compatible rumint stub."""
    try:
        so_what    = _build_so_what(scan_data)
        red_lines  = _check_red_lines(scan_data)
        historical = _match_historical(scan_data)
        return {
            'so_what':             so_what,
            'red_lines':           red_lines,
            'historical_matches':  historical,
            'rumint':              {'active': False, 'band': 'off', 'label': '',
                                    'driver': '', 'framing': 0, 'specificity': 0,
                                    'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0',
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print('[Azerbaijan Interpreter] Error: %s' % str(e)[:120])
        return {
            'so_what':            {'scenario': 'Interpreter error', 'assessment': str(e)[:200]},
            'red_lines':          {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'historical_matches': [],
            'rumint':             {'active': False, 'band': 'off', 'label': '',
                                   'driver': '', 'framing': 0, 'specificity': 0,
                                   'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0',
            'error':              str(e)[:200],
        }


# ============================================
# TOP SIGNALS (canonical schema for BLUF / GPI / card)
# ============================================
def build_top_signals(scan_data):
    """Canonical top_signals[]: priority / category / theatre / level / icon /
    color / short_text / long_text. Sorted descending by priority."""
    signals = []
    FLAG = AZ_FLAG

    interp    = scan_data.get('interpretation', {}) or {}
    red_lines = interp.get('red_lines', {}) or {}

    theatre_level = scan_data.get('theatre_level', 0) or 0
    theatre_score = scan_data.get('theatre_score', 0) or 0

    tk = scan_data.get('turkey_axis_level', 0) or 0
    ru = scan_data.get('russia_rupture_level', 0) or 0
    ir = scan_data.get('iran_friction_level', 0) or 0
    il = scan_data.get('israel_axis_level', 0) or 0
    am = scan_data.get('armenia_corridor_level', 0) or 0
    contested  = scan_data.get('contested_node_score', 0) or 0
    is_node    = scan_data.get('is_contested_node', False)
    active     = scan_data.get('active_wheels', []) or []
    convergence_signal = scan_data.get('convergence_signal', '') or ''

    # ----- 1. Red lines (real detection) -----
    rl_triggered = red_lines.get('triggered', []) or []
    breached    = [r for r in rl_triggered if isinstance(r, dict) and r.get('status') == 'BREACHED']
    approaching = [r for r in rl_triggered if isinstance(r, dict) and r.get('status') == 'APPROACHING']
    for rl in sorted(breached, key=lambda r: r.get('severity', 0), reverse=True)[:3]:
        label = rl.get('label', 'Red line')
        signals.append({
            'priority':   12 + rl.get('severity', 0), 'category': 'red_line_breached', 'theatre': 'azerbaijan',
            'level':      max(theatre_level, 4), 'icon': rl.get('icon', ICON_SIREN), 'color': '#dc2626',
            'short_text': '%s AZERBAIJAN: BREACH - %s' % (FLAG, label[:55]),
            'long_text':  'AZERBAIJAN red line breached: %s. %s' % (label, rl.get('precedent', '')),
        })
    for rl in approaching[:2]:
        label = rl.get('label', 'Red line')
        signals.append({
            'priority':   9, 'category': 'red_line_approaching', 'theatre': 'azerbaijan',
            'level':      theatre_level, 'icon': ICON_ORANGE, 'color': '#f97316',
            'short_text': '%s AZERBAIJAN: Approaching - %s' % (FLAG, label[:50]),
            'long_text':  'AZERBAIJAN approaching red line: %s. %s' % (label, rl.get('precedent', '')),
        })

    # ----- 2. Four-wheel contested node (the signature Azerbaijan signal) -----
    if is_node:
        names = ', '.join(w.title() for w in active)
        signals.append({
            'priority':   13, 'category': 'contested_node', 'theatre': 'azerbaijan',
            'level':      max(theatre_level, 3), 'icon': ICON_NODE, 'color': '#dc2626',
            'short_text': '%s AZERBAIJAN: Four-wheel node (%d/4)' % (FLAG, contested),
            'long_text':  ('AZERBAIJAN four-wheel contested node - %s active simultaneously on Baku. '
                           'Active-balancer signature under stress.' % names),
        })

    # ----- 3. Theatre-high -----
    if theatre_level >= 4:
        signals.append({
            'priority':   9 + theatre_level, 'category': 'theatre_high', 'theatre': 'azerbaijan',
            'level':      theatre_level, 'icon': ICON_RED,
            'color':      '#b91c1c' if theatre_level >= 5 else '#ef4444',
            'short_text': '%s AZERBAIJAN L%d - Acute balancing stress' % (FLAG, theatre_level),
            'long_text':  'AZERBAIJAN at L%d (score %d/100). Russia rupture L%d, corridor L%d.' % (theatre_level, theatre_score, ru, am),
        })
    elif theatre_level >= 3:
        signals.append({
            'priority':   8, 'category': 'theatre_high', 'theatre': 'azerbaijan',
            'level':      theatre_level, 'icon': ICON_ORANGE, 'color': '#f97316',
            'short_text': '%s AZERBAIJAN L%d - Elevated activity' % (FLAG, theatre_level),
            'long_text':  'AZERBAIJAN at L%d (score %d/100). Lead wheels: Russia L%d, Iran L%d, corridor L%d.' % (theatre_level, theatre_score, ru, ir, am),
        })

    # ----- 4. Russia rupture (the live wire) -----
    if ru >= 4:
        signals.append({
            'priority':   11, 'category': 'russia_rupture_high', 'theatre': 'azerbaijan',
            'level':      ru, 'icon': ICON_RUSSIA, 'color': '#b91c1c',
            'short_text': '%s AZERBAIJAN: Russia rupture L%d' % (FLAG, ru),
            'long_text':  'AZERBAIJAN-Russia rupture L%d - recall, strike, or detention signaling out of the post-AZAL trajectory.' % ru,
        })
    elif ru >= 3:
        signals.append({
            'priority':   8, 'category': 'russia_rupture_high', 'theatre': 'azerbaijan',
            'level':      ru, 'icon': ICON_RUSSIA, 'color': '#f97316',
            'short_text': '%s AZERBAIJAN: Russia friction L%d' % (FLAG, ru),
            'long_text':  'AZERBAIJAN-Russia decoupling L%d - calculated insulation from Moscow deepening.' % ru,
        })

    # ----- 5. Armenia / corridor (the convergence object) -----
    if am >= 4:
        signals.append({
            'priority':   10, 'category': 'corridor_high', 'theatre': 'azerbaijan',
            'level':      am, 'icon': ICON_CORRIDOR, 'color': '#dc2626',
            'short_text': '%s AZERBAIJAN: Corridor forcing L%d' % (FLAG, am),
            'long_text':  'AZERBAIJAN Zangezur / TRIPP corridor L%d - unilateral forcing or clash signaling; displaces Russia and Iran at once.' % am,
        })
    elif am >= 3:
        signals.append({
            'priority':   7, 'category': 'corridor_high', 'theatre': 'azerbaijan',
            'level':      am, 'icon': ICON_CORRIDOR, 'color': '#8b5cf6',
            'short_text': '%s AZERBAIJAN: Corridor track L%d' % (FLAG, am),
            'long_text':  'AZERBAIJAN corridor track L%d - Zangezur / TRIPP activity elevated; the four-wheel convergence object is warm.' % am,
        })

    # ----- 6. Iran friction -----
    if ir >= 4:
        signals.append({
            'priority':   10, 'category': 'iran_friction_high', 'theatre': 'azerbaijan',
            'level':      ir, 'icon': ICON_IRAN, 'color': '#dc2626',
            'short_text': '%s AZERBAIJAN: Iran friction L%d' % (FLAG, ir),
            'long_text':  'AZERBAIJAN-Iran friction L%d - border drills or platform accusations framed against the Baku-Jerusalem axis.' % ir,
        })
    elif ir >= 3:
        signals.append({
            'priority':   7, 'category': 'iran_friction_high', 'theatre': 'azerbaijan',
            'level':      ir, 'icon': ICON_IRAN, 'color': '#f97316',
            'short_text': '%s AZERBAIJAN: Iran friction L%d' % (FLAG, ir),
            'long_text':  'AZERBAIJAN-Iran friction L%d - elevated border / rhetoric tension with Tehran.' % ir,
        })

    # ----- 7. Turkey axis -----
    if tk >= 4:
        signals.append({
            'priority':   8, 'category': 'turkey_axis_high', 'theatre': 'azerbaijan',
            'level':      tk, 'icon': ICON_TURKEY, 'color': '#dc2626',
            'short_text': '%s AZERBAIJAN: Turkey axis L%d' % (FLAG, tk),
            'long_text':  'AZERBAIJAN-Turkey axis L%d - major pact or defense signal under the "one nation, two states" frame.' % tk,
        })
    elif tk >= 3:
        signals.append({
            'priority':   6, 'category': 'turkey_axis_high', 'theatre': 'azerbaijan',
            'level':      tk, 'icon': ICON_TURKEY, 'color': '#f59e0b',
            'short_text': '%s AZERBAIJAN: Turkey axis L%d' % (FLAG, tk),
            'long_text':  'AZERBAIJAN-Turkey alignment L%d - Ankara-Baku coordination intensifying.' % tk,
        })

    # ----- 8. Israel axis -----
    if il >= 4:
        signals.append({
            'priority':   8, 'category': 'israel_axis_high', 'theatre': 'azerbaijan',
            'level':      il, 'icon': ICON_ISRAEL, 'color': '#0ea5e9',
            'short_text': '%s AZERBAIJAN: Israel axis L%d' % (FLAG, il),
            'long_text':  'AZERBAIJAN-Israel axis L%d - major arms or energy signaling on the Iran-facing relationship.' % il,
        })
    elif il >= 3:
        signals.append({
            'priority':   6, 'category': 'israel_axis_high', 'theatre': 'azerbaijan',
            'level':      il, 'icon': ICON_ISRAEL, 'color': '#0ea5e9',
            'short_text': '%s AZERBAIJAN: Israel axis L%d' % (FLAG, il),
            'long_text':  'AZERBAIJAN-Israel axis L%d - arms / oil activity on the quiet Iran-facing relationship.' % il,
        })

    # ----- 9. Convergence flag (only if not already covered by the node) -----
    if convergence_signal and not is_node:
        signals.append({
            'priority':   7, 'category': 'convergence_signal', 'theatre': 'azerbaijan',
            'level':      theatre_level, 'icon': ICON_ANTENNA, 'color': '#f59e0b',
            'short_text': '%s AZERBAIJAN: %s' % (FLAG, convergence_signal[:55]),
            'long_text':  'AZERBAIJAN convergence: %s' % convergence_signal,
        })

    signals.sort(key=lambda s: s['priority'], reverse=True)
    return signals
