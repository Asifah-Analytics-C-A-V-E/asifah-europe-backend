"""
russia_signal_interpreter.py
Asifah Analytics -- Europe Backend Module
v1.3.0 -- Nov 5, 2026 (v1.2.0 Nov 3; v1.1.0 May 17 2026)

v1.3.0 -- HYBRID IS NOT KINETIC, AND "95% CERTAIN" IS NOT "CONFIRMED"
  * The hybrid red line now says WHAT KIND of attack it saw: 'cyber',
    'sabotage' (cables, pipelines, arson, explosions) or 'jamming' (GPS),
    read from the matched headlines. The signal carries 'mode' and its text
    says "CYBER, not kinetic" so no reader takes a hack for a strike.
  * Renamed "Confirmed Hybrid Attack..." -> "Russian-Attributed Hybrid Attack
    on NATO Infrastructure". The text says "officially attributed" only when a
    matched headline has a government / NATO / intelligence voice blaming
    Russia; otherwise "attributed in press reporting, not officially confirmed".

v1.2.0 -- EVIDENCE, THE WAR FLOOR, AND A TOPLINE
  * The ground_ops vector floors at L4 because the war is the baseline. v1.1
    read that floor as "Russian major advance BREACHED" and, with Ukraine's
    actor at L1, "Ukraine collapse APPROACHING" -- on EVERY scan. A standing
    war is not an advance. Those two lines now need evidence (2+ outlets on a
    breakthrough / city-capture / front-collapse phrase) or ground_ops L5.
  * Every headline-triggered line ("putin warns", one Cuba headline, one
    "trump putin" story) is now scored on the WHOLE corpus with publisher
    counting (europe_evidence): BREACHED needs 2 outlets. Vector levels (which
    obey the 2-outlet rule since tracker v1.5.0) can still set a line's status.
  * The two de-escalation "red lines" (talks, ceasefire framework) left the
    red-line list -- talks were being counted as "approaching red lines". They
    live in the TALKS TRACK (dated baseline + live read) and green lines.
  * Green lines read the whole corpus, not two actors' top-5 headlines.
  * top_signals: a breached red line emits L4, never L5 (L5 assertion rule:
    only the kinetic ladder may assert L5).
  * top_indicator, THIN READ, talks_track.

Signal interpretation engine for the Russia Rhetoric Tracker.

v1.1 adds CARIBBEAN FOOTHOLD RECOGNITION — recognizing when Russia is
forward-staging kinetic capability in Cuba (the structural 1962 pattern,
not just SIGINT/oil access). The Axios disclosure of 300 drones to Cuba
from Russia + Iran requires the Russia interpreter to recognize Cuba as
a STRATEGIC theater, not just an axis-of-resistance partner.

Russia's analytical frame is now SIX-WAY:

  1. Is Russia signaling conventional escalation on NATO's eastern flank?
     (Baltic, Poland, Kaliningrad, Finland, Suwalki Gap)
  2. Is nuclear rhetoric coercive posturing vs. genuine doctrinal signal?
     (Medvedev/Putin language ladder, Iskander, SSBN, doctrine shifts)
  6. [v1.1] Is Russia forward-staging kinetic capability in Cuba?
     (drones, advisers, weapons transfer — the 1962 Caribbean foothold pattern
     in multilateralized 21st-century form, often coordinated with Iran)

  3. Is the Ukraine war trajectory shifting?
     (Russian gains = emboldened; losses = desperate escalation)
     (Ukrainian diplomatic posture = off-ramp or entrenchment)
  4. Is Russia coordinating cross-theater pressure simultaneously?
     (Iran weapons, DPRK ammunition, Cuba/Venezuela WHA, Arctic)
  5. Are Arctic / GIUK Gap signals above baseline?
     (Northern Fleet, SSBN patrols, Svalbard, GIUK, Greenland convergence)

KEY ANALYTICAL INSIGHT:
Russia's escalation ladder is multi-flank. Unlike China (Taiwan-focused)
or Iran (ME-focused), Russia can pressure NATO via ALL five vectors
simultaneously. Maximum pressure scenario = all five elevated at once.
Partial pressure = coercion without commitment to kinetics.

The Ukraine war creates a paradox:
  - Russian gains → emboldened, more aggressive NATO posture signals
  - Russian losses → desperate, more likely to escalate with nuclear rhetoric
  - Ukrainian diplomatic openness → green line (off-ramp possible)
  - Ukrainian entrenchment + US aid suspension → Russian opportunity window

CROSS-THEATER NOTE:
Russia's fingerprint is written to shared Redis key and is readable by:
  - ME backend (Iran-Russia strategic partnership)
  - WHA backend (Cuba, Venezuela, Nicaragua)
  - Europe backend (Ukraine, Baltic, Arctic)
Russia is the ONLY theater actor that directly affects ALL other theaters.

Author: RCGG / Asifah Analytics
"""

from datetime import datetime, timezone

from europe_evidence import build_corpus, score_line, find, corpus_health

INTERPRETER_VERSION = '1.3.0'
THIN_MIN_ARTICLES = 60

# Evidence triggers: (breach phrases, approach phrases). Context: the phrase
# lists below are about Russia by construction (they name Russia, Moscow, the
# Kremlin, Russian forces or a Russian platform) -- generic words stay out.
RED_LINE_TRIGGERS = {
    'nuclear_rhetoric_escalation': (
        ['putin threatens nuclear', 'medvedev threatens nuclear', 'russia threatens nuclear',
         'kremlin threatens nuclear', 'russia nuclear ultimatum', 'russia changes nuclear doctrine',
         'russia lowers nuclear threshold'],
        ['medvedev nuclear', 'putin nuclear', 'russian nuclear doctrine', 'russia nuclear warning',
         'kremlin nuclear warning', 'oreshnik']),
    'tactical_nuclear_deployment': (
        ['russia deploys tactical nuclear', 'nuclear warheads moved', 'nuclear weapons moved to belarus',
         'russia nuclear drills with live warheads'],
        ['tactical nuclear exercise', 'russia nuclear drills', 'nuclear-capable iskander', 'non-strategic nuclear']),
    'kaliningrad_escalation': (
        ['russia reinforces kaliningrad', 'kaliningrad blockade', 'iskander deployed to kaliningrad'],
        ['kaliningrad', 'suwalki']),
    'article5_trigger_language': (
        ['article 5 invoked', 'invokes article 5', 'attack on nato territory', 'russian strike on nato territory'],
        ['article 5', 'article 4', 'invokes article 4', 'nato airspace violation', 'russian drones over poland',
         'russian drones over romania', 'russian jets violate']),
    'suwalki_gap_threat': (
        ['suwalki gap blockade', 'russian troops near suwalki'],
        ['suwalki gap', 'suwalki corridor']),
    'russian_major_advance': (
        ['russia captures pokrovsk', 'russia captures kostiantynivka', 'russia captures zaporizhzhia',
         'russia captures kramatorsk', 'russia captures sloviansk', 'russian breakthrough',
         'front collapses', 'ukrainian lines collapse', 'russia takes control of the city'],
        ['russia claims capture', 'russian forces captured', 'russia advances toward',
         'encirclement', 'ukrainian troops withdraw from', 'ukraine withdraws from']),
    'ukraine_collapse_signal': (
        ['ukrainian front collapses', 'ukraine front collapse', 'mass surrender of ukrainian'],
        ['ukraine manpower crisis', 'ukrainian desertions', 'ukraine retreats', 'ukrainian retreat']),
    'us_aid_suspension': (
        ['us suspends aid to ukraine', 'us halts weapons to ukraine', 'us halts intelligence sharing',
         'pentagon pauses weapons', 'trump halts aid'],
        ['aid pause', 'weapons delay', 'patriot delay', 'intelligence sharing problems',
         'starlink access problems', 'us eases sanctions on russia']),
    'ssbn_unusual_deployment': (
        ['russian ballistic missile submarine surfaced', 'ssbn surge', 'russian submarine surge'],
        ['russian submarine', 'northern fleet submarine', 'ballistic missile submarine']),
    'arctic_territorial_escalation': (
        ['russia claims svalbard', 'russian troops svalbard', 'svalbard incident'],
        ['svalbard', 'arctic claim', 'arctic territorial']),
    'giuk_gap_surge': (
        ['giuk gap russian surge'],
        ['giuk gap', 'giuk']),
    'cross_theater_coordination': (
        ['north korean troops in russia', 'iran supplies russia missiles', 'dprk troops fighting'],
        ['north korea russia weapons', 'iran russia drones', 'dprk russia', 'russia iran military cooperation']),
    'hybrid_infrastructure_attack': (
        ['russia blamed for sabotage', 'russian sabotage', 'russia behind cyberattack',
         'undersea cable cut russia', 'russian-linked arson'],
        ['sabotage', 'undersea cable', 'gps jamming', 'cyberattack', 'hybrid attack', 'shadow fleet tanker']),
    'russia_cuba_kinetic_weapons_transfer': (
        ['russia drones to cuba', 'russian drones delivered to cuba', 'russia weapons shipment cuba'],
        ['russia cuba drone', 'russia cuba weapons', 'russia cuba military']),
    'russia_cuban_soldiers_procurement': (
        ['cuban soldiers fighting for russia', 'cubans recruited by russia', 'cuban mercenaries russia'],
        ['cuban soldiers ukraine', 'cuban fighters russia', 'cuban recruits russia']),
    'russia_iran_cuba_coalition_active': (
        ['russia and iran send drones to cuba'],
        ['iran cuba drone', 'iranian advisers havana']),
}

# Talks track: date-stamped background (NOT scored). Review when the round lands.
TALKS_BASELINE = {
    'as_of': '2026-10-25',
    'round': ('Trilateral US-Russia-Ukraine round planned for the first half of November in Abu Dhabi '
              '(Kremlin: after Nov 4). A similar round expected in October never happened.'),
    'positions': ('Moscow: large territorial concessions and no NATO for Ukraine; talks on long-term '
                  'security arrangements, not a short truce. Kyiv: security guarantees, 10 years of army '
                  'funding, Europe at the table.'),
    'washington': ('The US has eased some sanctions on Moscow and agreed to buy Russian diesel; it brokered a '
                   'localised ceasefire in Oleshky and has criticised Ukrainian strikes on Russian energy.'),
    'sources': ['https://www.aljazeera.com/news/2026/10/23/russia-ukraine-talks-planned-for-november-in-uae-kremlin',
                'https://www.euronews.com/2026/10/25/ukraines-zelenskyy-confirms-trilateral-talks-with-russia-and-us-to-take-place-in-november'],
}
TALKS_ACTIVE = ['abu dhabi talks', 'talks in abu dhabi', 'trilateral talks', 'trilateral meeting',
                'delegations met', 'round of talks', 'peace talks resume', 'ceasefire agreed', 'truce agreed',
                'prisoner exchange', 'witkoff', 'dmitriev', 'umerov', 'medinsky']
TALKS_STRAIN = ['talks postponed', 'talks cancelled', 'talks collapse', 'walked out', 'no progress',
                'ultimatum', 'rejects proposal', 'rejected the proposal', 'talks stall']


# ============================================================
# RED LINE DEFINITIONS (escalation triggers)
# ============================================================
RED_LINES = [

    # ── Category A: Nuclear signals ───────────────────────────
    {
        'id':       'nuclear_rhetoric_escalation',
        'label':    'Nuclear Rhetoric Above Doctrinal Baseline',
        'detail':   'Putin/Medvedev/Kremlin uses nuclear language beyond routine deterrence -- '
                    'specific threat language, deployment signals, or doctrine change',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '☢️',
        'category': 'nuclear',
        'source':   'Russian nuclear doctrine: rhetoric escalation historically precedes '
                    'deployment posture changes. Medvedev is the designated nuclear coercion instrument.',
    },
    {
        'id':       'tactical_nuclear_deployment',
        'label':    'Tactical Nuclear Deployment Signal',
        'detail':   'Credible signal of tactical nuclear weapons deployment -- '
                    'Iskander nuclear warheads, Belarus deployment, submarine surge',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '💣',
        'category': 'nuclear',
        'source':   'NATO doctrine: tactical nuclear deployment is the threshold before use. '
                    'Belarus deployment (2023) established precedent.',
    },

    # ── Category B: NATO Flank triggers ───────────────────────
    {
        'id':       'kaliningrad_escalation',
        'label':    'Kaliningrad Military Escalation',
        'detail':   'Unusual military buildup or Iskander deployment in Kaliningrad -- '
                    'threatens Baltic states and Suwalki Gap connectivity',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🗺️',
        'category': 'nato_flank',
        'source':   'Strategic geography: Kaliningrad is Russia\'s NATO flank pressure point. '
                    'Suwalki Gap closure would isolate Baltic states from NATO.',
    },
    {
        'id':       'article5_trigger_language',
        'label':    'Article 5 Trigger Language / NATO Attack Signal',
        'detail':   'Russian actions or statements that could trigger NATO Article 5 collective defense -- '
                    'attack on NATO member territory, infrastructure, or personnel',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🔴',
        'category': 'nato_flank',
        'source':   'NATO founding document: Article 5 invocation would be unprecedented. '
                    'Baltic cable attacks, airspace violations, proxy attacks approach this threshold.',
    },
    {
        'id':       'suwalki_gap_threat',
        'label':    'Suwalki Gap Closure Threat',
        'detail':   'Russian/Belarusian signals suggesting intent to close the Suwalki Gap -- '
                    'would physically isolate Estonia, Latvia, Lithuania from NATO',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🚪',
        'category': 'nato_flank',
        'source':   'NATO strategic vulnerability: Suwalki Corridor is 65km between '
                    'Kaliningrad and Belarus -- the single land connection to Baltic NATO members.',
    },

    # ── Category C: Ukraine war trajectory ───────────────────
    {
        'id':       'russian_major_advance',
        'label':    'Russian Major Territorial Advance in Ukraine',
        'detail':   'Russia achieves significant territorial gain -- signals military momentum '
                    'and emboldens further NATO pressure signals',
        'severity': 2,
        'color':    '#f97316',
        'icon':     '⚔️',
        'category': 'ukraine_front',
        'source':   'Pattern: Russian territorial gains historically correlate with '
                    'increased Kremlin risk appetite on NATO pressure signals.',
    },
    {
        'id':       'ukraine_collapse_signal',
        'label':    'Ukrainian Military Cohesion Collapse Signal',
        'detail':   'Credible signals of Ukrainian front collapse, major city loss, '
                    'or morale/supply breakdown -- creates Russian opportunity window',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🏳️',
        'category': 'ukraine_front',
        'source':   'Strategic: Ukrainian collapse would remove the primary NATO '
                    'pressure absorption point and shift Russian attention to NATO directly.',
    },
    {
        'id':       'us_aid_suspension',
        'label':    'US Ukraine Aid Suspension',
        'detail':   'United States suspends or significantly reduces military aid to Ukraine -- '
                    'creates Russian opportunity window and emboldens pressure on NATO',
        'severity': 2,
        'color':    '#f97316',
        'icon':     '💰',
        'category': 'ukraine_front',
        'source':   'Pattern: Russian offensive tempo historically correlates with '
                    'Western aid uncertainty. Trump administration creates structural uncertainty.',
    },

    # ── Category D: Arctic signals ───────────────────────────
    {
        'id':       'ssbn_unusual_deployment',
        'label':    'Russian SSBN Unusual Deployment Pattern',
        'detail':   'Russian ballistic missile submarine deployment above normal patrol pattern -- '
                    'GIUK Gap surge, Mediterranean deployment, or simultaneous multi-boat patrol',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🌊',
        'category': 'arctic',
        'source':   'NATO ASWRG doctrine: SSBN surge is the most significant nuclear '
                    'alert signal short of weapons deployment. Historically precedes '
                    'major political pressure campaigns.',
    },
    {
        'id':       'arctic_territorial_escalation',
        'label':    'Arctic Territorial Escalation',
        'detail':   'Russia makes aggressive move on Arctic territorial claims -- '
                    'Svalbard militarization, Arctic shelf dispute force, '
                    'or Northern Sea Route closure threat',
        'severity': 2,
        'color':    '#f97316',
        'icon':     '🧊',
        'category': 'arctic',
        'source':   'Arctic Council breakdown (post-2022) removed diplomatic channel. '
                    'Svalbard Treaty gives Russia access rights -- Norway is the trip wire.',
    },
    {
        'id':       'giuk_gap_surge',
        'label':    'GIUK Gap Russian Submarine Surge',
        'detail':   'Multiple Russian submarines detected in GIUK Gap simultaneously -- '
                    'threatens NATO Atlantic LOCs and signals strategic positioning',
        'severity': 2,
        'color':    '#f97316',
        'icon':     '🔱',
        'category': 'arctic',
        'source':   'Cold War precedent: GIUK surge historically preceded major pressure campaigns. '
                    'Also threatens undersea cables and pipeline infrastructure.',
    },

    # ── Category E: Cross-theater coordination ───────────────
    {
        'id':       'cross_theater_coordination',
        'label':    'Multi-Theater Russian Pressure Coordination',
        'detail':   'Russia coordinating pressure across 3+ theaters simultaneously -- '
                    'Iran/ME + DPRK/Asia + Cuba/WHA + Arctic = maximum pressure scenario',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🌐',
        'category': 'cross_theater',
        'source':   'Analytical: simultaneous multi-theater Russian pressure has no Cold War analog. '
                    'Iran weapons + DPRK ammunition + Cuba SIGINT = structured alliance.',
    },
    {
        'id':       'hybrid_infrastructure_attack',
        'label':    'Russian-Attributed Hybrid Attack on NATO Infrastructure',
        'detail':   'A cyberattack, undersea cable cut, GPS jamming or sabotage of NATO/European '
                    'critical infrastructure, attributed to Russia. Hybrid means below the '
                    'threshold of armed attack: not kinetic, not Article 5 on its own',
        'severity': 2,
        'color':    '#f97316',
        'icon':     '💻',
        'category': 'hybrid',
        'source':   'Baltic cable incidents (2023-2024) established the pattern. '
                    'European power grid, internet exchange, and pipeline attacks '
                    'are below Article 5 threshold but escalatory.',
    },

    # (v1.2.0: the two de-escalation entries moved to TALKS_BASELINE / green lines.)

    # ─── v1.1: CARIBBEAN FOOTHOLD / 1962 COALITION RECOGNITION ───
    # The Axios disclosure (May 17, 2026) of 300 drones from Russia + Iran
    # to Cuba is a structural revival of the October 1962 forward-staging
    # doctrine — multilateralized, denial-capable, but functionally
    # equivalent to Soviet Cuba positioning. Russia's interpreter must
    # recognize this as a STRATEGIC pivot, not just access exploitation.
    {
        'id':       'russia_cuba_kinetic_weapons_transfer',
        'label':    'Russia Transferring Kinetic Weapons to Cuba (Caribbean Foothold Doctrine)',
        'detail':   'Russia transferring drones, missiles, or other kinetic-strike weapons to '
                    'Cuba — distinct from historical SIGINT (Lourdes) or oil (Rosneft) access '
                    'patterns. Forward-staging strike capability 90 miles from US territory '
                    'is the canonical October 1962 doctrinal frame in 21st-century form.',
        'severity': 3,
        'color':    '#dc2626',
        'icon':     '🚀',
        'category': 'cross_theater',
        'source':   'Soviet Cuba 1962-1991 was the canonical forward-deployment posture for '
                    'Russian strategic competition with the US. 2026 revival via drones (vs '
                    'MRBMs) reduces strategic-strike footprint but increases tactical-strike '
                    'ambiguity. Combined with Cuban soldiers in Ukraine, signals Moscow '
                    'treating Cuba as a structural strategic asset, not just sanctions evasion.',
    },
    {
        'id':       'russia_cuban_soldiers_procurement',
        'label':    'Russia Procuring Foreign Military Labor from Cuba',
        'detail':   'Documented Cuban soldier deployment to Russian forces in Ukraine — '
                    'reportedly ~5,000 soldiers at ~$25,000/soldier paid to the Cuban '
                    'government. Foreign-military-labor procurement at scale is a new '
                    'Russian strategic adaptation distinct from Wagner/PMC patterns.',
        'severity': 2,
        'color':    '#ef4444',
        'icon':     '🪖',
        'category': 'foreign_military',
        'source':   'Soviet doctrine relied on Warsaw Pact allies (East Germans, Cubans in '
                    'Angola/Ethiopia). 2026 Cuban-soldiers-in-Ukraine signal revives this '
                    'pattern but commercializes it — Cuba receives hard currency, Russia '
                    'receives meat-grinder reinforcements without domestic mobilization cost. '
                    'The financial arrangement makes Cuba structurally dependent on Russia '
                    'for foreign exchange, deepening the strategic relationship.',
    },
    {
        'id':       'russia_iran_cuba_coalition_active',
        'label':    'Russia + Iran Coalition Forward-Staging in Cuba (1962 Pattern)',
        'detail':   'BOTH Russia AND Iran simultaneously transferring weapons or military '
                    'capability to Cuba within a 30-day window. Coordinated coalition '
                    'forward-deployment vs unilateral access exploitation. Structural '
                    'analog to October 1962, multilateralized.',
        'severity': 3,
        'color':    '#7c0a02',
        'icon':     '🤝',
        'category': 'cross_theater',
        'source':   'The 1962 Cuban Missile Crisis was bilateral USSR-Cuba. The 2026 case is '
                    'multilateral RU-IR-Cuba. Multilateral coalition staging increases '
                    'ambiguity (which adversary launched?), reduces deterrence clarity, and '
                    'creates new escalation pathways the Cold War doctrine never addressed. '
                    'This is the highest-confidence Western Hemisphere coalition-threat signal.',
    },
]


# ============================================================
# GREEN LINE DEFINITIONS (diplomatic off-ramp signals)
# ============================================================
GREEN_LINES = [
    {
        'id':       'trump_putin_talks_active',
        'label':    'Trump-Putin Direct Talks Active',
        'detail':   'US-Russia direct engagement at presidential level -- '
                    'the only channel with leverage to produce Ukraine settlement',
        'momentum': 3,
        'color':    '#10b981',
        'icon':     '🤝',
        'category': 'us_russia_diplomacy',
        'source':   'Trump has stated intent to end Ukraine war quickly. '
                    'Direct Putin engagement is the prerequisite for any deal.',
    },
    {
        'id':       'ukraine_ceasefire_active',
        'label':    'Ukraine Ceasefire Negotiations Active',
        'detail':   'Formal ceasefire talks with named parties, conditions, and timeline',
        'momentum': 3,
        'color':    '#10b981',
        'icon':     '🕊️',
        'category': 'ukraine_peace',
        'source':   'Ukraine ceasefire is the primary de-escalation signal for '
                    'the Russia tracker. All other pressure vectors reduce if war ends.',
    },
    {
        'id':       'russia_military_pullback',
        'label':    'Russian Military Pullback Signal',
        'detail':   'Credible Russian military drawdown from NATO border or Ukraine front -- '
                    'genuine de-escalation vs. tactical repositioning',
        'momentum': 2,
        'color':    '#22c55e',
        'icon':     '↩️',
        'category': 'military_deescalation',
        'source':   'Pattern: Russian military pullback signals (2022 pre-invasion feint) '
                    'require verification. Genuine drawdown is a strong de-escalation signal.',
    },
    {
        'id':       'ukraine_diplomatic_openness',
        'label':    'Ukraine Signals Openness to Negotiations',
        'detail':   'Zelenskyy or Ukrainian government signals willingness to negotiate -- '
                    'distinct from military posture',
        'momentum': 2,
        'color':    '#22c55e',
        'icon':     '🇺🇦',
        'category': 'ukraine_peace',
        'source':   'Ukrainian diplomatic flexibility is a necessary condition for settlement. '
                    'Trump pressure on Zelenskyy to negotiate is the key variable.',
    },
    {
        'id':       'nato_russia_hotline_active',
        'label':    'NATO-Russia Hotline / Deconfliction Active',
        'detail':   'NATO-Russia Council or military deconfliction channels reactivated -- '
                    'reduces risk of miscalculation escalation',
        'momentum': 1,
        'color':    '#4ade80',
        'icon':     '📞',
        'category': 'nato_russia_diplomacy',
        'source':   'NATO-Russia Council suspended post-2022. Reactivation would be '
                    'significant confidence-building measure.',
    },
    {
        'id':       'arctic_council_reengagement',
        'label':    'Arctic Council Re-engagement Signal',
        'detail':   'Russia or NATO members signal willingness to re-engage in '
                    'Arctic Council -- reduces Arctic militarization risk',
        'momentum': 1,
        'color':    '#4ade80',
        'icon':     '🧊',
        'category': 'arctic_diplomacy',
        'source':   'Arctic Council suspended after 2022 invasion. '
                    'Re-engagement would signal broader diplomatic opening.',
    },
    {
        'id':       'hungary_eu_veto_vehicle_lost',
        'label':    'Hungary EU Veto Vehicle Lost (Axis Reversal)',
        'detail':   'April 2026 Tisza/Magyar election ended 16 years of Orban government -- '
                    'Russia loses its primary EU veto blocker. Since then Budapest has returned the '
                    'seized Oschadbank cash and gold (May 6), unlocked EUR 16.4bn of EU funds (May 29) '
                    'and lifted its veto on Ukraine\'s accession clusters (June 3; further clusters '
                    'after Kyiv\'s minority-rights law, Oct 12-13). Paks II (Rosatom) is under review, '
                    'decision due end-2026/early-2027.',
        'momentum': 3,
        'color':    '#10b981',
        'icon':     '🏛️',
        'category': 'eu_influence_loss',
        'source':   'Hungary cross-theater fingerprints (axis_reversal_active, '
                    'orban_revival_signal, hungary_russia_axis_level). '
                    'Structural EU-level de-escalation for Russia hybrid operations. '
                    'Orban revival signal would REVERSE this green line.',
    },
]


# ============================================================
# HISTORICAL PRECEDENTS
# ============================================================
HISTORICAL_PRECEDENTS = [
    {
        'id':          'ukraine_2022_invasion',
        'label':       'Russian Full-Scale Invasion of Ukraine (Feb 2022)',
        'description': 'Russia launched full-scale invasion after months of buildup and diplomatic ultimatums',
        'source':      'ISW; IISS; NATO; multiple open source',
        'signals': {
            'russia_military_min': 4,
            'russia_gov_min':      4,
            'nato_pressure':       True,
            'nuclear_rhetoric':    True,
            'belarus_active':      True,
        },
        'outcome':      'Full invasion failed to take Kyiv. War of attrition followed. '
                        'NATO expanded (Finland, Sweden). Russian economy under severe sanctions.',
        'window_hours': 72,
        'confidence':   'High',
    },
    {
        'id':          'crimea_2014',
        'label':       'Crimea Annexation (2014)',
        'description': 'Russia annexed Crimea and supported Donbas separatists under "little green men" model',
        'source':      'IISS; ISW; Chatham House',
        'signals': {
            'russia_military_min': 3,
            'russia_gov_min':      3,
            'hybrid_active':       True,
            'nato_pressure':       False,
            'ukraine_weak':        True,
        },
        'outcome':      'Crimea annexed. Donbas frozen conflict. NATO slow response. '
                        'Established precedent for hybrid + conventional combination.',
        'window_hours': 168,
        'confidence':   'High',
    },
    {
        'id':          'nuclear_coercion_2022_2023',
        'label':       'Russian Nuclear Coercion Campaign (2022-2023)',
        'description': 'Systematic nuclear rhetoric campaign by Medvedev/Putin to deter Western Ukraine aid',
        'source':      'Carnegie; RAND; Belfer Center nuclear coercion analysis',
        'signals': {
            'nuclear_rhetoric':    True,
            'russia_gov_min':      3,
            'ukraine_aid_context': True,
        },
        'outcome':      'Rhetoric did not prevent Western aid but delayed heavy weapons. '
                        'Established Medvedev as designated nuclear signaling instrument. '
                        'NATO absorbed signals without Article 5 response.',
        'window_hours': 0,
        'confidence':   'High',
    },
    {
        'id':          'belarus_nuclear_2023',
        'label':       'Tactical Nuclear Weapons to Belarus (2023)',
        'description': 'Russia deployed tactical nuclear weapons to Belarus -- first non-Russian territory since Soviet era',
        'source':      'Putin statement June 2023; Lukashenko confirmation; IAEA monitoring',
        'signals': {
            'nuclear_rhetoric':    True,
            'belarus_active':      True,
            'russia_gov_min':      3,
        },
        'outcome':      'Deployment completed without NATO kinetic response. '
                        'Established precedent for forward nuclear deployment. '
                        'NATO Article 5 guarantee not invoked despite deployment to neighbor.',
        'window_hours': 0,
        'confidence':   'High',
    },
    {
        'id':          'arctic_cold_war_patrols',
        'label':       'Soviet/Russian Arctic SSBN Surge Precedents',
        'description': 'Cold War and post-Cold War SSBN surge deployments correlating with political pressure campaigns',
        'source':      'IISS Military Balance; US Navy ASWRG historical; Submariner Association archives',
        'signals': {
            'arctic_elevated':     True,
            'nuclear_rhetoric':    True,
            'russia_military_min': 3,
        },
        'outcome':      'Historical pattern: SSBN surges preceded major Soviet/Russian '
                        'diplomatic pressure campaigns by 2-4 weeks. '
                        'GIUK gap remains NATO\'s primary Atlantic vulnerability.',
        'window_hours': 336,
        'confidence':   'Medium',
    },

    # ─── v1.1: 1962 Caribbean foothold analog ───
    {
        'id':          'cuba_october_1962',
        'label':       'October 1962 Cuban Missile Crisis (Caribbean Foothold Doctrine)',
        'description': 'Soviet forward-staging of MRBMs in Cuba — the canonical Russian '
                       'Western Hemisphere strategic-pressure precedent. 13 days of '
                       'confrontation ending in mutual withdrawal (USSR removed missiles, '
                       'US removed Jupiter missiles from Turkey + pledged no-invasion).',
        'source':      'Khrushchev memoirs; Kennedy administration tapes; National Security Archive '
                       'JFK Library declassified collection; Allyn/Blight/Welch *Cuba on the Brink*',
        'signals': {
            'russia_cuba_weapons':  True,    # russia_cuba_kinetic_weapons_transfer red line breached
            'russia_military_min':  3,
        },
        'outcome':      'Historical pattern: forward-deployment of Russian kinetic capability '
                        'in Cuba triggered the most dangerous nuclear crisis of the Cold War. '
                        '2026 revival is multilateralized (RU+IR vs sole USSR) and tactical '
                        '(drones vs MRBMs) but structurally identical: hostile-state forward '
                        'staging 90 miles from US territory during regime brittleness. The '
                        '1962 resolution required US concessions (Turkey missiles, no-invasion '
                        'pledge) — the 2026 case offers no obvious symmetric trade space.',
        'window_hours': 720,  # 30-day pattern window
        'confidence':   'High',
    },
]


# ============================================================
# CORE SCORING FUNCTIONS
# ============================================================

def _corpus(scan_data):
    arts = scan_data.get('_corpus') or []
    if not arts:   # cached / test payloads: fall back to actors' top articles
        for a in (scan_data.get('actors') or {}).values():
            arts = arts + list(a.get('top_articles') or [])
    return build_corpus({'articles_en': arts, 'telegram_messages': []})


_RANK = {'INACTIVE': 0, 'WATCHING': 1, 'APPROACHING': 2, 'BREACHED': 3}


def _vector_status(rid, v):
    """Status from the (corroborated) vector levels. The ground_ops L4 war floor
    never counts as an advance; only ground_ops L5 does."""
    nuc, gnd, nat, arc, hyb, bal, bel = (v['nuclear'], v['ground'], v['nato'], v['arctic'],
                                         v['hybrid'], v['baltic'], v['belarus'])
    if rid == 'nuclear_rhetoric_escalation':
        return 'BREACHED' if nuc >= 4 else 'APPROACHING' if nuc >= 3 else None
    if rid == 'tactical_nuclear_deployment':
        return 'BREACHED' if nuc >= 5 else 'APPROACHING' if nuc >= 4 else None
    if rid == 'kaliningrad_escalation':
        return 'BREACHED' if nat >= 5 else 'APPROACHING' if (nat >= 3 and bel >= 2) else None
    if rid == 'article5_trigger_language':
        return 'BREACHED' if nat >= 5 else 'APPROACHING' if nat >= 4 else None
    if rid == 'suwalki_gap_threat':
        return 'APPROACHING' if (nat >= 4 and bel >= 3) else None
    if rid == 'russian_major_advance':
        return 'BREACHED' if gnd >= 5 else None
    if rid == 'ssbn_unusual_deployment':
        return 'BREACHED' if arc >= 5 else 'APPROACHING' if arc >= 4 else None
    if rid == 'arctic_territorial_escalation':
        return 'BREACHED' if arc >= 4 else 'APPROACHING' if arc >= 3 else None
    if rid == 'cross_theater_coordination':
        hot = sum(1 for x in (nuc, nat, arc, hyb) if x >= 3) + (1 if gnd >= 5 else 0)
        return 'BREACHED' if hot >= 4 else 'APPROACHING' if hot >= 3 else None
    if rid == 'hybrid_infrastructure_attack':
        return 'BREACHED' if hyb >= 4 else 'APPROACHING' if hyb >= 3 else None
    if rid == 'russia_cuba_kinetic_weapons_transfer':
        return 'APPROACHING' if v['cuba'] >= 3 else None
    return None


def _score_red_lines(scan_data, corpus=None):
    """v1.2.0: status = the higher of (a) the vector read and (b) per-article
    evidence on the whole corpus (BREACHED = 2+ outlets). Each line carries its
    evidence and a plain trigger sentence."""
    corpus = corpus if corpus is not None else _corpus(scan_data)
    actors = scan_data.get('actors', {}) or {}
    v = {
        'nuclear': scan_data.get('nuclear_level', 0) or 0,
        'ground':  scan_data.get('ground_ops_level', 0) or 0,
        'nato':    scan_data.get('nato_flank_level', 0) or 0,
        'arctic':  scan_data.get('arctic_level', 0) or 0,
        'hybrid':  scan_data.get('hybrid_level', 0) or 0,
        'baltic':  (actors.get('baltic_flank', {}) or {}).get('escalation_level', 0) or 0,
        'belarus': (actors.get('belarus', {}) or {}).get('escalation_level', 0) or 0,
        'cuba':    scan_data.get('russia_cuba_weapons_level', 0) or 0,
    }
    triggered = []
    for base in RED_LINES:
        rid = base['id']
        if rid not in RED_LINE_TRIGGERS:
            continue
        br, ap = RED_LINE_TRIGGERS[rid]
        sc = score_line(corpus, br, ap)
        vs = _vector_status(rid, v)
        status = sc['status']
        via = 'evidence'
        if vs and _RANK[vs] > _RANK[status]:
            status, via = vs, 'vector'
        if rid == 'russia_iran_cuba_coalition_active' and status == 'BREACHED':
            # needs BOTH halves corroborated
            ru = score_line(corpus, *RED_LINE_TRIGGERS['russia_cuba_kinetic_weapons_transfer'])
            if ru['status'] != 'BREACHED':
                status = 'APPROACHING'
        if status == 'INACTIVE':
            continue
        if via == 'vector':
            trig = f"Set by the corroborated vector read ({base.get('category', '')} levels this scan)"
        else:
            n = sc['breach_outlets'] if status == 'BREACHED' else max(sc['breach_outlets'], sc['approach_outlets'])
            ev = sc['evidence'][0] if sc['evidence'] else None
            trig = (f"{status.title()} on {n} outlet{'s' if n != 1 else ''}"
                    + (f' -- e.g. "{ev["title"][:90]}" ({ev["outlet"]})' if ev else ''))
        triggered.append({**base, **sc, 'status': status, 'via': via, 'trigger': trig})
    triggered.sort(key=lambda x: (-_RANK[x['status']], -x.get('severity', 0)))
    return triggered


def _talks_track(corpus):
    act = find(corpus, TALKS_ACTIVE)
    strain = find(corpus, TALKS_STRAIN)
    na, ns = len(act['outlets']), len(strain['outlets'])
    if na >= 2 and ns >= 2:
        status = 'contested'
        read = (f'The talks are in the news ({na} outlets) alongside stall/rejection language ({ns} outlets): '
                'a round is being tested, not settled.')
    elif na >= 2:
        status = 'active'
        read = f'The trilateral track is live in the reporting ({na} outlets) without corroborated breakdown language.'
    elif ns >= 2:
        status = 'strain'
        read = f'Stall or rejection language ({ns} outlets) without the round itself in view.'
    elif na == 1:
        status = 'signalled'
        read = 'One outlet carries the talks this cycle -- signalled, not corroborated.'
    else:
        status = 'quiet'
        read = 'The talks are not in this cycle\'s corpus; the dated baseline below is the context.'
    return {'status': status, 'talks_outlets': na, 'strain_outlets': ns, 'read': read,
            'baseline': TALKS_BASELINE, 'evidence': (act['evidence'][:2] + strain['evidence'][:2])[:4]}


def _top_indicator(scan_data, red_lines, talks, health):
    br = [r for r in red_lines if r['status'] == 'BREACHED']
    nuc = scan_data.get('nuclear_level', 0) or 0
    gnd = scan_data.get('ground_ops_level', 0) or 0
    nat = scan_data.get('nato_flank_level', 0) or 0
    hyb = scan_data.get('hybrid_level', 0) or 0
    beyond = [n for n, lv in (('the NATO flank', nat), ('hybrid operations', hyb), ('nuclear signalling', nuc),
                              ('drone incursions', scan_data.get('drone_incursion_level', 0) or 0),
                              ('the Black Sea', scan_data.get('black_sea_level', 0) or 0)) if lv >= 3]
    if gnd >= 5:
        line = 'Russia\'s war in Ukraine is above its grinding baseline this cycle -- a strategic-escalation signal is corroborated.'
    elif br:
        line = f"{br[0]['label']}: corroborated this cycle."
    elif len(beyond) >= 2:
        line = 'Beyond Ukraine, Moscow is pressing more than one front at once: ' + ' and '.join(beyond[:2]) + '.'
    elif beyond:
        line = f'Beyond the war in Ukraine, the live front this cycle is {beyond[0]}.'
    elif talks['status'] in ('active', 'contested'):
        line = 'War at its grinding baseline while the Abu Dhabi talks track is live -- watch whether talk changes tempo.'
    else:
        line = 'The war grinds at its baseline; no second front is corroborated this cycle.'
    return ('Thin read -- ' + line) if health['thin'] else line


def _score_green_lines(scan_data, corpus=None):
    """Evaluate Russia diplomatic off-ramp signals.
    v1.2.0: reads the whole corpus (any outlet) -- de-escalation never inflates
    a risk read, so one outlet may activate a green line."""
    actors = scan_data.get('actors', {})
    nuclear_level = scan_data.get('nuclear_level', 0)
    arctic_level  = scan_data.get('arctic_level', 0)
    corpus = corpus if corpus is not None else _corpus(scan_data)

    def _scan_articles(actor_ids, keywords):
        return bool(find(corpus, keywords)['outlets'])

    # v1.2 (May 24 2026): All green-line scan keyword sets expanded
    # to catch EARLY-TREND signals. Pattern: catch the diplomatic warming
    # in analyst commentary / op-eds / leaked frameworks / mediator
    # activity BEFORE a formal track emerges. Mirror Ukraine interpreter
    # v1.1 expansion for cross-theater consistency.
    trump_putin = _scan_articles(
        ['united_states', 'russia_government', 'ukraine', 'nato_alliance'],
        ['trump putin meeting', 'trump putin call', 'trump putin talks',
         'call putin', 'call with putin', 'meet zelensky', 'trump zelensky',
         'созвониться с путиным', 'звонок путину', 'встретиться с зеленским',
         'переговоры трампа и путина',
         'us russia summit', 'trump ukraine deal', 'trump russia negotiate',
         # ── v1.2 — early trend ──
         'trump pressures putin', 'trump pressures russia',
         'trump putin direct', 'trump putin envoy', 'trump putin framework',
         'witkoff putin', 'witkoff moscow', 'witkoff kremlin',
         'kellogg russia', 'kellogg moscow', 'kellogg ukraine envoy',
         'us envoy moscow', 'us special envoy russia',
         'us russia framework discussions', 'us russia channel',
         'us russia back channel', 'trump kremlin contact']
    )
    ceasefire = _scan_articles(
        ['ukraine', 'united_states', 'russia_government'],
        ['ceasefire ukraine', 'ukraine peace deal', 'peace framework ukraine',
         'ukraine negotiations', 'ukraine peace talks', 'ukraine ceasefire',
         # ── v1.2 — early-trend / chatter / leaked ──
         'ukraine ceasefire framework', 'ukraine ceasefire signed',
         'ukraine peace agreement signed', 'ukraine peace plan',
         'ukraine 14-point plan', 'ukraine peace proposal',
         'ukraine off ramp', 'ukraine de-escalation framework',
         'leaked peace plan ukraine', 'leaked ceasefire framework',
         'reported peace plan ukraine', 'rumored ukraine ceasefire',
         'analyst ukraine ceasefire', 'columnist ukraine peace',
         'ukraine peace summit', 'ukraine peace conference',
         'turkey mediates ukraine', 'china mediates ukraine',
         'saudi mediates ukraine', 'india mediates ukraine',
         'european push ukraine peace', 'macron ukraine peace plan',
         'starmer ukraine peace plan', 'merz ukraine peace plan',
         'erdogan ukraine peace plan']
    )
    russia_pullback = _scan_articles(
        ['russia_military', 'ukraine'],
        ['russia withdraws', 'russia pulls back', 'russia reduces troops',
         'russian drawdown', 'russia military reduction',
         # ── v1.2 — softer signals ──
         'russia signals drawdown', 'russia hints withdrawal',
         'russia front stabilization', 'russia pause offensive']
    )
    ukraine_openness = _scan_articles(
        ['ukraine'],
        ['zelenskyy open to talks', 'ukraine willing to negotiate',
         'peace diplomacy', 'diplomatic efforts to achieve peace',
         'coordination of peace', 'coordination of diplomatic efforts',
         'ukraine ceasefire terms', 'zelenskyy peace proposal',
         'ukraine accepts negotiations', 'ukraine peace conditions',
         # ── v1.2 — early signaling / openness chatter ──
         'zelensky open negotiations', 'zelensky considers talks',
         'zelensky willing talks', 'zelensky peace offer',
         'kyiv open to talks', 'kyiv signals openness',
         'ukraine open negotiations', 'ukraine signals openness',
         'ukraine considers ceasefire', 'ukraine softens position',
         'ukraine territorial concession discussion',
         'zelensky negotiating position evolution']
    )
    nato_russia_dialog = _scan_articles(
        ['nato_alliance', 'russia_government'],
        ['nato russia meeting', 'nato russia talks', 'nato russia dialogue',
         'nato russia deconfliction', 'nato russia hotline',
         # ── v1.2 — softer dialog signals ──
         'nato russia channel', 'nato russia contact',
         'nato russia restore communication', 'lavrov nato meeting']
    )
    arctic_diplomacy = _scan_articles(
        ['arctic_watch', 'nato_alliance'],
        ['arctic council', 'arctic diplomacy', 'arctic cooperation russia',
         'arctic forum russia', 'norway russia arctic talks']
    )

    triggered = []

    if trump_putin:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'trump_putin_talks_active'),
            'status': 'ACTIVE',
            'trigger': 'Trump-Putin direct engagement signals detected',
        })

    if ceasefire:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'ukraine_ceasefire_active'),
            'status': 'ACTIVE' if trump_putin else 'SIGNALED',
            'trigger': 'Ukraine ceasefire/negotiations framework signals detected',
        })

    if russia_pullback:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'russia_military_pullback'),
            'status': 'SIGNALED',
            'trigger': 'Russian military pullback language detected -- verify vs. tactical repositioning',
        })

    if ukraine_openness:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'ukraine_diplomatic_openness'),
            'status': 'SIGNALED',
            'trigger': 'Ukrainian government signals openness to negotiations',
        })

    if nato_russia_dialog:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'nato_russia_hotline_active'),
            'status': 'SIGNALED',
            'trigger': 'NATO-Russia dialogue/deconfliction signals detected',
        })

    if arctic_diplomacy:
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'arctic_council_reengagement'),
            'status': 'SIGNALED',
            'trigger': 'Arctic Council re-engagement signals detected',
        })

    # ── Hungary axis reversal green line (added May 18 2026) ──
    # Reads cross-theater fingerprints injected by tracker via scan_data.
    # Active when Hungary's axis-reversal pattern is firing AND the Russia-Hungary
    # axis level has dropped (Russia is on the losing end of the reversal).
    # Reversed if orban_revival_signal fires.
    # v1.2.0: the reversal is a standing fact since April; Hungary v1.1.0 publishes
    # its posture (holding / tested / eroding). The 3-trigger flag stays as a fallback.
    hu_posture = scan_data.get('hungary_reversal_posture', 'unread')
    hu_axis_reversal = scan_data.get('hungary_axis_reversal_active', False) or hu_posture in ('holding', 'tested')
    hu_orban_revival = scan_data.get('hungary_orban_revival_signal', False) or hu_posture == 'eroding'
    hu_russia_axis_level = scan_data.get('hungary_russia_axis_level', 0)

    if hu_axis_reversal and not hu_orban_revival:
        if hu_russia_axis_level <= 2:
            hu_status = 'ACTIVE'
            hu_trigger = (
                f'Hungary axis reversal confirmed; Russia-Hungary axis at L{hu_russia_axis_level} '
                f'(reversed from pre-election baseline). EU veto vehicle lost: Budapest lifted its '
                f'Ukraine-accession veto (June, October 2026) and unlocked EUR 16.4bn of EU funds (May).'
            )
        else:
            hu_status = 'SIGNALED'
            hu_trigger = (
                f'Hungary axis reversal detected but Russia-Hungary axis still elevated '
                f'at L{hu_russia_axis_level} -- monitoring for sustained reversal.'
            )
        triggered.append({
            **next(g for g in GREEN_LINES if g['id'] == 'hungary_eu_veto_vehicle_lost'),
            'status':  hu_status,
            'trigger': hu_trigger,
        })

    triggered.sort(key=lambda x: -x['momentum'])
    return triggered


def _score_diplomatic_track(scan_data, green_lines_triggered):
    """Compute diplomatic momentum score 0-100 and detect key conditions."""
    nuclear_level  = scan_data.get('nuclear_level',    0)
    gnd_level      = scan_data.get('ground_ops_level', 0)
    nat_level      = scan_data.get('nato_flank_level', 0)
    arctic_level   = scan_data.get('arctic_level',     0)
    hybrid_level   = scan_data.get('hybrid_level',     0)

    active_lines   = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']
    signaled_lines = [g for g in green_lines_triggered if g['status'] == 'SIGNALED']

    momentum = sum(g['momentum'] * 20 for g in active_lines)
    momentum += sum(g['momentum'] * 10 for g in signaled_lines)
    score = min(100, momentum)

    if score >= 75:
        scenario       = 'BREAKTHROUGH — Active Peace Framework, Settlement Possible'
        scenario_color = '#10b981'
    elif score >= 50:
        scenario       = 'ACTIVE NEGOTIATION — US-Russia Engagement, Momentum Building'
        scenario_color = '#22c55e'
    elif score >= 30:
        scenario       = 'DIPLOMATIC SIGNALS — Off-Ramp Visible, Not Yet Real'
        scenario_color = '#84cc16'
    elif score >= 15:
        scenario       = 'LOW MOMENTUM — Peace Calls, No Framework'
        scenario_color = '#f59e0b'
    else:
        scenario       = 'NO DIPLOMATIC TRACK — Military Logic Dominates'
        scenario_color = '#6b7280'

    # Multi-vector escalation with no diplomatic track = maximum danger
    high_vectors = sum(1 for lvl in [nuclear_level, gnd_level, nat_level, arctic_level, hybrid_level]
                       if lvl >= 3)
    maximum_pressure = high_vectors >= 3 and len(active_lines) == 0

    return {
        'score':            score,
        'scenario':         scenario,
        'scenario_color':   scenario_color,
        'maximum_pressure': maximum_pressure,
        'high_vector_count': high_vectors,
        'active_count':     len(active_lines),
        'signaled_count':   len(signaled_lines),
    }


def _match_historical(scan_data):
    """Match current Russia signals against historical precedents."""
    actors = scan_data.get('actors', {})

    russia_mil_level = actors.get('russia_military',  {}).get('escalation_level', 0)
    russia_gov_level = actors.get('russia_government',{}).get('escalation_level', 0)
    belarus_level    = actors.get('belarus',          {}).get('escalation_level', 0)
    nuclear_level    = scan_data.get('nuclear_level',    0)
    nato_flank_level = scan_data.get('nato_flank_level', 0)
    arctic_level     = scan_data.get('arctic_level',     0)
    hybrid_level     = scan_data.get('hybrid_level',     0)
    gnd_level        = scan_data.get('ground_ops_level', 0)

    matches = []

    for precedent in HISTORICAL_PRECEDENTS:
        sigs = precedent['signals']
        score = 0
        max_score = 0
        matched_signals = []
        missed_signals  = []

        def check(condition, label, weight=1):
            nonlocal score, max_score
            max_score += weight
            if condition:
                score += weight
                matched_signals.append(label)
            else:
                missed_signals.append(label)

        if 'russia_military_min' in sigs:
            check(russia_mil_level >= sigs['russia_military_min'],
                  f'Russia military L{russia_mil_level} >= L{sigs["russia_military_min"]}', weight=3)
        if 'russia_gov_min' in sigs:
            check(russia_gov_level >= sigs['russia_gov_min'],
                  f'Russia gov L{russia_gov_level} >= L{sigs["russia_gov_min"]}', weight=2)
        if 'nuclear_rhetoric' in sigs:
            check(nuclear_level >= 2,
                  'Nuclear rhetoric elevated', weight=3)
        if 'nato_pressure' in sigs:
            check(nato_flank_level >= 2 == sigs['nato_pressure'],
                  'NATO flank pressure', weight=2)
        if 'belarus_active' in sigs:
            check(belarus_level >= 2 == sigs['belarus_active'],
                  'Belarus active', weight=1)
        if 'hybrid_active' in sigs:
            check(hybrid_level >= 2 == sigs['hybrid_active'],
                  'Hybrid active', weight=1)
        if 'arctic_elevated' in sigs:
            check(arctic_level >= 2, 'Arctic elevated', weight=2)
        if 'russia_cuba_weapons' in sigs:
            # v1.1: check if russia_cuba_kinetic_weapons_transfer red line is breached
            triggered_ids = scan_data.get('_triggered_red_line_ids', [])
            cuba_weapons_active = (
                'russia_cuba_kinetic_weapons_transfer' in triggered_ids
                or 'russia_iran_cuba_coalition_active' in triggered_ids
            )
            check(cuba_weapons_active,
                  '1962-pattern Cuba weapons-staging active', weight=4)

        if 'ukraine_weak' in sigs:
            check(gnd_level >= 3, 'Ukraine front under pressure', weight=1)

        if max_score == 0:
            continue

        similarity = round((score / max_score) * 100)
        if similarity >= 40:
            matches.append({
                'id':              precedent['id'],
                'label':           precedent['label'],
                'description':     precedent['description'],
                'source':          precedent['source'],
                'outcome':         precedent['outcome'],
                'window_hours':    precedent['window_hours'],
                'confidence':      precedent['confidence'],
                'similarity':      similarity,
                'matched_signals': matched_signals,
                'missed_signals':  missed_signals,
            })

    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches[:3]


def _build_so_what(scan_data, red_lines_triggered, historical_matches,
                   green_lines_triggered, diplomatic_track):
    """
    Generate Russia command node assessment.
    Five-way analysis: conventional, nuclear, Ukraine, cross-theater, Arctic.
    """
    actors = scan_data.get('actors', {})

    russia_mil_level = actors.get('russia_military',  {}).get('escalation_level', 0)
    russia_gov_level = actors.get('russia_government',{}).get('escalation_level', 0)
    ukraine_level    = actors.get('ukraine',          {}).get('escalation_level', 0)
    nato_level       = actors.get('nato_alliance',    {}).get('escalation_level', 0)
    us_level         = actors.get('united_states',    {}).get('escalation_level', 0)
    baltic_level     = actors.get('baltic_flank',     {}).get('escalation_level', 0)
    arctic_actor     = actors.get('arctic_watch',     {}).get('escalation_level', 0)
    belarus_level    = actors.get('belarus',          {}).get('escalation_level', 0)

    nuclear_level    = scan_data.get('nuclear_level',    0)
    gnd_level        = scan_data.get('ground_ops_level', 0)
    nato_flank_level = scan_data.get('nato_flank_level', 0)
    arctic_level     = scan_data.get('arctic_level',     max(arctic_actor, 0))
    hybrid_level     = scan_data.get('hybrid_level',     0)

    theatre_score = scan_data.get('rhetoric_score', scan_data.get('theatre_score', 0))
    delta = scan_data.get('delta', {}) or {}

    breached_count    = sum(1 for r in red_lines_triggered if r['status'] == 'BREACHED')
    approaching_count = sum(1 for r in red_lines_triggered if r['status'] == 'APPROACHING')
    top_match         = historical_matches[0] if historical_matches else None

    diplomatic_score  = diplomatic_track.get('score', 0)
    maximum_pressure  = diplomatic_track.get('maximum_pressure', False)
    high_vector_count = diplomatic_track.get('high_vector_count', 0)

    # ── Scenario label ──
    if nuclear_level >= 4 or nato_flank_level >= 5:
        scenario       = 'CRITICAL — Nuclear Signaling or NATO Flank Active Threat'
        scenario_color = '#dc2626'
        scenario_icon  = '🔴'
    elif nuclear_level >= 3 or nato_flank_level >= 4 or high_vector_count >= 3:
        scenario       = 'ELEVATED — Multi-Vector Pressure, Escalation Signals Present'
        scenario_color = '#f97316'
        scenario_icon  = '🟠'
    elif russia_mil_level >= 3 or gnd_level >= 3 or nato_flank_level >= 3:
        scenario       = 'WARNING — Russian Military Posture Above Baseline'
        scenario_color = '#f59e0b'
        scenario_icon  = '🟡'
    elif diplomatic_score >= 50:
        scenario       = 'MONITORING — Diplomatic Activity, Military Below Threshold'
        scenario_color = '#3b82f6'
        scenario_icon  = '🔵'
    else:
        scenario       = 'MONITORING — Below Escalation Threshold'
        scenario_color = '#6b7280'
        scenario_icon  = '⚪'

    # ── Situation ──
    situation_parts = []

    if russia_mil_level >= 2 or gnd_level >= 2:
        situation_parts.append(
            f'Russian military posture at L{russia_mil_level} -- '
            f'{"active operations in Ukraine with offensive pressure" if gnd_level >= 3 else "elevated but below major offensive threshold"}. '
            f'Ground ops vector at L{gnd_level}.'
        )

    if nuclear_level >= 2:
        situation_parts.append(
            f'Nuclear signaling at L{nuclear_level} -- '
            f'{"above baseline, Kremlin/Medvedev escalatory language detected" if nuclear_level >= 3 else "routine deterrence language, monitor for escalation"}. '
            f'Note: Medvedev is the designated nuclear coercion instrument; his statements are deliberate signals, not noise.'
        )

    if nato_flank_level >= 2:
        situation_parts.append(
            f'NATO eastern flank pressure at L{nato_flank_level} -- '
            f'{"Baltic/Kaliningrad signals above baseline, Suwalki Gap watch active" if nato_flank_level >= 3 else "routine NATO-Russia friction"}. '
            f'Baltic flank actor at L{baltic_level}.'
        )

    if arctic_level >= 2:
        situation_parts.append(
            f'Arctic signals at L{arctic_level} -- '
            f'{"Northern Fleet/SSBN activity above baseline" if arctic_level >= 3 else "elevated above quiet baseline"}. '
            f'GIUK Gap is NATO\'s primary Atlantic vulnerability -- watch for submarine surge.'
        )

    if high_vector_count >= 3:
        situation_parts.append(
            f'MAXIMUM PRESSURE PATTERN: {high_vector_count} vectors simultaneously at L3+ -- '
            f'Russia coordinating pressure across multiple domains. '
            f'This pattern has no post-Cold War precedent at this vector count.'
        )

    if diplomatic_score >= 30:
        situation_parts.append(
            f'DIPLOMATIC TRACK ACTIVE (score {diplomatic_score}/100): '
            f'{diplomatic_track.get("scenario", "")}. '
            f'Trump-Putin engagement is the primary off-ramp variable. '
            f'Watch Ukraine territorial concessions language as the key indicator.'
        )

    # ─── v1.1: CARIBBEAN FOOTHOLD RECOGNITION (6th frame question) ───
    # Detect when Russia is forward-staging kinetic capability in Cuba —
    # structurally distinct from traditional SIGINT/oil access patterns.
    breached_ids = [r.get('id') for r in red_lines_triggered if r.get('status') == 'BREACHED']
    cuba_weapons_breached     = 'russia_cuba_kinetic_weapons_transfer' in breached_ids
    cuban_soldiers_breached   = 'russia_cuban_soldiers_procurement' in breached_ids
    ru_ir_coalition_breached  = 'russia_iran_cuba_coalition_active' in breached_ids

    if ru_ir_coalition_breached:
        situation_parts.append(
            'CARIBBEAN FOOTHOLD — 1962 PATTERN ACTIVE: Russia and Iran are simultaneously '
            'forward-staging weapons or military capability in Cuba — the multilateralized '
            '21st-century revival of the October 1962 Cuban Missile Crisis doctrinal frame. '
            'This is qualitatively different from traditional Russia-Cuba access patterns '
            '(Lourdes SIGINT, Rosneft tankers). Coalition staging increases ambiguity and '
            'reduces deterrence clarity. The 1962 precedent reached 13 days of confrontation '
            'and nearly produced nuclear war; the 2026 case offers no obvious symmetric trade '
            'space (no NATO Turkey-missiles analog). Treat as STRATEGIC, not tactical.'
        )
    elif cuba_weapons_breached:
        situation_parts.append(
            'CARIBBEAN FOOTHOLD DEVELOPING: Russia transferring kinetic weapons (drones, '
            'advanced systems) to Cuba — structurally distinct from traditional SIGINT or '
            'oil access. Forward-staging strike capability 90 miles from US territory is the '
            'canonical October 1962 Caribbean foothold pattern. Watch for Iran parallel '
            'transfers (which would upgrade to coalition staging) and US executive cadence '
            'response (the Venezuela January 2026 raid was preceded by 21-day sequencing).'
        )

    if cuban_soldiers_breached:
        situation_parts.append(
            'FOREIGN MILITARY PROCUREMENT (Cuban soldiers): Russia procuring ~5,000 Cuban '
            'soldiers at ~$25,000/soldier for Ukraine operations. Foreign-military-labor '
            'commercialization revives the Cold War Cuban-internationalist pattern '
            '(Angola, Ethiopia) but with hard-currency compensation flowing to a regime '
            'in fiscal crisis. This deepens Cuban dependency on Russia for foreign exchange '
            '— a structural lever beyond episodic SIGINT or oil access.'
        )

    # ── Hungary axis reversal narrative (added May 18 2026) ──
    # The April 2026 Tisza/Magyar election is one of the most consequential
    # structural shifts for Russia in 2026: loss of primary EU veto vehicle.
    # v1.2.0: the reversal is a standing fact since April; Hungary v1.1.0 publishes
    # its posture (holding / tested / eroding). The 3-trigger flag stays as a fallback.
    hu_posture = scan_data.get('hungary_reversal_posture', 'unread')
    hu_axis_reversal = scan_data.get('hungary_axis_reversal_active', False) or hu_posture in ('holding', 'tested')
    hu_orban_revival = scan_data.get('hungary_orban_revival_signal', False) or hu_posture == 'eroding'
    hu_russia_axis_level = scan_data.get('hungary_russia_axis_level', 0)
    hu_ukraine_track_level = scan_data.get('hungary_ukraine_track_level', 0)
    hu_druzhba_status = scan_data.get('druzhba_pipeline_status', 'unknown')

    if hu_axis_reversal and not hu_orban_revival:
        druzhba_clause = ''
        if hu_druzhba_status == 'flowing':
            druzhba_clause = ' Druzhba flows resumed post-election under Tisza government oversight.'
        elif hu_druzhba_status == 'disrupted':
            druzhba_clause = ' Druzhba pipeline currently disrupted -- monitor for repair cadence.'
        situation_parts.append(
            f'HUNGARY: Russia has lost its primary EU veto vehicle (Hungary posture: {hu_posture}). '
            f'Since the April 12 2026 election the Magyar government has unlocked EUR 16.4bn of EU funds, '
            f'lifted its veto on Ukraine\'s accession clusters (June; more after Kyiv\'s Oct 12 minority-rights '
            f'law) and put Rosatom\'s Paks II under review (decision end-2026 / early 2027). '
            f'Russia-Hungary axis at L{hu_russia_axis_level}; Hungary-Ukraine track at L{hu_ukraine_track_level}.'
            f'{druzhba_clause} '
            f'Strategic consequence: the hybrid influence card inside EU decision-making is gone; Moscow\'s '
            f'EU-sympathetic vectors narrow to Slovakia. The levers left are energy (Druzhba, gas, Paks II) -- '
            f'and Orban himself, now reportedly floated for UN Secretary-General with Russian support.'
        )
    elif hu_orban_revival:
        situation_parts.append(
            f'HUNGARY ORBAN REVIVAL SIGNAL: Counter-narrative detected -- Orban/Fidesz '
            f'opposition mobilization signals present (Moscow visits, Tucker Carlson media, '
            f'Article 7 defiance language). Hungary-Russia axis at L{hu_russia_axis_level}. '
            f'If sustained, would reverse the post-April 2026 EU re-integration trajectory '
            f'and restore Russia\'s primary EU veto vehicle. Monitor Tisza government '
            f'cohesion + Fidesz street mobilization cadence.'
        )

    # ── Key indicators ──
    indicators = []
    # v1.1: Caribbean Foothold indicator (priority — listed first when active)
    if ru_ir_coalition_breached:
        indicators.append(
            '🚨 CARIBBEAN FOOTHOLD COALITION WATCH: Russia + Iran forward-staging active. '
            'Monitor Mariel/Cienfuegos port traffic, Russian/Iranian cargo flights to Havana, '
            'US executive cadence response (Venezuela 2026 precedent: 21-day sequencing to '
            'kinetic action). Highest-confidence Western Hemisphere coalition-threat signal.'
        )
    elif cuba_weapons_breached:
        indicators.append(
            'CARIBBEAN FOOTHOLD WATCH: Russia kinetic weapons transfer to Cuba detected. '
            'Watch for Iran parallel transfers, Cuban defense reorganization announcements, '
            'and US executive response cadence (CIA director visits, DOJ Cuba indictments, '
            'Sec-Def/State congressional posture-setting).'
        )

    if nuclear_level >= 3:
        indicators.append(
            'NUCLEAR SIGNALING WATCH: Russia nuclear rhetoric above baseline. '
            'Key distinction: coercive posturing (Medvedev) vs. doctrinal shift (Putin direct). '
            'Watch for: Iskander nuclear warhead movement, SSBN deployment orders, '
            'strategic force readiness changes.'
        )

    if maximum_pressure:
        indicators.append(
            f'MAXIMUM PRESSURE: {high_vector_count} vectors at L3+ with no diplomatic track -- '
            'this is the most dangerous configuration. Russia is applying simultaneous pressure '
            'across nuclear, conventional, NATO flank, Arctic, and hybrid domains '
            'with no diplomatic channel absorbing the pressure.'
        )

    if arctic_level >= 3:
        indicators.append(
            'ARCTIC ELEVATED: Northern Fleet/SSBN signals above quiet baseline. '
            'Historical pattern: SSBN surges preceded major Soviet/Russian diplomatic pressure '
            'campaigns by 2-4 weeks. Cross-reference with Greenland tracker for convergence. '
            'GIUK Gap submarine activity threatens NATO Atlantic LOCs.'
        )

    if hybrid_level >= 3:
        indicators.append(
            'HYBRID WARFARE SIGNALS: Cross-theater coordination detected -- '
            'Iran weapons supply to Russia, DPRK ammunition transfers, '
            'Cuba/Venezuela WHA presence signals. '
            'Russia is building a structured counter-NATO alliance across all theaters.'
        )

    if breached_count >= 1:
        indicators.append(
            f'{breached_count} red line(s) currently breached -- '
            f'signals that historically precede Russian kinetic or escalatory action.'
        )

    if diplomatic_score >= 50:
        indicators.append(
            'DIPLOMATIC OFF-RAMP: Trump-Putin engagement creates potential Ukraine settlement path. '
            'Watch: Ukraine territorial concessions language, US sanctions relief signals, '
            'Zelenskyy NATO membership demands softening. '
            'Any Ukraine ceasefire would fundamentally reduce Russia threat posture to NATO.'
        )

    # ── Assessment ──
    assessment_parts = []

    if top_match and top_match['similarity'] >= 50:
        assessment_parts.append(
            f'Signal pattern shows {top_match["similarity"]}% similarity to '
            f'{top_match["label"]}. Outcome: {top_match["outcome"].lower()}'
        )
        assessment_parts.append(
            f'Confidence: {top_match["confidence"]}. '
            f'Historical response window: {top_match["window_hours"]}h.'
        )

    if diplomatic_score >= 30:
        assessment_parts.append(
            f'However: diplomatic track at {diplomatic_score}/100 introduces off-ramp potential. '
            f'Unlike 2022, Trump-Putin engagement creates structural possibility of Ukraine settlement. '
            f'If settlement emerges, Russian pressure on NATO flanks reduces significantly.'
        )

    # ── Watch list ──
    watch_items = []

    if diplomatic_score >= 30:
        watch_items.append(
            'Trump-Putin engagement -- watch for: Ukraine territorial deal language, '
            'Zelenskyy NATO membership demand softening, US sanctions relief signals'
        )

    watch_items += [
        'Medvedev nuclear language escalation -- specific threat vs. routine deterrence (key distinction)',
        f'Northern Fleet/SSBN deployment patterns -- Arctic L{arctic_level}, watch for surge above baseline',
        'Kaliningrad Iskander deployment signals -- Suwalki Gap is the NATO Baltic connectivity tripwire',
        'DPRK ammunition + Iran weapons transfers to Russia -- cross-theater coordination building',
        'Ukrainian front cohesion -- Russian gains embolden NATO pressure; losses trigger desperation signals',
        'Belarus military buildup near Polish/Lithuanian border -- Suwalki Gap secondary indicator',
    ]

    return {
        'scenario':                scenario,
        'scenario_color':          scenario_color,
        'scenario_icon':           scenario_icon,
        'situation':               ' '.join(situation_parts),
        'key_indicators':          indicators,
        'assessment':              ' '.join(assessment_parts),
        'watch_list':              watch_items[:6],
        # EVIDENCE FOR THE FLAG (Sep 2026). `nuclear_elevated` forces the
        # Europe posture to CRITICAL and fires the GPI's priority-15 narrative.
        # A boolean that carries that much weight must be auditable: a reader
        # has to be able to see WHAT fired it without reading the source.
        'nuclear_elevated':        nuclear_level >= 3,
        'nuclear_level':           nuclear_level,
        # Read from scan_data like nuclear_level itself -- the tracker now
        # writes `nuclear_trigger` alongside it in both fingerprint payloads.
        'nuclear_trigger':         scan_data.get('nuclear_trigger', ''),
        'arctic_elevated':         arctic_level >= 3,
        'maximum_pressure':        maximum_pressure,
        'high_vector_count':       high_vector_count,
        'diplomatic_score':        diplomatic_score,
        'diplomatic_scenario':     diplomatic_track.get('scenario', ''),
        'diplomatic_scenario_color': diplomatic_track.get('scenario_color', '#6b7280'),
        'generated_at':            datetime.now(timezone.utc).isoformat(),
        'confidence_note': (
            'Russia assessment generated from open-source signal data. '
            'Not a prediction. Verify through official channels. '
            'Nuclear signaling distinction (coercion vs. doctrine) and '
            'Arctic baseline judgments are analytical estimates. '
            'Cross-theater coordination signals require multi-source verification.'
        ),
    }


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

# ── v1.3.0: hybrid mode + attribution ─────────────────────────
_MODE_WORDS = (
    ('cyber',    ('cyber', 'hack', 'ransomware', 'malware', 'ddos', 'phishing')),
    ('jamming',  ('jamming', 'jammed', 'gps interference', 'spoofing')),
    ('sabotage', ('cable', 'pipeline', 'arson', 'explosion', 'sabotage', 'derail', 'anchor drag')),
)
_MODE_LABEL = {'cyber': 'CYBER', 'jamming': 'GPS / SIGNAL JAMMING', 'sabotage': 'PHYSICAL SABOTAGE',
               'unknown': 'HYBRID (type unclear)'}
_MODE_ICON = {'cyber': '\U0001F4BB', 'jamming': '\U0001F4E1', 'sabotage': '\u2693', 'unknown': '\U0001F4BB'}
_OFFICIAL = ('government', 'minister', 'ministry', 'nato ', 'nato:', 'intelligence', 'officials',
             'prime minister', 'president', 'police', 'prosecutor', 'security service')
_HEDGE = ('% certain', 'suspected', 'suspect', 'likely', 'possible', 'may have', 'probe', 'investigat')


def hybrid_mode(texts):
    t = ' '.join(texts).lower()
    for mode, words in _MODE_WORDS:          # order matters: a hack described as "sabotage" is cyber
        if any(w in t for w in words):
            return mode
    return 'unknown'


def hybrid_attribution(texts):
    t = ' '.join(texts).lower()
    if any(h in t for h in _HEDGE):
        return 'hedged'
    if any(o in t for o in _OFFICIAL):
        return 'official'
    return 'press'


def _hybrid_signal(rl, breached):
    titles = [e.get('title', '') for e in (rl.get('evidence') or [])]
    mode = hybrid_mode(titles or [rl.get('trigger', '')])
    attr = hybrid_attribution(titles or [rl.get('trigger', '')])
    attr_txt = {'official': 'officially attributed to Russia',
                'hedged': 'attributed to Russia with a hedge in the reporting (suspected / "95% certain"), '
                          'not officially confirmed',
                'press': 'attributed to Russia in press reporting, not officially confirmed'}[attr]
    return {
        'priority':  13 if breached else 11,
        'category':  'hybrid_red_line',
        'theatre':   'russia',
        'level':     4 if (breached and attr == 'official') else 3,
        'mode':      mode,
        'mode_label': _MODE_LABEL[mode],
        'attribution': attr,
        'icon':      _MODE_ICON[mode],
        'color':     '#f97316',
        'short_text': '\U0001F1F7\U0001F1FA RUSSIA hybrid red line %s: %s, not kinetic'
                      % ('breached' if breached else 'approaching', _MODE_LABEL[mode]),
        'long_text': ('%s. %s, %s. Hybrid means below the threshold of armed attack: it raises '
                      'the temperature without anyone firing a shot.'
                      % (rl.get('trigger', ''), _MODE_LABEL[mode].capitalize(), attr_txt))[:480],
    }


def _inject_triggered_ids(scan_data, red_lines_triggered):
    """v1.1 helper: inject triggered red-line IDs into scan_data so downstream
    functions (like _match_historical) can check which red lines are active."""
    if isinstance(scan_data, dict):
        scan_data['_triggered_red_line_ids'] = [
            r.get('id') for r in (red_lines_triggered or []) if r.get('status') == 'BREACHED'
        ]
    return scan_data


def interpret_signals(scan_data):
    """
    Main entry point. Called from rhetoric_tracker_russia.py or app.py.
    Returns interpretation dict.
    """
    try:
        corpus      = _corpus(scan_data)
        health      = corpus_health(scan_data, corpus, THIN_MIN_ARTICLES)
        red_lines   = _score_red_lines(scan_data, corpus)
        green_lines = _score_green_lines(scan_data, corpus)
        talks       = _talks_track(corpus)
        # v1.2.0: a corroborated talks round is a green line in its own right.
        if talks['status'] in ('active', 'contested') and not any(
                g['id'] == 'trump_putin_talks_active' for g in green_lines):
            green_lines.insert(0, {
                **next(g for g in GREEN_LINES if g['id'] == 'trump_putin_talks_active'),
                'status': 'ACTIVE' if talks['status'] == 'active' else 'SIGNALED',
                'trigger': talks['read'],
            })
        diplomatic  = _score_diplomatic_track(scan_data, green_lines)
        # v1.1: inject triggered red-line IDs so _match_historical can detect
        # 1962-pattern signals (russia_cuba_weapons, etc)
        scan_data = _inject_triggered_ids(scan_data, red_lines)
        historical  = _match_historical(scan_data)
        so_what     = _build_so_what(scan_data, red_lines, historical,
                                     green_lines, diplomatic)

        breached    = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl   = [g for g in green_lines if g['status'] == 'ACTIVE']
        top_indicator = _top_indicator(scan_data, red_lines, talks, health)

        so_what['talks_track'] = talks['read']
        so_what['top_indicator'] = top_indicator
        if health['thin']:
            so_what['scenario'] = 'THIN READ -- ' + str(so_what.get('scenario', ''))
            so_what['situation'] = ('THIN READ -- under-read scan (' + health['reason'] + '); quiet lines '
                                    'may be unread. ') + str(so_what.get('situation', ''))

        return {
            'so_what':             so_what,
            'top_indicator':       top_indicator,
            'thin_read':           health['thin'],
            'corpus_health':       health,
            'talks_track':         talks,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in breached), default=0),
            },
            'green_lines': {
                'triggered':         green_lines,
                'active_count':      len(active_gl),
                'signaled_count':    len(green_lines) - len(active_gl),
                'diplomatic_score':  diplomatic['score'],
            },
            'diplomatic_track':    diplomatic,
            'historical_matches':  historical,
            'interpreter_version': INTERPRETER_VERSION,
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        print(f'[Russia Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what':            {'scenario': 'Interpreter error -- unread, not calm', 'assessment': str(e)[:200]},
            'top_indicator':      'Interpreter error this cycle -- unread, not calm.',
            'thin_read':          True,
            'red_lines':          {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'green_lines':        {'triggered': [], 'active_count': 0, 'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track':   {'score': 0, 'scenario': 'Unknown', 'maximum_pressure': False},
            'historical_matches': [],
            'interpreter_version': INTERPRETER_VERSION,
            'error':              str(e)[:200],
        }


# ============================================================
# STANDALONE TEST
# ============================================================
if __name__ == '__main__':
    # Simulate current conditions: Ukraine war ongoing, nuclear rhetoric
    # present, Trump-Putin talks emerging, Arctic at baseline
    test_data = {
        'rhetoric_score':    55,
        'nuclear_level':     3,
        'ground_ops_level':  3,
        'nato_flank_level':  2,
        'arctic_level':      1,
        'hybrid_level':      3,
        'delta': {'direction': 'stable', 'score_change': 0},
        'actors': {
            'russia_military': {'escalation_level': 3, 'statement_count': 45, 'top_articles': [
                {'title': 'Russian forces advance in Zaporizhzhia region, capturing two villages', 'published': ''},
                {'title': 'Russia launches massive drone attack on Ukraine energy infrastructure', 'published': ''},
            ]},
            'russia_government': {'escalation_level': 3, 'statement_count': 30, 'top_articles': [
                {'title': 'Medvedev nuclear warning if NATO intervenes directly in Ukraine', 'published': ''},
                {'title': 'Putin warns consequences for countries supplying long-range missiles to Ukraine', 'published': ''},
            ]},
            'ukraine': {'escalation_level': 2, 'statement_count': 20, 'top_articles': [
                {'title': 'Zelenskyy open to peace negotiations if security guarantees provided', 'published': ''},
                {'title': 'Ukrainian forces hold line in Donbas despite Russian pressure', 'published': ''},
            ]},
            'nato_alliance': {'escalation_level': 2, 'statement_count': 15, 'top_articles': [
                {'title': 'NATO reinforces eastern flank with additional battle groups', 'published': ''},
            ]},
            'united_states': {'escalation_level': 2, 'statement_count': 18, 'top_articles': [
                {'title': 'Trump Putin direct talks on Ukraine peace deal scheduled', 'published': ''},
                {'title': 'US considers Ukraine minerals deal as part of ceasefire framework', 'published': ''},
            ]},
            'baltic_flank': {'escalation_level': 2, 'statement_count': 8, 'top_articles': [
                {'title': 'Estonia Latvia Lithuania boost defense spending amid Russian threats', 'published': ''},
            ]},
            'arctic_watch': {'escalation_level': 1, 'statement_count': 2, 'top_articles': [
                {'title': 'Russian Northern Fleet conducts routine patrol exercise in Barents Sea', 'published': ''},
            ]},
            'belarus': {'escalation_level': 2, 'statement_count': 5, 'top_articles': [
                {'title': 'Russia deploys additional troops to Belarus for joint exercises', 'published': ''},
            ]},
        },
    }

    result = interpret_signals(test_data)

    print('\n' + '='*70)
    print('MILITARY SCENARIO:', result['so_what']['scenario'])
    print('DIPLOMATIC SCENARIO:', result['so_what'].get('diplomatic_scenario', 'None'))
    print(f'DIPLOMATIC SCORE: {result["so_what"].get("diplomatic_score", 0)}/100')
    print(f'NUCLEAR ELEVATED: {result["so_what"].get("nuclear_elevated", False)}')
    print(f'ARCTIC ELEVATED: {result["so_what"].get("arctic_elevated", False)}')
    print(f'MAXIMUM PRESSURE: {result["so_what"].get("maximum_pressure", False)}')
    print(f'HIGH VECTOR COUNT: {result["so_what"].get("high_vector_count", 0)}')
    print('='*70)
    print('\nSITUATION (excerpt):')
    print(result['so_what']['situation'][:400])
    print('\nKEY INDICATORS:')
    for ind in result['so_what']['key_indicators']:
        print(f'  -- {ind[:120]}')
    print('\nWATCH LIST:')
    for item in result['so_what']['watch_list']:
        print(f'  -> {item[:100]}')
    print('\nRED LINES:')
    for rl in result['red_lines']['triggered']:
        print(f'  {rl["icon"]} [{rl["status"]}] {rl["label"]} (Sev {rl["severity"]}) [{rl["category"]}]')
    print('\nGREEN LINES:')
    for gl in result['green_lines']['triggered']:
        print(f'  {gl["icon"]} [{gl["status"]}] {gl["label"]} (Momentum {gl["momentum"]})')
    print('\nHISTORICAL MATCHES:')
    for hm in result['historical_matches']:
        print(f'  {hm["similarity"]}% -- {hm["label"]} | Confidence: {hm["confidence"]}')
    print(f'\nDIPLOMATIC TRACK: score={result["diplomatic_track"]["score"]}, '
          f'max_pressure={result["diplomatic_track"]["maximum_pressure"]}')

def build_top_signals(scan_data):
    """
    v1.1 (Jul 2026) -- Canonical top_signals[] emission for Europe BLUF / GPI.

    This function was imported by the tracker since v2.0 but never existed --
    every scan hit ImportError and emitted top_signals: []. Russia has been
    invisible to the Europe regional BLUF. This fixes it.

    Emits the canonical schema: priority / category / theatre / level /
    icon / color / short_text / long_text. Escalatory (red lines, hot
    vectors) AND de-escalatory (green lines, diplomatic track) signals
    both surface -- peace signals reach the BLUF too.
    """
    sigs = []
    interp = scan_data.get('interpretation', {}) or {}

    # 1. Red lines (breached outrank approaching)
    for rl in (interp.get('red_lines', {}) or {}).get('triggered', [])[:3]:
        breached = rl.get('status') == 'BREACHED'
        if rl.get('category') == 'hybrid':
            sigs.append(_hybrid_signal(rl, breached))
            continue
        sigs.append({
            'priority':  14 if breached else 12,
            'category':  'red_line',
            'theatre':   'russia',
            'level':     4 if breached else 3,     # v1.2.0: L5 only via the kinetic ladder
            'icon':      rl.get('icon', '\U0001F6A8'),
            'color':     rl.get('color', '#dc2626'),
            'short_text': '\U0001F1F7\U0001F1FA RUSSIA red line ' +
                          ('BREACHED' if breached else 'approaching') + ': ' + rl.get('label', ''),
            'long_text': (rl.get('trigger', '') + '. ' + rl.get('detail', ''))[:480],
        })

    # 2. Green lines -- de-escalatory, the peace signals (momentum-weighted)
    for gl in (interp.get('green_lines', {}) or {}).get('triggered', [])[:2]:
        sigs.append({
            'priority':  10,
            'category':  'diplomatic_offramp',
            'theatre':   'russia',
            'level':     2,
            'icon':      gl.get('icon', '\U0001F54A'),
            'color':     gl.get('color', '#10b981'),
            'short_text': '\U0001F1F7\U0001F1FA RUSSIA off-ramp signal: ' + gl.get('label', ''),
            'long_text': (gl.get('detail', '') + ' ' + gl.get('trigger', ''))[:480],
        })

    # 3. Hot vectors (L3+)
    _VN = {'nuclear_level': ('Nuclear signaling', '\u2622\uFE0F'),
           'ground_ops_level': ('Ukraine ground operations', '\u2694\uFE0F'),
           'nato_flank_level': ('NATO flank pressure', '\U0001F6E1'),
           'arctic_level': ('Arctic posture', '\U0001F9CA'),
           'hybrid_level': ('Hybrid operations', '\U0001F4BB')}
    for key, (name, icon) in _VN.items():
        lvl = scan_data.get(key, 0)
        if lvl >= 3:
            sigs.append({
                'priority':  8 + lvl,
                'category':  'vector_escalation',
                'theatre':   'russia',
                'level':     lvl,
                'icon':      icon,
                'color':     '#ef4444' if lvl >= 4 else '#f97316',
                'short_text': '\U0001F1F7\U0001F1FA RUSSIA ' + name + ' at L' + str(lvl),
                'long_text': name + ' vector elevated to L' + str(lvl) +
                             ' this scan -- see Russia Pressure Tracker for the signal detail.',
            })

    # 4. Historical precedent matches (>=70% similarity)
    for hm in (interp.get('historical_matches', []) or []):
        sim = hm.get('similarity', 0)
        if sim >= 70:
            sigs.append({
                'priority':  9,
                'category':  'historical_match',
                'theatre':   'russia',
                'level':     3,
                'icon':      '\U0001F4DC',
                'color':     '#f59e0b',
                'short_text': '\U0001F1F7\U0001F1FA RUSSIA pattern ' + str(sim) +
                              '% similar to ' + hm.get('label', ''),
                'long_text': (hm.get('description', '') +
                              ' Outcome: ' + hm.get('outcome', ''))[:480],
            })

    # Highest priority first; cap for BLUF hygiene
    sigs.sort(key=lambda x: x['priority'], reverse=True)
    return sigs[:8]
