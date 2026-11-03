"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — UKRAINE SIGNAL INTERPRETER
  v1.1.0 (Nov 3 2026)    (v1.0.0 Apr 30 2026)
═══════════════════════════════════════════════════════════════════════

v1.1.0 (Nov 3 2026) -- EVIDENCE, SPOKES, AND THE THREE QUESTIONS
  1. Red lines are scored PER ARTICLE with publishers counted (europe_evidence):
     BREACHED needs 2+ outlets. v1.0 pooled every headline into one string, so two
     trigger phrases in one blog post breached a red line and nothing said which.
     Each red line now carries its evidence (title, outlet, phrase).
     Loose triggers removed: 'cabinet of ministers', 'kyiv overnight', 'kyiv hit',
     'dsns kyiv', 'zelensky warns', 'kyiv warns' -- everyday war-coverage words.
  2. THIN READ. When the scan is under-read (too few articles or outlets) the So
     What says so in its headline. A thin scan is a blind spot, not a quiet war.
  3. Per-actor LEVELS (0-4) so the Europe Actor Matrix and the BLUF can read
     Ukraine's actors -- v1.0 actor_summaries carried counts only.
  4. US VECTOR (the US spoke): aid pipeline, Washington's pressure on Kyiv vs on
     Moscow, the envoy track. Answers: who is Washington leaning on?
  5. NATO TRACK: membership raised / guarantees in play / renunciation on the
     table -- plus a date-stamped baseline of where the bid stands.
  6. DRONE DIPLOMACY / IRAN LINK: Ukraine as a drone-defence exporter against
     Iranian drones in the Gulf, and its strikes on the Iran->Russia supply line.
     The same Shahed design is the threat at both ends of the axis.
  7. RUSSIA PRESSURE: the read the Russia wheel's spoke carries.
  8. top_indicator: one plain-language line.

ANALYTICAL FRAMING (unchanged):
  Ukraine's rhetoric posture is shaped by four concurrent dynamics -- frontline
  reality, the Western aid pipeline (US decisive), defence-industrial maturation
  (the drone export vector), and the diplomatic track -- plus the Black Sea
  grain corridor as the cross-cutting commodity node.

USAGE:
  from ukraine_signal_interpreter import interpret_signals
  result = interpret_signals(scan_data)
"""

import requests
from datetime import datetime, timezone

from europe_evidence import (build_corpus, score_line, score_green, find, outlet_level,
                             phrase_count, corpus_health, STATUS_LEVEL)

INTERPRETER_VERSION = '1.1.0'

# Europe backend self-call URL (interpreter runs in Europe backend)
COMMODITY_PROXY_URL = 'http://localhost:10000/api/europe/commodity/ukraine'

THIN_MIN_ARTICLES = 40      # below this the scan is under-read for an active war


# ============================================================
# RED LINES
# ============================================================
RED_LINES = [
    {
        'id':       'frontline_collapse',
        'category': 'Battlefield',
        'title':    'Ukrainian Frontline Collapse Indicator',
        'severity': 5,
        'description':
            'Reports of significant breakthrough by Russian forces — '
            'multiple settlement losses in 48-72h, command-and-control '
            'failure, mass retreat patterns, or political signaling of '
            'territorial concession on a major axis (Donbas, Zaporizhzhia, '
            'Kharkiv). Catastrophic for Ukrainian war posture.',
        'triggers_breached': [
            'mass retreat', 'frontline collapse', 'major breakthrough',
            'city falls', 'kupyansk fall', 'pokrovsk fall',
            'kostiantynivka fall', 'breakthrough confirmed',
        ],
        'triggers_approaching': [
            'frontline pressure', 'tactical retreat', 'salient under threat',
            'russian advance', 'positions abandoned',
        ],
    },
    {
        'id':       'us_aid_suspension_total',
        'category': 'Western Support',
        'title':    'US Aid Pipeline Suspension',
        'severity': 5,
        'description':
            'Trump administration formal suspension of military aid to '
            'Ukraine — weapons authorizations halted, funding frozen, '
            'intelligence-sharing curtailed. Existential for Ukrainian '
            'defense capacity.',
        'triggers_breached': [
            'aid suspended ukraine', 'weapons halted ukraine',
            'frozen ukraine funding', 'intelligence cut ukraine',
            'aid cutoff confirmed', 'congressional aid blocked',
        ],
        'triggers_approaching': [
            'aid pause', 'aid review', 'intelligence sharing review',
            'patriot delay', 'aid bill stalled',
        ],
    },
    {
        'id':       'tactical_nuclear_signaling',
        'category': 'Nuclear',
        'title':    'Russian Tactical Nuclear Signaling vs Ukraine',
        'severity': 5,
        'description':
            'Concrete Russian indicators of preparation to use tactical '
            'nuclear weapons against Ukraine — doctrinal statements, '
            'warhead movement, exercise patterns, or Putin-level threats '
            'with specific targeting language.',
        'triggers_breached': [
            'tactical nuclear strike', 'nuclear use ukraine',
            'tactical warhead deployed', 'nuclear posture raised',
        ],
        'triggers_approaching': [
            'nuclear threat ukraine', 'tactical nuclear option',
            'nuclear doctrine ukraine', 'red line nuclear',
        ],
    },
    {
        'id':       'energy_grid_collapse',
        'category': 'Infrastructure',
        'title':    'Energy Grid Catastrophic Failure',
        'severity': 4,
        'description':
            'Sustained Russian strike campaign produces grid collapse with '
            'extended blackouts, heating failure during winter, water/sewage '
            'shutdowns. Triggers humanitarian and refugee surge dynamics.',
        'triggers_breached': [
            # original analyst tags
            'grid collapse', 'blackout extended', 'heating failure',
            'thermal plant destroyed', 'substation strike critical',
            # ── v1.2 (May 24 2026) news-language expansion ──
            'thermal plant damaged', 'substation damaged', 'substation hit',
            'substation destroyed', 'energy infrastructure destroyed',
            'power grid collapse', 'electricity blackout', 'massive blackout',
            'nationwide blackout', 'heating systems failed', 'no heating',
            'no electricity', 'water supply disrupted', 'water system damaged',
            'energy facilities destroyed',
        ],
        'triggers_approaching': [
            # original analyst tags
            'energy strikes wave', 'power outage', 'shahed swarm',
            'grid damage major', 'rolling blackouts',
            # ── v1.2 (May 24 2026) news-language expansion ──
            'attack on energy', 'strike on energy', 'energy facility hit',
            'power plant attacked', 'energy infrastructure attacked',
            'shahed drones', 'drone swarm', 'mass drone attack',
            'power cuts', 'electricity cuts', 'emergency blackouts',
            'energy facilities damaged', 'attacks on power',
        ],
    },
    {
        'id':       'pre_strike_warning_issued',
        'category': 'Pre-Strike Indicator',
        'title':    'Ukrainian Pre-Strike Warning Issued (Imminent Russian Attack)',
        'severity': 3,
        'description':
            'Zelensky or Ukrainian intelligence publicly discloses '
            'intel — typically sourced from US/UK partners — about an '
            'imminent Russian missile or drone strike. Pattern: warning is '
            'issued hours before kinetic activity. Historical precedent: '
            'May 23 2026 Oreshnik warning preceded May 24 mass strike on '
            'Kyiv (>50 missiles + 700 drones) by ~6 hours. US Embassy Kyiv '
            'security alerts to citizens are a corroborating signal. This '
            'is a NARROW analytical window — typically 6-24h from warning '
            'to strike — and a high-signal early-warning indicator.',
        'triggers_breached': [
            # original v1.1
            'oreshnik strike confirmed', 'oreshnik launched',
            'hypersonic launched at ukraine', 'mass attack confirmed',
            'combined strike underway', 'air raid alert nationwide ukraine',
            # ── v1.2 (May 24 2026) news-language expansion ──
            'russia launches oreshnik', 'oreshnik missile launched',
            'oreshnik fired', 'russia fires oreshnik',
            'oreshnik used against ukraine', 'oreshnik strike ukraine',
            'hypersonic missile launched ukraine', 'russia launches hypersonic',
            'combined strike on ukraine', 'massive missile attack',
            'mass missile attack ukraine', 'largest missile attack',
            'wave of strikes ukraine',
        ],
        'triggers_approaching': [
            # original v1.1
            'zelensky warns russia preparing', 'zelensky warning oreshnik',
            'zelensky warning hypersonic', 'zelensky strike warning',
            'zelensky pre-strike warning', 'ukraine intelligence russia preparing',
            'ukrainian intelligence indicates russia preparing',
            'ukraine intel hypersonic', 'us embassy kyiv security alert',
            'us embassy kyiv warns', 'embassy kyiv shelter',
            'kyiv warns of imminent strike', 'ukraine prepares air defense',
            'russia preparing combined strike', 'signs of preparation strike',
            'kyiv intel imminent attack', 'partners warn russia strike',
            'european partners warn russia preparing',
            # ── v1.2 (May 24 2026) news-language expansion ──
            'zelensky says russia preparing',
            'ukrainian intelligence warns',
            'ukrainian intel warns', 'intelligence indicates russia',
            'kyiv intelligence warning',
            'embassy security alert kyiv', 'embassy alert kyiv',
            'embassy advisory kyiv', 'embassy warns americans kyiv',
            'shelter in place kyiv', 'shelter-in-place kyiv',
            'imminent strike ukraine', 'imminent attack ukraine',
            'partners share intelligence ukraine',
        ],
    },
    {
        'id':       'kyiv_strike_significant',
        'category': 'Strategic Strike',
        'title':    'Significant Strike on Kyiv',
        'severity': 4,
        'description':
            'Major Russian strike against Kyiv with civilian casualties or '
            'significant infrastructure damage — government district, '
            'mass civilian targets, presidential or military command '
            'facilities. v1.1 (May 24 2026): expanded for Oreshnik / '
            'hypersonic IRBM / mass combined missile-drone attack signatures '
            '(e.g. May 24 2026 attack: >50 missiles + 700 drones on Kyiv).',
        'triggers_breached': [
            'kyiv strike major', 'kyiv casualties mass', 'kyiv attack civilian',
            'presidential building hit', 'kyiv government strike',
            # ── v1.1 — mass + novel-weapon breach signatures ──
            'oreshnik strike kyiv', 'oreshnik hits ukraine',
            'hypersonic strike kyiv', 'hypersonic missile hits ukraine',
            'mass missile attack kyiv', 'combined strike kyiv casualties',
            '700 drones ukraine', 'russia largest attack ukraine',
            'kyiv multiple districts damaged', 'damage in every district kyiv',
            # ── v1.2 (May 24 2026) news-language expansion -- SCALE words only.
            # v1.1.0 interpreter (Nov 3 2026): 'attack on kyiv', 'strike on kyiv',
            # 'kyiv casualties', 'injured in kyiv' etc. moved to APPROACHING. They
            # fire on routine strikes ("Teenager injured in Russian attack on Kyiv
            # region") -- every week of this war. A breach needs scale or target.
            'massive attack kyiv', 'large-scale attack kyiv', 'massive strike on kyiv',
            'massive attack on kyiv', 'large-scale attack on kyiv', 'massive russian attack on kyiv',
            'combined attack on kyiv', 'mass attack on kyiv', 'government building in kyiv',
            'government quarter in kyiv', 'government building damaged in kyiv',
            'oreshnik kyiv', 'hypersonic kyiv',
            'cabinet of ministers damaged',
            'cabinet of ministers building', 'government building damaged kyiv',
            'mfa damaged', 'foreign ministry damaged kyiv',
            'kyiv buildings damaged',
            
        ],
        'triggers_approaching': [
            # v1.1.0 interpreter: routine-strike phrases (were breach triggers)
            'russia attacks kyiv', 'attack on kyiv', 'strike on kyiv', 'missile strike kyiv',
            'overnight attack kyiv', 'civilians killed kyiv', 'killed in kyiv strike',
            'kyiv casualties', 'kyiv civilian deaths', 'injured in kyiv', 'wounded in kyiv',
            'kyiv attacked', 'kyiv shahed', 'air raid kyiv',
            'kyiv missile', 'air defense kyiv',
            # ── v1.1 — pre-strike / scale-of-attack approaching signals ──
            'oreshnik preparing', 'russia preparing oreshnik',
            'hypersonic missile preparation russia', 'russia preparing strike',
            'preparing combined strike ukraine', 'combined strike preparation',
            'mass attack preparation', 'overnight strike kyiv',
            'salvo attack approaching', 'wave of missiles incoming',
            'polish jets scramble', 'nato jets scramble ukraine',
            # ── v1.2 (May 24 2026) news-language expansion ──
            'kyiv region attack', 'kyiv region strike', 'attack kyiv region',
            'shahed kyiv', 'drones over kyiv', 'air alert kyiv',
            'air raid alert kyiv', 'air defense activated kyiv',
            'explosions kyiv', 'explosions heard kyiv', 'kyiv damaged',
            'damage in kyiv', 'fire in kyiv', 'kyiv district damaged',
            'russian missiles kyiv', 'russian drones kyiv',
        ],
    },
    {
        'id':       'ukraine_strike_russia_significant',
        'category': 'Strategic Strike',
        'title':    'Significant Ukrainian Strike on Russia',
        'severity': 4,
        'description':
            'Major Ukrainian deep strike against Moscow, the Russian capital, '
            'or strategic Russian energy infrastructure -- record-scale drone '
            'barrages on Moscow, refinery fires, capital airport closures. The '
            'OUTBOUND mirror of a significant strike on Kyiv: a record strike '
            'is a record strike. v1.2 (Jun 18 2026): built for the largest '
            'Ukrainian drone attack on Moscow of the war (4 airports closed, '
            'Moscow refinery ablaze).',
        'triggers_breached': [
            'barrage on moscow', 'drone barrage on moscow', 'ukrainian drone barrage',
            'attack on moscow', 'strike on moscow', 'strikes on moscow',
            'attack on the russian capital', 'strike on the russian capital',
            'on the russian capital', 'largest drone attack on moscow',
            'record drone attack on moscow', 'massive drone attack moscow',
            'mass drone attack moscow', 'moscow under attack',
            'ukraine strikes moscow', 'ukraine hits moscow', 'ukrainian drones hit moscow',
            'moscow refinery ablaze', 'moscow oil refinery', 'moscow refinery struck',
            'moscow refinery on fire', 'russian refinery ablaze', 'russian refinery on fire',
            'struck russian refinery', 'moscow airports closed', 'moscow airports shut',
            'moscow airport closed', 'airports closed moscow',
        ],
        'triggers_approaching': [
            'drones over moscow', 'drones approaching moscow', 'air alert moscow',
            'air raid moscow', 'air defense moscow', 'moscow air defense',
            'moscow region drone', 'moscow oblast drone', 'explosions near moscow',
            'explosions moscow', 'fire near moscow', 'drones downed moscow',
            'drones intercepted moscow', 'russia downs drones', 'moscow will burn',
            'russian fuel shortage', 'russian gasoline shortage', 'russia fuel rationing',
            'ukraine threatens moscow', 'ukraine vows strikes russia',
        ],
    },
    {
        'id':       'drone_advisor_export_disclosed',
        'category': 'Defense Industry (cross-theatre)',
        'title':    'Ukrainian Drone Advisor Export Operations Disclosed',
        'severity': 3,
        'description':
            'Public disclosure or expansion of Ukrainian drone advisor / '
            'training operations to GCC partners (UAE, Saudi Arabia, Israel) '
            'or other partners. Unique Ukrainian leverage vector — defense '
            'knowledge as strategic export.',
        'triggers_breached': [
            'ukrainian drone advisors uae', 'ukrainian advisors saudi',
            'ukraine drone training gcc', 'ukrainian drone instructors',
            'ukraine drone export disclosed', 'kyiv drone training abroad',
        ],
        'triggers_approaching': [
            'ukraine drone partnership', 'ukraine defense export',
            'ukrainian drone industry', 'kyiv drone diplomacy',
        ],
    },
    {
        'id':       'grain_corridor_disruption',
        'category': 'Commodity / Strategic',
        'title':    'Black Sea Grain Corridor Disruption',
        'severity': 3,
        'description':
            'Major Russian attack on grain corridor infrastructure (Odesa '
            'ports, ships, insurance regime collapse). Ripples into MENA '
            'food security and global commodity markets.',
        'triggers_breached': [
            'odesa port strike major', 'grain ship hit',
            'grain corridor blocked', 'insurance withdrawal black sea',
            'grain export halted',
        ],
        'triggers_approaching': [
            'odesa attack', 'grain ship threat', 'black sea drone',
            'grain corridor pressure',
        ],
    },
    {
        'id':       'mobilization_crisis_ukraine',
        'category': 'Manpower',
        'title':    'Ukrainian Mobilization Crisis',
        'severity': 3,
        'description':
            'Indicators of severe Ukrainian manpower shortage — political '
            'crisis over conscription, mass evasion, frontline unit collapse '
            'from undermanning, or major mobilization law overhaul.',
        'triggers_breached': [
            'mobilization crisis', 'conscription crisis', 'tcc protests',
            'manpower shortage critical', 'mobilization riots',
        ],
        'triggers_approaching': [
            'mobilization protest', 'tcc tension', 'recruitment shortfall',
            'conscription debate', 'mobilization age lowered',
        ],
    },
    {
        'id':       'occupation_atrocity_disclosure',
        'category': 'Occupied Territories',
        'title':    'Major Atrocity Disclosure in Occupied Territories',
        'severity': 3,
        'description':
            'Disclosure of significant civilian atrocity, mass deportation '
            'event, or filtration camp expansion in Russian-occupied '
            'territories. Drives Western political pressure and ICC dynamics.',
        'triggers_breached': [
            'mass grave found', 'filtration camp disclosed',
            'forced deportation children mass', 'icc warrant new',
            'atrocity site disclosed',
        ],
        'triggers_approaching': [
            'occupation report', 'filtration camp', 'forced russification',
            'children deported', 'mariupol survivors',
        ],
    },
    {
        'id': 'crimea_bsf_displacement',
        'category': 'Occupied Territories',
        'title': 'Black Sea Fleet Displacement from Crimea (RUMINT)',
        'severity': 3,
        'description':
            'Ukrainian-sourced reports of Black Sea Fleet command and '
            'military-family relocation OUT of occupied Sevastopol toward '
            'Novorossiysk, under the sustained Ukrainian strike campaign on '
            'Crimea. Consistent with successful sea-denial and logistics '
            'strain on Russian naval infrastructure. CONVERGENCE / RUMINT '
            'framing: this is a pressure read on Russian control of occupied '
            'territory, NOT evidence of a Russian decision to concede Crimea '
            'and NOT a change in stated war aims. Sources are partisan '
            '(Atesh reconnaissance) and leaked garrison orders — interested '
            'parties; the confirmable core is the strike campaign, not the '
            'evacuation decision. A genuine concession signal would come as '
            'OFFICIAL Russian language, not Ukrainian partisan leaks.',
        'triggers_breached': [
            'black sea fleet evacuation', 'black sea fleet withdrawal',
            'sevastopol evacuation', 'fleet command novorossiysk',
            'fleet relocation novorossiysk',
        ],
        'triggers_approaching': [
            'crimea evacuation', 'evacuate crimea', 'crimea military families',
            'bsf withdrawal', 'pinchuk sevastopol', 'atesh', 'void group',
        ],
    },
]


# ============================================================
# GREEN LINES
# ============================================================
GREEN_LINES = [
    {
        'id':       'ceasefire_framework_active',
        'category': 'Diplomatic',
        'title':    'Ukraine Ceasefire Framework Active',
        'description':
            'Concrete ceasefire negotiation framework underway — named '
            'envoys, agreed venue, line-of-contact discussions, prisoner '
            'exchange momentum. v1.1 (May 24 2026): Expanded with broader '
            'keyword set tuned to catch EARLY-TREND signals (analyst pieces, '
            'social/Reddit chatter, leaked frameworks, columnist op-eds, '
            'Trump statements about Ukraine peace) BEFORE a formal framework '
            'emerges. Currently NO active ceasefire track but architecture is '
            'in place to detect tilt toward one.',
        'triggers_active': [
            'ceasefire framework', 'ceasefire negotiation', 'minsk format revived',
            'istanbul format', 'witkoff zelensky', 'negotiated settlement framework',
            # ── v1.1 — additional concrete-framework signals ──
            'ukraine ceasefire agreement', 'ukraine peace deal signed',
            'ukraine peace agreement signed', 'ukraine ceasefire signed',
            'ukraine ceasefire announced', 'russia ukraine ceasefire signed',
            'ukraine us russia framework', 'ukraine framework agreement',
            'ukraine peace framework signed', 'witkoff putin ukraine',
            'kellogg ukraine envoy', 'keith kellogg ukraine',
            'trump putin ukraine deal', 'trump putin ukraine framework',
            'ukraine 14-point peace plan', 'ukraine peace plan agreed',
            'line of contact agreed', 'ukraine territorial concession',
            'ukraine eu fast track', 'ukraine nato pathway agreed',
        ],
        'triggers_signaled': [
            'ceasefire talks', 'negotiation possibility',
            'diplomatic opening ukraine',
            # v1.2 (Jun 2026) -- looser real-headline phrasings + Kushner
            'kushner', 'jared kushner', 'us envoys', 'us envoys ukraine',
            'peace efforts', 'peace efforts ukraine', 'positive call',
            'zelensky us envoys', 'zelensky peace efforts', 'zelensky witkoff',
            'zelensky kushner', 'moscow intentions', 'white house ukraine peace',
            # ── v1.1 — early-trend / soft / chatter signals ──
            'trump ukraine peace', 'trump push ukraine peace',
            'trump pressures zelensky', 'trump pressures ukraine',
            'trump pressures russia', 'trump pressures putin',
            'trump ukraine deal', 'trump zelensky deal',
            'us push ukraine ceasefire', 'witkoff ukraine envoy',
            'witkoff ukraine mission', 'witkoff kyiv visit',
            'witkoff moscow visit', 'witkoff zelensky meeting',
            'kellogg ukraine plan', 'us envoy kyiv',
            'us envoy moscow ukraine', 'ukraine negotiations possible',
            'putin signals talks', 'putin open to talks',
            'putin negotiations possible', 'kremlin signals openness',
            'lavrov ukraine talks', 'lavrov negotiations possible',
            'zelensky open negotiations', 'zelensky considers talks',
            'zelensky willing talks', 'zelensky talks possible',
            'zelensky peace offer', 'ukraine peace offer',
            'kyiv negotiations possible', 'kyiv open to talks',
            'european push ceasefire', 'european push peace ukraine',
            'macron ukraine peace', 'starmer ukraine peace',
            'merz ukraine peace', 'erdogan ukraine peace',
            'turkey mediation ukraine', 'china mediation ukraine',
            'india mediation ukraine', 'saudi mediation ukraine',
            'ukraine peace conference', 'peace summit ukraine',
            'ukraine peace summit announced',
            'ukraine ceasefire possibility', 'ukraine deal possibility',
            'ceasefire trial balloon', 'leaked ceasefire framework',
            'leaked peace plan ukraine', 'reported peace plan ukraine',
            'reported ceasefire framework', 'rumored ukraine ceasefire',
            'ukraine ceasefire speculation', 'analysts ukraine ceasefire',
            'reuters ukraine peace', 'ft ukraine peace plan',
            'wsj ukraine peace plan', 'bloomberg ukraine peace',
            'ap ukraine ceasefire', 'ukraine off ramp',
            'путин переговоры украина', 'мирный план украина',
            'переговоры украина прекращение', 'witkoff украина',
        ],
    },
    {
        'id':       'us_aid_continuity',
        'category': 'Western Support',
        'title':    'US Aid Continuity Confirmed',
        'description':
            'Trump administration confirms aid continuation, weapons '
            'authorization, or new military package. De-risks war posture.',
        'triggers_active': [
            'aid continued ukraine', 'weapons authorized ukraine',
            'patriot delivery', 'atacms approved', 'aid package signed',
        ],
        'triggers_signaled': [
            'aid signal positive', 'trump ukraine aid',
            'congressional support ukraine',
        ],
    },
    {
        'id':       'european_aid_surge',
        'category': 'Western Support',
        'title':    'European Aid Surge / Backfill',
        'description':
            'Major European aid surge (Germany, UK, France, EU) potentially '
            'backfilling US gaps. Signals durable European commitment.',
        'triggers_active': [
            'germany aid package', 'uk weapons ukraine', 'eu peace facility',
            'european aid surge', 'rheinmetall expansion',
        ],
        'triggers_signaled': [
            'european commitment ukraine', 'eu defense support',
        ],
    },
    {
        'id':       'prisoner_exchange_momentum',
        'category': 'Humanitarian',
        'title':    'Prisoner Exchange Momentum',
        'description':
            'Major prisoner exchange completed or scheduled — particularly '
            'Mariupol defenders, journalists, or civilian hostages.',
        'triggers_active': [
            'prisoner exchange completed', 'pow swap', 'azov defenders home',
            'civilian prisoner returned', 'mass exchange',
        ],
        'triggers_signaled': [
            'prisoner exchange planned', 'pow negotiation',
        ],
    },
    {
        'id':       'reconstruction_signaling',
        'category': 'Recovery',
        'title':    'Reconstruction Commitment Signaling',
        'description':
            'Concrete reconstruction commitments — Lugano follow-on, EU '
            'frozen-asset deployment, IMF Ukraine facility expansion.',
        'triggers_active': [
            'frozen assets deployed', 'reconstruction package agreed',
            'ukraine recovery fund', 'eu reconstruction confirmed',
        ],
        'triggers_signaled': [
            'reconstruction conference', 'recovery framework',
            'lugano follow on',
        ],
    },
    {
        'id':       'hungary_bilateral_normalization',
        'category': 'Bilateral',
        'title':    'Hungary Bilateral Normalization Active',
        'description':
            'Post-April 2026 Tisza/Magyar government has reversed 16 years of '
            'Orban-era anti-Ukraine policy. Hungary lifted Ukraine EU loan veto, '
            'returned $82M Oschadbank cash + gold shipment seized in March, '
            'pledged "strong NATO ally" posture, signaled openness to resolve '
            'Transcarpathia ethnic Hungarian minority dispute. Removes Putin\'s '
            'primary EU veto vehicle and restores NATO consensus on weapons transit.',
        'triggers_active': [
            'hungary returns ukraine 82 million',
            'hungary returns oschadbank',
            'hungary returns ukrainian gold',
            'hungary returns ukrainian valuables',
            'hungary lifts loan veto',
            'hungary unlocks eu loan',
            'hungary eu funds released',
            'zelensky magyar summit',
            'magyar zelensky',
            'hungary lifts ukraine accession veto',
            'tisza government supports ukraine',
        ],
        'triggers_signaled': [
            'magyar tisza government',
            'hungary new government ukraine',
            'orban concedes',
            'hungary article 7 closed',
            'hungary nato ally pledge',
            'hungary returns gold ukraine',
        ],
    },
]


# ============================================================
# COMMODITY INTEGRATION
# ============================================================

def _fetch_commodity_signal():
    """Reads from Europe commodity proxy. Returns analytical band + modifier."""
    try:
        resp = requests.get(COMMODITY_PROXY_URL, timeout=4)
        if resp.status_code != 200:
            return None
        d = resp.json()
        if not d.get('success', True):
            return None

        alert = (d.get('alert_level') or 'normal').lower()
        pressure = d.get('commodity_pressure', 0)
        commodities = d.get('commodity_summaries') or []

        modifier_map = {'normal': 0, 'elevated': 1, 'high': 3, 'critical': 5, 'surge': 5}
        modifier = modifier_map.get(alert, 0)

        # Strategic priority — Ukraine's distinctive commodities first.
        # Wheat is the headline (pre-war top-5 wheat exporter, Black Sea corridor signal).
        # Corn and sunflower_oil are secondary (Odesa port dependency, ~50% global sunflower).
        # Falls back to highest-signal-count if no priority match.
        UKRAINE_COMMODITY_PRIORITY = ['wheat', 'corn', 'sunflower_oil']

        if commodities:
            top_c = None
            for priority_key in UKRAINE_COMMODITY_PRIORITY:
                for c in commodities:
                    if (c.get('commodity') == priority_key
                            and (c.get('signal_count', 0) or 0) >= 1):
                        top_c = c
                        break
                if top_c:
                    break
            if not top_c:
                top_c = max(commodities, key=lambda c: c.get('signal_count', 0) or 0)

            top_name = (top_c.get('name') or top_c.get('commodity') or 'commodity').upper()
            top_sigs = top_c.get('signal_count', 0)
            short = f"Commodity Pressure: {alert.upper()} — {top_name} ({top_sigs} signals)"
        else:
            short = f"Commodity Pressure: {alert.upper()}"

        long_parts = [
            "Pre-war Ukraine: world's #1 sunflower oil exporter, top-3 corn, top-5 wheat.",
            "Black Sea grain corridor disruption ripples into MENA food security signals.",
            "Defense industrial base — including drone advisor exports — is unique strategic vector.",
        ]
        if commodities:
            top3 = sorted(commodities, key=lambda c: c.get('signal_count', 0) or 0, reverse=True)[:3]
            cmd_summary = ', '.join(
                f"{(c.get('name') or c.get('commodity') or '').upper()} ({c.get('signal_count', 0)})"
                for c in top3
            )
            long_parts.append(f"Top exposures by signal count: {cmd_summary}.")
        long = ' '.join(long_parts)

        # Map alert level → integer level (matches escalation ladder used elsewhere)
        # AND alert color (matches commodity_tracker palette so card visuals are consistent)
        ALERT_LEVEL_MAP = {
            'normal':    1,    # gray-cool baseline
            'elevated':  3,    # amber
            'high':      4,    # orange
            'critical':  5,    # red
            'surge':     5,    # red — same severity as critical
        }
        ALERT_COLOR_MAP = {
            'normal':    '#3b82f6',   # blue — baseline rhetoric
            'elevated':  '#fbbf24',   # amber
            'high':      '#fb923c',   # orange
            'critical':  '#ef4444',   # red
            'surge':     '#dc2626',   # deep red — convergence trigger
        }
        int_level = ALERT_LEVEL_MAP.get(alert, 1)
        alert_color = ALERT_COLOR_MAP.get(alert, '#6b7280')

        band = {
            'category':    'commodity',
            'level':       int_level,        # int — matches schema used elsewhere
            'alert_level': alert,             # keep the string too for display/debug
            'color':       alert_color,       # explicit color so europe BLUF doesn't fall through to gray
            'short_text':  short,
            'long_text':   long,
            'icon':        '🛢️',
            'source_link': '/commodities.html#wheat',
            'pressure':    pressure,
        }
        return {
            'band':                band,
            'escalation_modifier': modifier,
            'pressure':            pressure,
            'alert':               alert,
        }
    except Exception as e:
        print(f'[Ukraine Interpreter] Commodity fetch failed: {str(e)[:120]}')
        return None
# ============================================================
# DIPLOMATIC TRACK
# ============================================================

CEASEFIRE_TRIGGERS = [
    # v1.1.0 (Nov 3 2026): local / humanitarian ceasefires are the live track in
    # autumn 2026 (Oleshky evacuation, energy-ceasefire proposals).
    'temporary ceasefire', 'local ceasefire', 'humanitarian ceasefire', 'energy ceasefire',
    'humanitarian corridor', 'ombudsmen', 'prisoner exchange',
    # ── v1.2 (Jun 2026) — looser headline/lede/URL-slug phrasings + Kushner ──
    # The narrow contiguous phrases below miss real headline wording such as
    # "peace efforts in positive call with US envoys". These match the words
    # actually used in titles, ledes, and URL slugs.
    'kushner', 'jared kushner', 'kushner ukraine', 'kushner zelensky',
    'witkoff', 'steve witkoff', 'us envoys', 'us envoy', 'special envoy ukraine',
    'us envoys ukraine', 'zelensky us envoys', 'zelensky envoys', 'envoys ukraine',
    'zelensky witkoff', 'zelensky kushner', 'zelensky discusses peace',
    'peace efforts', 'peace effort ukraine', 'peace efforts ukraine', 'peace push',
    'positive call', 'positive talks', 'constructive call', 'constructive talks',
    'moscow intentions', 'moscows intentions', 'russia intentions ukraine',
    'peace negotiations', 'peace process ukraine', 'diplomatic push ukraine',
    'white house ukraine peace', 'trump envoy ukraine', 'ceasefire discussions',
    # ── Concrete-framework signals (original) ──
    'ceasefire negotiation', 'witkoff zelensky', 'istanbul format',
    'minsk format revived', 'envoy ukraine russia',
    'переговоры украина', 'мирный процесс',
    # ── v1.1 (May 24 2026) — Earlier-trend signals ──
    # Anything from analyst commentary to leaked frameworks to social
    # chatter that suggests the diplomatic track is warming.
    'trump putin ukraine', 'trump zelensky deal', 'trump ukraine peace',
    'witkoff ukraine', 'witkoff kyiv', 'witkoff moscow',
    'witkoff putin ukraine', 'kellogg ukraine envoy',
    'us envoy ukraine', 'us envoy moscow ukraine',
    'ukraine ceasefire framework', 'ukraine peace framework',
    'ukraine peace plan', 'ukraine 14-point plan',
    'ukraine peace conference', 'ukraine peace summit',
    'putin open negotiations', 'putin signals talks',
    'kremlin signals openness', 'kremlin negotiations possible',
    'zelensky open talks', 'zelensky open negotiations',
    'zelensky peace offer', 'kyiv ceasefire offer',
    'turkey mediates ukraine', 'china mediates ukraine',
    'saudi mediates ukraine', 'european push ukraine peace',
    'leaked peace plan ukraine', 'leaked ceasefire framework',
    'reported ukraine peace plan', 'analyst ukraine ceasefire',
    'ukraine off ramp', 'ukraine de-escalation',
    'мирный план украина', 'трамп путин украина',
    'переговоры прекращение украина',
]


# Stance guard (v1.3, Jun 2026): phrases where peace is being REJECTED or is
# COLLAPSING. These are NOT de-escalation -- they net against positive ceasefire
# matches so "Moscow rejects peace" cannot read as a warming diplomatic track.
CEASEFIRE_NEGATORS = [
    'rejects peace', 'rejected peace', 'reject peace',
    'rejects ceasefire', 'rejected ceasefire', 'rejects the ceasefire',
    'rules out ceasefire', 'rules out talks', 'rules out negotiations',
    'refuses negotiations', 'refuses to negotiate', 'refuses ceasefire',
    'no ceasefire', 'no peace deal', 'no negotiations',
    'peace talks collapse', 'peace talks collapsed', 'talks collapse',
    'talks collapsed', 'negotiations collapse', 'ceasefire collapse',
    'peace talks fail', 'peace talks failed', 'breaks off talks',
    'walks away from talks', 'moscow rejects', 'kremlin rejects',
    'putin rejects', 'russia rejects peace',
]


# ============================================================
# VECTOR VOCABULARY (v1.1.0)
# ============================================================

# -- US vector: who is Washington leaning on? ------------------------------
US_AID_STRESS = [
    'patriot shortage', 'patriot shortfall', 'shortage of patriot', 'patriot interceptors shortage',
    'aid pause', 'aid paused', 'pauses aid', 'halted military aid', 'halts military aid',
    'halt military aid', 'no new aid', 'us aid cut', 'cut off aid', 'decline in american',
    'decline in us support', 'withdrawn support', 'withholding weapons', 'weapons delayed',
    'deliveries delayed', 'starlink restrictions', 'starshield', 'starlink slowdown',
    'intelligence sharing paused', 'intelligence pause', 'intelligence cut',
    'this is not support', 'us support declining', 'russian gas sales',
]
# Aid DELAY is read by co-occurrence: a weapons word AND a delay word in one item.
# "Ukraine won't receive 500 newly approved U.S. Patriot missiles until at least
# late 2030" names neither 'aid' nor 'pause' -- and is the aid story of the week.
US_AID_ITEM = ['patriot', 'interceptor', 'weapons', 'military aid', 'missiles', 'air defence', 'air defense',
               'himars', 'tomahawk', 'atacms', 'f-16']
US_AID_DELAY = ["won't receive", 'will not receive', 'not receive', 'until at least', 'until 2030', 'in 2030',
                'delayed until', 'delay in', 'delays', 'shortage', 'shortfall', 'only 24', 'span 3 years',
                'span three years', 'redirected to', 'diverted to']
US_AID_FLOW = [
    'purl', 'weapons package', 'approved sale', 'approves sale', 'patriot delivery',
    'patriots delivered', 'aid package', 'tomahawk', 'security assistance ukraine',
    'foreign military sale', 'nato-funded us weapons', 'us weapons ukraine',
    'us approves', 'state department approves',
]
US_PRESS_KYIV = [
    'trump pressures zelensky', 'trump pressures ukraine', 'trump presses zelensky',
    'trump blames zelensky', 'trump criticizes zelensky', 'trump criticises zelensky',
    'trump slams zelensky', 'trump says zelensky', 'trump tells zelensky', 'trump urges ukraine',
    'trump urges zelensky', 'zelensky has to', 'better deal', 'no cards', 'take the deal',
    'cede territory', 'give up donbas', 'hand over donbas', 'withdraw from donbas',
    "i don't care how it's done", 'pressure on kyiv', 'pressure on zelensky',
    'pressures ukraine to', 'pressures kyiv', 'ultimatum to ukraine', 'deadline for ukraine',
]
US_PRESS_MOSCOW = [
    'trump sanctions russia', 'sanctions on rosneft', 'sanctions on lukoil', 'new sanctions on russia',
    'trump pressures putin', 'trump threatens russia', 'trump criticizes putin', 'trump criticises putin',
    'secondary tariffs', 'trump slams putin', 'trump disappointed with putin', 'pressure on moscow',
    'pressure on putin',
]
US_EASE_MOSCOW = [
    'sanctions waiver', 'waived sanctions', 'waives sanctions', 'lift sanctions on russia',
    'easing sanctions', 'eases sanctions', 'russian diesel', 'trump putin summit', 'trump invites putin',
    'russian gas sales', 'resuming russian gas', 'resume russian gas',
]
US_ENVOY = [
    'witkoff', 'kushner', 'us envoy', 'us envoys', 'trilateral talks', 'trilateral meeting',
    'abu dhabi talks', 'rubio ukraine', 'peace talks ukraine', 'melania trump',
]

# -- NATO track ------------------------------------------------------------
NATO_OFF_TABLE = [
    'drop nato bid', 'drops nato', 'dropping nato', 'abandon nato', 'abandons nato',
    'renounce nato', 'renounces nato', 'nato renunciation', 'neutral status', 'neutrality for ukraine',
    'ukrainian neutrality', 'no nato membership', 'never join nato', 'nato off the table',
    'non-aligned status', 'gives up nato', 'give up nato', 'nato ambitions', 'renouncing nato',
    'renunciation of nato', 'renunciation of its nato', 'drop its nato', 'abandoning nato',
]
NATO_GUARANTEE = [
    'security guarantees', 'security guarantee', 'article 5-like', 'article 5 like', 'article 5-style',
    'article five', 'article 5 protection', 'coalition of the willing', 'reassurance force',
    'multinational force ukraine', 'bilateral security agreement', 'nato-like', 'backstop',
]
NATO_MEMBERSHIP = [
    'nato membership', 'join nato', 'joining nato', 'nato invitation', 'invitation to nato',
    'nato accession', 'irreversible path', 'nato-ukraine council', 'ukraine in nato',
]
# Date-stamped background. Not scored. Review when the trilateral round lands.
NATO_BASELINE = {
    'as_of': '2026-10-25',
    'membership': 'No invitation. Admission needs all 32 allies; the 2008 Bucharest pledge has no date attached.',
    'support': 'Ankara summit (2026): allies recorded EUR 70bn/yr in military support for 2026, at least the same for 2027.',
    'moscow_demand': 'A legally binding renunciation of the NATO bid -- the Kremlin calls it a "cornerstone" of any deal.',
    'kyiv_position': ('Membership, or Article-5-style protection from Europe and the US if membership is blocked. '
                      'Neutrality and limits on Ukraine\'s army are "not up for discussion" (Zelensky, Oct 25 2026).'),
    'sources': ['https://kyivindependent.com/zelensky-details-expectations-for-upcoming-trilateral-peace-talks-with-russia-us/',
                'https://www.fair.org.ua/en/ukraina-v-nato-shliakh-suchasnyi-status-ta-perspektyvy-chlenstva/'],
}

# -- Drone diplomacy / the Iran link -------------------------------------------
GULF_DRONE = [
    'ukrainian drone experts', 'ukrainian military experts', 'ukrainian specialists gulf',
    'ukrainian interceptor', 'ukrainian interceptors', 'interceptor drones', 'shahed interceptor',
    'ukraine gulf', 'ukraine saudi drone', 'ukraine uae drone', 'ukraine qatar drone',
    'ukraine drone deal', 'joint production drones', 'drone advisors', 'drone instructors',
    'ukrainian advisors uae', 'ukrainian advisors saudi', 'kyiv drone diplomacy',
    'ukraine drone export', 'ukraine israel drone', 'ukraine drone gcc',
]
IRAN_SUPPLY = [
    'caspian', 'iranian drones to russia', 'iranian drones russia', 'iran supplies russia',
    'shahed supply', 'iranian missiles to russia', 'iranian missiles russia', 'alabuga',
    'geran-2', 'geran 2', 'russia iran drone', 'russia supplies iran', 'russia supplied shahed',
    'brothers in hatred',
]
IRAN_FRICTION = [
    'iran threatens ukraine', 'iran warns ukraine', 'iran accuses ukraine', 'iran claims ukrainian',
    'ukrainian depot', 'iran condemns ukraine', 'tehran kyiv',
]

# Which red lines speak for which actor (for actor levels).
ACTOR_LINES = {
    'russian_forces_in_ukraine': ['kyiv_strike_significant', 'energy_grid_collapse', 'frontline_collapse',
                                  'pre_strike_warning_issued', 'tactical_nuclear_signaling',
                                  'grain_corridor_disruption'],
    'ukrainian_armed_forces': ['ukraine_strike_russia_significant', 'crimea_bsf_displacement'],
    'ukrainian_government': ['mobilization_crisis_ukraine'],
    'us_government': ['us_aid_suspension_total'],
    'defense_industrial_base': ['drone_advisor_export_disclosed'],
    'occupied_territories_signals': ['occupation_atrocity_disclosure', 'crimea_bsf_displacement'],
    'nato_western_support': [],
}
# Not an escalation line for Ukraine: read as a vector, kept out of the So What priority.
NON_ESCALATORY_LINES = {'drone_advisor_export_disclosed'}
STRATEGIC_LINES = {'kyiv_strike_significant', 'energy_grid_collapse', 'frontline_collapse',
                   'tactical_nuclear_signaling'}


# ============================================================
# RED / GREEN LINE SCORING (per article, outlets counted)
# ============================================================

def _score_red_lines(corpus):
    out = []
    for rl in RED_LINES:
        sc = score_line(corpus, rl.get('triggers_breached', []), rl.get('triggers_approaching', []))
        out.append({'id': rl['id'], 'category': rl['category'], 'title': rl['title'],
                    'severity': rl['severity'], 'description': rl['description'], **sc})
    return out


def _score_green_lines(corpus):
    out = []
    for gl in GREEN_LINES:
        sc = score_green(corpus, gl.get('triggers_active', []), gl.get('triggers_signaled', []))
        out.append({'id': gl['id'], 'category': gl['category'], 'title': gl['title'],
                    'description': gl['description'], **sc})
    return out


def _score_diplomatic_track(corpus, green_lines_triggered):
    matches = phrase_count(corpus, CEASEFIRE_TRIGGERS)
    negators = phrase_count(corpus, CEASEFIRE_NEGATORS)
    net_matches = max(0, matches - negators)
    active_gls = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']
    diplomatic_score = net_matches + (len(active_gls) * 2)
    framework_active = any(g.get('id') == 'ceasefire_framework_active' for g in active_gls)
    if diplomatic_score >= 6 and framework_active:
        scenario, modifier = 'Active Ceasefire Track', -10
    elif diplomatic_score >= 3:
        scenario, modifier = 'Tentative Diplomatic Signals', -5
    elif diplomatic_score >= 1:
        scenario, modifier = 'Limited De-escalation Indicators', -2
    else:
        scenario, modifier = 'No Active Track', 0
    return {'score': diplomatic_score, 'scenario': scenario, 'modifier': modifier,
            'active_green_lines_count': len(active_gls), 'framework_active': framework_active,
            'negator_hits': negators}


def _rl(lines, rid):
    return next((r for r in lines if r.get('id') == rid), {})


def _uniq(evs, n=5):
    """One headline once, even when it matched two vocabularies."""
    seen, out = set(), []
    for e in evs:
        k = (e.get('title') or '').lower()[:120]
        if k and k not in seen:
            seen.add(k)
            out.append(e)
    return out[:n]


def _st(d):
    return (d.get('status') or 'INACTIVE').upper()


# ============================================================
# VECTORS (v1.1.0)
# ============================================================

def _us_vector(corpus, red_lines):
    """The US spoke. Level = how hard Washington is pulling on this war this cycle,
    in either direction; `posture` says which way."""
    stress = find(corpus, US_AID_STRESS)
    for it in corpus:   # co-occurrence: weapons word + delay word in one item
        if it['kind'] == 'news' and any(w in it['text'] for w in US_AID_ITEM) \
                and any(d in it['text'] for d in US_AID_DELAY) and ('ukrain' in it['text'] or 'kyiv' in it['text']):
            if it['outlet'] not in stress['outlets'] and len(stress['evidence']) < 4:
                stress['evidence'].append({'title': it['title'][:180], 'outlet': it['outlet'],
                                           'url': it['url'], 'phrase': 'weapons + delay'})
            stress['outlets'].add(it['outlet'])
    flow = find(corpus, US_AID_FLOW)
    kyiv = find(corpus, US_PRESS_KYIV)
    moscow = find(corpus, US_PRESS_MOSCOW)
    ease = find(corpus, US_EASE_MOSCOW)
    envoy = find(corpus, US_ENVOY)
    susp = _rl(red_lines, 'us_aid_suspension_total')
    n = {k: len(v['outlets']) for k, v in (('stress', stress), ('flow', flow), ('kyiv', kyiv),
                                          ('moscow', moscow), ('ease', ease), ('envoy', envoy))}
    if _st(susp) == 'BREACHED':
        aid = 'suspended'
    elif _st(susp) == 'APPROACHING' or n['stress'] >= 2:
        aid = 'thinning'
    elif n['flow'] >= 1:
        aid = 'flowing'
    elif n['stress'] == 1:
        aid = 'questioned'
    else:
        aid = 'not_reported'
    pk, pm = outlet_level(n['kyiv']), outlet_level(n['moscow'])
    if pk >= 2 and pm >= 2:
        posture = 'pressing_both'
    elif pk >= 2 and pk > pm:
        posture = 'pressing_kyiv'
    elif pm >= 2:
        posture = 'pressing_moscow'
    elif n['envoy'] >= 1:
        posture = 'mediating'
    else:
        posture = 'quiet'
    aid_lv = {'suspended': 4, 'thinning': 3, 'questioned': 1}.get(aid, 0)
    level = min(4, max(pk, pm, aid_lv, min(2, outlet_level(n['envoy']))))
    parts = []
    if posture == 'pressing_kyiv':
        parts.append(f"Washington's public pressure is running mainly toward Kyiv ({n['kyiv']} outlets) "
                     f"rather than Moscow ({n['moscow']}).")
    elif posture == 'pressing_both':
        parts.append(f"Washington is leaning on both capitals ({n['kyiv']} outlets on Kyiv, {n['moscow']} on Moscow).")
    elif posture == 'pressing_moscow':
        parts.append(f"Washington's pressure is running mainly toward Moscow ({n['moscow']} outlets).")
    elif posture == 'mediating':
        parts.append(f"The US envoy track is active ({n['envoy']} outlets) without a clear lean.")
    if n['ease'] >= 1:
        parts.append(f"Signals of easing on Moscow (waivers, summitry) in {n['ease']} outlet(s).")
    parts.append({'suspended': 'US aid: suspension reported by 2+ outlets.',
                  'thinning': 'US aid: shortfalls reported (interceptors, deliveries, Starlink/intelligence).',
                  'flowing': 'US aid: deliveries or sales reported.',
                  'questioned': 'US aid: one outlet reports strain.',
                  'not_reported': 'US aid: not in the corpus this cycle.'}[aid])
    return {
        'level': level, 'posture': posture, 'aid_pipeline': aid,
        'pressure_on_kyiv': pk, 'pressure_on_moscow': pm,
        'easing_on_moscow': outlet_level(n['ease']), 'envoy_track': outlet_level(n['envoy']),
        'outlets': n, 'read': ' '.join(parts),
        'evidence': _uniq(kyiv['evidence'][:2] + moscow['evidence'][:1] + stress['evidence'][:2] + ease['evidence'][:1]),
    }


def _nato_track(corpus):
    off = find(corpus, NATO_OFF_TABLE)
    gua = find(corpus, NATO_GUARANTEE)
    mem = find(corpus, NATO_MEMBERSHIP)
    no, ng, nm = len(off['outlets']), len(gua['outlets']), len(mem['outlets'])
    if no >= 2:
        status = 'renunciation_on_table'
        read = (f'Renouncing the NATO bid is being discussed in {no} outlets. Moscow treats a legally binding '
                'renunciation as a cornerstone; Kyiv has tied any such step to binding guarantees.')
    elif ng >= 2:
        status = 'guarantees_in_play'
        read = (f'Security guarantees are on the table ({ng} outlets) -- the substitute for membership. '
                'What matters is whether they are binding and who would enforce them.')
    elif nm >= 1 or ng == 1 or no == 1:
        status = 'raised'
        read = 'NATO is mentioned in the corpus but no direction has corroboration this cycle.'
    else:
        status = 'quiet'
        read = 'NATO is not in this cycle\'s corpus.'
    return {'status': status, 'level': max(outlet_level(no), outlet_level(ng)),
            'renunciation_outlets': no, 'guarantee_outlets': ng, 'membership_outlets': nm,
            'read': read, 'baseline': NATO_BASELINE,
            'evidence': _uniq(off['evidence'][:2] + gua['evidence'][:2] + mem['evidence'][:1], 4)}


def _drone_diplomacy(corpus, red_lines):
    gulf = find(corpus, GULF_DRONE)
    supply = find(corpus, IRAN_SUPPLY)
    fric = find(corpus, IRAN_FRICTION)
    adv = _rl(red_lines, 'drone_advisor_export_disclosed')
    ng, ns, nf = len(gulf['outlets']), len(supply['outlets']), len(fric['outlets'])
    gulf_lv = max(outlet_level(ng), {'APPROACHING': 2, 'BREACHED': 3}.get(_st(adv), 0))
    level = min(3, max(gulf_lv, outlet_level(ns), outlet_level(nf)))
    active = gulf_lv >= 2 or _st(adv) in ('APPROACHING', 'BREACHED')
    bits = []
    if gulf_lv >= 1:
        bits.append(f'Ukrainian counter-drone expertise or interceptors in the Gulf ({ng} outlets).')
    if ns:
        bits.append(f'The Iran-Russia supply line is in the corpus ({ns} outlets) -- Shahed/Geran, Caspian shipping.')
    if nf:
        bits.append(f'Iran-Ukraine friction reported ({nf} outlets).')
    if not bits:
        bits.append('The Ukraine-Iran link is quiet this cycle.')
    return {'level': level, 'active': active, 'gulf_outlets': ng, 'supply_line_outlets': ns,
            'iran_friction_outlets': nf, 'read': ' '.join(bits),
            'evidence': _uniq(gulf['evidence'][:2] + supply['evidence'][:2] + fric['evidence'][:1], 4)}


def _russia_pressure(red_lines):
    """The Russia wheel's spoke level. The war is the floor (L4); L5 only when a
    strategic red line is BREACHED on 2+ outlets."""
    breached = [r for r in red_lines if r['id'] in STRATEGIC_LINES and r['status'] == 'BREACHED']
    approaching = [r for r in red_lines if r['id'] in STRATEGIC_LINES | {'pre_strike_warning_issued'}
                   and r['status'] == 'APPROACHING']
    top = (breached or approaching or [None])[0]
    return {'level': 5 if breached else 4,
            'basis': 'strategic red line breached' if breached else 'active-war floor',
            'top_signal': (f"{top['title']} -- {top['status']} ({top.get('breach_outlets', 0) or top.get('approach_outlets', 0)} outlets)"
                           if top else '')}


def _actor_levels(scan_data, red_lines, us, drone):
    out = {}
    for key, s in (scan_data.get('actor_summaries') or {}).items():
        outlets = {str(a.get('source') or '').lower() for a in (scan_data.get('by_actor') or {}).get(key, [])
                   if not a.get('co_credit')}
        outlets.discard('')
        vol = min(2, len(outlets))            # breadth, capped: volume never climbs above L2
        line_lv = max([STATUS_LEVEL.get(_rl(red_lines, rid).get('status', 'INACTIVE'), 0)
                       for rid in ACTOR_LINES.get(key, [])] or [0])
        lv = max(vol, line_lv)
        if key == 'us_government':
            lv = max(lv, us['level'])
        if key == 'defense_industrial_base':
            lv = max(lv, drone['level'])
        out[key] = {'level': min(4, lv), 'outlet_count': len(outlets), 'line_level': line_lv}
    return out


# ============================================================
# SO WHAT
# ============================================================

def _build_so_what_narrative(red_lines, green_lines, diplomatic, commodity_signal, us, nato, drone, health):
    threads = []
    if health['thin']:
        threads.append({'label': 'THIN READ',
                        'text': (f"This scan is under-read ({health['reason']}). Quiet lines below may be "
                                 "unread, not quiet -- treat absences as blind spots."),
                        'tone': 'watch'})

    scen, fw, negs = diplomatic.get('scenario', 'No Active Track'), diplomatic.get('framework_active'), diplomatic.get('negator_hits', 0)
    if scen == 'Active Ceasefire Track' and fw:
        p_text, p_tone = 'A ceasefire framework is active -- framework-grade evidence. Terms, not talk.', 'calm'
    elif scen == 'Tentative Diplomatic Signals':
        p_text, p_tone = ('Peace conversations are live -- envoy contact, leader-level messaging, a trilateral '
                          'round -- but no signed framework. Talk, not terms.'), 'watch'
    elif scen == 'Limited De-escalation Indicators':
        p_text, p_tone = 'Scattered de-escalation chatter; no structured negotiating track yet.', 'watch'
    else:
        p_text, p_tone = 'No diplomatic off-ramp detected in the current scan.', 'alert'
    if negs:
        p_text += ' Counter-signal: language consistent with terms being rejected is also in the corpus.'
    threads.append({'label': 'PEACE TRAJECTORY', 'text': p_text, 'tone': p_tone})

    kyiv, grid, front = _rl(red_lines, 'kyiv_strike_significant'), _rl(red_lines, 'energy_grid_collapse'), _rl(red_lines, 'frontline_collapse')
    nuke, warn, deep = _rl(red_lines, 'tactical_nuclear_signaling'), _rl(red_lines, 'pre_strike_warning_issued'), _rl(red_lines, 'ukraine_strike_russia_significant')
    bits = []
    if _st(kyiv) in ('APPROACHING', 'BREACHED'):
        bits.append(f"significant strikes on Kyiv ({_st(kyiv).lower()}, {kyiv.get('breach_outlets', 0)} outlets)")
    if _st(warn) in ('APPROACHING', 'BREACHED'):
        bits.append('an active pre-strike warning')
    if _st(grid) in ('WATCHING', 'APPROACHING', 'BREACHED'):
        bits.append(f'energy-grid pressure ({_st(grid).lower()})')
    if _st(front) in ('APPROACHING', 'BREACHED'):
        bits.append('frontline-collapse indicators')
    if _st(deep) in ('APPROACHING', 'BREACHED'):
        bits.append(f'Ukrainian deep strikes into Russia ({_st(deep).lower()})')
    crimea = _rl(red_lines, 'crimea_bsf_displacement')
    if _st(crimea) in ('APPROACHING', 'BREACHED'):
        bits.append('Black Sea Fleet displacement from Crimea (RUMINT, unverified)')
    nuke_clause = '; nuclear signalling inactive' if _st(nuke) == 'INACTIVE' else '; nuclear signalling ' + _st(nuke).lower()
    if bits:
        a_text = 'Kinetic picture: ' + ', '.join(bits) + nuke_clause + '.'
        a_tone = 'elevated' if any(_st(x) in ('APPROACHING', 'BREACHED') for x in (kyiv, front, nuke)) else 'watch'
    else:
        a_text = ('Kinetic picture: the war continues at its sustained floor' + nuke_clause
                  + '. No red line above the floor is corroborated this scan.')
        a_tone = 'watch'
    threads.append({'label': 'RUSSIA-UKRAINE AXIS', 'text': a_text, 'tone': a_tone})

    # AMERICAN LEVERAGE -- the US spoke
    l_text = us['read']
    if us['posture'] == 'pressing_kyiv':
        l_text += (' When the mediator\'s public pressure falls mainly on one side, the terms on the table tend to '
                   'move toward the other side\'s position -- watch the territorial and NATO clauses.')
    if us['aid_pipeline'] in ('thinning', 'suspended'):
        l_text += (' Air defence is the pressure point: interceptor shortfalls show up first as Russian strikes '
                   'that get through, then as leverage at the table.')
    l_tone = 'alert' if us['aid_pipeline'] == 'suspended' or us['posture'] == 'pressing_kyiv' else (
        'watch' if us['level'] >= 2 else 'calm')
    threads.append({'label': 'AMERICAN LEVERAGE', 'text': l_text, 'tone': l_tone})

    # NATO TRACK
    n_text = nato['read'] + ' Baseline (' + nato['baseline']['as_of'] + '): ' + nato['baseline']['membership']
    if nato['status'] in ('renunciation_on_table', 'guarantees_in_play'):
        n_text += (' The trade being negotiated is membership for guarantees: a guarantee with no enforcer leaves '
                   'Ukraine where Budapest 1994 did; a guarantee backed by forces on the ground changes Moscow\'s '
                   'cost of a second invasion.')
    threads.append({'label': 'NATO TRACK', 'text': n_text,
                    'tone': 'elevated' if nato['status'] == 'renunciation_on_table' else 'watch'})

    # IRAN LINK
    if drone['level'] >= 1:
        i_text = drone['read'] + (' Ukraine is fighting the same Iranian-designed drone at both ends of the '
                                  'Russia-Iran axis: over its own cities and, as an exporter, over the Gulf. That '
                                  'turns Kyiv from aid recipient into a security provider Washington and the Gulf '
                                  'states need -- and gives Tehran a reason to treat Ukraine as a party.')
        threads.append({'label': 'IRAN LINK', 'text': i_text, 'tone': 'watch' if drone['level'] < 3 else 'elevated'})

    alert = (commodity_signal or {}).get('alert', 'normal')
    if commodity_signal and alert and alert != 'normal':
        corridor = _rl(red_lines, 'grain_corridor_disruption')
        g_text = ('Commodity pressure at ' + alert.upper() + ' on news-signal volume (not price); wheat / grain '
                  'corridor the lead exposure. Black Sea corridor indicator ' + _st(corridor).lower()
                  + '. Ripples toward MENA food-security signals.')
        g_tone = 'elevated' if alert in ('surge', 'critical', 'high') else 'watch'
    else:
        g_text, g_tone = 'Commodity pressure normal; grain corridor quiet on the commodity read.', 'calm'
    threads.append({'label': 'GRAIN COROLLARY', 'text': g_text, 'tone': g_tone})
    return threads


def _top_indicator(red_lines, us, nato, drone, health):
    esc = [r for r in red_lines if r['id'] not in NON_ESCALATORY_LINES]
    br = sorted([r for r in esc if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])
    ap = sorted([r for r in esc if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])
    if br:
        r = br[0]
        line = f"{r['title']}: corroborated by {r['breach_outlets']} outlets."
    elif us['posture'] == 'pressing_kyiv' and us['pressure_on_kyiv'] >= 2:
        line = 'Washington is leaning on Kyiv more than on Moscow ahead of the trilateral round.'
    elif nato['status'] == 'renunciation_on_table':
        line = 'Renouncing the NATO bid is on the table -- the trade is membership for guarantees.'
    elif ap:
        line = f"Watching: {ap[0]['title'].lower()} -- reported, not yet corroborated."
    else:
        line = 'The war continues at its sustained floor; nothing above it is corroborated this cycle.'
    if health['thin']:
        line = 'Thin read -- ' + line
    return line


def _build_so_what(red_lines, green_lines, diplomatic, commodity_signal, us, nato, drone, health):
    esc = [r for r in red_lines if r['id'] not in NON_ESCALATORY_LINES]
    breached = [r for r in esc if r['status'] == 'BREACHED']
    approaching = [r for r in esc if r['status'] == 'APPROACHING']
    active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']
    highest = max((r['severity'] for r in breached), default=0)
    if highest >= 5:
        scenario, priority = 'CRITICAL: Strategic Red Line Breached', 'critical'
    elif highest >= 4 or len(breached) >= 2:
        scenario, priority = 'HIGH: Multiple Escalation Indicators', 'high'
    elif breached or len(approaching) >= 3:
        scenario, priority = 'ELEVATED: Approaching Threshold', 'elevated'
    elif approaching:
        scenario, priority = 'WATCH: Early Warning Indicators Active', 'watch'
    else:
        scenario, priority = 'ACTIVE WAR: Sustained Kinetic Tempo', 'elevated'
    if health['thin']:
        scenario = 'THIN READ -- ' + scenario

    parts = []
    if health['thin']:
        parts.append(f"Under-read scan ({health['reason']}): absences below are blind spots, not calm.")
    if breached:
        parts.append('Red line(s) breached: ' + ', '.join(f"{r['title']} ({r['breach_outlets']} outlets)" for r in breached[:3]) + '.')
    if approaching:
        parts.append('Approaching threshold: ' + ', '.join(r['title'] for r in approaching[:3]) + '.')
    if diplomatic['score'] > 0:
        parts.append(f"Diplomatic track: {diplomatic['scenario'].lower()} (score {diplomatic['score']}).")
    if us['posture'] != 'quiet' or us['aid_pipeline'] not in ('not_reported',):
        parts.append('US: ' + us['read'])
    if nato['status'] != 'quiet':
        parts.append('NATO: ' + nato['read'])
    if active_gl:
        parts.append('Active de-escalation indicators: ' + ', '.join(g['title'] for g in active_gl[:2]) + '.')
    hu = next((g for g in green_lines if g['id'] == 'hungary_bilateral_normalization'), None)
    if hu and hu['status'] == 'ACTIVE':
        parts.append('Hungary axis reversal active: the Tisza government lifted the Orban-era vetoes on Ukraine\'s '
                     'EU path (minority-language law satisfied Budapest, Oct 2026) -- Putin\'s main EU veto vehicle is gone.')
    if commodity_signal and commodity_signal.get('alert') != 'normal':
        parts.append(f"Commodity pressure: {commodity_signal['alert']} (grain corridor + defence export dynamics).")
    if not parts:
        parts.append('No active red lines. Monitoring frontline pressure, Western aid continuity, defence-industrial '
                     'signalling, and the diplomatic track.')
    return {
        'scenario': scenario, 'priority': priority, 'assessment': ' '.join(parts),
        'narrative': _build_so_what_narrative(red_lines, green_lines, diplomatic, commodity_signal, us, nato, drone, health),
        'breached_count': len(breached), 'approaching_count': len(approaching),
        'active_green_count': len(active_gl), 'thin_read': health['thin'],
    }


# ============================================================
# TOP SIGNALS
# ============================================================

def _build_top_signals(red_lines, green_lines, diplomatic, commodity_signal, us, nato, drone):
    signals = []
    SEV = {5: 'critical', 4: 'high', 3: 'elevated', 2: 'normal', 1: 'normal'}
    esc = [r for r in red_lines if r['id'] not in NON_ESCALATORY_LINES]
    for r in sorted([r for r in esc if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])[:3]:
        signals.append({'category': r['category'].lower().replace(' ', '_').replace('/', '_'),
                        'level': SEV.get(r['severity'], 'normal'),
                        'short_text': f"BREACHED: {r['title']} ({r['breach_outlets']} outlets)",
                        'long_text': r['description'], 'icon': '🚨',
                        'source_link': f"/rhetoric-ukraine.html#{r['id']}"})
    for r in sorted([r for r in esc if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])[:2]:
        signals.append({'category': r['category'].lower().replace(' ', '_').replace('/', '_'),
                        'level': 'elevated', 'short_text': f"Approaching: {r['title']}",
                        'long_text': r['description'], 'icon': '⚠️',
                        'source_link': f"/rhetoric-ukraine.html#{r['id']}"})
    if us['level'] >= 2:
        signals.append({'category': 'us_posture', 'level': 'elevated' if us['level'] >= 3 else 'normal',
                        'short_text': f"US: {us['posture'].replace('_', ' ')} · aid {us['aid_pipeline'].replace('_', ' ')}",
                        'long_text': us['read'], 'icon': '🇺🇸', 'source_link': '/rhetoric-ukraine.html#us-vector'})
    if nato['status'] in ('renunciation_on_table', 'guarantees_in_play'):
        signals.append({'category': 'nato_track', 'level': 'elevated',
                        'short_text': 'NATO: ' + nato['status'].replace('_', ' '),
                        'long_text': nato['read'], 'icon': '🛡️', 'source_link': '/rhetoric-ukraine.html#nato-track'})
    if drone['level'] >= 2:
        signals.append({'category': 'iran_link', 'level': 'normal',
                        'short_text': 'Iran link: Ukrainian drone defence in the Gulf / Iran-Russia supply line',
                        'long_text': drone['read'], 'icon': '🛸', 'source_link': '/rhetoric-ukraine.html#iran-link'})
    for g in [g for g in green_lines if g['status'] == 'ACTIVE'][:2]:
        signals.append({'category': 'diplomatic', 'level': 'normal', 'short_text': f"De-escalation: {g['title']}",
                        'long_text': g['description'], 'icon': '🟢', 'source_link': f"/rhetoric-ukraine.html#{g['id']}"})
    if commodity_signal and commodity_signal.get('band'):
        signals.append(commodity_signal['band'])
    if diplomatic['score'] >= 3:
        lvl = {'Active Ceasefire Track': 'high', 'Tentative Diplomatic Signals': 'elevated'}.get(diplomatic['scenario'], 'normal')
        signals.append({'category': 'diplomatic', 'level': lvl,
                        'short_text': f"Diplomatic Track: {diplomatic['scenario']}",
                        'long_text': (f"{diplomatic['scenario']} ({diplomatic['score']} signals). "
                                      + ('Framework-grade evidence present.' if diplomatic.get('framework_active')
                                         else 'Signals only -- conversations, not a signed framework.')),
                        'icon': '🤝', 'source_link': '/rhetoric-ukraine.html#diplomatic'})
    return signals[:8]


# ============================================================
# CROSS-THEATER FINGERPRINTS
# ============================================================

def _build_fingerprints(red_lines, green_lines, us, nato, drone):
    fp = {
        'ukraine_drone_advisor_active': bool(drone['active']),
        'ukraine_grain_corridor_status': 'open',
        'us_aid_continuity': us['aid_pipeline'] != 'suspended',
        'us_aid_pipeline': us['aid_pipeline'],
        'us_posture': us['posture'],
        'nato_track': nato['status'],
        'ukraine_iran_link_level': drone['level'],
        'frontline_pressure': 'normal',
        'kyiv_under_strike': False,
        'mobilization_crisis_active': False,
        'energy_grid_pressure': False,
        'ukraine_hungary_normalization': 'dormant',
        'ukraine_eu_loan_veto_status': 'blocked',
    }
    for r in red_lines:
        if r['status'] not in ('BREACHED', 'APPROACHING'):
            continue
        if r['id'] == 'grain_corridor_disruption':
            fp['ukraine_grain_corridor_status'] = 'disrupted' if r['status'] == 'BREACHED' else 'pressured'
        elif r['id'] == 'frontline_collapse':
            fp['frontline_pressure'] = 'critical' if r['status'] == 'BREACHED' else 'elevated'
        elif r['id'] == 'kyiv_strike_significant':
            fp['kyiv_under_strike'] = True
        elif r['id'] == 'mobilization_crisis_ukraine':
            fp['mobilization_crisis_active'] = True
        elif r['id'] == 'energy_grid_collapse':
            fp['energy_grid_pressure'] = True
    for g in green_lines:
        if g['id'] == 'hungary_bilateral_normalization':
            if g['status'] == 'ACTIVE':
                fp['ukraine_hungary_normalization'], fp['ukraine_eu_loan_veto_status'] = 'active', 'unblocked'
            elif g['status'] == 'SIGNALED':
                fp['ukraine_hungary_normalization'], fp['ukraine_eu_loan_veto_status'] = 'signaled', 'partial'
    return fp


# ============================================================
# MAIN ENTRY
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_ukraine.py."""
    try:
        corpus = build_corpus(scan_data)
        health = corpus_health(scan_data, corpus, THIN_MIN_ARTICLES)
        red_lines = _score_red_lines(corpus)
        green_lines = _score_green_lines(corpus)
        diplomatic = _score_diplomatic_track(corpus, green_lines)
        commodity_sig = _fetch_commodity_signal()
        us = _us_vector(corpus, red_lines)
        nato = _nato_track(corpus)
        drone = _drone_diplomacy(corpus, red_lines)
        russia = _russia_pressure(red_lines)
        actors = _actor_levels(scan_data, red_lines, us, drone)
        so_what = _build_so_what(red_lines, green_lines, diplomatic, commodity_sig, us, nato, drone, health)
        top_signals = _build_top_signals(red_lines, green_lines, diplomatic, commodity_sig, us, nato, drone)
        fingerprints = _build_fingerprints(red_lines, green_lines, us, nato, drone)

        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']
        composite_modifier = diplomatic['modifier'] + ((commodity_sig or {}).get('escalation_modifier', 0))

        return {
            'so_what': so_what,
            'top_signals': top_signals,
            'top_indicator': _top_indicator(red_lines, us, nato, drone, health),
            'red_lines': {'triggered': red_lines, 'breached_count': len(breached),
                          'approaching_count': len(approaching),
                          'highest_severity': max((r['severity'] for r in breached), default=0)},
            'green_lines': {'triggered': green_lines, 'active_count': len(active_gl),
                            'signaled_count': len([g for g in green_lines if g['status'] == 'SIGNALED']),
                            'diplomatic_score': diplomatic['score']},
            'diplomatic_track': diplomatic,
            'us_vector': us,
            'nato_track': nato,
            'drone_diplomacy': drone,
            'russia_pressure': russia,
            'actor_levels': actors,
            'corpus_health': health,
            'thin_read': health['thin'],
            'commodity_signal': commodity_sig,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier': composite_modifier,
            'interpreter_version': INTERPRETER_VERSION,
            'interpreted_at': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[Ukraine Interpreter] Error: {str(e)[:160]}')
        return {
            'so_what': {'scenario': 'Interpreter error -- unread, not calm', 'priority': 'normal',
                        'assessment': str(e)[:200], 'breached_count': 0, 'approaching_count': 0,
                        'active_green_count': 0, 'thin_read': True},
            'top_signals': [], 'top_indicator': 'Interpreter error this cycle -- unread, not calm.',
            'red_lines': {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'green_lines': {'triggered': [], 'active_count': 0, 'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track': {'score': 0, 'scenario': 'Unknown', 'modifier': 0},
            'us_vector': None, 'nato_track': None, 'drone_diplomacy': None, 'russia_pressure': None,
            'actor_levels': {}, 'corpus_health': {'thin': True, 'reason': 'interpreter error'}, 'thin_read': True,
            'commodity_signal': None, 'cross_theater_fingerprints': {}, 'composite_modifier': 0,
            'interpreter_version': INTERPRETER_VERSION, 'error': str(e)[:200],
        }
