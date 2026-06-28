"""
Asifah Analytics - Greece Signal Interpreter (analyst layer)
v1.0.0 - June 2026  |  Europe backend

Reads the raw vector levels + cross-tracker corroboration emitted by
rhetoric_tracker_greece.py and produces the estimative analyst read:
so_what (scenario + assessment + synthesized BLUF), canonical top_signals,
and a lean red-lines stub (heavy tripwire tier deferred, Cyprus pattern).

DOCTRINE: convergence, not prediction. Estimative voice only --
"consistent with / historically precedes / likely indicates", precedent-anchored.
No probabilities, no dates, no "will". The reader completes the inference.

The defining current condition is the MANAGED DETENTE: a live Greece-Turkey
diplomatic track (High-Level Cooperation Council, confidence-building measures)
running alongside FROZEN disputes (EEZ delimitation, the casus belli). The
interpreter weaves that state through every read.

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

from datetime import datetime, timezone

# Human-readable vector labels (kills snake_case in prose)
VECTOR_LABEL = {
    'turkey_axis':         'Turkey axis',
    'migration_frontline': 'Migration frontline',
    'domestic_pressure':   'Domestic pressure',
    'eu_anchor':           'EU anchor',
    'nato_us':             'NATO / US posture',
    'regional_alignment':  'Regional alignment',
}

VECTORS = list(VECTOR_LABEL.keys())
PRESSURE_VECTORS = ['turkey_axis', 'migration_frontline', 'domestic_pressure']
ANCHOR_VECTORS   = ['eu_anchor', 'nato_us', 'regional_alignment']

LADDER_WORD = {
    0: 'Baseline', 1: 'Rhetoric', 2: 'Pressure',
    3: 'Crisis', 4: 'Confrontation', 5: 'Rupture',
}


def _levels(scan_data):
    return {v: int(scan_data.get(f'{v}_level', 0) or 0) for v in VECTORS}


def _build_bluf(dominant, dom_lvl, dip, military, migration):
    """One-line analyst headline. Plain language, names the lead read + the detente state."""
    lead = VECTOR_LABEL.get(dominant, dominant)
    word = LADDER_WORD.get(dom_lvl, 'Baseline')

    if dom_lvl == 0:
        head = 'Greece is at managed-calm baseline across all six vectors'
    else:
        head = f'{lead} leads at {word} (L{dom_lvl})'

    tail = ''
    if dominant == 'turkey_axis' and dom_lvl >= 1:
        if military.get('active'):
            tail = '; Aegean rhetoric is corroborated by elevated military posture'
        else:
            tail = '; declaratory, with the detente track still containing it'
    elif dominant == 'migration_frontline' and dom_lvl >= 1 and migration.get('active'):
        tail = '; tracking the live Libya-to-Crete arrivals picture'
    elif dip.get('framework_active'):
        tail = '; the Greece-Turkey detente track is active'

    return head + tail + '.'


def _build_so_what(scan_data):
    levels  = _levels(scan_data)
    dominant = max(levels, key=lambda k: levels[k]) if levels else 'turkey_axis'
    dom_lvl  = levels.get(dominant, 0)
    tk       = levels['turkey_axis']

    military  = scan_data.get('military_corroboration', {}) or {}
    migration = scan_data.get('migration_corroboration', {}) or {}
    dip       = scan_data.get('diplomatic_track', {}) or {}
    detente_active = bool(dip.get('framework_active'))

    active_pressures = [v for v in PRESSURE_VECTORS if levels[v] >= 2]

    # ---- scenario + assessment (estimative, precedent-anchored) ----
    if dom_lvl == 0:
        scenario = 'Managed-calm baseline'
        assessment = (
            'Greece is running its primary Turkey axis and its EU/NATO anchors at routine '
            'intensity this cycle. The posture is consistent with the managed detente that has '
            'held since 2023 -- a live diplomatic track alongside frozen disputes (EEZ '
            'delimitation, the casus belli) that remain unresolved rather than settled. Absent '
            'a fresh trigger, this is baseline, not de-escalation.'
        )
    elif dominant == 'turkey_axis':
        if military.get('active'):
            scenario = 'Aegean friction -- operationally corroborated'
            assessment = (
                'Turkey-axis rhetoric is the lead signal AND it is corroborated by elevated '
                'military posture in the Aegean / East-Med theatre. That pairing -- declaratory '
                'friction plus operational backing -- is the pattern that has historically '
                'preceded the sharper Greece-Turkey standoffs (the Oruc Reis cycle being the '
                'reference). The casus belli and a drillship-into-EEZ move remain the tripwires '
                'that would carry this out of the managed-calm band.'
            )
        else:
            scenario = 'Aegean friction -- declaratory'
            assessment = (
                'Turkey-axis rhetoric is elevated but is not yet corroborated by a matching '
                'military posture, which is consistent with friction inside the managed-detente '
                'band rather than a break from it. The diplomatic track '
                + ('remains active' if detente_active else 'is the variable to watch')
                + '; the frozen EEZ / casus-belli file is where any escalation would surface first.'
            )
    elif dominant == 'migration_frontline':
        scenario = 'Migration-frontline pressure'
        assessment = (
            'The migration frontline is the lead pressure this cycle'
            + (', and the live arrivals sensor corroborates it' if migration.get('active') else '')
            + '. The analytically distinctive thread is the Libya-to-Crete corridor displacing the '
            'Turkey-cooperative Aegean route: that makes Greece the downstream arrival node of the '
            'Libya departure hub, and shifts EU-pact leverage onto Athens. Engineered surges via '
            'the Evros land border (the 2020 precedent) are the lever that would couple this back '
            'to the Turkey axis.'
        )
    elif dominant == 'domestic_pressure':
        scenario = 'Internal political pressure'
        assessment = (
            'Domestic pressure is the lead signal -- the Tempi accountability file, the Predator / '
            'EYP surveillance scandal, and cost-of-living strain against a governing party whose '
            'polling has slid. The estimative read is that internal pressure of this kind '
            'historically narrows a government\'s room for maneuver abroad; a Greece absorbed by a '
            'domestic accountability crisis is a Greece with less bandwidth for the Aegean file.'
        )
    else:
        scenario = 'Anchor activity -- ' + VECTOR_LABEL.get(dominant, dominant)
        assessment = (
            VECTOR_LABEL.get(dominant, dominant) + ' is the most active vector this cycle. '
            'Anchor activity is read as standing rather than strain: it reflects how firmly Greece '
            'is embedded in its EU / NATO / Eastern-Mediterranean alignments, which is the '
            'counterweight to the Turkey axis. The EU removal from the macroeconomic-imbalances '
            'list and the East-Med "3+1" alignment are the structural backing behind Athens\' '
            'position.'
        )

    # Weave the detente state in when it isn't already the headline
    if detente_active and dominant != 'turkey_axis' and dom_lvl > 0:
        assessment += (' The Greece-Turkey detente track remains active in the background, which '
                       'is consistent with the Aegean file staying contained while other vectors carry the load.')

    if len(active_pressures) >= 2:
        assessment += (' Note the breadth: ' + str(len(active_pressures)) +
                       ' pressure vectors are simultaneously active, which reads as compound strain '
                       'rather than a single hot file.')

    bluf = _build_bluf(dominant, dom_lvl, dip, military, migration)

    return {
        'scenario':         scenario,
        'assessment':       assessment,
        'dominant_vector':  dominant,
        'dominant_level':   dom_lvl,
        'bluf':             bluf,
        'detente_active':   detente_active,
    }


def _check_red_lines(scan_data):
    """Lean stub -- the heavy Greece tripwire tier (casus belli activation, drillship-into-EEZ
    under escort, militarized airspace incident, detente collapse, engineered Evros surge) is
    deferred to a later slice. Absence-honest: empty triggered list -> the card stays hidden."""
    return {
        'triggered':         [],
        'breached_count':    0,
        'approaching_count': 0,
        'highest_severity':  0,
        'note':              'Heavy red-line tier deferred (v1 lean). Tripwires tracked in prose.',
    }


def interpret_signals(scan_data):
    """Main entry -- returns the lean analyst contract."""
    try:
        so_what   = _build_so_what(scan_data)
        red_lines = _check_red_lines(scan_data)
        return {
            'so_what':             so_what,
            'red_lines':           red_lines,
            'historical_matches':  [],
            'rumint':              {'active': False, 'band': 'off', 'label': '',
                                    'driver': '', 'framing': 0, 'specificity': 0,
                                    'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0',
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print('[Greece Interpreter] Error: %s' % str(e)[:120])
        return {
            'so_what':            {'scenario': 'Interpreter error', 'assessment': str(e)[:200],
                                   'dominant_vector': 'turkey_axis', 'dominant_level': 0, 'bluf': ''},
            'red_lines':          {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'historical_matches': [],
            'rumint':             {'active': False, 'band': 'off', 'label': '', 'driver': '',
                                   'framing': 0, 'specificity': 0, 'reception': 0, 'corroboration': 0},
            'interpreter_version': '1.0.0',
            'error':              str(e)[:200],
        }


def build_top_signals(scan_data):
    """Canonical top_signals[] (short_text / long_text / priority / category).
    Drives the stability-page rhetoric card + regional BLUF + GPI consumers."""
    signals = []
    levels   = _levels(scan_data)
    military  = scan_data.get('military_corroboration', {}) or {}
    migration = scan_data.get('migration_corroboration', {}) or {}
    dip       = scan_data.get('diplomatic_track', {}) or {}
    actors    = scan_data.get('actors', {}) or {}
    pri = 1

    # 1. Hottest vector with an article behind it
    dominant = max(levels, key=lambda k: levels[k]) if levels else None
    if dominant and levels[dominant] >= 1:
        a = actors.get(dominant, {})
        top_art = (a.get('top_articles') or [{}])[0]
        signals.append({
            'priority':   pri,
            'short_text': f'{VECTOR_LABEL[dominant]} at {LADDER_WORD[levels[dominant]]} '
                          f'(L{levels[dominant]})',
            'long_text':  (top_art.get('title') or a.get('description') or
                           VECTOR_LABEL[dominant] + ' is the lead vector this cycle.')[:200],
            'category':   dominant,
        }); pri += 1

    # 2. Military corroboration (the compound read)
    if military.get('active') and levels.get('turkey_axis', 0) >= 1:
        signals.append({
            'priority':   pri,
            'short_text': 'Aegean rhetoric corroborated by military posture',
            'long_text':  military.get('note', 'Elevated Turkish/Greek military posture in the '
                                               'Aegean / East-Med theatre.')[:200],
            'category':   'military_corroboration',
        }); pri += 1

    # 3. Migration sensor corroboration
    if migration.get('active') and levels.get('migration_frontline', 0) >= 1:
        signals.append({
            'priority':   pri,
            'short_text': 'Migration rhetoric tracking live arrivals',
            'long_text':  (migration.get('note', '') or
                           'Live Greece arrivals sensor is reporting flow.')[:200],
            'category':   'migration_frontline',
        }); pri += 1

    # 4. Diplomatic off-ramp
    if dip.get('framework_active'):
        signals.append({
            'priority':   pri,
            'short_text': f'Diplomatic track: {dip.get("scenario", "active")}',
            'long_text':  ('Greece-Turkey detente track active -- High-Level Cooperation Council / '
                           'confidence-building measures running alongside the frozen disputes.')[:200],
            'category':   'diplomatic_track',
        }); pri += 1

    return signals[:5]
