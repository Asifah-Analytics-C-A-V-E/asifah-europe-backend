"""
Moldova Signal Interpreter -- v1.1.0 -- November 3, 2026   (v1.0.0 Jul 16 2026)
Asifah Analytics -- Europe backend

The analytical layer for rhetoric_tracker_moldova.py. Turns the classified
article corpus into the CONTEST read: capture-from-within vs integration lock-in.

v1.1.0 (Nov 3 2026)
  1. EVIDENCE. Red lines are scored per article with publishers counted
     (europe_evidence): BREACHED needs 2+ outlets, and every line carries the
     headlines that moved it. v1.0 pooled the corpus into one string.
  2. AIRSPACE red line (new). Russian drones crossing into Moldova -- five
     violations in one night (Oct 16 2026), a drone exploding on Moldovan soil
     (Sep 24 2026). The war reaching Moldova directly was not a v1.0 line at all.
  3. Transnistria triggers widened for the 2026 pattern: Moscow's "protect
     Russian citizens" / "blockade" framing (Shoigu, Apr 2026), eased Russian
     citizenship for Transnistrians (May 2026), the OGRF persona-non-grata row.
  4. THIN READ. An under-read scan says so in the scenario and the headline,
     and the capture-vs-anchor dial reads UNREAD rather than "contested".
     v1.0 printed "Contested equilibrium" off a 70-article RSS-only corpus with
     every vector at zero.
  5. CANONICAL top_signals (short_text / long_text / level / icon). v1.0 emitted
     only `text`, so the Europe BLUF rendered Moldova's top signal EMPTY.
  6. Per-actor LEVELS (0-4), the Russia-pressure level for spoke:russia:moldova,
     and a one-line top_indicator.

Estimative voice, precedent-anchored, never "will". Absence-honest: energy
convergence gates (structural energy stress counts only alongside a live vector).
"""

from datetime import datetime, timezone

from europe_evidence import (build_corpus, score_line, score_green, find, outlet_level,
                             corpus_health, STATUS_LEVEL)

INTERPRETER_VERSION = '1.1.0'
THIN_MIN_ARTICLES = 20

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
        'id': 'transnistria_mobilization', 'category': 'Frozen Conflict', 'severity': 5,
        'title': 'Transnistria Escalation / Manufactured Pretext',
        'description':
            'Indicators that the frozen conflict is being warmed up -- OGRF activity, "peacekeeper" '
            'reinforcement, Cobasna security alerts, mobilization framing, or a manufactured pretext '
            '("protect Russian citizens", "blockade" claims, staged provocation). Transnistria borders Ukraine\'s '
            "Odesa region: escalation here is a Moldova crisis and a threat to Ukraine's south-western flank.",
        'triggers_breached': [
            'transnistria mobilization', 'transnistria attack', 'ogrf reinforced', 'russian troops transnistria',
            'transnistria provocation', 'cobasna alert', 'transnistria referendum russia', 'tiraspol appeals russia',
            'russia intervene in transnistria', 'military intervention transnistria',
            'приднестровье мобилизация', 'тирасполь просит россию',
        ],
        'triggers_approaching': [
            'transnistria tension', 'transnistria escalation', 'peacekeeper language', 'transnistria gas cutoff',
            'tiraspol chisinau standoff', 'protect russian citizens', 'russian citizens in transnistria',
            'blockade of transnistria', 'blockade transnistria', 'russia warns moldova', 'shoigu moldova',
            'russian citizenship transnistria', 'russian passports transnistria', 'ogrf', 'operational group of russian forces',
            'persona non grata', 'blocada transnistriei', 'блокада приднестровья', 'защитить граждан россии',
        ],
    },
    {
        'id': 'airspace_violation', 'category': 'War Spillover', 'severity': 3,
        'title': 'Russian Drones Over Moldova',
        'description':
            'The war reaching Moldova directly: Russian drones crossing Moldovan airspace or crashing and '
            'exploding on its soil during strikes on southern Ukraine. Moldova is constitutionally neutral '
            'with no fighter cover of its own; each incursion tests whether Chisinau and Bucharest answer.',
        'triggers_breached': [
            'drone exploded in moldova', 'drone crashed in moldova', 'drone fell in moldova', 'drone crash moldova',
            'violated moldovan airspace', 'violated moldova airspace', 'drones over moldova', 'drone over moldova',
            'moldovan airspace violated', 'drone entered moldovan airspace', 'drone found in moldova',
            'dronă căzută', 'spațiul aerian al republicii moldova',
        ],
        'triggers_approaching': [
            'moldovan airspace', 'moldova airspace', 'drone moldova', 'drones moldova', 'airspace alert moldova',
            'moldova drone debris', 'дрон молдова', 'беспилотник молдова', 'dronă',
        ],
    },
    {
        'id': 'energy_cutoff', 'category': 'Energy Blackmail', 'severity': 4,
        'title': 'Energy Cutoff to the Right Bank',
        'description':
            'The most reliable destabilizer completing its chain -- a gas/power cutoff or tariff shock hitting '
            'the right bank, feeding the tariff->inflation->protest belt. The January 2025 Cuciurgan collapse '
            '(end of Russian gas transit through Ukraine) is the live precedent.',
        'triggers_breached': [
            'moldova blackout', 'moldova power cut', 'moldova gas cutoff', 'moldova energy emergency',
            'moldova rolling blackouts', 'cuciurgan shutdown', 'moldova electricity crisis',
            'stare de urgență energetică', 'отключение газа молдова',
        ],
        'triggers_approaching': [
            'moldova tariff hike', 'moldova gas price surge', 'moldova energy shortage', 'moldovagaz debt',
            'moldova heating crisis', 'transnistria energy crisis', 'transnistria gas',
        ],
    },
    {
        'id': 'election_capture', 'category': 'Interference', 'severity': 4,
        'title': 'Electoral Capture / Interference at Scale',
        'description':
            'Industrial-scale interference threatening electoral integrity -- mass vote-buying (Shor network), '
            'coordinated disinformation at campaign scale, banned-party reconstitution, or a contested result. '
            'The 2024 presidential race and EU referendum are the documented precedent.',
        'triggers_breached': [
            'moldova vote buying scheme', 'moldova election fraud', 'moldova result annulled', 'shor network exposed',
            'moldova mass disinformation', 'moldova ballot fraud', 'moldova electoral capture',
        ],
        'triggers_approaching': [
            'moldova interference', 'moldova disinformation surge', 'shor party activity', 'moldova vote buying',
            'moldova illicit finance', 'ilan shor', 'shor network', 'victory bloc', 'cumpărare de voturi',
            'cumparare voturi', 'подкуп избирателей',
        ],
    },
    {
        'id': 'gagauzia_escalation', 'category': 'Second Front', 'severity': 3,
        'title': 'Gagauzia Separatist Escalation',
        'description':
            'The southern pressure point activating -- autonomy demands escalating to separatist framing, '
            'Comrat-Chisinau confrontation, Gutul-camp mobilization, or pro-Russian unrest. A live Gagauzia '
            'crisis opens a second front without touching Transnistria.',
        'triggers_breached': [
            'gagauzia separatism', 'gagauzia independence', 'comrat revolt', 'gagauzia mobilization', 'gagauzia secession',
        ],
        'triggers_approaching': [
            'gagauzia autonomy demands', 'gutul protest', 'comrat chisinau standoff', 'gagauzia russia support',
            'gagauzia unrest', 'gutul', 'gutsul', 'гуцул', 'гагаузия протест',
        ],
    },
]

# Which red lines speak for which actor.
ACTOR_LINES = {
    'russia_inbound': ['transnistria_mobilization', 'energy_cutoff', 'election_capture', 'airspace_violation'],
    'transnistria': ['transnistria_mobilization'],
    'gagauzia': ['gagauzia_escalation'],
    'interference_shor': ['election_capture'],
    'energy_complex': ['energy_cutoff'],
    'moldovan_government': [],
    'eu_accession': [],
}


# ============================================================
# GREEN LINES -- the ANCHOR
# ============================================================

GREEN_LINES = [
    {
        'id': 'accession_cluster_progress', 'category': 'EU Integration',
        'title': 'EU Accession Cluster Progress',
        'description':
            'Concrete accession momentum -- clusters opened/closed, benchmarks met, a membership-timeline '
            "signal. Moldova's track is still tied to Ukraine's, so a Ukraine veto is a Moldova veto.",
        'triggers_active': [
            'moldova cluster opened', 'moldova accession negotiations opened', 'moldova eu accession progress',
            'moldova screening completed', 'moldova benchmark met', 'moldova membership timeline',
            'moldova accession talks advance', 'moldova eu chapter opened', 'clusters 2 and 3',
            'accession conference', 'opens clusters', 'open clusters', 'decoupling moldova',
        ],
        'triggers_signaled': [
            'moldova eu accession', 'moldova european integration', 'moldova enlargement',
            'moldova eu candidate progress', 'aderare ue', 'integrare europeana',
            'путь в ес', 'вступление в ес', 'евроинтеграц', 'blocking moldova', 'decouple moldova',
        ],
    },
    {
        'id': 'western_support_active', 'category': 'Western Anchor',
        'title': 'Active EU/Western Support Package',
        'description':
            'Concrete Western anchoring -- EU financial/energy support disbursed, a growth-plan tranche, '
            'Romanian energy solidarity, sanctions on interference networks, high-level solidarity visits.',
        'triggers_active': [
            'moldova eu funding', 'moldova growth plan', 'moldova eu support package',
            'moldova romania electricity deal', 'moldova energy support', 'eu sanctions shor',
            'moldova macro-financial assistance', 'european peace facility moldova',
            'joint defence procurement', 'joint defense procurement',
        ],
        'triggers_signaled': [
            'moldova eu support', 'moldova western backing', 'moldova solidarity', 'moldova brussels visit',
        ],
    },
    {
        'id': 'energy_diversification', 'category': 'Resilience',
        'title': 'Energy Diversification Win',
        'description':
            'Structural reduction of the energy lever -- interconnector capacity, Romanian/EU supply locked in, '
            "reduced Cuciurgan/Gazprom dependence. Every step removes a rung from Moscow's most reliable ladder.",
        'triggers_active': [
            'moldova energy independence', 'moldova interconnector', 'moldova gas diversification',
            'moldova romania power line', 'moldova ends russian gas', 'vulcanesti chisinau',
            'газ из черного моря', 'gaz din marea neagra', 'neptun deep',
        ],
        'triggers_signaled': [
            'moldova energy diversification', 'moldova energy security', 'moldova alternative supply',
        ],
    },
]


# ============================================================
# SCORING
# ============================================================

def _score_red_lines(corpus):
    out = []
    for rl in RED_LINES:
        sc = score_line(corpus, rl['triggers_breached'], rl['triggers_approaching'])
        out.append({'id': rl['id'], 'category': rl['category'], 'title': rl['title'],
                    'severity': rl['severity'], 'description': rl['description'], **sc})
    return out


def _score_green_lines(corpus):
    out = []
    for gl in GREEN_LINES:
        sc = score_green(corpus, gl['triggers_active'], gl['triggers_signaled'])
        out.append({'id': gl['id'], 'category': gl['category'], 'title': gl['title'],
                    'description': gl['description'], **sc})
    return out


def _rl(lines, rid):
    return next((r for r in lines if r['id'] == rid), {})


def _actor_count(scan_data, key):
    return (scan_data.get('actor_summaries', {}).get(key, {}) or {}).get('article_count', 0)


# ============================================================
# VECTORS
# ============================================================

def _vector(scan_data, red_lines, rid, actor, hot_read, quiet_read, thin):
    r = _rl(red_lines, rid)
    status = r.get('status', 'INACTIVE')
    if status in ('BREACHED', 'APPROACHING'):
        read = hot_read
    elif thin:
        read = 'Not read this cycle -- the scan is under-read. Unread, not quiet.'
    else:
        read = quiet_read
    return {'status': status, 'signal_count': _actor_count(scan_data, actor),
            'outlets': max(r.get('breach_outlets', 0), r.get('approach_outlets', 0)),
            'read': read, 'evidence': r.get('evidence', [])[:3]}


def _accession_momentum(scan_data, green_lines, thin):
    active = [g for g in green_lines if g['status'] == 'ACTIVE']
    signaled = [g for g in green_lines if g['status'] == 'SIGNALED']
    if active:
        maturity, read = 'advancing', ('EU-accession anchoring ADVANCING -- concrete integration momentum offsetting '
                                       'capture-pressure. The de-escalatory side of the contest gaining ground.')
    elif signaled:
        maturity, read = 'holding', ('Accession anchoring holding -- trajectory intact, no fresh concrete milestone '
                                     'this cycle.')
    elif thin:
        maturity, read = 'unread', 'Accession not read this cycle -- under-read scan, not a stalled anchor.'
    else:
        maturity, read = 'stalled', ('No fresh accession momentum this cycle -- the anchor is idle while pressure '
                                     'vectors remain live. The contest tilts toward capture when integration pauses.')
    return {'maturity': maturity, 'active_count': len(active), 'signaled_count': len(signaled),
            'signal_count': _actor_count(scan_data, 'eu_accession'), 'read': read}


def _commodity_convergence(scan_data, red_lines):
    commodity = scan_data.get('commodity_data') or {}
    present = bool(commodity)
    energy_pressure = commodity.get('commodity_pressure', 0) if present else 0
    live = [r for r in red_lines if r['status'] in ('BREACHED', 'APPROACHING')
            and r['id'] in ('transnistria_mobilization', 'energy_cutoff', 'election_capture')]
    gated_on = bool(live)
    if gated_on and energy_pressure:
        read = ('CONVERGENCE: structural energy dependence co-occurring with a live pressure vector -- worse than '
                'either alone. Global link: a Transnistria/energy crisis also threatens the Danube (Giurgiulesti) '
                'grain lane that moves Ukrainian wheat toward food-insecure MENA importers.')
    elif present:
        read = ('Energy exposure present but not converging with a live pressure vector this cycle -- held below '
                'the score by the convergence gate.')
    else:
        read = 'Commodity read unavailable this cycle.'
    return {'present': present, 'energy_pressure': energy_pressure, 'converging': gated_on and bool(energy_pressure),
            'live_vectors': [r['id'] for r in live], 'read': read}


def _capture_vs_anchor(red_lines, green_lines, thin):
    pressure = 0
    for r in red_lines:
        pressure += {'BREACHED': 4, 'APPROACHING': 2, 'WATCHING': 1}.get(r['status'], 0) * r['severity']
    anchor = sum({'ACTIVE': 10, 'SIGNALED': 4}.get(g['status'], 0) for g in green_lines)
    balance = max(-100, min(100, anchor - pressure))
    if thin and pressure == 0 and anchor == 0:
        tilt, read = 'unread', ('The contest is UNREAD this cycle -- the scan is too thin to weigh pressure against '
                                'the anchor. A blank dial, not a balanced one.')
    elif balance <= -20:
        tilt, read = 'capture', ('The contest tilts toward CAPTURE-FROM-WITHIN this cycle -- hybrid pressure is '
                                 'outrunning integration momentum.')
    elif balance >= 20:
        tilt, read = 'anchor', ('The contest tilts toward INTEGRATION LOCK-IN this cycle -- accession and Western '
                                'anchoring are outpacing capture pressure.')
    else:
        tilt, read = 'contested', ('The contest is CONTESTED this cycle -- neither capture pressure nor integration '
                                   'momentum is decisively ahead.')
    return {'balance': balance, 'tilt': tilt, 'pressure_index': pressure, 'anchor_index': anchor, 'read': read}


def _election_clock(scan_data):
    return {'note': ('Interference tempo clusters around electoral and EU-accession milestone windows -- read '
                     'interference spikes against the calendar, not in isolation.')}


def _russia_pressure(red_lines):
    """Level for spoke:russia:moldova -- the strongest corroborated lever, capped L4.
    Moldova is an inbound target, not a war: L5 is never asserted here."""
    lv, top = 0, None
    for r in red_lines:
        v = STATUS_LEVEL.get(r['status'], 0)
        if v > lv or (v == lv and top and r['severity'] > top['severity']):
            lv, top = v, r
    return {'level': min(4, lv),
            'lever': top['id'] if top and lv else None,
            'top_signal': (f"{top['title']} -- {top['status']}" if top and lv else '')}


def _actor_levels(scan_data, red_lines):
    out = {}
    for key, s in (scan_data.get('actor_summaries') or {}).items():
        outlets = {str(a.get('source') or '').lower() for a in (scan_data.get('by_actor') or {}).get(key, [])
                   if not a.get('co_credit')}
        outlets.discard('')
        vol = min(2, len(outlets))
        line_lv = max([STATUS_LEVEL.get(_rl(red_lines, rid).get('status', 'INACTIVE'), 0)
                       for rid in ACTOR_LINES.get(key, [])] or [0])
        lv = max(vol, line_lv)
        if key in ('eu_accession', 'moldovan_government', 'energy_complex'):
            lv = min(lv, 2)     # anchor / display actors never read as pressure above L2
        out[key] = {'level': min(4, lv), 'outlet_count': len(outlets), 'line_level': line_lv}
    return out


# ============================================================
# TOP SIGNALS + SO WHAT
# ============================================================

_PTYPE = {'election_capture': 'diplomatic', 'transnistria_mobilization': 'kinetic',
          'gagauzia_escalation': 'kinetic', 'airspace_violation': 'kinetic', 'energy_cutoff': 'economic'}
_ICON = {'transnistria_mobilization': '❄️', 'airspace_violation': '🛸', 'energy_cutoff': '⚡',
         'election_capture': '🗳️', 'gagauzia_escalation': '🏴'}


def _build_top_signals(red_lines, green_lines, cva, commodity_conv):
    signals = []
    for r in sorted(red_lines, key=lambda x: (x['status'] != 'BREACHED', -x['severity'])):
        if r['status'] not in ('BREACHED', 'APPROACHING'):
            continue
        n = r['breach_outlets'] if r['status'] == 'BREACHED' else max(r['breach_outlets'], r['approach_outlets'])
        signals.append({
            'type': 'red_line', 'id': r['id'], 'severity': r['severity'], 'status': r['status'],
            'title': r['title'], 'category': r['category'].lower().replace(' ', '_'),
            'level': 'high' if r['status'] == 'BREACHED' and r['severity'] >= 4 else 'elevated',
            'priority': 8 + r['severity'] if r['status'] == 'BREACHED' else 5 + r['severity'],
            'icon': _ICON.get(r['id'], '⚠️'),
            'text': f"{r['title']} -- {r['status']}",
            'short_text': f"{r['title']}: {r['status'].lower()} ({n} outlet{'s' if n != 1 else ''})",
            'long_text': r['description'],
            'pressure_type': _PTYPE.get(r['id'], 'economic'),
            'source_link': f"/rhetoric-moldova.html#{r['id']}",
        })
    if cva['tilt'] != 'unread':
        signals.append({
            'type': 'synthesis', 'id': 'capture_vs_anchor', 'title': 'Capture vs Anchor',
            'balance': cva['balance'], 'tilt': cva['tilt'], 'category': 'capture_vs_anchor',
            'level': 'elevated' if cva['tilt'] == 'capture' else 'normal', 'priority': 4, 'icon': '⚖️',
            'text': f"Capture-vs-anchor: {cva['tilt'].upper()} (balance {cva['balance']})",
            'short_text': f"Capture vs anchor: {cva['tilt']} (balance {cva['balance']:+d})",
            'long_text': cva['read'], 'pressure_type': 'diplomatic',
            'source_link': '/rhetoric-moldova.html#capture-vs-anchor',
        })
    for g in green_lines:
        if g['status'] == 'ACTIVE':
            signals.append({
                'type': 'green_line', 'id': g['id'], 'status': 'ACTIVE', 'title': g['title'],
                'category': 'diplomatic', 'level': 'normal', 'priority': 3, 'icon': '⚓',
                'text': f"{g['title']} -- ANCHORING", 'short_text': f"Anchor: {g['title']}",
                'long_text': g['description'], 'pressure_type': 'diplomatic',
                'source_link': f"/rhetoric-moldova.html#{g['id']}",
            })
    if commodity_conv.get('converging'):
        signals.append({
            'type': 'convergence', 'id': 'commodity_convergence', 'title': 'Energy x Pressure Convergence',
            'category': 'commodity', 'level': 'elevated', 'priority': 7, 'icon': '🛢️',
            'text': 'Structural energy dependence converging with a live pressure vector',
            'short_text': 'Energy dependence converging with a live pressure vector',
            'long_text': commodity_conv['read'], 'pressure_type': 'economic',
            'source_link': '/rhetoric-moldova.html#energy',
        })
    return signals[:8]


def _top_indicator(red_lines, green_lines, cva, health):
    br = sorted([r for r in red_lines if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])
    ap = sorted([r for r in red_lines if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])
    act = [g for g in green_lines if g['status'] == 'ACTIVE']
    if br:
        line = f"{br[0]['title']}: corroborated by {br[0]['breach_outlets']} outlets."
    elif ap:
        line = f"Watching: {ap[0]['title'].lower()} -- reported, not yet corroborated."
    elif act:
        line = f"The anchor is moving: {act[0]['title'].lower()}."
    elif health['thin']:
        return 'Thin read -- too little reporting this cycle to say whether pressure is building. Unread, not calm.'
    else:
        line = 'No capture lever is corroborated this cycle; the frozen levers are quiet, which is watched, not dismissed.'
    return ('Thin read -- ' + line) if health['thin'] else line


def _build_so_what(red_lines, green_lines, cva, health):
    breached = [r for r in red_lines if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
    active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']
    scenario = ('Capture pressure breaching' if breached else 'Capture pressure building' if approaching
                else 'Anchoring ahead' if active_gl
                else 'Unread -- thin scan' if health['thin'] else 'Contested equilibrium')
    if health['thin'] and scenario != 'Unread -- thin scan':
        scenario = 'THIN READ -- ' + scenario
    situation = ''
    if health['thin']:
        situation += f"Under-read scan ({health['reason']}): quiet vectors below may be unread, not quiet. "
    situation += cva['read'] + ' '
    if breached:
        situation += 'Breached: ' + ', '.join(f"{r['title']} ({r['breach_outlets']} outlets)" for r in breached) + '. '
    if approaching:
        situation += 'Building: ' + ', '.join(r['title'] for r in approaching) + '. '
    if active_gl:
        situation += 'Anchoring active: ' + ', '.join(g['title'] for g in active_gl) + '. '
    air = _rl(red_lines, 'airspace_violation')
    tr = _rl(red_lines, 'transnistria_mobilization')
    if air.get('status') in ('BREACHED', 'APPROACHING') and tr.get('status') in ('BREACHED', 'APPROACHING'):
        situation += ('Drones over Moldova while Transnistria warms: the war is reaching Moldova from the air at the '
                      'same time Moscow works the frozen lever on the ground -- the two-front squeeze the '
                      'garrison exists to make credible. ')
    situation += ('The named question: is Moldova being pulled out of the Western orbit faster than it is being '
                  'anchored in -- and by what means?')
    key_indicators = [f"{r['title']} ({r['status']})" for r in (breached + approaching)[:4]]
    key_indicators += [f"{g['title']} (ANCHORING)" for g in active_gl[:2]]
    return {
        'scenario': scenario, 'situation': situation, 'key_indicators': key_indicators,
        'watch_list': [
            'Transnistria: OGRF/Cobasna activity, "protect Russian citizens" / "blockade" framing, Russian passports',
            'Airspace: Russian drones crossing from the Odesa strikes -- crashes, Romanian scrambles',
            'Energy: Moldovagaz disputes, Cuciurgan fuel status, winter tariff cycles',
            'Interference: Shor-network activity vs the electoral calendar',
            'Gagauzia: Comrat-Chisinau confrontation, the Gutul camp',
            "Anchor: EU clusters (tied to Ukraine's track), Western support disbursement",
        ],
        'capture_vs_anchor': cva['tilt'], 'thin_read': health['thin'],
    }


def _build_fingerprints(energy, interference, transnistria, gagauzia, airspace, accession, commodity_conv, russia):
    return {
        'energy_lever': {'status': energy['status'], 'count': energy['signal_count']},
        'interference_tempo': {'status': interference['status'], 'count': interference['signal_count']},
        'transnistria_watch': {'status': transnistria['status'], 'count': transnistria['signal_count']},
        'gagauzia_watch': {'status': gagauzia['status'], 'count': gagauzia['signal_count']},
        'airspace_watch': {'status': airspace['status'], 'outlets': airspace['outlets']},
        'accession_momentum': {'maturity': accession['maturity'], 'active': accession['active_count']},
        'commodity_convergence': {'converging': commodity_conv['converging'],
                                  'live_vectors': commodity_conv['live_vectors']},
        'russia_spoke': {'level': russia['level'], 'note': russia['top_signal']},
    }


# ============================================================
# MAIN ENTRY
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_moldova.py."""
    try:
        corpus = build_corpus(scan_data, article_keys=('articles_en', 'articles_ru', 'articles_ro'))
        health = corpus_health(scan_data, corpus, THIN_MIN_ARTICLES)
        thin = health['thin']
        red_lines = _score_red_lines(corpus)
        green_lines = _score_green_lines(corpus)

        energy = _vector(scan_data, red_lines, 'energy_cutoff', 'energy_complex',
                         'Energy pressure building -- tariff/supply stress consistent with the lever being tested.',
                         'Energy lever quiet this cycle -- structural import dependence persists as standing vulnerability.', thin)
        if energy['status'] == 'BREACHED':
            energy['read'] = ('Energy cutoff chain BREACHED -- the tariff->inflation->protest belt is live; '
                              'historically the most reliable destabilizer of Moldovan politics.')
        interference = _vector(scan_data, red_lines, 'election_capture', 'interference_shor',
                               'Interference tempo elevated -- reported vote-buying/disinformation consistent with capture pressure.',
                               'Interference tempo at baseline this cycle.', thin)
        transnistria = _vector(scan_data, red_lines, 'transnistria_mobilization', 'transnistria',
                               ('Transnistria warming -- escalation or pretext language consistent with the frozen lever '
                                'being activated; Transnistria borders the Odesa region, so a Moldova crisis is also a '
                                'Ukraine-flank signal.'),
                               ('Transnistria quiet -- frozen-conflict baseline holds. Claiming actors go quiet before '
                                'they move; silence is watched, not dismissed.'), thin)
        gagauzia = _vector(scan_data, red_lines, 'gagauzia_escalation', 'gagauzia',
                           'Gagauzia activating as a second front -- autonomy/separatist framing on a parallel axis.',
                           'Gagauzia at baseline this cycle.', thin)
        airspace = _vector(scan_data, red_lines, 'airspace_violation', 'russia_inbound',
                           ('Russian drones are crossing into Moldova -- the war reaching a neutral state with no '
                            'fighter cover of its own.'),
                           'No airspace incursion reported this cycle.', thin)
        accession = _accession_momentum(scan_data, green_lines, thin)
        commodity_conv = _commodity_convergence(scan_data, red_lines)
        cva = _capture_vs_anchor(red_lines, green_lines, thin)
        russia = _russia_pressure(red_lines)
        actors = _actor_levels(scan_data, red_lines)

        so_what = _build_so_what(red_lines, green_lines, cva, health)
        top_signals = _build_top_signals(red_lines, green_lines, cva, commodity_conv)
        fingerprints = _build_fingerprints(energy, interference, transnistria, gagauzia, airspace,
                                           accession, commodity_conv, russia)
        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']
        return {
            'so_what': so_what, 'top_signals': top_signals,
            'top_indicator': _top_indicator(red_lines, green_lines, cva, health),
            'red_lines': {'triggered': red_lines, 'breached_count': len(breached),
                          'approaching_count': len(approaching),
                          'highest_severity': max((r['severity'] for r in breached), default=0)},
            'green_lines': {'triggered': green_lines, 'active_count': len(active_gl),
                            'signaled_count': len([g for g in green_lines if g['status'] == 'SIGNALED'])},
            'energy_lever': energy, 'interference_tempo': interference, 'transnistria_watch': transnistria,
            'gagauzia_watch': gagauzia, 'airspace_watch': airspace, 'accession_momentum': accession,
            'capture_vs_anchor': cva, 'commodity_convergence': commodity_conv,
            'election_clock': _election_clock(scan_data),
            'russia_pressure': russia, 'actor_levels': actors,
            'corpus_health': health, 'thin_read': thin,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier': -min(15, len(active_gl) * 5),
            'interpreter_version': INTERPRETER_VERSION,
            'interpreted_at': datetime.now(timezone.utc).isoformat(),
            'disclaimer': DISCLAIMER,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'so_what': {'scenario': 'Interpreter error -- unread, not calm', 'situation': str(e)[:200],
                        'key_indicators': [], 'watch_list': [], 'thin_read': True},
            'top_signals': [], 'top_indicator': 'Interpreter error this cycle -- unread, not calm.',
            'red_lines': {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'green_lines': {'triggered': [], 'active_count': 0, 'signaled_count': 0},
            'russia_pressure': {'level': 0, 'lever': None, 'top_signal': ''}, 'actor_levels': {},
            'corpus_health': {'thin': True, 'reason': 'interpreter error'}, 'thin_read': True,
            'cross_theater_fingerprints': {}, 'composite_modifier': 0,
            'interpreter_version': INTERPRETER_VERSION, 'disclaimer': DISCLAIMER,
        }
