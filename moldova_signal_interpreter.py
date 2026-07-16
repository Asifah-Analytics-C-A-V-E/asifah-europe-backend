"""
Moldova Signal Interpreter -- v1.0.0 -- July 16, 2026
Asifah Analytics -- Europe backend

The analytical layer for rhetoric_tracker_moldova.py. Turns the classified
article corpus into the CONTEST read: capture-from-within vs. integration-
lock-in.

Design (per the scoping note):
  RED LINES  = capture-pressure breaches (Transnistria mobilization, energy
               cutoff to the right bank, election capture, Gagauzia escalation)
  GREEN LINES = the ANCHOR -- EU-accession momentum, the de-escalatory side of
               the contest (this is what makes Moldova a TWO-SIDED tracker)
  VECTORS    = energy_lever, interference_tempo, transnistria_watch,
               gagauzia_watch, accession_momentum, commodity_convergence
  CAPTURE_VS_ANCHOR = the synthesis dial -- is pressure outrunning the anchor?

Estimative voice, precedent-anchored, never "will". The reader completes the
inference. Absence-honest: energy convergence gates (structural energy stress
counts only when it co-occurs with a live pressure vector).
"""

import os
from datetime import datetime, timezone

INTERPRETER_VERSION = '1.0.0'

DISCLAIMER = (
    'This is a CONVERGENCE indicator, NOT a probability of action. It reports '
    'where the capture-vs-anchor contest stands -- the balance between Russian '
    'hybrid pressure and EU-integration momentum -- never that any outcome will '
    'occur. The reader completes the inference.'
)


# ============================================================
# RED LINES -- capture-pressure breaches
# ============================================================

RED_LINES = [
    {
        'id':       'transnistria_mobilization',
        'category': 'Frozen Conflict',
        'title':    'Transnistria Escalation / Manufactured Pretext',
        'severity': 5,
        'description':
            'Indicators that the frozen conflict is being warmed up -- OGRF '
            'activity, "peacekeeper" reinforcement language, Cobasna security '
            'alerts, mobilization framing, or a manufactured pretext (staged '
            'provocation, "attack" claims). Transnistria sits ~40km from Odesa; '
            'escalation here is simultaneously a Moldova crisis and a threat to '
            "Ukraine's southwestern flank.",
        'triggers_breached': [
            'transnistria mobilization', 'transnistria attack', 'ogrf reinforced',
            'russian troops transnistria', 'transnistria provocation',
            'cobasna alert', 'transnistria referendum russia', 'tiraspol appeals russia',
        ],
        'triggers_approaching': [
            'transnistria tension', 'transnistria escalation', 'peacekeeper language',
            'transnistria gas cutoff', 'tiraspol chisinau standoff',
        ],
    },
    {
        'id':       'energy_cutoff',
        'category': 'Energy Blackmail',
        'title':    'Energy Cutoff to the Right Bank',
        'severity': 4,
        'description':
            'The most reliable destabilizer completing its chain -- a gas/power '
            'cutoff or tariff shock hitting the pro-Western right bank, feeding '
            'the tariff->inflation->protest transmission belt Moscow controls. '
            'The January 2025 Cuciurgan collapse is the live precedent.',
        'triggers_breached': [
            'moldova blackout', 'moldova power cut', 'moldova gas cutoff',
            'moldova energy emergency', 'moldova rolling blackouts',
            'cuciurgan shutdown', 'moldova electricity crisis',
        ],
        'triggers_approaching': [
            'moldova tariff hike', 'moldova gas price surge', 'moldova energy shortage',
            'moldovagaz debt', 'moldova heating crisis',
        ],
    },
    {
        'id':       'election_capture',
        'category': 'Interference',
        'title':    'Electoral Capture / Interference at Scale',
        'severity': 4,
        'description':
            'Industrial-scale interference threatening electoral integrity -- '
            'mass vote-buying (Shor network), coordinated disinformation at '
            'campaign scale, banned-party reconstitution, or a contested/annulled '
            'result. The 2024 presidential race and EU referendum are the '
            'documented precedent.',
        'triggers_breached': [
            'moldova vote buying scheme', 'moldova election fraud', 'moldova result annulled',
            'shor network exposed', 'moldova mass disinformation', 'moldova ballot fraud',
            'moldova electoral capture',
        ],
        'triggers_approaching': [
            'moldova interference', 'moldova disinformation surge', 'shor party activity',
            'moldova vote buying', 'moldova illicit finance',
        ],
    },
    {
        'id':       'gagauzia_escalation',
        'category': 'Second Front',
        'title':    'Gagauzia Separatist Escalation',
        'severity': 3,
        'description':
            'The southern pressure point activating -- autonomy-expansion '
            'demands escalating to separatist framing, Comrat-Chisinau '
            'confrontation, Gutul-led mobilization, or pro-Russian unrest. A '
            'live Gagauzia crisis opens a second front without touching '
            'Transnistria.',
        'triggers_breached': [
            'gagauzia separatism', 'gagauzia independence', 'comrat revolt',
            'gagauzia mobilization', 'gagauzia secession',
        ],
        'triggers_approaching': [
            'gagauzia autonomy demands', 'gutul protest', 'comrat chisinau standoff',
            'gagauzia russia support', 'gagauzia unrest',
        ],
    },
]


# ============================================================
# GREEN LINES -- the ANCHOR (EU-accession momentum)
# ============================================================

GREEN_LINES = [
    {
        'id':       'accession_cluster_progress',
        'category': 'EU Integration',
        'title':    'EU Accession Cluster Progress',
        'description':
            'Concrete accession momentum -- negotiating clusters opened/closed, '
            'reform benchmarks met, screening completed, a membership-timeline '
            'signal. Each is integration momentum that offsets capture-pressure. '
            'This is the anchoring side of the contest.',
        'triggers_active': [
            'moldova cluster opened', 'moldova accession negotiations opened',
            'moldova eu accession progress', 'moldova screening completed',
            'moldova benchmark met', 'moldova membership timeline',
            'moldova accession talks advance', 'moldova eu chapter opened',
        ],
        'triggers_signaled': [
            'moldova eu accession', 'moldova european integration',
            'moldova enlargement', 'moldova eu candidate progress',
        ],
    },
    {
        'id':       'western_support_active',
        'category': 'Western Anchor',
        'title':    'Active EU/Western Support Package',
        'description':
            'Concrete Western anchoring -- EU financial/energy support disbursed, '
            'a growth-plan tranche, Romanian energy solidarity, sanctions on '
            'interference networks, or high-level solidarity visits. Support that '
            'materially strengthens the target against capture-pressure.',
        'triggers_active': [
            'moldova eu funding', 'moldova growth plan', 'moldova eu support package',
            'moldova romania electricity deal', 'moldova energy support',
            'eu sanctions shor', 'moldova macro-financial assistance',
        ],
        'triggers_signaled': [
            'moldova eu support', 'moldova western backing', 'moldova solidarity',
            'moldova brussels visit',
        ],
    },
    {
        'id':       'energy_diversification',
        'category': 'Resilience',
        'title':    'Energy Diversification Win',
        'description':
            'Structural reduction of the energy lever -- new interconnector '
            'capacity, Romanian/EU supply locked in, reduced Cuciurgan/Gazprom '
            'dependence. Every step here removes a rung from Moscow\'s most '
            'reliable ladder.',
        'triggers_active': [
            'moldova energy independence', 'moldova interconnector', 'moldova gas diversification',
            'moldova romania power line', 'moldova ends russian gas',
        ],
        'triggers_signaled': [
            'moldova energy diversification', 'moldova energy security',
            'moldova alternative supply',
        ],
    },
]


# ============================================================
# KEYWORD MATCHING
# ============================================================

def _check_keywords(scan_data, keywords):
    """Match keywords against the scan_data corpus (articles + signals)."""
    if not keywords:
        return 0
    corpus = []
    for key in ('articles_en', 'articles_ru', 'articles_ro'):
        for art in (scan_data.get(key) or []):
            corpus.append((art.get('title') or '').lower())
            corpus.append((art.get('description') or '').lower())
            corpus.append((art.get('summary') or '').lower())
            corpus.append((art.get('content') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                corpus.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for sig in (scan_data.get('reddit_signals') or []):
        corpus.append((sig.get('title') or sig.get('text') or '').lower())
    blob = ' '.join(corpus)
    if not blob.strip():
        return 0
    return sum(1 for kw in keywords if kw.lower() in blob)


def _score_red_lines(scan_data):
    triggered = []
    for rl in RED_LINES:
        breached = _check_keywords(scan_data, rl.get('triggers_breached', []))
        approaching = _check_keywords(scan_data, rl.get('triggers_approaching', []))
        if breached >= 2:
            status = 'BREACHED'
        elif breached >= 1 or approaching >= 3:
            status = 'APPROACHING'
        elif approaching >= 1:
            status = 'WATCHING'
        else:
            status = 'INACTIVE'
        triggered.append({
            'id': rl['id'], 'category': rl['category'], 'title': rl['title'],
            'severity': rl['severity'], 'description': rl['description'],
            'status': status,
            'breached_hits': breached, 'approaching_hits': approaching,
        })
    return triggered


def _score_green_lines(scan_data):
    triggered = []
    for gl in GREEN_LINES:
        active = _check_keywords(scan_data, gl.get('triggers_active', []))
        signaled = _check_keywords(scan_data, gl.get('triggers_signaled', []))
        if active >= 1:
            status = 'ACTIVE'
        elif signaled >= 1:
            status = 'SIGNALED'
        else:
            status = 'DORMANT'
        triggered.append({
            'id': gl['id'], 'category': gl['category'], 'title': gl['title'],
            'description': gl['description'], 'status': status,
            'active_hits': active, 'signaled_hits': signaled,
        })
    return triggered


# ============================================================
# VECTOR PAYLOADS
# ============================================================

def _actor_count(scan_data, actor_key):
    return (scan_data.get('actor_summaries', {}).get(actor_key, {}) or {}).get('article_count', 0)


def _energy_lever(scan_data, red_lines):
    cutoff = next((r for r in red_lines if r['id'] == 'energy_cutoff'), {})
    n = _actor_count(scan_data, 'energy_complex')
    status = cutoff.get('status', 'INACTIVE')
    if status == 'BREACHED':
        read = ('Energy cutoff chain BREACHED -- the tariff->inflation->protest '
                'transmission belt is live; historically the most reliable '
                'destabilizer of Moldovan politics.')
    elif status in ('APPROACHING', 'WATCHING'):
        read = ('Energy pressure building -- tariff/supply stress consistent with '
                'the lever being tested ahead of a political pressure point.')
    else:
        read = ('Energy lever quiet this cycle -- structural import dependence '
                'persists as standing vulnerability.')
    return {'status': status, 'signal_count': n, 'read': read}


def _interference_tempo(scan_data, red_lines):
    capture = next((r for r in red_lines if r['id'] == 'election_capture'), {})
    n = _actor_count(scan_data, 'interference_shor')
    status = capture.get('status', 'INACTIVE')
    read = ('Interference tempo elevated -- reported vote-buying/disinformation '
            'activity consistent with capture pressure against the electoral '
            'calendar.' if status in ('BREACHED', 'APPROACHING')
            else 'Interference tempo at baseline this cycle.')
    return {'status': status, 'signal_count': n, 'read': read}


def _transnistria_watch(scan_data, red_lines):
    tr = next((r for r in red_lines if r['id'] == 'transnistria_mobilization'), {})
    n = _actor_count(scan_data, 'transnistria')
    status = tr.get('status', 'INACTIVE')
    read = ('Transnistria warming -- escalation/pretext language consistent with '
            'the frozen lever being activated; ~40km from Odesa, so a Moldova '
            "crisis is also a Ukraine-flank signal." if status in ('BREACHED', 'APPROACHING')
            else 'Transnistria quiet -- frozen-conflict baseline holds. Note: '
                 'claiming actors go quiet before they move; silence is watched, '
                 'not dismissed.')
    return {'status': status, 'signal_count': n, 'read': read}


def _gagauzia_watch(scan_data, red_lines):
    g = next((r for r in red_lines if r['id'] == 'gagauzia_escalation'), {})
    n = _actor_count(scan_data, 'gagauzia')
    status = g.get('status', 'INACTIVE')
    read = ('Gagauzia activating as a second front -- autonomy/separatist framing '
            'consistent with a parallel pressure axis.' if status in ('BREACHED', 'APPROACHING')
            else 'Gagauzia at baseline this cycle.')
    return {'status': status, 'signal_count': n, 'read': read}


def _accession_momentum(scan_data, green_lines):
    active = [g for g in green_lines if g['status'] == 'ACTIVE']
    signaled = [g for g in green_lines if g['status'] == 'SIGNALED']
    n = _actor_count(scan_data, 'eu_accession')
    if active:
        maturity = 'advancing'
        read = ('EU-accession anchoring ADVANCING -- concrete integration '
                'momentum offsetting capture-pressure. This is the de-escalatory '
                'side of the contest gaining ground.')
    elif signaled:
        maturity = 'holding'
        read = ('Accession anchoring holding -- integration trajectory intact but '
                'without fresh concrete milestones this cycle.')
    else:
        maturity = 'stalled'
        read = ('No fresh accession momentum this cycle -- the anchor is idle '
                'while pressure vectors remain live. A stalled anchor is itself a '
                'read: the contest tilts toward capture when integration pauses.')
    return {'maturity': maturity, 'active_count': len(active),
            'signaled_count': len(signaled), 'signal_count': n, 'read': read}


def _commodity_convergence(scan_data, red_lines):
    """CONVERGENCE GATE: energy stress is structural, so it counts only when it
    co-occurs with a live pressure vector. Also carries the wheat-transit-
    corridor global link -- a Transnistria flare-up threatens the Danube/
    Giurgiulesti grain lane feeding MENA food security."""
    commodity = scan_data.get('commodity_data') or {}
    present = bool(commodity)
    energy_pressure = commodity.get('commodity_pressure', 0) if present else 0
    live_vectors = [r for r in red_lines
                    if r['status'] in ('BREACHED', 'APPROACHING')
                    and r['id'] in ('transnistria_mobilization', 'energy_cutoff',
                                    'election_capture')]
    gated_on = bool(live_vectors)
    if gated_on and energy_pressure:
        read = ('CONVERGENCE: structural energy dependence co-occurring with a '
                'live pressure vector -- the combination is materially worse than '
                'either alone. Global link: a Transnistria/energy crisis also '
                'threatens the Danube (Giurgiulesti) grain-transit corridor that '
                'moves Ukrainian wheat to food-insecure MENA importers -- the '
                'same basket already under strain in Lebanon.')
    elif present:
        read = ('Energy exposure present but not converging with a live pressure '
                'vector this cycle -- held below the score by the convergence gate '
                '(structural, absence-honest).')
    else:
        read = 'Commodity read unavailable this cycle.'
    return {'present': present, 'energy_pressure': energy_pressure,
            'converging': gated_on and bool(energy_pressure),
            'live_vectors': [r['id'] for r in live_vectors], 'read': read}


def _capture_vs_anchor(red_lines, green_lines):
    """The synthesis dial: is capture-pressure outrunning the integration
    anchor? Balance in [-100 capture .. +100 anchor]."""
    pressure = 0
    for r in red_lines:
        if r['status'] == 'BREACHED':
            pressure += r['severity'] * 4
        elif r['status'] == 'APPROACHING':
            pressure += r['severity'] * 2
        elif r['status'] == 'WATCHING':
            pressure += r['severity']
    anchor = 0
    for g in green_lines:
        if g['status'] == 'ACTIVE':
            anchor += 10
        elif g['status'] == 'SIGNALED':
            anchor += 4
    balance = max(-100, min(100, anchor - pressure))
    if balance <= -20:
        tilt = 'capture'
        read = ('The contest tilts toward CAPTURE-FROM-WITHIN this cycle -- hybrid '
                'pressure is outrunning integration momentum. Watch the energy and '
                'interference vectors against the electoral/accession calendar.')
    elif balance >= 20:
        tilt = 'anchor'
        read = ('The contest tilts toward INTEGRATION-LOCK-IN this cycle -- '
                'accession/Western anchoring is outpacing capture-pressure.')
    else:
        tilt = 'contested'
        read = ('The contest is CONTESTED / balanced this cycle -- neither capture '
                'pressure nor integration momentum is decisively ahead.')
    return {'balance': balance, 'tilt': tilt, 'pressure_index': pressure,
            'anchor_index': anchor, 'read': read}


def _election_clock(scan_data):
    """Interference tempo clusters around the electoral/accession calendar.
    Lightweight calendar-awareness flag (not a standalone signal -- a
    multiplier context, per the Black Swan calendar pattern)."""
    # 2025 parliamentary elections done; next major cycle + accession milestones
    # are the pressure windows. This is a context flag, refined as dates firm.
    return {'note': ('Interference tempo historically clusters around electoral '
                     'and EU-accession milestone windows -- read interference '
                     'spikes against the calendar, not in isolation.')}


# ============================================================
# TOP SIGNALS + SO-WHAT
# ============================================================

def _build_top_signals(red_lines, green_lines, cva, commodity_conv, scan_data):
    signals = []
    # breached/approaching red lines first
    for r in sorted(red_lines, key=lambda x: (x['status'] != 'BREACHED', -x['severity'])):
        if r['status'] in ('BREACHED', 'APPROACHING'):
            signals.append({
                'type': 'red_line', 'id': r['id'], 'severity': r['severity'],
                'status': r['status'], 'title': r['title'],
                'text': f"{r['title']} -- {r['status']}",
                'pressure_type': 'diplomatic' if r['id'] in ('election_capture',)
                                 else 'kinetic' if r['id'] in ('transnistria_mobilization', 'gagauzia_escalation')
                                 else 'economic',
            })
    # the capture-vs-anchor synthesis as a signal
    signals.append({
        'type': 'synthesis', 'id': 'capture_vs_anchor',
        'title': 'Capture vs Anchor', 'balance': cva['balance'], 'tilt': cva['tilt'],
        'text': f"Capture-vs-anchor: {cva['tilt'].upper()} (balance {cva['balance']})",
        'pressure_type': 'diplomatic',
    })
    # active green lines (anchoring)
    for g in green_lines:
        if g['status'] == 'ACTIVE':
            signals.append({
                'type': 'green_line', 'id': g['id'], 'status': 'ACTIVE',
                'title': g['title'], 'text': f"{g['title']} -- ANCHORING",
                'pressure_type': 'diplomatic',
            })
    # commodity convergence if live
    if commodity_conv.get('converging'):
        signals.append({
            'type': 'convergence', 'id': 'commodity_convergence',
            'title': 'Energy x Pressure Convergence',
            'text': 'Structural energy dependence converging with a live pressure vector',
            'pressure_type': 'economic',
        })
    return signals[:8]


def _build_so_what(scan_data, red_lines, green_lines, cva, commodity_conv):
    breached = [r for r in red_lines if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
    active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']

    scenario = ('Capture pressure breaching' if breached
                else 'Capture pressure building' if approaching
                else 'Anchoring ahead' if active_gl
                else 'Contested equilibrium')

    situation = cva['read'] + ' '
    if breached:
        situation += ('Breached: ' + ', '.join(r['title'] for r in breached) + '. ')
    if active_gl:
        situation += ('Anchoring active: ' + ', '.join(g['title'] for g in active_gl) + '. ')
    situation += ('The named question: is Moldova being pulled out of the Western '
                  'orbit faster than it is being anchored in -- and by what means?')

    key_indicators = []
    for r in (breached + approaching)[:4]:
        key_indicators.append(f"{r['title']} ({r['status']})")
    for g in active_gl[:2]:
        key_indicators.append(f"{g['title']} (ANCHORING)")

    watch_list = [
        'Energy: Gazprom/Moldovagaz disputes, Cuciurgan fuel status, winter tariff cycles',
        'Interference: Shor-network activity, disinformation surges vs the electoral calendar',
        'Transnistria: OGRF/Cobasna activity, "peacekeeper" framing, manufactured-pretext watch',
        'Gagauzia: Comrat-Chisinau confrontation, Gutul moves',
        'Anchor: EU-accession cluster progress, Western support disbursement',
    ]

    return {
        'scenario': scenario,
        'situation': situation,
        'key_indicators': key_indicators,
        'watch_list': watch_list,
        'capture_vs_anchor': cva['tilt'],
    }


# ============================================================
# CROSS-THEATER FINGERPRINTS (Russia wheel spoke slices)
# ============================================================

def _build_fingerprints(scan_data, energy, interference, transnistria,
                        gagauzia, accession, commodity_conv):
    return {
        'energy_lever':          {'status': energy['status'], 'count': energy['signal_count']},
        'interference_tempo':    {'status': interference['status'], 'count': interference['signal_count']},
        'transnistria_watch':    {'status': transnistria['status'], 'count': transnistria['signal_count']},
        'gagauzia_watch':        {'status': gagauzia['status'], 'count': gagauzia['signal_count']},
        'accession_momentum':    {'maturity': accession['maturity'], 'active': accession['active_count']},
        'commodity_convergence': {'converging': commodity_conv['converging'],
                                  'live_vectors': commodity_conv['live_vectors']},
    }


# ============================================================
# MAIN ENTRY
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_moldova.py."""
    try:
        red_lines = _score_red_lines(scan_data)
        green_lines = _score_green_lines(scan_data)

        energy = _energy_lever(scan_data, red_lines)
        interference = _interference_tempo(scan_data, red_lines)
        transnistria = _transnistria_watch(scan_data, red_lines)
        gagauzia = _gagauzia_watch(scan_data, red_lines)
        accession = _accession_momentum(scan_data, green_lines)
        commodity_conv = _commodity_convergence(scan_data, red_lines)
        cva = _capture_vs_anchor(red_lines, green_lines)
        election_clock = _election_clock(scan_data)

        so_what = _build_so_what(scan_data, red_lines, green_lines, cva, commodity_conv)
        top_signals = _build_top_signals(red_lines, green_lines, cva, commodity_conv, scan_data)
        fingerprints = _build_fingerprints(scan_data, energy, interference,
                                           transnistria, gagauzia, accession, commodity_conv)

        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']

        # composite modifier: anchoring pulls the score down (de-escalatory),
        # per the bidirectional model. Capped like the diplomatic track.
        composite_modifier = -min(15, len(active_gl) * 5)

        return {
            'so_what':      so_what,
            'top_signals':  top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in red_lines), default=0),
            },
            'green_lines': {
                'triggered':      green_lines,
                'active_count':   len(active_gl),
                'signaled_count': len([g for g in green_lines if g['status'] == 'SIGNALED']),
            },
            # -- Moldova vector payloads --
            'energy_lever':          energy,
            'interference_tempo':    interference,
            'transnistria_watch':    transnistria,
            'gagauzia_watch':        gagauzia,
            'accession_momentum':    accession,
            'capture_vs_anchor':     cva,
            'commodity_convergence': commodity_conv,
            'election_clock':        election_clock,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':    composite_modifier,
            'interpreter_version':   INTERPRETER_VERSION,
            'interpreted_at':        datetime.now(timezone.utc).isoformat(),
            'disclaimer':            DISCLAIMER,
        }
    except Exception as e:
        return {
            'so_what': {'scenario': 'Interpreter error', 'situation': str(e)[:200],
                        'key_indicators': [], 'watch_list': []},
            'top_signals':                [],
            'red_lines':   {'triggered': [], 'breached_count': 0,
                            'approaching_count': 0, 'highest_severity': 0},
            'green_lines': {'triggered': [], 'active_count': 0, 'signaled_count': 0},
            'cross_theater_fingerprints': {},
            'composite_modifier':         0,
            'interpreter_version':        INTERPRETER_VERSION,
            'disclaimer':                 DISCLAIMER,
        }
