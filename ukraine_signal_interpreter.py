"""
═══════════════════════════════════════════════════════════════════════
  ASIFAH ANALYTICS — UKRAINE SIGNAL INTERPRETER
  v1.0.0 (Apr 30 2026)
═══════════════════════════════════════════════════════════════════════

Analytical layer for the Ukraine rhetoric tracker. Reads scan_data
(produced by rhetoric_tracker_ukraine.py), applies red/green-line rules,
detects historical patterns, builds So-What narrative, and emits
canonical top_signals[] for Europe Regional BLUF synthesis.

ANALYTICAL FRAMING:
  Ukraine's rhetoric posture is shaped by four concurrent dynamics:
    1. Frontline / battlefield reality (territorial control, attacks)
    2. Western aid pipeline integrity (US position decisive)
    3. Defense industrial maturation (drone advisor exports unique vector)
    4. Diplomatic / ceasefire prospects
  Plus the cross-cutting commodity vector — wheat, corn, sunflower oil,
  uranium pivot, titanium, steel — Black Sea grain corridor as strategic
  signal node.

ACTOR FRAMEWORK (7 actors):
  - ukrainian_government
  - ukrainian_armed_forces
  - russian_forces_in_ukraine
  - us_government                  (← own actor — aid pipeline decisive)
  - nato_western_support           (Europe + UK + non-US Western)
  - defense_industrial_base        (← includes drone advisor exports
                                      sub-vector for GCC/Israel)
  - occupied_territories_signals

CROSS-THEATER FINGERPRINTS WRITTEN:
  - ukraine_drone_advisor_active  → consumed by ME backend (UAE/Saudi/IL)
  - ukraine_grain_corridor_status → consumed by ME (food security signal)
  - us_aid_continuity             → consumed by Russia + GPI
  - frontline_pressure            → consumed by Russia + GPI

COMMODITY INTEGRATION (Phase 1 light):
  Reads /api/europe/commodity/ukraine and adds ONE band to top_signals.
  Triggers small escalation modifier when alert is high/critical.

USAGE:
  from ukraine_signal_interpreter import interpret_signals
  result = interpret_signals(scan_data)
"""

import requests
from datetime import datetime, timezone

INTERPRETER_VERSION = '1.0.0'

# Europe backend self-call URL (interpreter runs in Europe backend)
COMMODITY_PROXY_URL = 'http://localhost:10000/api/europe/commodity/ukraine'

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
            'zelensky warns', 'zelensky warned', 'zelensky says russia preparing',
            'zelensky intelligence', 'ukrainian intelligence warns',
            'ukrainian intel warns', 'intelligence indicates russia',
            'kyiv warning', 'kyiv warns', 'kyiv intelligence warning',
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
            # ── v1.2 (May 24 2026) news-language expansion ──
            'russia attacks kyiv', 'attack on kyiv', 'strike on kyiv',
            'missile strike kyiv', 'massive attack kyiv',
            'large-scale attack kyiv', 'kyiv overnight', 'overnight attack kyiv',
            'kyiv hit', 'oreshnik kyiv', 'hypersonic kyiv',
            'cabinet of ministers', 'cabinet of ministers damaged',
            'cabinet of ministers building', 'government building damaged kyiv',
            'national bank kyiv', 'mfa damaged',
            'foreign ministry damaged kyiv', 'civilians killed kyiv',
            'killed in kyiv strike', 'kyiv casualties', 'kyiv civilian deaths',
            'injured in kyiv', 'wounded in kyiv', 'kyiv buildings damaged',
            'chornobyl museum kyiv', 'dsns kyiv',
        ],
        'triggers_approaching': [
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
        'id':       'drone_advisor_export_disclosed',
        'category': 'Defense Industry',
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
# KEYWORD MATCHING
# ============================================================

def _check_keywords(scan_data, keywords):
    """Match keywords against scan_data article corpus + signals."""
    if not keywords:
        return 0
    corpus_parts = []
    for key in ('articles_en', 'articles_uk', 'articles_ru', 'articles_pl'):
        for art in (scan_data.get(key) or []):
            corpus_parts.append((art.get('title') or '').lower())
            corpus_parts.append((art.get('description') or '').lower())
            corpus_parts.append((art.get('summary') or '').lower())
            corpus_parts.append((art.get('content') or '').lower())
            # URL slugs encode the full headline (e.g. ".../zelensky-peace-efforts-us-envoys").
            # Slugify so hyphen/underscore-joined words match multi-word keywords.
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                corpus_parts.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('telegram_messages', 'bluesky_signals', 'reddit_signals'):
        for sig in (scan_data.get(key) or []):
            corpus_parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(corpus_parts)
    if not corpus:
        return 0
    matches = 0
    for kw in keywords:
        if kw.lower() in corpus:
            matches += 1
    return matches


# ============================================================
# RED / GREEN LINE SCORING
# ============================================================

def _score_red_lines(scan_data):
    triggered = []
    for rl in RED_LINES:
        breached_hits    = _check_keywords(scan_data, rl.get('triggers_breached', []))
        approaching_hits = _check_keywords(scan_data, rl.get('triggers_approaching', []))
        if breached_hits >= 2:
            status = 'BREACHED'
        elif breached_hits >= 1 or approaching_hits >= 3:
            status = 'APPROACHING'
        elif approaching_hits >= 1:
            status = 'WATCHING'
        else:
            status = 'INACTIVE'
        triggered.append({
            'id': rl['id'], 'category': rl['category'], 'title': rl['title'],
            'severity': rl['severity'], 'description': rl['description'],
            'status': status,
            'breached_hits': breached_hits, 'approaching_hits': approaching_hits,
        })
    return triggered


def _score_green_lines(scan_data):
    triggered = []
    for gl in GREEN_LINES:
        active_hits   = _check_keywords(scan_data, gl.get('triggers_active', []))
        signaled_hits = _check_keywords(scan_data, gl.get('triggers_signaled', []))
        if active_hits >= 1:
            status = 'ACTIVE'
        elif signaled_hits >= 1:
            status = 'SIGNALED'
        else:
            status = 'DORMANT'
        triggered.append({
            'id': gl['id'], 'category': gl['category'], 'title': gl['title'],
            'description': gl['description'], 'status': status,
            'active_hits': active_hits, 'signaled_hits': signaled_hits,
        })
    return triggered


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


def _score_diplomatic_track(scan_data, green_lines_triggered):
    matches  = _check_keywords(scan_data, CEASEFIRE_TRIGGERS)
    negators = _check_keywords(scan_data, CEASEFIRE_NEGATORS)
    # Stance guard: net negative-stance hits against positive matches (floored
    # at 0) so peace being rejected/collapsing does not count as de-escalation.
    net_matches = max(0, matches - negators)

    active_gls = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']
    diplomatic_score = net_matches + (len(active_gls) * 2)

    # Gate (v1.3, Jun 2026): "Active Ceasefire Track" (-10) requires the
    # ceasefire FRAMEWORK green line to be ACTIVE -- framework-grade evidence
    # (named venue, line-of-contact talks, signed framework), NOT a high count
    # of loose keyword matches. Conversations are not negotiations.
    framework_active = any(
        g.get('id') == 'ceasefire_framework_active' for g in active_gls
    )

    if diplomatic_score >= 6 and framework_active:
        scenario = 'Active Ceasefire Track'
        modifier = -10
    elif diplomatic_score >= 3:
        scenario = 'Tentative Diplomatic Signals'
        modifier = -5
    elif diplomatic_score >= 1:
        scenario = 'Limited De-escalation Indicators'
        modifier = -2
    else:
        scenario = 'No Active Track'
        modifier = 0

    return {
        'score':           diplomatic_score,
        'scenario':        scenario,
        'modifier':        modifier,
        'active_green_lines_count': len(active_gls),
        'framework_active': framework_active,
        'negator_hits':    negators,
    }


# ============================================================
# SO WHAT BUILDER
# ============================================================

def _build_so_what_narrative(red_lines_triggered, green_lines_triggered,
                             diplomatic, commodity_signal):
    """Multi-dimensional 'peace So-What' (v1.4): weaves four threads into one
    analyst read -- peace trajectory, the Russia-Ukraine kinetic axis, American
    leverage, and the grain-corridor corollary. CONVERGENCE FRAMING ONLY:
    describes signals present, never predicts action. Returns a list of
    {label, text, tone} threads for structured frontend rendering."""
    def _rl(rid):
        return next((r for r in red_lines_triggered if r.get('id') == rid), {})
    def _gl(gid):
        return next((g for g in green_lines_triggered if g.get('id') == gid), {})
    def _st(d):
        return (d.get('status') or 'INACTIVE').upper()

    threads = []

    # 1) PEACE TRAJECTORY -- from the gated diplomatic track
    scen = diplomatic.get('scenario', 'No Active Track')
    fw   = diplomatic.get('framework_active')
    negs = diplomatic.get('negator_hits', 0)
    if scen == 'Active Ceasefire Track' and fw:
        p_text = ("A ceasefire framework is active -- framework-grade evidence "
                  "(named venue / line-of-contact talks). This is terms, not talk.")
        p_tone = 'calm'
    elif scen == 'Tentative Diplomatic Signals':
        p_text = ("Peace conversations are live -- envoy contact and leader-level "
                  "messaging -- but no signed framework. Treat as talk, not terms.")
        p_tone = 'watch'
    elif scen == 'Limited De-escalation Indicators':
        p_text = ("Scattered de-escalation chatter; no structured negotiating "
                  "track yet.")
        p_tone = 'watch'
    else:
        p_text = "No diplomatic off-ramp detected in the current scan."
        p_tone = 'alert'
    if negs:
        p_text += (" Counter-signal present: language consistent with Moscow "
                   "rejecting terms is also in the corpus.")
    threads.append({'label': 'PEACE TRAJECTORY', 'text': p_text, 'tone': p_tone})

    # 2) RUSSIA-UKRAINE AXIS -- kinetic picture from red lines
    kyiv  = _rl('kyiv_strike_significant')
    grid  = _rl('energy_grid_collapse')
    front = _rl('frontline_collapse')
    nuke  = _rl('tactical_nuclear_signaling')
    warn  = _rl('pre_strike_warning_issued')
    bits = []
    if _st(kyiv) in ('APPROACHING', 'BREACHED'):
        bits.append("significant strikes on Kyiv")
    if _st(warn) in ('APPROACHING', 'BREACHED'):
        bits.append("an active pre-strike warning")
    if _st(grid) in ('WATCHING', 'APPROACHING', 'BREACHED'):
        bits.append("energy-grid pressure (" + _st(grid).lower() + ")")
    if _st(front) in ('APPROACHING', 'BREACHED'):
        bits.append("frontline-collapse indicators")
    nuke_clause = ("; nuclear signaling inactive" if _st(nuke) == 'INACTIVE'
                   else "; nuclear signaling " + _st(nuke).lower())
    if bits:
        a_text = "Kinetic picture: " + ", ".join(bits) + nuke_clause + "."
        a_tone = ('elevated'
                  if any(_st(x) in ('APPROACHING', 'BREACHED')
                         for x in (kyiv, front, nuke))
                  else 'watch')
    else:
        a_text = ("Kinetic picture: routine strike tempo, no red-line breach"
                  + nuke_clause + ".")
        a_tone = 'calm'
    threads.append({'label': 'RUSSIA-UKRAINE AXIS', 'text': a_text, 'tone': a_tone})

    # 3) AMERICAN LEVERAGE -- the decisive variable for war sustainability
    aid_susp = _rl('us_aid_suspension_total')
    if _st(aid_susp) in ('APPROACHING', 'BREACHED'):
        l_text = ("US aid pipeline under stress (" + _st(aid_susp).lower()
                  + ") -- the decisive variable for Ukrainian war sustainability "
                  "is wobbling.")
        l_tone = 'alert'
    else:
        eng = (" and engaged on the envoy track"
               if diplomatic.get('score', 0) > 0 else "")
        l_text = ("US aid pipeline shows no suspension signal" + eng
                  + ". Washington's posture remains the decisive variable.")
        l_tone = 'calm'
    threads.append({'label': 'AMERICAN LEVERAGE', 'text': l_text, 'tone': l_tone})

    # 4) GRAIN COROLLARY -- commodity pressure = news-signal VOLUME, not price
    alert = (commodity_signal or {}).get('alert', 'normal')
    if commodity_signal and alert and alert != 'normal':
        corridor = _rl('grain_corridor_disruption')
        corr_clause = (" Black Sea corridor disruption indicator "
                       + _st(corridor).lower() + "." if corridor else "")
        g_text = ("Commodity pressure at " + alert.upper()
                  + " on news-signal volume (not price); wheat / grain corridor "
                  "the lead exposure." + corr_clause
                  + " Ripples toward MENA food-security signals.")
        g_tone = 'elevated' if alert in ('surge', 'critical', 'high') else 'watch'
    else:
        g_text = ("Commodity pressure normal; grain corridor and defense-export "
                  "vectors quiet.")
        g_tone = 'calm'
    threads.append({'label': 'GRAIN COROLLARY', 'text': g_text, 'tone': g_tone})

    return threads


def _build_so_what(scan_data, red_lines_triggered, green_lines_triggered,
                   diplomatic, commodity_signal):
    breached    = [r for r in red_lines_triggered if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines_triggered if r['status'] == 'APPROACHING']
    active_gl   = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']

    highest_severity = max((r['severity'] for r in breached), default=0)

    if highest_severity >= 5:
        scenario = 'CRITICAL: Strategic Red Line Breached'
        priority = 'critical'
    elif highest_severity >= 4 or len(breached) >= 2:
        scenario = 'HIGH: Multiple Escalation Indicators'
        priority = 'high'
    elif breached or len(approaching) >= 3:
        scenario = 'ELEVATED: Approaching Threshold'
        priority = 'elevated'
    elif approaching:
        scenario = 'WATCH: Early Warning Indicators Active'
        priority = 'watch'
    else:
        scenario = 'NORMAL: Baseline Monitoring'
        priority = 'normal'

    assessment_parts = []

    if breached:
        breached_titles = ', '.join(r['title'] for r in breached[:3])
        assessment_parts.append(f"Red line(s) breached: {breached_titles}.")

    if approaching:
        approaching_titles = ', '.join(r['title'] for r in approaching[:3])
        assessment_parts.append(f"Approaching threshold: {approaching_titles}.")

    if diplomatic['score'] > 0:
        assessment_parts.append(
            f"Diplomatic track: {diplomatic['scenario'].lower()} (score {diplomatic['score']})."
        )

    if active_gl:
        gl_titles = ', '.join(g['title'] for g in active_gl[:2])
        assessment_parts.append(f"Active de-escalation indicators: {gl_titles}.")

    # ── Hungary bilateral normalization narrative (added May 18 2026) ──
    # Even though active_gl above names the green line, the structural
    # significance of Hungary's axis reversal deserves explicit articulation.
    hungary_gl = next(
        (g for g in green_lines_triggered if g['id'] == 'hungary_bilateral_normalization'),
        None
    )
    if hungary_gl and hungary_gl['status'] == 'ACTIVE':
        assessment_parts.append(
            "Hungary axis reversal CONFIRMED: April 2026 Tisza/Magyar election ended "
            "16 years of Orban-era anti-Ukraine policy. Hungary lifted Ukraine EU loan "
            "veto (90 billion euro package unblocked), returned 82 million dollar "
            "Oschadbank cash and gold shipment, restored NATO weapons transit, "
            "pledged 'strong NATO ally' posture. Removes Putin's primary EU veto "
            "vehicle. Transcarpathia ethnic Hungarian minority normalization pathway "
            "opened. Diplomatic track receives durable bilateral support beyond "
            "ceasefire-specific signals."
        )
    elif hungary_gl and hungary_gl['status'] == 'SIGNALED':
        assessment_parts.append(
            "Hungary bilateral normalization SIGNALED: Tisza/Magyar government "
            "post-election signals are detected but not yet confirmed at concrete "
            "action level. Monitor for: Oschadbank asset return execution, EU loan "
            "veto formal lift, NATO weapons transit restoration."
        )

    if commodity_signal and commodity_signal.get('alert') != 'normal':
        assessment_parts.append(
            f"Commodity pressure: {commodity_signal['alert']} "
            f"(grain corridor + defense export dynamics)."
        )

    if not assessment_parts:
        assessment_parts.append(
            "No active red lines. Monitoring baseline frontline pressure, "
            "Western aid continuity, defense industrial signaling, and "
            "diplomatic track."
        )

    return {
        'scenario':            scenario,
        'priority':            priority,
        'assessment':          ' '.join(assessment_parts),
        'narrative':           _build_so_what_narrative(
                                   red_lines_triggered, green_lines_triggered,
                                   diplomatic, commodity_signal),
        'breached_count':      len(breached),
        'approaching_count':   len(approaching),
        'active_green_count':  len(active_gl),
    }


# ============================================================
# TOP SIGNALS BUILDER
# ============================================================

def _build_top_signals(red_lines_triggered, green_lines_triggered,
                       diplomatic, commodity_signal, scan_data):
    signals = []
    SEVERITY_TO_LEVEL = {5: 'critical', 4: 'high', 3: 'elevated',
                         2: 'normal', 1: 'normal'}

    breached = [r for r in red_lines_triggered if r['status'] == 'BREACHED']
    breached.sort(key=lambda r: -r['severity'])
    for r in breached[:3]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       SEVERITY_TO_LEVEL.get(r['severity'], 'normal'),
            'short_text':  f"BREACHED: {r['title']}",
            'long_text':   r['description'],
            'icon':        '🚨',
            'source_link': f"/rhetoric-ukraine.html#{r['id']}",
        })

    approaching = [r for r in red_lines_triggered if r['status'] == 'APPROACHING']
    approaching.sort(key=lambda r: -r['severity'])
    for r in approaching[:2]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       'elevated',
            'short_text':  f"Approaching: {r['title']}",
            'long_text':   r['description'],
            'icon':        '⚠️',
            'source_link': f"/rhetoric-ukraine.html#{r['id']}",
        })

    active_gl = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']
    for g in active_gl[:2]:
        signals.append({
            'category':    'diplomatic',
            'level':       'normal',
            'short_text':  f"De-escalation: {g['title']}",
            'long_text':   g['description'],
            'icon':        '🟢',
            'source_link': f"/rhetoric-ukraine.html#{g['id']}",
        })

    if commodity_signal and commodity_signal.get('band'):
        signals.append(commodity_signal['band'])

    if diplomatic['score'] >= 3:
        # Scenario-driven level (v1.3): headline-grade in roll-ups (rhetoric-index,
        # regional BLUF) instead of stuck at 'normal'. Gate already ensures only a
        # framework-grade track earns 'Active Ceasefire Track'.
        _dip_level = {
            'Active Ceasefire Track':           'high',
            'Tentative Diplomatic Signals':     'elevated',
            'Limited De-escalation Indicators': 'normal',
        }.get(diplomatic['scenario'], 'normal')
        _sig_n = diplomatic['score']
        _sig_word = 'signal' if _sig_n == 1 else 'signals'
        _fw_note = ('Framework-grade evidence present (active ceasefire track).'
                    if diplomatic.get('framework_active')
                    else 'Signals only -- conversations, not a signed framework.')
        signals.append({
            'category':    'diplomatic',
            'level':       _dip_level,
            'short_text':  f"Diplomatic Track: {diplomatic['scenario']}",
            'long_text':   (f"{diplomatic['scenario']} ({_sig_n} {_sig_word}). "
                            f"{_fw_note}"),
            'icon':        '🤝',
            'source_link': '/rhetoric-ukraine.html#diplomatic',
        })

    return signals[:7]


# ============================================================
# CROSS-THEATER FINGERPRINTS
# ============================================================

def _build_fingerprints(red_lines_triggered, green_lines_triggered,
                       commodity_signal, scan_data):
    """
    Fingerprints written for downstream tracker consumption.

    May 18 2026: Added green_lines_triggered parameter to enable Hungary
    bilateral normalization fingerprints (read by Europe BLUF + GPI).
    """
    fingerprints = {
        'ukraine_drone_advisor_active':    False,
        'ukraine_grain_corridor_status':   'open',  # 'open'/'pressured'/'disrupted'
        'us_aid_continuity':               True,    # default-on, flips on suspension red line
        'frontline_pressure':              'normal', # 'normal'/'elevated'/'critical'
        'kyiv_under_strike':               False,
        'mobilization_crisis_active':      False,
        'energy_grid_pressure':            False,
        # Hungary bilateral signals (added May 18 2026)
        'ukraine_hungary_normalization':   'dormant',  # 'active'/'signaled'/'dormant'
        'ukraine_eu_loan_veto_status':     'blocked',  # 'unblocked'/'partial'/'blocked'
    }

    # Red-line driven fingerprints (existing)
    for r in red_lines_triggered:
        if r['status'] in ('BREACHED', 'APPROACHING'):
            if r['id'] == 'drone_advisor_export_disclosed':
                fingerprints['ukraine_drone_advisor_active'] = True
            elif r['id'] == 'grain_corridor_disruption':
                fingerprints['ukraine_grain_corridor_status'] = (
                    'disrupted' if r['status'] == 'BREACHED' else 'pressured'
                )
            elif r['id'] == 'us_aid_suspension_total':
                if r['status'] == 'BREACHED':
                    fingerprints['us_aid_continuity'] = False
            elif r['id'] == 'frontline_collapse':
                fingerprints['frontline_pressure'] = (
                    'critical' if r['status'] == 'BREACHED' else 'elevated'
                )
            elif r['id'] == 'kyiv_strike_significant':
                fingerprints['kyiv_under_strike'] = True
            elif r['id'] == 'mobilization_crisis_ukraine':
                fingerprints['mobilization_crisis_active'] = True
            elif r['id'] == 'energy_grid_collapse':
                fingerprints['energy_grid_pressure'] = True

    # Green-line driven fingerprints (added May 18 2026)
    for g in green_lines_triggered:
        if g['id'] == 'hungary_bilateral_normalization':
            if g['status'] == 'ACTIVE':
                fingerprints['ukraine_hungary_normalization'] = 'active'
                fingerprints['ukraine_eu_loan_veto_status']   = 'unblocked'
            elif g['status'] == 'SIGNALED':
                fingerprints['ukraine_hungary_normalization'] = 'signaled'
                fingerprints['ukraine_eu_loan_veto_status']   = 'partial'

    return fingerprints


# ============================================================
# MAIN ENTRY
# ============================================================

def interpret_signals(scan_data):
    """
    Main entry point. Called from rhetoric_tracker_ukraine.py.
    Returns interpretation dict with canonical top_signals[].
    """
    try:
        red_lines      = _score_red_lines(scan_data)
        green_lines    = _score_green_lines(scan_data)
        diplomatic     = _score_diplomatic_track(scan_data, green_lines)
        commodity_sig  = _fetch_commodity_signal()
        so_what        = _build_so_what(scan_data, red_lines, green_lines,
                                        diplomatic, commodity_sig)
        top_signals    = _build_top_signals(red_lines, green_lines,
                                            diplomatic, commodity_sig, scan_data)
        fingerprints   = _build_fingerprints(red_lines, green_lines, commodity_sig, scan_data)

        breached    = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl   = [g for g in green_lines if g['status'] == 'ACTIVE']

        composite_modifier = diplomatic['modifier']
        if commodity_sig:
            composite_modifier += commodity_sig.get('escalation_modifier', 0)

        return {
            'so_what':             so_what,
            'top_signals':         top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in red_lines), default=0),
            },
            'green_lines': {
                'triggered':         green_lines,
                'active_count':      len(active_gl),
                'signaled_count':    len([g for g in green_lines if g['status'] == 'SIGNALED']),
                'diplomatic_score':  diplomatic['score'],
            },
            'diplomatic_track':           diplomatic,
            'commodity_signal':           commodity_sig,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':         composite_modifier,
            'interpreter_version':        INTERPRETER_VERSION,
            'interpreted_at':             datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        print(f'[Ukraine Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what': {
                'scenario':           'Interpreter error',
                'priority':           'normal',
                'assessment':         str(e)[:200],
                'breached_count':     0,
                'approaching_count':  0,
                'active_green_count': 0,
            },
            'top_signals':                [],
            'red_lines':                  {'triggered': [], 'breached_count': 0,
                                           'approaching_count': 0, 'highest_severity': 0},
            'green_lines':                {'triggered': [], 'active_count': 0,
                                           'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track':           {'score': 0, 'scenario': 'Unknown', 'modifier': 0},
            'commodity_signal':           None,
            'cross_theater_fingerprints': {},
            'composite_modifier':         0,
            'interpreter_version':        INTERPRETER_VERSION,
            'error':                      str(e)[:200],
        }
