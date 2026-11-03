"""
Asifah Analytics - Cyprus Signal Interpreter
v1.1.0 - November 3, 2026   (v1.0.0-lean June 2026)

v1.1.0 -- FROM LEAN TO EVIDENCE TIER
  * RED LINES now exist (they were deferred stubs), scored per article on the
    whole corpus with publisher counting (europe_evidence): BREACHED needs a
    breach phrase in 2+ outlets.
  * SETTLEMENT MOMENTUM green line. The settlement_track vector is collapse-
    biased by design; v1.0 had no way to see the opposite. Since Tufan
    Erhurman (pro-federation) won the north in Oct 2025, the live story is
    whether leader-level talks restart -- that is now read, not assumed.
  * Display-only partnership / threat vectors (israel_partnership,
    us_partnership, iran_hezbollah_threat) -- they are wheels on Cyprus, kept
    OUT of the division composite so Dial 2 stays a division gauge.
  * Spokes for turkey / israel / us / iran, thin read, top_indicator.

Companion to rhetoric_tracker_cyprus.py (Dial 2, inverted + vectored).

This is the LEAN interpreter tier. It provides exactly what makes the Cyprus
rhetoric tracker an analyst-layer participant:

  * build_top_signals(scan_data)  -> canonical top_signals[] for the Gold
                                     Standard rhetoric card, the Europe regional
                                     BLUF, and the GPI rollup.
  * interpret_signals(scan_data)  -> estimative So-What read, plus forward-
                                     compatible (empty) red_lines / historical /
                                     rumint stubs.

BUILT in v1.1.0: RED_LINES (troop surge, escorted drillship, unilateral Varosha
move, talks collapse, Greece-Turkey casus belli, Iran/Hizballah threat) --
each carries its precedent line.
STILL DEFERRED:
  * HISTORICAL_PRECEDENTS matching (1974 invasion, 1983 TRNC UDI, 2004 Annan
    Plan rejection, 2017 Crans-Montana collapse, 2018 ENI/Saipem drillship
    blockade, 2020 Varosha reopening).
  * RUMINT scoring.

Doctrine: estimative voice only ("consistent with / historically precedes /
likely indicates"); no probabilities, no dates, no "will". Absence stays honest.

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

from datetime import datetime, timezone

from europe_evidence import build_corpus, score_line, score_green, corpus_health

INTERPRETER_VERSION = '1.1.0'
THIN_MIN_ARTICLES = 25

# (id, label, severity, icon, precedent, breach phrases, approach phrases)
RED_LINES = [
    ('turkish_troop_surge', 'Turkish troop surge in the north', 4, '\U0001fa96',
     '1974 -- Turkish forces landed after the Athens-backed coup; ~35,000 troops have stayed since.',
     ['turkey sends troops to cyprus', 'additional turkish troops', 'turkish reinforcements northern cyprus',
      'turkey deploys troops to northern cyprus', 'turkish troop build-up cyprus'],
     ['turkish troops cyprus', 'turkish military northern cyprus', 'turkey military base northern cyprus',
      'drone base northern cyprus', 'gecitkale']),
    ('drillship_escort', 'Turkish drillship in a licensed block under escort', 4, '\U0001f6e2\ufe0f',
     '2018 -- Turkish warships turned back ENI\'s Saipem 12000 from Cyprus Block 3.',
     ['drillship escorted by turkish warships', 'turkish navy blocks drillship', 'warships block drillship',
      'turkish drillship in cyprus eez', 'turkish drillship in block'],
     ['turkish drillship', 'navtex cyprus', 'turkish navtex', 'seismic vessel cyprus', 'oruc reis', 'abdulhamid han']),
    ('varosha_unilateral', 'Unilateral move on Varosha', 3, '\U0001f3da\ufe0f',
     '2020 -- partial reopening of fenced-off Varosha drew a UN Security Council rebuke.',
     ['varosha reopened', 'reopening of varosha', 'varosha resettlement', 'further opening of varosha'],
     ['varosha settlers', 'varosha resettle', 'varosha opening', 'opening of varosha', 'maras opening']),
    ('talks_collapse', 'Settlement talks collapse', 3, '\U0001f6ab',
     '2017 -- Crans-Montana collapsed over security and guarantees; no formal talks since.',
     ['talks collapsed', 'talks collapse', 'walked out of talks', 'cyprus talks fail', 'negotiations collapsed'],
     ['two-state solution', 'sovereign equality', 'talks deadlock', 'stalemate cyprus', 'no common ground']),
    ('greece_turkey_casus_belli', 'Greece-Turkey casus belli language', 4, '\u2694\ufe0f',
     '1995 -- the Turkish parliament declared any Greek 12-mile extension a casus belli; still on the books.',
     ['renews casus belli', 'reaffirms casus belli', 'casus belli threat', 'threatens war over'],
     ['casus belli', 'greece turkey tensions', 'aegean dispute', 'greek airspace violation', 'dogfight aegean']),
    ('iran_hezbollah_threat', 'Iran / Hizballah threat to Cyprus', 4, '\U0001f3af',
     '2024 -- Nasrallah warned Cyprus it would be treated as party to a war if Israel used its bases.',
     ['drone attack cyprus', 'drone strike akrotiri', 'missile fired at cyprus', 'attack on akrotiri', 'hezbollah threatens cyprus',
      'hizballah threatens cyprus', 'iran threatens cyprus'],
     ['hezbollah cyprus', 'hizballah cyprus', 'iran cyprus', 'akrotiri', 'raf akrotiri', 'british bases cyprus']),
]
GREEN_ACTIVE = ['christodoulides erhurman', 'christodoulides and erhurman', 'leaders met', 'leaders meet',
                'new crossing point', 'crossing points opened', 'informal meeting cyprus', 'enlarged meeting',
                'talks resume', 'resumption of talks', 'holguin', 'confidence-building measures agreed']
GREEN_SIGNALED = ['erhurman', 'erhürman', 'federation', 'bizonal', 'bi-zonal', 'rotating presidency',
                  'confidence-building', 'un envoy', 'guterres cyprus', 'resume negotiations']

# Display-only wheels (NOT in the division composite).
PARTNER_VECTORS = {
    'israel_partnership':   ('israel', 'security_partner', 'Israel partnership'),
    'us_partnership':       ('us', 'security_partner', 'US partnership'),
    'iran_hezbollah_threat': ('iran', 'target', 'Iran / Hizballah threat'),
}

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


def _corpus(scan_data):
    arts = scan_data.get('rumint_articles') or []
    if not arts:
        for a in (scan_data.get('actors') or {}).values():
            arts = arts + list(a.get('top_articles') or [])
    return build_corpus({'articles_en': arts, 'telegram_messages': scan_data.get('rumint_telegram') or []})


def _score_red_lines(corpus):
    out = []
    for rid, label, sev, icon, precedent, br, ap in RED_LINES:
        sc = score_line(corpus, br, ap)
        if sc['status'] == 'INACTIVE':
            continue
        n = sc['breach_outlets'] if sc['status'] == 'BREACHED' else max(sc['breach_outlets'], sc['approach_outlets'])
        ev = sc['evidence'][0] if sc['evidence'] else None
        out.append({'id': rid, 'label': label, 'severity': sev, 'icon': icon, 'precedent': precedent, **sc,
                    'trigger': ("%s on %d outlet%s" % (sc['status'].title(), n, '' if n == 1 else 's'))
                               + ((' -- e.g. "%s" (%s)' % (ev['title'][:90], ev['outlet'])) if ev else '')})
    out.sort(key=lambda x: (-{'BREACHED': 2, 'APPROACHING': 1}.get(x['status'], 0), -x['severity']))
    return out


def _settlement_momentum(corpus):
    g = score_green(corpus, GREEN_ACTIVE, GREEN_SIGNALED)
    if g['status'] == 'ACTIVE':
        read = ('Leader-level contact is in the news (%d outlet%s) -- the settlement track is moving, '
                'which is the opposite of what the collapse-biased friction vector measures.'
                % (g['active_outlets'], '' if g['active_outlets'] == 1 else 's'))
    elif g['status'] == 'SIGNALED':
        read = 'Federation / talks language is present without a meeting in view -- momentum signalled, not shown.'
    else:
        read = 'No settlement-momentum language this cycle.'
    return {**g, 'read': read}


def _partners(scan_data):
    actors = scan_data.get('actors') or {}
    out = {}
    for vid, (hub, node_class, label) in PARTNER_VECTORS.items():
        a = actors.get(vid) or {}
        out[vid] = {'hub': hub, 'node_class': node_class, 'label': label,
                    'level': a.get('level', 0), 'outlets': a.get('outlet_count', 0),
                    'present': vid in actors}
    return out


def _top_indicator(scan_data, red_lines, momentum, partners, health):
    br = [r for r in red_lines if r['status'] == 'BREACHED']
    tp = scan_data.get('turkey_posture_level', 0) or 0
    ih = partners.get('iran_hezbollah_threat', {}).get('level', 0)
    if br:
        line = '%s: corroborated by %d outlets.' % (br[0]['label'], br[0]['breach_outlets'])
    elif ih >= 3:
        line = 'The Middle East war is the louder threat to Cyprus this cycle (Iran / Hizballah L%d), not the Green Line.' % ih
    elif momentum['status'] == 'ACTIVE' and tp <= 2:
        line = 'The leaders are talking: settlement momentum is in the news and Turkish posture is not elevated.'
    elif momentum['status'] == 'ACTIVE':
        line = 'Talks and pressure in the same cycle: leaders meeting while Turkish posture sits at L%d.' % tp
    elif tp >= 3:
        line = 'Turkish posture toward Cyprus is at L%d -- the inbound driver is up.' % tp
    elif any(r['status'] == 'APPROACHING' for r in red_lines):
        r = next(r for r in red_lines if r['status'] == 'APPROACHING')
        line = 'Watching: %s -- reported, not corroborated.' % r['label'].lower()
    else:
        line = 'The frozen division is quiet: no corroborated pressure signal, and no talks breakthrough either.'
    return ('Thin read -- ' + line) if health['thin'] else line


# ============================================
# MAIN ENTRY
# ============================================
def interpret_signals(scan_data):
    """
    Main entry point. Called from rhetoric_tracker_cyprus.py with full scan_data.
    """
    try:
        corpus = _corpus(scan_data)
        health = corpus_health(scan_data, corpus, THIN_MIN_ARTICLES)
        so_what = _build_so_what(scan_data)
        red_lines = _score_red_lines(corpus)
        momentum = _settlement_momentum(corpus)
        partners = _partners(scan_data)
        top_indicator = _top_indicator(scan_data, red_lines, momentum, partners, health)
        so_what['settlement_momentum'] = momentum['read']
        if momentum['status'] == 'ACTIVE':
            so_what['assessment'] = so_what.get('assessment', '') + ' Counter-signal: ' + momentum['read']
        if health['thin']:
            so_what['scenario'] = 'THIN READ -- ' + so_what.get('scenario', '')
            so_what['assessment'] = ('Under-read scan (%s); quiet lines may be unread. ' % health['reason']) \
                + so_what.get('assessment', '')
        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        tp = scan_data.get('turkey_posture_level', 0) or 0
        spokes = {'turkey': {'level': min(4, tp), 'node_class': 'adversary',
                             'note': 'Turkish posture toward Cyprus L%d' % tp}}
        for vid, row in partners.items():
            spokes[row['hub']] = {'level': min(4, row['level']), 'node_class': row['node_class'],
                                  'note': '%s L%d (%d outlets)' % (row['label'], row['level'], row['outlets'])}
        return {
            'so_what':             so_what,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in breached), default=0),
            },
            'settlement_momentum': momentum,
            'partners':            partners,
            'historical_matches':  [],
            'rumint':              {'active': False, 'band': 'off', 'label': '',
                                    'driver': '', 'framing': 0, 'specificity': 0,
                                    'reception': 0, 'corroboration': 0},
            'top_indicator':       top_indicator,
            'corpus_health':       health,
            'thin_read':           health['thin'],
            'spokes':              spokes,
            'interpreter_version': INTERPRETER_VERSION,
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print('[Cyprus Interpreter] Error: %s' % str(e)[:120])
        return {
            'so_what':            {'scenario': 'Interpreter error -- unread, not calm', 'assessment': str(e)[:200]},
            'top_indicator':      'Interpreter error this cycle -- unread, not calm.',
            'thin_read':          True, 'spokes': {},
            'red_lines':          {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'historical_matches': [],
            'rumint':             {'active': False, 'band': 'off', 'label': '',
                                   'driver': '', 'framing': 0, 'specificity': 0,
                                   'reception': 0, 'corroboration': 0},
            'interpreter_version': INTERPRETER_VERSION,
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
            'long_text':  'CYPRUS red line breached: %s. %s' % (label, rl.get('trigger', '')),
        })
    for rl in approaching[:2]:
        label = rl.get('label', 'Division red line')
        signals.append({
            'priority':   8, 'category': 'red_line_approaching', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f7e0', 'color': '#f97316',
            'short_text': '%s CYPRUS: Approaching - %s' % (FLAG, label[:50]),
            'long_text':  'CYPRUS approaching red line: %s. %s' % (label, rl.get('trigger', '')),
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
            'long_text':  'CYPRUS Turkish-Cypriot north L%d - north elections, Erhurman leadership, or settler politics.' % tr,
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

    # ----- 9. Settlement momentum (v1.1.0 green read) -----
    mom = interp.get('settlement_momentum') or {}
    if mom.get('status') == 'ACTIVE':
        signals.append({
            'priority':   5, 'category': 'settlement_momentum', 'theatre': 'cyprus',
            'level':      theatre_level, 'icon': '\U0001f91d', 'color': '#10b981',
            'short_text': '%s CYPRUS: Leaders talking - settlement momentum' % FLAG,
            'long_text':  'CYPRUS: ' + (mom.get('read') or ''),
        })
    # ----- 10. Iran / Hizballah threat wheel -----
    ih = ((interp.get('partners') or {}).get('iran_hezbollah_threat') or {}).get('level', 0)
    if ih >= 3:
        signals.append({
            'priority':   9, 'category': 'iran_hezbollah_threat', 'theatre': 'cyprus',
            'level':      ih, 'icon': '\U0001f3af', 'color': '#ef4444',
            'short_text': '%s CYPRUS: Iran / Hizballah threat L%d' % (FLAG, ih),
            'long_text':  'CYPRUS: Iran / Hizballah threat language toward Cyprus or the UK bases at L%d.' % ih,
        })

    signals.sort(key=lambda s: s['priority'], reverse=True)
    return signals
