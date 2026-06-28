"""
Asifah Analytics - Cyprus Signal Interpreter (LEAN tier)
v1.0.0 - June 2026

Companion to rhetoric_tracker_cyprus.py (Dial 2, inverted + vectored).

This is the LEAN interpreter tier. It provides exactly what makes the Cyprus
rhetoric tracker an analyst-layer participant:

  * build_top_signals(scan_data)  -> canonical top_signals[] for the Gold
                                     Standard rhetoric card, the Europe regional
                                     BLUF, and the GPI rollup.
  * interpret_signals(scan_data)  -> estimative So-What read, plus forward-
                                     compatible (empty) red_lines / historical /
                                     rumint stubs.

DEFERRED to the HEAVY tier (build when rhetoric-cyprus.html is built):
  * RED_LINES scoring (e.g. Turkish troop surge past TRNC baseline, drillship
    into a licensed EEZ block under naval escort, unilateral Varosha annexation,
    formal settlement-talk collapse, Greece-Turkey casus belli).
  * HISTORICAL_PRECEDENTS matching (1974 invasion, 1983 TRNC UDI, 2004 Annan
    Plan rejection, 2017 Crans-Montana collapse, 2018 ENI/Saipem drillship
    blockade, 2020 Varosha reopening).
  * RUMINT scoring.

Doctrine: estimative voice only ("consistent with / historically precedes /
likely indicates"); no probabilities, no dates, no "will". Absence stays honest.

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

from datetime import datetime, timezone

# Cyprus flag (unicode escape -> ASCII-safe source, emoji at runtime)
CYPRUS_FLAG = '\U0001f1e8\U0001f1fe'   # CY


# ============================================
# VECTOR LABELS (plain-language; never leak snake_case into prose)
# ============================================
VECTOR_LABEL = {
    'turkey_posture':   'Turkish posture',
    'eez_maritime':     'EEZ / maritime',
    'green_line':       'Green Line',
    'trnc_politics':    'TRNC politics',
    'settlement_track': 'Settlement track',
}

LADDER_WORD = {0: 'Baseline', 1: 'Rhetoric', 2: 'Pressure',
               3: 'Crisis', 4: 'Confrontation', 5: 'Rupture'}


def _build_bluf(vectors, dominant, dom_level, convergence):
    """Plain-language one-line synthesis for the BLUF strip / Gold Standard
    card. Names the lead inbound vector, its intensity, and the convergence
    state. Cyprus is inbound-pressure framed. Estimative, no forecast."""
    active = sorted([(k, lv) for k, lv in vectors.items() if lv >= 2],
                    key=lambda kv: -kv[1])
    if dom_level <= 1:
        return ('Inbound pressure on the Cyprus status quo at baseline; the '
                'Republic of Cyprus holds as the calm anchor, no vector converging.')
    lead = '%s leads at %s (L%d)' % (
        VECTOR_LABEL.get(dominant, dominant),
        LADDER_WORD.get(dom_level, 'L%d' % dom_level), dom_level)
    if len(active) >= 2:
        sk, slv = active[1]
        return ('%s; %s also live at %s (L%d). Two inbound vectors active on the division.'
                % (lead, VECTOR_LABEL.get(sk, sk),
                   LADDER_WORD.get(slv, 'L%d' % slv), slv))
    return '%s; other inbound vectors quiet - no multi-vector convergence yet.' % lead


# ============================================
# SO WHAT (estimative; built from the vectored composite)
# ============================================
def _build_so_what(scan_data):
    """Estimative So-What from the dominant vector + convergence read."""
    theatre_level = scan_data.get('theatre_level', 0) or 0
    theatre_score = scan_data.get('theatre_score', 0) or 0
    convergence   = scan_data.get('convergence_signal', '') or ''

    vectors = {
        'turkey_posture':   scan_data.get('turkey_posture_level', 0) or 0,
        'eez_maritime':     scan_data.get('eez_level', 0) or 0,
        'green_line':       scan_data.get('green_line_level', 0) or 0,
        'trnc_politics':    scan_data.get('trnc_level', 0) or 0,
        'settlement_track': scan_data.get('settlement_level', 0) or 0,
    }
    dominant, dom_level = max(vectors.items(), key=lambda kv: kv[1])

    bluf = _build_bluf(vectors, dominant, dom_level, convergence)

    tp = vectors['turkey_posture']
    ez = vectors['eez_maritime']
    gl = vectors['green_line']
    st = vectors['settlement_track']

    # Baseline / quiet: absence stays honest, no manufactured story.
    if theatre_level <= 1 and dom_level <= 1:
        return {
            'scenario':   'Baseline division posture',
            'assessment': ('Inbound pressure on the Cyprus status quo is at baseline this cycle; '
                           'no vector is converging. The Republic of Cyprus (Dial 1) remains the '
                           'calm anchor. Watch the Turkish posture and EEZ / maritime vectors for first movement.'),
            'dominant_vector': dominant,
            'dominant_level':  dom_level,
            'bluf':            bluf,
        }

    if tp >= 4 and (ez >= 2 or gl >= 2):
        scenario = 'Turkish pressure converging with division friction'
        assessment = ('Acute inbound Turkish posture is co-occurring with maritime and/or buffer-zone '
                      'friction - the compound pattern consistent with periods of acute division stress. '
                      'Independent vectors stacking on the same window; the reader completes the inference.')
    elif tp >= 4:
        scenario = 'Acute Turkish two-state / coercion posture'
        assessment = ('Inbound Turkish posture toward Cyprus is at crisis level - two-state framing, troop '
                      'or drilling signaling - consistent with the language Ankara has historically used '
                      'ahead of unilateral moves on the island. EEZ and buffer-zone vectors are the lead reads.')
    elif ez >= 4:
        scenario = 'EEZ standoff'
        assessment = ('Maritime / EEZ friction is at confrontation level - drillship, NAVTEX, or delimitation '
                      'signaling consistent with pre-confrontation hydrocarbon posturing in the Eastern Med.')
    elif gl >= 4:
        scenario = 'Buffer-zone friction'
        assessment = ('Green Line / UNFICYP friction is at confrontation level - movement or incident signaling '
                      'along the ceasefire line, consistent with localized division-line stress.')
    elif st >= 3:
        scenario = 'Settlement-track hardening'
        assessment = ('Settlement-track signaling is collapse-biased this cycle - deadlock, two-state push, or '
                      'walkout language that historically precedes further entrenchment of the frozen division.')
    else:
        scenario = 'Elevated inbound division pressure'
        assessment = ('Inbound pressure on the Cyprus status quo is elevated, led by the %s vector. '
                      'No multi-vector convergence yet; watch for the Turkish posture vector to stack with EEZ '
                      'or buffer-zone friction.' % VECTOR_LABEL.get(dominant, dominant))

    if convergence:
        assessment = assessment + ' Convergence read: ' + convergence

    return {
        'scenario':        scenario,
        'assessment':      assessment,
        'theatre_level':   theatre_level,
        'theatre_score':   theatre_score,
        'dominant_vector': dominant,
        'dominant_level':  dom_level,
        'bluf':            bluf,
    }


# ============================================
# MAIN ENTRY (lean: So-What + forward-compatible stubs)
# ============================================
def interpret_signals(scan_data):
    """
    Main entry point. Called from rhetoric_tracker_cyprus.py with full scan_data.
    Returns the same contract as the heavy interpreters so callers don't branch:
    so_what + (empty) red_lines / historical_matches / rumint stubs.
    """
    try:
        so_what = _build_so_what(scan_data)
        return {
            'so_what':             so_what,
            'red_lines': {
                'triggered':         [],
                'breached_count':    0,
                'approaching_count': 0,
                'highest_severity':  0,
            },
            'historical_matches':  [],
            'rumint':              {'active': False, 'band': 'off', 'label': '',
                                    'driver': '', 'framing': 0, 'specificity': 0,
                                    'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0-lean',
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print('[Cyprus Interpreter] Error: %s' % str(e)[:120])
        return {
            'so_what':            {'scenario': 'Interpreter error', 'assessment': str(e)[:200]},
            'red_lines':          {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'historical_matches': [],
            'rumint':             {'active': False, 'band': 'off', 'label': '',
                                   'driver': '', 'framing': 0, 'specificity': 0,
                                   'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0-lean',
            'error':              str(e)[:200],
        }


# ============================================
# TOP SIGNALS (canonical schema for BLUF / GPI / card)
# ============================================
def build_top_signals(scan_data):
    """
    Build Cyprus's top_signals[] for BLUF / GPI / Gold Standard card consumption.
    Canonical schema: priority / category / theatre / level / icon / color /
    short_text / long_text. Driven by the vectored composite; the red-line
    section no-ops until the heavy interpreter tier is built. Sorted descending.
    """
    signals = []

    interp    = scan_data.get('interpretation', {}) or {}
    red_lines = interp.get('red_lines', {}) or {}

    theatre_level = scan_data.get('theatre_level', 0) or 0
    theatre_score = scan_data.get('theatre_score', 0) or 0

    tp = scan_data.get('turkey_posture_level', 0) or 0
    ez = scan_data.get('eez_level', 0) or 0
    gl = scan_data.get('green_line_level', 0) or 0
    tr = scan_data.get('trnc_level', 0) or 0
    st = scan_data.get('settlement_level', 0) or 0
    convergence_signal = scan_data.get('convergence_signal', '') or ''

    FLAG = CYPRUS_FLAG

    # ----- 1. Red lines (no-op until heavy tier; forward-compatible) -----
    rl_triggered = red_lines.get('triggered', []) or []
    breached    = [r for r in rl_triggered if isinstance(r, dict) and r.get('status') == 'BREACHED']
    approaching = [r for r in rl_triggered if isinstance(r, dict) and r.get('status') == 'APPROACHING']
    for rl in breached[:3]:
        label = rl.get('label', 'Division red line')
        signals.append({
            'priority':   12, 'category': 'red_line_breached', 'theatre': 'cyprus',
            'level':      max(theatre_level, 4), 'icon': rl.get('icon', '\U0001f6a8'), 'color': '#dc2626',
            'short_text': '%s CYPRUS: BREACH - %s' % (FLAG, label[:55]),
            'long_text':  'CYPRUS division red line breached: %s' % label,
        })
    for rl in approaching[:2]:
        label = rl.get('label', 'Division red line')
        signals.append({
            'priority':   8, 'category': 'red_line_approaching', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f7e0', 'color': '#f97316',
            'short_text': '%s CYPRUS: Approaching - %s' % (FLAG, label[:50]),
            'long_text':  'CYPRUS approaching red line: %s' % label,
        })

    # ----- 2. Theatre-high -----
    if theatre_level >= 4:
        signals.append({
            'priority':   9 + theatre_level, 'category': 'theatre_high', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f534',
            'color':      '#dc2626' if theatre_level >= 5 else '#ef4444',
            'short_text': '%s CYPRUS L%d - Division crisis' % (FLAG, theatre_level),
            'long_text':  'CYPRUS at L%d division crisis (score %d/100). Inbound Turkish posture L%d.' % (theatre_level, theatre_score, tp),
        })
    elif theatre_level >= 3:
        signals.append({
            'priority':   8, 'category': 'theatre_high', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f7e0', 'color': '#f97316',
            'short_text': '%s CYPRUS L%d - Division pressure' % (FLAG, theatre_level),
            'long_text':  'CYPRUS at L%d division pressure (score %d/100). Turkey posture L%d, EEZ L%d.' % (theatre_level, theatre_score, tp, ez),
        })

    # ----- 3. Turkey posture (the KEY inbound signal; also the spoke feed) -----
    if tp >= 4:
        signals.append({
            'priority':   11, 'category': 'turkey_posture_high', 'theatre': 'cyprus',
            'level':      tp, 'icon': '\U0001f1f9\U0001f1f7', 'color': '#dc2626',
            'short_text': '%s CYPRUS: Turkish posture L%d' % (FLAG, tp),
            'long_text':  'CYPRUS inbound Turkish posture L%d - two-state framing, troop or drilling signaling from Ankara.' % tp,
        })
    elif tp >= 3:
        signals.append({
            'priority':   8, 'category': 'turkey_posture_high', 'theatre': 'cyprus',
            'level':      tp, 'icon': '\U0001f1f9\U0001f1f7', 'color': '#f97316',
            'short_text': '%s CYPRUS: Turkish posture L%d' % (FLAG, tp),
            'long_text':  'CYPRUS inbound Turkish posture L%d - direct rhetoric from Ankara toward Cyprus.' % tp,
        })

    # ----- 4. EEZ / maritime -----
    if ez >= 4:
        signals.append({
            'priority':   10, 'category': 'eez_standoff', 'theatre': 'cyprus',
            'level':      ez, 'icon': '\U0001f6e2\ufe0f', 'color': '#dc2626',
            'short_text': '%s CYPRUS: EEZ standoff L%d' % (FLAG, ez),
            'long_text':  'CYPRUS maritime / EEZ friction L%d - drillship, NAVTEX, or delimitation signaling.' % ez,
        })
    elif ez >= 3:
        signals.append({
            'priority':   7, 'category': 'eez_friction', 'theatre': 'cyprus',
            'level':      ez, 'icon': '\U0001f6e2\ufe0f', 'color': '#0ea5e9',
            'short_text': '%s CYPRUS: EEZ friction L%d' % (FLAG, ez),
            'long_text':  'CYPRUS EEZ friction L%d - hydrocarbon / maritime delimitation tension with Turkey.' % ez,
        })

    # ----- 5. Green Line / buffer zone -----
    if gl >= 4:
        signals.append({
            'priority':   9, 'category': 'green_line_high', 'theatre': 'cyprus',
            'level':      gl, 'icon': '\U0001f6a7', 'color': '#dc2626',
            'short_text': '%s CYPRUS: Buffer-zone incident L%d' % (FLAG, gl),
            'long_text':  'CYPRUS Green Line / buffer-zone friction L%d - movement or incident along the ceasefire line.' % gl,
        })
    elif gl >= 3:
        signals.append({
            'priority':   6, 'category': 'green_line_high', 'theatre': 'cyprus',
            'level':      gl, 'icon': '\U0001f6a7', 'color': '#3b82f6',
            'short_text': '%s CYPRUS: Green Line friction L%d' % (FLAG, gl),
            'long_text':  'CYPRUS Green Line / UNFICYP friction L%d - buffer-zone or crossing tension.' % gl,
        })

    # ----- 6. TRNC politics -----
    if tr >= 4:
        signals.append({
            'priority':   8, 'category': 'trnc_politics_high', 'theatre': 'cyprus',
            'level':      tr, 'icon': '\U0001f7e7', 'color': '#dc2626',
            'short_text': '%s CYPRUS: TRNC move L%d' % (FLAG, tr),
            'long_text':  'CYPRUS Turkish-Cypriot north L%d - Varosha, settler, or two-state signaling under Ankara grip.' % tr,
        })
    elif tr >= 3:
        signals.append({
            'priority':   5, 'category': 'trnc_politics_high', 'theatre': 'cyprus',
            'level':      tr, 'icon': '\U0001f7e7', 'color': '#f59e0b',
            'short_text': '%s CYPRUS: TRNC politics L%d' % (FLAG, tr),
            'long_text':  'CYPRUS Turkish-Cypriot north L%d - north elections, Tatar, or settler politics.' % tr,
        })

    # ----- 7. Settlement-track friction (collapse-biased) -----
    if st >= 3:
        signals.append({
            'priority':   6, 'category': 'settlement_friction', 'theatre': 'cyprus',
            'level':      st, 'icon': '\U0001f54a\ufe0f', 'color': '#8b5cf6',
            'short_text': '%s CYPRUS: Settlement track hardening L%d' % (FLAG, st),
            'long_text':  'CYPRUS settlement-track friction L%d - deadlock, two-state push, or walkout signaling.' % st,
        })

    # ----- 8. Convergence signal (semantic flag) -----
    if convergence_signal:
        signals.append({
            'priority':   7, 'category': 'convergence_signal', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f4e1', 'color': '#f59e0b',
            'short_text': '%s CYPRUS: %s' % (FLAG, convergence_signal[:55]),
            'long_text':  'CYPRUS convergence: %s' % convergence_signal,
        })

    signals.sort(key=lambda s: s['priority'], reverse=True)
    return signals
