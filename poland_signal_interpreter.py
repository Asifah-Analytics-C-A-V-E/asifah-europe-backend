"""
Poland Signal Interpreter v1.0.0 (Jul 12 2026)
===============================================
Analytical layer for rhetoric_tracker_poland.py.

THE FRAME — and it is the whole build:

  Poland joined NATO in MARCH 1999. It is not a recent accession, it is not a
  buffer, and it is not drifting. Nobody is flipping Poland, and Moscow knows
  it.

  So Russia is not trying to flip Poland. Russia is trying to make Poland's
  support for Ukraine TOO EXPENSIVE TO SUSTAIN -- politically, economically,
  socially -- below the threshold of war, indefinitely. Defence24 calls the
  campaign "Phase 0": Russia testing methods and tools, sub-threshold, at a
  tempo that spiked precisely when Poland became the main logistical hub for
  aid to Kyiv.

  Poland is not the buffer. POLAND IS THE SPINE. That is why it is being hit.

  Therefore the instrument is NOT a drift axis (Armenia) and NOT a hedging
  index (Kazakhstan). It is a CONSENSUS-INTEGRITY index:

      Is the consensus holding, and what is the attrition rate?

  Same instrument family as Kazakhstan's hedge integrity. Opposite question.

VECTORS
  1. Hybrid Attack Tempo -- DOMAIN-SPLIT: kinetic / cyber / cognitive. Each
     domain has its own escalation ladder, because conflating them destroys the
     signal. A DDoS and a rail bomb are not the same event.
  2. Casualty Tripwire -- the Black Swan. An anonymous Polish officer, quoted in
     the Defence24 report: "We do not realise how much will change in Poland
     after a single terrorist attack with casualties, carried out as part of
     hybrid operations by the Russian Federation." That is an Article 5 question
     wearing plain clothes, and it gets its own detector.
  3. Polish-Ukrainian Wedge -- THE VECTOR RUSSIA IS ACTIVELY WORKING. On Jul 1
     2026 Polish special services publicly warned that Russia is preparing
     sabotage specifically to inflame Polish-Ukrainian tensions, after President
     Nawrocki stripped Zelensky of Poland's highest state honour over a unit
     named for WWII-era insurgents who massacred Poles. Volhynia is the fracture
     line. Moscow found it and is working it.
  4. Logistics Spine (corridor family member #3, class `military_logistics`) --
     Rzeszow-Jasionka and the rail east. The portable corridor schema's
     `blocker_actors` field, which meant DIPLOMATIC spoilers for TRIPP, here
     means LITERAL SABOTAGE CELLS. Same field, kinetic content.
  5. Instrumentalized Migration (corridor family member #4, INVERTED) -- the
     Belarus border. Reinforced tunnels; 180+ people through one on Dec 11 2025.
     That is not migration, it is a delivery system. Progress signals here are
     BAD news -- the only corridor in the family with inverted polarity.
  6. Cohabitation Fracture -- Nawrocki (president) vs Tusk (government), 2027
     parliamentary elections. A divided state cannot run a unified counter-
     narrative, and Defence24's editor names the cohabitation directly as what
     blunts Poland's disinformation resilience. THAT GAP IS THE TARGET.
  7. Defence-Economic Attrition -- 4.83% of GDP on defence against a 6.3%
     deficit, debt-financed, plus 700km of East Shield. Cost imposed without a
     shot fired -- and the cost is itself a domestic wedge.

MULTIPLIERS (never standalone -- Black Swan discipline)
  - 2027 election clock
  - Volhynia anniversary window (July 11) -- and note the Jul 1 2026 warning was
    pre-positioning for exactly that window.

TEMPO BASELINE
  Consumed from poland_tempo_baseline.py. Deviation reads (surge / anomalous
  quiet) fire ONLY once a 30-day baseline exists. Until then the interpreter
  says "baseline accumulating" and makes no claim. Silence is only a signal
  against a known normal; asserting otherwise would be astrology.

Doctrine: convergence, not prediction. Sensors below, analyst above.
"""

from datetime import datetime, timezone

INTERPRETER_VERSION = '1.0.0'

CONVERGENCE_DISCLAIMER = (
    'This composite is a CONVERGENCE indicator, NOT a probability of action. '
    'Active signals indicate pressure conditions are present; they do not '
    'predict whether or when any specific outcome will occur.'
)


# ============================================================
# CORPUS MATCHER
# ============================================================

def _check_keywords(scan_data, keywords):
    if not keywords:
        return 0
    parts = []
    for key in ('articles_en', 'articles_pl', 'articles_ru'):
        for art in (scan_data.get(key) or []):
            parts.append((art.get('title') or '').lower())
            parts.append((art.get('description') or '').lower())
            parts.append((art.get('summary') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                parts.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('reddit_signals', 'telegram_messages', 'bluesky_signals'):
        for sig in (scan_data.get(key) or []):
            parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(parts)
    if not corpus:
        return 0
    return sum(1 for kw in keywords if kw.lower() in corpus)


# ============================================================
# VECTOR 1 — HYBRID ATTACK TEMPO (DOMAIN-SPLIT)
# Kinetic, cyber and cognitive are DIFFERENT domains with DIFFERENT ladders.
# A DDoS and a rail bomb are not the same event, and averaging them produces a
# number that describes neither.
# ============================================================

KINETIC_KEYWORDS = [
    'sabotage poland', 'railway sabotage', 'rail explosion poland', 'arson poland',
    'arson warsaw', 'marywilska', 'explosion poland rail', 'sabotage rail line ukraine aid',
    'drone incursion poland', 'drone airspace poland', 'airspace violation poland',
    'gps jamming baltic', 'gps jamming poland', 'assassination plot poland',
    'saboteur arrested poland', 'sabotage suspect poland', 'infrastructure attack poland',
    'pipeline sabotage poland', 'sabotage act poland',
    'sabota\u017c', 'dywersja', 'podpalenie',
]

CYBER_KEYWORDS = [
    'cyberattack poland', 'cyber attack poland', 'ddos poland', 'ransomware poland',
    'data wiping malware', 'wiper malware poland', 'energy grid cyberattack',
    'poland power grid hack', 'nuclear research centre hack', 'hospital cyberattack poland',
    'polish railways hack', 'polish press agency hack', 'cyber incident poland',
    'critical infrastructure cyber poland', 'malware poland energy',
    'cyberatak', 'atak hakerski',
]

COGNITIVE_KEYWORDS = [
    'disinformation poland', 'doppelganger operation', 'matryoshka operation',
    'russian propaganda poland', 'bot campaign poland', 'troll farm poland',
    'fake news poland russia', 'information warfare poland', 'deepfake poland',
    'russian trolls poland', 'influence operation poland', 'narrative campaign poland',
    'dezinformacja', 'propaganda rosyjska',
]

# Attribution: Poland NAMING Russia. This is Poland's own voice, and it has a
# rhythm. When attribution tempo drops while attacks continue, the state is
# absorbing hits without saying so -- which is a POLITICAL signal, not a
# security one.
ATTRIBUTION_KEYWORDS = [
    'tusk blames russia', 'poland blames russia', 'abw russia', 'siemoniak russia',
    'polish intelligence russia', 'attributed to russia', 'commissioned by russian services',
    'russian services poland', 'kremlin-linked poland', 'gru poland',
    'poland accuses russia', 'sikorski russia', 'polish security service russia',
    'expelled russian diplomat poland', 'closed russian consulate',
]

_KINETIC_SEVERITY = {
    'nuisance':      ['gps jamming', 'drone incursion', 'airspace violation', 'graffiti'],
    'infrastructure': ['rail explosion', 'railway sabotage', 'arson', 'pipeline sabotage',
                       'infrastructure attack', 'sabotage rail'],
    'casualty':      ['killed', 'dead', 'fatalities', 'casualties', 'injured', 'wounded',
                      'died', 'deaths'],
}


def _score_hybrid_tempo(scan_data, tempo_baseline=None):
    kinetic   = _check_keywords(scan_data, KINETIC_KEYWORDS)
    cyber     = _check_keywords(scan_data, CYBER_KEYWORDS)
    cognitive = _check_keywords(scan_data, COGNITIVE_KEYWORDS)
    attribution = _check_keywords(scan_data, ATTRIBUTION_KEYWORDS)
    total = kinetic + cyber + cognitive

    def _band(n):
        return ('high' if n >= 6 else 'elevated' if n >= 3
                else 'simmering' if n >= 1 else 'quiet')

    # Kinetic ladder rung — WHAT KIND of kinetic, not just how much
    rung, rung_name = 0, 'None'
    if kinetic:
        for level, (name, kws) in enumerate(
                [('Nuisance', _KINETIC_SEVERITY['nuisance']),
                 ('Infrastructure', _KINETIC_SEVERITY['infrastructure']),
                 ('Casualty', _KINETIC_SEVERITY['casualty'])], start=1):
            if _check_keywords(scan_data, kws):
                rung, rung_name = level, name

    domains = {
        'kinetic':   {'signals': kinetic,   'band': _band(kinetic),
                      'rung': rung, 'rung_name': rung_name},
        'cyber':     {'signals': cyber,     'band': _band(cyber)},
        'cognitive': {'signals': cognitive, 'band': _band(cognitive)},
    }

    # Dominant domain — which instrument is Moscow reaching for this cycle?
    dom = max(('kinetic', 'cyber', 'cognitive'), key=lambda d: domains[d]['signals'])
    dominant = dom if domains[dom]['signals'] > 0 else None

    # ── DEVIATION (the Houthi/Hezbollah lesson, inverted for a deniable actor)
    # Hezbollah CLAIMS its attacks, so its silence is signal. Russia NEVER claims
    # anything in Poland -- deniability is the entire architecture. There is no
    # claiming actor to fall silent. So we measure the TAPE, not the actor:
    # attack tempo, attribution tempo, amplification tempo, each against its own
    # 30-day baseline.
    deviation = {'ready': False, 'read': 'Baseline accumulating -- no deviation call yet.'}
    if tempo_baseline and tempo_baseline.get('ready'):
        base = tempo_baseline.get('baselines') or {}
        cur = {'attack': kinetic + cyber, 'amplification': cognitive,
               'attribution': attribution}
        flags = []
        for stream, now in cur.items():
            mean = (base.get(stream) or {}).get('mean_7d')
            if mean is None:
                continue
            if mean >= 1 and now >= mean * 2:
                flags.append(f'{stream} SURGE ({now} vs {mean:.1f} baseline)')
            elif mean >= 3 and now <= mean * 0.3:
                flags.append(f'{stream} ANOMALOUS QUIET ({now} vs {mean:.1f} baseline)')

        if flags:
            read_parts = ['Tempo deviation: ' + '; '.join(flags) + '.']
            # The reads that actually matter -- named, not just flagged.
            amp_hot = any('amplification SURGE' in f for f in flags)
            atk_cold = any('attack ANOMALOUS QUIET' in f for f in flags)
            atr_cold = any('attribution ANOMALOUS QUIET' in f for f in flags)
            if amp_hot and atk_cold:
                read_parts.append(
                    'Amplification is surging while kinetic/cyber activity goes quiet. '
                    'Historically this pattern is consistent with narrative shaping ahead of '
                    'an operation, or with a deliberate shift of instrument. Either way the '
                    'quiet is not peace.')
            if atr_cold and (kinetic + cyber) >= 3:
                read_parts.append(
                    'Attribution tempo has dropped while attacks continue -- the state is '
                    'absorbing hits without publicly naming Moscow. That is a political '
                    'signal about the cohabitation, not a security one.')
            deviation = {'ready': True, 'flags': flags, 'read': ' '.join(read_parts)}
        else:
            deviation = {'ready': True, 'flags': [],
                         'read': 'Tempo within baseline across attack, attribution and '
                                 'amplification streams.'}

    band = _band(total)
    parts = []
    if dominant:
        parts.append(f'Hybrid tempo {band} ({total} signals). Dominant domain this cycle: '
                     f'{dominant.upper()}.')
    if kinetic:
        parts.append(f'Kinetic at rung {rung}/3 ({rung_name}).')
    if cyber >= 3:
        parts.append('Cyber activity clustered -- Poland is the world\'s most-targeted country '
                     'for politically motivated cyber incidents.')
    if attribution:
        parts.append(f'Polish services publicly attributing to Russia ({attribution} signals).')
    if not parts:
        parts.append('Hybrid tape quiet this cycle.')

    return {
        'band': band, 'total_signals': total, 'domains': domains,
        'dominant_domain': dominant, 'kinetic_rung': rung, 'kinetic_rung_name': rung_name,
        'attribution_signals': attribution, 'deviation': deviation,
        'reading': ' '.join(parts),
    }


# ============================================================
# VECTOR 2 — CASUALTY TRIPWIRE (the Black Swan)
# ============================================================

CASUALTY_KEYWORDS = [
    'killed in sabotage', 'deaths sabotage poland', 'casualties sabotage',
    'fatalities poland attack', 'train derailed casualties', 'passengers killed poland',
    'terrorist attack poland', 'bombing poland casualties', 'people killed poland attack',
    'mass casualty poland', 'lethal sabotage', 'deadly attack poland',
]
ARTICLE5_KEYWORDS = [
    'article 5', 'article five nato', 'nato consultations poland', 'article 4 poland',
    'nato invoke', 'collective defence poland', 'nato emergency meeting poland',
]


def _score_casualty_tripwire(scan_data, hybrid):
    casualty = _check_keywords(scan_data, CASUALTY_KEYWORDS)
    article5 = _check_keywords(scan_data, ARTICLE5_KEYWORDS)
    rung = hybrid.get('kinetic_rung', 0)

    if casualty >= 2 or rung >= 3:
        state = 'BREACHED'
        reading = (
            'CASUALTY TRIPWIRE BREACHED. Reporting is consistent with a hybrid operation on '
            'Polish soil that has produced deaths or injuries. This is the threshold Polish '
            'security officials have named as transformative: a serving officer, quoted in the '
            'Defence24 assessment, said the country does not realise how much would change '
            'after a single hybrid attack with casualties. Sub-threshold deniability is what '
            'has made the campaign sustainable; a casualty event is where deniability stops '
            'being cheap. Historically, the pressure to invoke consultation mechanisms rises '
            'sharply at this point.'
            + (' NATO consultation language is ALSO present on the tape.' if article5 else ''))
    elif casualty >= 1:
        state = 'APPROACHING'
        reading = ('Casualty-adjacent reporting present but below cluster threshold. The '
                   'distinction between property damage and human harm is the distinction '
                   'between a sustainable campaign and an unsustainable one.')
    elif rung == 2:
        state = 'ELEVATED'
        reading = ('Kinetic activity at the infrastructure rung -- rail, arson, energy. One rung '
                   'below the casualty threshold. GLOBSEC has assessed that the November 2025 '
                   'rail blasts could have derailed passenger trains had they not been caught '
                   'in time; the gap between infrastructure sabotage and mass casualty is '
                   'timing, not intent.')
    else:
        state = 'QUIET'
        reading = 'No casualty-class signal this cycle.'

    return {'state': state, 'casualty_signals': casualty, 'article5_signals': article5,
            'kinetic_rung': rung, 'reading': reading,
            'black_swan': state == 'BREACHED'}


# ============================================================
# VECTOR 3 — POLISH-UKRAINIAN WEDGE (the vector Russia is working)
# ============================================================

WEDGE_HISTORICAL = [
    'volhynia', 'wolyn', 'volyn massacre', 'upa', 'bandera', 'oun',
    'historical dispute poland ukraine', 'exhumation ukraine poland',
    'wwii massacre poles', 'nawrocki zelensky', 'stripped honour zelensky',
    'order of the white eagle', 'insurgent army unit name',
    'wo\u0142y\u0144', 'rze\u017a wo\u0142y\u0144ska',
]
WEDGE_ECONOMIC = [
    'ukrainian grain poland', 'farmers protest poland ukraine', 'border blockade poland',
    'grain imports ban poland', 'truckers blockade poland ukraine',
    'ukrainian trucks poland', 'agricultural protest poland', 'grain corridor dispute',
    'protest rolnik\u00f3w', 'blokada granicy',
]
WEDGE_REFUGEE = [
    'refugee benefits poland', 'ukrainian refugees benefits', 'refugee fatigue poland',
    '800 plus ukrainians', 'ukrainians welfare poland', 'anti-ukrainian sentiment poland',
    'ukrainian refugees resentment', 'refugee costs poland', 'ukrainians take jobs poland',
    'end temporary protection poland',
]
WEDGE_AMPLIFICATION = [
    'russia inflame polish ukrainian', 'sabotage polish ukrainian tensions',
    'russian trolls poland ukraine', 'divide poland ukraine', 'provocation poland ukraine',
    'disinformation poland ukraine',
]


def _score_wedge(scan_data, refugee_data=None):
    hist = _check_keywords(scan_data, WEDGE_HISTORICAL)
    econ = _check_keywords(scan_data, WEDGE_ECONOMIC)
    refu = _check_keywords(scan_data, WEDGE_REFUGEE)
    amp  = _check_keywords(scan_data, WEDGE_AMPLIFICATION)
    total = hist + econ + refu

    axes = []
    if hist:
        axes.append('historical (Volhynia)')
    if econ:
        axes.append('economic (grain/transit)')
    if refu:
        axes.append('social (refugee fatigue)')

    band = ('high' if total >= 7 else 'elevated' if total >= 4
            else 'simmering' if total >= 1 else 'quiet')

    # THE REFUGEE COUNT IS NOT A HUMANITARIAN SENSOR ON THIS PAGE.
    # It is the ammunition stockpile for the wedge. The number itself is
    # analytically inert -- Poland has hosted ~1M Ukrainians for four years
    # without incident. What matters is whether the RHETORIC ABOUT the number is
    # heating up. The count is the dial; the wedge is the story.
    refugee_context = None
    if refugee_data and refugee_data.get('total'):
        refugee_context = {
            'total':   refugee_data.get('total'),
            'trend':   refugee_data.get('trend'),
            'stale':   refugee_data.get('stale', False),
            'rhetoric_hot': refu >= 2,
        }

    parts = []
    if axes:
        parts.append(f"Wedge active on {len(axes)} axis/axes: {', '.join(axes)}.")
    if amp:
        parts.append(
            'Amplification signals present. On 1 July 2026 Polish special services publicly '
            'warned that Russia was preparing sabotage operations specifically to inflame '
            'Polish-Ukrainian tensions -- a warning issued days before the Volhynia anniversary '
            'window and after the President stripped Zelensky of Poland\'s highest state '
            'honour. Moscow did not create this fracture line; it found it.')
    if refugee_context and refugee_context['rhetoric_hot']:
        parts.append(
            f"Refugee-cost rhetoric is live while roughly {refugee_context['total']:,} displaced "
            'Ukrainians are hosted. The population has been stable for years -- what changes is '
            'the rhetoric about it. The count is the dial; the rhetoric is the signal.')
    elif refugee_context:
        parts.append(
            f"Roughly {refugee_context['total']:,} displaced Ukrainians hosted; refugee-cost "
            'rhetoric quiet this cycle. Presence without friction.')
    if hist and econ:
        parts.append(
            'Historical and economic grievance are co-firing. The 2024 farmer blockades showed '
            'the compound pattern: a grain dispute severs the logistics corridor AND widens the '
            'wedge in the same motion.')
    if not parts:
        parts.append('Poland-Ukraine wedge quiet this cycle.')

    return {
        'band': band, 'total_signals': total, 'axes': axes,
        'historical': hist, 'economic': econ, 'refugee': refu, 'amplification': amp,
        'multi_axis': len(axes) >= 2, 'refugee_context': refugee_context,
        'reading': ' '.join(parts),
    }


# ============================================================
# VECTOR 4 — LOGISTICS SPINE (corridor family #3, `military_logistics`)
# The portable corridor schema, third member. `blocker_actors` meant DIPLOMATIC
# spoilers for TRIPP. Here it means LITERAL SABOTAGE CELLS. Same field.
# ============================================================

SPINE_PROGRESS = [
    'rzeszow hub', 'rzeszow jasionka', 'aid corridor ukraine', 'military aid transit poland',
    'logistics hub ukraine aid', 'nato logistics poland', 'rail corridor ukraine',
    'via carpatia', 'three seas initiative', 'east shield', 'tarcza wschod',
    'poland ukraine rail capacity', 'weapons transit poland',
]
SPINE_THREAT = [
    'railway sabotage', 'rail explosion poland', 'sabotage aid route',
    'attack on logistics poland', 'rzeszow threat', 'drone over rzeszow',
    'blockade aid convoy', 'farmers block aid', 'transit disruption poland',
    'supply chain sabotage poland', 'arson logistics poland', 'depot fire poland',
]
_SPINE_BLOCKERS = {
    'russian_sabotage_cells': ['sabotage', 'saboteur', 'arson', 'explosion', 'gru',
                               'recruited', 'disposable agent', 'dywersja'],
    'domestic_blockade':      ['farmers', 'blockade', 'protest', 'truckers', 'rolnik'],
    'cyber':                  ['cyberattack', 'hack', 'malware', 'ddos'],
}


def _score_logistics_spine(scan_data):
    progress = _check_keywords(scan_data, SPINE_PROGRESS)
    threat   = _check_keywords(scan_data, SPINE_THREAT)

    blockers = []
    if threat:
        for actor, net in _SPINE_BLOCKERS.items():
            if _check_keywords(scan_data, net):
                blockers.append(actor)

    if progress >= 6:
        stage, stage_name = 4, 'Hardened'
    elif progress >= 4:
        stage, stage_name = 3, 'Reinforcing'
    elif progress >= 2:
        stage, stage_name = 2, 'Operational'
    elif progress >= 1:
        stage, stage_name = 1, 'Referenced'
    else:
        stage, stage_name = 0, 'Dormant This Cycle'

    threat_band = ('high' if threat >= 4 else 'elevated' if threat >= 2
                   else 'simmering' if threat >= 1 else 'quiet')

    if threat_band in ('elevated', 'high') and 'russian_sabotage_cells' in blockers:
        status_read = (
            'Constraint signals on the aid corridor with sabotage-class actors present. Poland '
            'became the primary logistics hub for assistance to Kyiv in 2022, and the documented '
            'spike in hybrid attacks coincides with exactly that transformation. Attacks on the '
            'spine are not incidental to the campaign -- they ARE the campaign.')
    elif threat_band in ('elevated', 'high') and 'domestic_blockade' in blockers:
        status_read = (
            'Corridor constraints arising from DOMESTIC blockade rather than sabotage. This is '
            'the compound pattern: a grain or transit dispute severs the corridor and widens the '
            'Poland-Ukraine wedge in the same motion, at no cost to Moscow.')
    elif threat_band != 'quiet':
        status_read = 'Corridor constraint signals present; blocker attribution unclear this cycle.'
    elif stage >= 2:
        status_read = ('Spine operating with constraint rhetoric quiet -- an uncontested window '
                       'for the aid corridor.')
    else:
        status_read = 'Logistics-spine axis quiet this cycle.'

    return {
        # portable corridor schema (shared with TRIPP + Middle Corridor)
        'corridor_name':    'Ukraine Aid Spine (Rzeszow-Jasionka)',
        'class':            'military_logistics',
        'progress_signals': progress,
        'threat_signals':   threat,
        'blocker_actors':   blockers,
        'status_read':      status_read,
        'ts':               datetime.now(timezone.utc).isoformat(),
        'stage':            stage,
        'stage_name':       stage_name,
        'threat_band':      threat_band,
    }


# ============================================================
# VECTOR 5 — INSTRUMENTALIZED MIGRATION (corridor family #4, INVERTED)
# The only corridor in the family where PROGRESS SIGNALS ARE BAD NEWS.
# This is not a migration route. It is a delivery system.
# ============================================================

MIGRATION_KEYWORDS = [
    'belarus border migrants', 'instrumentalized migration', 'weaponized migration',
    'migrant crisis belarus poland', 'border tunnel belarus', 'migrants tunnel poland',
    'push migrants poland border', 'lukashenko migrants', 'border guard poland migrants',
    'illegal crossing belarus poland', 'border wall poland belarus',
    'kryzys migracyjny', 'granica z bia\u0142orusi\u0105',
]
MIGRATION_ESCALATION = [
    'tunnel under border', 'coordinated crossing', 'organized crossing belarus',
    'record crossings belarus', 'surge belarus border', 'border guard injured',
    'shots fired border poland',
]


def _score_instrumentalized_migration(scan_data):
    activity = _check_keywords(scan_data, MIGRATION_KEYWORDS)
    escalation = _check_keywords(scan_data, MIGRATION_ESCALATION)

    band = ('high' if activity >= 6 else 'elevated' if activity >= 3
            else 'simmering' if activity >= 1 else 'quiet')

    if escalation >= 2:
        status_read = (
            'Escalation-class signals on the Belarus border. In December 2025 Polish authorities '
            'exposed reinforced tunnels beneath the frontier -- over 180 people crossed through '
            'one on 11 December alone. Engineered infrastructure of that kind is not a migration '
            'route; it is a delivery system, and its purpose is to strain border resources and '
            'public cohesion rather than to move people.')
    elif band in ('elevated', 'high'):
        status_read = (
            'Belarus-border activity elevated. This corridor runs INVERTED to every other '
            'corridor the platform tracks: progress signals here are bad news, because the flow '
            'is the weapon.')
    elif band == 'simmering':
        status_read = 'Scattered Belarus-border signals; below cluster threshold.'
    else:
        status_read = 'Belarus-border corridor quiet this cycle.'

    return {
        'corridor_name':    'Belarus Border (Instrumentalized Migration)',
        'class':            'instrumentalized_migration',
        'polarity':         'inverted',   # progress == bad news
        'progress_signals': activity,     # NB: "progress" here is adversary progress
        'threat_signals':   escalation,
        'blocker_actors':   ['belarus', 'russia'] if activity >= 3 else [],
        'status_read':      status_read,
        'ts':               datetime.now(timezone.utc).isoformat(),
        'band':             band,
        'escalation_signals': escalation,
    }


# ============================================================
# VECTOR 6 — COHABITATION FRACTURE (the opening)
# ============================================================

COHABITATION_KEYWORDS = [
    'nawrocki tusk', 'presidential veto poland', 'nawrocki veto', 'cohabitation poland',
    'poland political deadlock', 'tusk government crisis', 'pis government conflict',
    'konfederacja', 'poland 2027 election', 'parliamentary election poland',
    'coalition collapse poland', 'poland political crisis', 'president blocks bill poland',
    'kohabitacja', 'weto prezydenta',
]
CONSENSUS_EROSION = [
    'end aid to ukraine poland', 'poland aid fatigue', 'stop supporting ukraine',
    'poland ukraine support falls', 'polls ukraine support poland', 'ukraine fatigue poland',
    'reduce support ukraine poland', 'poland questions ukraine aid',
]


def _score_cohabitation(scan_data):
    fracture = _check_keywords(scan_data, COHABITATION_KEYWORDS)
    erosion  = _check_keywords(scan_data, CONSENSUS_EROSION)

    band = ('high' if fracture >= 6 else 'elevated' if fracture >= 3
            else 'simmering' if fracture >= 1 else 'quiet')

    parts = []
    if fracture:
        parts.append(
            f'Cohabitation friction at {fracture} signals. President Nawrocki and the Tusk '
            'government are in open cohabitation ahead of 2027 parliamentary elections. This is '
            'not incidental to the hybrid campaign -- Defence24\'s assessment names the '
            'cohabitation directly as what blunts Poland\'s disinformation resilience: without a '
            'unified political approach, even good counter-measures remain insufficient. '
            'A divided state cannot run a unified counter-narrative, and THAT GAP IS THE TARGET.')
    if erosion:
        parts.append(f'Aid-fatigue signals present ({erosion}). This is the objective: not to '
                     'flip Poland, but to make the support too expensive to sustain.')
    if not parts:
        parts.append('Cohabitation tape quiet this cycle.')

    return {'band': band, 'fracture_signals': fracture, 'erosion_signals': erosion,
            'reading': ' '.join(parts)}


# ============================================================
# VECTOR 7 — DEFENCE-ECONOMIC ATTRITION (cost imposed without a shot)
# ============================================================

ATTRITION_KEYWORDS = [
    'poland defense budget', 'poland defence spending', 'poland deficit', 'east shield cost',
    'poland military spending gdp', 'defense budget zloty', 'poland debt defense',
    'guns versus butter poland', 'poland fiscal pressure', 'poland budget deficit eu',
    'cybersecurity budget poland', 'poland armament spending',
    'bud\u017cet obronny',
]


def _score_attrition(scan_data, financial_data=None):
    hits = _check_keywords(scan_data, ATTRITION_KEYWORDS)
    band = 'active' if hits >= 3 else 'simmering' if hits >= 1 else 'quiet'

    fin = None
    if financial_data and (financial_data.get('tiles') or {}).get('ATTRITION'):
        t = financial_data['tiles']['ATTRITION']
        if not t.get('unavailable'):
            fin = {'instrument': t.get('name'), 'value': t.get('value'),
                   'change_pct_24h': t.get('change_pct_24h'), 'is_yield': t.get('is_yield')}

    parts = []
    if hits:
        parts.append(
            f'Defence-cost discourse active ({hits} signals). Poland spends 4.83% of GDP on '
            'defence -- nearly triple the NATO minimum and above the United States -- against a '
            '6.3% deficit, well past the EU\'s 3% limit, and the spending is debt-financed. '
            'Russia is imposing cost without firing a shot, and the cost is itself a domestic '
            'wedge: every zloty of armament is a zloty not spent on social goods, which is an '
            'argument that writes itself for anyone who wants to make it.')
    if fin and fin.get('is_yield') and (fin.get('change_pct_24h') or 0) > 1:
        parts.append('Sovereign borrowing costs are rising on the tape -- the armament spiral '
                     'getting measurably dearer.')
    if not parts:
        parts.append('Defence-attrition discourse quiet this cycle.')

    return {'band': band, 'hits': hits, 'financial': fin, 'reading': ' '.join(parts)}


# ============================================================
# THE INSTRUMENT — CONSENSUS INTEGRITY
# Mirror of Kazakhstan's hedging integrity. Opposite question.
# Kazakhstan: is the hedge holding? Poland: is the consensus holding, and at
# what rate is it being spent?
# ============================================================

def _score_consensus_integrity(hybrid, wedge, cohab, spine, attrition):
    """Consensus is spent, not flipped. Each vector debits it differently.

    The scale is 0-100 where 100 = fully intact. This is NOT a probability and
    NOT a forecast -- it is a running account of pressure ON the consensus,
    which is exactly what Russia's campaign is designed to draw down."""
    integrity = 100

    # The wedge is the primary instrument of attrition -- it is what Moscow is
    # actively working, so it debits hardest.
    integrity -= min(30, wedge['total_signals'] * 3)
    if wedge['multi_axis']:
        integrity -= 8          # multi-axis grievance compounds
    if wedge['amplification']:
        integrity -= 6          # someone is actively pushing on it

    # Cohabitation is the OPENING -- the gap the campaign works through.
    integrity -= min(20, cohab['fracture_signals'] * 2)
    integrity -= min(12, cohab['erosion_signals'] * 4)

    # Attack tempo raises the cost of holding the line.
    integrity -= min(15, hybrid['total_signals'] * 1.5)

    # Attacks on the spine attack the thing the consensus DELIVERS.
    if spine['threat_band'] in ('elevated', 'high'):
        integrity -= 8

    # Defence-cost discourse is the economic half of the attrition.
    integrity -= min(8, attrition['hits'] * 2)

    # ATTRIBUTION IS RESILIENCE, NOT DAMAGE. A state naming its attacker in
    # public is a state whose consensus is functioning. Credit it back.
    integrity += min(10, hybrid['attribution_signals'] * 2)

    integrity = max(0, min(100, int(round(integrity))))

    if integrity >= 80:
        state = 'holding'
        reading = (f'Consensus integrity HOLDING ({integrity}/100). Pressure present but the '
                   'support-for-Ukraine consensus is not visibly fracturing this cycle.')
    elif integrity >= 60:
        state = 'strained'
        reading = (f'Consensus integrity STRAINED ({integrity}/100). Attrition is registering. '
                   'The campaign is not designed to flip Poland -- it is designed to make '
                   'holding the line expensive, and the tape shows the bill being run up.')
    elif integrity >= 40:
        state = 'fracturing'
        reading = (f'Consensus integrity FRACTURING ({integrity}/100). Multiple attrition vectors '
                   'are live simultaneously. This is the condition the hybrid campaign exists to '
                   'produce, and it is the condition under which Polish support for Ukraine has '
                   'historically become a contested domestic question rather than a settled one.')
    else:
        state = 'contested'
        reading = (f'Consensus integrity CONTESTED ({integrity}/100). Support for Ukraine reads as '
                   'an open domestic argument on this cycle\'s tape rather than a national given.')

    return {'integrity': integrity, 'state': state, 'reading': reading}


# ============================================================
# MULTIPLIERS
# ============================================================

def _election_clock(scan_data, cohab):
    hits = _check_keywords(scan_data, [
        'poland 2027 election', 'parliamentary election poland', 'election campaign poland',
        'poland polls', 'wybory parlamentarne'])
    if hits >= 2 and cohab['band'] in ('elevated', 'high'):
        return {'active': True, 'multiplier': 0.15, 'hits': hits,
                'reading': 'Election-window conditions amplifying an active cohabitation fracture.'}
    return {'active': False, 'multiplier': 0.0, 'hits': hits, 'reading': ''}


def _volhynia_window(wedge):
    """July 11 is the Volhynia massacre anniversary -- the single most
    combustible date on the Polish-Ukrainian calendar. AMPLIFIER ONLY: the
    anniversary contributes nothing on a quiet tape.

    Note the timing of the real world here: Polish services issued their
    Russia-will-inflame-Polish-Ukrainian-tensions warning on July 1 2026, ten
    days before the window. That is what pre-positioning looks like."""
    now = datetime.now(timezone.utc)
    in_window = (now.month == 7 and 1 <= now.day <= 21)
    if not in_window or wedge['band'] == 'quiet':
        return {'active': False, 'multiplier': 0.0, 'in_window': in_window, 'reading': ''}
    mult = 0.25 if wedge['historical'] else 0.12
    return {
        'active': True, 'multiplier': mult, 'in_window': True,
        'reading': ('Volhynia anniversary window (July 11) amplifying a live wedge. This is the '
                    'most combustible date on the Polish-Ukrainian calendar, and Polish special '
                    'services warned on 1 July 2026 that Russia was preparing sabotage aimed '
                    'precisely at inflaming those tensions.'),
    }


# ============================================================
# SO WHAT
# ============================================================

def _build_so_what(consensus, hybrid, casualty, wedge, spine, migration, cohab,
                   attrition, elec, volhynia):
    if casualty['black_swan']:
        priority, scenario = 'critical', 'CASUALTY TRIPWIRE BREACHED — hybrid attack with human harm'
    elif consensus['state'] in ('fracturing', 'contested'):
        priority, scenario = 'high', f"Consensus {consensus['state']} — attrition registering"
    elif (hybrid['band'] == 'high' or wedge['band'] == 'high'
          or casualty['state'] == 'APPROACHING'):
        priority, scenario = 'high', 'Hybrid pressure high'
    elif (consensus['state'] == 'strained' or hybrid['band'] == 'elevated'
          or wedge['multi_axis']):
        priority, scenario = 'elevated', f"Consensus {consensus['state']}"
    else:
        priority, scenario = 'normal', 'Baseline — consensus holding'

    parts = [
        'Poland has been in NATO since 1999 and is not drifting: nobody is flipping Poland, and '
        'Moscow knows it. So the campaign is not aimed at alignment -- it is aimed at COST. '
        'Russia is working to make Poland\'s support for Ukraine too expensive to sustain, '
        'below the threshold of war, indefinitely. Poland is not the buffer; Poland is the '
        'spine, which is precisely why it is being hit. The sensor therefore asks whether the '
        'consensus is holding and at what rate it is being spent.'
    ]
    parts.append(consensus['reading'])
    if casualty['state'] != 'QUIET':
        parts.append(casualty['reading'])
    if hybrid['band'] != 'quiet':
        parts.append(hybrid['reading'])
    if hybrid['deviation'].get('ready') and hybrid['deviation'].get('flags'):
        parts.append(hybrid['deviation']['read'])
    if wedge['band'] != 'quiet':
        parts.append(wedge['reading'])
    if spine['threat_band'] != 'quiet' or spine['stage'] >= 2:
        parts.append(spine['status_read'])
    if migration['band'] != 'quiet':
        parts.append(migration['status_read'])
    if cohab['band'] != 'quiet':
        parts.append(cohab['reading'])
    if attrition['band'] != 'quiet':
        parts.append(attrition['reading'])
    if volhynia['active']:
        parts.append(volhynia['reading'])
    if elec['active']:
        parts.append(elec['reading'])
    if (hybrid['band'] == 'quiet' and wedge['band'] == 'quiet'
            and cohab['band'] == 'quiet' and spine['threat_band'] == 'quiet'):
        parts.append('All pressure vectors quiet this cycle. Silence is a valid analytical '
                     'output; manufactured signal is not.')

    return {
        'scenario': scenario, 'priority': priority, 'assessment': ' '.join(parts),
        'situation': scenario, 'consensus_integrity': consensus['integrity'],
        'disclaimer': CONVERGENCE_DISCLAIMER,
    }


# ============================================================
# TOP SIGNALS
# ============================================================

def _build_top_signals(consensus, hybrid, casualty, wedge, spine, migration,
                       cohab, attrition):
    s = []

    if casualty['black_swan']:
        s.append({'priority': 1, 'category': 'casualty_tripwire',
                  'short_text': 'BLACK SWAN: casualty tripwire BREACHED — hybrid attack with human harm',
                  'long_text': casualty['reading'], 'pressure_type': 'kinetic'})
    elif casualty['state'] == 'APPROACHING':
        s.append({'priority': 1, 'category': 'casualty_tripwire',
                  'short_text': 'Casualty tripwire APPROACHING — human-harm reporting below cluster threshold',
                  'long_text': casualty['reading'], 'pressure_type': 'kinetic'})
    elif casualty['state'] == 'ELEVATED':
        s.append({'priority': 2, 'category': 'casualty_tripwire',
                  'short_text': 'Kinetic at infrastructure rung — one below the casualty threshold',
                  'long_text': casualty['reading'], 'pressure_type': 'kinetic'})

    if consensus['state'] in ('fracturing', 'contested'):
        s.append({'priority': 1, 'category': 'consensus_integrity',
                  'short_text': f"Consensus {consensus['state'].upper()} ({consensus['integrity']}/100)",
                  'long_text': consensus['reading'], 'pressure_type': 'diplomatic'})
    elif consensus['state'] == 'strained':
        s.append({'priority': 2, 'category': 'consensus_integrity',
                  'short_text': f"Consensus STRAINED ({consensus['integrity']}/100) — attrition registering",
                  'long_text': consensus['reading'], 'pressure_type': 'diplomatic'})

    if wedge['multi_axis'] or wedge['band'] in ('elevated', 'high'):
        s.append({'priority': 1 if wedge['multi_axis'] and wedge['amplification'] else 2,
                  'category': 'ukraine_wedge',
                  'short_text': f"Poland-Ukraine wedge {wedge['band']} on {len(wedge['axes'])} axis/axes"
                                + (' + amplification' if wedge['amplification'] else ''),
                  'long_text': wedge['reading'], 'pressure_type': 'cognitive'})

    if hybrid['band'] in ('elevated', 'high'):
        d = hybrid['dominant_domain']
        s.append({'priority': 2, 'category': 'hybrid_tempo',
                  'short_text': f"Hybrid tempo {hybrid['band']} — dominant domain {str(d).upper()}"
                                + (f", kinetic rung {hybrid['kinetic_rung']}/3"
                                   if hybrid['kinetic_rung'] else ''),
                  'long_text': hybrid['reading'],
                  'pressure_type': d if d in ('kinetic', 'cyber') else 'cognitive'})

    dev = hybrid.get('deviation') or {}
    if dev.get('ready') and dev.get('flags'):
        s.append({'priority': 2, 'category': 'tempo_deviation',
                  'short_text': 'TEMPO DEVIATION: ' + '; '.join(dev['flags'])[:80],
                  'long_text': dev['read'], 'pressure_type': 'cognitive'})

    if spine['threat_band'] in ('elevated', 'high'):
        s.append({'priority': 2, 'category': 'logistics_spine',
                  'short_text': f"Aid spine under constraint ({spine['threat_band']})"
                                + (f" — blockers: {', '.join(spine['blocker_actors'])}"
                                   if spine['blocker_actors'] else ''),
                  'long_text': spine['status_read'], 'pressure_type': 'kinetic'})

    if migration['band'] in ('elevated', 'high'):
        s.append({'priority': 2 if migration['escalation_signals'] >= 2 else 3,
                  'category': 'instrumentalized_migration',
                  'short_text': f"Belarus border {migration['band']} (inverted corridor — flow is the weapon)",
                  'long_text': migration['status_read'], 'pressure_type': 'hybrid'})

    if cohab['band'] in ('elevated', 'high') or cohab['erosion_signals']:
        s.append({'priority': 2 if cohab['erosion_signals'] else 3,
                  'category': 'cohabitation',
                  'short_text': f"Cohabitation fracture {cohab['band']}"
                                + (f" + aid-fatigue signals ({cohab['erosion_signals']})"
                                   if cohab['erosion_signals'] else ''),
                  'long_text': cohab['reading'], 'pressure_type': 'diplomatic'})

    if attrition['band'] == 'active':
        s.append({'priority': 3, 'category': 'defence_attrition',
                  'short_text': f"Defence-cost discourse active ({attrition['hits']} signals)",
                  'long_text': attrition['reading'], 'pressure_type': 'economic'})

    if hybrid['attribution_signals'] >= 3:
        s.append({'priority': 3, 'category': 'attribution_resilience',
                  'short_text': f"GREEN: Polish services publicly attributing to Russia "
                                f"({hybrid['attribution_signals']} signals)",
                  'long_text': ('A state that names its attacker in public is a state whose '
                                'consensus is functioning. Attribution is resilience, and it is '
                                'credited back to consensus integrity rather than debited from it.'),
                  'pressure_type': 'diplomatic'})

    if spine['stage'] >= 3 and spine['threat_band'] == 'quiet':
        s.append({'priority': 3, 'category': 'spine_hardening',
                  'short_text': f"GREEN: aid spine {spine['stage_name'].lower()} with constraints quiet",
                  'long_text': spine['status_read'], 'pressure_type': 'diplomatic'})

    s.sort(key=lambda x: x['priority'])
    return s[:8]


# ============================================================
# MAIN
# ============================================================

def interpret_signals(scan_data):
    """Entry point. scan_data may carry:
        refugee_data    (poland_refugee_tracker — the wedge's ammunition dial)
        financial_data  (poland_financial_pulse — the attrition tile)
        tempo_baseline  (poland_tempo_baseline — deviation reads)
    All optional; all absence-honest."""
    try:
        tempo_baseline = scan_data.get('tempo_baseline')
        refugee_data   = scan_data.get('refugee_data')
        financial_data = scan_data.get('financial_data')

        hybrid    = _score_hybrid_tempo(scan_data, tempo_baseline)
        casualty  = _score_casualty_tripwire(scan_data, hybrid)
        wedge     = _score_wedge(scan_data, refugee_data)
        spine     = _score_logistics_spine(scan_data)
        migration = _score_instrumentalized_migration(scan_data)
        cohab     = _score_cohabitation(scan_data)
        attrition = _score_attrition(scan_data, financial_data)

        consensus = _score_consensus_integrity(hybrid, wedge, cohab, spine, attrition)

        elec     = _election_clock(scan_data, cohab)
        volhynia = _volhynia_window(wedge)

        so_what = _build_so_what(consensus, hybrid, casualty, wedge, spine, migration,
                                 cohab, attrition, elec, volhynia)
        top_signals = _build_top_signals(consensus, hybrid, casualty, wedge, spine,
                                         migration, cohab, attrition)

        # Composite. Consensus integrity is INVERTED into the modifier: a lower
        # integrity means more pressure. Multipliers amplify only.
        composite = int(round((100 - consensus['integrity']) * 0.5
                              * (1.0 + elec['multiplier'] + volhynia['multiplier'])))
        if casualty['black_swan']:
            composite += 30

        fingerprints = {
            'consensus_integrity': {
                'integrity': consensus['integrity'], 'state': consensus['state'],
            },
            'hybrid_tempo': {
                'band': hybrid['band'], 'dominant_domain': hybrid['dominant_domain'],
                'kinetic_rung': hybrid['kinetic_rung'],
                'domains': {k: v['band'] for k, v in hybrid['domains'].items()},
                'deviation_ready': hybrid['deviation'].get('ready', False),
                'deviation_flags': hybrid['deviation'].get('flags', []),
            },
            'casualty_tripwire': {
                'state': casualty['state'], 'black_swan': casualty['black_swan'],
            },
            'ukraine_wedge': {
                'band': wedge['band'], 'axes': wedge['axes'],
                'multi_axis': wedge['multi_axis'], 'amplification': wedge['amplification'],
            },
            'logistics_spine': {
                'corridor_name': spine['corridor_name'], 'class': spine['class'],
                'stage': spine['stage'], 'threat_band': spine['threat_band'],
                'blocker_actors': spine['blocker_actors'],
            },
            'instrumentalized_migration': {
                'corridor_name': migration['corridor_name'], 'class': migration['class'],
                'polarity': migration['polarity'], 'band': migration['band'],
            },
            'cohabitation': {
                'band': cohab['band'], 'erosion_signals': cohab['erosion_signals'],
            },
        }

        return {
            'so_what': so_what,
            'top_signals': top_signals,
            'consensus_integrity':        consensus,
            'hybrid_tempo':               hybrid,
            'casualty_tripwire':          casualty,
            'ukraine_wedge':              wedge,
            'logistics_spine':            spine,
            'instrumentalized_migration': migration,
            'cohabitation':               cohab,
            'defence_attrition':          attrition,
            'election_clock':             elec,
            'volhynia_window':            volhynia,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':         composite,
            'interpreter_version':        INTERPRETER_VERSION,
            'interpreted_at':             datetime.now(timezone.utc).isoformat(),
            'disclaimer':                 CONVERGENCE_DISCLAIMER,
        }

    except Exception as e:
        print(f'[Poland Interpreter] Error: {str(e)[:140]}')
        return {
            'so_what': {'scenario': 'Interpreter error', 'priority': 'normal',
                        'assessment': str(e)[:200], 'situation': 'Interpreter error',
                        'consensus_integrity': 100, 'disclaimer': CONVERGENCE_DISCLAIMER},
            'top_signals': [],
            'consensus_integrity': {'integrity': 100, 'state': 'holding', 'reading': ''},
            'hybrid_tempo': {'band': 'quiet', 'total_signals': 0, 'domains': {},
                             'dominant_domain': None, 'kinetic_rung': 0,
                             'kinetic_rung_name': 'None', 'attribution_signals': 0,
                             'deviation': {'ready': False, 'read': ''}, 'reading': ''},
            'casualty_tripwire': {'state': 'QUIET', 'black_swan': False,
                                  'casualty_signals': 0, 'article5_signals': 0,
                                  'kinetic_rung': 0, 'reading': ''},
            'ukraine_wedge': {'band': 'quiet', 'total_signals': 0, 'axes': [],
                              'multi_axis': False, 'amplification': 0, 'historical': 0,
                              'economic': 0, 'refugee': 0, 'refugee_context': None,
                              'reading': ''},
            'logistics_spine': {'corridor_name': 'Ukraine Aid Spine (Rzeszow-Jasionka)',
                                'class': 'military_logistics', 'stage': 0,
                                'stage_name': 'Unknown', 'threat_band': 'quiet',
                                'blocker_actors': [], 'progress_signals': 0,
                                'threat_signals': 0, 'status_read': ''},
            'instrumentalized_migration': {'corridor_name': 'Belarus Border',
                                           'class': 'instrumentalized_migration',
                                           'polarity': 'inverted', 'band': 'quiet',
                                           'progress_signals': 0, 'threat_signals': 0,
                                           'escalation_signals': 0, 'status_read': ''},
            'cohabitation': {'band': 'quiet', 'fracture_signals': 0,
                             'erosion_signals': 0, 'reading': ''},
            'defence_attrition': {'band': 'quiet', 'hits': 0, 'financial': None, 'reading': ''},
            'election_clock': {'active': False, 'multiplier': 0.0, 'hits': 0, 'reading': ''},
            'volhynia_window': {'active': False, 'multiplier': 0.0, 'in_window': False,
                                'reading': ''},
            'cross_theater_fingerprints': {},
            'composite_modifier': 0,
            'interpreter_version': INTERPRETER_VERSION,
            'error': str(e)[:200],
        }
